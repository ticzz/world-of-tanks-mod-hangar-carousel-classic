# Hangar Carousel Classic 1.0.12

- Add a hangar context guard so the mod stays inactive in event hangars such as Onslaught (`spaces/h33_comp7`).
- Remove the global carousel row and action card CSS classes when leaving an approved hangar, so the carousel no longer stretches over the full screen height and blocks the game menu.
- Fail closed while the hangar space is still unknown, because the client restores the last used game mode on startup and may open an event hangar directly.
- Re-evaluate the hangar context on `IHangarSpace` space events so switching game modes updates the view immediately.
- Keep the native vehicle list unfiltered outside the standard hangar.
- Skip carousel row overrides, automatic row calculation, and tooltip injection when the active hangar space is not approved.
