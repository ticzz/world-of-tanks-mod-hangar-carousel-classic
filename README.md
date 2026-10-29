# Hangar Carousel Classic (World of Tanks Mod)

Classic-style hangar carousel for World of Tanks 2.x with native Gameface integration, advanced sorting, and card stats overlays.

## Quick Facts

- Version: 1.0.23
- Latest release: [v1.0.23](https://github.com/ticzz/world-of-tanks-mod-hangar-carousel-classic/releases/tag/v1.0.23)
- Full release notes: [GitHub Releases](https://github.com/ticzz/world-of-tanks-mod-hangar-carousel-classic/releases)
- Mod ID: hangar.carousel.classic
- Runtime: WoT embedded Python 2.7
- Build target: WoT 2.4.1.1; native bundles and hashes verified against the installed client.
- OpenWG GameFace 1.2.2 is included in the fullpack and required when installing the standalone WOTMOD.
- In-game hangar smoke test has not yet been performed.

## Key Features

- Carousel rows: manual 1-4 and auto mode.
- Vehicle card stats: battles, win rate, average damage, alpha damage, mastery, marks on gun.
- Vanilla filters include bonus, favorite, elite, premium, and rented/temporary vehicles. HCC provides more-credits, incomplete-field-modifications, non-elite, not-ready, marks-incomplete, and crew-not-fully-trained filters. Active filters are combined with AND logic and immediately applied to the carousel.
- Filtering, sorting, and card statistics can be enabled independently. Individual filters and single-rule sorting are toggled in the HCC panel; multiple sorting rules are configured as a hierarchy in ModsSettingsAPI.
- Advanced hierarchical sorting with optional reverse per criterion.
- Nation/type priority layers for deterministic grouping.
- Version 1.0.23 restores native rented-filter behavior based on Aslain's hotfix and reduces repeated garage-stat work.

## How to Install (using .wotmod only)

- See the complete [installation guide](docs/INSTALLATION.md).
- First, download the [v1.0.23 release](https://github.com/ticzz/world-of-tanks-mod-hangar-carousel-classic/releases/tag/v1.0.23).
- Copy the `.wotmod` file into your World of Tanks client's mods directory. 
For instance, you might place it in a path like `G:/Games/World_of_Tanks_EU/mods/2.4.1.1/`.
- The standalone WOTMOD requires `net.openwg.gameface_1.2.2.wotmod` or newer in the same client mods folder. The full package already includes GameFace 1.2.2.

- Launch the game. Use the native carousel filter popover to toggle vehicle filters. Aslain's Mod Menu and ModsSettingsBridge are optional and are not included in the full package. Install or update them separately via [Aslain's WoT ModPack](https://aslain.com/index.php?/topic/13-download-%E2%98%85-world-of-tanks-%E2%98%85-modpack/) if you use the in-game settings menu.

- Please be aware that net.openwg.gameface is essential for injecting the carousel's user interface. Mod Menu is optional and is solely used for accessing the in-game settings menu.

## Full Package Installation

- If you choose the complete package, [hangar_carousel_classic_1.0.23_full.zip](https://github.com/ticzz/world-of-tanks-mod-hangar-carousel-classic/releases/download/v1.0.23/hangar_carousel_classic_1.0.23_full.zip) includes the carousel mod and GameFace 1.2.2 in `mods/2.4.1.1/`. Extract it directly into the World of Tanks installation directory. Aslain's Mod Menu and ModsSettingsBridge are intentionally omitted; get or update them separately via [Aslain's WoT ModPack](https://aslain.com/index.php?/topic/13-download-%E2%98%85-world-of-tanks-%E2%98%85-modpack/) if needed.

## Build Locally

```powershell
./tools/build.ps1
./tools/validate.ps1 -PackagePath ./dist/mod_hangar_carousel_classic_1.0.23.wotmod -GameRoot G:/Games/World_of_Tanks_EU
./tools/install.ps1 -GameRoot G:/Games/World_of_Tanks_EU -PackagePath ./dist/mod_hangar_carousel_classic_1.0.23.wotmod
```

## Documentation

- Detailed feature/config/build docs: [docs/TECHNICAL_DETAILS.md](docs/TECHNICAL_DETAILS.md)
- Current release details: [docs/RELEASE_NOTES_1.0.23.md](docs/RELEASE_NOTES_1.0.23.md)
- Security summary: [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md)
- Security audit: [SECURITY_AUDIT_REPORT.md](SECURITY_AUDIT_REPORT.md)

## Quick Links

- Releases overview: [GitHub Releases](https://github.com/ticzz/world-of-tanks-mod-hangar-carousel-classic/releases)
- Latest package (v1.0.23): [mod_hangar_carousel_classic_1.0.23.wotmod](https://github.com/ticzz/world-of-tanks-mod-hangar-carousel-classic/releases/download/v1.0.23/mod_hangar_carousel_classic_1.0.23.wotmod)
- Full package (v1.0.23): [hangar_carousel_classic_1.0.23_full.zip](https://github.com/ticzz/world-of-tanks-mod-hangar-carousel-classic/releases/download/v1.0.23/hangar_carousel_classic_1.0.23_full.zip)
- Full technical docs: [docs/TECHNICAL_DETAILS.md](docs/TECHNICAL_DETAILS.md)
- Main mod source: [res/scripts/client/gui/mods/mod_hangar_carousel_classic.py](res/scripts/client/gui/mods/mod_hangar_carousel_classic.py)
- Frontend assets: [res/gui/gameface/mods/hcc/hangar_carousel_classic](res/gui/gameface/mods/hcc/hangar_carousel_classic)
- Build script: [tools/build.ps1](tools/build.ps1)
- Validate script: [tools/validate.ps1](tools/validate.ps1)
- Install script: [tools/install.ps1](tools/install.ps1)
- Default config: [config/default.json](config/default.json)
- Package metadata: [meta.xml](meta.xml)

## Changelog Policy

- README contains only short release highlights.
- Full per-release details are published on [GitHub Releases](https://github.com/ticzz/world-of-tanks-mod-hangar-carousel-classic/releases).

## Credits

- Original concept: [RCooLeR / WoT-Hangar-carousel-plus](https://github.com/RCooLeR/WoT-Hangar-carousel-plus)

## Disclaimer

This is a third-party mod for World of Tanks. Use at your own responsibility and keep backups of your config and installed mods.
