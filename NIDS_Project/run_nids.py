"""
# -*- coding: utf-8 -*-
=======================================================================
  FILE: run_nids.py  (Easy Startup Script)
  PROJECT: Network Intrusion Detection System (NIDS)
  STUDENT: Harsh Soam, Abhishek Arya
  TEACHER: Mr. Varun Chaudhary
=======================================================================

  WHAT IS THIS?
  -------------
  A helper startup script that:
  1. Checks if Flask is installed (and installs it if not)
  2. Starts the NIDS system
  3. Opens the browser automatically
  
  RUN THIS FILE TO START THE PROJECT:
  ------------------------------------
  python run_nids.py
=======================================================================
"""

import subprocess
import sys
import time
import webbrowser
import os

# Fix Windows console encoding so ASCII art displays correctly
try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass  # Python 3.6 doesn't have reconfigure


def check_and_install_dependencies():
    """
    Check if required packages are installed.
    If not, automatically install them using pip.
    
    WHY THIS APPROACH?
    Makes the project self-contained. Teacher/students don't need
    to manually install packages — the script does it automatically!
    
    WHAT IS pip?
    pip = "Pip Installs Packages" — Python's package manager.
    Like an app store for Python libraries.
    """
    print("=" * 60)
    print("  NETWORK INTRUSION DETECTION SYSTEM (NIDS)")
    print("  Students : Harsh Soam | Abhishek Arya")
    print("  Teacher  : Mr. Varun Chaudhary")
    print("=" * 60)
    print()
    
    required_packages = {
        "flask": "Flask",
    }
    
    missing_packages = []
    
    for import_name, package_name in required_packages.items():
        try:
            __import__(import_name)
            print(f"  [OK]  {package_name} - already installed")
        except ImportError:
            print(f"  [!!]  {package_name} - NOT installed")
            missing_packages.append(package_name)
    
    if missing_packages:
        print()
        print(f"  [INFO] Installing missing packages: {', '.join(missing_packages)}")
        print()
        
        for package in missing_packages:
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", package],
                    stdout=subprocess.DEVNULL,  # Suppress pip output (too verbose)
                    stderr=subprocess.DEVNULL
                )
                print(f"  [OK]  {package} installed successfully!")
            except subprocess.CalledProcessError:
                print(f"  [!!]  Failed to install {package}")
                print(f"        Please run manually: pip install {package}")
                sys.exit(1)
    
    print()
    print("  [INFO] All dependencies satisfied!")


def main():
    """Main entry point."""
    
    # Step 1: Check dependencies
    check_and_install_dependencies()
    
    # Step 2: Show startup info
    print()
    print("  [STARTING] Launching NIDS Engine...")
    print()
    print("  [+] Dashboard URL : http://localhost:5000")
    print("  [+] To stop       : Press Ctrl+C")
    print()
    
    # Step 3: Open browser after a short delay
    # (server needs a moment to start before browser can connect)
    def open_browser():
        time.sleep(2)  # Wait for Flask to start
        webbrowser.open("http://localhost:5000")
        print("  [INFO] Browser opened automatically at http://localhost:5000")
    
    import threading
    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()
    
    # Step 4: Import and run the Flask app
    # We import here (not at top) because packages might have just been installed
    try:
        from app import app, start_nids
        
        start_nids()
        
        app.run(
            host="0.0.0.0",
            port=5000,
            debug=False,
            use_reloader=False,
            threaded=True
        )
        
    except KeyboardInterrupt:
        print()
        print("  [INFO] NIDS stopped by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"  [ERROR] Failed to start NIDS: {e}")
        print(f"  [HELP]  Make sure you're running from the NIDS_Project folder!")
        sys.exit(1)


if __name__ == "__main__":
    main()
