import os
import sys
import shutil
import importlib.util
import subprocess

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

def build():
    # Import PyInstaller here to avoid crash if not installed (handled by check_dependencies)
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
    check_dependencies()

    # 1. Verify database exists
    if not os.path.exists(db_src):
        print(f"[ERROR] Database directory not found at {db_src}")
        print("Please ensure 'src/database' exists and contains the CSV files.")
        sys.exit(1)
        
    # 2. Verify database contains files
    if not os.listdir(db_src):
        print(f"[ERROR] Database directory is empty: {db_src}")
        sys.exit(1)

    # 3. Clean previous builds
    dist_dir = os.path.join(project_root, 'dist')
    build_dir = os.path.join(project_root, 'build')
    if os.path.exists(dist_dir):
        print("Cleaning dist directory...")
        try:
            shutil.rmtree(dist_dir, ignore_errors=True)
        except OSError as e:
            print(f"Warning: Could not fully clean dist directory: {e}")
    if os.path.exists(build_dir):
        print("Cleaning build directory...")
        try:
            shutil.rmtree(build_dir)
        except OSError as e:
            print(f"Warning: Could not fully clean build directory: {e}")

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
    ])

    # Generate Spec File content
    # We explicitly define the spec to ensure base_library.zip is handled correctly in COLLECT/BUNDLE
    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

