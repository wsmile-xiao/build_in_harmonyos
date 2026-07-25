#!/usr/bin/env python3
"""Conan recipe for libunistring 1.0 on OHOS."""
import os

from conan import ConanFile
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
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return compilers.get("c", "clang")

    def _configure_args(self):
        configure_args = []
        if self.options.shared:
            configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            configure_args.extend(["--disable-shared", "--enable-static"])
        configure_args.extend([
            "--disable-rpath",
            "--disable-dependency-tracking",
            "--cache-file=config.cache",
        ])
        return configure_args

    def build(self):
        apply_conandata_patches(self)
        tmpdir = os.environ.get("TMPDIR", os.path.join(self.build_folder, "tmp"))
        os.makedirs(tmpdir, exist_ok=True)
        config_cache = os.path.join(self.source_folder, "config.cache")
        with open(config_cache, "w", encoding="utf-8") as cache:
            cache.write("gl_cv_socklen_t_equiv=int\n")
            cache.write("gl_cv_socket_ipv4=yes\n")
            cache.write("gl_cv_socket_ipv6=no\n")
            cache.write("gl_cv_socket_unix=yes\n")
        for filename in ("configure", "build-aux/config.guess", "build-aux/config.sub"):
            path = os.path.join(self.source_folder, filename)
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                    content = handle.read()
                content = content.replace("umask 077", "umask 022")
                content = content.replace("/tmp", tmpdir)
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(content)
        shell = "/system/bin/sh"
        os.environ["SHELL"] = shell
        os.environ["CONFIG_SHELL"] = shell
        configure_args = self._configure_args()
        configure_args.extend([
            "--prefix=/",
            "--bindir=${prefix}/bin",
            "--sbindir=${prefix}/bin",
            "--libdir=${prefix}/lib",
            "--includedir=${prefix}/include",
            "--oldincludedir=${prefix}/include",
        ])
        cc = self._compiler()
        build_env = f"SHELL={shell} CONFIG_SHELL={shell} CC={cc} LD=ld.lld AR=llvm-ar RANLIB=llvm-ranlib STRIP=:"
        self.run(f"{build_env} {shell} ./configure {' '.join(configure_args)}", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)

    def package(self):
        self.run(f"make DESTDIR={self.package_folder} install", cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["unistring"]
        self.cpp_info.set_property("pkg_config_name", "libunistring")
