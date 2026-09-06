# Hangar Carousel Classic (World of Tanks Mod)

Classic-style hangar carousel for World of Tanks 2.x with native Gameface integration, advanced sorting, and card stats overlays.

## Quick Facts

- Version: 1.0.14
- Latest release: [v1.0.14](https://github.com/ticzz/world-of-tanks-mod-hangar-carousel-classic/releases/tag/v1.0.14)
- Full release notes: [GitHub Releases](https://github.com/ticzz/world-of-tanks-mod-hangar-carousel-classic/releases)
- Mod ID: hangar.carousel.classic
- Runtime: WoT embedded Python 2.7
- Tested game version: 2.4.0.0

## Key Features

- Carousel rows: manual 1-4 and auto mode.
- Vehicle card stats: battles, win rate, average damage, alpha damage, mastery, marks on gun.
- Native filters: bonus, favorite, elite, premium, non-elite, not ready, marks incomplete, and crew not maxed are always shown in the vanilla carousel filter popover. Active filters are combined with AND logic and immediately applied to the carousel.
- Filtering, sorting, and card statistics can be enabled independently. Individual filters and single-rule sorting are toggled in the HCC panel; multiple sorting rules are configured as a hierarchy in ModsSettingsAPI.
- Advanced hierarchical sorting with optional reverse per criterion.
- Nation/type priority layers for deterministic grouping.

## How to Install (using .wotmod only)

- See the complete [installation guide](docs/INSTALLATION.md).
- First, download the most recent version from the [Releases](https://github.com/ticzz/world-of-tanks-mod-hangar-carousel-classic/releases) page.
- Copy the `.wotmod` file into your World of Tanks client's mods directory. 
For instance, you might place it in a path like `G:/Games/World_of_Tanks_EU/mods/2.4.0.0/`. 
- Additionally, you'll need to install the corresponding `net.openwg.gameface_*.wotmod` file, 
which can be found in the [OpenWG Gameface releases](https://gitlab.com/openwg/wot.gameface/-/releases), also into your client mods folder.

- Launch the game. Use the native carousel filter popover to toggle vehicle filters. Mod Menu is optional and provides carousel, card, sorting, and action-card settings. (It is included in the full package.)

- Please be aware that net.openwg.gameface is essential for injecting the carousel's user interface. Mod Menu is optional and is solely used for accessing the in-game settings menu.

## Full Package Installation

- If you choose the complete package, [hangar_carousel_classic_1.0.14_full.zip](https://github.com/ticzz/world-of-tanks-mod-hangar-carousel-classic/releases/download/v1.0.14/hangar_carousel_classic_1.0.14_full.zip) includes the carousel mod, `Mod Menu`, `ModsSettingsBridge`, and `net.openwg.gameface`, all organized within `mods/2.4.0.0/`. Extract the contents directly into the World of Tanks installation directory.

## Build Locally

```powershell
./tools/build.ps1
./tools/validate.ps1 -PackagePath ./dist/mod_hangar_carousel_classic_1.0.14.wotmod
./tools/install.ps1 -GameRoot G:/Games/World_of_Tanks_EU -PackagePath ./dist/mod_hangar_carousel_classic_1.0.14.wotmod
```

## Documentation

- Detailed feature/config/build docs: [docs/TECHNICAL_DETAILS.md](docs/TECHNICAL_DETAILS.md)
- Security summary: [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md)
- Security audit: [SECURITY_AUDIT_REPORT.md](SECURITY_AUDIT_REPORT.md)

## Quick Links

- Releases overview: [GitHub Releases](https://github.com/ticzz/world-of-tanks-mod-hangar-carousel-classic/releases)
- Latest package (v1.0.14): [mod_hangar_carousel_classic_1.0.14.wotmod](https://github.com/ticzz/world-of-tanks-mod-hangar-carousel-classic/releases/download/v1.0.14/mod_hangar_carousel_classic_1.0.14.wotmod)
- Full package (v1.0.14): [hangar_carousel_classic_1.0.14_full.zip](https://github.com/ticzz/world-of-tanks-mod-hangar-carousel-classic/releases/download/v1.0.14/hangar_carousel_classic_1.0.14_full.zip)
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
