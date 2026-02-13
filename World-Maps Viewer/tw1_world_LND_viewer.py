#!/usr/bin/env python3
"""TW1 World Heightmap Viewer v1.1
Loads all .lnd map tiles, stitches world maps, exports as PNG.
Supports: Heightmap, Color Base, Water, Flower/Grass, EAX, Passable.
v1.1: Fixed tile flip (bottom-to-top storage), passable bitfield, heightmap display."""
import struct, os, sys, zlib, re, tkinter as tk
from tkinter import ttk, filedialog, messagebox
from collections import OrderedDict
import numpy as np
from PIL import Image, ImageTk, ImageDraw

# ============================================================
# THEME
# ============================================================
BG = "#1e1e2e"; BG2 = "#252536"; BG3 = "#2a2a3d"; BG4 = "#32324a"
FG = "#e0e0e0"; FG_DIM = "#888899"; GREEN = "#50fa7b"; BLUE = "#6272a4"
ORANGE = "#ffb86c"; RED = "#ff5555"; CYAN = "#8be9fd"; PINK = "#ff79c6"
YELLOW = "#f1fa8c"; PURPLE = "#bd93f9"

# ============================================================
# LND PARSER
# ============================================================
def _dstr(data, pos):
    sl = struct.unpack_from("<I", data, pos)[0]; pos += 4
    return data[pos:pos+sl].decode("ascii", errors="replace"), pos + sl

def _dstr2(data, pos):
    sl = struct.unpack_from("<I", data, pos)[0]; pos += 4
    return data[pos:pos+sl*2].decode("utf-16-le", errors="replace"), pos + sl*2

def _u32(data, pos):
    return struct.unpack_from("<I", data, pos)[0], pos + 4

def _u16(data, pos):
    return struct.unpack_from("<H", data, pos)[0], pos + 2

def _decompress_lnd(raw):
    """Try multiple decompression strategies."""
    hdr_default = {"pre_head": 0, "extra_int": b"LN\x00\x00", "guid": b"\x00"*16, "is_editor": False}
    if raw[:4] == b"LN\x00\x00":
        return raw, hdr_default
    try:
        d1 = zlib.decompressobj()
        chunk1 = d1.decompress(raw)
        remaining = d1.unused_data
        if remaining and len(chunk1) <= 64:
            try:
                d2 = zlib.decompressobj()
                map_data = d2.decompress(remaining)
                if map_data[:4] == b"LN\x00\x00":
                    pre_head = struct.unpack_from("<I", chunk1, 0)[0] if len(chunk1) >= 4 else 0
                    extra_int = chunk1[4:8] if len(chunk1) >= 8 else b"LN\x00\x00"
                    guid = chunk1[8:24] if len(chunk1) >= 24 else b"\x00"*16
                    return map_data, {"pre_head": pre_head, "extra_int": extra_int,
                                       "guid": guid, "is_editor": True}
            except: pass
        if chunk1[:4] == b"LN\x00\x00":
            return chunk1, hdr_default
    except zlib.error: pass
    try:
        decompressed = zlib.decompress(raw)
        if decompressed[:4] == b"LN\x00\x00":
            return decompressed, hdr_default
    except: pass
    raise ValueError(f"Unknown LND format. First 16 bytes: {raw[:16].hex()}")

def _skip_markers(data, pos):
    cnt, pos = _u32(data, pos); pad, pos = _u32(data, pos)
    for _ in range(cnt):
        sl, pos = _u32(data, pos); pos += sl + 4 + 12 + 9
    return pos

def _skip_skybox(data, pos):
    cnt, pos = _u32(data, pos); pad, pos = _u32(data, pos)
    for _ in range(cnt):
        sl, pos = _u32(data, pos); pos += sl
    return pos

def _skip_skystates(data, pos):
    cnt, pos = _u32(data, pos); pad, pos = _u32(data, pos)
    pos += cnt * 168
    return pos

