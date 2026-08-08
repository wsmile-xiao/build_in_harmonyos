#!/usr/bin/env python3
"""Conan test_package for muon — verifies the binary runs and parses a meson.build.

muon is a command-line build tool (application package), so the L1 test
executes the installed `muon` binary and runs `muon version` plus a real
`muon setup` on a minimal meson.build project (R34 substantive test).
"""
import os

from conan import ConanFile


class MuonTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # HarmonyOS: /system/bin/sh cannot parse muon's compiler-detection
        # scripts (E165-family); force a POSIX-compatible shell for child
        # processes spawned by muon.
        os.environ["SHELL"] = "/data/service/hnp/bin/bash"
        os.environ["CONFIG_SHELL"] = "/data/service/hnp/bin/bash"

        # Locate the installed muon binary via cpp_info.bindirs
        muon_bin = None
        for dep in self.dependencies.values():
            for bdir in dep.cpp_info.bindirs:
                cand = os.path.join(dep.package_folder, bdir, "muon")
                if os.path.exists(cand):
                    muon_bin = cand
                    break
        assert muon_bin, "muon binary not found in package"
        self.output.info(f"muon binary: {muon_bin}")

        # 1) version smoke test
        self.run(f'"{muon_bin}" version', env="conanrun")

        # 2) substantive test: parse a minimal meson.build project
        proj_dir = os.path.join(self.source_folder, "proj")
        os.makedirs(proj_dir, exist_ok=True)
        with open(os.path.join(proj_dir, "meson.build"), "w") as f:
            f.write(
                "project('smoke', 'c')\n"
                "executable('hello', 'main.c')\n"
            )
        with open(os.path.join(proj_dir, "main.c"), "w") as f:
            f.write("int main(void){return 0;}\n")
        os.makedirs(os.path.join(proj_dir, "build"), exist_ok=True)
        self.run(
            f'cd "{proj_dir}" && "{muon_bin}" setup build',
            env="conanrun",
        )
        self.run(
            f'cd "{proj_dir}" && "{muon_bin}" -C build samu',
            env="conanrun",
        )
        self.output.info("muon setup+compile on minimal project: OK")
