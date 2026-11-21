# Hangar Carousel Classic 1.0.28

## Changes

- Nation and vehicle-type sorting now has a deterministic WoT default order when no custom order is configured.
- Custom nation/type entries retain their configured priority; unlisted entries follow the default order.
- Updated settings tooltips and technical documentation to explain the fallback behavior.

## Verification

- Python 2.7 compile check and all 32 inventory-lifecycle regression tests passed.
- GameFace lifecycle, card-stat and Frontline rendered-list regression tests passed.
- This sorting-order change has not yet been retested in-game.
- World of Tanks EU 2.4.1.1; OpenWG GameFace 1.2.2 or newer required for the standalone WOTMOD.
