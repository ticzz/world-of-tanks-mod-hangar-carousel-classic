# Hangar Carousel Classic (World of Tanks Mod)

Classic-style hangar carousel for World of Tanks 2.x with native Gameface integration, advanced sorting, and card stats overlays.

## Quick Facts

- Version: 1.0.24
- Latest release: [v1.0.24](https://github.com/ticzz/world-of-tanks-mod-hangar-carousel-classic/releases/tag/v1.0.24)
- Full release notes: [GitHub Releases](https://github.com/ticzz/world-of-tanks-mod-hangar-carousel-classic/releases)
- Mod ID: hangar.carousel.classic
- Runtime: WoT embedded Python 2.7
- Build target: WoT 2.4.1.1; native bundles and hashes verified against the installed client.
- OpenWG GameFace 1.2.2 is included in the fullpack and required when installing the standalone WOTMOD.
- The user reports normal operation after the client compatibility and dependency fixes. Detailed large-garage timings and all controls/settings have not been independently verified in game.

## Key Features

- Carousel rows: manual 1-4 and auto mode.
- Vehicle card stats: battles, win rate, average damage, alpha damage, mastery, marks on gun.
- Vanilla filters include bonus, favorite, elite, premium, and rented/temporary vehicles. HCC provides more-credits, incomplete-field-modifications, non-elite, not-ready, marks-incomplete, and crew-not-fully-trained filters. Active filters are combined with AND logic and immediately applied to the carousel.
- Filtering, sorting, and card statistics can be enabled independently. Individual filters and single-rule sorting are toggled in the HCC panel; multiple sorting rules are configured as a hierarchy in ModsSettingsAPI.
- Advanced hierarchical sorting with optional reverse per criterion.
- Nation/type priority layers for deterministic grouping.
- Version 1.0.23 restores native rented-filter behavior based on Aslain's hotfix and reduces repeated garage-stat work.
- Version 1.0.24 removes the 256-dossier limit for correct marks filtering, badge counts, and card stats in large garages. Thanks to Aslain for the detailed follow-up in [issue #4](https://github.com/ticzz/world-of-tanks-mod-hangar-carousel-classic/issues/4#issuecomment-6509364155). Dossier and alpha-damage caches remain enabled; initial-build latency is not claimed to be fixed.
- Release packages: `dist/mod_hangar_carousel_classic_1.0.24.wotmod` and `dist/hangar_carousel_classic_1.0.24_full.zip`. The normal release includes the functional candidate fixes below without timing instrumentation. All 60 Python 2.7 regression tests pass, including large-garage checks with up to 925 simulated vehicles.

## Separate loading-time diagnostic build

- Build with Python 2.7: `python tools/build_diagnostic.py`, after building the normal 1.0.24 package. This creates `dist/mod_hangar_carousel_classic_1.0.24-diagnostic.wotmod` without changing the base source or normal packages.
- For testing, replace the existing Classic WOTMOD with the diagnostic WOTMOD; do not install both. Keep the existing GameFace dependency. Restore the normal WOTMOD after testing.
- Restart the game, enter the garage, then turn card statistics off and back on in the mod settings to request a second complete stats build without restarting. Send the `HCC DIAG 1.0.24-diagnostic` lines from `game.log`, including the initial build.
- Each rebuilt payload produces one diagnostic summary: payload/statistics milliseconds, alpha-damage milliseconds, actual vehicle-dossier fetch milliseconds, dossier-value extraction milliseconds, alpha cache reuse/computations, and dossier cache hits/misses/fetches. Lightweight refreshes do not produce a summary. Failed measured builds are marked `complete=False`; existing exceptions still propagate.
- Timings use Python 2.7's high-resolution Windows `time.clock()` elapsed-time counter. `payload_ms` includes filtering and other payload work; `stats_ms` includes its alpha/dossier/extraction components, so do not add these inclusive totals together. Extraction covers random-stats access, battles, win rate, average damage, and both marks helpers, not account-dossier setup or JSON/UI rendering. Dossier counters apply to this payload, not the whole game session; zero misses may mean the cache was already filled by another consumer.
- This is measurement only, with small instrumentation overhead: no scheduling, cache, filtering, or statistical-value changes. Run the Python 2.7 regression suite with `python -m unittest discover -s tools -p "test*.py"`.

## Native inventory startup fix (local test)

The current source distinguishes a native statistics presenter that is still loading from a ready, empty vehicle inventory. While waiting, it preserves the last published HCC state instead of sending an empty object to the UI. The existing native statistics update triggers the full model refresh when the inventory becomes available; no polling or inventory fallback is introduced. Waiting/recovery are logged once per transition. An existing presenter with a malformed vehicle component still produces a warning.

The separate `dist/mod_hangar_carousel_classic_1.0.24-lifecycle-test.wotmod` contains this fix and the dossier-limit removal, but no alpha-damage optimization or timing instrumentation. Replace, rather than combine, existing Classic WOTMODs for testing. The previously sent normal and diagnostic 1.0.24 archives remain unchanged. The diagnostic builder rejects a base package that no longer matches the edited source. Startup, delayed native updates, empty inventories, invalid components, state preservation, and presenter teardown are covered by `tools/test_inventory_lifecycle.py`; in-game startup/return-to-garage verification remains pending.

## Alpha-loading optimization (local instrumented candidate)

- Build with Python 2.7: `python tools/build_diagnostic.py --candidate`. The separate output is `dist/mod_hangar_carousel_classic_1.0.24-alpha-test7.wotmod`. This explicit candidate mode packages current Python source with native resources from the existing 1.0.24 base archive, excluding the obsolete standalone HCC layout registration; it does not overwrite earlier normal, diagnostic, lifecycle-test, or alpha-test packages.
- Includes the dossier-limit removal, native-inventory startup fix, and the same `HCC DIAG` timing fields as the original diagnostic build. Replace any other Classic WOTMOD for testing; keep GameFace installed.
- Alpha lookup now reads `VehicleParams(vehicle).avgDamage` directly. The old code rejected the client's lazy `ParamsDictProxy` because it was not a `dict`, then unnecessarily built a similar-crew comparator with extra vehicle/crew/bonus work. The native alpha property retains the client's selected-shot, damage-distribution/KPI, and rounding logic without a handwritten base-shell substitution. The existing setup cache and lazy candidate lookups remain.
- The final descriptor fallback uses the shell's `armorDamage`, as the client does, rather than `damage`. Normal operation uses the native property, not this fallback.
- `tools/test_alpha_damage.py` checks lazy native lookups, cache reuse/loadout changes, 925 mock vehicles, and the actual local client alpha formula with asymmetric damage-distribution modifiers. The local-source comparison requires the sibling `wot-src-EU` checkout or `WOT_SOURCE_ROOT`; without it, that specific test is skipped.
- The revised alpha-test2 also fixes the 2.4.1.1 filter-provider refresh: it calls the existing `VehicleFiltersDataProvider.__updateCarousel` without requiring a nonexistent `__updateVehicles`. This updates layout only; HCC filter changes continue to refresh vehicle statistics through the separate `VehiclesStatisticsPresenter.__updateVehicles` path. Missing carousel methods remain warnings and refresh exceptions are logged with a traceback.
- Alpha-test3 also fixes cache and startup/settings consistency: the card-payload signature includes gun/shell/selected-shot setup, and alpha caches are invalidated after loadout/crew-affecting item-cache syncs. These updates run on a tracked, one-shot next-tick callback so native vehicle components finish handling the sync before HCC reads them. Dossier-only syncs retain alpha caches.
- When native inventory is not ready, sort/filter publication is deferred too; initial models use neutral `{}` rather than an active filter with an empty allowlist. Existing native sort/filter state is preserved until the native presenter updates it. A genuinely ready empty inventory still publishes an empty allowlist correctly.
- Changing the card-statistics enabled setting now triggers a full payload rebuild when it differs from the last built state. Re-enabling statistics therefore repopulates values and generates a new diagnostic measurement; unchanged settings remain lightweight.
- The revised alpha-test4 removes an unused standalone WULF layout registration that lacked an `id` and pointed to a nonexistent HTML file, causing a startup parse error. HCC continues to inject its JS/CSS into the native carousel model via `gf_mod_inject`; no carousel, controls, or statistics feature is removed. Both builders omit the registration and package validation rejects it.
- Alpha-test5 uses the native `onSyncCompleted` invalid-item mapping for partial client updates: only cached setups belonging to affected vehicle compact descriptors are evicted. Native invalidation already includes crew/equipment/field-modification dependencies. Nonvehicle partial updates preserve alpha entries. Full resyncs and empty/missing mappings still clear all alpha entries, because the client also returns an empty mapping after full invalidation. Dossier refresh behavior is unchanged. The 925-vehicle regression checks that repeated single-vehicle updates each compute one alpha and reuse 924.
- Alpha-test6 adds a cross-session cache in `alpha_cache.json` beside the preferences-based HCC config. Its key contains the exact inputs used by native `VehicleParams.avgDamage`: vehicle/shell compact descriptors, shell base damage/randomization, and the native lower/upper damage-distribution KPI factors. Computing `getKpiFactors(vehicle)` validates crew, equipment and field-modification effects without the unrelated `getVehicleFactors` initialization. No account identifiers are stored: identical complete alpha inputs produce the same value across accounts.
- First use computes native alpha and saves successful primary-vehicle results. Subsequent sessions reuse entries only after validating those inputs. New vehicles or changed alpha inputs are computed normally; an equipment change that does not affect alpha can safely reuse the stored value. Session caches and selective invalidation remain. Fallback results are not persisted under the primary vehicle's key. Client-version/schema changes discard saved entries; invalid files log an error and rebuild. Writes are batched on a tracked callback; pending data is flushed at `fini()`.
- Alpha-test7 fixes alpha-test6's import failure: WoT lacks `_ctypes`, so persistence now uses standard-library temporary files and backup/rename instead of `ctypes`. Failed replacement restores the old file; a startup interrupted between renames recovers the backup. This is recoverable replacement, not a single atomic Windows replace.
- The 2026-11-05 client compatibility refresh accepts the updated main and Comp7 bundle hashes and builds normal 1.0.24 from those current client resources, retaining the candidate's functional fixes without timing instrumentation. All 16 main and 8 Comp7 patch anchors remain unique; tooltip JS/CSS are unchanged. The runtime stylesheet resource group is also corrected to a singleton tuple so compatibility verification reaches the stylesheet. In-game startup verification remains pending; accepting hashes alone does not establish that the garage hang is resolved.
- Test twice with alpha-test7: first start fills the cache, second start should show `alpha_persistent_reused` for unchanged vehicles and `alpha_computed=0`. `alpha_fingerprint_ms` measures validation and is included in `alpha_ms`, not added to it. Check displayed alpha values and test one new vehicle or an alpha-relevant loadout/crew change. The first start adds validation work; the real benefit on subsequent starts must be measured, not inferred from mock tests. No release or live installation is performed by this command.

## How to Install (using .wotmod only)

- See the complete [installation guide](docs/INSTALLATION.md).
- First, download the [v1.0.24 release](https://github.com/ticzz/world-of-tanks-mod-hangar-carousel-classic/releases/tag/v1.0.24).
- Copy the `.wotmod` file into your World of Tanks client's mods directory. 
For instance, you might place it in a path like `G:/Games/World_of_Tanks_EU/mods/2.4.1.1/`.
- The standalone WOTMOD requires `net.openwg.gameface_1.2.2.wotmod` or newer in the same client mods folder. The full package already includes GameFace 1.2.2.

- Launch the game. Use the native carousel filter popover to toggle vehicle filters. Aslain's Mod Menu and ModsSettingsBridge are optional and are not included in the full package. Install or update them separately via [Aslain's WoT ModPack](https://aslain.com/index.php?/topic/13-download-%E2%98%85-world-of-tanks-%E2%98%85-modpack/) if you use the in-game settings menu.

- Please be aware that net.openwg.gameface is essential for injecting the carousel's user interface. Mod Menu is optional and is solely used for accessing the in-game settings menu.

## Full Package Installation

- If you choose the complete package, [hangar_carousel_classic_1.0.24_full.zip](https://github.com/ticzz/world-of-tanks-mod-hangar-carousel-classic/releases/download/v1.0.24/hangar_carousel_classic_1.0.24_full.zip) includes the carousel mod and GameFace 1.2.2 in `mods/2.4.1.1/`. Extract it directly into the World of Tanks installation directory. Aslain's Mod Menu and ModsSettingsBridge are intentionally omitted; get or update them separately via [Aslain's WoT ModPack](https://aslain.com/index.php?/topic/13-download-%E2%98%85-world-of-tanks-%E2%98%85-modpack/) if needed.

## Build Locally

```powershell
./tools/build.ps1
./tools/validate.ps1 -PackagePath ./dist/mod_hangar_carousel_classic_1.0.24.wotmod
./tools/install.ps1 -GameRoot G:/Games/World_of_Tanks_EU -PackagePath ./dist/mod_hangar_carousel_classic_1.0.24.wotmod
```

## Documentation

- Detailed feature/config/build docs: [docs/TECHNICAL_DETAILS.md](docs/TECHNICAL_DETAILS.md)
- Current release details: [docs/RELEASE_NOTES_1.0.24.md](docs/RELEASE_NOTES_1.0.24.md)
- Security summary: [EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md)
- Security audit: [SECURITY_AUDIT_REPORT.md](SECURITY_AUDIT_REPORT.md)

## Quick Links

- Releases overview: [GitHub Releases](https://github.com/ticzz/world-of-tanks-mod-hangar-carousel-classic/releases)
- Latest package (v1.0.24): [mod_hangar_carousel_classic_1.0.24.wotmod](https://github.com/ticzz/world-of-tanks-mod-hangar-carousel-classic/releases/download/v1.0.24/mod_hangar_carousel_classic_1.0.24.wotmod)
- Full package (v1.0.24): [hangar_carousel_classic_1.0.24_full.zip](https://github.com/ticzz/world-of-tanks-mod-hangar-carousel-classic/releases/download/v1.0.24/hangar_carousel_classic_1.0.24_full.zip)
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
