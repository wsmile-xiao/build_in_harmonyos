#!/usr/bin/env python3
"""Conan recipe — menu-cache 1.1.0.

menu-cache is the LXDE menu cache library.
Bypass autotools entirely to avoid configure link test failure on OHOS.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class MenucacheConan(ConanFile):
    name = "menu-cache"
    version = "1.1.0"
    description = "menu-cache 1.1.0"
    license = "MIT"
    homepage = "https://github.com/lxde/menu-cache"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.88.0")
        self.requires("libfm-extra/1.3.2.1")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply config.guess/config.sub patches for OHOS triplet support
        apply_conandata_patches(self)

        # Create pcre2.pc symlink if missing
        pcre2_dir = os.path.join(
            self.dependencies.host["pcre2"].package_folder, "lib", "pkgconfig"
        )
        pcre2_sym = os.path.join(pcre2_dir, "pcre2.pc")
        if not os.path.exists(pcre2_sym):
            os.symlink("libpcre2-8.pc", pcre2_sym)

        # Generate menu-cache.h from menu-cache.h.in
        glib = self.dependencies.host["glib"]
        lfm = self.dependencies.host["libfm-extra"]

        src_dir = self.source_folder
        content = open(os.path.join(src_dir, "libmenu-cache", "menu-cache.h.in")).read()
        content = content.replace("@MC_VERSION_MAJOR@", "1")
        content = content.replace("@MC_VERSION_MINOR@", "1")
        content = content.replace("@MC_VERSION_MICRO@", "0")
        # Write generated header to source dir
        with open(os.path.join(src_dir, "libmenu-cache", "menu-cache.h"), "w") as f:
            f.write(content)

        # Compile menu-cache.c directly with clang
        cc = os.environ.get("CC", "clang")
        ar = os.environ.get("AR", "llvm-ar")

        inc_dirs = " ".join([
            f"-I{src_dir}/libmenu-cache",
            f"-I{glib.package_folder}/include",
            f"-I{glib.package_folder}/include/glib-2.0",
            f"-I{glib.package_folder}/lib/glib-2.0/include",
            f"-I{lfm.package_folder}/include",
            f"-I{lfm.package_folder}/include/libfm-1.0",
        ])
        defines = '-DMENUCACHE_LIBEXECDIR="" -DMENUCACHE_LOCALEDIR="" -DGETTEXT_PACKAGE="menu-cache"'

        src = os.path.join(src_dir, "libmenu-cache", "menu-cache.c")
        obj = os.path.join(self.build_folder, "menu-cache.o")
        self.run(f"{cc} -c {inc_dirs} {defines} -fPIC {src} -o {obj}")

        # Archive into static library
        lib_dir = os.path.join(self.build_folder, ".libs")
        os.makedirs(lib_dir, exist_ok=True)
        self.run(f"{ar} rcs {lib_dir}/libmenu-cache.a {obj}")

    def package(self):
        lib_dir = os.path.join(self.package_folder, "lib")
        inc_dir = os.path.join(self.package_folder, "include")
        os.makedirs(lib_dir)
        os.makedirs(inc_dir)

        shutil.copy2(
            os.path.join(self.build_folder, ".libs", "libmenu-cache.a"),
            lib_dir,
        )
        shutil.copy2(
            os.path.join(self.source_folder, "libmenu-cache", "menu-cache.h"),
            inc_dir,
        )

    def package_info(self):
        self.cpp_info.libs = ["menu-cache"]