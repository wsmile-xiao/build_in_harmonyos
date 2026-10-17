#!/usr/bin/env python3
"""Conan recipe for ppp 2.5.2 on OpenHarmony/HarmonyOS."""

import os
from shlex import quote

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.env import Environment
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PppConan(ConanFile):
    name = "ppp"
    version = "2.5.2"
    description = "Point-to-Point Protocol daemon and user-space utilities"
    license = "BSD-3-Clause AND GPL-2.0-only"
    homepage = "https://ppp.samba.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # EAP-TLS, PEAP, MS-CHAP and MPPE use the upstream OpenSSL backend.
        self.requires("openssl/3.5.6", run=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        openssl_root = self.dependencies["openssl"].package_folder

        tc = AutotoolsToolchain(self)
        # ppp recognizes Linux and Solaris. This canonical tuple yields
        # host_os=linux-ohos and selects its Linux user-space implementation.
        tc.update_configure_args(
            {
                "--build": "aarch64-unknown-linux-ohos",
                "--host": "aarch64-unknown-linux-ohos",
            }
        )
        # Consume release-generated files without invoking maintainer tools.
        # The target environment intentionally has no Autoconf or Automake.
        tc.configure_args.extend(
            [
                f"--with-openssl={openssl_root}",
                "--disable-openssl-engine",
                "--without-atm",
                "--without-pam",
                "--without-pcap",
                "--without-srp",
                "--disable-maintainer-mode",
                "--disable-systemd",
                "--disable-multilink",
            ]
        )
        tc.generate()
        AutotoolsDeps(self).generate()

    def build(self):
        self._remove_stale_generated_headers()
        apply_conandata_patches(self)
        self._relax_generated_tmp_permissions()

        autotools = Autotools(self)
        # HMDFS does not allow direct execution of extracted scripts. Keep the
        # Conan-generated configure arguments and environment, but invoke the
        # script through the system shell.
        configure = os.path.join(self.source_folder, "configure")
        self.run(
            f"/system/bin/sh {quote(configure)} {autotools._configure_args}",
            env="conanbuild",
        )
        autotools.make(args=["-j1"])
        # Native OHOS CI uses the same host/build profile, so the five pppd
        # unit tests are executable here without a cross-runner. Point OpenSSL
        # at its Conan provider modules and keep test scratch data off /tmp,
        # which is not writable by the CI user on HarmonyOS.
        openssl_root = self.dependencies["openssl"].package_folder
        test_tmp = os.path.join(self.build_folder, "test-tmp")
        os.makedirs(test_tmp, exist_ok=True)
        test_env = Environment()
        test_env.define(
            "OPENSSL_MODULES", os.path.join(openssl_root, "lib", "ossl-modules")
        )
        test_env.define("TMPDIR", test_tmp)
        with test_env.vars(self).apply():
            autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        copy(
            self,
            "LICENSE.*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        # AutotoolsToolchain maps both bindir and sbindir to this directory.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.define_path(
            "OPENSSL_MODULES",
            os.path.join(self.dependencies["openssl"].package_folder, "lib", "ossl-modules"),
        )

    def _relax_generated_tmp_permissions(self):
        """Avoid Autoconf's umask 077 temporary dirs on HMDFS (E011)."""
        configure = os.path.join(self.source_folder, "configure")
        with open(configure, encoding="utf-8") as handle:
            content = handle.read()
        content = content.replace("umask 077", "umask 022")
        with open(configure, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)

    def _remove_stale_generated_headers(self):
        """Let the out-of-source build use headers from this configure run."""
        for relative_path in (
            os.path.join("pppd", "config.h"),
            os.path.join("pppd", "pppdconf.h"),
            os.path.join("pppd", "plugins", "pppoe", "config.h"),
        ):
            generated = os.path.join(self.source_folder, relative_path)
            if os.path.isfile(generated):
                os.remove(generated)
