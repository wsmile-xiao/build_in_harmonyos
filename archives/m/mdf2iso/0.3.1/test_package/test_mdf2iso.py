#!/usr/bin/env python3
"""Exercise the packaged CLI and a real MDF-to-ISO conversion."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile


SYNC_HEADER = bytes([0x00] + [0xFF] * 10 + [0x00])
SYNC_HEADER_MDF = bytes(
    [0x80, 0xC0, 0x80, 0x80, 0x80, 0x80, 0x80, 0xC0, 0x80, 0x80, 0x80, 0x80]
)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: test_mdf2iso.py <mdf2iso-binary>")

    binary = Path(sys.argv[1]).resolve()
    assert binary.is_file(), f"mdf2iso binary not found: {binary}"
    assert os.access(binary, os.X_OK), f"mdf2iso binary is not executable: {binary}"

    help_result = subprocess.run(
        [str(binary), "--help"], capture_output=True, text=True, check=False
    )
    help_output = help_result.stdout + help_result.stderr
    assert help_result.returncode == 0, help_output
    assert "mdf2iso v0.3.1" in help_output
    assert "Usage :" in help_output
    assert "--cue" in help_output
    assert "--toc" in help_output
    print("PASS: CLI reports the expected version and conversion modes")

    with tempfile.TemporaryDirectory(prefix="mdf2iso-test-") as temp_dir:
        temp_path = Path(temp_dir)
        source_path = temp_path / "sample.mdf"
        output_path = temp_path / "sample.iso"

        expected_payload = bytes(index % 251 for index in range(2048))
        sector = bytearray(2448)
        sector[:12] = SYNC_HEADER
        sector[16:2064] = expected_payload
        sector[2352:2364] = SYNC_HEADER_MDF
        source_path.write_bytes(sector)

        convert_result = subprocess.run(
            [str(binary), str(source_path), str(output_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        convert_output = convert_result.stdout + convert_result.stderr
        assert convert_result.returncode == 0, convert_output
        assert "Created iso9660" in convert_output
        assert output_path.is_file(), "mdf2iso did not create the ISO output"
        assert output_path.read_bytes() == expected_payload, "converted ISO payload mismatch"
        print("PASS: MDF sector converts to the expected 2048-byte ISO payload")


if __name__ == "__main__":
    main()
