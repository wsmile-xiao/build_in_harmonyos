#!/usr/bin/env python3
"""Conan test_package for libnfs-tools 5.0.3 (L1 official test).

libnfs-tools is a CLI tool set (nfs-ls/nfs-cat/nfs-cp/nfs-stat) — there is
no library to link against.  The consumer tests therefore run the four
packaged binaries and assert real behaviour (R34 substantive dependency):

  1. Each tool with no arguments must print its usage line (proves the
     binary loads and executes on the target platform).
  2. HarmonyOS-specific checks (R53) via ohos_specific_test.py: ELF64 ARM
     aarch64 identity, .codesign section present, interpreter
     ld-musl-aarch64.so.1, no build-tree RPATH/RUNPATH leakage.
"""
import os

from conan import ConanFile


class LibnfsToolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = ("ohos_specific_test.py",)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        pkg = self.dependencies[self.tested_reference_str]
        bindir = os.path.join(pkg.package_folder, "bin")

        expected_usage = {
            "nfs-ls": "Usage: nfs-ls",
            "nfs-cat": "Usage: nfs-cat",
            "nfs-cp": "Usage: nfs-cp",
            "nfs-stat": "Usage: nfs-stat",
        }

        for tool, usage in expected_usage.items():
            path = os.path.join(bindir, tool)
            if not os.path.isfile(path):
                raise Exception(f"expected CLI not packaged: {path}")
            outfile = os.path.join(self.build_folder, f"{tool}.out")
            self.run(f'{bash} -c "{path} > {outfile} 2>&1"',
                     ignore_errors=True, env="conanrun")
            with open(outfile, "r", errors="replace") as fh:
                out = fh.read()
            if usage not in out:
                raise Exception(
                    f"{tool} did not print usage ({usage!r}): {out[:200]!r}"
                )
            self.output.info(f"CLI smoke OK: {tool} -> {usage}")

        # R53 — HarmonyOS-specific structural suite (independent, fail closed)
        python = os.environ.get("CONAN_TEST_PYTHON3", "") or "python3"
        self.run(
            f'"{python}" "{self.source_folder}/ohos_specific_test.py" "{bindir}"',
            env="conanrun",
        )
