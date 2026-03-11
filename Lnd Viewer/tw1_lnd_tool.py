#!/usr/bin/env python3
"""TW1 LND Map Editor v2.0 — View/Edit/Import/Export Two Worlds 1 map files (.lnd)
Full format parser per BugLord spec. Import & export binary maps as PNG."""
import struct, os, sys, re, zlib, tkinter as tk
from tkinter import ttk, filedialog, messagebox
from collections import OrderedDict
import numpy as np
try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("WARNING: Pillow not installed. Image export disabled. pip install Pillow")

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

def _i32(data, pos):
    return struct.unpack_from("<i", data, pos)[0], pos + 4

def _u16(data, pos):
    return struct.unpack_from("<H", data, pos)[0], pos + 2

def _f32(data, pos):
    return struct.unpack_from("<f", data, pos)[0], pos + 4

def _frgb(data, pos):
    r, pos = _f32(data, pos); g, pos = _f32(data, pos); b, pos = _f32(data, pos)
    return (r, g, b), pos

def _read_marker(data, pos):
    name, pos = _dstr(data, pos)
    inst, pos = _u32(data, pos)
    x, pos = _u32(data, pos); y, pos = _u32(data, pos); z, pos = _u32(data, pos)
    unk = data[pos:pos+9]; pos += 9
    return {"name": name, "instance": inst, "x": x, "y": y, "z": z, "_unk9": unk}, pos

def _read_skystate(data, pos):
    s = {}
    s["state"], pos = _f32(data, pos)
    s["ambient"], pos = _frgb(data, pos)
    s["diffuse"], pos = _frgb(data, pos)
    s["sun_alpha"], pos = _f32(data, pos)
    s["sun_beta"], pos = _f32(data, pos)
    s["shadow_opacity"], pos = _f32(data, pos)
    s["fog_color"], pos = _frgb(data, pos)
    s["fog_start"], pos = _f32(data, pos)
    s["fog_end"], pos = _f32(data, pos)
    s["fog_fl"], pos = _f32(data, pos)
    s["fog_fc"], pos = _f32(data, pos)
    s["water_fog"], pos = _frgb(data, pos)
    s["rain_color"], pos = _frgb(data, pos)
    s["raindrop_alpha"], pos = _f32(data, pos)
    s["sky_color"], pos = _frgb(data, pos)
    s["raindrop_end_alpha"], pos = _f32(data, pos)
    s["snow_color"], pos = _frgb(data, pos)
    s["snowflake_alpha"], pos = _f32(data, pos)
    s["sky_glow"], pos = _frgb(data, pos)
    s["snowflake_end_alpha"], pos = _f32(data, pos)
    s["cloud_a"], pos = _frgb(data, pos)
    s["cloud_b"], pos = _frgb(data, pos)
    return s, pos

def _read_water_pool(data, pos):
    p = {}
    p["color_r"], p["color_g"], p["color_b"], p["_unk1"] = struct.unpack_from("BBBB", data, pos); pos += 4
    p["color_depth"], pos = _f32(data, pos)
    p["_unk4"] = data[pos:pos+4]; pos += 4
    p["height"], pos = _u16(data, pos)
    p["liquid_lightning"], pos = _u32(data, pos)
    p["is_lava"], pos = _u32(data, pos)
    p["_unk88"] = data[pos:pos+88]; pos += 88
    p["flow_dir"], pos = _f32(data, pos)
    p["flow_speed"], pos = _f32(data, pos)
    p["_unk8"] = data[pos:pos+8]; pos += 8
    p["reflect_min"], pos = _f32(data, pos)
    p["reflect_max"], pos = _f32(data, pos)
    p["_unk16"] = data[pos:pos+16]; pos += 16
    p["is_rain"], pos = _u32(data, pos)
    p["lava_tex1"], pos = _dstr(data, pos)
    p["lava_tex2"], pos = _dstr(data, pos)
    p["min_x"], pos = _u16(data, pos); p["min_y"], pos = _u16(data, pos)
    p["max_x"], pos = _u16(data, pos); p["max_y"], pos = _u16(data, pos)
    return p, pos

def _read_object(data, pos):
    name, pos = _dstr(data, pos)
    unk8 = data[pos:pos+8]; pos += 8
    x, pos = _u32(data, pos); y, pos = _u32(data, pos); z, pos = _u32(data, pos)
    rot = data[pos:pos+3]; pos += 3
    return {"name": name, "_unk8": unk8, "x": x, "y": y, "z": z, "rot": rot}, pos

def _read_fog(data, pos):
    level, pos = _u16(data, pos); offset, pos = _u16(data, pos)
    light, pos = _u32(data, pos)
    b, g, r, a = struct.unpack_from("BBBB", data, pos); pos += 4
    return {"level": level, "offset": offset, "light": light,
            "r": r, "g": g, "b": b, "a": a}, pos

def _decompress_lnd(raw):
    """Try multiple decompression strategies. Returns (map_data, header_info)."""
    hdr_default = {"pre_head": 0, "extra_int": b"LN\x00\x00", "guid": b"\x00"*16, "is_editor": False}
    
    # Strategy 1: Raw LND (starts with LN\0\0)
    if raw[:4] == b"LN\x00\x00":
        return raw, hdr_default
    
    # Strategy 2: Try zlib decompression
    try:
        d1 = zlib.decompressobj()
        chunk1 = d1.decompress(raw)
        remaining = d1.unused_data
        
        # 2a: Editor format (dual zlib: small header + map)
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
            except:
                pass
        
        # 2b: Single zlib -> LND data directly
        if chunk1[:4] == b"LN\x00\x00":
            return chunk1, hdr_default
        
        # 2c: Remaining might contain LND data
        if remaining:
            try:
                d2 = zlib.decompressobj()
                map_data = d2.decompress(remaining)
                if map_data[:4] == b"LN\x00\x00":
                    return map_data, {"pre_head": 0, "extra_int": b"LN\x00\x00",
                                       "guid": b"\x00"*16, "is_editor": True}
            except:
                pass
    except zlib.error:
        pass
    
    # Strategy 3: Full file zlib.decompress
    try:
        decompressed = zlib.decompress(raw)
        if decompressed[:4] == b"LN\x00\x00":
            return decompressed, hdr_default
    except:
        pass
    
    raise ValueError(f"Unknown LND format. First 16 bytes: {raw[:16].hex()}")

