#!/usr/bin/env python3
"""Conan recipe — proftpd-mod-procfs 0.1 (ProFTPD mod_procfs DSO module).

mod_procfs controls the visibility/use of the /proc filesystem for
ProFTPD. The upstream tarball ships only mod_procfs.c; compiling it into
a DSO requires the ProFTPD headers, so this recipe uses the proftpd
1.3.9c source tree as the build host (patched for OHOS, same 8 patches
as proftpd-mod_radius) and compiles mod_procfs.c (bundled via
export_sources) directly with clang into a shared object.
"""
import os

from conan import ConanFile
from conan.tools.files import (get, copy, apply_conandata_patches,
                               export_conandata_patches)
from conan.tools.layout import basic_layout
from conan.errors import ConanException


class ProftpdmodprocfsConan(ConanFile):
    name = "proftpd-mod-procfs"
    version = "0.1"
    description = "ProFTPD mod_procfs — configurable procfs/sysfs visibility module"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/Castaglia/proftpd-mod_procfs"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)
        # Bundle mod_procfs.c (single upstream source file) and the
        # proftpd headers it needs are taken from the proftpd source tree.
        copy(self, "mod_procfs.c", self.recipe_folder,
             self.export_sources_folder)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply OHOS portability patches to the proftpd source tree
        apply_conandata_patches(self)

        src = self.source_folder
        mod = os.path.join(self.export_sources_folder, "mod_procfs.c")
        if not os.path.isfile(mod):
            raise ConanException("bundled mod_procfs.c missing")

        # Run configure to generate config.h (include/os.h requires it);
        # the applied patches let configure run on OHOS. No full build is
        # needed — only the generated config.h plus the header tree.
        self.run(
            f'cd "{src}" && ./configure --disable-nls --enable-dso '
            f'--enable-shared --disable-openssl '
            f'--disable-ctrls --disable-sql --disable-lua --disable-memcache '
            f'--disable-redis --disable-tests >/dev/null 2>&1'
        )

        # include/version.h requires include/buildstamp.h, which the
        # Makefile generates at build time; emit the equivalent here.
        stamp = os.path.join(src, "include", "buildstamp.h")
        if not os.path.isfile(stamp):
            self.run(
                f'echo \'#define BUILD_STAMP "OHOS build"\' > "{stamp}"'
            )

        # Compile the DSO directly with clang (PR_SHARED_MODULE like prxs);
        # headers come from the proftpd source tree (include/ + root config.h)
        obj = os.path.join(self.build_folder, "mod_procfs.o")
        self.run(
            f'clang -fPIC -DPR_SHARED_MODULE -DLINUX '
            f'-I"{src}/include" -I"{src}" -c "{mod}" -o "{obj}"'
        )
        so = os.path.join(self.build_folder, "mod_procfs.so")
        self.run(f'clang -shared -o "{so}" "{obj}"')

    def package(self):
        so = os.path.join(self.build_folder, "mod_procfs.so")
        if not os.path.exists(so):
            raise ConanException("mod_procfs.so not built")
        copy(self, "mod_procfs.so", self.build_folder,
             os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libs = ["mod_procfs"]
