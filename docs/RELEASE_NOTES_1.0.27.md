# Hangar Carousel Classic 1.0.27

## Changes

- Fix a startup crash when migrating legacy `runtime.json` settings and no preferences copy exists yet.
- Clean up Python class hooks, the item-cache invalidation override, hangar event handlers, and the optional settings callback on unload. If another mod still calls HCC's carousel load hook, the retired hook passes the call through without applying HCC changes.
- Tear down the GameFace observer, engine listener, timers, and pending render callback when the view is hidden or replaced, and restart them when the page is shown again.
- Apply the main ModsSettingsAPI switch directly to the open hangar. Turning HCC off restores the native carousel layout and hides HCC controls and card stats; turning it on reapplies HCC without leaving the garage.

## Verification

- In-game Random hangar: integrated filters and sorting, reopening the filter menu, card stats off/on, and the main mod switch in both directions without a shop visit.
- Local regression tests cover migration, Python and GameFace teardown, and Frontline playlist/search filtering. Comp7 and Frontline transitions and a garage with more than 256 vehicles have not been retested in-game on this build.
