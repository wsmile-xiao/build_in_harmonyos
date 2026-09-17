#!/usr/bin/env python3
"""Consumer test — termrec/0.19 (Conan L1 test).

Builds a C consumer against the installed libtty (public ttyrec writer /
reader API round trip) and additionally runs the installed ``termcat`` CLI
end-to-end (asciicast → ttyrec conversion, output asserted non-empty).

The termrec tools link libzstd dynamically (the zstd package ships a shared
library only) so every executed binary needs the dependency libdirs on
LD_LIBRARY_PATH — OHOS musl ignores DT_RUNPATH.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class TermrecTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _runtime_env(self):
        libdirs = []
        for dep in self.dependencies.host.values():
            cpp = dep.cpp_info.aggregated_components()
            for libdir in cpp.libdirs:
                libdirs.append(libdir if os.path.isabs(libdir)
                               else os.path.join(dep.package_folder, libdir))
        env = Environment()
        if libdirs:
            env.append_path("LD_LIBRARY_PATH", libdirs)
        return env

    def test(self):
        with self._runtime_env().vars(self).apply():
            cmake = CMake(self)
            cmake.test()
            if cross_building(self):
                self.output.info("cross-building: library-API verification only")
                return
            dep = self.dependencies[self.tested_reference_str]
            termcat = os.path.join(dep.cpp_info.bindirs[0], "termcat")
            fixture = os.path.join(self.source_folder, "fixture.cast")
            out = os.path.join(self.build_folder, "out.ttyrec")
            self.run(f'"{termcat}" "{fixture}" "{out}"')
            size = os.path.getsize(out) if os.path.exists(out) else 0
            if size <= 12:
                raise ConanException(
                    f"termcat produced no ttyrec data ({size} bytes)")
            self.output.info(
                f"termcat CLI round trip OK: {size} bytes ttyrec written")
