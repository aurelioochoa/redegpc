# redegpc notices

This repository retains touchHLE history at ca1de89c578e79746f33c1332e28efd106c334ba, upstream source copyright headers, Cargo.lock and all vendor gitlink revisions. New Rust host and compatibility code is provided under MPL-2.0, following the source file notices. See LICENSE, dev-scripts/gpl-3.0.txt, and the original README.touchHLE.md for upstream source and combined-binary terms. The documented combined binary is GPL-3.0-or-later; individual components retain their licenses.

Do not remove touchHLE_dylibs/COPYING.*, touchHLE_fonts/LICENSE.*, vendor licenses, or the runtime-generated dependency notices (available through `redegpc --copyright`). Distribution must include the runtime-resource notices and meet all dependency license obligations. FFmpeg is an external runtime dependency, not vendored or redistributed by this project; its installed build has its own license terms.

The Linux host links the system liblzma library from XZ Utils for bounded asset decoding. liblzma is copyright the XZ Utils authors and contributors and licensed under the BSD Zero Clause License (0BSD). No XZ command-line tool is bundled.

Resident Evil Degeneration and its supplied IPA/assets remain the property of their respective owners. No game executable, archive, or extracted game data is included in the source tree. The README includes captured gameplay screenshots and GIFs, plus an original illustrated fan banner; see docs/media/README.md for provenance. Import copies user-supplied files into private local application storage.
