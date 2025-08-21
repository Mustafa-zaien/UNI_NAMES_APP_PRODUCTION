import requests
import json
import os
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from PyQt6.QtWidgets import QMessageBox, QProgressDialog
from PyQt6.QtCore import QThread, pyqtSignal

class GitHubUpdateChecker(QThread):
    """Thread to check for updates from GitHub releases"""
    update_available = pyqtSignal(dict)
    no_update = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, current_version="2.1.0"):
        super().__init__()
        self.current_version = current_version
        # ✅ استخدام GitHub API للريبو الخاص بك
        self.github_repo = "Mustafa-zaien/UNI_NAMES_APP_PRODUCTION"
        self.api_url = f"https://api.github.com/repos/{self.github_repo}/releases/latest"
    
    def run(self):
        """Check GitHub for latest release"""
        try:
            headers = {
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'UniNames-Updater/1.0'
            }
            
            response = requests.get(self.api_url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                release_data = response.json()
                
                # Extract version (remove 'v' prefix if exists)
                remote_version = release_data.get("tag_name", "").lstrip('v')
                
                # Find downloadable asset (.exe or .zip)
                download_url = None
                file_size = 0
                
                for asset in release_data.get("assets", []):
                    if asset["name"].endswith((".exe", ".zip")):
                        download_url = asset["browser_download_url"]
                        file_size = asset.get("size", 0)
                        break
                
                if self.is_newer_version(remote_version) and download_url:
                    update_info = {
                        "version": remote_version,
                        "download_url": download_url,
                        "changelog": release_data.get("body", "New features and improvements"),
                        "release_date": release_data.get("published_at", ""),
                        "size_mb": round(file_size / (1024*1024), 1) if file_size > 0 else 0
                    }
                    self.update_available.emit(update_info)
                else:
                    self.no_update.emit()
                    
            elif response.status_code == 404:
                self.error.emit("Repository not found or no releases available")
            else:
                self.error.emit(f"GitHub API error: {response.status_code}")
                
        except requests.exceptions.Timeout:
            self.error.emit("Connection timeout - please check your internet")
        except Exception as e:
            self.error.emit(f"Update check failed: {str(e)}")
    
    def is_newer_version(self, remote_version):
        """Compare version numbers"""
        try:
            current_parts = [int(x) for x in self.current_version.split('.')]
            remote_parts = [int(x) for x in remote_version.split('.')]
            
            # Pad with zeros if needed
            max_len = max(len(current_parts), len(remote_parts))
            current_parts.extend([0] * (max_len - len(current_parts)))
            remote_parts.extend([0] * (max_len - len(remote_parts)))
            
            return remote_parts > current_parts
        except ValueError:
            return False

class UpdateDownloader(QThread):
    """Thread to download update file"""
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, download_url, filename):
        super().__init__()
        self.download_url = download_url
        self.filename = filename
    
    def run(self):
        """Download update file with progress tracking"""
        try:
            headers = {
                'User-Agent': 'UniNames-Updater/1.0'
            }
            
            response = requests.get(self.download_url, stream=True, headers=headers, timeout=60)
            total_size = int(response.headers.get('content-length', 0))
            
            downloaded_size = 0
            with open(self.filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:  # filter out keep-alive new chunks
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        if total_size > 0:
                            progress = int((downloaded_size / total_size) * 100)
                            self.progress.emit(progress)
            
            self.finished.emit(self.filename)
        except Exception as e:
            self.error.emit(str(e))

class AutoUpdater:
    """Main auto-updater controller"""
    
    def __init__(self, parent_widget, current_version="2.1.0"):
        self.parent = parent_widget
        self.current_version = current_version
        self.temp_dir = Path.cwd() / "temp_updates"
        self.temp_dir.mkdir(exist_ok=True)
    
    def check_for_updates(self, show_no_update_message=True):
        """Check for available updates"""
        self.checker = GitHubUpdateChecker(self.current_version)
        self.checker.update_available.connect(self.handle_update_available)
        self.checker.no_update.connect(lambda: self.show_no_update(show_no_update_message))
        self.checker.error.connect(self.handle_error)
        self.checker.start()
    
    def handle_update_available(self, update_info):
        """Handle when update is available"""
        size_info = f"\nFile size: {update_info.get('size_mb', 'Unknown')} MB" if update_info.get('size_mb') else ""
        
        reply = QMessageBox.question(
            self.parent,
            "تحديث متوفر - Update Available",
            f"🆕 New update available!\n\n"
            f"📱 Current version: {self.current_version}\n"
            f"🚀 New version: {update_info.get('version', '')}\n"
            f"{size_info}\n\n"
            f"📋 What's new:\n{update_info.get('changelog', 'New features and improvements')}\n\n"
            f"Do you want to update now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.download_update(update_info)
    
    def download_update(self, update_info):
        """Download the update file"""
        download_url = update_info.get('download_url', '')
        
        # Determine file extension from URL
        if download_url.endswith('.exe'):
            filename = self.temp_dir / "update.exe"
        else:
            filename = self.temp_dir / "update.zip"
        
        # Show progress dialog
        self.progress_dialog = QProgressDialog(
            f"Downloading update v{update_info.get('version', '')}...", 
            "Cancel", 0, 100, self.parent
        )
        self.progress_dialog.setWindowTitle("جاري التحديث - Updating Application")
        self.progress_dialog.setModal(True)
        
        # Start download
        self.downloader = UpdateDownloader(download_url, str(filename))
        self.downloader.progress.connect(self.progress_dialog.setValue)
        self.downloader.finished.connect(self.install_update)
        self.downloader.error.connect(self.handle_download_error)
        self.downloader.start()
        
        self.progress_dialog.show()
    
    def handle_download_error(self, error_message):
        """Handle download errors"""
        self.progress_dialog.close()
        QMessageBox.warning(
            self.parent, 
            "Download Error", 
            f"Failed to download update:\n{error_message}\n\nPlease try again later."
        )
    
    def install_update(self, update_file):
        """Install the downloaded update"""
        self.progress_dialog.close()
        
        # Check if downloaded file exists and is valid
        if not Path(update_file).exists():
            QMessageBox.warning(self.parent, "Error", "Downloaded file not found!")
            return
        
        # Create updater script
        updater_script = self.create_updater_script(update_file)
        
        # Show final confirmation
        reply = QMessageBox.question(
            self.parent,
            "Install Update",
            "Update downloaded successfully!\n\n"
            "The application will now restart to complete the installation.\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Run updater script and close current app
            try:
                subprocess.Popen([sys.executable, updater_script], 
                               creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform.startswith('win') else 0)
                
                # Close current application
                sys.exit(0)
            except Exception as e:
                QMessageBox.warning(self.parent, "Error", f"Failed to start updater: {e}")
    
    def create_updater_script(self, update_file):
        """Create external updater script"""
        script_path = self.temp_dir / "updater.py"
        
        # Determine if we're updating with .exe or .zip
        is_exe = update_file.endswith('.exe')
        
        script_content = f'''
import time
import zipfile
import shutil
import subprocess
import os
from pathlib import Path

def main():
    print("Starting update process...")
    time.sleep(3)  # Wait for main app to close completely
    
    try:
        update_file = r"{update_file}"
        current_dir = Path.cwd()
        
        if "{is_exe}":
            # Direct .exe replacement
            target_exe = current_dir / "UniNames_Medical_Suite.exe"
            if target_exe.exists():
                # Backup current version
                backup_path = current_dir / "UniNames_Medical_Suite_backup.exe"
                shutil.copy2(target_exe, backup_path)
                print("Created backup of current version")
            
            # Replace with new version
            shutil.copy2(update_file, target_exe)
            print("Replaced executable with new version")
            
        else:
            # Extract from zip
            with zipfile.ZipFile(update_file, 'r') as zip_ref:
                zip_ref.extractall(current_dir)
            print("Update extracted successfully")
        
        # Clean up downloaded file
        os.remove(update_file)
        print("Cleaned up temporary files")
        
        # Restart application
        app_path = current_dir / "UniNames_Medical_Suite.exe"
        if app_path.exists():
            print("Restarting application...")
            subprocess.Popen([str(app_path)])
            print("Application restarted successfully")
        else:
            print("Warning: Application executable not found")
            input("Press Enter to close...")
        
    except Exception as e:
        print(f"Update error: {{e}}")
        input("Press Enter to close...")

if __name__ == "__main__":
    main()
'''
        
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        return str(script_path)
    
    def show_no_update(self, show_message):
        """Show no update available message"""
        if show_message:
            QMessageBox.information(
                self.parent, 
                "No Updates", 
                f"✅ You are using the latest version ({self.current_version})\n\n"
                f"No updates available at this time."
            )
    
    def handle_error(self, error_message):
        """Handle update check errors"""
        QMessageBox.warning(
            self.parent, 
            "Update Check Failed", 
            f"Unable to check for updates:\n{error_message}\n\n"
            f"Please check your internet connection and try again."
        )

# Alias for backwards compatibility
UpdateChecker = GitHubUpdateChecker
