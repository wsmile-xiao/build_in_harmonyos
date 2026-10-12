#!/usr/bin/env python3
"""Conan test_package — tta 2.2.

Upstream libtta 2.2 ships no formal automated-test framework (no make check /
ctest / TESTS target), but the release tarball DOES ship the `console/tta`
command-line encode/decode tool (bin_PROGRAMS = tta in console/Makefile.am).
Following the repo precedent for autotools packages without a formal harness
(ccrtp), we promote functional verification of the shipped upstream console
tool into the upstream regression suite and run it on the real device:

  case 1 : `tta -e in.wav out.tta`  — upstream console encoder
  case 2 : `tta -d out.tta back.wav` — upstream console decoder
  case 3 : decoded WAV bit-exact vs original (roundtrip)

test.c separately exercises the installed libtta.a public API directly
(consumerView) and prints HMBS_TEST_PACKAGE_RESULT from its own counters.

Both hard-gate JSON markers are emitted from genuinely executed commands:
  - HMBS_TEST_PACKAGE_RESULT is printed by test.c (tests_run/tests_failed).
  - HMBS_UPSTREAM_TEST_RESULT is printed here from the real encode/decode/
    roundtrip pass/fail counts of the upstream `tta` console tool.
"""
import json
import os
import shlex
import struct
import subprocess
import wave

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TtaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _gen_wav(self, path):
        """Write a deterministic 16-bit mono PCM WAV (8000 Hz) via stdlib."""
        sps = 8000
        nch = 1
        bouts = 2
        samples = 10000  # > MUL_FRAME_TIME(8000) -> multiple TTA frames
        with wave.open(path, "wb") as w:
            w.setnchannels(nch)
            w.setsampwidth(bouts)
            w.setframerate(sps)
            frames = bytearray()
            for i in range(samples):
                val = ((i * 3) % 20001) - 10000  # 16-bit signed, deterministic
                frames += struct.pack("<h", val)
            w.writeframes(bytes(frames))
        return path

    def _run_upstream_tests(self):
        """Promote the shipped upstream `console/tta` tool into an upstream
        regression suite: encode, decode, bit-exact roundtrip. Emits the
        HMBS_UPSTREAM_TEST_RESULT marker from real executed cases."""
        tta_pkg = self.dependencies["tta"].package_folder
        tta_bin = os.path.join(tta_pkg, "bin", "tta")
        if not os.path.isfile(tta_bin):
            # The upstream console tool is part of this static library's
            # package (bindirs -> bin); a malformed package has no tool to run.
            raise Exception(f"upstream console tool not found in package: {tta_bin}")

        workdir = self.build_folder or "."
        wav_in = os.path.join(workdir, "upstream_in.wav")
        tta_out = os.path.join(workdir, "upstream_out.tta")
        wav_back = os.path.join(workdir, "upstream_back.wav")

        # 1) generate deterministic WAV input (real, non-empty fixture)
        self._gen_wav(wav_in)

        def run_tool(cmd):
            """Run the upstream console tool, capturing stdout+stderr so a
            failure is diagnosable from the tool's own message rather than a
            bare exit code. Returns (returncode, combined_output-as-text)."""
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True,
                                      errors="replace")
                combined = (proc.stdout or "") + (proc.stderr or "")
                return proc.returncode, combined
            except Exception as e:  # pragma: no cover - e.g. exec failure
                return None, f"failed to exec {cmd!r}: {e}"

        cases = []  # (name, ok, note)

        # case 1: upstream console encoder
        # `tta -e in.wav out.tta` encodes the deterministic WAV -> TTA stream.
        enc_cmd = [tta_bin, "-e", wav_in, tta_out]
        enc_rc, enc_out = run_tool(enc_cmd)
        enc_note = (f"returncode={enc_rc} stdout/stderr: "
                    f"{shlex.quote(enc_out.strip()[:400])}") if enc_out.strip() \
                    else f"returncode={enc_rc}, no tool output"
        enc_ok = (enc_rc == 0) and os.path.isfile(tta_out) and \
                 os.path.getsize(tta_out) > 4
        enc_extra = (f"production produced {os.path.getsize(tta_out)}-byte stream"
                     if os.path.isfile(tta_out) else "no output file")
        cases.append(("encode (tta -e wav->tta)", enc_ok,
                      enc_note + " | " + enc_extra))

        # case 2: upstream console decoder
        # `tta -d out.tta back.wav` decodes the TTA stream back to WAV.
        dec_cmd = [tta_bin, "-d", tta_out, wav_back]
        dec_rc, dec_out = run_tool(dec_cmd)
        dec_note = (f"returncode={dec_rc} stdout/stderr: "
                    f"{shlex.quote(dec_out.strip()[:400])}") if dec_out.strip() \
                    else f"returncode={dec_rc}, no tool output"
        dec_ok = (dec_rc == 0) and os.path.isfile(wav_back) and \
                 os.path.getsize(wav_back) > 0
        dec_extra = (f"decoding produced {(os.path.getsize(wav_back) if os.path.isfile(wav_back) else 0)}-byte wav")
        cases.append(("decode (tta -d tta->wav)", dec_ok,
                      dec_note + " | " + dec_extra))

        # case 3: bit-exact roundtrip
        if dec_ok and os.path.isfile(wav_in):
            with open(wav_in, "rb") as f:
                orig = f.read()
            with open(wav_back, "rb") as f:
                back = f.read()
            rt_ok = (orig == back)
            rt_note = f"roundtrip {len(orig)}/{len(back)} bytes bit-exact" if rt_ok else \
                      f"roundtrip mismatch: orig {len(orig)}B vs decoded {len(back)}B"
            cases.append(("roundtrip bit-exact", rt_ok, rt_note))
        else:
            cases.append(("roundtrip bit-exact", False,
                          "skipped: decode did not produce a wav to compare"))

        # surface per-case outcome in the conan log
        for name, ok, note in cases:
            self.output.info(f"[upstream] {name}: {'PASS' if ok else 'FAIL'} ({note})")

        discovered = len(cases)
        passed = sum(1 for _, ok, _ in cases if ok)
        failed = discovered - passed
        executed = discovered
        status = "passed" if failed == 0 else "failed"
        up = {
            "status": status,
            "framework": "python_def",
            "command": f"{tta_bin} -e|-d <wav> <tta> (upstream console tool)",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(up, ensure_ascii=False))
        if failed != 0:
            raise Exception("upstream console-tool regression FAILED")

    def test(self):
        # consumer test: installed libtta.a via test.c (HMBS_TEST_PACKAGE_RESULT
        # is emitted by test.c itself, so it flows into the shared log).
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_tta")
        self.run(f'"{test_bin}"', env="conanrun")

        # upstream regression: shipped `console/tta` tool encode/decode/roundtrip
        self._run_upstream_tests()