def parse_lnd(filepath):
    """Parse a TW1 .lnd file. Returns dict with all sections."""
    with open(filepath, "rb") as f:
        raw = f.read()
    data, hdr_info = _decompress_lnd(raw)

    m = OrderedDict()
    m["_pre_head"] = hdr_info["pre_head"]
    m["_extra_int"] = hdr_info["extra_int"]
    m["_guid"] = hdr_info["guid"]
    m["_is_editor"] = hdr_info["is_editor"]
    pos = 0

    # Header
    hdr = data[0:4]; pos = 4
    if hdr != b"LN\x00\x00":
        raise ValueError(f"Bad LND header: {hdr.hex()}")

    m["map_name"], pos = _dstr2(data, pos)
    m["width"], pos = _u32(data, pos)
    m["height"], pos = _u32(data, pos)
    m["_unk_pair"] = data[pos:pos+8]; pos += 8
    m["underground"], pos = _u32(data, pos)
    m["upper"], pos = _dstr(data, pos)
    m["lower"], pos = _dstr(data, pos)
    m["left"], pos = _dstr(data, pos)
    m["right"], pos = _dstr(data, pos)
    m["down"], pos = _dstr(data, pos)
    m["up"], pos = _dstr(data, pos)

    # Markers
    cnt, pos = _u32(data, pos); pad, pos = _u32(data, pos)
    m["_markers_pad"] = pad
    m["markers"] = []
    for _ in range(cnt):
        mk, pos = _read_marker(data, pos)
        m["markers"].append(mk)

    # Skybox Textures
    cnt, pos = _u32(data, pos); pad, pos = _u32(data, pos)
    m["_skybox_pad"] = pad
    m["skybox_textures"] = []
    for _ in range(cnt):
        t, pos = _dstr(data, pos)
        m["skybox_textures"].append(t)

    # Sky States
    cnt, pos = _u32(data, pos); pad, pos = _u32(data, pos)
    m["_skystates_pad"] = pad
    m["sky_states"] = []
    for _ in range(cnt):
        ss, pos = _read_skystate(data, pos)
        m["sky_states"].append(ss)

    m["day_length"], pos = _u32(data, pos)
    m["sunrise_state"], pos = _u32(data, pos)
    m["sunset_state"], pos = _u32(data, pos)

    # Heightmap (2D Array uint16)
    w, pos = _u32(data, pos); h, pos = _u32(data, pos)
    sz = w * h * 2
    m["heightmap"] = {"w": w, "h": h, "data": data[pos:pos+sz]}; pos += sz

    # Vertical Edge
    cnt, pos = _u32(data, pos)
    m["vert_edge"] = {"count": cnt, "data": data[pos:pos+cnt*2]}; pos += cnt * 2

    # Horizontal Edge
    cnt, pos = _u32(data, pos)
    m["horiz_edge"] = {"count": cnt, "data": data[pos:pos+cnt*2]}; pos += cnt * 2

    # Water Tile FarLOD
    w, pos = _u32(data, pos); h, pos = _u32(data, pos)
    sz = w * h * 2
    m["water_farlod"] = {"w": w, "h": h, "data": data[pos:pos+sz]}; pos += sz

    # Water Pools
    cnt, pos = _u32(data, pos); pad, pos = _u32(data, pos)
    m["_waterpools_pad"] = pad
    m["water_pools"] = []
    for _ in range(cnt):
        wp, pos = _read_water_pool(data, pos)
        m["water_pools"].append(wp)

    # Map Color Base (2D BGRA)
    w, pos = _u32(data, pos); h, pos = _u32(data, pos)
    sz = w * h * 4
    m["color_base"] = {"w": w, "h": h, "data": data[pos:pos+sz]}; pos += sz

    # Textures & Stamps
    cnt, pos = _u32(data, pos); pad, pos = _u32(data, pos)
    m["_texstamps_pad"] = pad
    m["textures_stamps"] = []
    for _ in range(cnt):
        t, pos = _dstr(data, pos)
        m["textures_stamps"].append(t)

    # Unknown byte
    m["_unk_byte1"] = data[pos]; pos += 1

    # Texture Reference Map
    w, pos = _u32(data, pos); h, pos = _u32(data, pos)
    sz = w * h * 4
    m["tex_ref_map"] = {"w": w, "h": h, "data": data[pos:pos+sz]}; pos += sz

    # Texture Alpha Map
    w, pos = _u32(data, pos); h, pos = _u32(data, pos)
    sz = w * h * 4
    m["tex_alpha_map"] = {"w": w, "h": h, "data": data[pos:pos+sz]}; pos += sz

    # Objects
    cnt, pos = _u32(data, pos); pad, pos = _u32(data, pos)
    m["_objects_pad"] = pad
    m["objects"] = []
    for _ in range(cnt):
        obj, pos = _read_object(data, pos)
        m["objects"].append(obj)

    # Terrain Fog Ref Map
    w, pos = _u32(data, pos); h, pos = _u32(data, pos)
    sz = w * h * 2
    m["fog_ref_map"] = {"w": w, "h": h, "data": data[pos:pos+sz]}; pos += sz

    # Fog Descriptions
    cnt, pos = _u32(data, pos); pad, pos = _u32(data, pos)
    m["_fog_pad"] = pad
    m["fogs"] = []
    for _ in range(cnt):
        fg, pos = _read_fog(data, pos)
        m["fogs"].append(fg)

    # Flower/Grass Map (21 bytes per tile)
    w, pos = _u32(data, pos); h, pos = _u32(data, pos)
    sz = w * h * 21
    m["flower_grass"] = {"w": w, "h": h, "data": data[pos:pos+sz]}; pos += sz

    # Stamp Map (16 bytes per tile)
    w, pos = _u32(data, pos); h, pos = _u32(data, pos)
    sz = w * h * 16
    m["stamp_map"] = {"w": w, "h": h, "data": data[pos:pos+sz]}; pos += sz

    # EAX Map (1 byte per tile)
    w, pos = _u32(data, pos); h, pos = _u32(data, pos)
    sz = w * h
    m["eax_map"] = {"w": w, "h": h, "data": data[pos:pos+sz]}; pos += sz

    # Passable Terrain (Weird 2D: w, h, w_again, data)
    w, pos = _u32(data, pos); h, pos = _u32(data, pos)
    w2, pos = _u32(data, pos)
    sz = w * h * 4
    m["passable"] = {"w": w, "h": h, "w2": w2, "data": data[pos:pos+sz]}; pos += sz

    # Disabled Terrain
    w, pos = _u32(data, pos); h, pos = _u32(data, pos)
    w2, pos = _u32(data, pos)
    sz = w * h * 4
    m["disabled"] = {"w": w, "h": h, "w2": w2, "data": data[pos:pos+sz]}; pos += sz

    # Interiors
    w, pos = _u32(data, pos); h, pos = _u32(data, pos)
    w2, pos = _u32(data, pos)
    sz = w * h * 4
    m["interiors"] = {"w": w, "h": h, "w2": w2, "data": data[pos:pos+sz]}; pos += sz

    # Unknown uint16 array
    cnt, pos = _u32(data, pos)
    m["_unk_u16arr"] = {"count": cnt, "data": data[pos:pos+cnt*2]}; pos += cnt * 2

    # Unknown 2D uint32
    w, pos = _u32(data, pos); h, pos = _u32(data, pos)
    sz = w * h * 4
    m["_unk_2d_u32"] = {"w": w, "h": h, "data": data[pos:pos+sz]}; pos += sz

    # Plaintext Objects
    cnt, pos = _u32(data, pos); pad, pos = _u32(data, pos)
    m["_plainobj_pad"] = pad
    m["plaintext_objects"] = []
    for _ in range(cnt):
        o, pos = _dstr(data, pos)
        m["plaintext_objects"].append(o)

    m["_parse_pos"] = pos
    m["_data_len"] = len(data)
    return m

# ============================================================
# LND WRITER
# ============================================================
def _wdstr(out, s):
    b = s.encode("ascii")
    out += struct.pack("<I", len(b)) + b

