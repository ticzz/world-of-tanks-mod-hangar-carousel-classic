# Hangar Carousel Classic 1.0.23

## Fixes

- Fix the Random Battles carousel appearing empty for players without rented vehicles. This restores the native rental-filter behavior based on a hotfix supplied by Aslain, which identified the filter regression.
- Reduce garage refresh work in large vehicle collections: cache alpha-damage calculations by vehicle, gun, and shell setup; reuse dossier and filter results; and defer repeated item lookups.
- Keep dossier fetches capped per payload and log when the cap is reached, while avoiding false exclusion of vehicles when their marks data is deferred.
- Add targeted card-stat timing and alpha-cache diagnostics for slow refreshes.

## Compatibility

- Targets World of Tanks 2.4.1.1 and requires OpenWG GameFace 1.2.2 or newer.
- In-game hangar smoke testing remains pending.
