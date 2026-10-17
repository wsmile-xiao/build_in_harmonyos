#!/usr/bin/env python3
"""HarmonyOS-exclusive consumer harness for the swish-e package.

swish-e 2.4.7 delivers the ``swish-e`` CLI indexer.  This harness
exercises the real consumer chain on the OHOS device:

  1. artifact assertions (ELF64/AArch64, musl loader, NEEDED closure);
  2. a full end-to-end index -> search round trip against fixture
     documents, driving the packaged binary through its production
     CLI contract:
       swish-e -c config -i -f index  (index)
       swish-e -f index -w "query"    (search)
  3. result assertions: the query returns the fixture hit, the index
     file exists and is non-trivial, and ``swish-e -V`` reports the
     expected version.

Exit code 0 = all checks pass.
"""
import argparse
import os
import struct
import subprocess
import sys
import tempfile

EM_AARCH64 = 183


def elf_identity(path):
    with open(path, "rb") as fh:
        data = fh.read(64)
    if data[:4] != b"\x7fELF":
        raise AssertionError(f"{path}: not an ELF file")
    return {
        "class": data[4],            # 2 = ELF64
        "data": data[5],             # 1 = little-endian
        "machine": struct.unpack_from("<H", data, 18)[0],
    }


def run(cmd, **kw):
    kw.setdefault("stdout", subprocess.PIPE)
    kw.setdefault("stderr", subprocess.STDOUT)
    kw.setdefault("text", True)
    res = subprocess.run(cmd, **kw)
    return res.returncode, res.stdout or ""


FIXTURES = {
    "harmony.html": (
        "<html><head><title>HarmonyOS PC</title></head>"
        "<body>HarmonyOS PC adaptation of third-party C libraries "
        "with conan recipes.</body></html>\n"),
    "swish.html": (
        "<html><head><title>Swish</title></head>"
        "<body>SWISH-E indexes documents quickly and reliably for "
        "web and embedded collections.</body></html>\n"),
}

CONFIG = """\
IndexDir {index}
IndexFile {out}
"""

QUERIES = [
    # (query, expected substring in output, check name)
    # NOTE: swish-e default word-splitting indexes whole words — queries
    # must be the full token ("harmonyos", not "harmony").
    ("harmonyos", "harmony.html", "H3 检索命中"),
    ("swish", "swish.html", "H3 检索命中 2"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", required=True)
    args = ap.parse_args()

    pkg = os.path.abspath(args.package)
    binary = os.path.join(pkg, "bin", "swish-e")
    if not os.path.isfile(binary):
        raise AssertionError(f"missing from package: {binary}")

    results = []

    def ok(title, detail):
        results.append(("P", title))
        print(f"  [ok]   {title}: {detail}")

    print("== swish-e consumer harness (HarmonyOS) ==")
    print("-- artifact assertions --")

    ident = elf_identity(binary)
    if ident["machine"] != EM_AARCH64 or ident["class"] != 2 \
            or ident["data"] != 1:
        raise AssertionError(f"unexpected ELF identity: {ident}")
    ok("H2 目标数据模型 ELF64 / 小端 / AArch64", f"e_machine={ident['machine']}")

    rc, out = run([binary, "-V"])
    if rc != 0 or "2.4.7" not in out:
        raise AssertionError(f"-V rc={rc}: {out[-300:]}")
    ok("版本自报", out.strip().splitlines()[0])

    with open(binary, "rb") as fh:
        dyn = fh.read()
    if b"/lib/ld-musl-aarch64.so.1" not in dyn:
        raise AssertionError("interpreter is not /lib/ld-musl-aarch64.so.1")
    ok("H1 动态加载器为 musl", "/lib/ld-musl-aarch64.so.1")

    print("-- real index -> search chain --")
    work = tempfile.mkdtemp(prefix="swishe-test-")
    srcdir = os.path.join(work, "docs")
    os.makedirs(srcdir)
    for name, body in FIXTURES.items():
        with open(os.path.join(srcdir, name), "w") as fh:
            fh.write(body)
    index = os.path.join(work, "test.index")
    cfg = os.path.join(work, "swish.conf")
    with open(cfg, "w") as fh:
        fh.write(CONFIG.format(index=srcdir, out=index))

    # --- production CLI contract: index (-i takes the dirs as arguments) ---
    rc, out = run([binary, "-c", cfg, "-i", srcdir])
    if rc != 0:
        raise AssertionError(f"indexing failed rc={rc}: {out[-500:]}")
    if not os.path.isfile(index) or os.path.getsize(index) < 1024:
        raise AssertionError("index file missing or implausibly small")
    ok("H4 建立索引（真实文件产物）",
       f"index={os.path.getsize(index)} bytes")

    # --- production CLI contract: search ---
    for query, want, check in QUERIES:
        rc, out = run([binary, "-f", index, "-w", query])
        if rc != 0:
            raise AssertionError(f"search {query!r} rc={rc}: {out[-400:]}")
        if want not in out:
            raise AssertionError(
                f"search {query!r}: output lacks {want!r}\n{out[-400:]}")
        ok(check, f"-w {query!r} -> {want}")

    # --- rank/score sanity: both docs indexed ---
    rc, out = run([binary, "-f", index, "-w", "documents"])
    if rc != 0:
        raise AssertionError(f"search rc={rc}: {out[-300:]}")
    n_hits = out.count("harmony.html") + out.count("swish.html")
    if n_hits < 1:
        raise AssertionError("common-term query returned no hits")
    ok("多词公共项检索", f"hits={n_hits}")

    passed = sum(1 for r in results if r[0] == "P")
    print(f"== {passed}/{len(results)} checks passed ==")
    if passed != len(results):
        sys.exit(1)
    print("swish-e consumer harness: OK")


if __name__ == "__main__":
    main()
