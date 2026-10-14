#!/usr/bin/env python3
"""Generate Extra Trims armor-trim textures.

Armor trim textures must use only the eight greys of the vanilla
``trims/color_palettes/trim_palette.png`` key, because the armor_trims atlas
recolours them per trim material via ``paletted_permutations``. Any other
colour simply will not be remapped, so the art here is authored in tones,
never in colour -- the trim material supplies that at runtime.

Most patterns are hand-authored pixel art, written as one small bitmap per
kind of armour face and painted into the standard UV boxes. A pattern may
instead supply a function of (face, u, v, fw, fh) when it is a repeating
texture rather than a drawn figure.

Everything is finally masked against the real vanilla armour footprint, so
no pixel can land off-model.

Usage:
    python3 tools/generate_textures.py --masks <dir with vanilla textures>
"""

import argparse
import os

from PIL import Image

# trim_palette.png, lightest first. Index i of this ramp is recoloured to
# index i of the trim material's palette, so using several steps is what gives
# a single trim its light and shade -- gold runs #fffd90 down to #572300.
RAMP = [224, 192, 160, 128, 96, 64, 32, 0]

# Explicit tones usable in art: '#' means "shade this automatically", while a
# digit pins a step of the ramp.
TONES = {"4": 224, "3": 192, "2": 160, "1": 128, "0": 96}
T4, T3, T2, T1, T0 = 224, 192, 160, 128, 96

# Keep off the last two steps: on already-dark materials such as netherite
# they are close enough to black that the trim stops reading.
DEEPEST = 5

W, H = 64, 32

# Standard armour UV boxes: name -> (x, y, w, h)
HUMANOID_FACES = {
    "helm_top":   (8, 0, 8, 8),
    "helm_right": (0, 8, 8, 8),
    "helm_front": (8, 8, 8, 8),
    "helm_left":  (16, 8, 8, 8),
    "helm_back":  (24, 8, 8, 8),
    "boot_sole":  (8, 16, 4, 4),
    "leg_right":  (0, 20, 4, 12),
    "leg_front":  (4, 20, 4, 12),
    "leg_left":   (8, 20, 4, 12),
    "leg_back":   (12, 20, 4, 12),
    "body_right": (16, 20, 4, 12),
    "body_front": (20, 20, 8, 12),
    "body_left":  (28, 20, 4, 12),
    "body_back":  (32, 20, 8, 12),
    "arm_top":    (44, 16, 4, 4),
    "arm_right":  (40, 20, 4, 12),
    "arm_front":  (44, 20, 4, 12),
    "arm_left":   (48, 20, 4, 12),
    "arm_back":   (52, 20, 4, 12),
}

LEGGINGS_FACES = {
    "leg_top":    (4, 16, 4, 4),
    "leg_right":  (0, 20, 4, 12),
    "leg_front":  (4, 20, 4, 12),
    "leg_left":   (8, 20, 4, 12),
    "leg_back":   (12, 20, 4, 12),
    "body_right": (16, 20, 4, 12),
    "body_front": (20, 20, 8, 12),
    "body_left":  (28, 20, 4, 12),
    "body_back":  (32, 20, 8, 12),
}

# Which art bitmap each face draws, and which rows of it to take.
# The 4x4 cap faces borrow a slice of the limb they belong to.
FACE_ART = {
    "helm_top":   ("helm_top", 0),
    "helm_right": ("helm", 0),
    "helm_front": ("helm", 0),
    "helm_left":  ("helm", 0),
    "helm_back":  ("helm", 0),
    "body_front": ("body", 0),
    "body_back":  ("body", 0),
    "body_right": ("side", 0),
    "body_left":  ("side", 0),
    "arm_top":    ("arm", 0),
    "arm_right":  ("arm", 0),
    "arm_front":  ("arm", 0),
    "arm_left":   ("arm", 0),
    "arm_back":   ("arm", 0),
    "boot_sole":  ("leg", 8),
    "leg_top":    ("leg", 0),
    "leg_right":  ("leg", 0),
    "leg_front":  ("leg", 0),
    "leg_left":   ("leg", 0),
    "leg_back":   ("leg", 0),
}

# If a pattern omits a bitmap, fall back to one it does define.
ART_FALLBACK = {"helm_top": "helm", "side": "arm"}


# --- ember keeps its procedural motif -------------------------------------

