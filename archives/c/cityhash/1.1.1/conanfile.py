#!/usr/bin/env python3
"""Conan recipe for cityhash 1.1.1 — Google CityHash family of hash functions.

CityHash 1.1.1 is a C++ libtool library (libcityhash) distributed via the
Google Code archive. The released configure ships a 2005-era config.guess
and config.sub that predate `aarch64`. The recipe explicitly supplies
`--build=aarch64-unknown-linux-gnu` and deliberately omits `--host`, so this
native OHOS build does not need config.guess to infer the build tuple and
avoids the old config.sub host validation.

The applied patch (see patches/) contains:
- E011: relax `umask 077` temp-dir creation in configure to `umask 022`
  (HMDFS cannot write into 0700 dirs). The E160 config.guess branch is a
  related general case, but is not applied by this recipe.
"""
import os

from conan import ConanFile
from conan.tools.files import (
    copy,
    get,
    apply_conandata_patches,
    export_conandata_patches,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class CityhashConan(ConanFile):
    name = "cityhash"
    version = "1.1.1"
    description = "CityHash — family of hash functions for strings (Google)"
    license = "MIT"
    homepage = "https://github.com/google/cityhash"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E386: autoconf adopts CONFIG_SHELL from the profile [buildenv]
        # (/data/service/hnp/bin/bash); that bash's getcwd() intermittently
        # fails on HMDFS dirs ("working directory cannot be determined") and
        # profile buildenv overrides toolchain-level env — pin the shell
        # inline on the configure invocation instead.
        configure = os.path.join(self.source_folder, "configure")
        shared_args = "" if self.options.shared else "--disable-shared --enable-static"
        self.run(
            f'cd "{self.build_folder}" && CONFIG_SHELL=/bin/sh SHELL=/bin/sh '
            f'/bin/sh "{configure}" --prefix="{self.package_folder}" '
            f'--build=aarch64-unknown-linux-gnu CC={self._cc()} '
            f'CXX={self._cxx()} {shared_args}'
        )
        autotools = Autotools(self)
        autotools.make(args=["-j1"])
        # Run the official upstream test suite (src/Makefile.am TESTS =
        # cityhash_unittest via `make check`): a self-contained binary
        # checking CityHash64/32/128 outputs against fixed reference
        # vectors. Executed here so CI L1c can verify real upstream test
        # execution from the conan create log.
        autotools.make(args=["check"])

    def _cc(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return compilers.get("c", "clang")

    def _cxx(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return compilers.get("cpp", "clang++")

    def package(self):
        # Static-only packaging: avoids HMDFS symlink handling for the
        # libtool .so/.so.0/.so.0.0.0 triple; consumers link libcityhash.a.
        copy(self, "city.h", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "libcityhash.a", src=os.path.join(self.build_folder, "src", ".libs"),
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["cityhash"]
