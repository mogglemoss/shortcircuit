import PyInstaller.__main__
import os
import sys
import shutil
import importlib.util
import subprocess
from PyInstaller.utils.hooks import collect_submodules

def check_dependencies():
    """Checks if required dependencies are installed."""
    required = [
        'PySide6', 'httpx', 'semver', 'dateutil', 'qdarktheme', 'appdirs', 'typing_extensions'
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
            'qdarktheme': 'pyqtdarktheme'
        }
        packages = [package_map.get(m, m) for m in missing]
        install_cmd = "python -m pip install " + " ".join(packages)
        print(f"\nPlease install them using:\n  {install_cmd}\n")
        sys.exit(1)

def build():
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
            shutil.rmtree(dist_dir)
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

    # Use subprocess to run PyInstaller to ensure a clean environment
    args = [
        sys.executable, '-m', 'PyInstaller',
        os.path.join(src_path, 'main.py'),
        f'--name={app_name_build}',         # Use name without spaces for build
        '--windowed',                       # No console window
        '--onedir',                         # Create a directory bundle
        '--clean',                          # Clean cache
        '--noconfirm',                      # Overwrite output directory
        f'--add-data={add_data}',           # Include database files
        f'--paths={src_path}',              # Add src to python path
    ]
    
    for hidden in hidden_imports:
        args.append(f'--hidden-import={hidden}')

    print("Running PyInstaller...")
    subprocess.run(args, check=True)

    # Rename the app bundle to the final name with spaces
    dist_dir = os.path.join(project_root, 'dist')
    built_app = os.path.join(dist_dir, f'{app_name_build}.app')
    final_app = os.path.join(dist_dir, f'{app_name_final}.app')

    if sys.platform == 'darwin' and os.path.exists(built_app):
        if os.path.exists(final_app):
            shutil.rmtree(final_app)
        print(f"Renaming {app_name_build}.app to {app_name_final}.app...")
        os.rename(built_app, final_app)
        app_bundle = final_app
    else:
        app_bundle = built_app

    # Fix macOS code signing issues (resource forks/Finder info)
    if sys.platform == 'darwin':
        if os.path.exists(app_bundle):
            print("\n[INFO] Fixing macOS code signing...")
            try:
                # 1. Merge/Clean AppleDouble (._) files which confuse codesign
                print("  - Running dot_clean...")
                subprocess.run(['dot_clean', '-m', app_bundle], check=True)
                
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
    build()