#!/usr/bin/env python3
"""TW1 Object Exporter v1.0
Extracts all placed objects from .lnd files and exports per-tile CSVs.
CSV: MeshName, X, Y, Z, RotX, RotY, RotZ, Scale"""
import struct, os, sys, zlib, re, csv

# ============================================================
# LND PARSER — navigate to plaintext objects
# ============================================================
def _u32(data, pos):
    return struct.unpack_from("<I", data, pos)[0], pos + 4

def _skip_str(data, pos):
    sl, pos = _u32(data, pos)
    return pos + sl

def _skip_str2(data, pos):
    sl, pos = _u32(data, pos)
    return pos + sl * 2

def _decompress_lnd(raw):
    if raw[:4] == b"LN\x00\x00":
        return raw
    try:
        d1 = zlib.decompressobj()
        chunk1 = d1.decompress(raw)
        remaining = d1.unused_data
        if remaining and len(chunk1) <= 64:
            try:
                d2 = zlib.decompressobj()
                map_data = d2.decompress(remaining)
                if map_data[:4] == b"LN\x00\x00":
                    return map_data
            except: pass
        if chunk1[:4] == b"LN\x00\x00":
            return chunk1
    except zlib.error: pass
    try:
        d = zlib.decompress(raw)
        if d[:4] == b"LN\x00\x00":
            return d
    except: pass
    raise ValueError(f"Unknown LND format: {raw[:16].hex()}")

def extract_objects(filepath):
    """Parse .lnd and extract all plaintext objects.
    Returns list of dicts with MeshName, X, Y, Z, RotX, RotY, RotZ, Scale."""
    with open(filepath, "rb") as f:
        raw = f.read()
    data = _decompress_lnd(raw)
    
    pos = 4
    # Map name (utf16)
    pos = _skip_str2(data, pos)
    pos += 20  # w, h, unk_pair, underground
    # Adjacent maps (6x ascii string)
    for _ in range(6):
        pos = _skip_str(data, pos)
    # Markers
    cnt, pos = _u32(data, pos); pad, pos = _u32(data, pos)
    for _ in range(cnt):
        pos = _skip_str(data, pos)
        pos += 4 + 12 + 9  # instance + xyz + unk9
    # Skybox textures
    cnt, pos = _u32(data, pos); pad, pos = _u32(data, pos)
    for _ in range(cnt):
        pos = _skip_str(data, pos)
    # Sky states
    cnt, pos = _u32(data, pos); pad, pos = _u32(data, pos)
    pos += cnt * 168
    pos += 12  # day/sunrise/sunset
    # Heightmap
    w, pos = _u32(data, pos); h, pos = _u32(data, pos); pos += w * h * 2
    # Vert/Horiz edges
    cnt, pos = _u32(data, pos); pos += cnt * 2
    cnt, pos = _u32(data, pos); pos += cnt * 2
    # Water FarLOD
    w, pos = _u32(data, pos); h, pos = _u32(data, pos); pos += w * h * 2
    # Water Pools
    cnt, pos = _u32(data, pos); pad, pos = _u32(data, pos)
    for _ in range(cnt):
        pos += 4 + 4 + 4 + 2 + 4 + 4 + 88 + 4 + 4 + 8 + 4 + 4 + 16 + 4
        pos = _skip_str(data, pos)  # lava tex 1
        pos = _skip_str(data, pos)  # lava tex 2
        pos += 8  # bounds
    # Color Base
    w, pos = _u32(data, pos); h, pos = _u32(data, pos); pos += w * h * 4
    # Texture list
    cnt, pos = _u32(data, pos); pad, pos = _u32(data, pos)
    for _ in range(cnt):
        pos = _skip_str(data, pos)
    pos += 1  # unk byte
    # Tex Ref + Tex Alpha
    w, pos = _u32(data, pos); h, pos = _u32(data, pos); pos += w * h * 4
    w, pos = _u32(data, pos); h, pos = _u32(data, pos); pos += w * h * 4
    # 3D Objects (binary, pos=0,0,0 templates)
    cnt, pos = _u32(data, pos); pad, pos = _u32(data, pos)
    for _ in range(cnt):
        pos = _skip_str(data, pos)
        pos += 8 + 12 + 3  # unk8 + xyz + rot3
    # Fog Ref
    w, pos = _u32(data, pos); h, pos = _u32(data, pos); pos += w * h * 2
    # Fog Descriptions
    cnt, pos = _u32(data, pos); pad, pos = _u32(data, pos); pos += cnt * 12
    # Flower/Grass
    w, pos = _u32(data, pos); h, pos = _u32(data, pos); pos += w * h * 21
    # Stamp Map
    w, pos = _u32(data, pos); h, pos = _u32(data, pos); pos += w * h * 16
    # EAX
    w, pos = _u32(data, pos); h, pos = _u32(data, pos); pos += w * h
    # Passable
    w, pos = _u32(data, pos); h, pos = _u32(data, pos); pos += 4; pos += w * h * 4
    # Disabled
    w, pos = _u32(data, pos); h, pos = _u32(data, pos); pos += 4; pos += w * h * 4
    # Interiors
    w, pos = _u32(data, pos); h, pos = _u32(data, pos); pos += 4; pos += w * h * 4
    # Unk uint16 array
    cnt, pos = _u32(data, pos); pos += cnt * 2
    # Unk 2D uint32
    w, pos = _u32(data, pos); h, pos = _u32(data, pos); pos += w * h * 4
    
    # === PLAINTEXT OBJECTS ===
    cnt, pos = _u32(data, pos); pad, pos = _u32(data, pos)
    objects = []
    for _ in range(cnt):
        sl, pos = _u32(data, pos)
        txt = data[pos:pos+sl].decode("ascii", errors="replace"); pos += sl
        parts = txt.split()
        if len(parts) >= 12:
            # [0]Type [1]Mesh [2]Prob [3]Group [4]X [5]Y [6]Z [7]unk [8]RotY [9]RotX [10]RotZ [11]Scale
            try:
                objects.append({
                    "MeshName": parts[1],
                    "X": int(parts[4]),
                    "Y": int(parts[5]),
                    "Z": int(parts[6]),
                    "RotX": int(parts[9]),
                    "RotY": int(parts[8]),
                    "RotZ": int(parts[10]),
                    "Scale": int(parts[11]),
                })
            except (ValueError, IndexError):
                pass  # skip malformed entries
    return objects

