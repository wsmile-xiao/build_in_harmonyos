#!/usr/bin/env python3
"""Conan test_package for shush 1.2.3 - HarmonyOS PC consumer test.

build(): compiles test_shush.c, a consumer program that plays three roles
(driver, sendmail(1) stand-in, supervised job), with the OHOS toolchain.

test(): runs the consumer against the packaged bin/shush.  It writes shush
configurations, lets shush supervise the consumer's own "job" role, deliver
reports to the consumer's "sendmail" role and checks the observable result
(cases C1-C8, see MANIFEST.yml).

The delivered binaries are dynamically linked against the OHOS musl loader
/lib/ld-musl-aarch64.so.1, so they only execute on an aarch64 host.  On an
x86_64 cross-building runner the runtime cases are reported as SKIP (never as
passed) after the artifact checks; the same test_shush.c is exercised there
through static relinks under qemu-aarch64 (notes.md).
"""
import os
import platform

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class ShushTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str, run=True)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        shush = os.path.join(self.dependencies["shush"].package_folder, "bin", "shush")
        consumer = os.path.join(self.build_folder, "test_shush")
        # Artifact checks run everywhere: removing bin/ must fail (CI L1e).
        for path in (shush, consumer):
            if not os.path.isfile(path):
                raise ConanException(f"missing executable: {path}")
            with open(path, "rb") as handle:
                if handle.read(4) != b"\x7fELF":
                    raise ConanException(f"not an ELF executable: {path}")

        machine = platform.machine().lower()
        if machine not in ("aarch64", "arm64"):
            self.output.warning(
                f"SKIP runtime cases C1-C8: host {machine} cannot execute the "
                "dynamically linked aarch64 OHOS binaries (missing "
                "/lib/ld-musl-aarch64.so.1); they run on the aarch64 CI worker")
            return

        workdir = os.path.join(self.build_folder, "shush-consumer")
        self.run(f'"{consumer}" run "{shush}" "{consumer}" "{workdir}"',
                 env="conanrun")
