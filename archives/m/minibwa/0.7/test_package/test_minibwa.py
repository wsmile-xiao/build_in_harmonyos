#!/usr/bin/env python3
"""Consumer checks for the installed minibwa package.

Stage 1 (CLI): run the upstream README chrM workflow with the packaged
binary and packaged test data — version, index, paired-end map — and
verify the SAM output shape (record count, mandatory NM tag).

Stage 2 (library): compile a C consumer (generated at generate() time
from the upstream api-test/ex-one.c pattern) against the packaged
libminibwa.a + minibwa.h, then run it on the same data and verify the
PAF-like output record counts.

Stage 3 (ELF): the packaged binary is AArch64 OHOS musl and carries a
.code-sign section (package-time self-signing).
"""

import os
import shutil
import subprocess
import sys
import tempfile


checks = 0


def check(condition, message):
    global checks
    if not condition:
        raise AssertionError(message)
    checks += 1


def run(args, cwd=None, timeout=600):
    return subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def main():
    if len(sys.argv) != 3:
        raise SystemExit(
            "usage: test_minibwa.py <package-dir> <test-source-dir>"
        )

    package = os.path.abspath(sys.argv[1])
    src_dir = os.path.abspath(sys.argv[2])

    minibwa = os.path.join(package, "bin", "minibwa")
    check(os.path.isfile(minibwa), "minibwa binary is missing from the package")

    testdata = os.path.join(package, "share", "minibwa", "test")
    fasta = os.path.join(testdata, "chrM-human.fa.gz")
    read1 = os.path.join(testdata, "chrM-read_1.fa.gz")
    read2 = os.path.join(testdata, "chrM-read_2.fa.gz")
    for path in (fasta, read1, read2):
        check(os.path.isfile(path), f"test data {os.path.basename(path)} is missing")

    # Stage 0: ELF properties of the packaged CLI.
    with open(minibwa, "rb") as stream:
        head = stream.read(20)
    check(head[:4] == b"\x7fELF", "minibwa is not an ELF binary")
    check(head[4] == 2, "minibwa is not ELF64")
    check(head[5] == 1, "minibwa is not little-endian")
    check(head[18] == 0xb7, "minibwa is not AArch64 (EM_AARCH64)")
    readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
    if readelf:
        result = run([readelf, "-S", minibwa])
        check(
            ".codesign" in (result.stdout or ""),
            "minibwa ELF lacks the OHOS .codesign section",
        )

    work = tempfile.mkdtemp(prefix="minibwa-test-")
    try:
        # Stage 1: upstream README workflow — version, index, map.
        result = run([minibwa, "version"])
        check(result.returncode == 0, "minibwa version failed")
        check(
            (result.stdout or "").strip() == "0.7-r421",
            "minibwa version output mismatch",
        )

        index_prefix = os.path.join(work, "chrM-human")
        result = run([minibwa, "index", fasta, index_prefix])
        check(result.returncode == 0, "minibwa index failed")
        check(
            os.path.isfile(index_prefix + ".l2b"),
            "minibwa index did not produce the .l2b index",
        )

        sam_path = os.path.join(work, "aln.sam")
        with open(sam_path, "wb") as sink:
            proc = subprocess.run(
                [minibwa, "map", index_prefix, read1, read2],
                stdout=sink,
                stderr=subprocess.PIPE,
                timeout=600,
            )
        check(proc.returncode == 0, "minibwa map failed")
        with open(sam_path, encoding="utf-8") as stream:
            lines = [line.rstrip("\n") for line in stream]
        records = [line for line in lines if not line.startswith("@")]
        check(len(records) >= 2000, f"map produced only {len(records)} SAM records")
        # Every mapped record must carry an NM tag; unmapped mates
        # (FLAG 0x4, e.g. 133/165) legitimately have no NM.
        mapped = [line for line in records if int(line.split("\t", 2)[1]) & 0x4 == 0]
        n_nm = sum(1 for line in mapped if "\tNM:i:" in line)
        check(
            n_nm == len(mapped),
            f"only {n_nm}/{len(mapped)} mapped records carry the NM tag",
        )
        qnames = {line.split("\t", 1)[0] for line in records}
        check(len(qnames) == 1000, f"map covered {len(qnames)} unique QNAMEs")

        # Stage 2: library consumer (upstream api-test/ex-one.c pattern).
        consumer_src = os.path.join(src_dir, "mbconsumer.c")
        consumer = os.path.join(work, "mbconsumer")
        inc = os.path.join(package, "include", "minibwa")
        lib = os.path.join(package, "lib")
        check(
            os.path.isfile(os.path.join(inc, "minibwa.h")),
            "minibwa.h is missing from the package",
        )
        check(
            os.path.isfile(os.path.join(lib, "libminibwa.a")),
            "libminibwa.a is missing from the package",
        )
        # kseq.h ships alongside minibwa.h in the package for the documented
        # streaming API; zlib flags come from VirtualRunEnv (conanrun).
        check(
            os.path.isfile(os.path.join(inc, "kseq.h")),
            "kseq.h is missing from the package",
        )

        # CI injects the cross toolchain via MINIBWA_TEST_CC (from Conan conf
        # tools.build:compiler_executables); fall back to host env/PATH.
        cc = (
            os.environ.get("MINIBWA_TEST_CC")
            or os.environ.get("CC")
            or shutil.which("clang")
            or shutil.which("gcc")
        )
        check(cc is not None, "no C compiler found for the consumer build")
        zlib_info = os.environ.get("ZLIB_ROOT", "")
        link = [os.path.join(lib, "libminibwa.a"), "-lz", "-lpthread", "-lm"]
        if zlib_info and os.path.isdir(os.path.join(zlib_info, "lib")):
            link.insert(1, f"-L{os.path.join(zlib_info, 'lib')}")
        result = run(
            [cc, "-std=gnu99", "-O2", f"-I{inc}", consumer_src] + link + [
                "-o", consumer,
            ]
        )
        check(
            result.returncode == 0,
            f"consumer compile failed: {(result.stderr or '')[-500:]}",
        )

        result = run([consumer, index_prefix, read1])
        check(result.returncode == 0, "consumer mb_map run failed")
        stderr = result.stderr or ""
        check("RECORDS=1000" in stderr, f"consumer records mismatch: {stderr[-200:]}")
        paf_lines = [line for line in (result.stdout or "").splitlines() if line]
        check(len(paf_lines) >= 1000, f"consumer produced {len(paf_lines)} hits")

        print(
            f"PASS: minibwa packaged consumer test ({checks} assertions)"
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