def _skip_water_pool(data, pos):
    """Skip one water pool entry."""
    pos += 4   # color BGRA
    pos += 4   # depth float
    pos += 4   # unk4
    pos += 2   # height uint16
    pos += 4   # liquid lightning
    pos += 4   # is lava
    pos += 88  # unk88
    pos += 4   # flow dir
    pos += 4   # flow speed
    pos += 8   # unk8
    pos += 4   # reflect min
    pos += 4   # reflect max
    pos += 16  # unk16
    pos += 4   # is rain
    sl, pos = _u32(data, pos); pos += sl  # lava tex 1
    sl, pos = _u32(data, pos); pos += sl  # lava tex 2
    pos += 8   # bounds (4x uint16)
    return pos

def _skip_objects(data, pos):
    cnt, pos = _u32(data, pos); pad, pos = _u32(data, pos)
    for _ in range(cnt):
        sl, pos = _u32(data, pos); pos += sl + 8 + 12 + 3
    return pos

def _skip_fogs(data, pos):
    cnt, pos = _u32(data, pos); pad, pos = _u32(data, pos)
    pos += cnt * 12
    return pos

def _skip_plaintext(data, pos):
    cnt, pos = _u32(data, pos); pad, pos = _u32(data, pos)
    for _ in range(cnt):
        sl, pos = _u32(data, pos); pos += sl
    return pos

def parse_lnd_maps(filepath):
    """Parse .lnd and extract all binary map data."""
    with open(filepath, "rb") as f:
        raw = f.read()
    data, _ = _decompress_lnd(raw)
    
    m = {}; pos = 4
    m["map_name"], pos = _dstr2(data, pos)
    m["width"], pos = _u32(data, pos)
    m["height"], pos = _u32(data, pos)
    pos += 8  # unk pair
    m["underground"], pos = _u32(data, pos)
    for k in ["upper", "lower", "left", "right", "down", "up"]:
        m[k], pos = _dstr(data, pos)
    
    pos = _skip_markers(data, pos)
    pos = _skip_skybox(data, pos)
    pos = _skip_skystates(data, pos)
    pos += 12  # day/sunrise/sunset
    
    # HEIGHTMAP
    w, pos = _u32(data, pos); h, pos = _u32(data, pos)
    m["heightmap"] = {"w": w, "h": h, "data": data[pos:pos+w*h*2]}; pos += w*h*2
    
    # Vert/Horiz Edge
    cnt, pos = _u32(data, pos); pos += cnt * 2
    cnt, pos = _u32(data, pos); pos += cnt * 2
    
    # WATER FARLOD
    w, pos = _u32(data, pos); h, pos = _u32(data, pos)
    m["water_farlod"] = {"w": w, "h": h, "data": data[pos:pos+w*h*2]}; pos += w*h*2
    
    # Water Pools
    cnt, pos = _u32(data, pos); pad, pos = _u32(data, pos)
    for _ in range(cnt):
        pos = _skip_water_pool(data, pos)
    
    # COLOR BASE
    w, pos = _u32(data, pos); h, pos = _u32(data, pos)
    m["color_base"] = {"w": w, "h": h, "data": data[pos:pos+w*h*4]}; pos += w*h*4
    
    # Textures & Stamps
    cnt, pos = _u32(data, pos); pad, pos = _u32(data, pos)
    for _ in range(cnt):
        sl, pos = _u32(data, pos); pos += sl
    pos += 1  # unk byte
    
    # Tex Ref/Alpha (skip)
    w, pos = _u32(data, pos); h, pos = _u32(data, pos); pos += w*h*4
    w, pos = _u32(data, pos); h, pos = _u32(data, pos); pos += w*h*4
    
    pos = _skip_objects(data, pos)
    
    # FOG REF
    w, pos = _u32(data, pos); h, pos = _u32(data, pos)
    m["fog_ref"] = {"w": w, "h": h, "data": data[pos:pos+w*h*2]}; pos += w*h*2
    
    pos = _skip_fogs(data, pos)
    
    # FLOWER/GRASS
    w, pos = _u32(data, pos); h, pos = _u32(data, pos)
    m["flower_grass"] = {"w": w, "h": h, "data": data[pos:pos+w*h*21]}; pos += w*h*21
    
    # Stamp (skip)
    w, pos = _u32(data, pos); h, pos = _u32(data, pos); pos += w*h*16
    
    # EAX
    w, pos = _u32(data, pos); h, pos = _u32(data, pos)
    m["eax_map"] = {"w": w, "h": h, "data": data[pos:pos+w*h]}; pos += w*h
    
    # PASSABLE
    w, pos = _u32(data, pos); h, pos = _u32(data, pos)
    w2, pos = _u32(data, pos)
    m["passable"] = {"w": w, "h": h, "data": data[pos:pos+w*h*4]}; pos += w*h*4
    
    return m