def export_csv(objects, filepath):
    """Write objects to CSV."""
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["MeshName", "X", "Y", "Z", "RotX", "RotY", "RotZ", "Scale"])
        writer.writeheader()
        writer.writerows(objects)

# ============================================================
# CATEGORIZATION
# ============================================================
FOLIAGE_PREFIXES = (
    "EN_TREE_", "EN_BUSH_", "EN_BAMBOO_", "EN_PALM_",
    "EN_TRUNK_", "EN_DEAD_TREE_", "MUSHROOM_",
)

INTERACTIVE_PREFIXES = (
    "ING_", "CHEST_", "MINE_01_", "TELEPORT_", "TEL_",
    "ANKH_", "MO_", "BEAVER_", "FOX_", "BUTTERFLY_",
    "AMB_MARK_", "AMB_", "MANA_REG", "QITEM_", "POTION_",
    "DOOR_", "THE_TAINT", "ALTAR_", "MINE_ENTRANCE",
    "LIGHT_", "MARKER_", "FIRE", "Torch_",
    "CAVE_TORCH_", "CAVE_ENTRANCE_", "CAVE_EXIT_",
    "DUN_ENTRANCE_", "DUN_LVLUP_",
    "MO_HORSE_", "MO_SNAKE_", "MO_RABBIT_", "MO_DODO_",
    "MO_MUTARI_",
)

def categorize(mesh_name):
    """Return 'foliage', 'interactive', or 'static'."""
    for prefix in FOLIAGE_PREFIXES:
        if mesh_name.startswith(prefix):
            return "foliage"
    for prefix in INTERACTIVE_PREFIXES:
        if mesh_name.startswith(prefix):
            return "interactive"
    return "static"

def split_by_category(objects):
    """Split objects into 3 lists by category."""
    foliage = []; static = []; interactive = []
    for o in objects:
        cat = categorize(o["MeshName"])
        if cat == "foliage": foliage.append(o)
        elif cat == "interactive": interactive.append(o)
        else: static.append(o)
    return foliage, static, interactive

# ============================================================
# GUI
# ============================================================
import tkinter as tk
from tkinter import filedialog, messagebox

BG = "#1e1e2e"; BG2 = "#252536"; BG3 = "#2a2a3d"
FG = "#e0e0e0"; GREEN = "#50fa7b"; ORANGE = "#ffb86c"
RED = "#ff5555"; CYAN = "#8be9fd"; PURPLE = "#bd93f9"; YELLOW = "#f1fa8c"

