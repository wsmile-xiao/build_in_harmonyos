#!/usr/bin/env python3
"""Conan recipe for pps-tools 1.0.3 - LinuxPPS user-space tools and PPSAPI header.

The upstream project ships a small, dependency-free Makefile that builds four
programs against the LinuxPPS user-space API:

* ``ppstest``  - PPSAPI interface tester (opens a PPS device and prints timestamps)
* ``ppsctl``   - PPS device manager (bind/unbind the kernel consumer, NTP flags)
* ``ppswatch`` - continuously print PPS timestamps and running statistics
* ``ppsldisc`` - set the PPS line discipline on an RS232 serial port

and the public PPSAPI header ``sys/timepps.h``.  The ``ppsfind`` shell helper is
installed next to the compiled programs.

There are no third-party dependencies: the OHOS SDK sysroot already provides the
only kernel headers the sources need (``<linux/pps.h>``, ``<linux/types.h>``,
``<linux/tty.h>``).  Upstream has no test suite, so ``test_package`` builds a
header consumer and exercises the installed programs.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get)
from conan.tools.layout import basic_layout

_PROGRAMS = ("ppstest", "ppsctl", "ppswatch", "ppsldisc")


class PpsToolsConan(ConanFile):
    name = "pps-tools"
    version = "1.0.3"
    description = ("LinuxPPS support tools and headers (PPSAPI user-space "
                   "interface for the Linux PPS subsystem)")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/redlab-i/pps-tools"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pps-tools OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def build(self):
        apply_conandata_patches(self)
        cc = self._compiler("c", "clang")
        opt = "-O2" if str(self.settings.build_type) == "Release" else "-g -O0"
        self.run('make CC="{}" CFLAGS="-Wall {} -D_GNU_SOURCE -fPIC" -j1'.format(cc, opt),
                 cwd=self.source_folder)
        for prog in _PROGRAMS:
            if not os.path.isfile(os.path.join(self.source_folder, prog)):
                raise ConanInvalidConfiguration(
                    "build did not produce the '{}' program".format(prog))

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        for prog in _PROGRAMS + ("ppsfind",):
            copy(self, prog, self.source_folder, bindir)
        ppsfind = os.path.join(bindir, "ppsfind")
        if os.path.isfile(ppsfind):
            os.chmod(ppsfind, 0o755)
        copy(self, "timepps.h", self.source_folder,
             os.path.join(self.package_folder, "include", "sys"))
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README.md", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
