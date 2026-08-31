#!/usr/bin/env python3
# test_package/conanfile.py — mdds/3.2.1
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class MddsTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # Resolve the real OHOS aarch64 clang dynamically — same principle as
        # the main recipe. The profile may pin a device path that does not
        # exist in this build sandbox; fall back to PATH lookup of the same
        # compiler name. Never hardcode user/storage paths.
        def resolve_compiler(lang):
            raw = self.conf.get("tools.build:compiler_executables", check_type=dict)
            cand = None
            if raw:
                cand = raw.get(lang) or raw.get(lang.upper())
            if cand and os.path.isfile(cand):
                return cand
            base = os.path.basename(cand) if cand else ("clang" if lang == "c" else "clang++")
            return shutil.which(base)
        def assert_ohos_aarch64(path, label):
            assert path and os.path.isfile(path), f"{label} not found: {path!r}"
            r = subprocess.run([path, "-print-target-triple"],
                               capture_output=True, text=True)
            triple = (r.stdout or "").strip()
            assert triple == "aarch64-unknown-linux-ohos", (
                f"{label} is not an OHOS aarch64 compiler "
                f"(triple={triple!r}, path={path!r})")
            assert r.returncode == 0, f"{label} -print-target-triple failed"
        cc = resolve_compiler("c")
        cxx = resolve_compiler("cpp")
        assert_ohos_aarch64(cc, "CC")
        assert_ohos_aarch64(cxx, "CXX")
        tc.variables["CMAKE_C_COMPILER"] = cc
        tc.variables["CMAKE_CXX_COMPILER"] = cxx
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Do not override the system name: let CMakeToolchain honour the
        # profile (HarmonyOS). OHOS must not be disguised as Linux.
        tc.generate()
    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the compiled test binary on the real OHOS aarch64 target.
        cmd = os.path.join(self.build_folder, "test_mdds")
        self.run(cmd, env="conanrun")
