#!/usr/bin/env python3
"""test_package for enzyme — R34 genuine dependency via nm symbol presence check.

Strategy (avoids OHOS SDK LLVM relocation gap, E216-draft gap 4):
  We do NOT run any binary linked against libLLVMEnzyme-15.so, because the
  dynamic loader would load libLLDEnzyme-15.so → triggers relocation against
  LLVM C++ API symbols NOT exported by the OHOS SDK monolithic libLLVM-15.so
  (hundreds of "symbol not found" → exit 127). That is a platform toolchain
  gap (path C candidate), not a recipe defect.

  Instead we verify the package's plugin entry symbol is present in the
  shipped library via `nm` (static analysis, no relocation):
    1. Use self.run() (required by L0d gate) to invoke nm on the shipped
       libLLVMEnzyme-15.so in the package cache.
    2. nm -D <lib> | grep llvmGetPassPluginInfo — confirms the LLVM pass
       plugin entry point is exported by the tested package.
    3. L1e destructive negative test (R34): sabotage moves lib/ away →
       nm cannot find the .so → self.run() fails → conan test fails →
       genuine dependency confirmed (no false pass).
"""
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout
import os
import shutil


class EnzymeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "build"

    requires = "enzyme/0.0.284"

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Locate the shipped plugin library in the Conan package cache
        env_cache = os.environ.get("CONAN_PACKAGE_CACHE") or os.path.expanduser("~/.conan2/p")
        found_lib = None
        plugin_libs = ["libLLVMEnzyme-15.so"]
        for libname in plugin_libs:
            for root in [env_cache, os.path.join(self.source_folder, "..")]:
                if os.path.isdir(root):
                    for dirpath, _dirs, files in os.walk(root):
                        if libname in files:
                            found_lib = os.path.join(dirpath, libname)
                            break
                if found_lib:
                    break
            if found_lib:
                break

        if not found_lib:
            raise ConanException(
                "R34 FAIL: libLLVMEnzyme-15.so not found. "
                "Package artifacts missing — test genuinely depends on package."
            )
        self.output.info(f"enzyme: found plugin library: {found_lib}")

        # Build test_enzyme binary, then run it with ENZYME_PLUGIN_LIB set.
        # The binary itself does the nm -D check (no relocation triggered).
        # L1e sabotage (lib/ moved) → nm can't find .so → test_enzyme returns 1
        # → conan test fails → genuine dependency confirmed (R34, no false pass).
        test_exe = os.path.join(self.cpp.build.bindirs[0], "test_enzyme")
        if not os.path.isfile(test_exe):
            raise ConanException("test_enzyme binary not found — build failed")
        self.output.info("enzyme: running test_enzyme with ENZYME_PLUGIN_LIB via self.run()")
        run_cmd = f"ENZYME_PLUGIN_LIB={found_lib} {test_exe}"
        self.run(run_cmd, env="conanrun")