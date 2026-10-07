#!/usr/bin/env python3
"""
Download and integrate all available Acehnese-Indonesian data sources.
Run this on your Mac to gather FLORES-200, NusaX-Lexicon, and prepare for hikayat PDF.

Usage: python3 collect_data.py
"""

import os
import json
import zipfile
import shutil
from pathlib import Path

def download_flores200():
    """Download FLORES-200 dataset."""
    print("\n[1/3] Downloading FLORES-200 (3K sentences)...")
    
    import subprocess
    result = subprocess.run(
        ["curl", "-L", "https://tinyurl.com/flores200dataset", "-o", "/tmp/flores200.zip"],
        capture_output=True
    )
    
    if result.returncode == 0 and os.path.exists("/tmp/flores200.zip"):
        print("  ✓ Downloaded FLORES-200")
        return True
    else:
        print("  ⚠ Could not download (check internet connection)")
        return False

def prepare_hikayat():
    """Create directory for hikayat PDF."""
    os.makedirs("data/raw/hikayat", exist_ok=True)
    print("\n[3/3] Prepared data/raw/hikayat/ for PDF")

def main():
    print("="*70)
    print("ACEHNESE-INDONESIAN DATA COLLECTION")
    print("="*70)
    
    flores_ok = download_flores200()
    prepare_hikayat()
    
    print("\n" + "="*70)
    print("NEXT STEPS:")
    print("="*70)
    print("1. Run ./start.sh to start the web app")
    print("2. Upload Hikayat PDF via http://localhost:5000")
    print("3. Check DATA_SOURCES.md for all available data")
    print("="*70)

if __name__ == "__main__":
    main()
