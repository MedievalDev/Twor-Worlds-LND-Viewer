# TW1 LND Map Editor

Full viewer and editor for individual Two Worlds 1 map tiles (`.lnd` format).

## Features

- **View** all 30+ sections: heightmap, color base, textures, objects, water pools, fog, flower/grass, EAX zones, passable terrain and more
- **Export** binary map layers as PNG — 12 types including heightmap (512×512 uint16), color base (BGRA), water, fog, passable, EAX, flower/grass
- **Import** PNG images to replace any map layer — swap heightmaps, color maps, texture maps, fog, EAX zones, passable terrain, etc.
- **Save** modified LND files with automatic `.bak` backup, or **Save As** to a new file
- **Pack/Unpack** with byte-perfect roundtrip
- Supports both editor format (dual zlib) and SDK/game format (single zlib)
- Dark theme UI with tree navigation

## Requirements

```
Python 3.8+
Pillow          pip install Pillow
NumPy           pip install numpy
```

## Usage

```bash
python tw1_lnd_tool.py
```

Or double-click `START_LND_TOOL.bat`.

1. Click **Load** and select a `.lnd` file (from the SDK or extracted from the game's WD archive)
2. Browse sections in the tree on the left
3. Select a **Binary Map** layer (e.g., Heightmap, Color Base)
4. Click **Export PNG** to save the current map as an image
5. Click **Import PNG** to replace the map data with a new image
6. Click **Save** to overwrite the original file or **Save As** to write to a new file

## Import Requirements

When importing a PNG to replace a map layer, the image dimensions must match exactly:

| Layer | Expected Size | Format |
|-------|--------------|--------|
| Heightmap | 512×512 | 16-bit grayscale (or 8-bit, auto-scaled) |
| Color Base | 512×512 | RGBA (auto-converted from any format) |
| Tex Reference | 512×512 | RGBA |
| Tex Alpha | 512×512 | RGBA |
| Water FarLOD | 128×128 | Grayscale (8-bit or 16-bit) |
| Fog Reference | 128×128 | Grayscale |
| EAX Zones | 128×128 | Grayscale (uint8 zone IDs) |
| Flower/Grass | 128×128 | RGB (updates density channels) |
| Stamp Map | varies | RGB (updates first 3 bytes per cell) |
| Passable | varies | Grayscale (>0 = passable) |
| Disabled | varies | Grayscale (>0 = disabled) |
| Interiors | varies | Grayscale (>0 = interior) |

## Supported Sections

| Section | Type | Description |
|---------|------|-------------|
| Heightmap | 512×512 uint16 | Terrain elevation |
| Color Base | 512×512 BGRA | Vertex color overlay (tinting, ambient occlusion) |
| Water FarLOD | 128×128 uint16 | Water level map |
| Texture Ref | 512×512 uint32 | Terrain texture assignments |
| Texture Alpha | 512×512 uint32 | Texture blend weights |
| Fog Ref | 128×128 uint16 | Fog zone references |
| Flower/Grass | 128×128 × 21 bytes | Vegetation density and types |
| EAX Zones | 128×128 uint8 | Audio reverb zone IDs |
| Passable | 1024×32 uint32 | Collision bitmap (bitfield) |
| Markers | variable | Named position markers |
| 3D Objects | variable | Object templates |
| Plaintext Objects | variable | Placed instances with world coordinates |
| Water Pools | variable | Pool geometry, flow, reflection |
| Skybox | variable | Sky textures and states |
| + more | | Stamps, edges, disabled zones, interiors |

## Notes

- Roundtrip verified: load → save produces byte-identical output
- The tool auto-detects compression format (editor dual-zlib vs SDK single-zlib)
- Saving creates a `.bak` backup of the original file automatically
- Place the `.bat` file in the same folder as the `.py` file
