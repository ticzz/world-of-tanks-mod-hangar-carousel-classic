# Hangar Carousel Classic Details

This document contains the full technical details that were intentionally moved out of the main README.

## What This Mod Does

- Restores and extends classic hangar carousel behavior.
- Adds configurable carousel row handling (1-4 rows and auto mode).
- Adds card statistics overlays (battles, win rate, average damage, alpha damage, mastery, marks on gun).
- Integrates with native Gameface model properties and patched native bundles.
- JS/CSS injection uses `gf_mod_inject` on the native carousel model. HCC does not register a standalone WULF layout or HTML view. The obsolete `gui/gen_resources/hangar_carousel_classic.json` entry must not be packaged: it lacks the required resource `id` and references nonexistent HTML, producing a WULF startup parse error.
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

Card statistics refresh after the client completes a dossier or account-stats cache sync. This also covers battle results that arrive after returning to the hangar, rather than relying only on the immediate post-return refreshes. Partial client updates invalidate alpha entries only for `invalidItems[GUI_ITEM_TYPE.VEHICLE]`; the native requester resolves loadout, crew, and field-modification dependencies to vehicle compact descriptors. Nonvehicle partial updates retain alpha entries. Both full resets and settings-only diffs return empty mappings. A wrapper observes `ItemsRequester.invalidateCache(diff)` without changing its return identity or exceptions; a matching result with `diff is not None` identifies a partial update. Known partial empty mappings preserve alpha entries. GUI, inventory, shop, account-stats resyncs, and unknown empty/missing client-update mappings still clear all alpha entries. Refresh runs on a tracked next-tick callback after native inventory components process the sync. Dossier-only syncs preserve alpha results. Toggling card statistics rebuilds their payload; changes only to display fields remain lightweight.

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

- HCC carousel integration is enabled in the standard hangar (`spaces/hangar_v4`) and Onslaught/Comp 7 (`spaces/h33_comp7`). Frontline/Epic Battles is detected through its mode-specific carousel filter because it shares the native hangar filter provider and vehicle-statistics presenter. Other hangar spaces remain inactive until verified.
- Onslaught uses the shared random-hangar vehicle filter and statistics presenters in the inspected client source. Mode-specific eligibility or layout differences still require an in-game check.
- Frontline uses the shared `VehicleFiltersDataProvider` and `VehicleFilterModel`, plus a statistics presenter derived from the native presenter. Its separate hangar bundle has its own vehicle-list model and two-row carousel implementation. The build exposes `hccSortJson` and applies its allowed IDs and sort keys both to the playlist selection model and to the inventory model reaction that publishes `current.list()`/`current.ids()` for the rendered carousel, including active playlists. Patching only playlist selection does not affect the rendered carousel. Three-/four-row renderer and page-height changes remain; three-row layout was confirmed in game.
- Run `node tools/test_frontline_filters.js` to reproduce the unpatched rendered-list failure and exercise the replacement expressions with filter toggles, AND combinations, tier-VIII restrictions, empty matches, inventory IDs, native search and exclusions, playlists, and hierarchical sorting. Pass the built Frontline `bundle.js` path as an argument to verify it contains those exact tested expressions. Frontline filtering was confirmed in game on 2026-11-08.
- Three- and four-row layout CSS targets only the patched native vehicle-carousel page, so unrelated carousels in mode-specific hangar UI are not resized.
- Defensive error handling around game services access.
- Hot-reload cleanup for callbacks/providers/models.
- The native rented filter keeps the client's selection behavior so selecting it does not hide owned vehicles when no rentals are available.
- Alpha-damage results use the native `VehicleParams.avgDamage` property, without a similar-crew comparator. Results are cached by vehicle, gun, shell setup, and selected shot, with sync-driven invalidation for KPI changes. The card-payload signature includes this setup so a gun/shot change cannot reuse old card values. Vehicle item lookups remain lazy and card-stat build time/cache activity is logged when useful.
- A preferences-based `alpha_cache.json` also persists native results across sessions. On an in-memory miss, a SHA256 key validates vehicle/shell identity, `armorDamage[0]`, `damageRandomization`, and the two distribution factors from native `getKpiFactors`. These are the inputs read by the inspected `avgDamage` formula; no custom damage formula or manual crew fingerprint is introduced. Unchanged inputs bypass `VehicleParams` entirely, while changed/new inputs use it normally. The cache is shared safely across accounts by these complete alpha inputs without storing account identifiers. Client version and schema guard against formula updates.
- Cache schema 2 stores one identifiable record per vehicle compact descriptor, containing its current validated `fingerprint` and `alpha`. Input changes replace that record; old configurations are not retained. In-memory entries likewise discard previous setups of that vehicle on a miss. At most 4096 vehicle records are retained in insertion order; oldest vehicle records are evicted on overflow.
- Schema-1 hashes migrate only when live fingerprint validation identifies their vehicle. Matching values transfer without native recalculation; new/changed inputs are calculated normally. Saves write only identified schema-2 records, dropping unmatched legacy hashes. The cache serves responsive mod use across startup, filtering, statistics refreshes and crew/equipment updates; input-validation cost is unchanged by this format migration.
- Card-overlay off/on rendering is covered by a DOM regression, but the reported client visibility issue remains unconfirmed. UI diagnostics include minimum-battle exclusions and created-overlay vehicle IDs. Counts of created DOM overlays do not prove actual screen visibility.
- Persistent writes are batched after two seconds and at finalization, flushed to a temporary file and installed using standard-library backup/rename. WoT lacks `_ctypes`, so Windows `MoveFileExW` is not used. Failed replacement restores the previous file; loading recovers `.bak` if interruption left the main path absent. Replacement is recoverable, not a single atomic operation. Load/write failures are logged. Only successful primary-vehicle results are persisted, not cached/stock fallback values. Diagnostic `alpha_persistent_reused` counts disk-cache hits and `alpha_fingerprint_ms` measures input-validation cost inside `alpha_ms`. The first population incurs extra KPI validation; real second-start savings require an in-game measurement.
- Native inventory not yet available is distinct from a ready empty inventory: both HCC card-state and native sort/filter updates are deferred while waiting. The native statistics update resumes publication; initial filter models use neutral `{}` instead of an active empty allowlist.
- Dossier lookups, marks-incomplete results, and filter matches are reused to avoid duplicate garage-wide work. Dossiers are cached per vehicle and cache generation without a vehicle-count cap, so large garages receive complete marks-filter checks and card statistics. Genuinely unavailable dossiers retain the existing fallback behavior.
- Legacy config migration path to current schema.