# ============================================================
# GRID — A=east edge, I=west edge, rows top-to-bottom
# Image: col 0(left)=I(west), col 8(right)=A(east)
# Data stored bottom-to-top → flipud needed
# ============================================================
def grid_from_name(filename):
    """Extract grid col,row from filename. Returns (col, row, is_underground) or None.
    Col 0=A(west/left) ... Col 8=I(east/right). Row 0=01(north/top) ... Row 11=12(south/bottom)."""
    base = os.path.splitext(os.path.basename(filename))[0]
    match = re.match(r"Map_([A-I])(\d{2})(_1)?$", base, re.IGNORECASE)
    if not match:
        return None
    col = ord(match.group(1).upper()) - ord('A')  # A=0(left) ... I=8(right)
    row = int(match.group(2)) - 1  # 01=0(top) ... 12=11(bottom)
    underground = match.group(3) is not None
    return col, row, underground

def col_to_letter(col):
    """Convert image column to letter. Col 0=A, Col 8=I."""
    return chr(ord('A') + col)

def load_all_tiles(folder):
    """Load all .lnd files from folder."""
    surface = {}; underground = {}
    files = [f for f in os.listdir(folder) if f.lower().endswith(".lnd")]
    total = len(files); loaded = 0; skipped = 0
    for fn in sorted(files):
        grid = grid_from_name(fn)
        if grid is None:
            continue
        col, row, is_ug = grid
        try:
            m = parse_lnd_maps(os.path.join(folder, fn))
            m["_filename"] = fn
            m["_col"] = col
            m["_row"] = row
            if is_ug:
                underground[(col, row)] = m
            else:
                surface[(col, row)] = m
            loaded += 1
        except Exception as e:
            skipped += 1
            print(f"  SKIP {fn}: {e}")
    print(f"Loaded {loaded}/{total} files ({skipped} skipped)")
    return surface, underground

# ============================================================
# STITCHING
# ============================================================
LAYERS = OrderedDict([
    ("heightmap",    {"label": "Heightmap"}),
    ("color_base",   {"label": "Color Base"}),
    ("water_farlod", {"label": "Water FarLOD"}),
    ("flower_grass", {"label": "Flower/Grass"}),
    ("eax_map",      {"label": "EAX Zones"}),
    ("passable",     {"label": "Passable"}),
])

def _tile_to_array(m, layer_key):
    """Convert a single tile's layer data to numpy array, with flipud.
    Returns (array, tw, th) or None."""
    ld = m.get(layer_key)
    if not ld or ld["w"] == 0 or not ld["data"]:
        return None
    tw, th = ld["w"], ld["h"]
    
    if layer_key == "color_base":
        arr = np.frombuffer(ld["data"], dtype=np.uint8).reshape(th, tw, 4)
        return np.flipud(arr).copy(), tw, th
    elif layer_key == "flower_grass":
        raw = np.frombuffer(ld["data"], dtype=np.uint8).reshape(th, tw, 21)
        # Bytes 15,17,19 = density channels (0-255), bytes 0-2 are just texture IDs (0-8)
        rgb = np.stack([raw[:,:,15], raw[:,:,17], raw[:,:,19]], axis=2)
        return np.flipud(rgb), tw, th
    elif layer_key == "passable":
        # Bitfield: w=1024 rows, h=32 uint32s per row → 1024×1024 bitmap
        raw32 = np.frombuffer(ld["data"], dtype=np.uint32).reshape(tw, th)
        bits = np.unpackbits(raw32.view(np.uint8).reshape(tw, th*4), axis=1,
                              bitorder='little')[:, :th*32]
        return np.flipud(bits), th * 32, tw  # actual pixel size
    elif layer_key in ("heightmap", "water_farlod"):
        arr = np.frombuffer(ld["data"], dtype=np.uint16).reshape(th, tw)
        return np.flipud(arr).copy(), tw, th
    elif layer_key == "eax_map":
        arr = np.frombuffer(ld["data"], dtype=np.uint8).reshape(th, tw)
        return np.flipud(arr).copy(), tw, th
    return None

