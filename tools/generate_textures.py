#!/usr/bin/env python3
"""Generate Extra Trims armor-trim and smithing-template textures.

Armor trim textures must use only the eight greys of the vanilla
``trims/color_palettes/trim_palette.png`` key, because the armor_trims atlas
recolours them per trim material via ``paletted_permutations``. Any other
colour simply will not be remapped.

Motifs are authored in face-local coordinates (u, v) of the standard armour
UV boxes and then masked against the real vanilla armour footprint, so no
pixel can land off-model.

Usage:
    python3 tools/generate_textures.py --masks <dir with vanilla textures>
"""

import argparse
import os

from PIL import Image

# trim_palette.png, darkest-last. Index 0 is the highlight.
T4, T3, T2, T1, T0 = 224, 192, 160, 128, 96
DARK = 64

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


# Every armour UV face is 4 or 8 pixels wide, so motifs repeat on a period of
# 4 and tile cleanly on both without clipping into noise at the face seams.
#
# Which rows of a 12-row side face each piece actually shows:
#   helmet  v0-4    chestplate v0-8   arms v0-5
#   boots   v6-11   leggings legs v0-6   leggings belt v7-11
# Bands at v1 / v7 / v10 therefore reach every piece.
COLLAR, WAIST, HEM = 1, 7, 10


def crest(u, v, fw, fh):
    """Chevrons marching around collar and waist."""
    uu = u % 4
    for base in (COLLAR, WAIST):
        if v == base and uu in (1, 2):
            return T4
        if v == base + 1 and uu in (0, 3):
            return T2
    if v == HEM and uu in (1, 2):
        return T3
    return None


def tusk(u, v, fw, fh):
    """Broad blunt banding, the heaviest of the set."""
    uu = u % 4
    for base in (COLLAR, WAIST):
        if v == base and uu != 3:
            return T4
        if v == base + 1 and uu == 1:
            return T1
    if v == HEM and uu != 3:
        return T3
    return None


def thorn(u, v, fw, fh):
    """A rule with barbs biting away from it."""
    uu = u % 4
    if v == COLLAR and uu != 2:
        return T3
    if v == COLLAR + 1 and uu == 0:
        return T4
    if v == WAIST and uu != 2:
        return T3
    if v == WAIST - 1 and uu == 0:
        return T4
    if v == HEM and uu != 2:
        return T2
    return None


def lattice(u, v, fw, fh):
    """Crosshatched diagonals inside narrow bands."""
    for base in (COLLAR, WAIST):
        if base <= v <= base + 1:
            if (u + v) % 4 == 0:
                return T4
            if (u - v) % 4 == 0:
                return T2
    if v == HEM and u % 4 == 0:
        return T2
    return None


def prism(u, v, fw, fh):
    """Faceted rhombi, one row per band."""
    for cy in (COLLAR + 1, WAIST + 1):
        if u % 4 == 1:
            if abs(v - cy) == 1:
                return T4
            if v == cy:
                return T1
        elif u % 4 in (0, 2) and v == cy:
            return T3
    if v == HEM and u % 4 == 1:
        return T2
    return None


def ember(u, v, fw, fh):
    """Guttering flecks that thin out as they rise."""
    h = (u * 7 + v * 13) % 11
    if v == COLLAR and h < 5:
        return T3
    if v == COLLAR + 2 and h < 2:
        return T1
    if v == WAIST and h < 6:
        return T4
    if v == WAIST + 1 and h < 3:
        return T2
    if v == HEM and h < 6:
        return T3
    return None


def weave(u, v, fw, fh):
    """Over-and-under braid."""
    for base in (COLLAR, WAIST):
        if base <= v <= base + 1 and u % 4 != 3:
            return T4 if ((u // 2) + (v - base)) % 2 == 0 else T1
    if v == HEM and u % 4 != 3:
        return T2
    return None


def halo(u, v, fw, fh):
    """Dashed rings with a soft shadow under each."""
    uu = u % 4
    for base in (COLLAR, WAIST):
        if v == base and uu != 3:
            return T4
        if v == base + 1 and uu != 3:
            return T0
    if v == HEM and uu != 3:
        return T2
    return None


PATTERNS = {
    "crest": crest,
    "tusk": tusk,
    "thorn": thorn,
    "lattice": lattice,
    "prism": prism,
    "ember": ember,
    "weave": weave,
    "halo": halo,
}


def load_mask(path):
    im = Image.open(path).convert("RGBA")
    if im.size != (W, H):
        raise SystemExit(f"unexpected mask size {im.size} for {path}")
    px = im.load()
    return {(x, y) for y in range(H) for x in range(W) if px[x, y][3] > 0}


def render(motif, faces, mask):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = im.load()
    for fx, fy, fw, fh in faces.values():
        for v in range(fh):
            for u in range(fw):
                x, y = fx + u, fy + v
                if (x, y) not in mask:
                    continue
                tone = motif(u, v, fw, fh)
                if tone is not None:
                    px[x, y] = (tone, tone, tone, 255)
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--masks", required=True,
                    help="directory holding assets/minecraft/textures/entity/equipment/...")
    ap.add_argument("--out", default="src/main/resources/assets/extratrims/textures")
    ap.add_argument("--preview", action="store_true")
    args = ap.parse_args()

    eq = os.path.join(args.masks, "assets/minecraft/textures/entity/equipment")
    masks = {
        "humanoid": load_mask(os.path.join(eq, "humanoid/iron.png")),
        "humanoid_leggings": load_mask(os.path.join(eq, "humanoid_leggings/iron.png")),
    }
    faces = {"humanoid": HUMANOID_FACES, "humanoid_leggings": LEGGINGS_FACES}

    for name, motif in PATTERNS.items():
        for layer in ("humanoid", "humanoid_leggings"):
            im = render(motif, faces[layer], masks[layer])
            out_dir = os.path.join(args.out, "trims/entity", layer)
            os.makedirs(out_dir, exist_ok=True)
            im.save(os.path.join(out_dir, f"{name}.png"))
            count = sum(1 for p in im.get_flattened_data() if p[3] > 0)
            print(f"{name:8} {layer:18} {count:4} px")
            if args.preview:
                px = im.load()
                for y in range(H):
                    row = "".join(
                        (str(px[x, y][0] // 32) if px[x, y][3] else ".")
                        for x in range(W)
                    )
                    print(f"  {y:3} {row}")


if __name__ == "__main__":
    main()
