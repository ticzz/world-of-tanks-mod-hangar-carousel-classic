# Hangar Carousel Classic 1.0.25

## Changes since 1.0.24

- Apply HCC filtering/sorting to Frontline's rendered carousel list, including active playlists, rather than only the playlist-selection model. Preserve native eligibility/search filtering and the three-/four-row carousel/page-height patch. Frontline layout and filtering were confirmed in game on 2026-11-08.
- Retain in-memory alpha cache entries during known settings-only updates instead of treating every empty invalid-item mapping as a full reset. Genuine full resets and unknown empty mappings remain conservative.
- Upgrade the persistent alpha cache to schema 2: one validated record per vehicle, replacing older setups and limiting storage to 4096 vehicle records. Migrate schema-1 values only after matching the live native-input fingerprint.

Native alpha calculation, the original cross-session cache, targeted vehicle invalidation, and inventory-startup state preservation were already included in 1.0.24 and remain unchanged features, not new additions in this release.

## Compatibility and validation

- World of Tanks EU 2.4.1.1; OpenWG GameFace 1.2.2 or newer required.
- Python 2.7 compilation and all 71 regression tests pass.
- The JavaScript rendered-list regression reproduces the previous Frontline filtering failure and verifies the actual replacement expressions.
- The standalone WOTMOD and full ZIP pass package validation. The full ZIP includes GameFace 1.2.2.

Replace the previous Classic WOTMOD rather than installing both versions. Do not combine Classic and Mini.