a = Analysis(
    ['{os.path.join(src_path, "main.py")}'],
    pathex=['{project_root}'],
    binaries=[],
    datas=[('{db_src}', 'database')],
    hiddenimports={hidden_imports},
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=['PySide6.QtQml', 'PySide6.QtQuick'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='{app_name_build}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False, 
    upx=True,
    console=False,  # Windowed mode
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch='x86_64',
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='{app_name_build}',
)
"""
    
    spec_file = os.path.join(project_root, f"{app_name_build}.spec")
    with open(spec_file, "w") as f:
        f.write(spec_content)
    
    print(f"Generated spec file: {spec_file}")

    print("Running PyInstaller...")
    try:
        subprocess.run([sys.executable, '-m', 'PyInstaller', '--clean', '--noconfirm', spec_file], check=True)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] PyInstaller failed with exit code {e.returncode}")
        sys.exit(e.returncode)

    # Rename the app bundle to the final name with spaces
    dist_dir = os.path.join(project_root, 'dist')
    
    if sys.platform == 'darwin':
        built_name = f'{app_name_build}.app'
        final_name = f'{app_name_final}.app'
    else:
        built_name = app_name_build
        final_name = app_name_final

    # Manual macOS Bundling (since we removed BUNDLE from spec)
    if sys.platform == 'darwin':
        print("Creating macOS App Bundle manually...")
        collect_output = os.path.join(dist_dir, app_name_build)
        app_bundle_path = os.path.join(dist_dir, final_name)
        contents_path = os.path.join(app_bundle_path, "Contents")
        macos_path = os.path.join(contents_path, "MacOS")
        resources_path = os.path.join(contents_path, "Resources")
        frameworks_path = os.path.join(contents_path, "Frameworks")
        
        if os.path.exists(app_bundle_path):
            shutil.rmtree(app_bundle_path)
            
        os.makedirs(macos_path)
        os.makedirs(resources_path)
        
        # Move COLLECT output to MacOS folder
        for item in os.listdir(collect_output):
            s = os.path.join(collect_output, item)
            d = os.path.join(macos_path, item)
            if os.path.isdir(s):
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)
        
        # Fix for Python shared library location
        # PyInstaller bootloader in a bundle looks for Python in ../Frameworks/Python
        if not os.path.exists(frameworks_path):
            os.makedirs(frameworks_path)
            
        # Search for Python library in _internal (default PyInstaller 6)
        python_lib_src = None
        internal_dir = os.path.join(macos_path, "_internal")
        
        if os.path.exists(internal_dir):
            # Check for 'Python' or 'libpython*.dylib' inside _internal
            if os.path.exists(os.path.join(internal_dir, "Python")):
                python_lib_src = os.path.join(internal_dir, "Python")
            else:
                for f in os.listdir(internal_dir):
                    if f.startswith("libpython") and f.endswith(".dylib"):
                        python_lib_src = os.path.join(internal_dir, f)
                        break
        
        if not python_lib_src:
             # Fallback: check root of MacOS
             if os.path.exists(os.path.join(macos_path, "Python")):
                 python_lib_src = os.path.join(macos_path, "Python")
        
        if python_lib_src:
            print(f"  - Found Python library at: {python_lib_src}")
            
            # 1. Symlink Python library to Frameworks/Python (for bootloader)
            dest_link = os.path.join(frameworks_path, "Python")
            
            if os.path.exists(dest_link):
                os.remove(dest_link)
                
            # Calculate relative path: e.g. ../MacOS/_internal/Python
            link_target = os.path.relpath(python_lib_src, frameworks_path)
            print(f"  - Symlinking {link_target} to {dest_link}...")
            os.symlink(link_target, dest_link)

            # 2. Symlink _internal to Frameworks/_internal (for interpreter to find encodings)
            # If the DLL is loaded from Frameworks, it might look for _internal next to it
            if os.path.exists(internal_dir):
                dest_internal_link = os.path.join(frameworks_path, "_internal")
                if os.path.exists(dest_internal_link):
                    os.remove(dest_internal_link)
                
                rel_internal_path = os.path.relpath(internal_dir, frameworks_path)
                print(f"  - Symlinking {rel_internal_path} to {dest_internal_link}...")
                os.symlink(rel_internal_path, dest_internal_link)
        else:
            print("[WARNING] Could not find Python shared library to move to Frameworks!")
            # List contents to help debugging
            try:
                print(f"Contents of {macos_path}: {os.listdir(macos_path)}")
                if os.path.exists(internal_dir):
                    print(f"Contents of {internal_dir}: {os.listdir(internal_dir)}")
            except OSError:
                pass
        
        # Create Info.plist
        info_plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDisplayName</key>
    <string>{app_name_final}</string>
    <key>CFBundleExecutable</key>
    <string>{app_name_build}</string>
    <key>CFBundleIdentifier</key>
    <string>com.mogglemoss.shortcircuit</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>{app_name_final}</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.1.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
"""
        with open(os.path.join(contents_path, "Info.plist"), "w") as f:
            f.write(info_plist)
            
        # Clean up original COLLECT folder
        shutil.rmtree(collect_output)
        
        app_bundle = app_bundle_path
        print(f"App bundle created at: {app_bundle}")

    else:
        # Linux/Windows handling
        built_path = os.path.join(dist_dir, built_name)
        final_path = os.path.join(dist_dir, final_name)
        if os.path.exists(built_path):
            if os.path.exists(final_path):
                shutil.rmtree(final_path)
            os.rename(built_path, final_path)
        app_bundle = final_path

    # Fix macOS code signing issues (resource forks/Finder info)
    if sys.platform == 'darwin':
        if os.path.exists(app_bundle):
            print("\n[INFO] Fixing macOS code signing...")
            try:
                # 0. Unlock files to ensure we can modify them
                print("  - Unlocking files...")
                subprocess.run(['chflags', '-R', 'nouchg', app_bundle], check=False)

                # 0. Remove extended attributes first (clears resource forks on APFS)
                print("  - Removing extended attributes...")
                subprocess.run(['xattr', '-cr', app_bundle], check=True)

                # 1. Remove ._ files (AppleDouble) and .DS_Store recursively
                print("  - Removing ._ files...")
                subprocess.run(['find', app_bundle, '-name', '._*', '-delete'], check=True)
                print("  - Removing .DS_Store files...")
                subprocess.run(['find', app_bundle, '-name', '.DS_Store', '-delete'], check=True)

                # 2. Run dot_clean to merge AppleDouble files
                print("  - Running dot_clean...")
                subprocess.run(['dot_clean', '-m', app_bundle], check=False)

                # 2. Remove existing signatures
                print("  - Removing extended attributes...")
                subprocess.run(['xattr', '-cr', app_bundle], check=True)
                print("  - Removing existing signatures...")
                subprocess.run(['codesign', '--remove-signature', app_bundle], check=False)
                
                # 4. Re-sign the bundle ad-hoc
                print("  - Re-signing bundle...")
                subprocess.run(['codesign', '--force', '--deep', '-s', '-', app_bundle], check=True)
                print("[SUCCESS] App bundle signed and cleaned.")
            except subprocess.CalledProcessError as e:
                print(f"[WARNING] Failed to sign app bundle: {e}")
            except Exception as e:
                print(f"[WARNING] An error occurred during signing fix: {e}")

        # Touch the app to force Finder to refresh (fixes "can't see it" issue)
        print("  - Touching app bundle to refresh Finder...")
        subprocess.run(['touch', app_bundle], check=False)

    print(f"Build complete! Executable is in dist/Short Circuit/")

if __name__ == "__main__":
    build()