# TW1 LND Tool

Full viewer and editor for individual Two Worlds 1 map tiles (`.lnd` format).

## Features

- **View** all 30+ sections: heightmap, color base, textures, objects, water pools, fog, flower/grass, EAX zones, passable terrain and more
- **Export** binary map layers as PNG — 12 types including heightmap (512×512 uint16), color base (BGRA), water, fog, passable, EAX, flower/grass
- **Edit** section data with built-in hex editor
- **Pack/Unpack** with byte-perfect roundtrip and automatic `.bak` backup
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
3. Click **Export Map** on any binary map section to save as PNG
4. Edit values in the hex view and click **Save** to write changes back
5. Use **Pack** to recompress the modified file

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
- Place the `.bat` file in the same folder as the `.py` file
