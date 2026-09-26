#!/usr/bin/env python3
"""Conan test_package — gplotpp 1.1.0.

Consumer validation: compiles a program that uses the installed public
header gplot++.h and the public Gnuplot API, links gplotpp::gplotpp, and
runs it against a real `gnuplot` executable so the rendered SVG output
can be verified. gnuplot/6.0.3 is declared as a tool requirement of this
test package so the clean CI environment also resolves it from the ohpcd
registry (the consumer needs the real gnuplot binary at runtime).
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class GplotppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        # Consumer test drives the real gnuplot executable at runtime;
        # make it available in the CI build context too.
        self.tool_requires("gnuplot/6.0.3")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _find_gnuplot_bin(self):
        # 1) gnuplot provided by the declared tool_requires (authoritative
        #    in clean CI)
        try:
            dep = self.dependencies.build["gnuplot"]
            p = os.path.join(dep.package_folder, "bin", "gnuplot")
            if os.path.isfile(p):
                return p
        except Exception:
            pass
        # 2) anything on PATH
        import shutil

        found = shutil.which("gnuplot")
        if found and os.path.isfile(found):
            return found
        home = os.path.expanduser("~")
        # HMDFS ignores chmod → os.access(X_OK) is always False; rely on isfile.
        # conan2 cache dir is `gnupla03c6b9f7091e` → match `gnu*`.
        for p in sorted(
            glob.glob(os.path.join(home, ".conan2", "p", "gnu*", "p", "bin", "gnuplot"))
        ):
            if os.path.isfile(p):
                return p
        return None

    def test(self):
        # Run the consumer binary directly (with gnuplot injected into
        # PATH inside the command) instead of via CTest: CTest spawns the
        # test in its own environment that does not inherit the injected
        # PATH, and the consumer needs the real `gnuplot` executable.
        gnuplot_bin = self._find_gnuplot_bin()
        test_exe = os.path.join(self.cpp.build.bindirs[0], "test_gplotpp")
        if gnuplot_bin:
            # Inject gnuplot dir into PATH inside the command itself.
            gpdir = os.path.dirname(gnuplot_bin)
            self.run(
                'export PATH="%s${PATH:+:$PATH}"; "%s"'
                % (gpdir, test_exe)
            )
        else:
            raise RuntimeError(
                "gnuplot executable not found (tool_requires gnuplot/6.0.3 "
                "should provide it); refusing to run the consumer test "
                "without the real gnuplot binary"
            )