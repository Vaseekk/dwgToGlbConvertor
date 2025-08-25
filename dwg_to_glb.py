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
    ]
    for p in common_paths:
        if os.path.isfile(p):
            if cfg_key == "oda" and p.lower().endswith("odafileconverter.exe"):
                return p
            if cfg_key == "assimp" and os.path.basename(p).lower() == "assimp.exe":
                return p
    return None


def run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if proc.returncode != 0:
        print(proc.stdout)
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")


def call_oda_folder(oda_exe: str, src_dir: Path, dst_dir: Path, dxf_version: str) -> None:
    # ODA File Converter CLI usage (simplified):
    # ODAFileConverter <inDir> <outDir> <inVer> <outVer> <type> [options]
    # We use: inVer=ACAD2018 (auto), outVer=<dxf_version>, type=DXF
    cmd = [
        oda_exe,
        str(src_dir),
        str(dst_dir),
        "ACAD2018",
        dxf_version,
        "DXF",
        "0",  # recurse: 0 no, 1 yes (we handle recursion ourselves)
    ]
    run(cmd)


def assimp_export(assimp_exe: str, dxf_file: Path, out_file: Path, glb: bool) -> None:
    fmt = "glb2" if glb else "gltf2"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    cmd = [assimp_exe, "export", str(dxf_file), str(out_file), "-f", fmt]
    run(cmd)


def convert_single_file(oda_exe: str, assimp_exe: str, dwg_path: Path, out_dir: Path, dxf_version: str, glb: bool) -> Path:
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
        call_oda_folder(oda_exe, tmp_src, tmp_out, dxf_version)
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
    parser = argparse.ArgumentParser(description="Convert DWG to GLB using ODA and Assimp")
    parser.add_argument("--input", required=True, help="Input DWG file or folder")
    parser.add_argument("--output", required=True, help="Output folder for GLB/GLTF")
    parser.add_argument("--recursive", action="store_true", help="Recurse into subfolders when input is a folder")
    parser.add_argument("--oda", help="Path to ODAFileConverter.exe")
    parser.add_argument("--assimp", help="Path to assimp.exe")
    parser.add_argument("--config", default="dwg2glb.toml", help="Path to config TOML")
    parser.add_argument("--dxf-version", default=None, help="DXF target version (e.g., ACAD2018)")
    parser.add_argument("--glb", default=None, choices=["true", "false"], help="Emit GLB (true) or GLTF (false)")
    args = parser.parse_args(argv)

    cfg = read_config(Path(args.config))

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
            out_file = convert_single_file(oda, assimp, dwg, target_dir, dxf_version, glb)
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


