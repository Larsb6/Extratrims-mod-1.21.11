#!/usr/bin/env python3
"""Render a front-on preview of each trim pattern on a full suit of armour.

This performs the same palette swap the armor_trims atlas does at runtime
(every grey of trim_palette.png is mapped to the matching index of the trim
material's palette), then composites the front faces of the armour UV boxes
into a player-shaped view. It is a preview tool, not part of the mod.
"""

import argparse
import os

from PIL import Image, ImageDraw

PATTERNS = ["crest", "tusk", "thorn", "lattice", "prism", "ember", "weave", "halo"]

# Front faces: (src_x, src_y, w, h) -> (dst_x, dst_y) in a 16x32 front view.
# "mirror" duplicates the right limb as the left one, as the model does.
FRONT = [
    ("humanoid", (8, 8, 8, 8), (4, 0), False),    # helmet
    ("humanoid", (20, 20, 8, 12), (4, 8), False),  # chestplate body
    ("humanoid", (44, 20, 4, 12), (0, 8), False),  # right arm
    ("humanoid", (44, 20, 4, 12), (12, 8), True),  # left arm (mirrored)
    ("leggings", (20, 20, 8, 12), (4, 8), False),  # leggings belt
    ("leggings", (4, 20, 4, 12), (4, 20), False),  # right leg
    ("leggings", (4, 20, 4, 12), (8, 20), True),   # left leg
    ("humanoid", (4, 20, 4, 12), (4, 20), False),  # boot
    ("humanoid", (4, 20, 4, 12), (8, 20), True),
]


def load_palette(path):
    im = Image.open(path).convert("RGBA")
    return [im.getpixel((x, 0)) for x in range(im.size[0])]


def recolour(sprite, key, palette):
    """The paletted_permutations transform: key[i] -> palette[i]."""
    lookup = {k[:3]: palette[i] for i, k in enumerate(key)}
    out = Image.new("RGBA", sprite.size, (0, 0, 0, 0))
    src, dst = sprite.load(), out.load()
    for y in range(sprite.size[1]):
        for x in range(sprite.size[0]):
            r, g, b, a = src[x, y]
            if a == 0:
                continue
            dst[x, y] = lookup.get((r, g, b), (r, g, b, a))
    return out


def compose_front(layers):
    """layers: {"humanoid": Image, "leggings": Image} -> 16x32 front view."""
    out = Image.new("RGBA", (16, 32), (0, 0, 0, 0))
    for layer, (sx, sy, w, h), (dx, dy), mirror in FRONT:
        src = layers.get(layer)
        if src is None:
            continue
        part = src.crop((sx, sy, sx + w, sy + h))
        if mirror:
            part = part.transpose(Image.FLIP_LEFT_RIGHT)
        out.alpha_composite(part, (dx, dy))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vanilla", required=True, help="directory of extracted vanilla assets")
    ap.add_argument("--material", default="gold")
    ap.add_argument("--scale", type=int, default=6)
    ap.add_argument("--out", default="preview.png")
    args = ap.parse_args()

    mc = os.path.join(args.vanilla, "assets/minecraft/textures")
    pal_dir = os.path.join(mc, "trims/color_palettes")
    key = load_palette(os.path.join(pal_dir, "trim_palette.png"))
    palette = load_palette(os.path.join(pal_dir, f"{args.material}.png"))

    armour = {
        "humanoid": Image.open(os.path.join(mc, "entity/equipment/humanoid/iron.png")).convert("RGBA"),
        "leggings": Image.open(os.path.join(mc, "entity/equipment/humanoid_leggings/iron.png")).convert("RGBA"),
    }
    base = compose_front(armour)

    s = args.scale
    cell_w, cell_h = 16 * s + 16, 32 * s + 28
    sheet = Image.new("RGBA", (cell_w * len(PATTERNS), cell_h), (24, 24, 28, 255))
    draw = ImageDraw.Draw(sheet)

    trims = "src/main/resources/assets/extratrims/textures/trims/entity"
    for i, name in enumerate(PATTERNS):
        layers = {
            "humanoid": recolour(Image.open(f"{trims}/humanoid/{name}.png").convert("RGBA"), key, palette),
            "leggings": recolour(Image.open(f"{trims}/humanoid_leggings/{name}.png").convert("RGBA"), key, palette),
        }
        figure = base.copy()
        figure.alpha_composite(compose_front(layers))
        figure = figure.resize((16 * s, 32 * s), Image.NEAREST)
        x = i * cell_w + 8
        sheet.alpha_composite(figure, (x, 8))
        draw.text((x + 2, 32 * s + 14), name, fill=(235, 235, 235, 255))

    sheet.save(args.out)
    print(f"wrote {args.out} ({sheet.size[0]}x{sheet.size[1]}, material={args.material})")


if __name__ == "__main__":
    main()
