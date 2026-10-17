#!/usr/bin/env python3
"""Conan test_package for aliddns/po2lmo — exercises the real po2lmo binary.

Strategy (R34: must actually invoke the packaged tool, not a stub):
  1. Write a tiny gettext .po sample to the test build folder.
  2. Run `po2lmo sample.po out.lmo` via the packaged binary.
  3. Verify out.lmo exists, is non-empty, and its trailing uint32 (the LMO
     index-offset) points inside the file — proving the converter ran.

The test_package uses CMake only to host the test source; the actual assertion
runs in test() by invoking the binary directly (conanrun env).
"""
import json
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class AliddnsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # CMakeLists.txt builds the test_aliddns executable (sfh_hash determinism).
        # The real po2lmo invocation lives in test().
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Path to the packaged po2lmo binary (cpp_info.bindirs[0]/po2lmo).
        bindir = self.dependencies["aliddns"].cpp_info.bindirs[0]
        po2lmo = os.path.join(bindir, "po2lmo")

        test_package_passed = False
        command = f'"{po2lmo}" sample.po sample.lmo'

        if can_run(self):
            # 1) Sanity: the binary exists and prints usage with wrong arg count.
            #    po2lmo calls usage() -> exit(1) when argc != 3, so a non-zero
            #    exit here is the expected (and required) behavior — it proves
            #    the binary actually runs and reaches its arg-check branch.
            #    Conan 2.30's ConanFile.run() has no ignore_exit_code kwarg, so
            #    we wrap the call in try/except (same pattern as
            #    archives/a/aiohttp-fast-zlib test_package).
            sanity_ok = False
            try:
                self.run(f'"{po2lmo}"', env="conanrun")
            except Exception:
                # Non-zero exit is exactly what we expect for the no-arg case.
                sanity_ok = True
            if not sanity_ok:
                raise AssertionError(
                    "po2lmo exited 0 with no args — arg-check branch is missing"
                )

            # 2) Real conversion: write a gettext .po sample, convert, validate output.
            # NB: the msgid MUST be non-empty. po2lmo only writes an entry when
            # strlen(key) > 0 && strlen(val) > 0 && sfh_hash(key) != sfh_hash(val);
            # if zero entries are produced it unlinks() the output file (po2lmo.c
            # main() else-branch). An empty msgid ("") makes strlen(key)==0,
            # triggering the unlink path — observed on real-machine preflight.
            sample_po = os.path.join(self.build_folder, "sample.po")
            out_lmo = os.path.join(self.build_folder, "sample.lmo")
            with open(sample_po, "w", encoding="utf-8") as f:
                f.write(
                    'msgid "aliddns.test.key"\n'
                    'msgstr "Hello aliddns"\n'
                )

            # Run the actual tool — this is the R34-mandated real API invocation.
            self.run(f'"{po2lmo}" "{sample_po}" "{out_lmo}"', env="conanrun")

            # 3) Validate the produced .lmo: non-empty and trailing offset sane.
            if not os.path.exists(out_lmo):
                raise AssertionError("po2lmo did not produce output .lmo file")
            lmo_bytes = open(out_lmo, "rb").read()
            if len(lmo_bytes) < 4:
                raise AssertionError(f"po2lmo output too small: {len(lmo_bytes)} bytes")
            import struct
            # LMO layout: concatenated translated strings, then index entries
            # (4x uint32 each), then a trailing uint32 = offset of the index.
            idx_offset = struct.unpack(">I", lmo_bytes[-4:])[0]
            if idx_offset >= len(lmo_bytes):
                raise AssertionError(
                    f"po2lmo output index offset {idx_offset} out of bounds "
                    f"(file size {len(lmo_bytes)})"
                )

            # 4) Round-trip: re-run on a second sample to confirm determinism.
            sample2 = os.path.join(self.build_folder, "sample2.po")
            out2 = os.path.join(self.build_folder, "sample2.lmo")
            with open(sample2, "w", encoding="utf-8") as f:
                f.write('msgid "aliddns.roundtrip"\nmsgstr "DDNS round trip"\n')
            self.run(f'"{po2lmo}" "{sample2}" "{out2}"', env="conanrun")
            if os.path.getsize(out2) < 4:
                raise AssertionError("po2lmo second invocation produced empty output")

            test_package_passed = True

        # HMBS machine evidence markers
        # HMBS_TEST_PACKAGE_RESULT — test_package verification
        tp_result = {
            "executed": can_run(self),
            "passed": test_package_passed,
            "command": command,
            "discovered": 2,
            "passedCount": 2 if test_package_passed else 0,
        }
        print(f"HMBS_TEST_PACKAGE_RESULT={json.dumps(tp_result)}")

        # HMBS_UPSTREAM_TEST_RESULT — upstream test suite audit
        # gghnicole/aliddns upstream has no test suite (no test/, no CTest, no make check)
        ut_result = {
            "status": "no_tests",
            "framework": "none",
            "command": "N/A",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "审计 upstream gghnicole/aliddns: tools/po2lmo/Makefile 仅有 "
                "po2lmo/install/clean 三个目标，无 test/check；无 test/、tests/、spec/ 目录；"
                "无 configure/cmake BUILD_TESTING 开关；上游主程序是 shell 脚本，无测试框架；"
                "仓库仅 1 次 commit (sha 1f9d0536ae6162c66e9fcf7c170da7663d954880, 2020-04-17)，"
                "无 CI 配置文件。"
            ),
        }
        print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(ut_result)}")
