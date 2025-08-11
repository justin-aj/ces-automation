import os
import sys
import subprocess
from pathlib import Path

def ensure_requirements():
    """Ensure all required packages are installed."""
    requirements_path = Path(__file__).parent / "dagster_dir" / "requirements.txt"
    
    if not requirements_path.exists():
        print(f"Requirements file not found at {requirements_path}")
        return False
    
    print("Installing required dependencies...")
    result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(requirements_path)])
    
    if result.returncode != 0:
        print("Failed to install required dependencies")
        return False
    
    return True

def start_dagster():
    """Start the Dagster UI."""
    # Set DAGSTER_HOME environment variable
    os.environ["DAGSTER_HOME"] = str(Path(__file__).parent)
    
    print("Starting Dagster UI...")
    print("Once started, you can access the UI at http://localhost:3001")
    print("Press Ctrl+C to stop the server")
    
    # Start the Dagster server
    subprocess.run([
        sys.executable, 
        "-m", 
        "dagster", 
        "dev", 
        "-f", 
        str(Path(__file__).parent / "dagster_dir" / "__init__.py"),
        "--port",
        "3001"
    ])

if __name__ == "__main__":
    print("====== Cold Email Automation - Dagster UI ======")
    start_dagster()
