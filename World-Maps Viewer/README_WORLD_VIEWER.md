# TW1 World Heightmap Viewer

Stitches all 108 surface tiles (9×12 grid, A01–I12) of Two Worlds 1 into a complete world map.

## Features

- **6 viewable layers**: Heightmap, Color Base, Water FarLOD, Flower/Grass, EAX Zones, Passable
- **Zoom/pan** with mouse wheel and drag
- **Tile grid overlay** with labels (toggle on/off)
- **Mouse hover** shows tile name, pixel coordinates and raw data values
- **Toggle** between surface and underground maps
- **Export World PNG** — single stitched image (e.g. 4608×6144px heightmap, 16-bit for heightmap/water)
- **Export All Tiles** — individual tile PNGs with global normalization across all tiles
- **Export RAW Tiles** — original uint16 values without normalization, for Unreal Engine Landscape import

## Requirements

```
Python 3.8+
Pillow          pip install Pillow
NumPy           pip install numpy
```

## Usage

```bash
python tw1_world_viewer.py
```

Or double-click `START_WORLD_VIEWER.bat`.

1. Click **Load Folder** and select the folder containing all `.lnd` map tiles
2. Select a layer with the radio buttons (Heightmap, Color Base, etc.)
3. Scroll to zoom, drag to pan
4. Hover over tiles to see coordinates and values in the top-right
5. Use the export buttons to save maps

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

A01 = top-left (northwest), I12 = bottom-right (southeast). Underground tiles have a `_1` suffix (e.g. `Map_G03_1.lnd`).

## Export Formats

| Button | Output | Use Case |
|--------|--------|----------|
| Export World PNG | Single stitched image, 16-bit for heightmap | Overview, documentation |
| Export All Tiles | Per-tile PNGs, globally normalized | Comparison, texture work |
| Export RAW Tiles | Per-tile 16-bit PNGs, original values | Unreal Engine Landscape import |

## Layer Details

| Layer | Tile Size | World Size | Description |
|-------|-----------|------------|-------------|
| Heightmap | 512×512 | 4608×6144 | Terrain elevation, uint16 |
| Color Base | 512×512 | 4608×6144 | Vertex color (BGRA → RGBA) |
| Water FarLOD | 128×128 | 1152×1536 | Water level, uint16 |
| Flower/Grass | 128×128 | 1152×1536 | Vegetation density (RGB) |
| EAX Zones | 128×128 | 1152×1536 | Reverb zones, normalized for display |
| Passable | 1024×1024 | 9216×12288 | Collision bitmap (bitfield unpacked) |

## Technical Notes

- LND files store data bottom-to-top — the viewer applies vertical flip automatically
- Passable terrain is stored as a bitfield (1024 rows × 32 uint32 = 1024×1024 bitmap per tile)
- EAX values are typically in range 29–40, normalized to 0–255 for visibility
- Flower/Grass uses bytes 15, 17, 19 of each 21-byte record as RGB density channels
- Heightmap display is 8-bit normalized, but exports preserve full 16-bit precision
