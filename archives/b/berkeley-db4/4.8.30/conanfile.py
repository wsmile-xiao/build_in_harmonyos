#!/usr/bin/env python3
"""Conan recipe for Berkeley DB 4.8.30.

Berkeley DB uses a non-standard autotools layout: the configure script
is in dist/ and must be run from a build_unix/ directory.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, chdir
from conan.tools.layout import basic_layout
import os


class Berkeleydb4Conan(ConanFile):
    name = "berkeley-db4"
    version = "4.8.30"
    description = "Berkeley DB is a family of embedded key-value database libraries providing scalable high-performance data management"
    license = "Sleepycat"
    homepage = "https://www.oracle.com/database/berkeley-db/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Berkeley DB's configure is in dist/ and must be run from build_unix/
        build_unix = os.path.join(self.source_folder, "build_unix")
        os.makedirs(build_unix, exist_ok=True)
        with chdir(self, build_unix):
            # On HarmonyOS HMDFS, ld.lld fails; use ld.bfd via -fuse-ld=bfd.
            # --host skips cross-compile detection (unsigned test binaries can't execute on HMDFS).
            prefix = self.package_folder
            shared_flags = "--enable-shared --enable-static" if self.options.shared else "--disable-shared --enable-static"
            self.run(
                f'../dist/configure --prefix="{prefix}" '
                f'--build=aarch64-unknown-linux-gnu '
                f'--host=aarch64-unknown-linux-ohos '
                f'{shared_flags} '
                f'CC="clang -fuse-ld=bfd" '
                f'CXX="clang++ -fuse-ld=bfd" '
                f'LD=ld.bfd'
            )
            self.run("make -j1")

    def package(self):
        with chdir(self, os.path.join(self.source_folder, "build_unix")):
            self.run("make install")

    def package_info(self):
        self.cpp_info.libs = ["db-4.8"]
