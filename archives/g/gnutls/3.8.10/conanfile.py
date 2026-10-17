#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Gnutls, gnutls, 3.8.10, GNU Transport Layer Security Library, LGPL-2.1-or-later, https://www.gnutls.org/
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for system-name libraries.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os


class GnutlsConan(ConanFile):
    name = "gnutls"
    version = "3.8.10"
    description = "GNU Transport Layer Security Library"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.gnutls.org/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("nettle/3.10.2.1")
        self.requires("libtasn1/4.21.0")
        self.requires("libgcrypt/1.11.0")
        self.requires("libgpg-error/1.55")
        self.requires("gmp/6.3.0")
        self.requires("libunistring/1.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--prefix=/")
        tc.configure_args.append("--with-included-libtasn1=no")
        tc.configure_args.append("--with-included-unistring=no")
        tc.configure_args.append("--without-p11-kit")
        tc.configure_args.append("--disable-doc")
        tc.configure_args.append("--disable-valgrind-tests")
        # Set CC/CXX and PKG_CONFIG_PATH via buildenv so configure can find
        # clang and dependency .pc files (nettle/libtasn1/libgcrypt/gpg-error).
        self.buildenv_info.append("CC", "clang")
        self.buildenv_info.append("CXX", "clang++")
        pkg_dirs = []
        for dep_name in ["nettle", "libtasn1", "libgcrypt", "libgpg-error"]:
            try:
                dep = self.dependencies[dep_name]
                pkg_dir = os.path.join(dep.package_folder, "lib", "pkgconfig")
                if os.path.isdir(pkg_dir):
                    pkg_dirs.append(pkg_dir)
            except Exception:
                pass
        if pkg_dirs:
            self.buildenv_info.append("PKG_CONFIG_PATH", ":".join(pkg_dirs))
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Use self.run() with environment variables set directly on the command
        # line.  This bypasses AutotoolsToolchain which can't properly propagate
        # CC=clang and PKG_CONFIG_PATH on OHOS.
        pkg_dirs = []
        lib_dirs = []
        for dep_name in ["nettle", "libtasn1", "libgcrypt", "libgpg-error", "gmp", "libunistring"]:
            try:
                dep = self.dependencies[dep_name]
                pkg_dir = os.path.join(dep.package_folder, "lib", "pkgconfig")
                if os.path.isdir(pkg_dir):
                    pkg_dirs.append(pkg_dir)
                # gmp may not ship a .pc; add lib dir for -L flag
                lib_dir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    lib_dirs.append(lib_dir)
            except Exception:
                pass
        pkg_path = ":".join(pkg_dirs) if pkg_dirs else ""
        lib_path = ":".join(lib_dirs) if lib_dirs else ""
        src = self.source_folder
        ldflags = " ".join([f"-L{d}" for d in lib_dirs]) if lib_dirs else ""
        cflags = f"-fPIC -O2 -UNDEBUG -I{src}/lib -I/storage/Users/currentUser/usr/local/include"
        # Also add dependency include paths for headers (e.g. gmp.h)
        inc_dirs = []
        for dep_name in ["nettle", "libtasn1", "libgcrypt", "libgpg-error", "gmp", "libunistring"]:
            try:
                dep = self.dependencies[dep_name]
                for inc_dir in dep.cpp_info.includedirs:
                    if os.path.isdir(inc_dir):
                        inc_dirs.append(inc_dir)
            except Exception:
                pass
        for d in inc_dirs:
            cflags += f" -I{d}"
        self.run(f"cd {src} && CC=clang CXX=clang++"
                 f" CFLAGS='{cflags}'"
                 f" CXXFLAGS='{cflags}'"
                 f" LDFLAGS='{ldflags}'"
                 f" PKG_CONFIG_PATH='{pkg_path}'"
                 f" ./configure --prefix=/storage/Users/currentUser/usr/local"
                 " --with-included-libtasn1=no"
                 " --with-included-unistring=no"
                 " --without-p11-kit --disable-doc --disable-valgrind-tests")
        self.run(f"cd {src} && make -j1")

    def package(self):
        # 直接从源码构建树复制产物到包目录（make install 在 conan 环境不可靠）。
        src = self.source_folder
        pkg = self.package_folder
        libs = os.path.join(src, "lib", ".libs")
        inc = os.path.join(src, "lib", "includes", "gnutls")
        self.run(f"mkdir -p {pkg}/lib {pkg}/include/gnutls {pkg}/bin")
        # 库：复制真实文件 + 创建软链接
        self.run(f"cp {libs}/libgnutls.so.30.40.4 {libs}/libgnutlsxx.so.30.0.0 {pkg}/lib/")
        self.run(f"cd {pkg}/lib && ln -sf libgnutls.so.30.40.4 libgnutls.so.30 && "
                 f"ln -sf libgnutls.so.30 libgnutls.so && "
                 f"ln -sf libgnutlsxx.so.30.0.0 libgnutlsxx.so.30 && "
                 f"ln -sf libgnutlsxx.so.30 libgnutlsxx.so")
        # 头文件
        self.run(f"cp {inc}/*.h {pkg}/include/gnutls/")
        # pkg-config（gnutls.pc 在 {src}/lib/ 下，不是 pkgconfig/ 子目录）
        self.run(f"cp {src}/lib/gnutls.pc {pkg}/lib/")
        # CLI 工具
        self.run(f"cp {src}/src/.libs/gnutls-cli {src}/src/.libs/gnutls-serv {src}/src/.libs/certtool {pkg}/bin/")

    def package_info(self):
        self.cpp_info.libs = ["gnutls"]
