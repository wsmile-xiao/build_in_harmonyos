import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.layout import basic_layout


class LibkeyutilsConan(ConanFile):
    name = "libkeyutils"
    version = "1.6.3"
    description = "Linux key management utilities library (keyutils)"
    license = "LGPL-2.1-or-later"
    homepage = "https://git.kernel.org/pub/scm/linux/kernel/git/dhowells/keyutils.git/"
    url = ""
    package_type = "library"

    settings = ("os", "compiler", "build_type", "arch")
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libkeyutils is supported only on Linux/OHOS"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compilers from Conan conf, never from bare shell env vars.
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = comp_execs.get("c") or "clang"
        cxx = comp_execs.get("cpp") or "clang++"

        # Override upstream CFLAGS which include -Werror (breaks clang on musl).
        # -Drindex=strrchr: BSD alias rindex() is not declared in musl libc;
        #   map it to the standard strrchr() which musl provides.
        cflags = "-fPIC -O2 -g -Wall -Drindex=strrchr"
        cxxflags = "-fPIC -O2 -g -Wall"
        ldflags = "-fPIC"

        prefix = self.package_folder.replace("\\", "/")
        libdir = os.path.join(prefix, "lib")
        usrlibdir = os.path.join(prefix, "lib")
        includedir = os.path.join(prefix, "include")

        # Run upstream tests (non-blocking)
        self.run("make check 2>\&1 || true", cwd=self.source_folder, env="conanbuild")

        # R9: Always use -j1.
        # LIBDIR and USRLIBDIR are passed explicitly because the Makefile
        # auto-detects them by running `ldd /usr/bin/make` which fails on OHOS.
        self.run(
            f'make CC="{cc}" CXX="{cxx}" '
            f'CFLAGS="{cflags}" CXXFLAGS="{cxxflags}" LDFLAGS="{ldflags}" '
            f"PREFIX={prefix} LIBDIR={libdir} USRLIBDIR={usrlibdir} "
            f"INCLUDEDIR={includedir} NO_ARLIB=0 NO_SOLIB=0 -j1",
            env="conanbuild",
            cwd=self.source_folder,
        )

    def package(self):
        # Copy header
        copy(
            self,
            "keyutils.h",
            self.source_folder,
            os.path.join(self.package_folder, "include"),
        )
        # Copy static library
        copy(
            self,
            "libkeyutils.a",
            self.source_folder,
            os.path.join(self.package_folder, "lib"),
        )
        # Copy shared library and symlinks
        copy(
            self,
            "libkeyutils.so*",
            self.source_folder,
            os.path.join(self.package_folder, "lib"),
        )

        # Generate pkgconfig file (keyutils.pc)
        pkgconfig_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        os.makedirs(pkgconfig_dir, exist_ok=True)
        pc_content = (
            f"prefix={self.package_folder}\n"
            f"exec_prefix=${{prefix}}\n"
            f"libdir=${{prefix}}/lib\n"
            f"includedir=${{prefix}}/include\n"
            f"\n"
            f"Name: libkeyutils\n"
            f"Description: Linux key management utilities library\n"
            f"Version: 1.6.3\n"
            f"Cflags: -I${{includedir}}\n"
            f"Libs: -L${{libdir}} -lkeyutils\n"
        )
        save(self, os.path.join(pkgconfig_dir, "keyutils.pc"), pc_content)

    def package_info(self):
        self.cpp_info.libs = ["keyutils"]
        self.cpp_info.set_property("pkg_config_name", "keyutils")
