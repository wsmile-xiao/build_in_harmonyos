#!/usr/bin/env python3
"""Conan recipe for libp11 0.4.16-r0."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class Libp11Conan(ConanFile):
    name = "libp11"
    version = "0.4.16-r0"
    description = "PKCS#11 wrapper library for OpenSSL applications"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/OpenSC/libp11"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libp11 supports Linux and OHOS")

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
        apply_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def _prepare_upstream_test_tools(self):
        test_prefix = os.path.join(self.build_folder, "upstream-test-tools")
        for tool in self.conan_data["test_tools"].values():
            get(
                self,
                **tool,
                destination=test_prefix,
                keep_permissions=True,
            )
        return test_prefix

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-ohos",
            ])
        tc.configure_args.extend([
            "--disable-shared",
            "--enable-static",
            "--disable-static-engine",
            "--disable-api-doc",
            "--with-enginesdir=/lib/engines-3",
            "--with-modulesdir=/lib/ossl-modules",
        ])
        tc.generate()

    def build(self):
        openssl = self.dependencies["openssl"].package_folder
        env = Environment()
        env.define("OPENSSL_CFLAGS", f"-I{os.path.join(openssl, 'include')}")
        env.define(
            "OPENSSL_LIBS",
            f"-L{os.path.join(openssl, 'lib')} -lcrypto",
        )
        with env.vars(self).apply():
            autotools = Autotools(self)
            autotools.configure()
            self.run("make -C src -j1 libp11.la", cwd=self.source_folder)
            if can_run(self) and self.settings.os == "Linux":
                test_prefix = self._prepare_upstream_test_tools()
                test_env = Environment()
                test_env.define("LIBP11_TEST_PREFIX", test_prefix)
                test_env.prepend_path("PATH", os.path.join(test_prefix, "bin"))
                test_env.prepend_path("PATH", os.path.join(openssl, "bin"))
                test_env.prepend_path(
                    "LD_LIBRARY_PATH",
                    os.path.join(test_prefix, "lib", "external"),
                )
                test_env.prepend_path(
                    "LD_LIBRARY_PATH",
                    os.path.join(test_prefix, "lib"),
                )
                test_env.prepend_path(
                    "LD_LIBRARY_PATH",
                    os.path.join(openssl, "lib"),
                )
                with test_env.vars(self).apply():
                    self.run(
                        "make -C src -j1 pkcs11.la pkcs11prov.la",
                        cwd=self.source_folder,
                    )
                    self.run(
                        "make -C tests -j1 check LOG_COMPILER=bash",
                        cwd=self.source_folder,
                    )

    def package(self):
        src_dir = os.path.join(self.source_folder, "src")
        copy(self, "libp11.a", src=os.path.join(src_dir, ".libs"), dst=os.path.join(self.package_folder, "lib"))
        for header in ("libp11.h", "p11_err.h", "pkcs11.h"):
            copy(self, header, src=src_dir, dst=os.path.join(self.package_folder, "include"))
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["p11"]
        self.cpp_info.set_property("cmake_file_name", "libp11")
        self.cpp_info.set_property("cmake_target_name", "libp11::libp11")
        self.cpp_info.requires = ["openssl::openssl"]
        self.cpp_info.system_libs = ["m"] if self.settings.os == "OHOS" else ["dl", "pthread"]
