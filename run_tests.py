import os
import sys
import subprocess

def main():
    # Ensure we are in the project root
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Add src to PYTHONPATH so the 'shortcircuit' package can be imported
    src_path = os.path.join(project_root, 'src')
    env = os.environ.copy()
    env['PYTHONPATH'] = src_path + os.pathsep + env.get('PYTHONPATH', '')
    
    # Check if pytest is installed
    try:
        import pytest
    except ImportError:
        print("pytest is not installed. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pytest"])

    # Arguments to pass to pytest
    # Default to running all model tests if no args provided
    args = sys.argv[1:]
    if not args:
        args = [os.path.join(src_path, 'shortcircuit', 'model')]
    
    cmd = [sys.executable, '-m', 'pytest', '-v'] + args
    
    print(f"Running: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, env=env, check=True)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)

if __name__ == "__main__":
    main()