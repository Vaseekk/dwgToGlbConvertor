import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Made by Shalek Chaye

try:
    import tomllib  # Python 3.11+
except Exception:  # pragma: no cover
    import tomli as tomllib  # type: ignore


def read_config(config_path: Path) -> dict:
    if not config_path.exists():
        return {}
    with config_path.open("rb") as f:
        return tomllib.load(f)


def which(exe: str) -> str | None:
    return shutil.which(exe)


def resolve_tool_path(cli_arg: str | None, cfg: dict, cfg_key: str, common_names: list[str]) -> str | None:
    if cli_arg:
        return cli_arg
    tools = cfg.get("tools", {}) if cfg else {}
    if tools.get(cfg_key):
        return tools[cfg_key]
    for name in common_names:
        path = which(name)
        if path:
            return path
    # Try common install locations on Windows
    common_paths = [
        r"C:\\Program Files\\ODA\\ODAFileConverter\\ODAFileConverter.exe",
        r"C:\\Program Files (x86)\\ODA\\ODAFileConverter\\ODAFileConverter.exe",
        r"C:\\Program Files\\Assimp\\bin\\assimp.exe",
        r"C:\\Program Files (x86)\\Assimp\\bin\\assimp.exe",
        r"C:\\Program Files\\Autodesk\\AutoCAD 2024\\acad.exe",
        r"C:\\Program Files\\Autodesk\\AutoCAD 2023\\acad.exe",
        r"C:\\Program Files\\Autodesk\\AutoCAD 2022\\acad.exe",
        r"C:\\Program Files\\Autodesk\\AutoCAD 2021\\acad.exe",
        r"C:\\Program Files\\Blender Foundation\\Blender 4.0\\blender.exe",
        r"C:\\Program Files\\Blender Foundation\\Blender 3.6\\blender.exe",
        r"C:\\Program Files\\Blender Foundation\\Blender 3.5\\blender.exe",
    ]
    for p in common_paths:
        if os.path.isfile(p):
            if cfg_key == "oda" and p.lower().endswith("odafileconverter.exe"):
                return p
            if cfg_key == "assimp" and os.path.basename(p).lower() == "assimp.exe":
                return p
            if cfg_key == "autocad" and os.path.basename(p).lower() == "acad.exe":
                return p
            if cfg_key == "blender" and os.path.basename(p).lower() == "blender.exe":
                return p
    return None


def run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if proc.returncode != 0:
        print(proc.stdout)
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")


def call_oda_folder(oda_exe: str, src_dir: Path, dst_dir: Path, dxf_version: str) -> None:
    # ODA File Converter CLI usage (from help dialog):
    # ODAFileConverter "inDir" "outDir" Output_version {"DWG","DXF","DXB"} Recurse Audit [filter]
    cmd = [
        oda_exe,
        str(src_dir),
        str(dst_dir),
        dxf_version,
        "DXF",
        "0",  # recurse: 0 no, 1 yes
        "0",  # audit: 0 off, 1 on
        "*.DWG",
    ]
    run(cmd)


def assimp_export(assimp_exe: str, dxf_file: Path, out_file: Path, glb: bool) -> None:
    fmt = "glb2" if glb else "gltf2"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    cmd = [assimp_exe, "export", str(dxf_file), str(out_file), "-f", fmt]
    run(cmd)


def autocad_to_fbx(autocad_exe: str, dwg_file: Path, fbx_file: Path) -> None:
    """Convert DWG to FBX using AutoCAD via COM automation"""
    try:
        import win32com.client
        import time
        
        # Create AutoCAD application object
        acad = win32com.client.Dispatch("AutoCAD.Application")
        acad.Visible = False
        
        # Open the DWG file
        doc = acad.Documents.Open(str(dwg_file.absolute()))
        
        # Export to FBX
        fbx_file.parent.mkdir(parents=True, exist_ok=True)
        doc.Export(str(fbx_file.absolute()), "FBX")
        
        # Close document and quit AutoCAD
        doc.Close(False)  # False = don't save changes
        acad.Quit()
        
    except ImportError:
        # Fallback to command line if win32com is not available
        print("Warning: win32com not available, trying command line approach...")
        autocad_to_fbx_cli(autocad_exe, dwg_file, fbx_file)


