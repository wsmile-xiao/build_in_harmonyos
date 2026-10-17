#!/usr/bin/env python3
"""Conan recipe — libproperties 1.1.2 (CMake)

Upstream is plain CMake with no external dependencies (buf.c + properties.c only).
Two HarmonyOS-specific facts drive the non-obvious lines below:

1. DT_SONAME — the device/CI CMake reports ``CMAKE_SYSTEM_NAME=HarmonyOS`` but no
   ``Modules/Platform/HarmonyOS.cmake`` exists, so
   ``CMAKE_SHARED_LIBRARY_SONAME_C_FLAG`` is never defined.  Without it lld emits a
   shared object with no DT_SONAME *and* CMake does not create the versioned file
   names at all (installed tree ends up with a bare ``libproperties.so``), which
   fails W3's ``L5a: ... 缺少 DT_SONAME`` gate.  We inject the flag at configure
   time (producer side, no post-link ELF rewrite, toolchain self-signature intact).

2. rpath — the same missing platform module leaves the rpath link flags undefined,
   so ``CMAKE_BUILD_RPATH`` is silently a no-op (verified: the test binary links
   with no RPATH/RUNPATH entry) and ctest fails with
   ``Error loading shared library libproperties.so.1``.  The upstream suite is
   therefore executed with ``LD_LIBRARY_PATH`` pointing at the build tree.
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class LibpropertiesConan(ConanFile):
    name = "libproperties"
    version = "1.1.2"
    description = "Small C library for parsing property-list (.properties) files"
    license = "Apache-2.0"
    homepage = "https://github.com/tinyhubs/libproperties"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 零运行时/构建期依赖：上游只编 buf.c + properties.c，产物 DT_NEEDED 仅 libc.so。
        pass

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream default is BUILD_SHARED_LIBS=ON; keep it option-driven.
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Upstream registers its ctest suite next to the library (test/*.properties).
        tc.variables["LIBPROPERTIES_TEST"] = "ON"
        tc.variables["LIBPROPERTIES_INSTALL"] = "ON"
        if self.settings.os != "Windows":
            # Module docstring, item 1: HarmonyOS platform module has no SONAME flag.
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_ctest()

    def _run_upstream_ctest(self):
        """Run the upstream ctest suite in the build tree.

        N (upstream test count) is decided by ``add_test()`` in the upstream
        CMakeLists: it globs ``test/*.properties`` (1.properties, 2.properties)
        and registers exactly two cases.  The loader path is injected manually
        because rpath support is missing on this platform (docstring, item 2).
        """
        build_dir = self.build_folder
        existing = os.environ.get("LD_LIBRARY_PATH", "")
        entries = [build_dir] + ([existing] if existing else [])
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(entries)
        self.run(
            'ctest --test-dir "{}" --output-on-failure'.format(build_dir),
            cwd=build_dir,
            env="conanbuild",
        )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Upstream target is add_library(properties ...) -> libproperties.so / .a
        self.cpp_info.libs = ["properties"]
        self.cpp_info.set_property("cmake_file_name", "libproperties")
        self.cpp_info.set_property("cmake_target_name", "libproperties::libproperties")
