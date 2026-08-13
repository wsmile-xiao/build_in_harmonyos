#!/usr/bin/env python3
"""Conan recipe — nmap 7.99 for HarmonyOS.

nmap is a network security scanner and discovery tool (command-line application).
Produces three executables: nmap, ncat, nping.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class NmapConan(ConanFile):
    name = "nmap"
    version = "7.99"
    description = "Network security scanner and discovery tool"
    license = "GPL-2.0"
    homepage = "https://nmap.org/"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        src = self.source_folder
        # E002: /tmp is read-only on HarmonyOS
        os.environ["TMPDIR"] = os.path.expanduser("~/.tmp")
        os.makedirs(os.environ["TMPDIR"], exist_ok=True)

        apply_conandata_patches(self)

        # Get OpenSSL paths from Conan dependency (R33: from conf, not hardcoded)
        openssl = self.dependencies["openssl"]
        openssl_prefix = openssl.package_folder

        # R32: platform check
        # R33: use Conan-generated env (conanbuild.sh sets CC/CXX/CONFIG_SHELL)
        # Source the Conan build environment which sets CC, CXX, CFLAGS, etc.
        conanbuild = os.path.join(self.generators_folder, "conanbuild.sh")
        env_prefix = f'source "{conanbuild}" && '

        # Configure with OpenSSL path and static linking (R26)
        self.run(
            'cd {} && {} ./configure --prefix=/ --enable-static --disable-shared --with-openssl={}'.format(
                src, env_prefix, openssl_prefix
            )
        )

        # Build core tools (skip zenmap)
        self.run('cd {} && {} make nmap'.format(src, env_prefix))
        self.run('cd {} && {} make -C ncat'.format(src, env_prefix))
        self.run('cd {} && {} make -C nping'.format(src, env_prefix))

    def package(self):
        src = self.source_folder
        conanbuild = os.path.join(self.generators_folder, "conanbuild.sh")
        env_prefix = f'source "{conanbuild}" && '
        self.run('cd {} && {} make install DESTDIR={}'.format(src, env_prefix, self.package_folder))
        self.run('cd {} && {} make -C ncat install DESTDIR={}'.format(src, env_prefix, self.package_folder))
        self.run('cd {} && {} make -C nping install DESTDIR={}'.format(src, env_prefix, self.package_folder))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
