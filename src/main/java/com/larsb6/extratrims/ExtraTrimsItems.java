package com.larsb6.extratrims;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

import net.fabricmc.fabric.api.itemgroup.v1.ItemGroupEvents;

import net.minecraft.item.Item;
import net.minecraft.item.ItemGroups;
import net.minecraft.registry.Registries;
import net.minecraft.registry.Registry;
import net.minecraft.registry.RegistryKey;
import net.minecraft.registry.RegistryKeys;
import net.minecraft.util.Identifier;
import net.minecraft.util.Rarity;

/**
 * The smithing template items.
 *
 * <p>Since 1.21.5 a smithing template needs no dedicated item class: it is an
 * ordinary uncommon item, and the {@code minecraft:smithing_trim} recipe is
 * what binds it to a trim pattern. The pattern definitions themselves live in
 * {@code data/extratrims/trim_pattern/}.
 */
public final class ExtraTrimsItems {
	/** Pattern ids, matching the trim_pattern files and texture names. */
	public static final String[] PATTERNS = {
			"crest", "weave", "halo", "thorn", "ember", "fang", "coil", "sigil", "scale"
	};

	private static final Map<String, Item> TEMPLATES = new LinkedHashMap<>();

	private ExtraTrimsItems() {
	}

	public static Map<String, Item> templates() {
		return Collections.unmodifiableMap(TEMPLATES);
	}

	public static String templateName(String pattern) {
		return pattern + "_armor_trim_smithing_template";
	}

	public static void register() {
		for (String pattern : PATTERNS) {
			RegistryKey<Item> key = RegistryKey.of(RegistryKeys.ITEM,
					Identifier.of(ExtraTrims.MOD_ID, templateName(pattern)));
			Item item = new Item(new Item.Settings().registryKey(key).rarity(Rarity.UNCOMMON));
			TEMPLATES.put(pattern, Registry.register(Registries.ITEM, key, item));
		}

		// Vanilla keeps smithing templates in the Ingredients tab.
		ItemGroupEvents.modifyEntriesEvent(ItemGroups.INGREDIENTS).register(entries -> {
			for (Item item : TEMPLATES.values()) {
				entries.add(item);
			}
		});
	}
}
