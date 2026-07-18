#!/usr/bin/env python3
"""Conan recipe for the Homebrew gcli 2.12.0 task."""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class GcliConan(ConanFile):
    name = "gcli"
    version = "2.12.0"
    package_type = "application"

    description = "Portable command-line client for Git forges"
    license = "BSD-2-Clause"
    homepage = "https://sr.ht/~herrhotzenplotz/gcli"
    url = "https://git.sr.ht/~herrhotzenplotz/gcli"
    topics = ("github", "gitlab", "gitea", "bugzilla", "cli")

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("curl/8.19.0")
        self.requires("openssl/1.1.1w")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("gcli supports Linux/OHOS builds only")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._write_libcrypto_pc()

    def _write_libcrypto_pc(self):
        openssl = self.dependencies["openssl"].package_folder
        os.makedirs(self.generators_folder, exist_ok=True)
        pc_path = os.path.join(self.generators_folder, "libcrypto.pc")
        with open(pc_path, "w", encoding="utf-8") as pc:
            pc.write(
                f"prefix={openssl}\n"
                "libdir=${prefix}/lib\n"
                "includedir=${prefix}/include\n\n"
                "Name: libcrypto\n"
                "Description: OpenSSL crypto library\n"
                "Version: 1.1.1w\n"
                "Libs: -L${libdir} -lcrypto\n"
                "Cflags: -I${includedir}\n"
            )

    def _pkg_config_path(self):
        paths = [self.generators_folder]
        for dep in self.dependencies.values():
            pkgconfig_dir = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(pkgconfig_dir):
                paths.append(pkgconfig_dir)
        existing = os.environ.get("PKG_CONFIG_PATH")
        if existing:
            paths.append(existing)
        return os.pathsep.join(paths)

    def _env_prefix(self):
        assignments = {
            "PKG_CONFIG_PATH": self._pkg_config_path(),
            "CCACHE": "env",
        }
        return " ".join(f"{key}={shlex.quote(value)}" for key, value in assignments.items())

    def build(self):
        args = [
            "--prefix=/",
            "--disable-libedit",
            "--disable-libreadline",
            "--disable-liblowdown",
            "--disable-librt",
            "--release",
        ]
        configure = os.path.join(self.source_folder, "configure")
        self.run(f"{self._env_prefix()} {shlex.quote(configure)} {' '.join(args)}")
        self.run("make -j1")

    def package(self):
        self.run(f"make install DESTDIR={shlex.quote(self.package_folder)}")
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
