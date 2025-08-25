#!/usr/bin/env python3
"""
Test script to verify AutoCAD and Blender setup for DWG to GLB conversion.
"""

import sys
from pathlib import Path

# Add the current directory to Python path to import dwg_to_glb
sys.path.insert(0, str(Path(__file__).parent))

from dwg_to_glb import resolve_tool_path, read_config


def test_tools():
    """Test if AutoCAD and Blender can be found."""
    print("Testing tool detection...")
    
    # Read config
    config_path = Path("dwg2glb.toml")
    if config_path.exists():
        cfg = read_config(config_path)
        print(f"✓ Config file found: {config_path}")
    else:
        cfg = {}
        print(f"⚠ Config file not found: {config_path}")
    
    # Test AutoCAD detection
    autocad = resolve_tool_path(None, cfg, "autocad", ["acad.exe", "AutoCAD"])
    if autocad:
        print(f"✓ AutoCAD found: {autocad}")
    else:
        print("✗ AutoCAD not found")
        print("  Install AutoCAD or add path to dwg2glb.toml")
    
    # Test Blender detection
    blender = resolve_tool_path(None, cfg, "blender", ["blender.exe", "blender"])
    if blender:
        print(f"✓ Blender found: {blender}")
    else:
        print("✗ Blender not found")
        print("  Install Blender or add path to dwg2glb.toml")
    
    # Test pywin32 availability
    try:
        import win32com.client
        print("✓ pywin32 available for COM automation")
    except ImportError:
        print("⚠ pywin32 not available - will use command line approach")
        print("  Install with: pip install pywin32")
    
    return autocad and blender


def test_legacy_tools():
    """Test if legacy tools (ODA + Assimp) can be found."""
    print("\nTesting legacy tool detection...")
    
    config_path = Path("dwg2glb.toml")
    if config_path.exists():
        cfg = read_config(config_path)
    else:
        cfg = {}
    
    # Test ODA detection
    oda = resolve_tool_path(None, cfg, "oda", ["ODAFileConverter.exe", "ODAFileConverter"])
    if oda:
        print(f"✓ ODA File Converter found: {oda}")
    else:
        print("✗ ODA File Converter not found")
    
    # Test Assimp detection
    assimp = resolve_tool_path(None, cfg, "assimp", ["assimp.exe", "assimp"])
    if assimp:
        print(f"✓ Assimp found: {assimp}")
    else:
        print("✗ Assimp not found")
    
    return oda and assimp


if __name__ == "__main__":
    print("DWG to GLB Converter - Setup Test")
    print("=" * 40)
    
    new_workflow_ok = test_tools()
    legacy_workflow_ok = test_legacy_tools()
    
    print("\n" + "=" * 40)
    if new_workflow_ok:
        print("✓ New workflow (AutoCAD + Blender) is ready!")
        print("  Run: python dwg_to_glb.py --input file.dwg --output out/")
    elif legacy_workflow_ok:
        print("✓ Legacy workflow (ODA + Assimp) is ready!")
        print("  Run: python dwg_to_glb.py --input file.dwg --output out/ --legacy")
    else:
        print("✗ No workflow is ready")
        print("  Please install required tools and configure dwg2glb.toml")
    
    print("\nFor help, see README.md")