def ember(face, u, v, fw, fh):
    """Flecks banked at the hem, guttering out towards the shoulders."""
    h = (u * 7 + v * 13) % 11
    if v >= 10:
        threshold = 7
    elif v >= 7:
        threshold = 5
    elif v >= 4:
        threshold = 3
    else:
        threshold = 1
    if h >= threshold:
        return None
    # Embers cool as they settle: deeper steps towards the hem, with the odd
    # bright fleck left glowing.
    return RAMP[min(DEEPEST, v // 3 + (0 if h == 0 else 1))]


# How each pattern is lit. All three keep a trim reading as one design while
# spending several steps of the material's ramp instead of a single flat tone.
#   relief  edges catch the light, undersides fall into shadow
#   strata  each course of the design sits a step deeper than the last
#   depth   a long fade from lit shoulders down to a dark hem
STYLES = {
    "umbra": "relief",
    "totemic": "strata",
    "halo": "relief",
    "keystone": "strata",
    "mosaic": "depth",
    "zenith": "relief",
    "harbor": "relief",
    "runic": "depth",
    "lattice": "strata",
}


def shade(rows, style):
    """Turn a shape into tones. A digit in the art pins its own step."""
    h = len(rows)
    w = len(rows[0]) if h else 0

    def filled(r, c):
        return 0 <= r < h and 0 <= c < w and rows[r][c] != "."

    grid = []
    for r in range(h):
        line = []
        for c in range(w):
            if not filled(r, c):
                line.append(None)
                continue

            ch = rows[r][c]
            if ch in TONES:
                line.append(TONES[ch])
                continue

            lit = not filled(r - 1, c)
            under = not filled(r + 1, c)

            if style == "strata":
                # Clean two-row courses. No edge-lighting here: these designs
                # are built from isolated one-pixel rows, where every pixel is
                # an edge, which would flatten the banding back to one tone.
                idx = r // 2
            elif style == "depth":
                idx = r * 5 // max(1, h)
                if lit:
                    idx = max(0, idx - 1)
            else:  # relief
                idx = 0 if lit else (3 if under else 2)
                idx += r // 4

            line.append(RAMP[min(DEEPEST, idx)])
        grid.append(line)
    return grid


# Visible rows per piece, measured from the vanilla armour footprint:
#   helmet sides v0-4, helmet top v0-7, chestplate v0-10, arms v0-5,
#   leggings legs v0-8, leggings belt v7-11, boots v6-11.
# Art is written for the whole 12-row box; each piece shows its own part, so
# a chest emblem belongs around v3-v8 and arm art past v5 is never drawn.
ART = {
    "umbra": {  # a chunky cross patee, plumed helm, solid boots
        "helm": [
            "...##...",
            "...##...",
            ".######.",
            "...##...",
            "...##...",
        ],
        "helm_top": ["...##..."] * 8,
        "body": [
            "##....##",
            "#......#",
            "...##...",
            "...##...",
            "..####..",
            "########",
            "########",
            "..####..",
            "...##...",
            "..####..",
            "..####..",
            "........",
        ],
        "arm": [
            "....",
            ".##.",
            "#..#",
            "....",
            "....",
            "....",
        ],
        "side": [
            "....",
            "....",
            ".##.",
            ".##.",
            ".##.",
            ".##.",
            ".##.",
            "....",
            "....",
            "....",
            "####",
            "....",
        ],
        "leg": [
            "####",
            "....",
            "....",
            "....",
            "....",
            "....",
            ".##.",
            ".##.",
            ".##.",
            ".##.",
            "####",
            "####",
        ],
    },
    "totemic": {  # a long tapering stack with a bold wing bar
        "helm": [
            "..####..",
            ".##..##.",
            "........",
            "..####..",
            ".##..##.",
        ],
        "body": [
            "##....##",
            "#......#",
            "..####..",
            ".##..##.",
            "..####..",
            "########",
            "..####..",
            ".##..##.",
            "..####..",
            ".######.",
            "..####..",
            "........",
        ],
        "arm": [
            "####",
            "####",
            "#...",
            "....",
            "....",
            "....",
        ],
        "leg": [
            ".##.",
            "#..#",
            "....",
            ".##.",
            "#..#",
            "....",
            ".##.",
            "#..#",
            "....",
            ".##.",
            "####",
            "####",
        ],
    },
    "halo": {  # a shallow arch over a triangular tent, crowned helm
        "helm": [
            "########",
            ".#.##.#.",
            "........",
            "........",
            "........",
        ],
        "body": [
            "##....##",
            "#......#",
            "..####..",
            ".#....#.",
            "#......#",
            "...##...",
            "..#..#..",
            ".#....#.",
            "########",
            ".######.",
            "..#..#..",
            "........",
        ],
        "arm": [
            "....",
            "....",
            "####",
            "....",
            "....",
            "....",
        ],
        "leg": [
            "....",
            "####",
            "....",
            "....",
            "....",
            "....",
            ".##.",
            "####",
            "....",
            ".##.",
            "####",
            "####",
        ],
    },
    "keystone": {  # dense masonry blocks, bracketed shoulders
        "helm": [
            "#..#..#.",
            ".##..##.",
            "........",
            ".##..##.",
            "#..##..#",
        ],
        "body": [
            "##....##",
            "##....##",
            ".##..##.",
            "#..##..#",
            ".##..##.",
            "........",
            ".##..##.",
            "#..##..#",
            ".##..##.",
            ".#.##.#.",
            "..####..",
            "........",
        ],
        "arm": [
            "####",
            "##..",
            "##..",
            "####",
            "....",
            "....",
        ],
        "leg": [
            ".##.",
            "#..#",
            ".##.",
            "....",
            ".##.",
            "#..#",
            ".##.",
            "....",
            ".##.",
            "#..#",
            ".##.",
            "....",
        ],
    },
    "mosaic": {  # a centred vertical stack of tiles
        "helm": [
            "#......#",
            "........",
            "..####..",
            ".#....#.",
            "........",
        ],
        "body": [
            "##....##",
            "#......#",
            "..####..",
            ".#....#.",
            "..####..",
            "........",
            ".######.",
            "..#..#..",
            ".######.",
            "..####..",
            "..####..",
            "........",
        ],
        "arm": [
            "....",
            "....",
            "####",
            "....",
            "....",
            "....",
        ],
        "leg": [
            "..#.",
            ".##.",
            "....",
            "####",
            ".##.",
            "....",
            "####",
            ".##.",
            "....",
            "####",
            "####",
            ".##.",
        ],
    },
    "zenith": {  # a long thin cross with a single crossbar
        "helm": [
            ".#.##.#.",
            "#.#..#.#",
            "........",
            "........",
            "........",
        ],
        "body": [
            "##....##",
            "#......#",
            "...##...",
            "...##...",
            "...##...",
            ".######.",
            "...##...",
            "...##...",
            "...##...",
            "...##...",
            "...##...",
            "........",
        ],
        "arm": [
            "....",
            "####",
            "....",
            "....",
            "....",
            "....",
        ],
        "leg": [
            "....",
            "....",
            ".##.",
            ".##.",
            ".##.",
            ".##.",
            ".##.",
            ".##.",
            ".##.",
            ".##.",
            "####",
            "....",
        ],
    },
    "harbor": {  # a mast with two spars widening downward
        "helm": [
            "...##...",
            "...##...",
            "...##...",
            "...##...",
            "...##...",
        ],
        "body": [
            "##....##",
            "#......#",
            "...##...",
            "..####..",
            "...##...",
            "...##...",
            ".######.",
            "...##...",
            "########",
            ".######.",
            "..####..",
            "........",
        ],
        "arm": [
            "....",
            "####",
            "....",
            "####",
            "....",
            "....",
        ],
        "leg": [
            "....",
            ".##.",
            ".##.",
            ".##.",
            "####",
            ".##.",
            ".##.",
            ".##.",
            "....",
            "####",
            "####",
            "....",
        ],
    },
    "runic": {  # nested arches under bold shoulder bars
        "helm": [
            "##....##",
            "...##...",
            "........",
            "..####..",
            ".#....#.",
        ],
        "body": [
            "##....##",
            "#......#",
            "...##...",
            "..####..",
            ".#....#.",
            "........",
            "..####..",
            ".#....#.",
            "#......#",
            "..####..",
            "..####..",
            "........",
        ],
        "arm": [
            "####",
            "####",
            "....",
            "....",
            "....",
            "....",
        ],
        "leg": [
            "....",
            ".##.",
            "#..#",
            "....",
            ".##.",
            "#..#",
            "....",
            ".##.",
            "#..#",
            "....",
            ".##.",
            "####",
        ],
    },
    "lattice": {  # zigzag rows with hollow shoulder rings
        "helm": [
            ".#.##.#.",
            "#.#..#.#",
            "........",
            ".#.##.#.",
            "#.#..#.#",
        ],
        "body": [
            "##....##",
            "#......#",
            ".#.##.#.",
            "#.#..#.#",
            "........",
            ".#.##.#.",
            "#.#..#.#",
            "........",
            "########",
            ".#.##.#.",
            "..####..",
            "........",
        ],
        "arm": [
            "####",
            "#..#",
            "#..#",
            "####",
            "....",
            "....",
        ],
        "leg": [
            ".##.",
            "#..#",
            "....",
            ".##.",
            "#..#",
            "....",
            ".##.",
            "#..#",
            "....",
            "####",
            ".##.",
            "....",
        ],
    },
}

# Draw order is the order patterns appear everywhere else.
PATTERN_ORDER = [
    "ember", "umbra", "totemic", "halo", "keystone",
    "mosaic", "zenith", "harbor", "runic", "lattice",
]

FUNCTIONS = {"ember": ember}


def art_motif(art, style):
    """Turn a dict of per-face bitmaps into a motif function, shaded."""
    shaded = {key: shade(rows, style) for key, rows in art.items()}

    def motif(face, u, v, fw, fh):
        key, offset = FACE_ART[face]
        grid = shaded.get(key)

        while grid is None and key in ART_FALLBACK:
            key = ART_FALLBACK[key]
            grid = shaded.get(key)

        if grid is None:
            return None

        row = v + offset
        if not 0 <= row < len(grid):
            return None

        if not 0 <= u < len(grid[row]):
            return None

        return grid[row][u]

    return motif


def motif_for(name):
    if name in FUNCTIONS:
        return FUNCTIONS[name]
    return art_motif(ART[name], STYLES[name])


def check_art():
    """Every bitmap row must match the width of the faces that use it."""
    widths = {"helm": 8, "helm_top": 8, "body": 8, "side": 4, "arm": 4, "leg": 4}
    problems = []
    for name, art in ART.items():
        for key, rows in art.items():
            want = widths[key]
            for i, row in enumerate(rows):
                if len(row) != want:
                    problems.append(f"{name}.{key}[{i}] is {len(row)} wide, expected {want}")
                for ch in row:
                    if ch not in (".", "#") and ch not in TONES:
                        problems.append(f"{name}.{key}[{i}] has unknown tone {ch!r}")
    if problems:
        raise SystemExit("art errors:\n  " + "\n  ".join(problems))


def load_mask(path):
    im = Image.open(path).convert("RGBA")
    if im.size != (W, H):
        raise SystemExit(f"unexpected mask size {im.size} for {path}")
    px = im.load()
    return {(x, y) for y in range(H) for x in range(W) if px[x, y][3] > 0}


def render(motif, faces, mask):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = im.load()
    for face, (fx, fy, fw, fh) in faces.items():
        for v in range(fh):
            for u in range(fw):
                x, y = fx + u, fy + v
                if (x, y) not in mask:
                    continue
                tone = motif(face, u, v, fw, fh)
                if tone is not None:
                    px[x, y] = (tone, tone, tone, 255)
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--masks", required=True,
                    help="directory holding assets/minecraft/textures/entity/equipment/")
    ap.add_argument("--out", default="src/main/resources/assets/extratrims/textures")
    args = ap.parse_args()

    check_art()

    eq = os.path.join(args.masks, "assets/minecraft/textures/entity/equipment")
    masks = {
        "humanoid": load_mask(os.path.join(eq, "humanoid/iron.png")),
        "humanoid_leggings": load_mask(os.path.join(eq, "humanoid_leggings/iron.png")),
    }
    faces = {"humanoid": HUMANOID_FACES, "humanoid_leggings": LEGGINGS_FACES}

    for name in PATTERN_ORDER:
        motif = motif_for(name)
        counts = []
        for layer in ("humanoid", "humanoid_leggings"):
            im = render(motif, faces[layer], masks[layer])
            out_dir = os.path.join(args.out, "trims/entity", layer)
            os.makedirs(out_dir, exist_ok=True)
            im.save(os.path.join(out_dir, f"{name}.png"))
            counts.append(sum(1 for p in im.get_flattened_data() if p[3] > 0))
        print(f"{name:9} humanoid {counts[0]:4} px ({counts[0] / 648 * 100:3.0f}%)"
              f"   leggings {counts[1]:4} px")


if __name__ == "__main__":
    main()
