#!/usr/bin/env python3
"""Conan test_package — rotter 0.9 (executable package).

Two HarmonyOS consumer-use checks:
1. consumer_test (C): a real C consumer links and calls the dependency stack
   rotter itself uses — libsndfile (WAV write/read roundtrip), lame (MP3
   encode/flush) and twolame (MP2 encode/flush) — proving the adapted
   dependency stack is consumable from third-party C code on HarmonyOS.
2. rotter smoke: actually executes the packaged `rotter` binary (--help),
   proving the built program runs on HarmonyOS (loader resolves libjack etc.).

CI runs this automatically via `conan create` (which invokes test_package).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class RotterTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # The consumer test links the codec/file stacks directly (same versions
        # rotter pins), so CMakeDeps generates their package configs.
        self.requires("libsndfile/1.2.2")
        self.requires("lame/3.100")
        self.requires("twolame/0.4.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # OHOS/HMDFS: shared libraries inside the conan cache may be unreadable
        # by the dynamic loader (uid/HMDFS quirk). Materialize owned copies of
        # the dependency shared libs next to the test binaries and point
        # LD_LIBRARY_PATH at them first (a harmless no-op on CI where the
        # cache is directly loadable).
        import glob
        import shutil

        bindirs = self.cpp.build.bindirs[0]
        rtlibs = os.path.join(bindirs, "rtlibs")
        os.makedirs(rtlibs, exist_ok=True)
        for dep in self.dependencies.host.values():
            for libdir in dep.cpp_info.libdirs:
                for so in glob.glob(os.path.join(libdir, "*.so*")):
                    shutil.copy2(so, rtlibs, follow_symlinks=True)

        # OHOS: /system/bin/sh (mksh) cannot exec ELF directly — use bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        runenv = f'LD_LIBRARY_PATH="{rtlibs}:$LD_LIBRARY_PATH"'

        # 1) Dependency-stack consumer test (conanrun env + rtlibs resolve the
        #    dependency shared libraries for the dynamic loader).
        consumer = os.path.join(bindirs, "rotter_consumer_test")
        self.run(f'{runenv} "{consumer}"', env="conanrun")

        # 2) Execute the packaged rotter binary.
        dep_bindir = self.dependencies[self.tested_reference_str].cpp_info.bindirs[0]
        rotter = os.path.join(dep_bindir, "rotter")
        # `rotter --help` prints the version banner and usage, then exits 1
        # (old getopt behavior) — accept both exit codes when the banner shows.
        cmd = (
            f'out=$("{rotter}" --help 2>&1); rc=$?; '
            'echo "$out" | head -3; '
            'case "$out" in *"rotter version 0.9"*) echo "[PASS] rotter --help smoke"; exit 0 ;; '
            '*) echo "[FAIL] rotter --help smoke (rc=$rc)"; exit 1 ;; esac'
        )
        self.run(f'{runenv} "{bash}" -c \'{cmd}\'', env="conanrun")
