#!/usr/bin/env python3
"""Conan test_package - mbuffer 20260511 (consumer-side verification).

mbuffer installs a CLI binary and no library, so a consumer here is somebody who
runs it.  Every check below feeds real data through the buffer and asserts on
what came out -- nothing merely prints or links.

  1. `mbuffer --version` reports the upstream build tag (binary is installed,
     loadable and executable).
  2. a 3 MiB stream survives the buffer byte-for-byte (independent digest of
     input == output, and the byte counts match).
  3. the throughput report is a real measurement, not a placeholder: the summary
     line exists and the rate is not 0.
  4. `--md5` prints the digest mbuffer computed over the bytes it forwarded,
     compared against the digest this test computes independently.
  5. forced-write / header mode (`-f -o <name> -H`) still yields a byte-identical
     copy of the stream (volume *switching* is upstream's own test4/test5 job,
     which needs tapetest.so to inject ENOSPC and runs inside build()).
  6. test_package/mbuffer_probe.sh repeats checks 2-4 from a plain shell
     consumer's point of view.

The 8 upstream tests (test0..test7) are not counted here -- they run inside
build(); see reports/test-report.md for the per-test verdicts.
"""
import hashlib
import os
import shutil

from conan import ConanFile
from conan.tools.files import load


def _stream(path, size_kib=3 * 1024):
    """Deterministic pseudo-random payload -- no dependency on /dev/urandom."""
    seed = 0x5D1E9C3B7A42
    with open(path, "wb") as fh:
        for _ in range(size_kib):
            block = bytearray()
            for _ in range(128):
                seed = (seed * 6364136223846793005 + 1442695040888963407) & ((1 << 64) - 1)
                block += seed.to_bytes(8, "little")
            fh.write(bytes(block))


def _md5(path):
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class MbufferTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 工作目录必须落在 PR 树之外：test_package 的 build_folder 在本框架下为空，
        # 回退到 recipe_folder 会把 3MiB 级可再生测试产物写进 archives/（JC1/JC2，
        # 且归档含二进制会让 CI checkout-pr 永久失败）。每轮先清掉自己上一轮的产物，
        # 因为设备不允许截断由更早进程创建的文件 —— 第二轮否则必挂 File exists。
        work = os.path.join(os.path.expanduser("~"), "tmp", "uc2",
                            "mbuffer-test_package")
        if os.path.isdir(work):
            shutil.rmtree(work, ignore_errors=True)
        os.makedirs(work)
        payload = os.path.join(work, "stream.bin")
        _stream(payload)
        want = _md5(payload)

        # 1. installed, loadable, and reports its build tag
        out = os.path.join(work, "version.txt")
        self.run('mbuffer --version > "%s" 2>&1' % out, env="conanrun")
        text = load(self, out)
        assert "R20260511" in text, "unexpected version banner: %r" % text[-300:]

        # 2. byte-for-byte round trip through the buffer
        sink = os.path.join(work, "sink.bin")
        self.run('mbuffer -q -s 100k -i "%s" -o "%s"' % (payload, sink), env="conanrun")
        assert os.path.getsize(sink) == os.path.getsize(payload), "byte count changed"
        assert _md5(sink) == want, "the buffer corrupted the payload"

        # 3. the throughput summary is a measurement
        stats = os.path.join(work, "stats.log")
        self.run('mbuffer -s 64k -i "%s" -o /dev/null > "%s" 2>&1' % (payload, stats),
                 env="conanrun")
        report = load(self, stats)
        assert "average of" in report, "no throughput summary in: %r" % report[-400:]
        assert "0.0 kiB/s" not in report.split("average of")[-1], \
            "mbuffer reported a zero transfer rate: %r" % report[-200:]

        # 4. mbuffer's own digest for the bytes it forwarded
        mdlog = os.path.join(work, "md5.log")
        self.run('mbuffer -q --md5 -i "%s" -o /dev/null > "%s" 2>&1' % (payload, mdlog),
                 env="conanrun")
        digest = load(self, mdlog)
        assert want in digest, \
            "mbuffer --md5 did not report %s, got: %r" % (want, digest[-400:])

        # 5. forced-write / header mode (-f -o <name> -H) must still hand back the
        #    exact byte stream.  It does NOT split into volumes by itself: upstream
        #    only exercises volume switching by injecting ENOSPC through tapetest.so,
        #    which is what upstream tests test4/test5 do inside build().  Asserting a
        #    volume count here would be testing the wrong thing.
        vol = os.path.join(work, "vol")
        self.run('rm -f "%s" "%s".*; mbuffer -q -s 256k -f -o "%s" -H '
                 '-i "%s" > /dev/null 2>&1' % (vol, vol, vol, payload), env="conanrun")
        parts = sorted(f for f in os.listdir(work)
                       if f == "vol" or f.startswith("vol."))
        assert parts, "-f -o <name> -H produced no output file at all"
        joined = os.path.join(work, "joined.bin")
        with open(joined, "wb") as dst:
            for p in parts:
                with open(os.path.join(work, p), "rb") as src:
                    dst.write(src.read())
        assert _md5(joined) == want, "forced-write out not byte-identical: %r" % (parts,)

        # 6. the same contract from a plain shell consumer
        probe = os.path.join(self.recipe_folder, "mbuffer_probe.sh")
        self.run('sh "%s" "%s"' % (probe, work), env="conanrun")
