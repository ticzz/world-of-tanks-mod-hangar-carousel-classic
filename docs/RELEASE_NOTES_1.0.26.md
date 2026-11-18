# Hangar Carousel Classic 1.0.26

## Fixes and improvements

- Detect modded hangars through the live native carousel provider instead of relying only on known space paths. This supports hangar mods that replace the animated background or use a static scene while retaining the native carousel.
- Refresh HCC state when the carousel provider becomes available or is finalized, so controls follow hangar transitions.
- Hangars with a custom carousel or GameFace bundle still require a separate integration.

## Compatibility and validation

- World of Tanks EU 2.4.1.1; OpenWG GameFace 1.2.2 or newer required.
- Python 2.7 compilation and all 21 targeted inventory-lifecycle regression tests pass.
- The standalone WOTMOD passes package validation. The full ZIP includes GameFace 1.2.2.

Replace the previous Classic WOTMOD rather than installing both versions. Do not combine Classic and Mini.