def _wdstr2(out, s):
    b = s.encode("utf-16-le")
    out += struct.pack("<I", len(b) // 2) + b

def _wu32(out, v):
    out += struct.pack("<I", v)

def _wi32(out, v):
    out += struct.pack("<i", v)

def _wu16(out, v):
    out += struct.pack("<H", v)

def _wf32(out, v):
    out += struct.pack("<f", v)

def _wfrgb(out, rgb):
    out += struct.pack("<fff", *rgb)

def _write_skystate(out, s):
    _wf32(out, s["state"])
    _wfrgb(out, s["ambient"]); _wfrgb(out, s["diffuse"])
    _wf32(out, s["sun_alpha"]); _wf32(out, s["sun_beta"]); _wf32(out, s["shadow_opacity"])
    _wfrgb(out, s["fog_color"])
    _wf32(out, s["fog_start"]); _wf32(out, s["fog_end"])
    _wf32(out, s["fog_fl"]); _wf32(out, s["fog_fc"])
    _wfrgb(out, s["water_fog"]); _wfrgb(out, s["rain_color"])
    _wf32(out, s["raindrop_alpha"])
    _wfrgb(out, s["sky_color"]); _wf32(out, s["raindrop_end_alpha"])
    _wfrgb(out, s["snow_color"]); _wf32(out, s["snowflake_alpha"])
    _wfrgb(out, s["sky_glow"]); _wf32(out, s["snowflake_end_alpha"])
    _wfrgb(out, s["cloud_a"]); _wfrgb(out, s["cloud_b"])

def write_lnd(filepath, m):
    """Write a TW1 .lnd file. Creates .bak backup first."""
    if os.path.exists(filepath):
        import shutil; shutil.copy2(filepath, filepath + ".bak")
    out = bytearray()
    out += b"LN\x00\x00"
    _wdstr2(out, m["map_name"])
    _wu32(out, m["width"]); _wu32(out, m["height"])
    out += m["_unk_pair"]
    _wu32(out, m["underground"])
    for k in ["upper", "lower", "left", "right", "down", "up"]:
        _wdstr(out, m[k])
    # Markers
    _wu32(out, len(m["markers"])); _wu32(out, m.get("_markers_pad", 0))
    for mk in m["markers"]:
        _wdstr(out, mk["name"]); _wu32(out, mk["instance"])
        _wu32(out, mk["x"]); _wu32(out, mk["y"]); _wu32(out, mk["z"])
        out += mk["_unk9"]
    # Skybox
    _wu32(out, len(m["skybox_textures"])); _wu32(out, m.get("_skybox_pad", 0))
    for t in m["skybox_textures"]:
        _wdstr(out, t)
    # Sky States
    _wu32(out, len(m["sky_states"])); _wu32(out, m.get("_skystates_pad", 0))
    for ss in m["sky_states"]:
        _write_skystate(out, ss)
    _wu32(out, m["day_length"]); _wu32(out, m["sunrise_state"]); _wu32(out, m["sunset_state"])
    # Heightmap
    hm = m["heightmap"]
    _wu32(out, hm["w"]); _wu32(out, hm["h"]); out += hm["data"]
    # Vert/Horiz Edge
    ve = m["vert_edge"]; _wu32(out, ve["count"]); out += ve["data"]
    he = m["horiz_edge"]; _wu32(out, he["count"]); out += he["data"]
    # Water FarLOD
    wf = m["water_farlod"]; _wu32(out, wf["w"]); _wu32(out, wf["h"]); out += wf["data"]
    # Water Pools
    _wu32(out, len(m["water_pools"])); _wu32(out, m.get("_waterpools_pad", 0))
    for wp in m["water_pools"]:
        out += struct.pack("BBBB", wp["color_r"], wp["color_g"], wp["color_b"], wp["_unk1"])
        _wf32(out, wp["color_depth"]); out += wp["_unk4"]
        _wu16(out, wp["height"]); _wu32(out, wp["liquid_lightning"]); _wu32(out, wp["is_lava"])
        out += wp["_unk88"]
        _wf32(out, wp["flow_dir"]); _wf32(out, wp["flow_speed"]); out += wp["_unk8"]
        _wf32(out, wp["reflect_min"]); _wf32(out, wp["reflect_max"]); out += wp["_unk16"]
        _wu32(out, wp["is_rain"])
        _wdstr(out, wp["lava_tex1"]); _wdstr(out, wp["lava_tex2"])
        _wu16(out, wp["min_x"]); _wu16(out, wp["min_y"])
        _wu16(out, wp["max_x"]); _wu16(out, wp["max_y"])
    # Color Base
    cb = m["color_base"]; _wu32(out, cb["w"]); _wu32(out, cb["h"]); out += cb["data"]
    # Textures & Stamps
    _wu32(out, len(m["textures_stamps"])); _wu32(out, m.get("_texstamps_pad", 0))
    for t in m["textures_stamps"]:
        _wdstr(out, t)
    out += bytes([m["_unk_byte1"]])
    # Tex Ref Map
    tr = m["tex_ref_map"]; _wu32(out, tr["w"]); _wu32(out, tr["h"]); out += tr["data"]
    # Tex Alpha Map
    ta = m["tex_alpha_map"]; _wu32(out, ta["w"]); _wu32(out, ta["h"]); out += ta["data"]
    # Objects
    _wu32(out, len(m["objects"])); _wu32(out, m.get("_objects_pad", 0))
    for obj in m["objects"]:
        _wdstr(out, obj["name"]); out += obj["_unk8"]
        _wu32(out, obj["x"]); _wu32(out, obj["y"]); _wu32(out, obj["z"])
        out += obj["rot"]
    # Fog Ref Map
    fr = m["fog_ref_map"]; _wu32(out, fr["w"]); _wu32(out, fr["h"]); out += fr["data"]
    # Fog Descs
    _wu32(out, len(m["fogs"])); _wu32(out, m.get("_fog_pad", 0))
    for fg in m["fogs"]:
        _wu16(out, fg["level"]); _wu16(out, fg["offset"]); _wu32(out, fg["light"])
        out += struct.pack("BBBB", fg["b"], fg["g"], fg["r"], fg["a"])
    # Flower/Grass
    fg = m["flower_grass"]; _wu32(out, fg["w"]); _wu32(out, fg["h"]); out += fg["data"]
    # Stamp Map
    sm = m["stamp_map"]; _wu32(out, sm["w"]); _wu32(out, sm["h"]); out += sm["data"]
    # EAX Map
    em = m["eax_map"]; _wu32(out, em["w"]); _wu32(out, em["h"]); out += em["data"]
    # Passable
    pt = m["passable"]; _wu32(out, pt["w"]); _wu32(out, pt["h"]); _wu32(out, pt["w2"]); out += pt["data"]
    # Disabled
    dt = m["disabled"]; _wu32(out, dt["w"]); _wu32(out, dt["h"]); _wu32(out, dt["w2"]); out += dt["data"]
    # Interiors
    it = m["interiors"]; _wu32(out, it["w"]); _wu32(out, it["h"]); _wu32(out, it["w2"]); out += it["data"]
    # Unknown arrays
    ua = m["_unk_u16arr"]; _wu32(out, ua["count"]); out += ua["data"]
    u2 = m["_unk_2d_u32"]; _wu32(out, u2["w"]); _wu32(out, u2["h"]); out += u2["data"]
    # Plaintext Objects
    _wu32(out, len(m["plaintext_objects"])); _wu32(out, m.get("_plainobj_pad", 0))
    for o in m["plaintext_objects"]:
        _wdstr(out, o)

    # Compress as editor format
    if m.get("_is_editor", True):
        hdr_data = bytearray()
        hdr_data += struct.pack("<I", m["_pre_head"])
        hdr_data += m["_extra_int"]
        hdr_data += m["_guid"]
        compressed_hdr = zlib.compress(bytes(hdr_data))
        compressed_map = zlib.compress(bytes(out))
        final = compressed_hdr + compressed_map
    else:
        final = bytes(out)

    with open(filepath, "wb") as f:
        f.write(final)
    return len(final)

# ============================================================
# IMAGE EXPORT
# ============================================================
def export_heightmap(m, path):
    hm = m["heightmap"]
    arr = np.frombuffer(hm["data"], dtype=np.uint16).reshape(hm["h"], hm["w"])
    # Normalize to 0-65535
    mn, mx = arr.min(), arr.max()
    if mx > mn:
        norm = ((arr.astype(np.float32) - mn) / (mx - mn) * 65535).astype(np.uint16)
    else:
        norm = arr
    # Save as 16-bit grayscale PNG
    img = Image.fromarray(norm)
    img.save(path)
    return img

def export_color_base(m, path):
    cb = m["color_base"]
    arr = np.frombuffer(cb["data"], dtype=np.uint8).reshape(cb["h"], cb["w"], 4)
    # BGRA -> RGBA
    rgba = arr[:, :, [2, 1, 0, 3]]
    img = Image.fromarray(rgba, mode="RGBA")
    img.save(path)
    return img

def export_tex_ref(m, path):
    tr = m["tex_ref_map"]
    arr = np.frombuffer(tr["data"], dtype=np.uint8).reshape(tr["h"], tr["w"], 4)
    # 4 texture indices as RGBA channels (scaled for visibility)
    vis = (arr.astype(np.float32) / max(arr.max(), 1) * 255).astype(np.uint8)
    img = Image.fromarray(vis, mode="RGBA")
    img.save(path)
    return img

def export_tex_alpha(m, path):
    ta = m["tex_alpha_map"]
    arr = np.frombuffer(ta["data"], dtype=np.uint8).reshape(ta["h"], ta["w"], 4)
    img = Image.fromarray(arr, mode="RGBA")
    img.save(path)
    return img

def export_water_farlod(m, path):
    wf = m["water_farlod"]
    if wf["w"] == 0 or wf["h"] == 0: return None
    arr = np.frombuffer(wf["data"], dtype=np.uint16).reshape(wf["h"], wf["w"])
    mn, mx = arr.min(), arr.max()
    if mx > mn:
        norm = ((arr.astype(np.float32) - mn) / (mx - mn) * 255).astype(np.uint8)
    else:
        norm = np.zeros((wf["h"], wf["w"]), dtype=np.uint8)
    img = Image.fromarray(norm, mode="L")
    img.save(path)
    return img

def export_fog_ref(m, path):
    fr = m["fog_ref_map"]
    if fr["w"] == 0 or fr["h"] == 0: return None
    arr = np.frombuffer(fr["data"], dtype=np.uint16).reshape(fr["h"], fr["w"])
    mn, mx = arr.min(), arr.max()
    if mx > mn:
        norm = ((arr.astype(np.float32) - mn) / (mx - mn) * 255).astype(np.uint8)
    else:
        norm = np.zeros((fr["h"], fr["w"]), dtype=np.uint8)
    img = Image.fromarray(norm, mode="L")
    img.save(path)
    return img

def export_eax(m, path):
    em = m["eax_map"]
    if em["w"] == 0 or em["h"] == 0: return None
    arr = np.frombuffer(em["data"], dtype=np.uint8).reshape(em["h"], em["w"])
    img = Image.fromarray(arr, mode="L")
    img.save(path)
    return img

def export_flower_grass(m, path):
    fg = m["flower_grass"]
    if fg["w"] == 0 or fg["h"] == 0: return None
    raw = np.frombuffer(fg["data"], dtype=np.uint8).reshape(fg["h"], fg["w"], 21)
    # ref1=byte1, ref2=byte2, amounts at bytes 13-16 and 17-20 (float32)
    r = raw[:, :, 1]  # ref1
    g = raw[:, :, 2]  # ref2
    b = raw[:, :, 0]  # unknown first byte
    rgb = np.stack([r, g, b], axis=2)
    img = Image.fromarray(rgb, mode="RGB")
    img.save(path)
    return img

def export_stamp_map(m, path):
    sm = m["stamp_map"]
    if sm["w"] == 0 or sm["h"] == 0: return None
    raw = np.frombuffer(sm["data"], dtype=np.uint8).reshape(sm["h"], sm["w"], 16)
    # Use first 3 bytes as RGB
    rgb = raw[:, :, :3]
    img = Image.fromarray(rgb, mode="RGB")
    img.save(path)
    return img

def export_passable(m, path):
    pt = m["passable"]
    if pt["w"] == 0 or pt["h"] == 0: return None
    arr = np.frombuffer(pt["data"], dtype=np.uint32).reshape(pt["h"], pt["w"])
    vis = (arr > 0).astype(np.uint8) * 255
    img = Image.fromarray(vis, mode="L")
    img.save(path)
    return img

def export_disabled(m, path):
    dt = m["disabled"]
    if dt["w"] == 0 or dt["h"] == 0: return None
    arr = np.frombuffer(dt["data"], dtype=np.uint32).reshape(dt["h"], dt["w"])
    vis = (arr > 0).astype(np.uint8) * 255
    img = Image.fromarray(vis, mode="L")
    img.save(path)
    return img

def export_interiors(m, path):
    it = m["interiors"]
    if it["w"] == 0 or it["h"] == 0: return None
    arr = np.frombuffer(it["data"], dtype=np.uint32).reshape(it["h"], it["w"])
    vis = (arr > 0).astype(np.uint8) * 255
    img = Image.fromarray(vis, mode="L")
    img.save(path)
    return img

# ============================================================
# IMAGE IMPORT — Replace map data from PNG
# ============================================================
def _validate_import_dims(img, expected_w, expected_h, label):
    """Validate imported image dimensions match the map."""
    if img.width != expected_w or img.height != expected_h:
        raise ValueError(
            f"{label}: Image is {img.width}x{img.height}, "
            f"but map expects {expected_w}x{expected_h}")

def import_heightmap(m, path):
    """Import heightmap from 16-bit or 8-bit grayscale PNG."""
    hm = m["heightmap"]
    img = Image.open(path)
    _validate_import_dims(img, hm["w"], hm["h"], "Heightmap")
    arr = np.array(img)
    if arr.dtype == np.uint16:
        data = arr.astype(np.uint16)
    elif arr.dtype == np.uint8:
        if arr.ndim == 3:
            arr = arr[:, :, 0]
        data = (arr.astype(np.uint16) * 257)  # scale 0-255 → 0-65535
    else:
        data = arr.astype(np.uint16)
    m["heightmap"]["data"] = data.tobytes()

def import_color_base(m, path):
    """Import color base from RGBA PNG → stored as BGRA."""
    cb = m["color_base"]
    img = Image.open(path).convert("RGBA")
    _validate_import_dims(img, cb["w"], cb["h"], "Color Base")
    arr = np.array(img)
    bgra = arr[:, :, [2, 1, 0, 3]]  # RGBA → BGRA
    m["color_base"]["data"] = bgra.tobytes()

def import_tex_ref(m, path):
    """Import texture reference map from RGBA PNG."""
    tr = m["tex_ref_map"]
    img = Image.open(path).convert("RGBA")
    _validate_import_dims(img, tr["w"], tr["h"], "Tex Reference")
    arr = np.array(img)
    m["tex_ref_map"]["data"] = arr.tobytes()

def import_tex_alpha(m, path):
    """Import texture alpha map from RGBA PNG."""
    ta = m["tex_alpha_map"]
    img = Image.open(path).convert("RGBA")
    _validate_import_dims(img, ta["w"], ta["h"], "Tex Alpha")
    arr = np.array(img)
    m["tex_alpha_map"]["data"] = arr.tobytes()

def import_water_farlod(m, path):
    """Import water FarLOD from grayscale PNG → uint16."""
    wf = m["water_farlod"]
    img = Image.open(path)
    _validate_import_dims(img, wf["w"], wf["h"], "Water FarLOD")
    arr = np.array(img)
    if arr.dtype == np.uint16:
        data = arr
    elif arr.dtype == np.uint8:
        if arr.ndim == 3: arr = arr[:, :, 0]
        data = (arr.astype(np.uint16) * 257)
    else:
        data = arr.astype(np.uint16)
    m["water_farlod"]["data"] = data.tobytes()

def import_fog_ref(m, path):
    """Import fog reference from grayscale PNG → uint16."""
    fr = m["fog_ref_map"]
    img = Image.open(path)
    _validate_import_dims(img, fr["w"], fr["h"], "Fog Reference")
    arr = np.array(img)
    if arr.dtype == np.uint16:
        data = arr
    elif arr.dtype == np.uint8:
        if arr.ndim == 3: arr = arr[:, :, 0]
        data = (arr.astype(np.uint16) * 257)
    else:
        data = arr.astype(np.uint16)
    m["fog_ref_map"]["data"] = data.tobytes()

def import_eax(m, path):
    """Import EAX map from grayscale PNG → uint8."""
    em = m["eax_map"]
    img = Image.open(path).convert("L")
    _validate_import_dims(img, em["w"], em["h"], "EAX Map")
    arr = np.array(img, dtype=np.uint8)
    m["eax_map"]["data"] = arr.tobytes()

def import_flower_grass(m, path):
    """Import flower/grass from RGB PNG → update density channels (bytes 15,17,19)."""
    fg = m["flower_grass"]
    img = Image.open(path).convert("RGB")
    _validate_import_dims(img, fg["w"], fg["h"], "Flower/Grass")
    rgb = np.array(img, dtype=np.uint8)
    raw = np.frombuffer(fg["data"], dtype=np.uint8).reshape(fg["h"], fg["w"], 21).copy()
    raw[:, :, 1] = rgb[:, :, 0]   # ref1 channel
    raw[:, :, 2] = rgb[:, :, 1]   # ref2 channel
    raw[:, :, 0] = rgb[:, :, 2]   # byte0
    m["flower_grass"]["data"] = raw.tobytes()

def import_stamp_map(m, path):
    """Import stamp map from RGB PNG → update first 3 bytes per cell."""
    sm = m["stamp_map"]
    img = Image.open(path).convert("RGB")
    _validate_import_dims(img, sm["w"], sm["h"], "Stamp Map")
    rgb = np.array(img, dtype=np.uint8)
    raw = np.frombuffer(sm["data"], dtype=np.uint8).reshape(sm["h"], sm["w"], 16).copy()
    raw[:, :, :3] = rgb
    m["stamp_map"]["data"] = raw.tobytes()

def import_passable(m, path):
    """Import passable terrain from grayscale PNG → uint32 (>0 = passable)."""
    pt = m["passable"]
    img = Image.open(path).convert("L")
    _validate_import_dims(img, pt["w"], pt["h"], "Passable")
    arr = np.array(img, dtype=np.uint8)
    data = (arr > 0).astype(np.uint32)
    m["passable"]["data"] = data.tobytes()

def import_disabled(m, path):
    """Import disabled terrain from grayscale PNG → uint32 (>0 = disabled)."""
    dt = m["disabled"]
    img = Image.open(path).convert("L")
    _validate_import_dims(img, dt["w"], dt["h"], "Disabled")
    arr = np.array(img, dtype=np.uint8)
    data = (arr > 0).astype(np.uint32)
    m["disabled"]["data"] = data.tobytes()

def import_interiors(m, path):
    """Import interiors from grayscale PNG → uint32 (>0 = interior)."""
    it = m["interiors"]
    img = Image.open(path).convert("L")
    _validate_import_dims(img, it["w"], it["h"], "Interiors")
    arr = np.array(img, dtype=np.uint8)
    data = (arr > 0).astype(np.uint32)
    m["interiors"]["data"] = data.tobytes()

def export_all_maps(m, out_dir):
    """Export all binary maps as PNGs. Returns list of (name, path, img)."""
    os.makedirs(out_dir, exist_ok=True)
    name = m["map_name"]
    results = []
    exporters = [
        ("Heightmap", export_heightmap),
        ("ColorBase", export_color_base),
        ("TexRef", export_tex_ref),
        ("TexAlpha", export_tex_alpha),
        ("WaterFarLOD", export_water_farlod),
        ("FogRef", export_fog_ref),
        ("EAX", export_eax),
        ("FlowerGrass", export_flower_grass),
        ("StampMap", export_stamp_map),
        ("Passable", export_passable),
        ("Disabled", export_disabled),
        ("Interiors", export_interiors),
    ]
    for label, fn in exporters:
        try:
            p = os.path.join(out_dir, f"{name}_{label}.png")
            img = fn(m, p)
            if img:
                results.append((label, p, img))
        except Exception as e:
            print(f"Export {label} failed: {e}")
    return results

# ============================================================
# APP
# ============================================================
class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("TW1 LND Map Editor v2.0")
        self.root.geometry("1280x800")
        self.root.configure(bg=BG)
        self.root.minsize(900, 600)
        self.font_size = 11
        self.m = None
        self.filepath = None
        self.modified = False
        self.tree_map = {}
        self._photo_refs = []
        self._build_ui()
        self._auto_load()
        self.root.mainloop()

    def _build_ui(self):
        tb = tk.Frame(self.root, bg=BG2, padx=8, pady=6); tb.pack(fill="x")
        tk.Label(tb, text="TW1 LND Map Editor v2.0", font=("Segoe UI", 12, "bold"),
                 bg=BG2, fg=GREEN).pack(side="left")
        self.status_lbl = tk.Label(tb, text="", font=("Segoe UI", 9), bg=BG2, fg=ORANGE)
        self.status_lbl.pack(side="left", padx=12)
        tk.Button(tb, text="Export All PNGs", bg=PURPLE, fg="#fff", font=("Segoe UI", 10, "bold"),
                  bd=0, padx=10, command=self._export_all).pack(side="right", padx=4)
        tk.Button(tb, text="Save As", bg=CYAN, fg="#000",
                  font=("Segoe UI", 10, "bold"), bd=0, padx=10,
                  command=self._save_as).pack(side="right", padx=4)
        self.save_btn = tk.Button(tb, text="Save", bg=GREEN, fg="#000",
                  font=("Segoe UI", 10, "bold"), bd=0, padx=12, command=self._save_file)
        self.save_btn.pack(side="right", padx=4)
        tk.Button(tb, text="Load", bg=RED, fg="#fff", font=("Segoe UI", 10, "bold"),
                  bd=0, padx=12, command=self._load_file).pack(side="right", padx=4)
        pw = tk.PanedWindow(self.root, orient="horizontal", bg=BG, sashwidth=4, sashrelief="flat")
        pw.pack(fill="both", expand=True)
        left = tk.Frame(pw, bg=BG); pw.add(left, width=340)
        style = ttk.Style(); style.theme_use("clam")
        style.configure("D.Treeview", background=BG, foreground=FG,
                         fieldbackground=BG, font=("Segoe UI", 10), rowheight=24)
        style.map("D.Treeview", background=[("selected", BG4)], foreground=[("selected", GREEN)])
        self.tree = ttk.Treeview(left, style="D.Treeview", show="tree")
        scr = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scr.set)
        scr.pack(side="right", fill="y"); self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        right = tk.Frame(pw, bg=BG); pw.add(right)
        self.detail = tk.Frame(right, bg=BG); self.detail.pack(fill="both", expand=True)
        self._show_welcome()

    def _auto_load(self):
        d = os.path.dirname(os.path.abspath(__file__))
        for f in os.listdir(d):
            if f.lower().endswith(".lnd"):
                self._do_load(os.path.join(d, f)); return

    def _load_file(self):
        p = filedialog.askopenfilename(title="Open LND file",
            filetypes=[("LND files", "*.lnd"), ("All", "*.*")])
        if p: self._do_load(p)

    def _save_file(self):
        if not self.m: return
        p = self.filepath or filedialog.asksaveasfilename(
            title="Save LND", defaultextension=".lnd",
            filetypes=[("LND files", "*.lnd")])
        if not p: return
        try:
            sz = write_lnd(p, self.m)
            self.modified = False
            self._update_title()
            self.status_lbl.config(text=f"Saved! {sz:,} bytes")
        except Exception as e:
            messagebox.showerror("Error", f"Save failed:\n{e}")
            import traceback; traceback.print_exc()

    def _save_as(self):
        if not self.m: return
        p = filedialog.asksaveasfilename(
            title="Save LND As", defaultextension=".lnd",
            filetypes=[("LND files", "*.lnd")])
        if not p: return
        try:
            sz = write_lnd(p, self.m)
            self.filepath = p
            self.modified = False
            self._update_title()
            self.status_lbl.config(text=f"Saved as {os.path.basename(p)}! {sz:,} bytes")
        except Exception as e:
            messagebox.showerror("Error", f"Save failed:\n{e}")
            import traceback; traceback.print_exc()

    def _export_all(self):
        if not self.m: return
        d = filedialog.askdirectory(title="Export PNGs to folder")
        if not d: return
        results = export_all_maps(self.m, d)
        self.status_lbl.config(text=f"Exported {len(results)} PNGs to {os.path.basename(d)}")
        messagebox.showinfo("Export Complete",
            f"Exported {len(results)} map images:\n\n" +
            "\n".join(f"  {r[0]}: {os.path.basename(r[1])}" for r in results))

    def _do_load(self, path):
        try:
            self.root.title("TW1 LND Map Editor v2.0 — Loading...")
            self.root.update()
            self.m = parse_lnd(path)
            self.filepath = path
            self.modified = False
            self._build_tree()
            self._update_title()
            m = self.m
            parts = [f"{m['map_name']}", f"{m['width']}x{m['height']}",
                     f"{len(m['markers'])} markers", f"{len(m['objects'])} objects",
                     f"{len(m['plaintext_objects'])} entities",
                     f"parse: {m['_parse_pos']}/{m['_data_len']}"]
            self.status_lbl.config(text="  |  ".join(parts))
            self._show_stats()
        except Exception as e:
            messagebox.showerror("Error", f"Load failed:\n{e}")
            import traceback; traceback.print_exc()

    def _update_title(self):
        name = os.path.basename(self.filepath) if self.filepath else "?"
        pfx = "* " if self.modified else ""
        self.root.title(f"{pfx}TW1 LND Map Editor v2.0 — {name}")

    def _mark_modified(self):
        self.modified = True; self._update_title()

    # ---- TREE ----
    def _build_tree(self):
        self.tree.delete(*self.tree.get_children()); self.tree_map.clear()
        m = self.m
        if not m: return
        # Map Info
        t = self.tree.insert("", "end", text=f"\U0001f5fa  Map Info"); self.tree_map[t] = ("info",)
        # Markers
        t = self.tree.insert("", "end", text=f"\U0001f4cd  Markers ({len(m['markers'])})"); self.tree_map[t] = ("markers",)
        # Skybox & Weather
        t = self.tree.insert("", "end", text=f"\u2600  Sky & Weather"); self.tree_map[t] = ("sky",)
        # Maps section
        maps_node = self.tree.insert("", "end", text=f"\U0001f5bc  Binary Maps (12)")
        map_items = [
            ("Heightmap", "heightmap", f"{m['heightmap']['w']}x{m['heightmap']['h']}"),
            ("Color Base", "color_base", f"{m['color_base']['w']}x{m['color_base']['h']}"),
            ("Tex Reference", "tex_ref", f"{m['tex_ref_map']['w']}x{m['tex_ref_map']['h']}"),
            ("Tex Alpha", "tex_alpha", f"{m['tex_alpha_map']['w']}x{m['tex_alpha_map']['h']}"),
            ("Water FarLOD", "water_farlod", f"{m['water_farlod']['w']}x{m['water_farlod']['h']}"),
            ("Fog Reference", "fog_ref", f"{m['fog_ref_map']['w']}x{m['fog_ref_map']['h']}"),
            ("Flower/Grass", "flower_grass", f"{m['flower_grass']['w']}x{m['flower_grass']['h']}"),
            ("Stamp Map", "stamp_map", f"{m['stamp_map']['w']}x{m['stamp_map']['h']}"),
            ("EAX Map", "eax_map", f"{m['eax_map']['w']}x{m['eax_map']['h']}"),
            ("Passable", "passable", f"{m['passable']['w']}x{m['passable']['h']}"),
            ("Disabled", "disabled", f"{m['disabled']['w']}x{m['disabled']['h']}"),
            ("Interiors", "interiors", f"{m['interiors']['w']}x{m['interiors']['h']}"),
        ]
        for label, key, sz in map_items:
            t = self.tree.insert(maps_node, "end", text=f"  {label}  ({sz})")
            self.tree_map[t] = ("map_preview", key, label)
        # Water Pools
        t = self.tree.insert("", "end", text=f"\U0001f30a  Water Pools ({len(m['water_pools'])})"); self.tree_map[t] = ("water",)
        # Textures
        t = self.tree.insert("", "end", text=f"\U0001f3a8  Textures ({len(m['textures_stamps'])})"); self.tree_map[t] = ("textures",)
        # 3D Objects
        t = self.tree.insert("", "end", text=f"\U0001f332  3D Objects ({len(m['objects'])})"); self.tree_map[t] = ("objects",)
        # Fog
        t = self.tree.insert("", "end", text=f"\U0001f32b  Fog ({len(m['fogs'])})"); self.tree_map[t] = ("fogs",)
        # Plaintext
        t = self.tree.insert("", "end", text=f"\U0001f4e6  Entities ({len(m['plaintext_objects'])})"); self.tree_map[t] = ("plaintext",)

    def _on_select(self, event):
        sel = self.tree.selection()
        if not sel: return
        info = self.tree_map.get(sel[0])
        if not info: return
        try:
            k = info[0]
            if k == "info": self._show_info()
            elif k == "markers": self._show_markers()
            elif k == "sky": self._show_sky()
            elif k == "water": self._show_water()
            elif k == "textures": self._show_textures()
            elif k == "objects": self._show_objects()
            elif k == "fogs": self._show_fogs()
            elif k == "plaintext": self._show_plaintext()
            elif k == "map_preview": self._show_map_preview(info[1], info[2])
        except Exception as e:
            print(f"View error: {e}"); import traceback; traceback.print_exc()

    # ---- SHARED ----
    def _clear(self):
        self._photo_refs.clear()
        for w in self.detail.winfo_children(): w.destroy()

    def _scrollable(self):
        canvas = tk.Canvas(self.detail, bg=BG, highlightthickness=0, bd=0)
        sb = ttk.Scrollbar(self.detail, orient="vertical", command=canvas.yview)
        frame = tk.Frame(canvas, bg=BG)
        frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y"); canvas.pack(fill="both", expand=True)
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(-1*(e.delta//120), "units"))
        return canvas, frame

    def _hdr(self, text, color=FG):
        h = tk.Frame(self.detail, bg=BG3, padx=12, pady=8); h.pack(fill="x")
        tk.Label(h, text=text, font=("Segoe UI", 13, "bold"), bg=BG3, fg=color).pack(anchor="w")
        return h

    def _prop(self, frame, label, val, color=FG, fs=None):
        fs = fs or self.font_size
        row = tk.Frame(frame, bg=BG); row.pack(fill="x", padx=16, pady=1)
        tk.Label(row, text=f"{label}:", font=("Segoe UI", fs-1), bg=BG, fg=FG_DIM,
                 width=20, anchor="e").pack(side="left")
        tk.Label(row, text=str(val), font=("Consolas", fs-1), bg=BG, fg=color).pack(side="left", padx=8)

    # ---- VIEWS ----
    def _show_welcome(self):
        self._clear()
        f = tk.Frame(self.detail, bg=BG); f.pack(expand=True)
        tk.Label(f, text="TW1 LND Map Editor", font=("Segoe UI", 20, "bold"), bg=BG, fg=FG).pack(pady=(40, 8))
        tk.Label(f, text="Two Worlds 1 Map File — View / Edit / Import / Export", font=("Segoe UI", 12), bg=BG, fg=FG_DIM).pack()
        tk.Label(f, text="Import & export maps as PNG • Swap heightmaps, color maps, etc. • Save modified LND",
                 font=("Segoe UI", 11), bg=BG, fg=CYAN).pack(pady=(4, 8))
        tk.Label(f, text="Select a map layer in the tree, then use Import PNG to replace it",
                 font=("Segoe UI", 10), bg=BG, fg=ORANGE).pack(pady=(0, 20))

    def _show_stats(self):
        self._show_info()

    def _show_info(self):
        self._clear(); m = self.m; fs = self.font_size
        self._hdr(f"\U0001f5fa  {m['map_name']}", GREEN)
        _, frame = self._scrollable()
        self._prop(frame, "Map Name", m["map_name"], GREEN)
        self._prop(frame, "Map Size", f"{m['width']}x{m['height']} tiles")
        self._prop(frame, "Underground", "Yes" if m["underground"] else "No",
                   RED if m["underground"] else GREEN)
        self._prop(frame, "GUID", m["_guid"].hex(), FG_DIM)
        tk.Frame(frame, bg=FG_DIM, height=1).pack(fill="x", padx=16, pady=8)
        tk.Label(frame, text="Adjacent Maps:", font=("Segoe UI", fs, "bold"),
                 bg=BG, fg=FG).pack(anchor="w", padx=16)
        dirs = {"upper": "Upper (Above)", "lower": "Lower (Under)",
                "left": "West", "right": "East", "down": "South", "up": "North"}
        for k, label in dirs.items():
            v = m.get(k, "")
            self._prop(frame, label, v if v else "(none)", CYAN if v else FG_DIM)
        tk.Frame(frame, bg=FG_DIM, height=1).pack(fill="x", padx=16, pady=8)
        tk.Label(frame, text="Data Sections:", font=("Segoe UI", fs, "bold"),
                 bg=BG, fg=FG).pack(anchor="w", padx=16)
        sections = [
            ("Markers", len(m["markers"])),
            ("Sky States", len(m["sky_states"])),
            ("Water Pools", len(m["water_pools"])),
            ("3D Objects", len(m["objects"])),
            ("Fog Descriptions", len(m["fogs"])),
            ("Textures & Stamps", len(m["textures_stamps"])),
            ("Plaintext Entities", len(m["plaintext_objects"])),
            ("Heightmap", f"{m['heightmap']['w']}x{m['heightmap']['h']}"),
            ("Color Base", f"{m['color_base']['w']}x{m['color_base']['h']}"),
        ]
        for label, val in sections:
            self._prop(frame, label, val, ORANGE)

    def _show_markers(self):
        self._clear(); m = self.m; fs = self.font_size
        self._hdr(f"\U0001f4cd  Markers ({len(m['markers'])})", ORANGE)
        _, frame = self._scrollable()
        from collections import Counter
        types = Counter(mk["name"] for mk in m["markers"])
        tk.Label(frame, text="Types:", font=("Segoe UI", fs, "bold"),
                 bg=BG, fg=FG).pack(anchor="w", padx=16, pady=(8, 4))
        for name, cnt in types.most_common():
            self._prop(frame, name, f"{cnt}x", CYAN)
        tk.Frame(frame, bg=FG_DIM, height=1).pack(fill="x", padx=16, pady=8)
        for i, mk in enumerate(m["markers"]):
            bg = BG2 if i % 2 == 0 else BG
            row = tk.Frame(frame, bg=bg, padx=10, pady=3); row.pack(fill="x", padx=4)
            tk.Label(row, text=f"[{i}] {mk['name']} #{mk['instance']}",
                     font=("Consolas", fs-2), bg=bg, fg=ORANGE).pack(side="left")
            tk.Label(row, text=f"({mk['x']}, {mk['y']}, {mk['z']})",
                     font=("Consolas", fs-2), bg=bg, fg=FG_DIM).pack(side="left", padx=8)

    def _show_sky(self):
        self._clear(); m = self.m; fs = self.font_size
        self._hdr("\u2600  Sky & Weather", YELLOW)
        _, frame = self._scrollable()
        self._prop(frame, "Day Length", f"{m['day_length']} minutes", CYAN)
        self._prop(frame, "Sunrise State", m["sunrise_state"], ORANGE)
        self._prop(frame, "Sunset State", m["sunset_state"], PINK)
        tk.Frame(frame, bg=FG_DIM, height=1).pack(fill="x", padx=16, pady=8)
        tk.Label(frame, text=f"Skybox Textures ({len(m['skybox_textures'])}):",
                 font=("Segoe UI", fs, "bold"), bg=BG, fg=FG).pack(anchor="w", padx=16)
        for i, t in enumerate(m["skybox_textures"]):
            self._prop(frame, f"[{i}]", t, CYAN if t else FG_DIM)
        tk.Frame(frame, bg=FG_DIM, height=1).pack(fill="x", padx=16, pady=8)
        tk.Label(frame, text=f"Sky States ({len(m['sky_states'])}):",
                 font=("Segoe UI", fs, "bold"), bg=BG, fg=FG).pack(anchor="w", padx=16)
        for i, ss in enumerate(m["sky_states"]):
            sf = tk.Frame(frame, bg=BG2, padx=10, pady=6); sf.pack(fill="x", padx=12, pady=2)
            tk.Label(sf, text=f"State {i}: time={ss['state']:.0f}",
                     font=("Segoe UI", fs, "bold"), bg=BG2, fg=YELLOW).pack(anchor="w")
            def _rgb_str(c): return f"({c[0]:.2f}, {c[1]:.2f}, {c[2]:.2f})"
            for k in ["ambient", "diffuse", "fog_color", "sky_color", "rain_color", "snow_color"]:
                tk.Label(sf, text=f"  {k}: {_rgb_str(ss[k])}", font=("Consolas", fs-2),
                         bg=BG2, fg=FG_DIM).pack(anchor="w")

    def _show_water(self):
        self._clear(); m = self.m; fs = self.font_size
        self._hdr(f"\U0001f30a  Water Pools ({len(m['water_pools'])})", BLUE)
        _, frame = self._scrollable()
        if not m["water_pools"]:
            tk.Label(frame, text="No water pools on this map tile.",
                     font=("Segoe UI", fs), bg=BG, fg=FG_DIM).pack(padx=16, pady=20)
            return
        for i, wp in enumerate(m["water_pools"]):
            sf = tk.Frame(frame, bg=BG2, padx=10, pady=6); sf.pack(fill="x", padx=12, pady=2)
            flags = []
            if wp["is_lava"]: flags.append("LAVA")
            if wp["is_rain"]: flags.append("RAIN")
            if wp["liquid_lightning"]: flags.append("LIGHTNING")
            tk.Label(sf, text=f"Pool [{i}] {' | '.join(flags)}" if flags else f"Pool [{i}]",
                     font=("Segoe UI", fs, "bold"), bg=BG2, fg=RED if wp["is_lava"] else BLUE).pack(anchor="w")
            self._prop(sf, "Height", wp["height"])
            self._prop(sf, "Bounds", f"({wp['min_x']},{wp['min_y']})-({wp['max_x']},{wp['max_y']})")
            self._prop(sf, "Flow", f"dir={wp['flow_dir']:.1f} speed={wp['flow_speed']:.1f}")

    def _show_textures(self):
        self._clear(); m = self.m; fs = self.font_size
        self._hdr(f"\U0001f3a8  Textures & Stamps ({len(m['textures_stamps'])})", PURPLE)
        _, frame = self._scrollable()
        labels = {0: "Terrain", 16: "Grass/Flora", 24: "Lava", 28: "Stamps"}
        for i, t in enumerate(m["textures_stamps"]):
            section = ""
            for idx, lbl in labels.items():
                if i == idx: section = lbl
            if section:
                tk.Label(frame, text=f"— {section} —", font=("Segoe UI", fs-1, "bold"),
                         bg=BG, fg=YELLOW).pack(anchor="w", padx=16, pady=(8, 2))
            bg = BG2 if i % 2 == 0 else BG
            row = tk.Frame(frame, bg=bg, padx=10, pady=2); row.pack(fill="x", padx=4)
            tk.Label(row, text=f"[{i:2d}]", font=("Consolas", fs-2), bg=bg, fg=FG_DIM).pack(side="left")
            tk.Label(row, text=t, font=("Consolas", fs-1), bg=bg, fg=FG).pack(side="left", padx=8)

    def _show_objects(self):
        self._clear(); m = self.m; fs = self.font_size
        self._hdr(f"\U0001f332  3D Objects ({len(m['objects'])})", GREEN)
        _, frame = self._scrollable()
        from collections import Counter
        types = Counter(o["name"] for o in m["objects"])
        tk.Label(frame, text="Object types:", font=("Segoe UI", fs, "bold"),
                 bg=BG, fg=FG).pack(anchor="w", padx=16, pady=(8, 4))
        mx = types.most_common(1)[0][1] if types else 1
        for name, cnt in types.most_common():
            row = tk.Frame(frame, bg=BG); row.pack(fill="x", padx=16, pady=1)
            tk.Label(row, text=name, font=("Consolas", fs-2), bg=BG, fg=ORANGE,
                     width=22, anchor="e").pack(side="left")
            bw = max(4, int(200 * cnt / mx))
            bar = tk.Frame(row, bg=GREEN, height=14, width=bw)
            bar.pack(side="left", padx=(8, 4)); bar.pack_propagate(False)
            tk.Label(row, text=str(cnt), font=("Segoe UI", fs-2, "bold"),
                     bg=BG, fg=GREEN).pack(side="left")

    def _show_fogs(self):
        self._clear(); m = self.m; fs = self.font_size
        self._hdr(f"\U0001f32b  Fog Descriptions ({len(m['fogs'])})", BLUE)
        _, frame = self._scrollable()
        if not m["fogs"]:
            tk.Label(frame, text="No fog on this tile.", font=("Segoe UI", fs),
                     bg=BG, fg=FG_DIM).pack(padx=16, pady=20)
            return
        for i, fg in enumerate(m["fogs"]):
            self._prop(frame, f"Fog [{i}]",
                f"level={fg['level']} offset={fg['offset']} color=({fg['r']},{fg['g']},{fg['b']},{fg['a']})",
                CYAN)

    def _show_plaintext(self):
        self._clear(); m = self.m; fs = self.font_size
        h = self._hdr(f"\U0001f4e6  Plaintext Entities ({len(m['plaintext_objects'])})", CYAN)
        _, frame = self._scrollable()
        from collections import Counter
        types = Counter()
        for o in m["plaintext_objects"]:
            parts = o.split()
            if len(parts) >= 2: types[parts[1]] += 1
        tk.Label(frame, text="Entity types:", font=("Segoe UI", fs, "bold"),
                 bg=BG, fg=FG).pack(anchor="w", padx=16, pady=(8, 4))
        for name, cnt in types.most_common(20):
            self._prop(frame, name, f"{cnt}x", ORANGE)
        tk.Frame(frame, bg=FG_DIM, height=1).pack(fill="x", padx=16, pady=8)
        for i, o in enumerate(m["plaintext_objects"][:200]):
            bg = BG2 if i % 2 == 0 else BG
            row = tk.Frame(frame, bg=bg, padx=8, pady=1); row.pack(fill="x", padx=4)
            tk.Label(row, text=o[:120], font=("Consolas", fs-2), bg=bg, fg=FG).pack(anchor="w")
        if len(m["plaintext_objects"]) > 200:
            tk.Label(frame, text=f"... +{len(m['plaintext_objects'])-200} more",
                     font=("Segoe UI", fs-1), bg=BG, fg=FG_DIM).pack(pady=8)

    def _show_map_preview(self, key, label):
        """Show map preview with export and import buttons."""
        self._clear(); m = self.m; fs = self.font_size
        # Map key to export function
        export_map = {
            "heightmap": export_heightmap, "color_base": export_color_base,
            "tex_ref": export_tex_ref, "tex_alpha": export_tex_alpha,
            "water_farlod": export_water_farlod, "fog_ref": export_fog_ref,
            "flower_grass": export_flower_grass, "stamp_map": export_stamp_map,
            "eax_map": export_eax, "passable": export_passable,
            "disabled": export_disabled, "interiors": export_interiors,
        }
        # Map key to import function
        import_map = {
            "heightmap": import_heightmap, "color_base": import_color_base,
            "tex_ref": import_tex_ref, "tex_alpha": import_tex_alpha,
            "water_farlod": import_water_farlod, "fog_ref": import_fog_ref,
            "flower_grass": import_flower_grass, "stamp_map": import_stamp_map,
            "eax_map": import_eax, "passable": import_passable,
            "disabled": import_disabled, "interiors": import_interiors,
        }
        # Map key to data key
        data_map = {
            "heightmap": "heightmap", "color_base": "color_base",
            "tex_ref": "tex_ref_map", "tex_alpha": "tex_alpha_map",
            "water_farlod": "water_farlod", "fog_ref": "fog_ref_map",
            "flower_grass": "flower_grass", "stamp_map": "stamp_map",
            "eax_map": "eax_map", "passable": "passable",
            "disabled": "disabled", "interiors": "interiors",
        }
        dk = data_map.get(key, key)
        info = m.get(dk, {})
        w = info.get("w", 0); h = info.get("h", 0)
        data_sz = len(info.get("data", b""))

        hdr = self._hdr(f"\U0001f5bc  {label}  ({w}x{h})", PURPLE)
        tk.Label(hdr, text=f"{data_sz:,} bytes", font=("Segoe UI", 9), bg=BG3, fg=FG_DIM).pack(anchor="w")

        def _export():
            p = filedialog.asksaveasfilename(title=f"Export {label}",
                defaultextension=".png", initialfile=f"{m['map_name']}_{label}.png",
                filetypes=[("PNG", "*.png")])
            if not p: return
            fn = export_map.get(key)
            if fn:
                try:
                    fn(m, p)
                    self.status_lbl.config(text=f"Exported: {os.path.basename(p)}")
                except Exception as e:
                    messagebox.showerror("Export Error", str(e))

        def _import():
            p = filedialog.askopenfilename(title=f"Import {label} from PNG",
                filetypes=[("PNG", "*.png"), ("All images", "*.png;*.bmp;*.tga;*.tiff")])
            if not p: return
            fn = import_map.get(key)
            if not fn:
                messagebox.showwarning("Import", f"Import not supported for {label}")
                return
            try:
                fn(m, p)
                self._mark_modified()
                self.status_lbl.config(text=f"Imported {label} from {os.path.basename(p)}")
                # Refresh preview
                self._show_map_preview(key, label)
            except Exception as e:
                messagebox.showerror("Import Error", str(e))

        btn_frame = tk.Frame(hdr, bg=BG3)
        btn_frame.pack(side="right")
        tk.Button(btn_frame, text="Import PNG", bg=ORANGE, fg="#000",
                  font=("Segoe UI", 9, "bold"), bd=0, padx=10,
                  command=_import).pack(side="right", padx=4)
        tk.Button(btn_frame, text="Export PNG", bg=PURPLE, fg="#fff",
                  font=("Segoe UI", 9, "bold"), bd=0, padx=10,
                  command=_export).pack(side="right")

        if not HAS_PIL or w == 0 or h == 0:
            tk.Label(self.detail, text="No preview (Pillow required or empty map)",
                     font=("Segoe UI", 12), bg=BG, fg=FG_DIM).pack(expand=True)
            return

        # Generate preview
        try:
            fn = export_map.get(key)
            if not fn: return
            import tempfile
            tmp = os.path.join(tempfile.gettempdir(), f"_lnd_preview_{key}.png")
            img = fn(m, tmp)
            if not img: return
            # Scale for display
            max_dim = 500
            scale = min(max_dim / img.width, max_dim / img.height, 4.0)
            dw, dh = int(img.width * scale), int(img.height * scale)
            if img.mode == "I" or img.mode == "I;16":
                arr = np.array(img)
                if arr.dtype == np.uint16:
                    arr8 = (arr / 256).astype(np.uint8)
                else:
                    mn, mx = arr.min(), arr.max()
                    arr8 = ((arr - mn) / max(mx - mn, 1) * 255).astype(np.uint8)
                display = Image.fromarray(arr8, mode="L").resize((dw, dh), Image.NEAREST)
            else:
                display = img.convert("RGBA").resize((dw, dh), Image.NEAREST)
            photo = ImageTk.PhotoImage(display)
            self._photo_refs.append(photo)
            canvas = tk.Canvas(self.detail, bg=BG, highlightthickness=0,
                              width=dw, height=dh)
            canvas.pack(padx=20, pady=10)
            canvas.create_image(0, 0, anchor="nw", image=photo)
            os.remove(tmp)
        except Exception as e:
            tk.Label(self.detail, text=f"Preview error: {e}",
                     font=("Segoe UI", 10), bg=BG, fg=RED).pack(pady=20)

if __name__ == "__main__":
    App()
