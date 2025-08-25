## DWG to GLB converter (Windows)

This small Python CLI converts DWG files to GLB using two different workflows:

### New Workflow (Recommended): AutoCAD + Blender
- AutoCAD: DWG → FBX (via COM automation or command line)
- Blender: FBX → GLB (via Python scripting)

### Legacy Workflow: ODA + Assimp
- ODA/Teigha File Converter: DWG → DXF (batch-capable)
- Assimp (Open Asset Import Library): DXF → GLB (glTF 2.0)

### Requirements

#### For New Workflow (AutoCAD + Blender)
- Windows 10/11
- Python 3.9+ on PATH (`python --version`)
- AutoCAD installed (any recent version):
  - Typical executable: `C:\Program Files\Autodesk\AutoCAD 2024\acad.exe` (path may vary)
- Blender installed (free):
  - Download: `https://www.blender.org/download/`
  - Typical executable: `C:\Program Files\Blender Foundation\Blender 4.0\blender.exe` (path may vary)
- Optional: `pywin32` for COM automation (install with `pip install pywin32`)

#### For Legacy Workflow (ODA + Assimp)
- Windows 10/11
- Python 3.9+ on PATH (`python --version`)
- ODA File Converter installed (free registration):
  - Download: `https://www.opendesign.com/guestfiles/oda_file_converter`
  - Typical executable: `C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe` (path may vary)
- Assimp CLI installed:
  - Download binaries: `https://github.com/assimp/assimp/releases` or `https://kimkulling.itch.io/the-asset-importer-lib`
  - After install, ensure `assimp.exe` is on PATH or note its full path

### Quick start

1) Configure tool locations (optional if both are on PATH/known locations):

Create `dwg2glb.toml` next to the script, based on the example below.

```toml
# dwg2glb.toml
[tools]
# For new workflow (AutoCAD + Blender)
autocad = "C:\\Program Files\\Autodesk\\AutoCAD 2024\\acad.exe"
blender = "C:\\Program Files\\Blender Foundation\\Blender 4.0\\blender.exe"

# For legacy workflow (ODA + Assimp)
oda = "C:\\Program Files\\ODA\\ODAFileConverter\\ODAFileConverter.exe"
assimp = "C:\\Program Files\\Assimp\\bin\\assimp.exe"
```

2) Run conversions:

#### New Workflow (AutoCAD + Blender) - Default
```powershell
# Single file
python .\dwg_to_glb.py --input C:\path\to\file.dwg --output C:\out

# Entire folder (recursive)
python .\dwg_to_glb.py --input C:\path\to\dwgs --output C:\out --recursive

# Explicit paths (override config/auto-detect)
python .\dwg_to_glb.py --input C:\in --output C:\out \
  --autocad "C:\\Program Files\\Autodesk\\AutoCAD 2024\\acad.exe" \
  --blender "C:\\Program Files\\Blender Foundation\\Blender 4.0\\blender.exe"
```

#### Legacy Workflow (ODA + Assimp)
```powershell
# Single file
python .\dwg_to_glb.py --input C:\path\to\file.dwg --output C:\out --legacy

# Entire folder (recursive)
python .\dwg_to_glb.py --input C:\path\to\dwgs --output C:\out --recursive --legacy

# Explicit paths (override config/auto-detect)
python .\dwg_to_glb.py --input C:\in --output C:\out --legacy \
  --oda "C:\\Program Files\\ODA\\ODAFileConverter\\ODAFileConverter.exe" \
  --assimp "C:\\Program Files\\Assimp\\bin\\assimp.exe"
```

### How it works

#### New Workflow (AutoCAD + Blender)
- For each DWG, the tool uses AutoCAD (via COM automation or command line) to export to FBX format
- Then it uses Blender (via Python scripting) to import the FBX and export as GLB
- Output files mirror input structure when processing folders

#### Legacy Workflow (ODA + Assimp)
- For each DWG, the tool copies the file into a temporary folder and calls ODA File Converter to produce a DXF (ACAD2018).
- Then it invokes `assimp export input.dxf output.glb -f glb2` to create a glTF 2.0 binary.
- Output files mirror input structure when processing folders

### Notes and tips

#### New Workflow (AutoCAD + Blender)
- AutoCAD COM automation requires `pywin32` package. If not available, falls back to command line approach.
- FBX format preserves more geometry and material information than DXF, potentially resulting in better quality GLB files.
- Blender's GLB export includes materials, textures, and animations if present in the FBX.

#### Legacy Workflow (ODA + Assimp)
- ODA File Converter processes folders, not individual files. For single DWG conversion, this CLI stages the file into a temp folder and runs ODA on that folder.
- If your DWG uses features not preserved in DXF or not supported by Assimp, results may vary.
- If you see geometry issues, try a different DXF target version via `--dxf-version` (e.g., `ACAD2007`).

### Troubleshooting

#### New Workflow (AutoCAD + Blender)
- "AutoCAD not found":
  - Provide `--autocad` path or define `[tools].autocad` in `dwg2glb.toml`.
- "Blender not found":
  - Provide `--blender` path or define `[tools].blender` in `dwg2glb.toml`.
- "AutoCAD COM automation failed":
  - Install `pywin32`: `pip install pywin32`
  - The tool will automatically fall back to command line approach if COM fails.
- "FBX export failed":
  - Ensure AutoCAD has proper permissions to write to the output directory.
  - Check if the DWG file is valid and not corrupted.

#### Legacy Workflow (ODA + Assimp)
- "ODA File Converter not found":
  - Provide `--oda` path or define `[tools].oda` in `dwg2glb.toml`.
- "assimp not found":
  - Provide `--assimp` path or put `assimp.exe` on PATH and reopen PowerShell.
- "Assimp export failed":
  - Run `"<assimp>" info <your.dxf>` to verify the DXF can be parsed.
  - Try converting to `glTF` first: add `--glb false` to emit `.gltf`+bin+textures.

### Testing your setup

Run the test script to verify that all tools are properly configured:

```powershell
python test_setup.py
```

This will check if AutoCAD, Blender, and optional dependencies are available.

### Example config

See `dwg2glb.example.toml` and copy it to `dwg2glb.toml`.

---

Made by Shalek Chaye
