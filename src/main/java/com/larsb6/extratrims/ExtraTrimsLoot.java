package com.larsb6.extratrims;

import java.util.LinkedHashMap;
import java.util.Map;

import net.fabricmc.fabric.api.loot.v3.LootTableEvents;

import net.minecraft.item.Item;
import net.minecraft.loot.LootPool;
import net.minecraft.loot.LootTable;
import net.minecraft.loot.LootTables;
import net.minecraft.loot.condition.RandomChanceLootCondition;
import net.minecraft.loot.entry.ItemEntry;
import net.minecraft.loot.provider.number.ConstantLootNumberProvider;
import net.minecraft.registry.RegistryKey;

/**
 * Adds each template to the chests of a structure that suits its look, so the
 * patterns are obtainable in survival without overwriting any vanilla table.
 */
public final class ExtraTrimsLoot {
	private record Placement(RegistryKey<LootTable> table, float chance) {
	}

	private static final Map<String, Placement> PLACEMENTS = new LinkedHashMap<>();

	static {
		PLACEMENTS.put("crest", new Placement(LootTables.PILLAGER_OUTPOST_CHEST, 0.25F));
		PLACEMENTS.put("weave", new Placement(LootTables.WOODLAND_MANSION_CHEST, 0.25F));
		PLACEMENTS.put("halo", new Placement(LootTables.END_CITY_TREASURE_CHEST, 0.20F));
		PLACEMENTS.put("thorn", new Placement(LootTables.JUNGLE_TEMPLE_CHEST, 0.25F));
		PLACEMENTS.put("ember", new Placement(LootTables.RUINED_PORTAL_CHEST, 0.25F));
		PLACEMENTS.put("fang", new Placement(LootTables.NETHER_BRIDGE_CHEST, 0.20F));
		PLACEMENTS.put("coil", new Placement(LootTables.STRONGHOLD_LIBRARY_CHEST, 0.20F));
		PLACEMENTS.put("sigil", new Placement(LootTables.DESERT_PYRAMID_CHEST, 0.20F));
		PLACEMENTS.put("scale", new Placement(LootTables.UNDERWATER_RUIN_BIG_CHEST, 0.20F));
	}

	private ExtraTrimsLoot() {
	}

	public static void register() {
		LootTableEvents.MODIFY.register((key, tableBuilder, source, registries) -> {
			if (!source.isBuiltin()) {
				return;
			}

			for (Map.Entry<String, Placement> entry : PLACEMENTS.entrySet()) {
				Placement placement = entry.getValue();

				if (!placement.table().equals(key)) {
					continue;
				}

				Item template = ExtraTrimsItems.templates().get(entry.getKey());

				if (template == null) {
					continue;
				}

				tableBuilder.pool(LootPool.builder()
						.rolls(ConstantLootNumberProvider.create(1.0F))
						.conditionally(RandomChanceLootCondition.builder(placement.chance()))
						.with(ItemEntry.builder(template)));
			}
		});
	}
}
