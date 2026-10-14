#!/usr/bin/env python3
"""Generate every JSON resource for Extra Trims from a single pattern table.

Keeping patterns, recipes, models, lang keys and the atlas in one place means
adding a trim is a one-line change here plus a motif in generate_textures.py.
"""

import json
import os

MODID = "extratrims"
RES = "src/main/resources"

# name -> (display name, duplication base block)
PATTERNS = {
    "ember":    ("Ember",    "minecraft:magma_block"),
    "umbra":    ("Umbra",    "minecraft:deepslate_bricks"),
    "totemic":  ("Totemic",  "minecraft:mossy_cobblestone"),
    "halo":     ("Halo",     "minecraft:purpur_block"),
    "keystone": ("Keystone", "minecraft:stone_bricks"),
    "mosaic":   ("Mosaic",   "minecraft:sandstone"),
    "zenith":   ("Zenith",   "minecraft:blackstone"),
    "harbor":   ("Harbor",   "minecraft:oak_planks"),
    "runic":    ("Runic",    "minecraft:end_stone_bricks"),
    "lattice":  ("Lattice",  "minecraft:dark_oak_planks"),
}

# The vanilla trim material permutations, copied from the client's
# assets/minecraft/atlases/armor_trims.json. Our pattern textures have to be
# listed against the same palette key or they will not be recoloured.
PERMUTATIONS = {
    "amethyst": "minecraft:trims/color_palettes/amethyst",
    "copper": "minecraft:trims/color_palettes/copper",
    "copper_darker": "minecraft:trims/color_palettes/copper_darker",
    "diamond": "minecraft:trims/color_palettes/diamond",
    "diamond_darker": "minecraft:trims/color_palettes/diamond_darker",
    "emerald": "minecraft:trims/color_palettes/emerald",
    "gold": "minecraft:trims/color_palettes/gold",
    "gold_darker": "minecraft:trims/color_palettes/gold_darker",
    "iron": "minecraft:trims/color_palettes/iron",
    "iron_darker": "minecraft:trims/color_palettes/iron_darker",
    "lapis": "minecraft:trims/color_palettes/lapis",
    "netherite": "minecraft:trims/color_palettes/netherite",
    "netherite_darker": "minecraft:trims/color_palettes/netherite_darker",
    "quartz": "minecraft:trims/color_palettes/quartz",
    "redstone": "minecraft:trims/color_palettes/redstone",
    "resin": "minecraft:trims/color_palettes/resin",
}


def write(path, data):
    full = os.path.join(RES, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")
    print(f"wrote {path}")


def template_id(name):
    return f"{name}_armor_trim_smithing_template"


def main():
    lang = {}

    for name, (display, base_block) in PATTERNS.items():
        item = template_id(name)

        # Trim pattern definition (dynamic registry, loaded from the data pack).
        write(f"data/{MODID}/trim_pattern/{name}.json", {
            "asset_id": f"{MODID}:{name}",
            "decal": False,
            "description": {"translate": f"trim_pattern.{MODID}.{name}"},
        })

        # Applying the trim in a smithing table. Since 1.21.5 the template item
        # is bound to the pattern here rather than on the pattern itself.
        write(f"data/{MODID}/recipe/{name}_armor_trim_smithing_trim.json", {
            "type": "minecraft:smithing_trim",
            "addition": "#minecraft:trim_materials",
            "base": "#minecraft:trimmable_armor",
            "pattern": f"{MODID}:{name}",
            "template": f"{MODID}:{item}",
        })

        # Duplication, matching vanilla's 7-diamond layout.
        write(f"data/{MODID}/recipe/{item}.json", {
            "type": "minecraft:crafting_shaped",
            "category": "misc",
            "key": {
                "#": "minecraft:diamond",
                "C": base_block,
                "S": f"{MODID}:{item}",
            },
            "pattern": ["#S#", "#C#", "###"],
            "result": {"count": 2, "id": f"{MODID}:{item}"},
        })

        # Item definition (1.21.4+ item model layer) and the model it points at.
        write(f"assets/{MODID}/items/{item}.json", {
            "model": {
                "type": "minecraft:model",
                "model": f"{MODID}:item/{item}",
            },
        })
        write(f"assets/{MODID}/models/item/{item}.json", {
            "parent": "minecraft:item/generated",
            "textures": {"layer0": f"{MODID}:item/{item}"},
        })

        lang[f"item.{MODID}.{item}"] = f"{display} Armor Trim Smithing Template"
        lang[f"trim_pattern.{MODID}.{name}"] = f"{display} Armor Trim"

    # Atlas sources are merged across packs, so we list only our own textures.
    textures = []
    for name in PATTERNS:
        textures.append(f"{MODID}:trims/entity/humanoid/{name}")
        textures.append(f"{MODID}:trims/entity/humanoid_leggings/{name}")
    write("assets/minecraft/atlases/armor_trims.json", {
        "sources": [{
            "type": "minecraft:paletted_permutations",
            "palette_key": "minecraft:trims/color_palettes/trim_palette",
            "permutations": PERMUTATIONS,
            "textures": textures,
        }],
    })

    write(f"assets/{MODID}/lang/en_us.json", dict(sorted(lang.items())))


if __name__ == "__main__":
    main()
