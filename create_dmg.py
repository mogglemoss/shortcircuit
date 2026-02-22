import os
import subprocess
import sys
import shutil

def create_dmg():
    app_name = "Short Circuit"
    dist_dir = "dist"
    app_path = os.path.join(dist_dir, f"{app_name}.app")
    dmg_name = f"{app_name}.dmg"
    dmg_path = os.path.join(dist_dir, dmg_name)

    # Verify the .app exists
    if not os.path.exists(app_path):
        print(f"[ERROR] {app_path} not found.")
        print("Please run 'python build.py' first.")
        sys.exit(1)

    # Remove existing DMG if it exists
    if os.path.exists(dmg_path):
        os.remove(dmg_path)

    print(f"Creating {dmg_name}...")

    # Create a temporary folder to layout the DMG contents
    src_folder = os.path.join(dist_dir, "dmg_source")
    if os.path.exists(src_folder):
        shutil.rmtree(src_folder)
    os.makedirs(src_folder)

    try:
        # 1. Copy the .app to the source folder
        print("  - Copying .app to staging area...")
        shutil.copytree(app_path, os.path.join(src_folder, f"{app_name}.app"))

        # 2. Create a symlink to /Applications for easy installation
        print("  - Creating /Applications link...")
        os.symlink("/Applications", os.path.join(src_folder, "Applications"))

        # 3. Create the DMG using hdiutil
        print("  - Running hdiutil...")
        cmd = ["hdiutil", "create", "-volname", app_name, "-srcfolder", src_folder, "-ov", "-format", "UDZO", dmg_path]
        subprocess.run(cmd, check=True)
        
        print(f"\n[SUCCESS] DMG created at: {dmg_path}")

    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Failed to create DMG: {e}")
    finally:
        # Cleanup temporary folder
        if os.path.exists(src_folder):
            shutil.rmtree(src_folder)

if __name__ == "__main__":
    create_dmg()