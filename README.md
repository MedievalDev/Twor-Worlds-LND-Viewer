# Twor-Worlds-LND-Viewer

# TW1 LND Toolkit

Python tools for reading, viewing, editing and exporting **Two Worlds 1** map files (`.lnd` format).

Built by reverse-engineering the binary LND format used in the Two Worlds SDK map editor (WhizzEdit).

![World Heightmap](https://img.shields.io/badge/Tiles-108_surface-brightgreen) ![Python](https://img.shields.io/badge/Python-3.8+-blue) ![License](https://img.shields.io/badge/License-MIT-yellow)

---

## Tools

### 🗺️ LND Tool (`tw1_lnd_tool.py`)
Full viewer and editor for individual `.lnd` map tiles.

- **View** all 30+ sections: heightmap, color base, textures, objects, water pools, fog, flower/grass, EAX zones, passable terrain and more
- **Export** binary map layers as PNG (heightmap, color base, water, fog, passable, EAX, flower/grass — 12 types total)
- **Edit** section data with hex editor
- **Pack/Unpack** with byte-perfect roundtrip and `.bak` backup
- Supports both editor format (dual zlib) and SDK/game format (single zlib)
- Dark theme UI with tree navigation

### 🌍 World Viewer (`tw1_world_viewer.py`)
Stitches all 108 surface tiles (9×12 grid, A01–I12) into a complete world map.

- **6 layers**: Heightmap, Color Base, Water FarLOD, Flower/Grass, EAX Zones, Passable
- **Zoom/pan** viewer with tile grid overlay and labels
- **Mouse hover** shows tile name, pixel coordinates and raw values
- **Toggle** surface / underground maps
- **Export World PNG** — single stitched image (e.g. 4608×6144px heightmap)
- **Export All Tiles** — individual PNGs with global normalization
- **Export RAW Tiles** — original uint16 values for Unreal Engine Landscape import
- Handles bottom-to-top storage, passable bitfield unpacking (1024×1024 per tile), and EAX normalization

### 📦 Object Exporter (`tw1_object_exporter.py`)
Extracts all placed objects from `.lnd` tiles into per-tile CSVs, split by category.

- **3 CSVs per tile**: `_foliage.csv`, `_static.csv`, `_interactive.csv`
- **Foliage**: Trees, bushes, mushrooms, palms, trunks — for UE Foliage Spawner
- **Static**: Stones, fences, buildings, furniture, camps, caves, dungeons — for Instanced Static Meshes
- **Interactive**: Ingredients, chests, animals, teleporters, sound markers, quest items — for Blueprint spawning
- CSV columns: `MeshName, X, Y, Z, RotX, RotY, RotZ, Scale`
- GUI shows per-tile object counts with F/S/I breakdown

---

## Requirements

```
Python 3.8+
Pillow (pip install Pillow)
NumPy (pip install numpy)
```

Tkinter is included with standard Python on Windows.

## Usage

Double-click the `.bat` files or run directly:

```bash
python tw1_lnd_tool.py
python tw1_world_viewer.py
python tw1_object_exporter.py
```

All tools auto-detect `.lnd` files in their directory. The World Viewer and Object Exporter accept a folder containing all map tiles extracted from the game's WD archive.

## LND Format

The `.lnd` binary format stores one map tile with ~30 sections:

| Section | Size per tile | Description |
|---------|--------------|-------------|
| Heightmap | 512×512 uint16 | Terrain elevation (bottom-to-top storage) |
| Color Base | 512×512 BGRA | Vertex color overlay for texture tinting/AO |
| Water FarLOD | 128×128 uint16 | Water level map |
| Texture Ref | 512×512 uint32 | Terrain texture assignments |
| Texture Alpha | 512×512 uint32 | Texture blend weights |
| Objects | variable | 3D object templates (binary) |
| Plaintext Objects | variable | Placed instances with world coordinates |
| Flower/Grass | 128×128 × 21 bytes | Vegetation density (3 channels) |
| EAX Zones | 128×128 uint8 | Reverb zone IDs |
| Passable | 1024×32 uint32 | Bitfield → 1024×1024 collision bitmap |
| Water Pools | variable | Pool geometry, flow, reflection settings |
| + 20 more sections | | Fog, markers, skybox, stamps, edges... |

Files use dual zlib compression (editor format) or single zlib (game/SDK format). The parser handles both transparently.

## Grid Layout

```
     A    B    C    D    E    F    G    H    I
01 [A01][B01][C01][D01][E01][F01][G01][H01][I01]  ← North
02 [A02][B02]...
..  ...
12 [A12][B12][C12][D12][E12][F12][G12][H12][I12]  ← South
 ↑                                             ↑
West                                         East
```

A01 = top-left (northwest), I12 = bottom-right (southeast). The complete world spans approximately 5×6 km across 108 surface tiles plus underground variants (`_1` suffix).

## Credits

Format documentation based on [BugLord's LND specification](http://www.buglord.net/) and extensive reverse engineering of the Two Worlds SDK (WhizzEdit) map editor files.
