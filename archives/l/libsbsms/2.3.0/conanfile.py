#!/usr/bin/env python3
"""Conan recipe — libsbsms 2.3.0 (Subband Sinusoidal Modeling Synthesis).

Upstream: https://github.com/claytonotey/libsbsms — a self-contained C++ library
for high quality time (tempo) and pitch scale modification built on octave
subband sinusoidal modeling.  It is the DSP core behind Audacity's
"Change Tempo" / "Change Pitch" effects.

HarmonyOS adaptation notes
--------------------------
* **Build system: CMake, not autotools.**  The 2.3.0 tag ships both a committed
  autotools ``configure`` (whose ``AC_INIT`` still says 2.2.0 and whose
  ``LIBSBSMS_RELEASE_*`` says 2.1.0, so ``sbsms.pc`` and the libtool
  ``-version-info`` are stale) and the CMake build that upstream's own
  ``.github/workflows/build.yml`` uses and whose ``project()`` version is the
  real 2.3.0.  CMake also sidesteps the ``config.guess``/``config.sub`` triplet
  problem the prescan reports for this tree (PSCAN-BUILD-001 / PSCAN-BUILD-102):
  no obsolete ``config.sub`` has to be taught an aarch64-ohos triplet, and no
  vendored autotools macro set has to run under a device whose PATH lacks
  automake (device-facts §一.4).
* ``cmake_minimum_required(VERSION 3.1)`` is rejected outright by CMake 4.x
  ("Compatibility with CMake < 3.5 has been removed").  The floor is raised
  with ``CMAKE_POLICY_VERSION_MINIMUM=3.5`` set as a **cache** variable: cache
  variables become ``-D...`` command-line definitions and are therefore
  evaluated before ``cmake_minimum_required()`` runs, whereas ``tc.variables``
  is written into ``conan_toolchain.cmake``, which the project includes only at
  ``project()`` time — after that call — and thus has no effect (E187/E321).
* Without an explicit platform name Conan hands CMake
  ``CMAKE_SYSTEM_NAME=HarmonyOS`` (``os=OHOS`` → ``HarmonyOS``) and CMake
  answers "System is unknown to cmake": there is no ``Platform/HarmonyOS.cmake``,
  so the shared-library SONAME flag stays undefined and the ``SOVERSION`` /
  ``VERSION`` properties on the ``sbsms`` target are silently dropped — the
  same failure mode already documented for libvpl.  Both the worker CMake
  (4.1.2) and the OHOS SDK CMake (3.28) ship ``Modules/Platform/OHOS.cmake``,
  which is just ``include(Platform/Linux)``, so selecting
  ``CMAKE_SYSTEM_NAME=OHOS`` restores the Linux link semantics
  (``-Wl,-soname,``) and produces ``libsbsms.so.2`` with ``DT_SONAME``.
* The sources build unmodified with the OHOS SDK clang for aarch64: no source
  patch, no platform macro, no ``#ifdef __OHOS__`` guard.

Upstream tests
--------------
There are none.  The 2.3.0 tarball ships no test directory and no test program:
``tar tzf`` lists 72 entries with no ``test/``/``tests/`` directory,
``find . -iname '*test*'`` matches nothing (only ``*check*`` matches, and that is
``m4/ax_check_compiler_flags.m4``), no translation unit in ``src/`` contains
``main()``, ``Makefile.am`` only has ``SUBDIRS = src`` without any
``TESTS``/``check-local`` target, and ``CMakeLists.txt`` has no
``enable_testing()``/``add_test()``.  The README still mentions a ``test.cpp``
that is not part of the repository.  The consumer assertions in
``test_package/`` are therefore the only executable evidence; they drive the
public API end to end and are counted separately from the (empty) upstream
tally — see ``reports/upstream-test-inventory.md``.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, load, save)

required_conan_version = ">=2.0"


class LibsbsmsConan(ConanFile):
    name = "libsbsms"
    version = "2.3.0"
    description = ("Subband Sinusoidal Modeling Synthesis: C++ library for high "
                   "quality time stretching and pitch scaling of audio")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/claytonotey/libsbsms"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    # Upstream CMakeLists declares option(BUILD_SHARED_LIBS "Build dynamic
    # library" ON); shared is the configuration upstream itself builds.  The
    # library does not collide with any system library name on OHOS
    # (/lib, /lib64, /system/lib carry no libsbsms*), so R26 does not force a
    # static build here.
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libsbsms is only supported on Linux/OHOS")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        # E187/E321 — must be a cache variable (see module docstring).
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        if self.settings.os == "OHOS":
            # Platform/HarmonyOS.cmake does not exist; without a known platform
            # name CMake never defines the SONAME flag and drops SOVERSION.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "OHOS"
            # Derive the target processor from the profile instead of hardcoding
            # aarch64, so a different `arch` cannot silently mismatch.
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8"
                else str(self.settings.arch))
        # Deterministic layout (GNUInstallDirs would otherwise vary by host).
        tc.cache_variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        self._make_pkgconfig_relocatable()

    def _make_pkgconfig_relocatable(self):
        """Point the generated pkg-config file at a package-relative prefix.

        Upstream's CMakeLists runs ``configure_file(sbsms.pc.in)``, which bakes
        ``CMAKE_INSTALL_PREFIX`` — i.e. this build's Conan package folder — into
        the ``prefix=`` line.  The shipped file therefore carries an absolute
        path into the local Conan cache and differs between two builds of the
        same recipe even when every other artifact is byte-identical (measured:
        7/8 artifacts identical across the 采信轮 and W3 rounds; this file was
        the only difference).  ``${pcfiledir}`` is expanded by pkg-config, so
        ``../..`` resolves to the package root from any install location.
        """
        pc = os.path.join(self.package_folder, "lib", "pkgconfig", "sbsms.pc")
        if not os.path.isfile(pc):
            return
        lines = load(self, pc).splitlines()
        for index, line in enumerate(lines):
            if line.startswith("prefix="):
                lines[index] = "prefix=${pcfiledir}/../.."
                save(self, pc, "\n".join(lines) + "\n")
                return

    def package_info(self):
        self.cpp_info.libs = ["sbsms"]
        # Upstream installs both a pkg-config file and an exported CMake package
        # (namespace sbsms::, target sbsms::sbsms); mirror those names so
        # consumers can use either discovery path.
        self.cpp_info.set_property("cmake_file_name", "sbsms")
        self.cpp_info.set_property("cmake_target_name", "sbsms::sbsms")
        self.cpp_info.set_property("pkg_config_name", "sbsms")
