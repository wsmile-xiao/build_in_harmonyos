#!/usr/bin/env python3
"""Conan recipe for gplotpp 1.1.0 — header-only C++17 interface to Gnuplot.

The library is a CMake INTERFACE target: it installs gplot++.h and the
CMake package config files, and has no compiled artifacts of its own.
Upstream tests (tests/src/run_tests.cpp, doctest) require the real
`gnuplot` executable at runtime, which is provided by the published
gnuplot/6.0.3 OHOS package on the ohpcd registry.
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class GplotppConan(ConanFile):
    name = "gplotpp"
    version = "1.1.0"
    description = "A C++ header-only interface to Gnuplot"
    license = "MIT"
    homepage = "https://github.com/ziotom78/gplotpp"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # gplotpp only includes the C++ standard library. The gnuplot
        # executable is a runtime tool of the consumers, not a link
        # dependency of this header-only library.
        pass

    def build_requirements(self):
        # The upstream doctest suite (tests/src/run_tests.cpp) drives the
        # real `gnuplot` executable via popen at build/test time. Declare
        # gnuplot/6.0.3 as a tool requirement so `conan create` /
        # build_and_test.sh in the clean CI environment resolves it from the
        # ohpcd registry and places it in the build context (its bin/ dir is
        # then available through the Conan build environment). Without this,
        # the "gnuplot injection" only works on the executor's local cache
        # and the remote CI gate fails (GPLOTPP_GNUPLOT_BIN=NOT_FOUND).
        self.tool_requires("gnuplot/6.0.3")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R32: keep the recipe valid for Linux and OHOS profiles.
        if self.settings.os in ("Linux", "OHOS"):
            tc.blocks["generic_system"].values["cmake_system_name"] = str(
                self.settings.os
            )
            if self.settings.os == "OHOS":
                tc.blocks["generic_system"].values["cmake_system_processor"] = (
                    "aarch64"
                )

        # CMake 4 no longer accepts projects whose minimum is below 3.5.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["GPLOTPP_ENABLE_TESTS"] = "ON"
        # Examples are extra demo binaries, not part of the installed package.
        tc.variables["GPLOTPP_BUILD_EXAMPLES"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(target="run_tests")

        test_binary = os.path.join(self.build_folder, "tests", "run_tests")
        if not os.path.exists(test_binary):
            raise RuntimeError("GPLOTPP_ENABLE_TESTS produced no run_tests binary")
        gnuplot_bin = self._find_gnuplot_bin()
        self.output.info("GPLOTPP_UPSTREAM_TESTS_REGISTERED=2 (complex, animation)")
        self.output.info("GPLOTPP_GNUPLOT_BIN=%s" % (gnuplot_bin or "NOT_FOUND"))
        if gnuplot_bin:
            gpdir = os.path.dirname(gnuplot_bin)
            # Inject gnuplot dir into PATH inside the command itself so the
            # subprocess shell resolves `gnuplot` regardless of how the
            # runner forwards the environment.
            self.run(
                'export PATH="%s${PATH:+:$PATH}"; "%s" --no-skip'
                % (gpdir, test_binary)
            )
        else:
            raise RuntimeError(
                "gnuplot executable not found (tool_requires gnuplot/6.0.3 "
                "should provide it); refusing to run the upstream suite "
                "without the real gnuplot binary"
            )

    def _find_gnuplot_bin(self):
        # 1) gnuplot provided by the declared tool_requires (authoritative
        #    in clean CI: resolved from the ohpcd registry into the build
        #    context, package folder available through self.dependencies)
        try:
            dep = self.dependencies.build["gnuplot"]
            p = os.path.join(dep.package_folder, "bin", "gnuplot")
            if os.path.isfile(p):
                return p
        except Exception:
            pass
        # 2) anything on PATH (shutil.which uses X_OK; on HMDFS chmod is
        #    ignored so this may miss, hence the cache glob below)
        import shutil

        found = shutil.which("gnuplot")
        if found and os.path.isfile(found):
            return found
        # 3) the ohpcd registry package cache (gnuplot/6.0.3).
        #    NOTE: do NOT gate on os.access(X_OK) — HMDFS ignores chmod
        #    and returns a fixed 660 mode, so X_OK is always False (E046).
        #    The conan2 cache dir is `gnupla03c6b9f7091e` (name prefix +
        #    hash), so match on `gnu*` rather than `gnuplot*`.
        home = os.path.expanduser("~")
        if not home:
            home = os.environ.get("HOME", "")
        for p in sorted(glob.glob(os.path.join(home, ".conan2", "p", "gnu*", "p", "bin", "gnuplot"))):
            if os.path.isfile(p):
                return p
        return None

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("cmake_file_name", "gplotpp")
        self.cpp_info.set_property("cmake_target_name", "gplotpp::gplotpp")
