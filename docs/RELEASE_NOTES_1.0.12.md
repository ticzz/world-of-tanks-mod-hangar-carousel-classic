# Hangar Carousel Classic 1.0.12

- Add a hangar context guard so the mod stays inactive in event hangars such as Onslaught (`spaces/h33_comp7`).
- Keep the native vehicle list unfiltered outside the standard hangar, preventing broken event hangar views.
- Skip carousel row overrides, automatic row calculation, and tooltip injection when the active hangar space is not approved.
- Fall back to active when the hangar space service is unavailable, so the standard hangar keeps working.
