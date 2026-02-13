# Two Worlds 1 — LND Format Guide

Technical reference for the `.lnd` binary map format used in Two Worlds 1 and its SDK map editor (WhizzEdit).

## Overview

Each `.lnd` file contains one map tile. The game world consists of 108 surface tiles arranged in a 9×12 grid (columns A–I, rows 01–12), plus underground variants with a `_1` suffix. The complete world spans approximately 5×6 km.

## Compression

LND files are zlib-compressed. Two formats exist:

### Editor Format (WhizzEdit)
Dual zlib compression with a 24-byte header between layers:

```
[zlib stream 1] → 24-byte header (pre_head uint32 + extra_int 4 bytes + GUID 16 bytes)
[zlib stream 2] → LND map data (starts with "LN\x00\x00")
```

### SDK/Game Format
Single zlib stream decompressing directly to LND data:

```
[zlib stream] → LND map data (starts with "LN\x00\x00")
```

Both formats decompress to identical LND data starting with the magic bytes `LN\x00\x00` (hex: `4C 4E 00 00`).

## File Structure

All multi-byte values are little-endian. Strings are length-prefixed (uint32 count, then ASCII bytes). The map name uses UTF-16-LE (uint32 char count, then count×2 bytes).

### Section Order

```
1.  Header ("LN\x00\x00")
2.  Map Name (UTF-16-LE string)
3.  Dimensions (width, height, unknown pair, underground flag)
4.  Adjacent Maps (6 strings: upper, lower, left, right, down, up)
5.  Markers
6.  Skybox Textures
7.  Sky States
8.  Day/Sunrise/Sunset Times
9.  Heightmap
10. Vertical Edges
11. Horizontal Edges
12. Water FarLOD
13. Water Pools
14. Color Base
15. Texture List
16. Unknown Byte
17. Texture Reference Map
18. Texture Alpha Map
19. 3D Objects (binary templates)
20. Fog Reference Map
21. Fog Descriptions
22. Flower/Grass Map
23. Stamp Map
24. EAX Zone Map
25. Passable Terrain
26. Disabled Terrain
27. Interior Zones
28. Unknown uint16 Array
29. Unknown 2D uint32 Map
30. Plaintext Objects (placed instances)
```

## Section Details

### Header
```
Offset  Size  Description
0       4     Magic "LN\x00\x00"
```

### Map Name
```
4       4     Character count (uint32)
8       n×2   Map name (UTF-16-LE)
```

### Dimensions
```
+0      4     Width (uint32, typically 128)
+4      4     Height (uint32, typically 128)
+8      4     Unknown 1
+12     4     Unknown 2
+16     4     Underground flag (0=surface, 1=underground)
```

### Adjacent Maps
Six length-prefixed ASCII strings defining tile neighbors:
```
upper, lower, left, right, down, up
```
Empty string = map edge (no neighbor). Example: `Map_F02.lnd` for the tile above.

### Markers
```
+0      4     Count (uint32)
+4      4     Padding (uint32)
Per entry:
  +0    4+n   Name (length-prefixed ASCII)
  +n    4     Instance ID (uint32)
  +n+4  12    Position XYZ (3× float32)
  +n+16 9     Unknown bytes
```

### Skybox Textures
```
+0      4     Count
+4      4     Padding
Per entry:
  +0    4+n   Texture path (length-prefixed ASCII)
```

### Sky States
```
+0      4     Count
+4      4     Padding
Per entry:
  +0    168   Sky state data (fixed size)
```

### Day/Sunrise/Sunset
```
+0      4     Day time (float32)
+4      4     Sunrise time (float32)
+8      4     Sunset time (float32)
```

### Heightmap
```
+0      4     Width (uint32, typically 512)
+4      4     Height (uint32, typically 512)
+8      w×h×2 Height data (uint16 per pixel, stored bottom-to-top)
```
Values are absolute terrain elevation. Typical range: 512 (sea level) to 31,968 (mountain peaks). Adjacent tiles share edge values for seamless stitching.

**Important:** Data is stored bottom-to-top — row 0 in the file is the southern edge of the tile. Flip vertically for correct display.

### Vertical/Horizontal Edges
```
+0      4     Count (uint32)
+4      n×2   Edge data (uint16 per entry)
```
Two separate sections, one for vertical edges, one for horizontal.

### Water FarLOD
```
+0      4     Width (typically 128)
+4      4     Height (typically 128)
+8      w×h×2 Water level data (uint16, stored bottom-to-top)
```

### Water Pools
```
+0      4     Count
+4      4     Padding
Per pool:
  +0    4     Color (BGRA)
  +4    4     Depth (float32)
  +8    4     Unknown
  +12   2     Height (uint16)
  +14   4     Liquid Lightning
  +18   4     Is Lava (uint32)
  +22   88    Unknown block
  +110  4     Flow Direction (float32)
  +114  4     Flow Speed (float32)
  +118  8     Unknown
  +126  4     Reflect Min (float32)
  +130  4     Reflect Max (float32)
  +134  16    Unknown
  +150  4     Is Rain (uint32)
  +154  4+n   Lava Texture 1 (string)
  +...  4+n   Lava Texture 2 (string)
  +...  8     Bounds (4× uint16)
```

