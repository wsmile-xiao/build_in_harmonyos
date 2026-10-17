#!/usr/bin/env python3
"""Conan recipe — dbeacon 0.4.0 (plain makefile, no configure step).

dbeacon is a multicast connectivity beacon: it announces itself on one or more
IPv4/IPv6 multicast groups and collects reachability, loss, delay and jitter
statistics about the other beacons of the group, optionally dumping them as XML
for the upstream matrix CGI scripts.

Build system: plain Makefile, no configure script, no external dependencies
(the binary only links the platform C/C++ runtime).

Upstream declares its own version string as ``0.3.9.2p1`` inside dbeacon.cpp
and never bumped it for the 0.4.0 release; the 0.4.0 release is identified by
the upstream Changelog and by the official ``dbeacon-0.4.0`` tag that this
recipe downloads.

OHOS specifics:
  - The source is a C++ translation unit that pulls the C++ standard library
    (<map>, <string>, ...) and then does ``using namespace std;``. The POSIX
    ``bind(2)`` call is written unqualified, so with libc++ (selected by the
    OHOS profile) ``std::bind`` becomes visible and the call is ambiguous.
    patches/0001 qualifies that single call with the global scope (``::bind``),
    which is a no-op on every other platform.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class DbeaconConan(ConanFile):
    name = "dbeacon"
    version = "0.4.0"
    description = ("Multicast connectivity beacon for IPv4/IPv6, monitoring "
                   "reachability, loss, delay and jitter between beacons")
    license = "MIT"
    homepage = "https://github.com/uoaerg/dbeacon"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"dbeacon supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: never rely on shell $CXX/$CXXFLAGS. The CI workers have no `c++`
        # in PATH, so the compiler comes from the profile conf.
        comp = self.conf.get("tools.build:compiler_executables", default={},
                             check_type=dict)
        cxx = comp.get("cpp") or comp.get("c") or "clang++"
        # The upstream Makefile has no out-of-tree support and keeps its own
        # -g -Wall -O2 flags, so build in the source folder with -j1 (R9).
        self.run(f"make -j1 CXX='{cxx}'", cwd=self.source_folder)

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "dbeacon", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "dbeacon.1", src=os.path.join(self.source_folder, "docs"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)

    def package_info(self):
        # Command-line tool: no library, no headers.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
