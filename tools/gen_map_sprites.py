#!/usr/bin/env python3
"""Generate the level-select map sprites with Google's image model.

Needs GEMINI_API_KEY.  Usage:
    python3 tools/gen_map_sprites.py [name ...]      # default: all

Each sprite is generated on a flat magenta field, background-keyed by flood fill
from the border (so magenta inside the art survives), trimmed to its content and
written to assets/map/<name>.png.
"""
import base64, json, os, sys, urllib.request
from collections import deque
from PIL import Image

MODEL = "gemini-3-pro-image"
KEY = os.environ.get("GEMINI_API_KEY")
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "map")
RAW = os.path.join(OUT, "_raw")

STYLE = (
    "Flat vector game art in a clean modern mobile-game style. Isometric view from "
    "above at a 30 degree angle, 2:1 isometric projection. Solid flat colour fills "
    "with two or three tones per material for shading, soft light from the upper "
    "left, no gradients, no outlines, no texture noise, no grain, no cross-hatching. "
    "Crisp smooth vector edges. A single centred object, complete and not cropped, "
    "with empty space around it. Plain solid magenta #FF00FF background, nothing "
    "else in the scene, no ground plane, no cast shadow, no text, no watermark, "
    "no user interface."
)

CHARACTER_STYLE = (
    "Flat vector game art in a clean modern mobile-game style. A standing character "
    "seen from the front, three quarter view from slightly above, matching an "
    "isometric game board. Solid flat colour fills with two or three tones per "
    "material for shading, soft light from the upper left, no gradients, no "
    "outlines, no texture noise, no grain. Crisp smooth vector edges. Chunky "
    "readable proportions with a slightly large head. A single centred character, "
    "complete and not cropped, full body including feet, with empty space around "
    "it. Plain solid magenta #FF00FF background, nothing else in the scene, no "
    "ground plane, no cast shadow, no text, no watermark, no user interface."
)

CHARACTERS = {"quinn"}

SPRITES = {
    "quinn": "A cheerful young fairy-tale princess standing straight with her arms at her "
             "sides. Long straight chestnut brown hair falling past her shoulders, a small "
             "pointed gold crown on her head. A sleeveless hot pink gown with a white "
             "bodice panel on the chest and a white band around the hem, pale blue cuffs "
             "at her wrists, small red shoes peeking out below the skirt. Simple friendly "
             "face: two small dark dot eyes, a little smile, no nose detail. Warm, kind, "
             "storybook.",
    "log-open": "A round slice of tree trunk used as a stepping stone, seen from above at an "
                "isometric angle. Pale cream and light tan cut face with concentric growth "
                "rings, a chunky dark brown bark side wall about a quarter of the height. "
                "Soft rounded square silhouette. Warm, inviting, freshly cut.",
    "log-cleared": "A round slice of tree trunk used as a stepping stone, seen from above at an "
                "isometric angle. Weathered honey and amber cut face with concentric growth "
                "rings, a chunky dark brown bark side wall about a quarter of the height. "
                "Soft rounded square silhouette. Slightly older and darker than fresh timber.",
    "log-locked": "A block of grey granite used as a stepping stone, seen from above at an "
                "isometric angle. Flat grey chiselled top face with a few facet lines, a "
                "chunky darker grey stone side wall about a quarter of the height. Soft "
                "rounded square silhouette. Cold and inert.",
    "tree-oak": "A stylised broadleaf oak tree. Rounded billowing leaf canopy built from a few "
                "overlapping soft lobes in two or three greens, a short tapered tan-brown "
                "trunk with a slight root flare. Storybook, friendly.",
    "tree-pine": "A stylised conifer pine tree with four tiers of soft triangular branches in "
                "two or three greens and a short brown trunk. Storybook, friendly.",
    "bush": "A small round garden shrub, a few overlapping leafy lobes in two greens, with a "
            "handful of small red berries. Storybook, friendly.",
    "rocks": "A small cluster of three grey boulders of different sizes with flat lit top "
             "facets and darker sides. Storybook, friendly.",
    "pond": "A small oval woodland pond. Blue water in two or three tones with a lighter "
            "shallow rim, a soft green grassy bank around the edge, three lily pads and a "
            "few reeds. Seen from above at an isometric angle.",
    "cabin": "A small wooden log cabin cottage. Stacked log walls in warm tan, a steep shingled "
             "gable roof in brown, a wooden front door, one window, and a stone chimney. "
             "Seen from above at an isometric angle, three quarter view. Storybook, cosy.",
}

