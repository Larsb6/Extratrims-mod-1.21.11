#!/usr/bin/env python3
"""Generate the 16x16 smithing-template item icons and the mod icon.

Each icon is an octagonal plate in a colour themed to the structure the
template generates in, carrying a cyan glyph that echoes the trim pattern.
The cyan accent is the shared visual cue vanilla uses for smithing templates.
"""

import argparse
import os

from PIL import Image

CYAN_HI = (134, 240, 240, 255)
CYAN_MID = (75, 201, 201, 255)

# pattern -> plate body colour, themed to its structure
BODY = {
    "ember":    (124, 72, 69),    # ruined portal, netherrack
    "umbra":    (74, 72, 86),     # ancient city, deepslate
    "totemic":  (106, 126, 88),   # jungle temple, moss
    "halo":     (161, 116, 161),  # end city, purpur
    "keystone": (134, 134, 134),  # stronghold corridor, stone brick
    "mosaic":   (213, 196, 150),  # desert pyramid, sandstone
    "zenith":   (168, 152, 96),   # bastion, gilded blackstone
    "harbor":   (162, 130, 78),   # shipwreck, oak
    "runic":    (196, 196, 160),  # stronghold library, end stone
    "lattice":  (102, 78, 47),    # woodland mansion, dark oak
}

# 6x6 glyphs echoing each pattern: '#' bright cyan, '+' mid cyan, '.' clear
GLYPHS = {
    "ember":    [".#..#.", "#..#.+", "+.#..#", ".#..#.", "#..#.+", "..##.."],
    "umbra":    ["..##..", "..##..", "######", "######", "..##..", "..##.."],
    "totemic":  [".####.", "#....#", "######", ".####.", "#....#", "######"],
    "halo":     [".####.", "#....#", "..##..", ".#..#.", "######", "......"],
    "keystone": ["######", "..#..#", "######", "#..#..", "######", "..#..#"],
    "mosaic":   [".####.", ".#..#.", ".####.", ".####.", ".#..#.", ".####."],
    "zenith":   ["..##..", "..##..", "######", "..##..", "..##..", "..##.."],
    "harbor":   ["..##..", ".####.", "..##..", "######", "..##..", "..##.."],
    "runic":    [".####.", "#....#", "......", ".####.", "#....#", "......"],
    "lattice":  ["#.##.#", ".#..#.", "#.##.#", ".#..#.", "#.##.#", ".#..#."],
}


def scale(rgb, factor):
    return tuple(max(0, min(255, round(c * factor))) for c in rgb) + (255,)


def plate_pixels():
    """Octagonal plate footprint."""
    out = set()
    for y in range(2, 14):
        for x in range(2, 14):
            if abs(x - 7.5) + abs(y - 7.5) <= 9.5:
                out.add((x, y))
    return out


def make_icon(name):
    body = BODY[name]
    outline = scale(body, 0.45)
    shade = scale(body, 0.75)
    light = scale(body, 1.18)
    fill = body + (255,)

    inside = plate_pixels()
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = im.load()

    for (x, y) in inside:
        edge = any((x + dx, y + dy) not in inside
                   for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        if edge:
            px[x, y] = outline
        elif x + y <= 13:
            px[x, y] = light
        elif x + y >= 19:
            px[x, y] = shade
        else:
            px[x, y] = fill

    for gy, row in enumerate(GLYPHS[name]):
        for gx, ch in enumerate(row):
            if ch == ".":
                continue
            px[5 + gx, 5 + gy] = CYAN_HI if ch == "#" else CYAN_MID
    return im


def make_mod_icon():
    """128x128 mod icon: the umbra plate, nearest-neighbour upscaled."""
    base = make_icon("umbra")
    return base.resize((128, 128), Image.NEAREST)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="src/main/resources/assets/extratrims")
    args = ap.parse_args()

    item_dir = os.path.join(args.out, "textures/item")
    os.makedirs(item_dir, exist_ok=True)
    for name in GLYPHS:
        icon = make_icon(name)
        icon.save(os.path.join(item_dir, f"{name}_armor_trim_smithing_template.png"))
        print(f"wrote {name}_armor_trim_smithing_template.png")

    make_mod_icon().save(os.path.join(args.out, "icon.png"))
    print("wrote icon.png")


if __name__ == "__main__":
    main()
