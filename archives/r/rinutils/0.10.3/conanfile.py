#!/usr/bin/env python3
"""Conan recipe — rinutils 0.10.3 (header-only C11 utilities library, OHOS PC).

rinutils ships 14 C headers plus a pkg-config file and a CMake package config;
there is no compiled deliverable (package_type = "header-library").

Build notes:
  * The upstream CMake tree downloads cmake/Shlomif_Common.cmake from GitHub at
    configure time and requires a perl interpreter. The adaptation vendors that
    module (patches/0001) and turns the download branch into a hard error
    (patches/0002), so configure is hermetic/offline.
  * The upstream cmocka C test (t/bit-reader-and-writer-test.c) is built and
    run for real inside build(); cmocka is a test_requires consumed through
    PkgConfigDeps, mirroring archives/b/blogc/0.20.1. The remaining upstream
    tests are Perl scripts that need the CPAN Inline::C toolchain and are not
    runnable on OHOS (per-module reasons in notes.md / test-report.md).
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps


class RinutilsConan(ConanFile):
    name = "rinutils"
    version = "0.10.3"
    description = ("rinutils - C11/gnu11 header-only utilities: sizeof-aware "
                   "allocation wrappers, COUNT/LAST, bit readers/writers, "
                   "portable time/long-long helpers and string utilities")
    license = "MIT"
    homepage = "https://github.com/shlomif/rinutils"
    url = "https://github.com/shlomif/rinutils"
    topics = ("header-only", "c11", "utilities")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "rinutils is prepared for Linux/OHOS targets only")

    def build_requirements(self):
        # Upstream C test suite (t/bit-reader-and-writer-test.c, cmocka) is
        # built and executed in build(); test_requires keeps cmocka out of
        # consumers' dependency graphs.
        self.test_requires("cmocka/2.0.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # The codeload URL ends with the bare tag ("0.10.3"), which Conan's
        # get() would otherwise use as the file name (no extension -> wrong
        # decoder).  An explicit *.tar.gz name selects the tar.gz decoder
        # (same pattern as archives/j/jattach).
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="rinutils-0.10.3.tar.gz")

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake has no OHOS platform module; the package is built natively on
        # OHOS with the SDK clang (repo-standard mapping, 300+ recipes).
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8"
                else str(self.settings.arch))
        tc.variables["WITH_TEST_SUITE"] = "ON"
        tc.generate()
        # Upstream finds cmocka via pkg-config
        # (pkg_check_modules(CMOCKA REQUIRED cmocka)).
        PkgConfigDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_c_tests()

    def _run_upstream_c_tests(self):
        """Run the real upstream cmocka test compiled from t/.

        rinutils' CMakeLists registers only the perl runner with CTest; the
        cmocka binary itself is executed directly (it is what run-tests.pl
        globs as t/*.t.exe).
        """
        exe = os.path.join(self.build_folder, "bit-reader-and-writer-test.t.exe")
        if not os.path.isfile(exe):
            raise ConanException("upstream cmocka test binary not found: %s" % exe)
        self.output.info("running upstream cmocka test: %s" % exe)
        self.run('"%s"' % exe, cwd=self.build_folder)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "Rinutils")
        self.cpp_info.set_property("cmake_target_name", "Rinutils::Rinutils")
        self.cpp_info.set_property("pkg_config_name", "rinutils")