def generate(name, prompt):
    style = CHARACTER_STYLE if name in CHARACTERS else STYLE
    body = json.dumps({
        "contents": [{"parts": [{"text": style + "\n\nSubject: " + prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"]},
    }).encode()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={KEY}"
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.load(r)
    for part in data["candidates"][0]["content"]["parts"]:
        if "inlineData" in part:
            return base64.b64decode(part["inlineData"]["data"])
    raise RuntimeError(f"{name}: no image in response: {json.dumps(data)[:400]}")

def key_background(img, tol=60):
    """Flood fill the flat background from the border so magenta inside art survives."""
    img = img.convert("RGBA")
    px = img.load()
    w, h = img.size
    bg = px[0, 0][:3]
    seen = bytearray(w * h)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            q.append((x, y))
    while q:
        x, y = q.popleft()
        i = y * w + x
        if seen[i]:
            continue
        seen[i] = 1
        r, g, b, a = px[x, y]
        if abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2]) > tol:
            continue
        px[x, y] = (r, g, b, 0)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not seen[ny * w + nx]:
                q.append((nx, ny))
    # The model likes to paint a soft cast shadow onto the backdrop, which reads as
    # darkened magenta rather than the exact key colour. Match it by hue — r and b
    # near each other with g well below both — so hot pink artwork survives.
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            if abs(r - b) < 40 and g < min(r, b) * 0.55 and min(r, b) > 60:
                px[x, y] = (r, g, b, 0)

    # soften the keyed fringe: pull remaining background-ish pixels toward transparent
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            d = abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2])
            if d < tol:
                px[x, y] = (r, g, b, 0)
            elif d < tol * 2.2:
                px[x, y] = (r, g, b, int(a * (d - tol) / (tol * 1.2)))
    return img

def bleed(img, passes=3):
    """Push edge colour into the transparent pixels so scaling cannot pull the
    keyed background back in as a fringe."""
    px = img.load()
    w, h = img.size
    for _ in range(passes):
        edits = []
        for y in range(h):
            for x in range(w):
                if px[x, y][3] != 0:
                    continue
                acc, n = [0, 0, 0], 0
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h:
                        r, g, b, a = px[nx, ny]
                        if a > 0:
                            acc[0] += r; acc[1] += g; acc[2] += b; n += 1
                if n:
                    edits.append((x, y, (acc[0] // n, acc[1] // n, acc[2] // n, 0)))
        if not edits:
            break
        for x, y, c in edits:
            px[x, y] = c
    return img

def anchor_of(name, img):
    """Ground contact as a fraction of height: the centre of the top face for the
    stepping stones and the pond, the base of the silhouette for everything else."""
    import numpy as np
    a = np.asarray(img)
    alpha = a[..., 3] > 24
    ys = np.nonzero(alpha.any(1))[0]
    top, bottom = int(ys.min()), int(ys.max())
    if name.startswith("log-"):
        col = a[:, img.width // 2]
        lum = col[..., :3].astype(int).sum(1)
        opaque = np.nonzero(col[..., 3] > 24)[0]
        t = int(opaque.min())
        face = lum[opaque] > lum[opaque].max() * 0.72
        idx = np.nonzero(~face)[0]
        b = int(opaque[idx[0]]) if len(idx) else bottom
        return round(((t + b) / 2) / img.height, 4)
    if name == "pond":
        return round(((top + bottom) / 2) / img.height, 4)
    if name in CHARACTERS:
        return round(bottom / img.height, 4)      # she stands on her feet
    return round((bottom - (bottom - top) * 0.03) / img.height, 4)

def trim(img, pad=6):
    bbox = img.getbbox()
    if not bbox:
        return img
    x0, y0, x1, y1 = bbox
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1, y1 = min(img.width, x1 + pad), min(img.height, y1 + pad)
    return img.crop((x0, y0, x1, y1))

def main():
    if not KEY:
        sys.exit("GEMINI_API_KEY is not set")
    os.makedirs(RAW, exist_ok=True)
    names = sys.argv[1:] or list(SPRITES)
    apath = os.path.join(OUT, "anchors.json")
    anchors = json.load(open(apath)) if os.path.exists(apath) else {}
    for name in names:
        raw = generate(name, SPRITES[name])
        raw_path = os.path.join(RAW, name + ".png")
        with open(raw_path, "wb") as f:
            f.write(raw)
        img = trim(bleed(key_background(Image.open(raw_path))))
        img.save(os.path.join(OUT, name + ".png"))
        anchors[name] = anchor_of(name, img)
        print(f"{name:14s} {img.width}x{img.height}  anchor {anchors[name]}")

    with open(os.path.join(OUT, "anchors.json"), "w") as f:
        json.dump(anchors, f, indent=2)

if __name__ == "__main__":
    main()
