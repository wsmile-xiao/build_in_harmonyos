#!/usr/bin/env python3
"""Conan recipe for NSD 4.15.0."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import (
    Autotools,
    AutotoolsDeps,
    AutotoolsToolchain,
    PkgConfigDeps,
)
from conan.tools.layout import basic_layout
from conan.tools.microsoft import unix_path


class NsdConan(ConanFile):
    name = "nsd"
    version = "4.15.0"
    description = "Authoritative-only DNS server"
    license = "BSD-3-Clause"
    homepage = "https://www.nlnetlabs.nl/projects/nsd/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    win_bash = True

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("nsd supports POSIX platforms")

    def requirements(self):
        self.requires(
            "openssl/3.5.6",
            transitive_headers=True,
            transitive_libs=True,
        )

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        basic_layout(self)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        openssl = unix_path(
            self, self.dependencies["openssl"].package_folder
        )
        toolchain = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS" and not cross_building(self):
            # Native OHOS workers cannot always execute config.guess because
            # its temporary directory may be read-only.  Supplying the
            # canonical tuple avoids that probe while preserving native mode.
            toolchain.configure_args.extend(
                [
                    "--build=aarch64-unknown-linux-ohos",
                    "--host=aarch64-unknown-linux-ohos",
                ]
            )
        toolchain.configure_args.extend(
            [
                f"--with-ssl={openssl}",
                "--with-libevent=no",
                "--disable-dnstap",
                "--disable-systemd",
                "--disable-xdp",
                "--disable-westmere",
                "--disable-haswell",
                "--disable-recvmmsg",
                "--disable-tcp-fastopen",
                "--with-configdir=/etc/nsd",
            ]
        )
        if str(self.settings.os) == "OHOS":
            toolchain.configure_args.extend(
                [
                    "--with-dbdir=/data/local/tmp/nsd/db",
                    "--with-pidfile=/data/local/tmp/nsd/nsd.pid",
                    "--with-xfrdir=/data/local/tmp/nsd/xfr",
                ]
            )
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.buildenv_info.append_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
        self.runenv_info.append_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
