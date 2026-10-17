#!/usr/bin/env python3
"""Compile a minimal SWF with swfc and inspect it with swfdump."""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


EXPECTED_TOOLS = (
    "wav2swf",
    "png2swf",
    "swfcombine",
    "swfstrings",
    "swfextract",
    "swfdump",
    "swfc",
    "swfbbox",
    "font2swf",
    "swfrender",
    "as3compile",
    "swfbytes",
    "ttftool",
)


def run(command, cwd=None):
    result = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"command failed ({result.returncode}): {command}\n{result.stdout}"
        )
    return result.stdout


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: test_swftools.py BIN_DIR SAMPLE_SC")

    bin_dir = Path(sys.argv[1])
    sample = Path(sys.argv[2])
    for tool in EXPECTED_TOOLS:
        assert (bin_dir / tool).is_file(), f"missing packaged tool: {tool}"

    version = run([str(bin_dir / "swfc"), "--version"])
    assert "swfc" in version.lower(), version
    assert "0.9.2" in version, version

    with tempfile.TemporaryDirectory(prefix="swftools-test-") as tmp:
        workdir = Path(tmp)
        input_sc = workdir / "smoke.sc"
        output_swf = workdir / "smoke.swf"
        shutil.copyfile(sample, input_sc)

        run(
            [str(bin_dir / "swfc"), "-o", str(output_swf), str(input_sc)],
            cwd=workdir,
        )
        assert output_swf.is_file(), "swfc did not create smoke.swf"
        payload = output_swf.read_bytes()
        assert len(payload) > 8, "generated SWF is shorter than its header"
        assert payload[:3] in (b"FWS", b"CWS"), payload[:3]

        dump = run([str(bin_dir / "swfdump"), str(output_swf)], cwd=workdir)
        assert "[HEADER]" in dump, dump
        assert "File version: 6" in dump, dump
        assert "Frame count: 1" in dump, dump

    print("swftools end-to-end smoke test passed")


if __name__ == "__main__":
    main()
