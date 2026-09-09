# Hangar Carousel Classic Details

This document contains the full technical details that were intentionally moved out of the main README.

## What This Mod Does

- Restores and extends classic hangar carousel behavior.
- Adds configurable carousel row handling (1-4 rows and auto mode).
- Adds card statistics overlays (battles, win rate, average damage, alpha damage, mastery, marks on gun).
- Integrates with native Gameface model properties and patched native bundles.
- Provides a hierarchical sorting schema that is XVM-compatible by design, but does not require XVM.
- Adds practical filter toggles in the hangar UI.

## Why It Is Different From Carousel Plus

Compared to the original carousel-plus approach, this project adds:

- Hierarchical sorting criteria list instead of single-mode sorting only.
- Per-criterion reverse mode using a minus prefix.
- Nation priority ordering and vehicle type priority ordering.
- Runtime and configuration migration logic (legacy format to schemaVersion 5).
- Compatibility and safety patches for modern WoT client behavior.
- Build-time validation gates for Python bytecode, native bundle hooks, and required assets.

## Feature Overview

### Carousel Rows

- Manual rows: 1, 2, 3, 4
- Auto mode: tracks and preserves client-resolved row count behavior where applicable

### Card Statistics

Configurable fields:

- battles
- winRate
- averageDamage
- alphaDamage
- mastery
- marksOnGun

Minimum battles threshold is configurable.

### Filters

HCC filter IDs:

- non_elite
- not_ready
- marks_incomplete
- crew_not_maxed (matches vehicles whose currently assigned crew is not fully trained for that vehicle according to the client crew state)

Native WoT filters, including bonus, favorite, elite, premium, and rented/temporary vehicles, remain available in the vanilla filter panel.

### Advanced Hierarchical Sorting

Sorting is configured via an ordered list of criteria.

- First entry = primary key
- Second entry = secondary key
- Third entry = tertiary key

Each criterion can be ascending or descending:

- Ascending: criterion name, for example `battles`
- Descending: prefix with `-`, for example `-battles`

Supported criteria:

- nation
- type
- level / -level
- maxBattleTier / -maxBattleTier
- premium / -premium
- battles / -battles
- winRate / -winRate
- markOfMastery / -markOfMastery
- averageDamage / -averageDamage
- marksOnGun / -marksOnGun
- battlePassPoints / -battlePassPoints
- lastPlayed / -lastPlayed

### Nation and Type Priority Layers

Custom priority can be defined independent from numeric sorting:

- nations_order: tokens such as ussr, germany, usa, china, france, uk, japan, czech, poland, sweden, italy
- types_order: tokens such as lightTank, mediumTank, heavyTank, AT-SPG, SPG

Unknown or unmapped entries are sorted last.

## Practical Sorting Examples

Use these examples inside sorting.sorting_criteria:

1. nation, type, level
2. nation, type, -level
3. -winRate, -battles, level
4. premium, nation, type, -averageDamage
5. -lastPlayed
6. nation, type, -markOfMastery, -marksOnGun

## Configuration

Default configuration:

- [config/default.json](../config/default.json)

Runtime/user config path:

- %APPDATA%/Wargaming.net/WorldOfTanks/mods/mod_hangar_carousel_classic/config.json

Runtime state path:

- %APPDATA%/Wargaming.net/WorldOfTanks/mods/mod_hangar_carousel_classic/runtime.json

Legacy fallback paths are read when present and then migrated.

## Build and Validation

Project scripts:

- [tools/build.ps1](../tools/build.ps1)
- [tools/install.ps1](../tools/install.ps1)
- [tools/validate.ps1](../tools/validate.ps1)
- [tools/package_wotmod.py](../tools/package_wotmod.py)

Recommended workflow:

```powershell
./tools/build.ps1
./tools/validate.ps1 -PackagePath ./dist/mod_hangar_carousel_classic_1.0.4.wotmod
./tools/install.ps1 -GameRoot G:/Games/World_of_Tanks_EU -PackagePath ./dist/mod_hangar_carousel_classic_1.0.4.wotmod
```

## Installation Notes

- Requires a World of Tanks client with Gameface support.
- Requires the matching `net.openwg.gameface_*.wotmod` from the [OpenWG Gameface releases](https://gitlab.com/openwg/wot.gameface/-/releases) in the client mods folder.
- If `net.openwg.gameface` is missing, injection is skipped and features fail closed.
- ModsSettingsAPI is optional; without it, edit the JSON configuration file directly.
- Existing installed versions are backed up by installer scripts before replacement.

## Repository Structure

- [res/scripts/client/gui/mods/mod_hangar_carousel_classic.py](../res/scripts/client/gui/mods/mod_hangar_carousel_classic.py): core Python 2.7 logic, integration hooks, sorting/filter/state handling.
- [res/gui/gameface/mods/hcc/hangar_carousel_classic](../res/gui/gameface/mods/hcc/hangar_carousel_classic): JS/CSS UI integration assets.
- [config/default.json](../config/default.json): default configuration values.
- [meta.xml](../meta.xml): package metadata.
- [tools](../tools): build/install/validate toolchain.

## Compatibility and Safety

- Defensive error handling around game services access.
- Hot-reload cleanup for callbacks/providers/models.
- Dossier fetch rate limiting to reduce UI blocking risk in large garages.
- Legacy config migration path to current schema.