def stitch_layer(tiles, layer_key, grid_cols=9, grid_rows=12):
    """Stitch a layer from all tiles into one array."""
    # Get tile pixel size from first available tile that has data
    tw = th = 0
    for sample in tiles.values():
        result = _tile_to_array(sample, layer_key)
        if result is not None:
            _, tw, th = result
            break
    if tw == 0 or th == 0:
        return None, None
    
    world_w = grid_cols * tw
    world_h = grid_rows * th
    
    # Determine array shape
    if layer_key == "color_base":
        world = np.zeros((world_h, world_w, 4), dtype=np.uint8)
    elif layer_key == "flower_grass":
        world = np.zeros((world_h, world_w, 3), dtype=np.uint8)
    elif layer_key in ("heightmap", "water_farlod"):
        world = np.zeros((world_h, world_w), dtype=np.uint16)
    else:
        world = np.zeros((world_h, world_w), dtype=np.uint8)
    
    placed = 0
    for (col, row), m in tiles.items():
        result = _tile_to_array(m, layer_key)
        if result is None:
            continue
        arr, atw, ath = result
        x = col * tw
        y = row * th
        # Handle passable which may have different actual pixel size
        if layer_key == "passable":
            # Resize passable to match tile grid
            x = col * tw
            y = row * th
            world[y:y+th, x:x+tw] = arr[:th, :tw] if arr.shape[0] >= th and arr.shape[1] >= tw else arr
        else:
            world[y:y+th, x:x+tw] = arr
        placed += 1
    
    return world, {"tw": tw, "th": th, "world_w": world_w, "world_h": world_h,
                    "placed": placed, "total": len(tiles)}

def world_to_image(world, layer_key):
    """Convert stitched world array to PIL Image for display."""
    if layer_key == "color_base":
        rgba = world[:, :, [2, 1, 0, 3]].copy()  # BGRA → RGBA
        return Image.fromarray(rgba, mode="RGBA")
    elif layer_key == "flower_grass":
        return Image.fromarray(world, mode="RGB")
    elif layer_key in ("heightmap", "water_farlod"):
        # Global normalize to 8-bit for DISPLAY (not export)
        mn, mx = world.min(), world.max()
        if mx > mn:
            norm = ((world.astype(np.float32) - mn) / (mx - mn) * 255).astype(np.uint8)
        else:
            norm = np.zeros_like(world, dtype=np.uint8)
        return Image.fromarray(norm, mode="L")
    elif layer_key == "passable":
        return Image.fromarray((world * 255).astype(np.uint8), mode="L")
    elif layer_key == "eax_map":
        # Normalize to full range for visibility (values typically 0-50)
        mn, mx = world.min(), world.max()
        if mx > mn:
            norm = ((world.astype(np.float32) - mn) / (mx - mn) * 255).astype(np.uint8)
        else:
            norm = world
        return Image.fromarray(norm, mode="L")
    else:
        return Image.fromarray(world, mode="L")

def world_to_image_16bit(world, layer_key):
    """Convert heightmap to 16-bit PNG for export (global normalized)."""
    mn, mx = world.min(), world.max()
    if mx > mn:
        norm = ((world.astype(np.float32) - mn) / (mx - mn) * 65535).astype(np.uint16)
    else:
        norm = world.copy()
    return Image.fromarray(norm)

