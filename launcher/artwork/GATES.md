# Gates: launcher individual artwork

Scope: analyze and regenerate every standalone launcher asset, keeping existing production filenames and dimensions. Remove obsolete full-screen copies, test crops, raw files and the old atlas from the asset folder. Colorize Leon and Claire, and add weapon, difficulty and platinum achievement artwork and design data.

- [x] A1: Every standalone artwork has a new generated source and final PNG, including both paper aliases; obsolete artwork is removed from the active asset folder.
  EVIDENCE: Final set verified: 41 independent sources, 42 active PNGs including one paper alias, 11 obsolete files removed. Original metadata in baseline.json.

- [x] A2: Final assets decode, retain expected dimensions, and transparent objects contain genuine alpha without baked checkerboards or unrelated UI fragments.
  EVIDENCE: python3 -B launcher/artwork/verify_assets.py exited 0 for the expanded set. Stale-digest negative control rejected. Manifest SHA256 e323f643ead87dd4bc1dd7c0dc6cc0eb03a45c29b88820c7bcd119bca3ec0294. Final preview visually reviewed.

- [x] A3: The complete set is visually reviewed and the audit, exact prompts, source mapping and before/after previews are saved locally.
  EVIDENCE: Audit, initial and expansion prompts, blueprint and portrait revision prompts, source logs and before/after previews saved. Final preview SHA256 e053c72ecdf252146577e4b80955550b9b6ad26e97cba20b87237b345b89efa0.

- [x] A4: Leon, Claire and paired portraits are full color, retaining original composition and production dimensions.
  EVIDENCE: Three colorized sources exported and visually reviewed. Automated color checks pass; original dimensions retained: Leon 260x325, Claire 320x310, paired 548x370.

- [x] A5: Separate weapon, difficulty and platinum achievement illustrations are generated, exported and catalogued; platinum requires all other achievements.
  EVIDENCE: Seven weapon trophies, three difficulty medals and platinum exported at 512x512. All 23 catalog entries map to real images. Platinum depends on exactly all 22 other ids; incomplete dependency negative control rejected. Catalog SHA256 f03c9d2913b9494e0568c9600cd1054ac9b644eaf0a965dc32405e8bb7342b74.

- [x] A6: The expanded asset set passes verification and visual review with updated prompts, catalog, manifest and preview.
  EVIDENCE: LAUNCHER_ARTWORK_VERIFIED: 41 independent generated assets, 1 compatibility alias. Process exited 0. Complete 41-tile after.jpg visually reviewed on light and dark backgrounds; no required work remains within artwork scope.
