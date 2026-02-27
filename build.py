#!/usr/bin/env python3
import os
import sys
import shutil
import importlib.util
import subprocess
import time
import urllib.request

def check_dependencies():
    """Checks if required dependencies are installed."""
    required = [
        'PySide6', 'httpx', 'semver', 'dateutil', 'qdarktheme', 'appdirs', 'typing_extensions', 'PyInstaller'
    ]
    missing = []
    for req in required:
        if not importlib.util.find_spec(req):
            missing.append(req)
    
    if missing:
        print("\n[ERROR] Missing dependencies in the current environment:")
        for m in missing:
            print(f"  - {m}")
        
        # Map import names to package names for pip
        package_map = {
            'dateutil': 'python-dateutil',
            'typing_extensions': 'typing-extensions',
            'qdarktheme': 'pyqtdarktheme',
            'PyInstaller': 'pyinstaller'
        }
        packages = [package_map.get(m, m) for m in missing]
        install_cmd = "python -m pip install " + " ".join(packages)
        print(f"\nPlease install them using:\n  {install_cmd}\n")
        sys.exit(1)

def build(sde_only=False):
    if not sde_only:
        # Import PyInstaller here to avoid crash if not installed
        import PyInstaller.__main__
        from PyInstaller.utils.hooks import collect_submodules
        
    # Get the absolute path to the project root
    # We assume this script is located in the project root
    project_root = os.path.abspath(os.path.dirname(__file__))
    src_path = os.path.join(project_root, 'src')
    
    # Path to the database folder
    db_src = os.path.join(src_path, 'database')
    
    print(f"Project Root: {project_root}")
    print(f"Source Path: {src_path}")
    print(f"Database Source: {db_src}")

    # Use a temporary name without spaces for the build to avoid PyInstaller path issues
    app_name_build = "ShortCircuit"
    app_name_final = "Short Circuit"

    # 0. Check dependencies
    if not sde_only:
        check_dependencies()

    # 1. Check and download SDE files
    required_sde = [
        'mapLocationWormholeClasses.csv',
        'mapSolarSystemJumps.csv',
        'mapSolarSystems.csv',
        'mapRegions.csv',
        'statics.csv',
        'renames.csv'
    ]
    
    if not os.path.exists(db_src):
        os.makedirs(db_src)
        
    base_url = "https://www.fuzzwork.co.uk/dump/latest/"
    print(f"Checking SDE files in {db_src}...")
    
    for sde in required_sde:
        path = os.path.join(db_src, sde)
        if not os.path.exists(path):
            print(f"  - Downloading {sde}...")
            try:
                urllib.request.urlretrieve(f"{base_url}{sde}", path)
            except Exception as e:
                print(f"[ERROR] Failed to download {sde}: {e}")
                sys.exit(1)

    if sde_only:
        print("SDE download complete. Skipping PyInstaller build.")
        return

    # 3. Clean previous builds
    dist_dir = os.path.join(project_root, 'dist')
    build_dir = os.path.join(project_root, 'build')
    
    for path_to_clean in [dist_dir, build_dir]:
        if os.path.exists(path_to_clean):
            print(f"Cleaning {path_to_clean}...")
            try:
                shutil.rmtree(path_to_clean)
            except OSError:
                print(f"  - Retrying clean of {path_to_clean}...")
                time.sleep(1)
                try:
                    shutil.rmtree(path_to_clean)
                except OSError as e:
                    print(f"[ERROR] Could not clean {path_to_clean}: {e}")
                    print("Please ensure the application is not running and try again.")
                    sys.exit(1)

    # 4. Configure PyInstaller
    # On Windows use ';', on Unix use ':'
    separator = ';' if os.name == 'nt' else ':'
    
    # This tells PyInstaller: "Take the CONTENTS of db_src and put them in a folder named 'database' in the bundle"
    add_data = f"{db_src}{separator}database"
    
    print(f"Adding data: {add_data}")

    # Add src to sys.path so PyInstaller can find the package
    sys.path.insert(0, src_path)
    
    # Automatically find all submodules in the shortcircuit package
    hidden_imports = collect_submodules('shortcircuit')
    
    # Add other necessary hidden imports
    hidden_imports.extend([
        'httpx',
        'dateutil',
        'semver',
        'qdarktheme',
        'typing_extensions',
        'appdirs',
        'shortcircuit.model.wanderer',
    ])

    # Configure PyInstaller arguments
    pyi_args = [
        os.path.join(src_path, 'main.py'),
        f'--name={app_name_build}',         # Use name without spaces for build
        '--windowed',                       # No console window
        '--onedir',                         # Create a directory bundle
        '--noconfirm',                      # Overwrite output directory
        f'--add-data={add_data}',           # Include database files
        f'--paths={src_path}',              # Add src to python path
        # Exclude QML/Quick to avoid plugin issues on macOS (libqtuiotouchplugin.dylib)
        '--exclude-module=PySide6.QtQml',
        '--exclude-module=PySide6.QtQuick',
    ]
    
    # Add application icon
    # Expects 'app.icns' for macOS and 'app.ico' for Windows in 'src/resources/'
    if sys.platform == 'darwin':
        icon_path = os.path.join(src_path, 'resources', 'app.icns')
        if os.path.exists(icon_path):
            print(f"Using icon: {icon_path}")
            pyi_args.append(f'--icon={icon_path}')
        else:
            print("[WARNING] app.icns not found in src/resources/. No icon will be set for macOS.")
    elif sys.platform == 'win32':
        icon_path = os.path.join(src_path, 'resources', 'app.ico')
        if os.path.exists(icon_path):
            print(f"Using icon: {icon_path}")
            pyi_args.append(f'--icon={icon_path}')
        else:
            print("[WARNING] app.ico not found in src/resources/. No icon will be set for Windows.")

    # Target Universal2 on macOS to support both Intel and Apple Silicon
    if sys.platform == 'darwin':
        pyi_args.append('--target-arch=universal2')

    for hidden in hidden_imports:
        pyi_args.append(f'--hidden-import={hidden}')

    print("Running PyInstaller...")
    try:
        PyInstaller.__main__.run(pyi_args)
    except SystemExit as e:
        if e.code != 0:
            print(f"[ERROR] PyInstaller failed with exit code {e.code}")
            sys.exit(e.code)
    except Exception as e:
        print(f"[ERROR] PyInstaller failed: {e}")
        sys.exit(1)

    # Rename the app bundle to the final name with spaces
    dist_dir = os.path.join(project_root, 'dist')
    
    if sys.platform == 'darwin':
        built_name = f'{app_name_build}.app'
        final_name = f'{app_name_final}.app'
    else:
        built_name = app_name_build
        final_name = app_name_final

    built_path = os.path.join(dist_dir, built_name)
    final_path = os.path.join(dist_dir, final_name)

    if os.path.exists(built_path):
        if os.path.exists(final_path):
            shutil.rmtree(final_path)
        print(f"Renaming {built_name} to {final_name}...")
        os.rename(built_path, final_path)
        app_bundle = final_path
    else:
        app_bundle = final_path

    # Fix macOS code signing issues (resource forks/Finder info)
    if sys.platform == 'darwin':
        if os.path.exists(app_bundle):
            print("\n[INFO] Fixing macOS code signing...")
            try:
                # 1. Remove ._ files (AppleDouble) explicitly
                print("  - Removing ._ files...")
                subprocess.run(['find', app_bundle, '-name', '._*', '-delete'], check=True)
                
                # 2. Remove extended attributes (resource forks, Finder info)
                print("  - Removing extended attributes...")
                subprocess.run(['xattr', '-cr', app_bundle], check=True)
                
                # 3. Re-sign the bundle ad-hoc
                print("  - Re-signing bundle...")
                subprocess.run(['codesign', '--force', '--deep', '-s', '-', app_bundle], check=True)
                print("[SUCCESS] App bundle signed and cleaned.")
            except subprocess.CalledProcessError as e:
                print(f"[WARNING] Failed to sign app bundle: {e}")
            except Exception as e:
                print(f"[WARNING] An error occurred during signing fix: {e}")

    print(f"Build complete! Executable is in dist/Short Circuit/")

if __name__ == "__main__":
    sde_only = "--sde-only" in sys.argv
    build(sde_only)