def autocad_to_fbx_cli(autocad_exe: str, dwg_file: Path, fbx_file: Path) -> None:
    """Convert DWG to FBX using AutoCAD command line"""
    # Create a script file for AutoCAD
    script_content = f"""
(command "._open" "{dwg_file.absolute()}")
(command "._export" "{fbx_file.absolute()}" "FBX")
(command "._close" "N")
(command "._quit")
"""
    
    script_file = fbx_file.parent / "autocad_script.scr"
    with open(script_file, "w") as f:
        f.write(script_content)
    
    # Run AutoCAD with script
    cmd = [autocad_exe, "/s", str(script_file)]
    run(cmd)
    
    # Clean up script file
    script_file.unlink(missing_ok=True)


def blender_to_glb(blender_exe: str, fbx_file: Path, glb_file: Path) -> None:
    """Convert FBX to GLB using Blender"""
    # Create a Python script for Blender
    script_content = f'''
import bpy
import os

# Clear existing scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# Import FBX
bpy.ops.import_scene.fbx(filepath="{fbx_file.absolute()}")

# Export as GLB
bpy.ops.export_scene.gltf(
    filepath="{glb_file.absolute()}",
    export_format='GLB',
    export_materials='EXPORT',
    export_normals=True,
    export_tangents=True,
    export_animations=True,
    export_skins=True
)
'''
    
    script_file = glb_file.parent / "blender_script.py"
    with open(script_file, "w") as f:
        f.write(script_content)
    
    # Run Blender with script
    cmd = [blender_exe, "--background", "--python", str(script_file)]
    run(cmd)
    
    # Clean up script file
    script_file.unlink(missing_ok=True)


def normalize_dxf_version(version: str) -> str:
    v = (version or "").upper().strip()
    if v.startswith("ACAD"):
        return v
    code_to_acad = {
        "AC1015": "ACAD2000",
        "AC1018": "ACAD2004",
        "AC1021": "ACAD2007",
        "AC1024": "ACAD2010",
        "AC1027": "ACAD2013",
        "AC1032": "ACAD2018",
    }
    return code_to_acad.get(v, "ACAD2018")


