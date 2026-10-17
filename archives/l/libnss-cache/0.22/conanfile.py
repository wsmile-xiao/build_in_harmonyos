#!/usr/bin/env python3
"""Conan recipe — libnss-cache 0.22 (Makefile project, no configure).

Upstream builds a shared NSS module `libnss_cache.so.2` with a plain Makefile
(make CC=... && make install). OHOS/musl adaptation (patch 0001):
  - Makefile links compat/fgetspent_r.o + compat/fgetsgent_r.o and adds -I.
    for tree-local nss.h/gshadow.h/shadow.h wrappers;
  - nss_cache.c builds shadow/gshadow support on all Linux (compat provides
    fgetspent_r/fgetsgent_r on non-glibc) and declares fgetpwent_r/fgetgrent_r.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LibnssCacheConan(ConanFile):
    name = "libnss-cache"
    version = "0.22"
    description = "libnss-cache 0.22 — file-based NSS module for caching remote directory service information"
    license = "LGPL-2.1"
    homepage = "https://github.com/google/libnss-cache"
    url = ""  # CI fills this

    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # codeload URL has no .tar.gz extension; conan infers archive format
        # from the filename, so pass an explicit one.
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="libnss-cache-0.22.tar.gz")

    def build(self):
        apply_conandata_patches(self)
        # R33: take compilers from Conan conf, never from shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        # Upstream Makefile defaults CC ?= gcc; force the Conan toolchain cc.
        self.run(f"make CC={cc} -j1", cwd=self.source_folder, env="conanbuild")

    def package(self):
        # Upstream `make install` copies libnss_cache.so.2 to $(DESTDIR)/usr/lib.
        copy(self, "libnss_cache.so.2", self.source_folder, os.path.join(self.package_folder, "lib"))
        # Consumers link against the unversioned soname; ship a copy without
        # the version suffix (HMDFS symlinks are unreliable, so copy instead).
        import shutil
        so2 = os.path.join(self.package_folder, "lib", "libnss_cache.so.2")
        shutil.copy2(so2, os.path.join(self.package_folder, "lib", "libnss_cache.so"))
        # Public headers used by consumers. nss_cache.h includes <nss.h>,
        # <gshadow.h>, <shadow.h>; on OHOS/musl those are provided by the
        # tree-local compat headers added in patch 0001, so ship them too.
        for hdr in ("nss_cache.h", "nss_test.h", "nss.h", "gshadow.h", "shadow.h"):
            copy(self, hdr, self.source_folder, os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["nss_cache"]
        self.cpp_info.set_property("cmake_file_name", "libnss-cache")
        self.cpp_info.set_property("cmake_target_name", "libnss-cache::libnss-cache")
        self.cpp_info.requires = []
