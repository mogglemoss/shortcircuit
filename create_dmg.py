import os
import subprocess
import sys

def create_dmg():
    if sys.platform != 'darwin':
        print("Error: DMG creation is only supported on macOS.")
        sys.exit(1)

    project_root = os.path.abspath(os.path.dirname(__file__))
    dist_dir = os.path.join(project_root, 'dist')
    app_name = "Short Circuit"
    app_bundle = os.path.join(dist_dir, f"{app_name}.app")
    dmg_output = os.path.join(dist_dir, f"{app_name}.dmg")

    if not os.path.exists(app_bundle):
        print(f"[ERROR] App bundle not found at: {app_bundle}")
        sys.exit(1)

    if os.path.exists(dmg_output):
        os.remove(dmg_output)

    print(f"Creating DMG: {dmg_output}")
    
    # Create DMG using hdiutil
    # -srcfolder: The .app bundle
    # -volname: The name of the mounted volume
    # -ov: Overwrite existing
    # -format UDZO: Compressed image
    cmd = [
        'hdiutil', 'create',
        '-volname', app_name,
        '-srcfolder', app_bundle,
        '-ov',
        '-format', 'UDZO',
        dmg_output
    ]

    try:
        subprocess.run(cmd, check=True)
        print(f"[SUCCESS] Created {dmg_output}")
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Failed to create DMG: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_dmg()