def convert_single_file_autocad_blender(autocad_exe: str, blender_exe: str, dwg_path: Path, out_dir: Path) -> Path:
    """Convert DWG to GLB using AutoCAD -> FBX -> Blender workflow"""
    if not dwg_path.exists():
        raise FileNotFoundError(dwg_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_dir = Path(tmpdir)
        
        # Step 1: Convert DWG to FBX using AutoCAD
        fbx_file = tmp_dir / (dwg_path.stem + ".fbx")
        print(f"Converting {dwg_path.name} to FBX...")
        autocad_to_fbx(autocad_exe, dwg_path, fbx_file)
        
        if not fbx_file.exists():
            raise RuntimeError(f"FBX file not created: {fbx_file}")
        
        # Step 2: Convert FBX to GLB using Blender
        glb_file = out_dir / (dwg_path.stem + ".glb")
        print(f"Converting {fbx_file.name} to GLB...")
        blender_to_glb(blender_exe, fbx_file, glb_file)
        
        if not glb_file.exists():
            raise RuntimeError(f"GLB file not created: {glb_file}")
        
        return glb_file


def convert_single_file(oda_exe: str, assimp_exe: str, dwg_path: Path, out_dir: Path, dxf_version: str, glb: bool) -> Path:
    """Legacy conversion using ODA -> DXF -> Assimp workflow"""
    if not dwg_path.exists():
        raise FileNotFoundError(dwg_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_src = Path(tmpdir) / "in"
        tmp_out = Path(tmpdir) / "out"
        tmp_src.mkdir(parents=True, exist_ok=True)
        tmp_out.mkdir(parents=True, exist_ok=True)
        staged = tmp_src / dwg_path.name
        shutil.copy2(dwg_path, staged)
        call_oda_folder(oda_exe, tmp_src, tmp_out, normalize_dxf_version(dxf_version))
        dxf_path = tmp_out / (dwg_path.stem + ".dxf")
        if not dxf_path.exists():
            # ODA may preserve subfolders; search for produced DXF
            candidates = list(tmp_out.rglob(dwg_path.stem + ".dxf"))
            if not candidates:
                raise RuntimeError("DXF not produced by ODA File Converter")
            dxf_path = candidates[0]
        out_ext = ".glb" if glb else ".gltf"
        out_file = out_dir / (dwg_path.stem + out_ext)
        assimp_export(assimp_exe, dxf_path, out_file, glb)
        return out_file


def iter_dwg_files(root: Path, recursive: bool) -> list[Path]:
    if root.is_file() and root.suffix.lower() == ".dwg":
        return [root]
    pattern = "**/*.dwg" if recursive else "*.dwg"
    return sorted(root.rglob("*.dwg") if recursive else root.glob("*.dwg"))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Convert DWG to GLB using AutoCAD and Blender")
    parser.add_argument("--input", required=True, help="Input DWG file or folder")
    parser.add_argument("--output", required=True, help="Output folder for GLB files")
    parser.add_argument("--recursive", action="store_true", help="Recurse into subfolders when input is a folder")
    parser.add_argument("--autocad", help="Path to AutoCAD executable")
    parser.add_argument("--blender", help="Path to Blender executable")
    parser.add_argument("--oda", help="Path to ODAFileConverter.exe (legacy mode)")
    parser.add_argument("--assimp", help="Path to assimp.exe (legacy mode)")
    parser.add_argument("--config", default="dwg2glb.toml", help="Path to config TOML")
    parser.add_argument("--legacy", action="store_true", help="Use legacy ODA+Assimp workflow")
    parser.add_argument("--dxf-version", default=None, help="DXF target version (e.g., ACAD2018) - legacy mode only")
    parser.add_argument("--glb", default=None, choices=["true", "false"], help="Emit GLB (true) or GLTF (false) - legacy mode only")
    args = parser.parse_args(argv)

    cfg = read_config(Path(args.config))

    if args.legacy:
        # Legacy workflow using ODA + Assimp
        oda = resolve_tool_path(args.oda, cfg, "oda", ["ODAFileConverter.exe", "ODAFileConverter"])
        assimp = resolve_tool_path(args.assimp, cfg, "assimp", ["assimp.exe", "assimp"])

        if not oda:
            print("ERROR: ODA File Converter not found. Provide --oda or configure in TOML.")
            return 2
        if not assimp:
            print("ERROR: assimp not found. Provide --assimp or put on PATH.")
            return 2

        defaults = (cfg or {}).get("defaults", {})
        dxf_version = args.dxf_version or defaults.get("dxf_version", "ACAD2018")
        glb = (
            (args.glb.lower() == "true") if args.glb is not None else bool(defaults.get("glb", True))
        )
    else:
        # New workflow using AutoCAD + Blender
        autocad = resolve_tool_path(args.autocad, cfg, "autocad", ["acad.exe", "AutoCAD"])
        blender = resolve_tool_path(args.blender, cfg, "blender", ["blender.exe", "blender"])

        if not autocad:
            print("ERROR: AutoCAD not found. Provide --autocad or configure in TOML.")
            return 2
        if not blender:
            print("ERROR: Blender not found. Provide --blender or put on PATH.")
            return 2

    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    files = iter_dwg_files(input_path, args.recursive)
    if not files:
        print("No DWG files found.")
        return 0

    errors: list[tuple[Path, str]] = []
    for dwg in files:
        # Maintain relative substructure under output when folder input
        rel_parent = Path(".")
        if input_path.is_dir():
            try:
                rel_parent = dwg.parent.relative_to(input_path)
            except ValueError:
                rel_parent = Path(".")
        target_dir = output_dir / rel_parent
        try:
            if args.legacy:
                out_file = convert_single_file(oda, assimp, dwg, target_dir, dxf_version, glb)
            else:
                out_file = convert_single_file_autocad_blender(autocad, blender, dwg, target_dir)
            print(f"OK: {dwg} -> {out_file}")
        except Exception as exc:  # noqa: BLE001
            errors.append((dwg, str(exc)))
            print(f"FAIL: {dwg}: {exc}")

    if errors:
        print(f"Completed with {len(errors)} failures.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))


