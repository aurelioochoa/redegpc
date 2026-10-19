/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. https://mozilla.org/MPL/2.0/. */
//! Desktop-only presentation of the English v1.03.00 touch HUD.
//!
//! Match decoded RGBA texture bytes, never GL object IDs or screen rectangles.
//! The uploaded copy changes; guest memory, input hitboxes, installed resources
//! and the decoded asset cache stay intact. Unknown textures pass through.

const ICONS: &str = "dc7a8eae03f02b1a3930948a71c54db0cfaebac4f9d73f70e074903ca6c0cadb";
const PAD: [&str; 2] = [
    "bd0f5e15327c85b4830f5239f5d4a41629974d7bb954ae05a4300b17d56a20f9",
    "c760d574b3d8cf8ba90c59cb63b6d70020647dfb2feec20402fd4f6fdfc6b4c6",
];
// Eight columns, four rows of 64×64 cells, origin at the first uploaded row.
// Knife, fire/target, walk, aim/sight. Keep the phone and every contextual cell,
// including pickup, door, both kicks, ladder, jump, reload and shake-off.
const CONTROLS: [(usize, usize); 4] = [(3, 0), (2, 2), (0, 3), (5, 3)];

/// Recognize the gameplay phone's keypad in the frame already read for
/// composition. This distinguishes gameplay from title/phone menus and movies
/// without adding GPU readbacks or relying on keyboard menu-state guesses.
pub(crate) fn gameplay_frame(pixels: &[u8], width: u32, height: u32) -> bool {
    if !matches!((width, height), (320, 480) | (480, 320))
        || pixels.len() != (width * height * 4) as usize
    {
        return false;
    }
    let brightness = |x: usize, y: usize| {
        // OpenGL rows start at the bottom. LandscapeLeft rotates the game's
        // portrait renderbuffer clockwise into logical landscape coordinates.
        let (x, y) = if width == 320 {
            (319 - y, 479 - x)
        } else {
            (x, 319 - y)
        };
        let offset = (y * width as usize + x) * 4;
        let p = &pixels[offset..offset + 3];
        (u16::from(p[0]) + u16::from(p[1]) + u16::from(p[2])) / 3
    };
    // Three bright keypad columns separated by dark horizontal/vertical gaps.
    // Relative contrast tolerates the HUD's translucent background.
    for x in [20, 32, 43] {
        let gap = brightness(x, 37).max(brightness(x, 49));
        for y in [33, 41, 45] {
            if brightness(x, y) < gap + 50 {
                return false;
            }
        }
    }
    brightness(12, 20) > brightness(32, 20) + 50 && brightness(50, 20) > brightness(32, 20) + 50
}

fn clear_controls(pixels: &mut [u8]) {
    for (column, row) in CONTROLS {
        for y in row * 64..(row + 1) * 64 {
            let start = (y * 512 + column * 64) * 4;
            pixels[start..start + 64 * 4].fill(0);
        }
    }
}

/// Called only for tightly packed, base-level RGBA/UNSIGNED_BYTE uploads.
pub(crate) fn desktop_texture(width: i32, height: i32, pixels: &[u8]) -> Option<Vec<u8>> {
    let expected = match (width, height) {
        (512, 256) => 512 * 256 * 4,
        (128, 128) => 128 * 128 * 4,
        _ => return None,
    };
    if pixels.len() != expected {
        return None;
    }
    let hash = super::hash::sha256(pixels).ok()?;
    if (width, height) == (512, 256) && hash == ICONS {
        let mut copy = pixels.to_vec();
        clear_controls(&mut copy);
        Some(copy)
    } else if (width, height) == (128, 128) && PAD.contains(&hash.as_str()) {
        Some(vec![0; expected])
    } else {
        None
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn contextual_cells_and_every_other_pixel_survive() {
        let original: Vec<u8> = (0..512 * 256 * 4).map(|i| (i % 255 + 1) as u8).collect();
        let mut filtered = original.clone();
        clear_controls(&mut filtered);
        // Independently enumerate all 32 cells, including the two distinct
        // kick icons (8 and 12), pickup (0), door (16) and ladder (13).
        let hidden = [3, 18, 24, 29];
        for y in 0..256 {
            for x in 0..512 {
                let offset = (y * 512 + x) * 4;
                let pixel = &filtered[offset..offset + 4];
                if hidden.contains(&(y / 64 * 8 + x / 64)) {
                    assert_eq!(pixel, &[0; 4]);
                } else {
                    assert_eq!(pixel, &original[offset..offset + 4]);
                }
            }
        }
    }

    #[test]
    fn unrelated_and_malformed_textures_pass_through() {
        for (w, h, len) in [
            (512, 256, 512 * 256 * 4),
            (128, 128, 128 * 128 * 4),
            (512, 256, 7),
            (256, 512, 512 * 256 * 4),
            (0, 0, 0),
        ] {
            assert!(desktop_texture(w, h, &vec![255; len]).is_none());
        }
    }
}
