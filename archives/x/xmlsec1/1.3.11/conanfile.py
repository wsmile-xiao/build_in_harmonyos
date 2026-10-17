#!/usr/bin/env python3
"""Conan recipe for xmlsec1 1.3.11."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    collect_libs,
    export_conandata_patches,
    get,
    mkdir,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class Xmlsec1Conan(ConanFile):
    name = "xmlsec1"
    version = "1.3.11"
    description = "XML signature and encryption library"
    license = "MIT"
    homepage = "https://github.com/lsh123/xmlsec"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("xmlsec1 supports Linux and OHOS")

    def requirements(self):
        self.requires(
            "libxml2/2.15.3",
            transitive_headers=True,
            transitive_libs=True,
        )
        self.requires(
            "openssl/3.5.6",
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
        VirtualRunEnv(self).generate()
        libxml2 = self.dependencies["libxml2"].package_folder
        openssl = self.dependencies["openssl"].package_folder
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-ohos",
            ])
        tc.configure_args.extend([
            "--disable-shared",
            "--enable-static",
            "--enable-static-linking",
            "--disable-crypto-dl",
            "--disable-apps-crypto-dl",
            f"--with-libxml={libxml2}",
            "--without-libxslt",
            f"--with-openssl={openssl}",
            "--without-gnutls",
            "--without-gcrypt",
            "--without-nss",
            "--with-default-crypto=openssl",
        ])
        tc.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        if can_run(self):
            test_tmp = os.path.join(self.build_folder, "test-tmp")
            mkdir(self, test_tmp)
            test_env = Environment()
            test_env.define("TMPFOLDER", test_tmp)
            test_env.define("TMPDIR", test_tmp)
            with test_env.vars(self).apply():
                self.run("make -j1 check", cwd=self.build_folder, env="conanrun")

    def package(self):
        Autotools(self).install()

    def package_info(self):
        libs = collect_libs(self)
        preferred = [name for name in ("xmlsec1-openssl", "xmlsec1") if name in libs]
        self.cpp_info.libs = preferred or libs
        self.cpp_info.includedirs = ["include/xmlsec1"]
        self.cpp_info.set_property("cmake_file_name", "xmlsec1")
        self.cpp_info.set_property("cmake_target_name", "xmlsec1::xmlsec1")
        self.cpp_info.system_libs = ["m"] if self.settings.os == "OHOS" else ["dl", "m", "pthread"]
