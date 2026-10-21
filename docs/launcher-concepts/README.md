# Resident Evil: Degeneration launcher concepts

Three visual proposals for the native `redegpc` launcher, plus an achievements page. These images are generated design mockups. The [native launcher](../../launcher/README.md) now implements the incident dossier overview and achievement browser using the separate production assets.

## Directions

| Concept | Visual direction | Purpose |
| --- | --- | --- |
| [01 — Terminal Lockdown](01-terminal-lockdown.png) | Blue-gray ruined terminal, brushed dark steel, safety-amber Play control | Emphasize the airport setting and environmental concept artwork. |
| [02 — Cinematic Key Art](02-cinematic-key-art.png) | Leon and Claire, cold CGI lighting, ivory title, oxblood-red Play control | Emphasize the film and original mobile promotional identity. |
| [03 — Incident Dossier](03-incident-dossier.png) | Cool-gray evidence folder, clipped airport photograph, blue floor plan, quarantine stamp | Carry the tactile RE4 launcher approach into Degeneration's airport setting. |
| [04 — Achievements](04-achievements.png) | Dossier list, steel inventory icons, selected achievement detail and airport evidence photograph | Explore the requested achievements feature in the dossier visual language. |

Recommended starting point: **03 — Incident Dossier**, because its physical papers, photographs and inventory objects make it a natural companion to the RE4 launcher while the blue terminal plans give Degeneration its own identity.

The proposed primary action is Play, with Achievements, Settings & controls, Import game and View logs. Labels such as “Game installed” illustrate a proposed installed state; they do not report or verify the local installation. Additional dossier/navigation elements are visual proposals.

Achievements were added to the concept scope at the user's request. The achievements screen uses proposed examples and illustrative counts; tracking rules and runtime integration remain future implementation work. Any production implementation needs live controls, import/error/running states, keyboard navigation, and responsive layout.

## References

Research date: 16 October 2026. References were reviewed visually before generation.

- [RE4 launcher preview](../../../re4mepc/docs/launcher-preview.png) — local reference for material texture, illustration-led composition and functional hierarchy. Local source path: `/home/aurelio/Repos/re4mepc/docs/launcher-preview.png`. The relative link is useful only in the sibling-checkout layout.
- [Resident Evil Center: Degeneration extras](https://residentevilcenter.net/especiales/37-resident-evil-degeneration) — airport environmental concept art, described by the gallery as material principally from the *Biohazard Degeneration Visual & Scenario Archive*. [Referenced airport artwork](https://residentevilcenter.net/images/animation/redegeneration/imagenes/bocetos/aeropuerto_art.jpg).
- [Digital Frontier: Biohazard — DEGENERATION](https://www.dfx.co.jp/cgmaking/biohazard) — production imagery; Leon and Claire's costumes, CGI character treatment, terminal background and cold lighting. [Referenced image](https://storage.googleapis.com/production-os-assets/assets/2a723725-2742-41a6-b984-93dded9f7dfe).
- [Project Umbrella: Resident Evil Degeneration](https://www.projectumbrella.net/resident-evil-degeneration.html) — archived original mobile promotional material; distressed title, character arrangement and red graphic accent. [Referenced promotional image](https://www.projectumbrella.net/uploads/1/3/0/6/130616230/portable-degeneration-ioscapcom2_orig.jpg).
- [Sony Pictures: Resident Evil: Degeneration](https://www.sonypictures.com/movies/residentevildegeneration) — film identity reference.
- [Capcom's original iPhone release announcement](https://www.capcom.co.jp/ir/english/news/html/e90512.html) — game/movie relationship and original platform.

External reference originals were downloaded to `/tmp/redegpc-references/` for visual study. Generated mockups are concept-stage artwork informed by these references.

## Generation

Generated with the built-in image generation tool, one call per initial concept, with the references supplied as visual guidance. Each overview was subsequently edited to include the user's requested Achievements entry. No CLI/API fallback was used.

These images contain proposed UI lettering; production labels and controls should be rendered by the application.
