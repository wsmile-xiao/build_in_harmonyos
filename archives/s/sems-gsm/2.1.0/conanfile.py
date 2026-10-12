#!/usr/bin/env python3
"""Conan recipe for SEMS 2.1.0 (sems-gsm) on HarmonyOS PC.

sems-gsm is the GSM 06.10 codec plug-in of SEMS (SIP Express Media
Server).  The upstream project migrated from Makefiles to CMake in
2.1.0; the gsm plug-in (core/plug-in/gsm) is built whenever the GSM
library is found, so requiring libgsm unconditionally is enough to get
it into the build.

OHOS-specific adaptations (patch 0001):
  - resolv: musl provides res_search() in libc, no separate -lresolv
  - monitoring Rust tools: cargo is unavailable on OHOS CI, the
    upstream CMake already falls back to Python wrappers (kept)
  - D_THREAD_SAFE / _REENTRANT are passed for all compilers already
  - SEMS_CFG_PREFIX/SEMS_EXEC_PREFIX default to /usr/local — the
    recipe overrides them to the conan package prefix
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class SemsConan(ConanFile):
    name = "sems-gsm"
    version = "2.1.0"
    description = (
        "SIP Express Media Server - GSM codec plug-in (sems-gsm) "
        "and SEMS core"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/sems-server/sems"

    package_type = "application"
    # CMakeLists.txt: C++11 required; the gsm plug-in itself is C
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # gsm codec plug-in (GSM 06.10); published to ohpcd
        self.requires("libgsm/1.0.18")
        # core: Libevent2 REQUIRED (AmRtpSocket etc.)
        self.requires("libevent/2.1.13")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["SEMS_CFG_PREFIX"] = self.package_folder
        tc.variables["SEMS_EXEC_PREFIX"] = self.package_folder
        tc.variables["SEMS_AUDIO_PREFIX"] = os.path.join(
            self.package_folder, "share", "sems", "audio")
        tc.variables["SEMS_LIBDIR"] = "lib"
        tc.variables["SEMS_DOC_PREFIX"] = os.path.join(
            self.package_folder, "share", "doc")
        tc.variables["SEMS_RUNDIR_PREFIX"] = os.path.join(
            self.package_folder, "var", "run")
        # Disable everything not needed for the gsm codec plug-in
        tc.variables["SEMS_USE_PYTHON"] = "OFF"
        tc.variables["SEMS_USE_SPANDSP"] = "OFF"
        tc.variables["SEMS_USE_OPUS"] = "OFF"
        tc.variables["SEMS_USE_MP3"] = "OFF"
        tc.variables["SEMS_USE_ILBC"] = "OFF"
        tc.variables["SEMS_USE_MONITORING"] = "OFF"
        # xmlrpc2di's bundled xmlrpc++ requires OpenSSL unconditionally
        # (HAVE_XMLRPCPP_SSL guards are incomplete upstream); the gsm
        # codec plug-in does not need it — exclude via upstream knob.
        tc.variables["EXCLUDE_APP_MODULES"] = "xmlrpc2di"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = \
                "-Wl,-soname,"
            tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = \
                "-Wl,-soname,"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        env = Environment()
        if self.settings.os == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        with env.vars(self).apply():
            cmake.configure()
            cmake.build()
        # Upstream unit tests (core/tests, sems_tests binary)
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        test_env = Environment()
        # sems_tests/sems link conan deps (libevent/libgsm) and the
        # freshly built in-tree modules; the loader needs all of these
        # on LD_LIBRARY_PATH (bare -levent lives outside default paths).
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                test_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
        for rel in ("core", "bin", "lib"):
            test_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        if self.settings.os == "OHOS":
            test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure '
                '--no-tests=error'.format(self.build_folder))

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_id(self):
        # application: only os/arch/build_type relevant
        del self.info.settings.compiler

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        bindir = os.path.join(self.package_folder, "sbin")
        self.cpp_info.bindirs = [bindir]
        # gsm plug-in lives in lib/sems/plug-in
        self.cpp_info.builddirs = []
