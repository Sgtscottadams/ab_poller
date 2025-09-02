#!/usr/bin/env python3
"""
Quick script to handle Windows executable creation from Mac
"""

import platform
import os
import sys

print("\n" + "="*60)
print(" PLC Toolkit - Windows Executable Builder")
print("="*60)

system = platform.system()

if system == "Darwin":  # macOS
    print("\n⚠️  You're on macOS - Cannot create Windows .exe here!")
    print("\n" + "="*60)
    print(" YOUR OPTIONS:")
    print("="*60)
    
    print("\n📦 OPTION 1: GitHub Actions (Recommended)")
    print("-" * 40)
    print("✓ Automated build in the cloud")
    print("✓ No Windows machine needed")
    print("\nSteps:")
    print("1. Push your code to GitHub")
    print("2. Go to 'Actions' tab in your repo")
    print("3. Run 'Build Windows Executable' workflow")
    print("4. Download the artifact\n")
    
    if os.path.exists(".github/workflows/build-windows.yml"):
        print("✅ GitHub workflow already set up!")
        print("   Just push to GitHub and check Actions tab")
    else:
        print("❌ Need to set up GitHub workflow")
        print("   Run: python make_exe_cross_platform.py")
    
    print("\n💻 OPTION 2: Ask a Windows Colleague")
    print("-" * 40)
    print("Send these 2 files to someone with Windows:")
    print("  • plc_toolkit_consolidated.py")
    print("  • BUILD_FOR_WINDOWS.bat")
    print("\nThey just double-click the .bat file")
    print("and send back the .exe\n")
    
    print("🖥️  OPTION 3: Windows VM (Parallels/VMware)")
    print("-" * 40)
    print("1. Install Windows in VM")
    print("2. Install Python in the VM")
    print("3. Run BUILD_FOR_WINDOWS.bat in VM\n")
    
    print("☁️  OPTION 4: Cloud Windows Machine")
    print("-" * 40)
    print("• AWS EC2 Windows instance")
    print("• Azure Windows VM")
    print("• Google Cloud Windows VM")
    print("(Usually free tier available)\n")
    
    print("="*60)
    print("\n📎 Files needed on Windows:")
    print("  1. plc_toolkit_consolidated.py (your code)")
    print("  2. BUILD_FOR_WINDOWS.bat (build script)")
    print("\n✨ That's it! The .bat file handles everything else.")
    
elif system == "Windows":
    print("\n✅ You're on Windows! Starting build...")
    print("\nRun this command:")
    print("  BUILD_FOR_WINDOWS.bat")
    print("\nOr:")
    print("  python make_exe.py")
    
else:
    print(f"\n⚠️  You're on {system}")
    print("You need Windows to create .exe files")

print("\n" + "="*60)
