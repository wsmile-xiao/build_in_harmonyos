#!/usr/bin/env python3
"""Conan test_package — LocARNA 2.0.1 (OHOS/aarch64).

Layer 2 consumer + end-to-end test:

1. Verify the installed package layout (headers + static libLocARNA-2.0.a +
   LocARNA-2.0.pc + the locarna CLI in bin/).
2. Build and run test_liblocarna, which links the installed static
   libLocARNA-2.0 (pulling ViennaRNA transitively) and constructs a real
   LocARNA::Sequence, exercising the MultipleAlignment/SeqEntry API.
3. OHOS-specific: run the installed `locarna` CLI (`--version` and a real
   pairwise alignment of two FASTA files) to prove the native tools execute
   on HarmonyOS. This is the regression test for the AArch64 unsigned-char
   / getopt_long(EOF) bug fixed by patches/0001: before the fix every tool
   spun at 100% CPU with no output, so `--version` alone is a meaningful
   assertion.
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class LocarnaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _package_folder(self):
        return self.dependencies[self.tested_reference_str].package_folder

    def _check_package_layout(self):
        pkg = self._package_folder()
        checks = [
            ("LocARNA headers",
             os.path.join(pkg, "include", "LocARNA-2.0", "LocARNA", "sequence.hh")),
            ("static libLocARNA", os.path.join(pkg, "lib", "libLocARNA-2.0.a")),
            ("pkgconfig LocARNA-2.0", os.path.join(pkg, "lib", "pkgconfig", "LocARNA-2.0.pc")),
            ("locarna program", os.path.join(pkg, "bin", "locarna")),
            ("sparse program", os.path.join(pkg, "bin", "sparse")),
        ]
        missing = [name for name, path in checks if not os.path.exists(path)]
        if missing:
            raise ConanException("missing locarna package artifacts: " + ", ".join(missing))

    def _cli_smoke(self):
        """Run the installed CLI: --version plus a real pairwise alignment."""
        pkg = self._package_folder()
        locarna = os.path.join(pkg, "bin", "locarna")
        self.run(f'"{locarna}" --version')

        work = os.path.join(self.build_folder, "cli-smoke")
        os.makedirs(work, exist_ok=True)
        fa1 = os.path.join(work, "seq1.fa")
        fa2 = os.path.join(work, "seq2.fa")
        out = os.path.join(work, "aln.out")
        with open(fa1, "w", encoding="utf-8") as f:
            f.write(">seq1\nGGGGAAAACCCCUUUU\n")
        with open(fa2, "w", encoding="utf-8") as f:
            f.write(">seq2\nGGGGAAAACCCCUUUU\n")
        # 2>/dev/null: locarna is chatty on stderr in some modes; the alignment
        # itself is on stdout.
        self.run(f'"{locarna}" "{fa1}" "{fa2}" > "{out}" 2>/dev/null')
        with open(out, encoding="utf-8", errors="replace") as f:
            text = f.read()
        if "Score:" not in text:
            raise ConanException(f"locarna produced no alignment score:\n{text}")
        if text.count("GGGGAAAACCCCUUUU") < 2:
            raise ConanException(f"locarna alignment output missing sequences:\n{text}")
        self.output.info("locarna CLI pairwise alignment OK:")
        for line in text.strip().splitlines():
            self.output.info("    " + line)

    def test(self):
        self._check_package_layout()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if not can_run(self):
            self.output.info("Skipping run: cannot run target binaries in this context")
            self.output.info('HMBS_TEST_PACKAGE_RESULT={"executed":false,"passed":false,'
                             '"command":"test_liblocarna","discovered":1,"passedCount":0}')
            return
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_liblocarna")
        self.run(bin_path, env="conanrun")
        # End-to-end tool smoke test: the installed CLI must load and run.
        self._cli_smoke()
        note = "" if str(self.settings.os) != "OHOS" else ", \"note\":\"ohos_runtime_cli\""
        self.output.info('HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,'
                         '"command":' + json.dumps(bin_path) +
                         ',"discovered":2,"passedCount":2' + note + '}')
