#!/usr/bin/env python3
"""Build a cdb dictionary for the dbskkd-cdb consumer test.

usage: make_dict.py <SKK-JISYO file> <output .cdb> <cdb tools bin dir>

The .cdb database is a binary fixture, and this repository must not carry new
binary files inside a PR: the CI `checkout-pr` step applies the
platform-generated PR diff with `git apply`, and that diff contains no
`GIT binary patch` data for added binary files ("error: missing binary patch
data for ..."), which fails the checkout before anything is built. The
dictionary is therefore rebuilt here, at test time, from the committed
plain-text SKK-JISYO fixture.

Conversion rule — identical to the upstream skktocdbm.sh (awk) that ships with
dbskkd-cdb:

  * lines starting with ";" and empty lines are skipped;
  * every other line is split at its first space into key and data;
  * the result line is "+<len(key)>,<len(data)>:<key>-><data>" with *byte*
    lengths (the awk script runs under LC_ALL=C);
  * the input is terminated by an empty line.

The cdbmake input text is written next to the .cdb file (with a .cdbmake
suffix) so that test.sh can compare it byte for byte against the committed
golden file fixtures/SKK-JISYO.test.cdbmake.

Writing the database itself is delegated to `cdbmake` from the cdb package —
the reference implementation of the very library the server links against —
instead of re-implementing the cdb hash table layout here.
"""
import os
import subprocess
import sys


def convert(skk_jisyo_bytes):
    """SKK-JISYO bytes -> cdbmake input bytes (same rule as skktocdbm.sh)."""
    out = []
    for raw_line in skk_jisyo_bytes.split(b"\n"):
        if not raw_line or raw_line.startswith(b";"):
            continue
        text = raw_line.decode("utf-8")
        pos = text.find(" ")
        if pos <= 0:
            raise SystemExit(
                f"[fail] make_dict: dictionary line without a key/data separator: {text!r}"
            )
        key, data = text[:pos], text[pos + 1:]
        out.append(
            "+%d,%d:%s->%s" % (
                len(key.encode("utf-8")), len(data.encode("utf-8")), key, data
            )
        )
    return ("\n".join(out) + "\n\n").encode("utf-8")


def main(argv):
    if len(argv) != 4:
        raise SystemExit(__doc__)
    skk_jisyo, out_cdb, tools_bin = argv[1], argv[2], argv[3]

    with open(skk_jisyo, "rb") as handle:
        source = handle.read()
    cdbmake_input = convert(source)
    input_path = out_cdb + ".cdbmake"
    with open(input_path, "wb") as handle:
        handle.write(cdbmake_input)

    cdbmake = os.path.join(tools_bin, "cdbmake")
    if not os.path.isfile(cdbmake) or not os.access(cdbmake, os.X_OK):
        raise SystemExit(f"[fail] make_dict: cdbmake not executable: {cdbmake}")

    tmp = out_cdb + ".tmp"
    for stale in (out_cdb, tmp):
        if os.path.exists(stale):
            os.unlink(stale)
    result = subprocess.run(
        [cdbmake, out_cdb, tmp], input=cdbmake_input,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        sys.stdout.write(result.stdout.decode("utf-8", "replace"))
        raise SystemExit(f"[fail] make_dict: cdbmake failed with rc={result.returncode}")
    if not os.path.isfile(out_cdb) or os.path.getsize(out_cdb) == 0:
        raise SystemExit(f"[fail] make_dict: cdbmake produced no database: {out_cdb}")

    print("[step] make_dict: %s (%d bytes) from %s"
          % (out_cdb, os.path.getsize(out_cdb), os.path.basename(skk_jisyo)))
    print("[step] make_dict: cdbmake input %s (%d bytes)"
          % (input_path, len(cdbmake_input)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
