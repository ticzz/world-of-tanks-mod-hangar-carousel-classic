# Hangar Carousel Classic 1.0.24

## Fixes and improvements

- Refresh the main hangar and Comp7 bundles for the updated WoT 2.4.1.1 client. All 16 main and 8 Comp7 patch anchors are verified; tooltip resources remain supported.
- Remove the unused standalone layout declaration that referenced missing HTML and lacked a native resource ID. UI injection into the native carousel remains intact.
- Remove the 256-dossier cap so large garages retain complete card statistics, marks filters and counts.
- Preserve published state while native inventory is loading, and refresh once the native statistics presenter becomes ready.
- Correct the filter-provider refresh path and rebuild statistics when they are re-enabled.
- Read native average damage directly and selectively invalidate alpha caches for affected vehicles.
- Add a versioned cross-session alpha cache, validating native damage inputs before reuse. Cache writes use recoverable backup/rename without the unavailable `_ctypes` dependency.
- Keep diagnostic builds separate; the normal release contains no timing instrumentation.

## Compatibility and validation

- World of Tanks EU 2.4.1.1; OpenWG GameFace 1.2.2 or newer required.
- The full ZIP includes GameFace 1.2.2; optional Aslain menu components are not bundled.
- Python 2.7 compilation, all 60 regression tests and archive validation pass. Release bytecode, metadata and UI assets match the current source; the fullpack contains the same WOTMOD.
- The user reports normal operation after the compatibility/dependency fixes. Detailed real-world large-garage timings and every UI control/persistence path have not been independently verified.

Replace the previous Classic WOTMOD rather than installing both versions. Do not combine Classic and Mini.
