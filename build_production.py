import os
import shutil
from pathlib import Path
import subprocess
import json
from datetime import datetime

def cleanup_old_builds():
    """Clean all old build and release folders"""
    folders_to_clean = ["dist", "build", "release"]
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
        text_width = bbox[2] - bbox    # ✅ Fixed
        text_height = bbox - bbox[1]   # ✅ Fixed
        
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

def build_production_app():
    """Build UniNames for production deployment"""
    print("=" * 60)
    print("🚀 BUILDING UNINAMES FOR PRODUCTION")
    print("=" * 60)
    
    start_time = datetime.now()
    
    # ✅ Clean ALL old builds first
    cleanup_old_builds()
    
    # Create required directories
    required_dirs = ["configs", "assets", "logs"]
    for dir_name in required_dirs:
        Path(dir_name).mkdir(exist_ok=True)
        print(f"[SETUP] Created directory: {dir_name}")
    
    # Create app config
    config_file = Path("configs/app_config.json")
    if not config_file.exists():
        config_content = {
            "app_name": "UniNames Medical Suite",
            "version": "2.1.0",
            "build_date": datetime.now().isoformat(),
            "theme": "dark",
            "auto_updater_enabled": True,
            "debug_mode": False
        }
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_content, f, indent=2)
        print(f"[CONFIG] Created: {config_file}")
    
    # Create application icon (will use existing if found)
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
    
    # Build command with comprehensive options
    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name", "UniNames_Medical_Suite",
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
    
    # Hidden imports for all required modules
    hidden_imports = [
        "pandas", "PyQt6", "PyQt6.QtCore", "PyQt6.QtWidgets", "PyQt6.QtGui",
        "fuzzywuzzy", "openpyxl", "xlsxwriter", "requests", "pathlib", "json",
        "logging", "datetime", "re", "sys", "os", "io", "builtins"
    ]
    
    for imp in hidden_imports:
        cmd.extend(["--hidden-import", imp])
    
    # Additional PyInstaller options
    cmd.extend([
        "--collect-all", "PyQt6",
        "--noupx",  # Disable UPX compression for better compatibility
        "--clean",   # Clean PyInstaller cache
        "main_app.py"
    ])
    
    print("[BUILD] Starting PyInstaller...")
    print(f"[COMMAND] {' '.join(cmd[:10])}...")
    
    # Run PyInstaller
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            print("[SUCCESS] PyInstaller completed successfully!")
            
            # Verify executable was created
            exe_source = Path("dist/UniNames_Medical_Suite.exe")
            if exe_source.exists():
                # Create release directory
                release_folder = Path("release")
                release_folder.mkdir(exist_ok=True)
                
                # Copy executable with versioned name
                build_time = datetime.now().strftime("%Y%m%d_%H%M")
                exe_name = f"UniNames_Medical_Suite_v2.1.0_{build_time}.exe"
                exe_dest = release_folder / exe_name
                
                shutil.copy2(exe_source, exe_dest)
                
                # Also create a generic copy
                generic_dest = release_folder / "UniNames_Medical_Suite.exe"
                shutil.copy2(exe_source, generic_dest)
                
                # Calculate file size
                file_size_mb = exe_dest.stat().st_size / (1024*1024)
                build_duration = (datetime.now() - start_time).total_seconds()
                
                # Create deployment info
                deploy_info = {
                    "version": "2.1.0",
                    "build_date": datetime.now().isoformat(),
                    "build_duration_seconds": build_duration,
                    "executable_size_mb": round(file_size_mb, 1),
                    "executable_name": exe_name,
                    "features": [
                        "Doctor names cleaning and standardization",
                        "Golden reference database search",
                        "Auto-update system with GitHub integration",
                        "Responsive UI with dark theme",
                        "Unicode support for international names"
                    ],
                    "system_requirements": {
                        "os": "Windows 10/11 (64-bit)",
                        "ram": "4GB minimum",
                        "disk_space": "200MB"
                    }
                }
                
                with open(release_folder / "deployment_info.json", 'w', encoding='utf-8') as f:
                    json.dump(deploy_info, f, indent=2)
                
                # Create README
                readme_content = f"""
UniNames Medical Suite v2.1.0
============================

🚀 Professional Medical Names Processing Application

Build Information:
• Version: {deploy_info['version']}
• Build Date: {deploy_info['build_date'][:19]}
• File Size: {deploy_info['executable_size_mb']} MB
• Build Duration: {deploy_info['build_duration_seconds']:.1f} seconds

Features:
• Doctor names cleaning and standardization
• Golden reference database search and matching
• Advanced fuzzy search with partial matching
• Auto-update system with GitHub integration
• Responsive UI with modern dark theme
• Unicode support for international names
• Multi-language processing capabilities

System Requirements:
• Windows 10/11 (64-bit)
• 4GB RAM minimum
• 200MB free disk space
• Internet connection for updates

Installation:
1. Download UniNames_Medical_Suite.exe
2. Run the executable (no installation required)
3. Allow Windows Defender if prompted
4. The application will start automatically

Usage:
• Double-click the executable to start
• Use sidebar navigation to switch between modules
• Check Help -> About for version information
• Use Help -> Check for Updates for latest version

Support:
For technical support or feature requests, contact the development team.

© 2025 Development Team
All rights reserved.
"""
                
                with open(release_folder / "README.txt", 'w', encoding='utf-8') as f:
                    f.write(readme_content)
                
                print("=" * 60)
                print("🎉 PRODUCTION BUILD SUCCESSFUL!")
                print("=" * 60)
                print(f"📁 Output Directory: {release_folder.absolute()}")
                print(f"💾 Executable: {exe_name}")
                print(f"💾 Generic Copy: UniNames_Medical_Suite.exe")
                print(f"📏 File Size: {file_size_mb:.1f} MB")
                print(f"⏱️ Build Time: {build_duration:.1f} seconds")
                print(f"📋 Documentation: README.txt")
                print(f"📋 Deploy Info: deployment_info.json")
                print("=" * 60)
                print("✅ Ready for distribution!")
                
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
    """Main build entry point"""
    success = build_production_app()
    
    if success:
        print("\n🚀 Build completed successfully!")
        print("The application is ready for deployment and distribution.")
        print("🗑️ Old builds have been automatically cleaned up.")
        input("\nPress Enter to exit...")
    else:
        print("\n❌ Build failed!")
        print("Check the error messages above and try again.")
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
