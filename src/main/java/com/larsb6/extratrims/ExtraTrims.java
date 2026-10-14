package com.larsb6.extratrims;

import net.fabricmc.api.ModInitializer;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class ExtraTrims implements ModInitializer {
	public static final String MOD_ID = "extratrims";
	public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

	@Override
	public void onInitialize() {
		ExtraTrimsItems.register();
		ExtraTrimsLoot.register();
		LOGGER.info("Extra Trims loaded {} armor trim patterns", ExtraTrimsItems.PATTERNS.length);
	}
}
