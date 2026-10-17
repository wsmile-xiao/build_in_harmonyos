#!/usr/bin/env python3
"""Conan test_package template — Conan L1 official test.

This is the L1 test in the five-level test system.
CI runs this automatically via `conan create` (which invokes test_package).

File location: archives/l/libigloo/0.9.5/test_package/conanfile.py
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibiglooTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # VirtualRunEnv generates conanrun.sh, applied by env="conanrun" in test().
    # CMakeToolchain is generated manually in generate() (not via class-level
    # generators) so the compiler fix-up below lands BEFORE the toolchain file
    # bakes in CMAKE_C_COMPILER — class-level generators run before the
    # generate() method, which would make the fix-up too late.
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        """Fix up tools.build:compiler_executables before CMakeToolchain runs.

        The ohos-aarch64 CI profile pins CC to /data/service/hnp/bin/clang, a
        device-only path missing on the build host. CMakeToolchain bakes that
        dead path into conan_toolchain.cmake as CMAKE_C_COMPILER, so configure
        fails at the compiler-works check. Resolve to the first clang on PATH
        (shutil.which, nothing hard-coded) before generating the toolchain —
        mirroring the fix-up in the libigloo recipe's generate().
        """
        compilers = dict(self.conf.get("tools.build:compiler_executables", check_type=dict) or {})
        changed = False
        for lang, name in (("c", "clang"), ("cpp", "clang++")):
            pinned = compilers.get(lang)
            if pinned and not (os.path.isfile(pinned) and os.access(pinned, os.X_OK)):
                found = shutil.which(name)
                if not found:
                    raise ConanInvalidConfiguration(
                        f"test_package: profile compiler for {lang} ({pinned}) does "
                        f"not exist on this host and no {name} was found on PATH"
                    )
                compilers[lang] = found
                changed = True
        if changed:
            self.conf.define("tools.build:compiler_executables", compilers)
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info(
                "Cross-compiling: consumer binaries cannot execute on this "
                "host, deferring runtime validation to the OHOS runner"
            )
            return

        # Resolve the executables built by build() from the cmake_layout
        # folders (single-config: build/<build_type>, bindirs == ["."]);
        # nothing hard-coded.
        rel_bindir = self.cpp.build.bindirs[0] if self.cpp.build.bindirs else "."
        bindir = os.path.normpath(os.path.join(self.build_folder, rel_bindir))
        test_libigloo = os.path.join(bindir, "test_libigloo")
        check_ohos_elf = os.path.join(bindir, "check_ohos_elf")
        for executable in (test_libigloo, check_ohos_elf):
            if not os.path.isfile(executable):
                raise FileNotFoundError(f"Test executable not found: {executable}")

        # Real execution (L0d): consumer binary linked against the packaged
        # libigloo — init, version, sp, uuid, tap and unref.
        self.run(f'"{test_libigloo}"', env="conanrun")

        # Real execution (L0d): OHOS ELF artifact check on the consumer
        # binary that just ran (ELF64 little-endian, EM_AARCH64).
        self.run(f'"{check_ohos_elf}" "{test_libigloo}"', env="conanrun")

        # Keep the CTest registration exercised as well (same two binaries).
        cmake = CMake(self)
        cmake.test()
