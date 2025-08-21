import os
import shutil
from pathlib import Path
import subprocess
import json
from datetime import datetime

def cleanup_old_builds():
    """Clean all old build and release folders"""
    folders_to_clean = ["dist", "build", "release", "release_offline"]
    print("[CLEANUP] Removing old builds and releases...")
    
    for folder_name in folders_to_clean:
        folder_path = Path(folder_name)
        if folder_path.exists():
            try:
                shutil.rmtree(folder_path)
                print(f"[CLEANUP] ✅ Removed: {folder_path}")
            except Exception as e:
                print(f"[CLEANUP] ❌ Failed to remove {folder_path}: {e}")
        else:
            print(f"[CLEANUP] ⏭️ Skipped (not found): {folder_path}")
    
    print("[CLEANUP] Old builds cleanup completed!")

def create_icon_if_needed():
    """Create application icon if it doesn't exist"""
    icon_path = Path("assets/icon.ico")
    if icon_path.exists():
        return str(icon_path)
    
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        os.makedirs('assets', exist_ok=True)
        
        size = 256
        image = Image.new('RGBA', (size, size), (124, 92, 255, 255))
        draw = ImageDraw.Draw(image)
        
        # Draw circle
        margin = 20
        draw.ellipse([margin, margin, size-margin, size-margin], 
                    fill=(124, 92, 255, 255), outline=(100, 70, 200, 255), width=4)
        
        # Add text
        try:
            font = ImageFont.truetype("arial.ttf", 120)
        except:
            font = ImageFont.load_default()
        
        text = "U"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox  # ✅ Fixed
        text_height = bbox - bbox[1]  # ✅ Fixed
        
        x = (size - text_width) // 2
        y = (size - text_height) // 2
        
        draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
        
        image.save(icon_path, format='ICO', 
                  sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
        
        print(f"[OK] Icon created: {icon_path}")
        return str(icon_path)
        
    except Exception as e:
        print(f"[WARNING] Icon creation failed: {e}")
        return None

def build_offline_app():
    """Build UniNames for OFFLINE deployment (no auto-updater)"""
    print("=" * 60)
    print("🔌 BUILDING UNINAMES FOR OFFLINE USE")
    print("=" * 60)
    
    start_time = datetime.now()
    
    # ✅ Clean ALL old builds first
    cleanup_old_builds()
    
    # Create required directories
    required_dirs = ["configs", "assets", "logs"]
    for dir_name in required_dirs:
        Path(dir_name).mkdir(exist_ok=True)
        print(f"[SETUP] Created directory: {dir_name}")
    
    # Create app config for OFFLINE mode
    config_file = Path("configs/app_config.json")
    config_content = {
        "app_name": "UniNames Medical Suite",
        "version": "2.1.0-OFFLINE",
        "build_date": datetime.now().isoformat(),
        "theme": "dark",
        "auto_updater_enabled": False,  # ✅ DISABLED for offline
        "debug_mode": False,
        "offline_mode": True  # ✅ NEW flag
    }
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config_content, f, indent=2)
    print(f"[CONFIG] Created OFFLINE config: {config_file}")
    
    # Create application icon
    icon_path = create_icon_if_needed()
    
    # Verify required files exist
    required_files = [
        "main_app.py",
        "src/uni_names/clean_names_app_qt.py",
        "src/uni_names/reference_search.py"
    ]
    
    missing_files = [f for f in required_files if not Path(f).exists()]
    if missing_files:
        print(f"[ERROR] Missing required files: {missing_files}")
        return False
    
    # Build command for OFFLINE version
    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name", "UniNames_Medical_Suite_OFFLINE",  # ✅ Different name
        "--distpath", "dist",
        "--workpath", "build",
        "--specpath", ".",
    ]
    
    # Add icon if available
    if icon_path and Path(icon_path).exists():
        cmd.extend(["--icon", icon_path])
        print(f"[ICON] Using: {icon_path}")
    
    # Add data directories
    data_mappings = [
        ("src", "src"),
        ("doctor_cleaner", "doctor_cleaner"),
        ("configs", "configs")
    ]
    
    # Only add directories that exist
    if Path("reference").exists():
        data_mappings.append(("reference", "reference"))
    
    for src, dest in data_mappings:
        if Path(src).exists():
            cmd.extend(["--add-data", f"{src};{dest}"])
            print(f"[DATA] Including: {src} -> {dest}")
    
    # Hidden imports - EXCLUDE requests for offline version
    hidden_imports = [
        "pandas", "PyQt6", "PyQt6.QtCore", "PyQt6.QtWidgets", "PyQt6.QtGui",
        "fuzzywuzzy", "openpyxl", "xlsxwriter", "pathlib", "json",
        "logging", "datetime", "re", "sys", "os", "io", "builtins"
        # ✅ NO "requests" - removed for offline version
    ]
    
    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])
    
    # Additional PyInstaller options
    cmd.extend([
        "--collect-all", "PyQt6",
        "--noupx",  # Disable UPX compression
        "--clean",   # Clean PyInstaller cache
        "main_app.py"
    ])
    
    print("[BUILD] Starting PyInstaller for OFFLINE version...")
    print(f"[COMMAND] {' '.join(cmd[:10])}...")
    
    # Run PyInstaller
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            print("[SUCCESS] PyInstaller completed successfully!")
            
            # Verify executable was created
            exe_source = Path("dist/UniNames_Medical_Suite_OFFLINE.exe")
            if exe_source.exists():
                # Create release directory
                release_folder = Path("release_offline")
                release_folder.mkdir(exist_ok=True)
                
                # Copy executable with versioned name
                build_time = datetime.now().strftime("%Y%m%d_%H%M")
                exe_name = f"UniNames_Medical_Suite_OFFLINE_v2.1.0_{build_time}.exe"
                exe_dest = release_folder / exe_name
                
                shutil.copy2(exe_source, exe_dest)
                
                # Also create a generic copy
                generic_dest = release_folder / "UniNames_Medical_Suite_OFFLINE.exe"
                shutil.copy2(exe_source, generic_dest)
                
                # Calculate file size
                file_size_mb = exe_dest.stat().st_size / (1024*1024)
                build_duration = (datetime.now() - start_time).total_seconds()
                
                # Create deployment info
                deploy_info = {
                    "version": "2.1.0-OFFLINE",
                    "build_date": datetime.now().isoformat(),
                    "build_duration_seconds": build_duration,
                    "executable_size_mb": round(file_size_mb, 1),
                    "executable_name": exe_name,
                    "offline_mode": True,
                    "auto_updater": False,
                    "features": [
                        "Doctor names cleaning and standardization",
                        "Golden reference database search",
                        "Responsive UI with dark theme",
                        "Unicode support for international names",
                        "OFFLINE MODE - No internet required"
                    ],
                    "system_requirements": {
                        "os": "Windows 10/11 (64-bit)",
                        "ram": "4GB minimum",
                        "disk_space": "200MB",
                        "internet": "NOT REQUIRED"
                    }
                }
                
                with open(release_folder / "deployment_info.json", 'w', encoding='utf-8') as f:
                    json.dump(deploy_info, f, indent=2)
                
                # Create README for OFFLINE version
                readme_content = f"""
UniNames Medical Suite v2.1.0-OFFLINE
====================================

🔌 OFFLINE Medical Names Processing Application

Build Information:
• Version: {deploy_info['version']}
• Build Date: {deploy_info['build_date'][:19]}
• File Size: {deploy_info['executable_size_mb']} MB
• Build Duration: {deploy_info['build_duration_seconds']:.1f} seconds
• Mode: OFFLINE (No internet required)

Features:
• Doctor names cleaning and standardization
• Golden reference database search and matching
• Advanced fuzzy search with partial matching
• Responsive UI with modern dark theme
• Unicode support for international names
• Multi-language processing capabilities
• ✅ WORKS COMPLETELY OFFLINE

System Requirements:
• Windows 10/11 (64-bit)
• 4GB RAM minimum
• 200MB free disk space
• ❌ NO INTERNET CONNECTION REQUIRED

Installation:
1. Download UniNames_Medical_Suite_OFFLINE.exe
2. Run the executable (no installation required)
3. Allow Windows Defender if prompted
4. The application will start automatically
5. ✅ No internet connection needed after installation

Usage:
• Double-click the executable to start
• Use sidebar navigation to switch between modules
• All features work without internet connection
• No automatic updates (manual upgrade required)

Differences from Online Version:
• No auto-update system
• No internet connectivity features
• Smaller file size (no requests library)
• Perfect for isolated/secure environments

Support:
For technical support or manual updates, contact the development team.

© 2025 Development Team
All rights reserved.
"""
                
                with open(release_folder / "README_OFFLINE.txt", 'w', encoding='utf-8') as f:
                    f.write(readme_content)
                
                print("=" * 60)
                print("🔌 OFFLINE BUILD SUCCESSFUL!")
                print("=" * 60)
                print(f"📁 Output Directory: {release_folder.absolute()}")
                print(f"💾 Executable: {exe_name}")  
                print(f"💾 Generic Copy: UniNames_Medical_Suite_OFFLINE.exe")
                print(f"📏 File Size: {file_size_mb:.1f} MB")
                print(f"⏱️ Build Time: {build_duration:.1f} seconds")
                print(f"📋 Documentation: README_OFFLINE.txt")
                print(f"📋 Deploy Info: deployment_info.json")
                print("🔌 OFFLINE MODE: No internet required!")
                print("=" * 60)
                print("✅ Ready for offline distribution!")
                
                # ✅ Clean temporary build files after success
                print("\n[POST-BUILD CLEANUP] Removing temporary build files...")
                if Path("build").exists():
                    shutil.rmtree("build")
                    print("[POST-BUILD CLEANUP] ✅ Removed: build/")
                if Path("dist").exists():
                    shutil.rmtree("dist") 
                    print("[POST-BUILD CLEANUP] ✅ Removed: dist/")
                print("[POST-BUILD CLEANUP] ✅ Temporary files cleaned!")
                
                return True
                
            else:
                print("[ERROR] Executable not found after build!")
                return False
                
        else:
            print("[ERROR] PyInstaller failed!")
            print("STDOUT:", result.stdout[-1000:] if result.stdout else "None")
            print("STDERR:", result.stderr[-1000:] if result.stderr else "None")
            return False
            
    except subprocess.TimeoutExpired:
        print("[ERROR] Build timed out after 10 minutes!")
        return False
    except Exception as e:
        print(f"[ERROR] Unexpected error during build: {e}")
        return False

def main():
    """Main build entry point for OFFLINE version"""
    success = build_offline_app()
    
    if success:
        print("\n🔌 OFFLINE Build completed successfully!")
        print("The application is ready for offline deployment and distribution.")
        print("✅ No internet connection required to run this version.")
        print("🗑️ Old builds have been automatically cleaned up.")
        input("\nPress Enter to exit...")
    else:
        print("\n❌ Build failed!")
        print("Check the error messages above and try again.")
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
