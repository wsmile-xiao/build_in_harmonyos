#!/usr/bin/env python3
"""Conan test_package — msgpack 7.0.1 consumer serialization round-trip test.

Packs a mixed array [int, bool, str], unpacks it back, and asserts each
deserialized value equals the original — using the real 7.0.1 public C API.
Only links against the Conan package's libmsgpack-c.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import load, save


class MsgpackTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        self._redirect_ci_compilers()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _redirect_ci_compilers(self):
        """Rewrite hnp compiler paths baked into generator artifacts.

        Mirrors the library recipe: the OHOS profile pins the compiler to
        /data/service/hnp/bin/clang (CI-only). On a dev box CMake configure
        fails with "not a full path to an existing compiler". When the hnp
        prefix is absent, rewrite conan_toolchain.cmake + conanbuildenv *.sh to
        the local clang/clang++/bash. No-op on CI. Never touches ci/.
        """
        if os.path.exists("/data/service/hnp/bin/clang"):
            return
        bash = shutil.which("bash") or "bash"
        cc = shutil.which("clang") or "clang"
        cxx = shutil.which("clang++") or "clang++"
        gen = getattr(self, "generators_folder", "") or ""
        if not gen or not os.path.isdir(gen):
            return
        for name in os.listdir(gen):
            path = os.path.join(gen, name)
            if not os.path.isfile(path):
                continue
            content = load(self, path)
            if "/data/service/hnp/bin/" not in content:
                continue
            content = content.replace("/data/service/hnp/bin/bash", bash)
            content = content.replace("/data/service/hnp/bin/clang++", cxx)
            content = content.replace("/data/service/hnp/bin/clang", cc)
            save(self, path, content)

    def test(self):
        # Run the compiled test binary directly so the consumer-side assertions
        # are actually exercised (self.run requires the binary on the PATH/run env).
        exe = os.path.join(self.cpp.build.bindirs[0], "test_msgpack")
        self.run(f'"{exe}"', env="conanrun")
