/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. https://mozilla.org/MPL/2.0/. */
fn main() {
    if let Err(error) = touchHLE::redegpc::cli(std::env::args_os().skip(1)) {
        eprintln!("redegpc: {error}");
        std::process::exit(1);
    }
}
