# TW1 Object Exporter

Extracts all placed objects from Two Worlds 1 map tiles (`.lnd`) and exports them as categorized CSV files — one set per tile.

## Features

- **3 CSVs per tile**, split by category:
  - `Map_G03_foliage.csv` — Trees, bushes, mushrooms, palms, trunks
  - `Map_G03_static.csv` — Stones, fences, buildings, furniture, camps, caves, dungeons
  - `Map_G03_interactive.csv` — Ingredients, chests, animals, teleporters, sound markers, quest items
- **Batch export** all tiles at once
- **GUI** shows per-tile object counts with Foliage/Static/Interactive breakdown
- Empty categories are skipped (no empty CSV files)

## Requirements

```
Python 3.8+
```

No additional packages needed (uses only standard library).

## Usage

```bash
python tw1_object_exporter.py
```

Or double-click `START_OBJECT_EXPORTER.bat`.

1. Click **Load Folder** and select the folder containing `.lnd` map tiles
2. Review the tile list — each row shows total objects and F/S/I counts
3. Click **Export All CSVs** and choose an output folder
4. Import CSVs into Unreal Engine via DataTable or custom Blueprint

## CSV Format

```csv
MeshName,X,Y,Z,RotX,RotY,RotZ,Scale
EN_TREE_09,1572,885,7866,0,153,0,100
EN_BUSH_06,2200,426,7460,0,127,0,100
CHEST_01_3,5412,1893,6200,0,64,0,100
```

| Column | Type | Description |
|--------|------|-------------|
| MeshName | string | Object/mesh name (e.g. `EN_TREE_09`, `CHEST_01_3`) |
| X, Y, Z | int | World position in TW1 units |
| RotX | int | Pitch (0–255 → 0°–360°) |
| RotY | int | Yaw / heading (0–255 → 0°–360°) |
| RotZ | int | Roll (0–255 → 0°–360°) |
| Scale | int | Scale in percent (100 = 1.0×) |

## Categories

### Foliage
Vegetation that can be spawned as Unreal Engine Foliage instances.

`EN_TREE_*`, `EN_BUSH_*`, `EN_BAMBOO_*`, `EN_PALM_*`, `EN_TRUNK_*`, `EN_DEAD_TREE_*`, `MUSHROOM_*`

### Static Meshes
Solid world objects for Instanced Static Mesh spawning.

Stones (`EN_STONE_*`), fences (`FENCE_*`), walls (`WALL_*`), towers (`TOWER_*`), caves (`Cave_*`), dungeons (`DUN_*`), huts (`HUT_*`), tents (`TENT_*`, `TIPI_*`, `WARTENT_*`, `ORCTENT_*`), furniture (`TABLE_*`, `CHAIR_*`, `BENCH_*`, `BED_*`), containers (`BARREL_*`, `CRATE_*`, `SACK_*`), decoration (`CAMPOBJ_*`, `WOODPIECES_*`, `GRAVE_*`, `MONUMENT_*`, `OBELISK_*`, `FLAG_*`, `SKELETON_*`, `BOAT_*`), and more.

### Interactive
Objects that need Blueprint logic for gameplay functionality.

Ingredients (`ING_*`), chests (`CHEST_*`), mining nodes (`MINE_*`), teleporters (`TELEPORT_*`, `TEL_*`), save points (`ANKH_*`), animals (`MO_*`, `BEAVER_*`, `FOX_*`, `BUTTERFLY_*`), ambient sounds (`AMB_MARK_*`, `AMB_*`), mana regeneration (`MANA_REG`), quest items (`QITEM_*`), potions (`POTION_*`), doors (`DOOR_*`), altars (`ALTAR_*`), fires (`FIRE*`, `Torch_*`), lights (`LIGHT_*`), and special objects (`THE_TAINT`).

## Unreal Engine Integration

### Foliage Spawner Blueprint
1. Import CSV as DataTable with matching struct
2. For each row: convert TW1 coordinates to UE world space
3. Add to Procedural Foliage Spawner or spawn via `AddInstance` on Foliage ISM Component

### Static Mesh Spawner Blueprint
1. Load CSV at runtime or editor time
2. Map MeshName to Static Mesh asset references
3. Spawn as Instanced Static Mesh Components for performance

### Interactive Object Spawner Blueprint
1. Load CSV and filter by MeshName prefix
2. Map to appropriate Blueprint class (e.g. `CHEST_*` → BP_Chest)
3. Spawn with full transform and configure gameplay properties

### Coordinate Conversion
TW1 uses integer coordinates. To convert to Unreal world space, you need to determine the correct scale factor based on the known world size (~5×6 km) and the coordinate ranges in the CSV data.

Rotation values 0–255 map to 0°–360° → multiply by 1.40625 (360/256) to get degrees.

Scale value 100 = 1.0× → divide by 100 for Unreal scale.