class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("TW1 Object Exporter v1.0")
        self.root.geometry("800x600")
        self.root.configure(bg=BG)
        self.tiles = {}  # filename -> object list
        self._build_ui()
        self.root.mainloop()

    def _build_ui(self):
        tb = tk.Frame(self.root, bg=BG2, padx=8, pady=6); tb.pack(fill="x")
        tk.Label(tb, text="TW1 Object Exporter", font=("Segoe UI", 12, "bold"),
                 bg=BG2, fg=GREEN).pack(side="left")
        self.status_lbl = tk.Label(tb, text="Load a folder with .lnd files",
                                    font=("Segoe UI", 9), bg=BG2, fg=ORANGE)
        self.status_lbl.pack(side="left", padx=12)
        
        tk.Button(tb, text="Load Folder", bg=RED, fg="#fff",
                  font=("Segoe UI", 10, "bold"), bd=0, padx=12,
                  command=self._load_folder).pack(side="right", padx=4)
        tk.Button(tb, text="Export All CSVs", bg=GREEN, fg="#000",
                  font=("Segoe UI", 10, "bold"), bd=0, padx=12,
                  command=self._export_all).pack(side="right", padx=4)
        
        # Stats bar
        sb = tk.Frame(self.root, bg=BG3, padx=8, pady=4); sb.pack(fill="x")
        self.stats_lbl = tk.Label(sb, text="", font=("Consolas", 9), bg=BG3, fg=CYAN)
        self.stats_lbl.pack(side="left")
        
        # Listbox with tile info
        frame = tk.Frame(self.root, bg=BG)
        frame.pack(fill="both", expand=True, padx=8, pady=8)
        
        self.listbox = tk.Listbox(frame, bg=BG3, fg=FG, font=("Consolas", 10),
                                   selectbackground=PURPLE, selectforeground="#fff",
                                   borderwidth=0, highlightthickness=0)
        scrollbar = tk.Scrollbar(frame, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.listbox.pack(fill="both", expand=True)

    def _load_folder(self):
        folder = filedialog.askdirectory(title="Select folder with .lnd files")
        if not folder: return
        
        self.status_lbl.config(text="Loading..."); self.root.update()
        self.tiles = {}
        self.listbox.delete(0, "end")
        
        files = sorted([f for f in os.listdir(folder) if f.lower().endswith(".lnd")])
        total_objects = 0
        mesh_names = set()
        
        for fn in files:
            # Only surface map tiles
            base = os.path.splitext(fn)[0]
            if not re.match(r"Map_[A-I]\d{2}(_1)?$", base, re.IGNORECASE):
                continue
            try:
                objects = extract_objects(os.path.join(folder, fn))
                self.tiles[fn] = objects
                for o in objects:
                    mesh_names.add(o["MeshName"])
                total_objects += len(objects)
                
                # Categorize
                fol, sta, inter = split_by_category(objects)
                tag = " [UG]" if "_1." in fn else ""
                self.listbox.insert("end",
                    f"  {base:16s}{tag}  {len(objects):5d} total  "
                    f"F:{len(fol):4d}  S:{len(sta):4d}  I:{len(inter):4d}")
            except Exception as e:
                self.listbox.insert("end", f"  {base:16s}  SKIP: {str(e)[:50]}")
        
        self.status_lbl.config(text=f"{len(self.tiles)} tiles loaded from {os.path.basename(folder)}")
        # Count categories
        tf = ts = ti = 0
        for objs in self.tiles.values():
            f, s, i = split_by_category(objs)
            tf += len(f); ts += len(s); ti += len(i)
        self.stats_lbl.config(
            text=f"Total: {total_objects:,} objects | {len(mesh_names)} meshes | "
                 f"Foliage: {tf:,}  Static: {ts:,}  Interactive: {ti:,}")

    def _export_all(self):
        if not self.tiles:
            messagebox.showinfo("Export", "Load a folder first."); return
        
        folder = filedialog.askdirectory(title="Export CSVs to folder")
        if not folder: return
        
        self.status_lbl.config(text="Exporting..."); self.root.update()
        exported = 0
        counts = {"foliage": 0, "static": 0, "interactive": 0}
        
        for fn, objects in sorted(self.tiles.items()):
            if not objects: continue
            base = os.path.splitext(fn)[0]
            foliage, static, interactive = split_by_category(objects)
            
            for cat_name, cat_list in [("foliage", foliage), ("static", static), ("interactive", interactive)]:
                if not cat_list: continue
                csv_path = os.path.join(folder, f"{base}_{cat_name}.csv")
                export_csv(cat_list, csv_path)
                exported += 1
                counts[cat_name] += len(cat_list)
        
        self.status_lbl.config(
            text=f"Exported {exported} CSVs — "
                 f"F:{counts['foliage']:,}  S:{counts['static']:,}  I:{counts['interactive']:,}")

if __name__ == "__main__":
    App()