# ============================================================
# TILE EXPORT
# ============================================================
def export_tile_pngs(tiles, layer_key, out_dir, global_norm=True):
    """Export individual tiles as PNGs with global normalization."""
    os.makedirs(out_dir, exist_ok=True)
    
    if global_norm and layer_key in ("heightmap", "water_farlod"):
        gmin, gmax = 65535, 0
        for m in tiles.values():
            result = _tile_to_array(m, layer_key)
            if result is None: continue
            arr = result[0]
            gmin = min(gmin, int(arr.min()))
            gmax = max(gmax, int(arr.max()))
    
    exported = []
    for (col, row), m in sorted(tiles.items()):
        result = _tile_to_array(m, layer_key)
        if result is None: continue
        arr, tw, th = result
        
        letter = col_to_letter(col)
        num = f"{row+1:02d}"
        fname = f"Map_{letter}{num}_{LAYERS[layer_key]['label'].replace('/', '_')}.png"
        fpath = os.path.join(out_dir, fname)
        
        if layer_key == "color_base":
            rgba = arr[:, :, [2, 1, 0, 3]]
            img = Image.fromarray(rgba, mode="RGBA")
        elif layer_key == "flower_grass":
            img = Image.fromarray(arr, mode="RGB")
        elif layer_key in ("heightmap", "water_farlod"):
            if global_norm and gmax > gmin:
                norm = ((arr.astype(np.float32) - gmin) / (gmax - gmin) * 65535).astype(np.uint16)
            else:
                norm = arr
            img = Image.fromarray(norm)
        elif layer_key == "passable":
            img = Image.fromarray((arr * 255).astype(np.uint8), mode="L")
        else:
            img = Image.fromarray(arr, mode="L")
        
        img.save(fpath)
        exported.append(fpath)
    return exported

def export_tile_raw(tiles, layer_key, out_dir):
    """Export tiles as raw 16-bit PNGs without normalization."""
    os.makedirs(out_dir, exist_ok=True)
    exported = []
    for (col, row), m in sorted(tiles.items()):
        result = _tile_to_array(m, layer_key)
        if result is None: continue
        arr, tw, th = result
        
        letter = col_to_letter(col)
        num = f"{row+1:02d}"
        fname = f"Map_{letter}{num}_{LAYERS[layer_key]['label']}_RAW.png"
        fpath = os.path.join(out_dir, fname)
        img = Image.fromarray(arr)
        img.save(fpath)
        exported.append(fpath)
    return exported

