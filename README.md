# Extra Trims

A Fabric mod for **Minecraft 1.21.11** that adds eight new armor trim patterns,
each with its own smithing template that generates in a structure suited to it.

![The eight patterns in gold trim](docs/preview-gold.png)

*The eight patterns, shown in gold on iron armour. All sixteen vanilla trim
materials work; `docs/preview-amethyst.png` shows the same set in amethyst.*

## The patterns

| Pattern | Found in | Duplicate with |
|---|---|---|
| Crest | Pillager outpost chests | Cobblestone |
| Tusk | Desert pyramid chests | Sandstone |
| Thorn | Jungle temple chests | Mossy cobblestone |
| Lattice | Stronghold library chests | Stone bricks |
| Prism | Large ocean ruin chests | Prismarine |
| Ember | Nether fortress chests | Netherrack |
| Weave | Woodland mansion chests | Dark oak planks |
| Halo | End city treasure chests | Purpur block |

Templates are applied at a smithing table exactly like vanilla ones, work with
all sixteen vanilla trim materials, and duplicate with the same
seven-diamond-plus-base-block recipe vanilla uses.

## Building

Requires JDK 21.

```sh
./gradlew build
```

The mod jar is written to `build/libs/extratrims-1.0.0.jar`. Install it with
[Fabric Loader](https://fabricmc.net/use/installer) 0.19.5 or newer and
[Fabric API](https://modrinth.com/mod/fabric-api) for 1.21.11.

To run a development client or server:

```sh
./gradlew runClient
./gradlew runServer
```

## How it is put together

Armor trims are almost entirely data-driven in this version, so the Java is
thin and most of the mod is JSON and textures.

- `data/extratrims/trim_pattern/` — the pattern definitions. Since 1.21.5 a
  pattern no longer names its template item; the `minecraft:smithing_trim`
  recipe binds the two together instead.
- `data/extratrims/recipe/` — one `smithing_trim` recipe and one duplication
  recipe per pattern.
- `assets/extratrims/textures/trims/entity/humanoid{,_leggings}/` — the trim
  textures, one pair per pattern. These must use only the eight greys of
  vanilla's `trim_palette.png`, because the atlas recolours them per material.
- `assets/minecraft/atlases/armor_trims.json` — registers those textures for
  palette swapping. Atlas sources from every pack are merged, so this adds to
  vanilla's list rather than replacing it.
- `ExtraTrimsItems` registers the eight template items. A smithing template
  needs no special item class in this version — it is a plain uncommon item.
- `ExtraTrimsLoot` adds each template to its structure's loot table through
  Fabric's `LootTableEvents.MODIFY`, so no vanilla file is overwritten.

## Regenerating assets

The textures and JSON are generated, so adding a pattern means editing two
tables rather than hand-writing a dozen files.

```sh
# Trim textures. Needs the vanilla armour textures as a mask source; point
# --masks at a directory containing assets/minecraft/textures/entity/equipment/
python3 tools/generate_textures.py --masks /path/to/extracted/client

python3 tools/generate_items.py    # smithing template icons and the mod icon
python3 tools/generate_data.py     # trim patterns, recipes, models, lang, atlas
python3 tools/validate.py          # consistency checks over everything above

# Re-render the preview sheets in docs/
python3 tools/preview.py --vanilla /path/to/extracted/client --material gold \
    --out docs/preview-gold.png
```

To add a pattern: add a motif function to `generate_textures.py`, a glyph and
colour to `generate_items.py`, a row to `PATTERNS` in `generate_data.py`, and
a placement in `ExtraTrimsLoot`.

## Licence

MIT, see [LICENSE](LICENSE).
