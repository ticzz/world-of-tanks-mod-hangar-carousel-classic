# Hangar Carousel Classic 1.0.25

## Fixes and improvements

- Include the functional alpha-test improvements in the normal release: native `VehicleParams.avgDamage`, setup-aware alpha caching and payload signatures, targeted cache invalidation, and a bounded cross-session alpha cache with safe migration and writes.
- Preserve HCC state while the native vehicle inventory is loading, and refresh after the native statistics presenter becomes ready.
- Apply HCC filtering/sorting to Frontline's rendered carousel list, including active playlists, rather than only the playlist-selection model. Preserve native eligibility/search filtering and the three-/four-row carousel/page-height patch. Frontline layout and filtering were confirmed in game on 2026-11-08.
- Keep timing instrumentation out of the normal release package.

## Compatibility and validation

- World of Tanks EU 2.4.1.1; OpenWG GameFace 1.2.2 or newer required.
- Python 2.7 compilation and all 71 regression tests pass.
- The JavaScript rendered-list regression reproduces the previous Frontline filtering failure and verifies the actual replacement expressions.
- The standalone WOTMOD and full ZIP pass package validation. The full ZIP includes GameFace 1.2.2.

Replace the previous Classic WOTMOD rather than installing both versions. Do not combine Classic and Mini.
