import os
import tarfile
import sys
import shutil

def create_tarball():
    # Determine platform-specific names
    if sys.platform == 'darwin':
        app_name = "Short Circuit.app"
        archive_name = "ShortCircuit-macOS.tar.gz"
    else:
        app_name = "Short Circuit"
        archive_name = "ShortCircuit-Linux.tar.gz"

    dist_dir = "dist"
    build_path = os.path.join(dist_dir, app_name)
    archive_path = os.path.join(dist_dir, archive_name)

    if not os.path.exists(build_path):
        print(f"[ERROR] {build_path} not found.")
        print("Please run 'python build.py' first.")
        sys.exit(1)

    if os.path.exists(archive_path):
        os.remove(archive_path)

    print(f"Creating {archive_name}...")
    
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(build_path, arcname=app_name)
        
    print(f"\n[SUCCESS] Archive created at: {archive_path}")

if __name__ == "__main__":
    create_tarball()