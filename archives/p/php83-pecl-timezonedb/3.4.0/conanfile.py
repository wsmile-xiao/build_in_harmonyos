#!/usr/bin/env python3
"""Conan recipe for php83-pecl-timezonedb 3.4.0 (timezonedb 2025.2).

PHP PECL extension providing updated timezone database.
Built via direct C compilation using PHP development headers from the php conan dependency.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches, chdir
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class Php83PeclTimezonedbConan(ConanFile):
    name = "php83-pecl-timezonedb"
    version = "3.4.0"
    description = "PHP timezonedb extension providing updated timezone data"
    license = "PHP-3.01"
    homepage = "https://pecl.php.net/package/timezonedb"
    url = ""

    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("php/8.5.8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=False)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # Ensure OHOS SDK lib directory is in LD_LIBRARY_PATH for lld
        ohos_sdk_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        if os.path.isdir(ohos_sdk_lib):
            cur_ld = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = f"{ohos_sdk_lib}:{cur_ld}" if cur_ld else ohos_sdk_lib

        php = self.dependencies["php"]
        php_inc = os.path.join(php.package_folder, "include", "php")

        includes = " ".join([
            f"-I{php_inc}",
            f"-I{php_inc}/main",
            f"-I{php_inc}/Zend",
            f"-I{php_inc}/TSRM",
            f"-I{php_inc}/ext/date/lib",
        ])

        defines = "-DCOMPILE_DL_TIMEZONEDB -DHAVE_CONFIG_H"

        src_dir = os.path.join(self.source_folder, "timezonedb-2025.2")
        with chdir(self, src_dir):
            self.run(
                f"$CC -fPIC -shared -O2 -Wall {defines} {includes} "
                f"-o timezonedb.so timezonedb.c",
                env="conanbuild"
            )

    def package(self):
        src_dir = os.path.join(self.source_folder, "timezonedb-2025.2")
        copy(self, "timezonedb.so", src=src_dir,
             dst=os.path.join(self.package_folder, "lib", "php", "extensions"))

    def package_info(self):
        self.cpp_info.libs = ["timezonedb"]
        self.cpp_info.libdirs = ["lib/php/extensions"]
