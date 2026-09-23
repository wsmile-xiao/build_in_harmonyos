#!/usr/bin/env python3
"""Conan test_package - osrm-backend 26.5.0.

Consumer test: uses the installed libosrm util API (coordinate calculation)
with real assertions and runs the packaged osrm-extract tool asserting its
version output.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv


class OsrmBackendTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # osrm's upstream CMake relies on vcpkg-style global include paths for
        # the third-party headers its public headers pull in transitively
        # (boost etc.); OBJECT libraries do not propagate them here. Inject
        # every dependency include dir into the global CXX flags.
        incs = []
        for dep_name, dep in self.dependencies.items():
            if not dep.package_folder:
                continue
            cpp = dep.cpp_info
            dirs = [d for d in (cpp.includedirs or []) if d]
            for comp in getattr(cpp, "components", {}).values():
                dirs.extend(d for d in (comp.includedirs or []) if d)
            for d in dirs:
                if not isinstance(d, str):
                    continue
                incs.append(d if os.path.isabs(d) else os.path.join(dep.package_folder, d))
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_FLAGS_INIT"] = " ".join(
            "-isystem " + p for p in sorted(set(incs)))
        tc.generate()
        deps_gen = CMakeDeps(self)
        deps_gen.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Run the consumer binary with every dependency lib dir on
        # LD_LIBRARY_PATH: the shared transitive deps (tbb/libarchive/expat)
        # live in the conan cache and VirtualRunEnv does not aggregate
        # component libdirs of the whole graph.
        libdirs = []
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            cpp = dep.cpp_info
            dirs = list(cpp.libdirs or [])
            for comp in getattr(cpp, "components", {}).values():
                dirs.extend(comp.libdirs or [])
            libdirs.extend(d if os.path.isabs(d) else os.path.join(dep.package_folder, d)
                           for d in dirs if d)
        lp = ":".join(sorted(set(libdirs)))
        exe = os.path.join(self.cpp.build.bindirs[0], "test_osrm_backend")
        self.run('LD_LIBRARY_PATH="' + lp + '" "' + exe + '"', env="conanrun")
        dep = self.dependencies["osrm-backend"]
        version = self.tested_reference_str.split("/")[1].split("@")[0].split("#")[0]
        bindir = dep.cpp_info.bindirs[0]
        if not os.path.isabs(bindir):
            bindir = os.path.join(dep.package_folder, bindir)
        extract = os.path.join(bindir, "osrm-extract")
        self.run('LD_LIBRARY_PATH="' + lp + '" "' + extract + '" --version 2>&1 | grep -q "' + version + '"',
                 env="conanrun")
