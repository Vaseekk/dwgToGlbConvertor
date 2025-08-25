## DWG to GLB converter (Windows)

This small Python CLI converts DWG files to GLB by chaining two widely-used tools:

- ODA/Teigha File Converter: DWG → DXF (batch-capable)
- Assimp (Open Asset Import Library): DXF → GLB (glTF 2.0)

### Requirements

- Windows 10/11
- Python 3.9+ on PATH (`python --version`)
- ODA File Converter installed (free registration):
  - Download: `https://www.opendesign.com/guestfiles/oda_file_converter`
  - Typical executable: `C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe` (path may vary)
- Assimp CLI installed:
  - Download binaries: `https://github.com/assimp/assimp/releases`
  - After install, ensure `assimp.exe` is on PATH or note its full path

### Quick start

1) Configure tool locations (optional if both are on PATH/known locations):

Create `dwg2glb.toml` next to the script, based on the example below.

```toml
# dwg2glb.toml
[tools]
oda = "C:\\Program Files\\ODA\\ODAFileConverter\\ODAFileConverter.exe"
assimp = "C:\\Program Files\\Assimp\\bin\\assimp.exe"
```

2) Run conversions:

```powershell
# Single file
python .\dwg_to_glb.py --input C:\path\to\file.dwg --output C:\out

# Entire folder (recursive)
python .\dwg_to_glb.py --input C:\path\to\dwgs --output C:\out --recursive

# Explicit paths (override config/auto-detect)
python .\dwg_to_glb.py --input C:\in --output C:\out \
  --oda "C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe" \
  --assimp "C:\Program Files\Assimp\bin\assimp.exe"
```

### How it works

- For each DWG, the tool copies the file into a temporary folder and calls ODA File Converter to produce a DXF (ACAD2018).
- Then it invokes `assimp export input.dxf output.glb -f glb2` to create a glTF 2.0 binary.
- Output files mirror input structure when processing folders.

### Notes and tips

- ODA File Converter processes folders, not individual files. For single DWG conversion, this CLI stages the file into a temp folder and runs ODA on that folder.
- If your DWG uses features not preserved in DXF or not supported by Assimp, results may vary.
- If you see geometry issues, try a different DXF target version via `--dxf-version` (e.g., `ACAD2007`).

### Troubleshooting

- "ODA File Converter not found":
  - Provide `--oda` path or define `[tools].oda` in `dwg2glb.toml`.
- "assimp not found":
  - Provide `--assimp` path or put `assimp.exe` on PATH and reopen PowerShell.
- "Assimp export failed":
  - Run `"<assimp>" info <your.dxf>` to verify the DXF can be parsed.
  - Try converting to `glTF` first: add `--glb false` to emit `.gltf`+bin+textures.

### Example config

See `dwg2glb.example.toml` and copy it to `dwg2glb.toml`.

---

Made by Shalek Chaye
