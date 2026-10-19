#!/usr/bin/env python3
"""Check CLI failures and XDG/source independence using a synthetic legal fixture."""
import hashlib
import os
from pathlib import Path
import plistlib
import struct
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "target/release/redegpc"

with tempfile.TemporaryDirectory(prefix="redegpc-cli-") as temporary:
    path = Path(temporary)
    env = dict(os.environ, XDG_DATA_HOME=str(path / "data"),
               XDG_CONFIG_HOME=str(path / "config"), XDG_STATE_HOME=str(path / "state"))

    def run(*args, success=True):
        result = subprocess.run([EXE, *args], cwd=path, env=env,
                                capture_output=True, text=True)
        assert (result.returncode == 0) == success, result.stdout + result.stderr
        return result.stdout + result.stderr

    assert "Usage:" in run("--help")
    assert "import" in run(success=False)
    run("unknown", success=False)
    run("import", success=False)
    run("run", "--volume=nan", success=False)
    run("run", "--volume=101", success=False)
    run("run", "--resources", success=False)
    ipa = path / "fixture.ipa"
    info = {"CFBundleIdentifier": "jp.co.capcom.residentevil.en",
            "CFBundleVersion": "1.03.00", "CFBundleExecutable": "game"}
    # The fixture only validates import semantics, not runnable guest behavior.
    executable = struct.pack("<12I", 0xfeedface, 12, 6, 2, 1, 20, 0, 0x21, 20, 0, 0, 0)
    with zipfile.ZipFile(ipa, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in {"Info.plist": plistlib.dumps(info), "game": executable,
                           "main.dz": b"unchanged resource", "intro.mp4": b"fixture"}.items():
            archive.writestr("Payload/game.app/" + name, data)
    digest = hashlib.sha256(ipa.read_bytes()).hexdigest()
    assert digest in run("import", str(ipa))
    ipa.unlink()
    assert digest in run("check")
    installation = path / "data/redegpc/installations" / digest
    manifest = plistlib.loads((installation / "manifest.plist").read_bytes())
    for name, expected in manifest["FilesSHA256"].items():
        assert hashlib.sha256((installation / name).read_bytes()).hexdigest() == expected
    (installation / "Payload/game.app/main.dz").write_bytes(b"tampered")
    assert "hash mismatch" in run("check", success=False)
    assert "MPL" in run("--copyright")
print("CLI_VERIFICATION_PASSED")
