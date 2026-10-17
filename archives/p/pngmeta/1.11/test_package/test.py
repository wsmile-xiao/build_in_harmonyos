#!/usr/bin/env python3
"""Consumer-side test for pngmeta 1.11.

Builds a small PNG carrying a tEXt and a tIME chunk, then checks that
pngmeta reports that metadata in its plain, SOIF, RDF/XML and HTML output.

Usage: test.py <bindir>
"""
import os
import platform
import struct
import subprocess
import sys
import tempfile
import zlib

TITLE = "PngmetaOhosCheck"
AUTHOR = "build_in_harmonyos"

_ELF_MACHINES = {0x03: "x86", 0x28: "arm", 0x3E: "x86_64", 0xB7: "aarch64", 0xF3: "riscv"}
_HOST_ALIASES = {"arm64": "aarch64", "amd64": "x86_64"}


def elf_machine(header):
    """Target architecture recorded in an ELF header (e_machine)."""
    order = "<" if header[5] == 1 else ">"      # EI_DATA: 1 = little endian
    (machine,) = struct.unpack(order + "H", header[18:20])
    return _ELF_MACHINES.get(machine, hex(machine))


def _chunk(tag, payload):
    body = tag + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body))


def make_png(path):
    """A 1x1 greyscale PNG with tEXt (before IDAT) and tIME (after IDAT)."""
    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 0, 0, 0, 0)
    idat = zlib.compress(b"\x00\x00")
    data = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"tEXt", b"Title\x00" + TITLE.encode())
        + _chunk(b"tEXt", b"Author\x00" + AUTHOR.encode())
        + _chunk(b"IDAT", idat)
        + _chunk(b"tIME", struct.pack(">HBBBBB", 2026, 9, 20, 12, 30, 45))
        + _chunk(b"IEND", b"")
    )
    with open(path, "wb") as fh:
        fh.write(data)


def run(pngmeta, args):
    try:
        proc = subprocess.run([pngmeta] + args, capture_output=True, text=True,
                              stdin=subprocess.DEVNULL)
    except OSError as exc:              # e.g. "Exec format error" without binfmt
        return 126, "", str(exc)
    return proc.returncode, proc.stdout, proc.stderr


def target_runnable(pngmeta):
    """Can this machine execute the packaged binary at all?

    `pngmeta --version` prints its banner (to stderr) and exits 1, so the
    banner — not the exit status — tells us whether the program ran.  When
    the package is cross-built for another architecture the loader or binfmt
    handler reports the failure instead, and the runtime checks below cannot
    be performed on this machine.
    """
    _, out, err = run(pngmeta, ["--version"])
    blob = out + err
    return ("built with libpng" in blob), blob.strip()


def main():
    if len(sys.argv) != 2:
        print("usage: test.py <bindir>", file=sys.stderr)
        return 2
    bindir = sys.argv[1]
    pngmeta = os.path.join(bindir, "pngmeta")

    # ── artifact checks (also the L1e negative test hook) ──
    # No os.access(X_OK) check: on HMDFS the mode bits are fixed and X_OK is
    # always False even for binaries that execute fine (see E524).
    assert os.path.isfile(pngmeta), f"missing binary: {pngmeta}"
    with open(pngmeta, "rb") as fh:
        header = fh.read(20)
    assert header[:4] == b"\x7fELF", f"not an ELF binary: {pngmeta}"
    target = elf_machine(header)
    host = platform.machine().lower()
    host = _HOST_ALIASES.get(host, host)
    print(f"[ok] artifact: {pngmeta} ({target} ELF, {host} host)")

    runnable, banner = target_runnable(pngmeta)
    if not runnable:
        first = banner.splitlines()[0] if banner else "(none)"
        if target == host:
            # Same architecture: nothing excuses a binary that does not run.
            print(f"[FAIL] {pngmeta} does not run on its own architecture: {first}")
            return 1
        print(f"[SKIP] runtime checks: a {host} host cannot execute the {target} binary")
        print(f"       probe output: {first}")
        print(f"       artifact checks passed; the runtime checks run on {target} hosts (CI)")
        return 0
    print(f"[ok] version banner: {banner.splitlines()[0]}")

    tmpdir = tempfile.mkdtemp(prefix="pngmeta-test-")
    sample = os.path.join(tmpdir, "sample.png")
    make_png(sample)

    # ── runtime checks ──
    rc, out, err = run(pngmeta, ["-quiet", sample])
    if rc != 0 and not out:
        print(f"[FAIL] pngmeta could not read {sample}: rc={rc} err={err.strip()}")
        return 1
    assert f"Title: {TITLE}" in out, f"tEXt Title missing from plain output:\n{out}"
    assert f"Author: {AUTHOR}" in out, f"tEXt Author missing from plain output:\n{out}"
    assert "Modification Time:" in out, f"tIME missing from plain output:\n{out}"
    print("[ok] plain output carries tEXt keywords and tIME")

    rc, out, _ = run(pngmeta, ["-soif", "-quiet", "-all", sample])
    assert "image-format{3}:\tPNG" in out, f"SOIF image-format missing:\n{out}"
    assert "image-width{1}:\t1" in out, f"SOIF image-width missing:\n{out}"
    assert f"Title{{{len(TITLE)}}}:\t{TITLE}" in out, f"SOIF Title missing:\n{out}"
    print("[ok] SOIF output carries IHDR geometry and tEXt keywords")

    rc, out, _ = run(pngmeta, ["-xrdf", "-quiet", sample])
    assert "<rdf:RDF" in out, f"RDF/XML header missing:\n{out}"
    assert "<png:Image rdf:about=" in out, f"RDF/XML subject missing:\n{out}"
    assert f"<png:Title>{TITLE}</png:Title>" in out, f"RDF/XML Title missing:\n{out}"
    print("[ok] RDF/XML output is well-formed and carries tEXt keywords")

    rc, out, _ = run(pngmeta, ["-html", "-quiet", sample])
    assert "<html>" in out and "</html>" in out, f"HTML skeleton missing:\n{out}"
    assert f"<dd>{TITLE}</dd>" in out, f"HTML Title missing:\n{out}"
    print("[ok] HTML output carries tEXt keywords")

    # A non-PNG input must be rejected rather than silently accepted.
    junk = os.path.join(tmpdir, "junk.png")
    with open(junk, "wb") as fh:
        fh.write(b"definitely not a png")
    rc, out, _ = run(pngmeta, ["-quiet", junk])
    assert rc != 0, "pngmeta accepted a non-PNG file"
    print("[ok] non-PNG input rejected")

    print("pngmeta 1.11: all consumer-side checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
