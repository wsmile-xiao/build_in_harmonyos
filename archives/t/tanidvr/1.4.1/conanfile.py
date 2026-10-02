#!/usr/bin/env python3
"""Conan recipe — tanidvr 1.4.1 (GNU Autotools).

TaniDVR ships two C command-line programs for the proprietary Dahua
DVR-IP protocol (TCP 37777):

* ``tanidvr``  — DVR / IP-camera client (live monitoring, recordings)
* ``dhav2mkv`` — converts ``.dhav`` / ``.dav`` recordings into Matroska

The upstream tarball ships a pre-generated ``configure`` script, so no
bootstrap/autoreconf step is needed. There are no third-party dependencies:
``configure.ac`` only probes libc/POSIX headers and socket functions.
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
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class TanidvrConan(ConanFile):
    name = "tanidvr"
    version = "1.4.1"
    description = "Command-line clients for Dahua DVRs and IP cameras (DVR-IP protocol)"
    license = "GPL-3.0-or-later"
    homepage = "https://tanidvr.sourceforge.net/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No third-party dependencies: upstream configure.ac only checks libc /
        # POSIX headers (fcntl.h, netdb.h, netinet/in.h, sys/socket.h, ...)
        # and libc functions (fork, malloc, socket, gethostbyname, ...).
        pass

    def layout(self):
        basic_layout(self, src_folder="src")

    # R32: only Linux/OHOS are supported hosts for this recipe.
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} is not supported"
            )

    def source(self):
        # get() accepts the URL list from conandata.yml and falls back to the
        # next mirror when one is unreachable (same bytes, same sha256).
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # AutotoolsToolchain passes --prefix plus CC/CFLAGS/CXX/CXXFLAGS taken
        # from tools.build:compiler_executables, so configure picks the OHOS
        # aarch64 clang driver instead of the build machine's gcc (R33).
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        # OHOS/HMDFS: the shipped configure creates its scratch directory with
        # "umask 077 && mktemp -d ./confXXXXXX"; HMDFS forces setgid on new
        # directories, so the result is drwx--S--- and config.status fails with
        # "./confXXXXXX/subs1.awk: Permission denied". Patch drops the umask.
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        autotools.install()

    def package(self):
        copy(
            self,
            "COPYING",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        for doc in ("README", "INSTALL"):
            copy(
                self,
                doc,
                self.source_folder,
                os.path.join(self.package_folder, "share", "doc", "tanidvr"),
                keep_path=False,
            )
        if os.name != "nt":
            for binary in ("tanidvr", "dhav2mkv"):
                os.chmod(os.path.join(self.package_folder, "bin", binary), 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
