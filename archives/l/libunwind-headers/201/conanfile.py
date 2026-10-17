#!/usr/bin/env python3
"""Conan recipe for the Apple libunwind 201 public headers.

This mirrors the Homebrew `libunwind-headers` formula: it installs only the
public header files from the upstream `libunwind/include/` tree together with
the `libunwind/src/*.h*` private headers that Homebrew exposes under
`include/libunwind/`. No library is built; the package is header-only and
exists to give consumers the public declarations, data layouts, and
architecture-specific unwind register/encoding definitions.
"""

import glob
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class LibunwindHeadersConan(ConanFile):
    name = "libunwind-headers"
    version = "201"
    package_type = "header-library"

    description = (
        "Public header files for Apple's libunwind, a C API for "
        "determining the call-chain of a program"
    )
    license = "APSL-2.0"
    homepage = "https://github.com/apple-oss-distributions/libunwind"
    url = "https://github.com/apple-oss-distributions/libunwind"
    topics = ("libunwind", "unwind", "headers", "apple")

    # Settings are declared so consumers can match the build context, but the
    # package carries no compiled artifact (see package_id).
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Header-only package: apply the (empty) patch set and verify the
        # upstream include directory is present so a broken tarball fails early.
        apply_conandata_patches(self)
        unw_dir = os.path.join(self.source_folder, "libunwind")
        include_dir = os.path.join(unw_dir, "include")
        if not os.path.isdir(include_dir):
            raise RuntimeError(
                "upstream libunwind/include directory was not found"
            )

    def package(self):
        unw_dir = os.path.join(self.source_folder, "libunwind")

        # Mirror Homebrew: include.install Dir["include/*"]
        copy(
            self,
            "*",
            src=os.path.join(unw_dir, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )

        # Mirror Homebrew: (include/"libunwind").install Dir["src/*.h*"]
        src_headers = glob.glob(os.path.join(unw_dir, "src", "*.h*"))
        for header in src_headers:
            copy(
                self,
                os.path.basename(header),
                src=os.path.dirname(header),
                dst=os.path.join(self.package_folder, "include", "libunwind"),
            )

        # License: the Apple oss-distributions tarball ships APPLE_LICENSE at
        # the archive root; install it when present, otherwise the license
        # metadata above is the authoritative declaration.
        for license_name in ("APPLE_LICENSE", "LICENSE", "LICENSE.txt"):
            candidate = os.path.join(self.source_folder, license_name)
            if os.path.isfile(candidate):
                copy(
                    self,
                    license_name,
                    src=self.source_folder,
                    dst=os.path.join(self.package_folder, "licenses"),
                )
                break

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "libunwind-headers")
        self.cpp_info.set_property(
            "cmake_target_name", "libunwind-headers::libunwind-headers"
        )
