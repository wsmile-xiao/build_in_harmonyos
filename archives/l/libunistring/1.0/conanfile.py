#!/usr/bin/env python3
"""Conan recipe for libunistring 1.0 on OHOS."""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibunistringConan(ConanFile):
    name = "libunistring"
    version = "1.0"
    description = "Unicode string library from GNU"
    license = "GPL-3.0-or-later OR LGPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/libunistring/"
    url = "https://www.gnu.org/software/libunistring/"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self):
        return self._tool("c", "clang")

    def _tool(self, name, default):
        tools = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return tools.get(name, default)

    def _build_environment(self, tmpdir=None):
        shell = "/system/bin/sh"
        build_environment = Environment()
        if tmpdir:
            build_environment.define("TMPDIR", tmpdir)
        build_environment.define("SHELL", shell)
        build_environment.define("CONFIG_SHELL", shell)
        build_environment.define("CC", self._compiler())
        build_environment.define("LD", self._tool("ld", "ld.lld"))
        build_environment.define("AR", self._tool("ar", "llvm-ar"))
        build_environment.define("RANLIB", self._tool("ranlib", "llvm-ranlib"))
        build_environment.define("STRIP", self._tool("strip", ":"))
        return shell, build_environment

    def _configure_args(self, config_cache):
        configure_args = []
        if self.options.shared:
            configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            configure_args.extend(["--disable-shared", "--enable-static"])
        configure_args.extend([
            "--disable-rpath",
            "--disable-dependency-tracking",
            f"--cache-file={config_cache}",
        ])
        return configure_args

    def build(self):
        apply_conandata_patches(self)
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        config_cache = os.path.join(self.build_folder, "config.cache")
        with open(config_cache, "w", encoding="utf-8") as cache:
            cache.write("gl_cv_socklen_t_equiv=int\n")
            cache.write("gl_cv_socket_ipv4=yes\n")
            cache.write("gl_cv_socket_ipv6=no\n")
            cache.write("gl_cv_socket_unix=yes\n")
        configure_args = self._configure_args(config_cache)
        configure_args.extend([
            "--prefix=/",
            "--bindir=${prefix}/bin",
            "--sbindir=${prefix}/bin",
            "--libdir=${prefix}/lib",
            "--includedir=${prefix}/include",
            "--oldincludedir=${prefix}/include",
        ])
        shell, build_environment = self._build_environment(tmpdir)
        with build_environment.vars(self).apply():
            self.run(f"{shell} ./configure {' '.join(configure_args)}", cwd=self.source_folder)
            self.run("make -j1", cwd=self.source_folder)

    def package(self):
        _, build_environment = self._build_environment()
        with build_environment.vars(self).apply():
            self.run(f"make DESTDIR={self.package_folder} install", cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["unistring"]
        self.cpp_info.set_property("pkg_config_name", "libunistring")
