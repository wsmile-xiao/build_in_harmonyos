#!/usr/bin/env python3
"""Conan recipe for YAZ 5.37.3."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    collect_libs,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class YazConan(ConanFile):
    name = "yaz"
    version = "5.37.3"
    description = "Z39.50 and SRU client/server library"
    license = "BSD-3-Clause"
    homepage = "https://www.indexdata.com/resources/software/yaz"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("YAZ supports Linux and OHOS")

    def requirements(self):
        self.requires(
            "libxml2/2.15.3",
            transitive_headers=True,
            transitive_libs=True,
        )

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            tc.configure_args.extend(
                [
                    "--build=aarch64-unknown-linux-gnu",
                    "--host=aarch64-unknown-linux-ohos",
                ]
            )
        tc.configure_args.extend(
            [
                "--disable-shared",
                "--enable-static",
                "--enable-threads",
                "--disable-tcpd",
                "--with-gnutls=no",
                "--with-icu=no",
                "--with-xml2=yes",
                "--with-xslt=no",
                "--with-exslt=no",
                "--with-memcached=no",
                "--with-redis=no",
                "--with-docbook-dsssl=no",
                "--with-docbook-dtd=no",
                "--with-docbook-xsl=no",
            ]
        )
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        if can_run(self):
            self.run(
                "make check -j1 TESTS=; status=$?; "
                "if [ $status -ne 0 ]; then "
                "find test -maxdepth 2 -type f -name '*.log' "
                "-print -exec cat {} \\;; fi; exit $status",
                env="conanbuild",
            )
            with VirtualRunEnv(self).vars().apply():
                self.run(
                    "make check -j1; status=$?; "
                    "if [ $status -ne 0 ]; then "
                    "find test -maxdepth 2 -type f -name '*.log' "
                    "-print -exec cat {} \\;; fi; exit $status",
                    env="conanbuild",
                )

    def package(self):
        Autotools(self).install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = collect_libs(self) or ["yaz", "yaz_server"]
        self.cpp_info.set_property("cmake_file_name", "yaz")
        self.cpp_info.set_property("cmake_target_name", "yaz::yaz")
        self.cpp_info.system_libs = ["m"] if self.settings.os == "OHOS" else ["m", "pthread", "dl"]
