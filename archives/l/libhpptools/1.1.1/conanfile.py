#!/usr/bin/env python3
"""Conan recipe — libhpptools 1.1.1 (header-only, no build step).

HarmonyOS PC adaptation. Upstream: mateidavid/hpptools, tag 1.1.1 (MIT).
The project ships only headers under include/ (alg/logdiff/logger/logsum/
logsumset/pfor/strict_fstream/tpool/zstr); there is nothing to compile at
package time. The only external dependency is zlib, required by zstr.hpp
(the ZLib stream wrapper includes zlib.h and consumers link libz), declared
with transitive_headers/transitive_libs so consumers inherit it.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout

required_conan_version = ">=1.52.0"


class LibhpptoolsConan(ConanFile):
    name = "libhpptools"
    version = "1.1.1"
    description = (
        "A collection of C++ (mostly C++11) header-only utility libraries: "
        "alg, logdiff, logger, logsum, logsumset, pfor, strict_fstream, "
        "tpool, zstr"
    )
    homepage = "https://github.com/mateidavid/hpptools"
    topics = ("header-only", "utilities", "thread-pool", "logging", "zlib")
    license = "MIT"
    url = "https://github.com/mateidavid/hpptools"

    # Header-only: no shared/static artifacts, no 'shared' option needed.
    package_type = "header-library"

    # No compiled artifacts; settings are kept only for profile consistency.
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        pass

    def requirements(self):
        # zstr.hpp wraps zlib (includes zlib.h; consumers link libz), so the
        # dependency must be visible to consumers at both compile and link
        # time. zlib/1.3.1.2 is the latest OHOS adaptation published on ohpcd.
        self.requires(
            "zlib/1.3.1.2", transitive_headers=True, transitive_libs=True
        )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # Header-only package: there is nothing to compile here (the real
        # compile/run validation happens in test_package, which builds the
        # unmodified upstream Catch suite plus a consumer smoke test against
        # the packaged headers). This step applies declared patches (no-op:
        # zero patches for this adaptation) and validates the source
        # inventory, in the same spirit as the in-repo no-build recipes.
        apply_conandata_patches(self)
        expected = {
            "alg.hpp", "logdiff.hpp", "logger.hpp", "logsum.hpp",
            "logsumset.hpp", "pfor.hpp", "strict_fstream.hpp", "tpool.hpp",
            "zstr.hpp",
        }
        inc = os.path.join(self.source_folder, "include")
        found = {f for f in os.listdir(inc) if f.endswith(".hpp")}
        missing = expected - found
        if missing:
            raise ConanInvalidConfiguration(
                "hpptools header inventory mismatch, missing: %s"
                % ", ".join(sorted(missing))
            )

    def package(self):
        # Upstream layout: all headers are flat under include/.
        copy(
            self,
            "*.hpp",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_id(self):
        # No build artifacts: a single package_id independent of
        # os/compiler/build_type.
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "hpptools")
        self.cpp_info.set_property("cmake_target_name", "hpptools::hpptools")
        self.cpp_info.names["cmake_find_package"] = "hpptools"
        self.cpp_info.names["cmake_find_package_multi"] = "hpptools"
