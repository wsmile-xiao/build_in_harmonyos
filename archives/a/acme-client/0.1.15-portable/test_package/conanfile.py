#!/usr/bin/env python3
"""Conan test package for acme-client 0.1.15-portable."""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import load, save
from conan.tools.layout import basic_layout


class AcmeClientTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("libressl/3.9.1")

    def layout(self):
        basic_layout(self)

    def _libressl(self):
        for dependency in self.dependencies.host.values():
            if dependency.ref and dependency.ref.name == "libressl":
                return dependency
        raise ConanException("libressl dependency is missing from the test graph")

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        binary = os.path.join(pkg, "bin", "acme-client")
        if not os.path.isfile(binary):
            raise ConanException(f"acme-client binary is missing: {binary}")

        libressl = self._libressl()
        tls_probe_source = os.path.join(self.source_folder, "test_libtls.c")
        tls_probe = os.path.join(self.build_folder, "test_libtls")
        os.makedirs(self.build_folder, exist_ok=True)

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = (
            compilers.get("c")
            or os.environ.get("CC")
            or shutil.which("clang")
            or shutil.which("cc")
            or "cc"
        )
        include_dir = os.path.join(libressl.package_folder, "include")
        lib_dir = os.path.join(libressl.package_folder, "lib")
        self.run(
            f'"{cc}" -I"{include_dir}" "{tls_probe_source}" -L"{lib_dir}" '
            f'-ltls -lssl -lcrypto -ldl -lpthread -o "{tls_probe}"'
        )

        if not can_run(self):
            return

        shell = os.environ.get("CONFIG_SHELL", "sh")
        script = os.path.join(self.source_folder, "test_acme_client.sh")
        normalized_script = os.path.join(self.build_folder, "test_acme_client.sh")
        script_text = load(self, script).replace("\r\n", "\n").replace("\r", "\n")
        save(self, normalized_script, script_text)
        self.run(f'"{shell}" "{normalized_script}" "{binary}"', env="conanrun")
        self.run(f'"{tls_probe}"', env="conanrun")
