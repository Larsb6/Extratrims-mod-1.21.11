#!/usr/bin/env python3
"""Static consistency checks for the Extra Trims resources.

Catches the mistakes that only show up as a silently missing texture or an
unapplied trim at runtime: an off-palette colour in a trim texture, an atlas
entry with no file behind it, a model pointing at a texture that is not there,
or a recipe naming a pattern that was never defined.
"""

import json
import os
import sys

from PIL import Image

RES = "src/main/resources"
MODID = "extratrims"
PALETTE = {224, 192, 160, 128, 96, 64, 32, 0}

errors = []
checks = 0


def check(condition, message):
    global checks
    checks += 1
    if not condition:
        errors.append(message)


def load(path):
    with open(os.path.join(RES, path)) as fh:
        return json.load(fh)


def exists(path):
    return os.path.isfile(os.path.join(RES, path))


def resolve(ref, kind, ext):
    """Turn 'ns:some/path' into its resource file path."""
    ns, _, path = ref.partition(":")
    if not path:
        ns, path = "minecraft", ns
    return f"assets/{ns}/{kind}/{path}.{ext}"


def main():
    patterns = sorted(
        f[:-5] for f in os.listdir(f"{RES}/data/{MODID}/trim_pattern")
    )
    check(bool(patterns), "no trim patterns found")
    print(f"checking {len(patterns)} patterns: {', '.join(patterns)}\n")

    atlas = load("assets/minecraft/atlases/armor_trims.json")
    atlas_textures = set()
    for source in atlas["sources"]:
        check(source["type"] == "minecraft:paletted_permutations",
              "atlas source is not paletted_permutations")
        check(source["palette_key"] == "minecraft:trims/color_palettes/trim_palette",
              "atlas palette_key does not match vanilla's trim palette")
        atlas_textures.update(source["textures"])
        for name, palette in source["permutations"].items():
            check(palette.startswith("minecraft:trims/color_palettes/"),
                  f"permutation {name} does not point at a vanilla palette")

    lang = load(f"assets/{MODID}/lang/en_us.json")

    for name in patterns:
        definition = load(f"data/{MODID}/trim_pattern/{name}.json")
        asset_id = definition["asset_id"]
        check(asset_id == f"{MODID}:{name}",
              f"{name}: asset_id {asset_id} does not match the file name")
        desc = definition["description"]["translate"]
        check(desc in lang, f"{name}: missing lang key {desc}")

        # Both armour layers must exist, be 64x32 and stay on-palette.
        for layer in ("humanoid", "humanoid_leggings"):
            rel = f"assets/{MODID}/textures/trims/entity/{layer}/{name}.png"
            if not exists(rel):
                errors.append(f"{name}: missing texture {rel}")
                continue
            im = Image.open(os.path.join(RES, rel)).convert("RGBA")
            check(im.size == (64, 32), f"{name} {layer}: size {im.size}, expected (64, 32)")
            opaque = 0
            for r, g, b, a in im.get_flattened_data():
                if a == 0:
                    continue
                opaque += 1
                if not (r == g == b and r in PALETTE):
                    errors.append(
                        f"{name} {layer}: off-palette colour ({r},{g},{b}) "
                        "will not be recoloured by the atlas")
                    break
            check(opaque > 0, f"{name} {layer}: texture is empty")

            ref = f"{MODID}:trims/entity/{layer}/{name}"
            check(ref in atlas_textures, f"{name}: {ref} not listed in the atlas")

        # The template item: definition -> model -> texture, plus both recipes.
        item = f"{name}_armor_trim_smithing_template"
        item_def = load(f"assets/{MODID}/items/{item}.json")
        model_ref = item_def["model"]["model"]
        model_path = resolve(model_ref, "models", "json")
        check(exists(model_path), f"{name}: item definition points at missing model {model_path}")
        if exists(model_path):
            model = load(model_path)
            tex = resolve(model["textures"]["layer0"], "textures", "png")
            check(exists(tex), f"{name}: model points at missing texture {tex}")

        check(f"item.{MODID}.{item}" in lang, f"{name}: missing item lang key")

        trim_recipe = load(f"data/{MODID}/recipe/{name}_armor_trim_smithing_trim.json")
        check(trim_recipe["pattern"] == f"{MODID}:{name}",
              f"{name}: smithing recipe names the wrong pattern")
        check(trim_recipe["template"] == f"{MODID}:{item}",
              f"{name}: smithing recipe names the wrong template item")

        dup = load(f"data/{MODID}/recipe/{item}.json")
        check(dup["result"]["id"] == f"{MODID}:{item}",
              f"{name}: duplication recipe yields the wrong item")
        check(dup["result"]["count"] == 2,
              f"{name}: duplication recipe should yield 2")

    # Nothing in the atlas should lack a file.
    for ref in sorted(atlas_textures):
        check(exists(resolve(ref, "textures", "png")),
              f"atlas lists {ref} but the texture is missing")

    # The Java pattern list has to agree with the data files.
    with open("src/main/java/com/larsb6/extratrims/ExtraTrimsItems.java") as fh:
        src = fh.read()
    for name in patterns:
        check(f'"{name}"' in src, f"{name}: not registered in ExtraTrimsItems")

    print(f"{checks} checks run")
    if errors:
        print(f"\n{len(errors)} FAILURE(S):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
