#!/usr/bin/env python3
"""Consumer test for liquidfun 1.1.0."""

import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LiquidfunTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # OHOS: wrap the cross-built ELF with bash (mksh cannot exec it),
        # extend LD_LIBRARY_PATH with the SDK libc++ triplet dirs.
        bash = os.environ.get("CONFIG_SHELL") or next(
            (p for p in ("/data/service/hnp/bin/bash", "/bin/bash") if os.path.exists(p)),
            "bash",
        )
        ld_paths = []
        base = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        if not os.path.isdir(base):
            cands = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"))
            base = cands[0] if cands else ""
        if base:
            for sub in ("aarch64-linux-ohos", "aarch64-linux-ohos/c++"):
                d = os.path.join(base, sub)
                if os.path.isdir(d):
                    ld_paths.append(d)
        binary = os.path.join(self.cpp.build.bindirs[0], "test_liquidfun")
        self.run(
            'LD_LIBRARY_PATH=%s:$LD_LIBRARY_PATH %s -c "%s"'
            % (":".join(ld_paths), bash, binary),
            env="conanrun",
        )