# ============================================================
# APP
# ============================================================
class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("TW1 World Heightmap Viewer v1.1")
        self.root.geometry("1400x900")
        self.root.configure(bg=BG)
        self.root.minsize(1000, 700)
        self.surface = {}; self.underground = {}
        self.current_tiles = {}
        self.show_underground = False
        self.current_layer = "heightmap"
        self.world_img = None; self.tk_img = None
        self.zoom = 1.0; self.pan_x = 0; self.pan_y = 0
        self._drag_start = None; self.show_grid = True
        self.stitch_info = None; self._world_raw = None
        self._grid_offset_col = 0; self._grid_offset_row = 0
        self._grid_cols = 9; self._grid_rows = 12
        self._build_ui()
        # Auto-load from same directory
        self._try_autoload()
        self.root.mainloop()

    def _build_ui(self):
        tb = tk.Frame(self.root, bg=BG2, padx=8, pady=6); tb.pack(fill="x")
        tk.Label(tb, text="TW1 World Viewer", font=("Segoe UI", 12, "bold"),
                 bg=BG2, fg=GREEN).pack(side="left")
        self.status_lbl = tk.Label(tb, text="Load a folder with .lnd files",
                                    font=("Segoe UI", 9), bg=BG2, fg=ORANGE)
        self.status_lbl.pack(side="left", padx=12)
        
        tk.Button(tb, text="Load Folder", bg=RED, fg="#fff",
                  font=("Segoe UI", 10, "bold"), bd=0, padx=12,
                  command=self._load_folder).pack(side="right", padx=4)
        tk.Button(tb, text="Export World PNG", bg=GREEN, fg="#000",
                  font=("Segoe UI", 10, "bold"), bd=0, padx=10,
                  command=self._export_world).pack(side="right", padx=4)
        tk.Button(tb, text="Export All Tiles", bg=PURPLE, fg="#fff",
                  font=("Segoe UI", 10, "bold"), bd=0, padx=10,
                  command=self._export_tiles).pack(side="right", padx=4)
        tk.Button(tb, text="Export RAW Tiles", bg=CYAN, fg="#000",
                  font=("Segoe UI", 10, "bold"), bd=0, padx=10,
                  command=self._export_raw).pack(side="right", padx=4)
        
        cb = tk.Frame(self.root, bg=BG3, padx=8, pady=4); cb.pack(fill="x")
        tk.Label(cb, text="Layer:", font=("Segoe UI", 10), bg=BG3, fg=FG).pack(side="left")
        self.layer_var = tk.StringVar(value="heightmap")
        for label, key in [("Heightmap", "heightmap"), ("Color Base", "color_base"),
                           ("Water FarLOD", "water_farlod"), ("Flower/Grass", "flower_grass"),
                           ("EAX Zones", "eax_map"), ("Passable", "passable")]:
            tk.Radiobutton(cb, text=label, variable=self.layer_var, value=key,
                           bg=BG3, fg=FG, selectcolor=BG4, activebackground=BG3,
                           activeforeground=GREEN, font=("Segoe UI", 9),
                           command=self._on_layer_change).pack(side="left", padx=4)
        
        tk.Frame(cb, bg=FG_DIM, width=2, height=20).pack(side="left", padx=8, fill="y")
        self.ug_var = tk.BooleanVar(value=False)
        tk.Checkbutton(cb, text="Underground", variable=self.ug_var,
                        bg=BG3, fg=FG, selectcolor=BG4, activebackground=BG3,
                        activeforeground=RED, font=("Segoe UI", 9),
                        command=self._on_ug_toggle).pack(side="left", padx=4)
        self.grid_var = tk.BooleanVar(value=True)
        tk.Checkbutton(cb, text="Grid", variable=self.grid_var,
                        bg=BG3, fg=FG, selectcolor=BG4, activebackground=BG3,
                        activeforeground=YELLOW, font=("Segoe UI", 9),
                        command=self._on_grid_toggle).pack(side="left", padx=4)
        
        self.zoom_lbl = tk.Label(cb, text="Zoom: 100%", font=("Segoe UI", 9), bg=BG3, fg=FG_DIM)
        self.zoom_lbl.pack(side="right", padx=8)
        self.coord_lbl = tk.Label(cb, text="", font=("Consolas", 9), bg=BG3, fg=CYAN)
        self.coord_lbl.pack(side="right", padx=8)
        
        self.canvas = tk.Canvas(self.root, bg="#000000", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<MouseWheel>", self._on_scroll)
        self.canvas.bind("<Button-4>", lambda e: self._do_zoom(1.15, e.x, e.y))
        self.canvas.bind("<Button-5>", lambda e: self._do_zoom(1/1.15, e.x, e.y))
        self.canvas.bind("<ButtonPress-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<Motion>", self._on_mouse_move)
        self.canvas.bind("<Configure>", self._on_resize)

    def _try_autoload(self):
        """Try to auto-load .lnd files from script directory."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        lnd_files = [f for f in os.listdir(script_dir) if f.lower().endswith(".lnd")]
        if len(lnd_files) >= 2:
            self._do_load(script_dir)

    def _load_folder(self):
        folder = filedialog.askdirectory(title="Select folder with .lnd files")
        if folder:
            self._do_load(folder)

    def _do_load(self, folder):
        self.status_lbl.config(text="Loading..."); self.root.update()
        self.surface, self.underground = load_all_tiles(folder)
        self.current_tiles = self.surface
        self.show_underground = False; self.ug_var.set(False)
        
        if not self.surface:
            messagebox.showwarning("No tiles", "No valid Map_[A-I][01-12].lnd files found.")
            return
        
        cols = [c for c, r in self.surface.keys()]
        rows = [r for c, r in self.surface.keys()]
        info = (f"{len(self.surface)} surface tiles "
                f"({col_to_letter(max(cols))}{min(rows)+1:02d} — "
                f"{col_to_letter(min(cols))}{max(rows)+1:02d})")
        if self.underground:
            info += f" + {len(self.underground)} underground"
        self.status_lbl.config(text=info)
        self._rebuild_world()

    def _on_layer_change(self):
        self.current_layer = self.layer_var.get(); self._rebuild_world()

    def _on_ug_toggle(self):
        self.show_underground = self.ug_var.get()
        self.current_tiles = self.underground if self.show_underground else self.surface
        self._rebuild_world()

    def _on_grid_toggle(self):
        self.show_grid = self.grid_var.get(); self._render()

    def _rebuild_world(self):
        if not self.current_tiles: return
        self.status_lbl.config(text="Stitching..."); self.root.update()
        
        cols = [c for c, r in self.current_tiles.keys()]
        rows = [r for c, r in self.current_tiles.keys()]
        min_col, max_col = min(cols), max(cols)
        min_row, max_row = min(rows), max(rows)
        gc = max_col - min_col + 1; gr = max_row - min_row + 1
        
        offset_tiles = {(c - min_col, r - min_row): m for (c, r), m in self.current_tiles.items()}
        self._grid_offset_col = min_col; self._grid_offset_row = min_row
        self._grid_cols = gc; self._grid_rows = gr
        self._offset_tiles = offset_tiles
        
        world, info = stitch_layer(offset_tiles, self.current_layer, gc, gr)
        if world is None:
            self.status_lbl.config(text="Layer empty"); return
        
        self.stitch_info = info
        self._world_raw = world
        self.world_img = world_to_image(world, self.current_layer)
        self._fit_zoom(); self._render()
        
        layer_label = LAYERS[self.current_layer]["label"]
        ug_str = " [UNDERGROUND]" if self.show_underground else ""
        self.status_lbl.config(
            text=f"{layer_label}{ug_str}: {info['world_w']}×{info['world_h']}px "
                 f"({info['placed']}/{info['total']} tiles) | Tile: {info['tw']}×{info['th']}")

    def _fit_zoom(self):
        if not self.world_img: return
        cw = self.canvas.winfo_width() or 800; ch = self.canvas.winfo_height() or 600
        iw, ih = self.world_img.size
        self.zoom = min(cw / iw, ch / ih) * 0.95
        self.pan_x = (cw - iw * self.zoom) / 2
        self.pan_y = (ch - ih * self.zoom) / 2
        self.zoom_lbl.config(text=f"Zoom: {self.zoom*100:.0f}%")

    def _render(self):
        if not self.world_img: return
        self.canvas.delete("all")
        iw, ih = self.world_img.size
        dw = max(1, int(iw * self.zoom)); dh = max(1, int(ih * self.zoom))
        resample = Image.NEAREST if self.zoom > 2 else Image.BILINEAR
        display = self.world_img.convert("RGBA").resize((dw, dh), resample)
        
        if self.show_grid and self.stitch_info and self.zoom > 0.05:
            draw = ImageDraw.Draw(display)
            tw, th = self.stitch_info["tw"], self.stitch_info["th"]
            ztw, zth = tw * self.zoom, th * self.zoom
            
            for c in range(self._grid_cols + 1):
                x = int(c * ztw)
                draw.line([(x, 0), (x, dh)], fill=(255, 255, 100, 80), width=1)
            for r in range(self._grid_rows + 1):
                y = int(r * zth)
                draw.line([(0, y), (dw, y)], fill=(255, 255, 100, 80), width=1)
            
            if self.zoom > 0.08:
                for c in range(self._grid_cols):
                    for r in range(self._grid_rows):
                        if (c, r) not in self._offset_tiles: continue
                        real_col = c + self._grid_offset_col
                        real_row = r + self._grid_offset_row
                        letter = col_to_letter(real_col)
                        num = f"{real_row+1:02d}"
                        lx = int(c * ztw + 4); ly = int(r * zth + 2)
                        draw.text((lx+1, ly+1), f"{letter}{num}", fill=(0, 0, 0, 180))
                        draw.text((lx, ly), f"{letter}{num}", fill=(255, 255, 100, 200))
        
        self.tk_img = ImageTk.PhotoImage(display)
        self.canvas.create_image(int(self.pan_x), int(self.pan_y), anchor="nw", image=self.tk_img)

    def _on_scroll(self, event):
        self._do_zoom(1.15 if event.delta > 0 else 1/1.15, event.x, event.y)

    def _do_zoom(self, factor, mx, my):
        old = self.zoom; self.zoom = max(0.02, min(20.0, self.zoom * factor))
        self.pan_x = mx - (mx - self.pan_x) * (self.zoom / old)
        self.pan_y = my - (my - self.pan_y) * (self.zoom / old)
        self.zoom_lbl.config(text=f"Zoom: {self.zoom*100:.0f}%"); self._render()

    def _on_drag_start(self, event):
        self._drag_start = (event.x, event.y, self.pan_x, self.pan_y)

    def _on_drag(self, event):
        if not self._drag_start: return
        self.pan_x = self._drag_start[2] + event.x - self._drag_start[0]
        self.pan_y = self._drag_start[3] + event.y - self._drag_start[1]
        self._render()

    def _on_mouse_move(self, event):
        if not self.world_img or not self.stitch_info: return
        ix = (event.x - self.pan_x) / self.zoom; iy = (event.y - self.pan_y) / self.zoom
        iw, ih = self.world_img.size
        if ix < 0 or iy < 0 or ix >= iw or iy >= ih:
            self.coord_lbl.config(text=""); return
        
        tw, th = self.stitch_info["tw"], self.stitch_info["th"]
        col = int(ix / tw) + self._grid_offset_col
        row = int(iy / th) + self._grid_offset_row
        letter = col_to_letter(col) if 0 <= col <= 8 else "?"
        num = f"{row+1:02d}" if 0 <= row <= 11 else "??"
        
        px, py = int(ix), int(iy)
        raw = self._world_raw
        if raw is not None and raw.ndim == 2 and py < raw.shape[0] and px < raw.shape[1]:
            val = raw[py, px]
            self.coord_lbl.config(text=f"{letter}{num}  ({px},{py})  val={val}")
        elif raw is not None and raw.ndim == 3 and py < raw.shape[0] and px < raw.shape[1]:
            self.coord_lbl.config(text=f"{letter}{num}  ({px},{py})  RGB={tuple(raw[py,px,:3])}")
        else:
            self.coord_lbl.config(text=f"{letter}{num}  ({px},{py})")

    def _on_resize(self, event):
        if self.world_img: self._render()

    def _export_world(self):
        if not self.world_img: return
        layer_label = LAYERS[self.current_layer]["label"]
        ug = "_UG" if self.show_underground else ""
        default_name = f"TW1_World_{layer_label}{ug}.png"
        path = filedialog.asksaveasfilename(title="Export World Map",
            defaultextension=".png", initialfile=default_name, filetypes=[("PNG", "*.png")])
        if not path: return
        # For heightmap/water: export 16-bit version
        if self.current_layer in ("heightmap", "water_farlod"):
            img16 = world_to_image_16bit(self._world_raw, self.current_layer)
            img16.save(path)
        else:
            self.world_img.save(path)
        self.status_lbl.config(text=f"Exported: {os.path.basename(path)} "
                                     f"({self.world_img.size[0]}×{self.world_img.size[1]})")

    def _export_tiles(self):
        if not self.current_tiles: return
        folder = filedialog.askdirectory(title="Export tiles to folder")
        if not folder: return
        self.status_lbl.config(text="Exporting..."); self.root.update()
        exported = export_tile_pngs(self.current_tiles, self.current_layer, folder)
        self.status_lbl.config(text=f"Exported {len(exported)} tiles (global normalized)")

    def _export_raw(self):
        if not self.current_tiles: return
        if self.current_layer not in ("heightmap", "water_farlod"):
            messagebox.showinfo("RAW Export",
                "RAW export only for Heightmap and Water FarLOD (uint16).\nOther layers: use Export All Tiles.")
            return
        folder = filedialog.askdirectory(title="Export RAW tiles to folder")
        if not folder: return
        self.status_lbl.config(text="Exporting RAW..."); self.root.update()
        exported = export_tile_raw(self.current_tiles, self.current_layer, folder)
        self.status_lbl.config(text=f"Exported {len(exported)} RAW tiles (original uint16)")

if __name__ == "__main__":
    App()
