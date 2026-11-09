# Bundled brand packs

Packs placed here ship inside the app and appear in the Appearance menu's
Brand list for every pilot. The public build ships none: like the Tripwire
fork, everything in this folder except this README is git-ignored, so a
corp's pack never lands in the public repo.

A corp that wants a pre-branded build copies its pack in before building:

```
src/shortcircuit/brand_packs/<slug>/brand.json
src/shortcircuit/brand_packs/<slug>/<logos and icons>
```

`<slug>` is lowercase letters, digits and dashes. The pack format is the
Tripwire fork's `brand.json` (see its README, **Brand packs**), so the same
pack themes both. Short Circuit reads `corp`, `short`, `accent` and both
`palette` modes; colors must be `#rrggbb`. Security, wormhole-class and
status colors are never taken from a pack.

Pilots can also add a pack themselves without a special build: Appearance ›
Import brand pack…, then pick the pack's folder.