### Color Base
```
+0      4     Width (typically 512)
+4      4     Height (typically 512)
+8      w×h×4 Color data (BGRA, 4 bytes per pixel, stored bottom-to-top)
```
Multiplied over terrain textures in-game. White (255,255,255) = no change, gray = darkening (useful for ambient occlusion at building foundations), colored = tinting.

### Texture List
```
+0      4     Count
+4      4     Padding
Per entry:
  +0    4+n   Texture filename (string)
+end    1     Unknown byte
```

### Texture Reference / Alpha Maps
Two separate sections, same format:
```
+0      4     Width (typically 512)
+4      4     Height (typically 512)
+8      w×h×4 Data (uint32 per pixel)
```

### 3D Objects (Binary Templates)
```
+0      4     Count
+4      4     Padding
Per entry:
  +0    4+n   Object name (string)
  +n    8     Unknown
  +n+8  12    Position XYZ (3× float32) — always (0,0,0)
  +n+20 3     Rotation bytes
```
These are template definitions, not placed instances. Actual placements are in the Plaintext Objects section.

### Fog Reference Map
```
+0      4     Width (typically 128)
+4      4     Height
+8      w×h×2 Fog reference data (uint16)
```

### Fog Descriptions
```
+0      4     Count
+4      4     Padding
+8      n×12  Fog entries (12 bytes each)
```

### Flower/Grass
```
+0      4     Width (typically 128)
+4      4     Height (typically 128)
+8      w×h×21 Flower data (21 bytes per cell)
```

Per cell (21 bytes):
```
Byte 0      Unknown (always 0 in observed files)
Byte 1      Texture channel 1 ID (0–8)
Byte 2      Texture channel 2 ID (0–8)
Bytes 3-12  Unknown
Byte 13     Scatter X
Byte 14     Scatter Y
Byte 15     Density channel 1 (0–254)
Byte 16     Density channel 1 extra (0–63)
Byte 17     Density channel 2 (0–255)
Byte 18     Density channel 2 extra (0–255)
Byte 19     Density channel 3 (0–255)
Byte 20     Density channel 3 extra (0–63)
```
For visualization, bytes 15, 17, 19 work well as RGB density.

### Stamp Map
```
+0      4     Width
+4      4     Height
+8      w×h×16 Stamp data (16 bytes per cell)
```

### EAX Zone Map
```
+0      4     Width (typically 128)
+4      4     Height (typically 128)
+8      w×h   Zone IDs (uint8, values typically 29–40)
```
Each value references an EAX reverb preset. Different zones create distinct audio environments (caves, forests, buildings, open plains).

### Passable Terrain
```
+0      4     Width (typically 1024)
+4      4     Height (typically 32)
+8      4     Unknown uint32
+12     w×h×4 Bitfield data (uint32)
```
This is a bitfield — each uint32 contains 32 bits, creating a 1024×1024 bitmap per tile. Bit=1 means passable, bit=0 means blocked. Collision shapes of trees, rocks, buildings, and terrain edges appear as blocked areas.

### Disabled Terrain / Interior Zones
Same format as Passable (width, height, unknown, bitfield data).

### Unknown Arrays
```
uint16 array:  count (uint32) + count×2 bytes
2D uint32 map: width + height + w×h×4 bytes
```

### Plaintext Objects
```
+0      4     Count
+4      4     Padding
Per entry:
  +0    4+n   Text line (length-prefixed ASCII)
```

Each text line contains 14 space-separated fields:

```
Storeable EN_TREE_09 100 -1 1572 885 7866 0 153 0 0 100 2 0
```

| Index | Field | Description |
|-------|-------|-------------|
| 0 | Type | Always "Storeable" |
| 1 | MeshName | Object/mesh identifier |
| 2 | Probability | Spawn probability (typically 100) |
| 3 | Group | Spawn group (-1 = none) |
| 4 | X | World X position (integer) |
| 5 | Y | World Y position (integer) |
| 6 | Z | World Z position (integer) |
| 7 | Unknown | Always 0 |
| 8 | RotY | Yaw rotation (0–255 → 0°–360°) |
| 9 | RotX | Pitch rotation (0–255) |
| 10 | RotZ | Roll rotation (0–255) |
| 11 | Scale | Scale in percent (100 = 1.0×) |
| 12 | Unknown | Varies (0–3) |
| 13 | Unknown | Always 0 |

## World Grid

```
     A    B    C    D    E    F    G    H    I
01 [A01][B01][C01][D01][E01][F01][G01][H01][I01]  ← North
02 [A02][B02]...
..  ...
12 [A12][B12][C12][D12][E12][F12][G12][H12][I12]  ← South
 ↑                                             ↑
West                                         East
```

- A = western edge (A.left is empty)
- I = eastern edge
- 01 = northern edge
- 12 = southern edge
- Underground tiles: `Map_G03_1.lnd` (suffix `_1`)
- Tile dimensions: 128×128 world units, heightmap 512×512 pixels
- Total world: ~5 km × 6 km across 108 surface tiles

## Credits

Format documentation based on [BugLord's LND specification](http://www.buglord.net/) and reverse engineering of the Two Worlds SDK (WhizzEdit) map editor files.
