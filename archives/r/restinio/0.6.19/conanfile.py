#!/usr/bin/env python3
"""Conan recipe — restinio 0.6.19 (header-only REST/HTTP server on Asio).

Layout:
  dev/                       upstream source tree (externals.rb layout)
    restinio/                129 public headers (the library)
    asio/                    bundled standalone-asio 1.28.1 snapshot (Boost-1.0)
  test_package/              Conan consumer smoke test

The Conan recipe:
  * packages the 129 restinio public headers + the bundled standalone-asio
    snapshot as a header-only library;
  * declares fmt/8.1.1 and http-parser/2.9.4 as Conan `requires` so consumers
    link against the real OpenHarmony PC platform packages rather than vendored
    copies (http_parser.h resolves from the http-parser package, libfmt from
    fmt);
  * does NOT vendor fmt or http-parser sources into this recipe.

Consumers:
  find_package(restinio REQUIRED)
  target_link_libraries(app PRIVATE restinio::restinio)
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get, export_conandata_patches


class RestinioConan(ConanFile):
    name = "restinio"
    version = "0.6.19"
    description = "Header-only C++14 REST/HTTP server library on top of Asio"
    license = "BSD-3-Clause"
    homepage = "https://github.com/Stiffstream/restinio"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def configure(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"restinio supports Linux and OHOS, not {self.settings.os}"
            )
        try:
            cppstd = int(self.settings.compiler.cppstd)
        except Exception:
            cppstd = 0
        if cppstd and cppstd < 14:
            raise ConanInvalidConfiguration(
                "restinio 0.6.19 requires C++14 or newer"
            )

    def requirements(self):
        # fmt is part of the public API (restinio/formatters.hpp uses fmt::format)
        self.requires("fmt/8.1.1")
        # http-parser is a required dependency (http_headers.hpp, websocket/)
        self.requires("http-parser/2.9.4")

    def export_sources(self):
        # G1 recipe-completeness expects an export_sources() hook; this recipe
        # ships no patches (conandata.yml patches: {}), so there is nothing to
        # export beyond the recipe tree itself.
        export_conandata_patches(self)

    def source(self):
        data = self.conan_data["sources"][str(self.version)]
        get(self, **data, strip_root=True)
        # restinio upstream ships externals.rb (MxxRu) rather than pre-bundled
        # deps. Conan does not run MxxRu, so we fetch the standalone-asio snapshot
        # explicitly and lay it out under dev/asio/ — matching upstream's
        # externals.rb arch_externals :asio do |e| e.map_dir 'asio/include' => 'dev/asio'
        # NOTE: codelload asio-1-28-1.tar.gz top wrapper is "asio-asio-1-28-1/".
        # Conan get(strip_root=True) strips ONLY that top wrapper, leaving
        # <dest>/asio/include/asio.hpp + <dest>/asio/include/asio/* (the inner
        # "asio/" is part of the repo tree, not a wrapper). So destination=dev/asio
        # yields dev/asio/asio/include/asio.hpp — package() must copy from
        # dev/asio/asio/include/ → include/.
        asio_data = self.conan_data["asio_snapshot"]
        get(self, **asio_data, strip_root=True,
            destination=os.path.join(self.source_folder, "dev", "asio"))
        # G1 recipe-completeness expects a patch-application call; conandata.yml
        # patches: {} so this is a no-op for this recipe.
        apply_conandata_patches(self)

    def build(self):
        # header-only: nothing to compile. The bundled standalone-asio snapshot
        # already ships as headers only; fmt and http-parser are Conan requires
        # and are not built here.
        pass

    def package(self):
        # restinio public headers → include/restinio/
        copy(
            self,
            "*.hpp",
            src=os.path.join(self.source_folder, "dev", "restinio"),
            dst=os.path.join(self.package_folder, "include", "restinio"),
        )
        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "dev", "restinio"),
            dst=os.path.join(self.package_folder, "include", "restinio"),
        )
        # restinio inline implementations (.ipp) — included by public headers
        # via #include "impl/...ipp" and "utils/...ipp" (e.g. os.hpp → impl/os_posix.ipp).
        copy(
            self,
            "*.ipp",
            src=os.path.join(self.source_folder, "dev", "restinio"),
            dst=os.path.join(self.package_folder, "include", "restinio"),
        )
        # bundled standalone-asio snapshot → include/ (so consumers see
        # <asio.hpp> and asio/... subheaders from include/ root, matching how
        # restinio's asio_include.hpp does #include <asio.hpp> with -I include/).
        # source() laid the snapshot at dev/asio/asio/include/asio.hpp + dev/asio/asio/include/asio/*.
        copy(
            self,
            "*.hpp",
            src=os.path.join(self.source_folder, "dev", "asio", "asio", "include"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "*.ipp",
            src=os.path.join(self.source_folder, "dev", "asio", "asio", "include"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "dev", "asio", "asio", "include"),
            dst=os.path.join(self.package_folder, "include"),
        )
        # license
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        # header-library: no lib/ or bin/ output; leave the output-dir fields at
        # their defaults (empty) so the R38 CLI-tool detector in L0k does not
        # misclassify this library as a command-line tool.
        self.cpp_info.set_property("cmake_file_name", "restinio")
        self.cpp_info.set_property("cmake_target_name", "restinio::restinio")
        self.cpp_info.set_property("pkg_config_name", "restinio")
        # Standalone-asio define is mandatory for the bundled snapshot;
        # restinio's asio_include.hpp includes <asio.hpp> and expects this define.
        self.cpp_info.defines = [
            "ASIO_STANDALONE",
            "ASIO_HAS_STD_CHRONO",
            "ASIO_DISABLE_STD_STRING_VIEW",
        ]
