#!/usr/bin/env python3

import os
import shutil
from urllib.parse import unquote

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibcsvConan(ConanFile):
    name = "libcsv"
    version = "3.0.3"
    description = "Fast and flexible CSV parser and writer library written in ANSI C"
    license = "LGPL-2.1-or-later"
    homepage = "https://sourceforge.net/projects/libcsv/"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }

    default_options = {
        "shared": False,
        "fPIC": True,
    }
    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libcsv is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        sources = dict(self.conan_data["sources"])
        urls = sources.get("url", [])
        if isinstance(urls, str):
            urls = [urls]

        for url in urls:
            if not isinstance(url, str) or not url.startswith("file://"):
                continue

            encoded_path = url[len("file://"):]
            decoded_path = unquote(encoded_path)

            if (
                encoded_path != decoded_path
                and os.path.isfile(encoded_path)
                and not os.path.exists(decoded_path)
            ):
                shutil.copyfile(encoded_path, decoded_path)

        get(self, **sources, strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--prefix=/")

        if self.settings.os == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-ohos",
                "--host=aarch64-unknown-linux-ohos",
            ])

        if self.options.shared:
            tc.configure_args.extend([
                "--enable-shared",
                "--disable-static",
            ])
        else:
            tc.configure_args.extend([
                "--disable-shared",
                "--enable-static",
            ])

        tc.generate()

    def build(self):
        for generated in ("aclocal.m4", "configure", "Makefile.in"):
            path = os.path.join(self.source_folder, generated)
            if os.path.exists(path):
                os.utime(path, None)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        autotools.make(
            target="check",
            args=["-j1", "check_csv_LDADD=libcsv.la"],
        )

    def package(self):
        autotools = Autotools(self)
        autotools.install()

        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

        copy(
            self,
            "COPYING.LESSER",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
    def package_info(self):
        self.cpp_info.libs = ["csv"]

        self.cpp_info.set_property("cmake_file_name", "libcsv")
        self.cpp_info.set_property("cmake_target_name", "libcsv::libcsv")

        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH",
            os.path.join(self.package_folder, "lib"),
        )
