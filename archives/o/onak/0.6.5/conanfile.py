#!/usr/bin/env python3
"""Conan recipe for onak 0.6.5 - an OpenPGP keyserver.

Builds the upstream CMake project for OHOS aarch64: the ``libonak`` static
library, the ``onak`` keyserver and companion tools, the CGI programs and the
dynamically loaded keydb backends (``dummy``/``file``/``fs``/``keyring``/
``stacked``).  Cryptographic support uses nettle/hogweed/gmp (detected through
pkg-config); the BDB, HKP (curl) and PostgreSQL backends are left out because
those libraries are not part of the OHOS toolchain.

The recipe runs one of the upstream test entry points (``runtests``, the
shellsuite exercised by ``ctest -R sanitytests``) directly in ``build()``.
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

required_conan_version = ">=2.0"


class OnakConan(ConanFile):
    name = "onak"
    version = "0.6.5"
    description = "OpenPGP keyserver with pluggable key database backends"
    license = "GPL-2.0-or-later"
    homepage = "https://www.earth.li/projectpurple/progs/onak.html"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "onak OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires("nettle/3.9.1")
        self.requires("hogweed/3.9.1")
        # nettle pins gmp/6.3.0, hogweed pins gmp/6.3.0.1: force one.
        self.requires("gmp/6.3.0", override=True)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # Dynamic backend: build every libkeydb_*.so so runtests can exercise
        # them, and export libonak symbols for dlopen resolution.
        tc.variables["DBTYPE"] = "dynamic"
        tc.variables["KEYD"] = "OFF"
        # Optional deps that are unavailable/undesirable in this environment.
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_BDB"] = True
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_Git"] = True
        # The Conan gmp package does not publish its include dir, so expose it.
        tc.variables["GMP_INCLUDE_DIR"] = os.path.join(
            self.dependencies["gmp"].package_folder, "include")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # Upstream sanitysuite (also wired as ctest -R sanitytests).
        script = os.path.join(self.source_folder, "runtests")
        log = os.path.join(self.build_folder, "runtests.out")
        self.run('sh "{}" > "{}" 2>&1'.format(script, log),
                 cwd=self.build_folder)
        with open(log) as fh:
            out = fh.read()
        self.output.info(out.strip().splitlines()[-1] if out.strip() else "no output")
        m = re.search(r"all tests succeeded \((\d+)\)", out)
        if not m:
            raise ConanException("onak runtests did not report success:\n" + out[-3000:])
        self.output.info("upstream runtests: %s script invocations passed" % m.group(1))

    def package(self):
        copy(self, "onak", self.build_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "splitkeys", self.build_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "stripkey", self.build_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "maxpath", self.build_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "sixdegrees", self.build_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "wotsap", self.build_folder, os.path.join(self.package_folder, "bin"))
        copy(self, "libonak.a", os.path.join(self.build_folder), os.path.join(self.package_folder, "lib"))
        copy(self, "libkeydb_*.so", os.path.join(self.build_folder, "keydb"),
             os.path.join(self.package_folder, "lib", "onak", "backends"))
        copy(self, "*.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
