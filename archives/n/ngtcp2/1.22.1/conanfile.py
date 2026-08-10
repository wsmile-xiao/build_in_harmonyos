#!/usr/bin/env python3
"""Conan recipe for ngtcp2 — IETF QUIC protocol implementation."""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class Ngtcp2Conan(ConanFile):
    name = "ngtcp2"
    version = "1.22.1"
    description = "ngtcp2 is an effort to implement IETF QUIC protocol"
    license = "MIT"
    homepage = "https://github.com/ngtcp2/ngtcp2"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "with_crypto_openssl": [True, False],
    }
    default_options = {
        "shared": False,
        "with_crypto_openssl": True,
    }

    generators = "AutotoolsDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        if self.options.with_crypto_openssl:
            self.requires("openssl/3.5.6.1.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--enable-lib-only")
        if self.options.with_crypto_openssl:
            tc.configure_args.append("--with-openssl")
        else:
            tc.configure_args.append("--without-openssl")
        tc.generate()

        if self.options.with_crypto_openssl:
            openssl_info = self.dependencies["openssl"]
            pkg_config_dir = os.path.join(
                openssl_info.package_folder, "lib", "pkgconfig"
            )
            env = Environment()
            env.define_path("PKG_CONFIG_PATH", pkg_config_dir)
            envvars = env.vars(self, scope="build")
            envvars.save_script("conan_pkgconfig")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "ngtcp2")

        self.cpp_info.components["ngtcp2"].set_property(
            "cmake_target_name", "ngtcp2::ngtcp2"
        )
        self.cpp_info.components["ngtcp2"].libs = ["ngtcp2"]

        if self.options.with_crypto_openssl:
            self.cpp_info.components["crypto_ossl"].set_property(
                "cmake_target_name", "ngtcp2::crypto_ossl"
            )
            self.cpp_info.components["crypto_ossl"].libs = ["ngtcp2_crypto_ossl"]
            self.cpp_info.components["crypto_ossl"].requires = ["openssl::openssl"]
