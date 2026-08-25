#!/usr/bin/env python3
"""Conan recipe for libselinux 3.10.1 on HarmonyOS PC.

libselinux is a plain Makefile project (no autotools/CMake/meson).
The SELinuxProject monorepo archive contains both libselinux and libsepol.
Only libselinux targets are built here; libsepol is consumed as a Conan dependency.

R33: Never use ${CC} or ${CFLAGS} in self.run() — they are empty on CI workers.
     Get compiler from Conan: self.conf.get("tools.build:compiler_executables:c", ...)
"""

import os
from conan import ConanFile
from conan.tools.files import get, copy, load, save, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibselinuxConan(ConanFile):
    name = "libselinux"
    version = "3.10.1"
    description = "SELinux library for security context management"
    license = "Public Domain"
    homepage = "https://github.com/SELinuxProject/selinux"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libsepol/3.10")
        self.requires("pcre2/10.45")
        # OHOS musl libc does not include fts.h; use musl-fts standalone
        self.requires("musl-fts/1.2.7")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True, filename="selinux-3.10.tar.gz")

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan conf
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c", "clang")

        # Gather dependency info
        dep_sepol = self.dependencies["libsepol"]
        dep_pcre2 = self.dependencies["pcre2"]
        dep_fts = self.dependencies["musl-fts"]

        # Build PKG_CONFIG_PATH from deps
        pkg_paths = []
        for dep in [dep_pcre2, dep_sepol, dep_fts]:
            pf = dep.package_folder
            if pf:
                pkg_paths.append(os.path.join(pf, "lib", "pkgconfig"))
        pkg_config_path = os.pathsep.join(pkg_paths)
        if pkg_config_path:
            os.environ["PKG_CONFIG_PATH"] = pkg_config_path

        # Build extra CFLAGS from dep include paths
        inc_flags = ""
        for dep in [dep_sepol, dep_pcre2, dep_fts]:
            pf = dep.package_folder
            if pf:
                include = os.path.join(pf, "include")
                if os.path.isdir(include):
                    inc_flags += f" -I{include}"

        # E091: OHOS sys/linux socket.h conflict → -D__MUSL__ 
        # (triggers #ifndef __MUSL__ guard in sys/socket.h)
        ext_cflags = f"{inc_flags} -D__MUSL__"
        # FTS_LDLIBS: musl needs -lfts (libselinux Makefile default is empty for glibc)
        fts_libs = f"-L{dep_fts.package_folder}/lib -lfts"
        sepol_libs = f"-L{dep_sepol.package_folder}/lib -l:libsepol.a"
        pcre2_libs = f"-L{dep_pcre2.package_folder}/lib -lpcre2-8"

        # Build libselinux static library (only libselinux subdir, not monorepo root)
        # monorepo SUBDIRS = libsepol libselinux libsemanage checkpolicy secilc policycoreutils
        # We must NOT build libsepol (it's a Conan dependency) or other subprojects.
        self.run(
            f"make -C {self.source_folder}/libselinux -j1 CC={cc} "
            f"CFLAGS='{ext_cflags}' "
            f"LDFLAGS='{sepol_libs} {fts_libs} {pcre2_libs}' "
            f"USE_PCRE2=y DISABLE_SHARED=y "
            f"FTS_LDLIBS='-lfts' "
            f"PREFIX=/usr LIBDIR=/usr/lib INCLUDEDIR=/usr/include "
            f"DESTDIR={self.package_folder} "
            f"all",
        )

    def package(self):
        # Install headers (monorepo: libselinux subdir)
        src_include = os.path.join(self.source_folder, "libselinux", "include", "selinux")
        if os.path.isdir(src_include):
            copy(self, "*.h", src_include,
                 os.path.join(self.package_folder, "include", "selinux"))

        # Install static lib
        src = os.path.join(self.source_folder, "libselinux", "src")
        copy(self, "libselinux.a", src, os.path.join(self.package_folder, "lib"))
        # Install pkg-config file
        copy(self, "libselinux.pc", src, os.path.join(self.package_folder, "lib", "pkgconfig"))

        # R41: the upstream Makefile generates libselinux.pc from libselinux.pc.in
        # via `sed` substituting PREFIX/LIBDIR/INCLUDEDIR, and the recipe builds
        # with PREFIX=/usr so the copied .pc hard-codes prefix=/usr. Consumers
        # resolving the raw package .pc (PKG_CONFIG_PATH into the installed
        # package) then get -I/usr/include and cannot find selinux/selinux.h.
        # Rewrite the packaged .pc so prefix resolves to the real package folder
        # inside the Conan cache (absolute path — never /usr, no env workaround).
        pc_path = os.path.join(self.package_folder, "lib", "pkgconfig", "libselinux.pc")
        if os.path.isfile(pc_path):
            pc_text = load(self, pc_path)
            prefix = self.package_folder
            pc_text = pc_text.replace("prefix=/usr", f"prefix={prefix}")
            pc_text = pc_text.replace("/usr/lib", f"{prefix}/lib")
            pc_text = pc_text.replace("/usr/include", f"{prefix}/include")
            save(self, pc_path, pc_text)

        # Install utils as smoke tools
        utils_src = os.path.join(self.source_folder, "libselinux", "utils")
        if os.path.isdir(utils_src):
            copy(self, "*", utils_src,
                 os.path.join(self.package_folder, "bin"),
                 excludes=["*.c", "Makefile", "*.o", "*.lo", "*.la"])

    def package_info(self):
        self.cpp_info.libs = ["selinux"]
        self.cpp_info.set_property("pkg_config_name", "libselinux")
        # libselinux links against libsepol, libpcre2-8, musl-fts, -ldl
        self.cpp_info.system_libs = ["dl"]