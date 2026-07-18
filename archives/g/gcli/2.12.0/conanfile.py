#!/usr/bin/env python3
"""Conan recipe for the Homebrew gcli 2.12.0 task."""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
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

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("gcli supports Linux/OHOS builds only")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        self._write_libcurl_pc()
        self._write_libcrypto_pc()

    def _default_prefix(self):
        return os.environ.get("DEFAULT_PREFIX", "/storage/Users/currentUser/usr/local")

    def _write_default_prefix_pc(self, filename, name, description, version, libs):
        prefix = self._default_prefix()
        os.makedirs(self.generators_folder, exist_ok=True)
        pc_path = os.path.join(self.generators_folder, filename)
        with open(pc_path, "w", encoding="utf-8") as pc:
            pc.write(
                f"prefix={prefix}\n"
                "libdir=${prefix}/lib\n"
                "includedir=${prefix}/include\n\n"
                f"Name: {name}\n"
                f"Description: {description}\n"
                f"Version: {version}\n"
                f"Libs: -L${{libdir}} {libs}\n"
                "Cflags: -I${includedir}\n"
            )

    def _write_libcurl_pc(self):
        self._write_default_prefix_pc(
            "libcurl.pc",
            "libcurl",
            "HarmonyOS PC libcurl from DEFAULT_PREFIX",
            "8.15.0",
            "-lcurl -lssl -lcrypto -lz",
        )

    def _write_libcrypto_pc(self):
        self._write_default_prefix_pc(
            "libcrypto.pc",
            "libcrypto",
            "HarmonyOS PC OpenSSL crypto library from DEFAULT_PREFIX",
            "3.5.6",
            "-lcrypto",
        )

    def _pkg_config_path(self):
        sysroot = self._default_prefix()
        paths = [
            self.generators_folder,
            os.path.join(sysroot, "lib", "pkgconfig"),
            os.path.join(sysroot, "share", "pkgconfig"),
        ]
        existing = os.environ.get("PKG_CONFIG_PATH")
        if existing:
            paths.append(existing)
        return os.pathsep.join(paths)

    def _append_env(self, name, value):
        existing = os.environ.get(name, "")
        return f"{existing} {value}".strip()

    def _env_prefix(self):
        sysroot = self._default_prefix()
        assignments = {
            "PKG_CONFIG_PATH": self._pkg_config_path(),
            "CPPFLAGS": self._append_env("CPPFLAGS", f"-I{sysroot}/include"),
            "LDFLAGS": self._append_env("LDFLAGS", f"-L{sysroot}/lib -Wl,-rpath,{sysroot}/lib"),
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
        sysroot = self._default_prefix()
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(sysroot, "lib"))
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
