#!/usr/bin/env python3
"""Pure-stdlib minimal .deb assembler (build-time test scaffolding only).

Usage: python hmbs_deb_assemble.py <srcdir> <out.deb>

Reads <srcdir>/DEBIAN/control and the <srcdir>/usr tree, writes a .deb
ar container with members debian-binary / control.tar / data.tar
(uncompressed members are accepted by libdpkg checkIsDeb; ownership and
compression are irrelevant to the exit-code assertions of the
debsig-verify autotest suite).

Like hmbs_gpg_shim.py this file is staged into the build directory and
invoked through the interpreter (no +x needed under chmod=0); it is NEVER
installed into the package.
"""

import io
import os
import sys
import tarfile


def ar_header(name, size, mtime=0, uid=0, gid=0, mode=0o100644):
    """60-byte GNU ar member header; short names as 'name/' + spaces."""
    if len(name) > 15:
        raise ValueError("ar member name too long: %r" % name)
    head = "%-16s%-12d%-6d%-6d%-8o%-10d`\n" % (
        name + "/", mtime, uid, gid, mode, size)
    raw = head.encode("ascii")
    if len(raw) != 60:
        raise ValueError("bad ar header length for %r" % name)
    return raw


def make_tar(filemap, mtime=0):
    """filemap: [(arcname, bytes)] -> USTAR tar bytes (deterministic)."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w",
                      format=tarfile.USTAR_FORMAT) as tar:
        for arcname, data in filemap:
            info = tarfile.TarInfo(arcname)
            info.size = len(data)
            info.mtime = mtime
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def build_deb(srcdir, outdeb):
    with open(os.path.join(srcdir, "DEBIAN", "control"), "rb") as f:
        control = f.read()
    data_files = []
    usr = os.path.join(srcdir, "usr")
    if os.path.isdir(usr):
        for root, dirs, files in os.walk(usr):
            dirs.sort()
            for filename in sorted(files):
                full = os.path.join(root, filename)
                rel = os.path.relpath(full, srcdir).replace(os.sep, "/")
                with open(full, "rb") as f:
                    data_files.append((rel, f.read()))
    control_tar = make_tar([("control", control)])
    data_tar = make_tar(data_files)
    members = [("debian-binary", b"2.0\n"),
               ("control.tar", control_tar),
               ("data.tar", data_tar)]
    with open(outdeb, "wb") as f:
        f.write(b"!<arch>\n")
        for name, data in members:
            f.write(ar_header(name, len(data)))
            f.write(data)
            if len(data) % 2:
                f.write(b"\n")
    size = os.path.getsize(outdeb)
    if size == 0:
        raise ValueError("wrote empty deb: %s" % outdeb)
    return [(name, len(data)) for name, data in members]


def main(argv):
    if len(argv) != 3:
        sys.stderr.write("usage: hmbs_deb_assemble.py <srcdir> <out.deb>\n")
        return 2
    members = build_deb(argv[1], argv[2])
    sys.stdout.write("hmbs-assembler: wrote %s members=%s\n"
                     % (argv[2], ",".join(
                         "%s:%d" % (n, s) for n, s in members)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
