import os
import tarfile
import sys
import shutil

def create_tarball():
    app_name = "Short Circuit"
    dist_dir = "dist"
    build_path = os.path.join(dist_dir, app_name)
    archive_name = "ShortCircuit-Linux.tar.gz"
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