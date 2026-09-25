#!/usr/bin/env python3
"""Conan recipe — kicad-library-symbols 10.0.5 (pure data package).

KiCad official schematic symbol libraries: 223 ``*.kicad_symdir``
directories (one file per symbol), a global ``sym-lib-table`` and a SPICE
simulation model (``Simulation_SPICE.sp``). No C/C++ sources exist and the
upstream CMake project is declared ``project(kicad-symbols NONE)``.

Build step mirrors upstream behavior:
  - ``KICAD_PACK_SYM_LIBRARIES=ON`` (upstream default): packs every symdir
    into a single-file ``.kicad_sym`` library at build time with the bundled
    pure-stdlib Python script ``tools/kicad_lib_pack.py`` (requires a
    Python3 interpreter on PATH).
  - ``KICAD_PACK_SYM_LIBRARIES=OFF`` fallback: installs the unpacked
    ``.kicad_symdir`` directory trees unchanged.

Install layout follows the upstream default ``KICAD_DATA=share/kicad``:
symbol libraries under ``share/kicad/symbols`` and the global table under
``share/kicad/template/sym-lib-table``.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class KicadLibrarySymbolsConan(ConanFile):
    name = "kicad-library-symbols"
    version = "10.0.5"
    description = "KiCad official schematic symbol libraries (pure data package)"
    license = "CC-BY-SA-4.0"
    homepage = "https://gitlab.com/kicad/libraries/kicad-symbols"
    url = "https://gitlab.com/kicad/libraries/kicad-symbols"
    topics = ("kicad", "eda", "schematic", "symbols", "data")
    # No package_type: the payload is pure data — no binaries (not an
    # "application"), no libraries/headers (not a library variant).

    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: recipe supports Linux and OHOS targets only. The payload is
        # platform-independent data, but keep the guard explicit.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"kicad-library-symbols does not support os={self.settings.os}")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        # CMake has no OHOS platform module.  The package is built natively
        # on OHOS with clang and the upstream project() is declared NONE
        # (no compiler/platform checks), but keep the explicit platform
        # match consistent with the other archives/ recipes.
        if self.settings.os in ("Linux", "OHOS"):
            toolchain.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            toolchain.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8" else str(self.settings.arch)
            )
        toolchain.generate()

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="kicad-symbols-10.0.5.tar.gz",
            strip_root=True,
        )

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # Upstream default: pack .kicad_symdir trees into .kicad_sym files at
        # build time. Needs Python3 on PATH (supplied by the CI profile
        # buildenv). Fallback documented in notes.md: set OFF to install the
        # unpacked directory trees instead.
        cmake.configure(variables={"KICAD_PACK_SYM_LIBRARIES": True})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream CMake does not install the license; ship it explicitly.
        copy(self, "LICENSE.md",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_id(self):
        # Architecture-independent data payload.
        self.info.clear()

    def package_info(self):
        # Data-only package: no headers, libraries, or binaries to link.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share/kicad"]
        self.cpp_info.set_property("cmake_file_name", "kicad-library-symbols")
        self.cpp_info.set_property(
            "cmake_target_name", "kicad-library-symbols::kicad-library-symbols"
        )
        self.cpp_info.set_property("pkg_config_name", "kicad-library-symbols")
