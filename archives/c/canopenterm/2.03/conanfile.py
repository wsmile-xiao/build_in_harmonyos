#!/usr/bin/env python3
"""Conan recipe for canopenterm 2.03 — CMake project (C).

CANopenTerm is a versatile software tool to analyse and configure CANopen
devices (terminal UI on SDL3).

OHOS adaptation (see patches/canopenterm-2.03/0001-0006):
- CMake sets OHOS when CMAKE_SYSTEM_NAME matches HarmonyOS/OpenHarmony and
  reuses the upstream "linux" (POSIX/SDL) platform sources (the OHOS profile
  sets CMAKE_SYSTEM_NAME=HarmonyOS, so CMake's UNIX is OFF).
- the Windows-only icon.rc resource is omitted on OHOS.
- the upstream ExternalProject dep builds (cJSON / CANvenient / pocketpy /
  inih / isocline / Lua / SDL3 / cmocka) receive the OHOS CMake toolchain
  file so all 8 bundled deps cross-compile for aarch64 musl.
- readline/history are not available on OHOS; isocline provides its own line
  editor (ic_readline), so they are only linked on Linux.
- SDL3, CANvenient and cmocka sources receive their OHOS patches through the
  ExternalProject PATCH_COMMAND scripts (patches/sdl3-3.4.12,
  patches/canvenient-1.02, patches/cmocka-1.1.7).
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, copy
import os


class CanopentermConan(ConanFile):
    name = "canopenterm"
    version = "2.03"
    description = "Versatile software tool to analyse and configure CANopen devices"
    license = "MIT"
    homepage = "https://github.com/CANopenTerm/CANopenTerm"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # dep source patches (patches/canvenient-1.02, patches/sdl3-3.4.12,
        # patches/cmocka-1.1.7) are applied at build time by the
        # ExternalProject PATCH_COMMAND scripts (cmake/patch_*.cmake), which
        # reference <source_root>/patches/ — ship the whole tree into the
        # source root (export_sources_folder is mirrored onto the source folder).
        copy(self, "*", src=os.path.join(self.recipe_folder, "patches"), dst=os.path.join(self.export_sources_folder, "patches"))

    def requirements(self):
        # No conan registry deps: the upstream CMake build fetches its 8
        # bundled dependencies (cJSON, CANvenient, pocketpy, inih, isocline,
        # Lua, SDL3, cmocka) itself via ExternalProject and cross-compiles
        # them with the OHOS toolchain (see patches 0003/0004/0005/0006).
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        from conan.tools.files import get
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTS"] = "ON"
        # The upstream CMake does not emit RUNPATH: pass the rpath straight to
        # the linker (CMAKE_EXE_LINKER_FLAGS) so the packaged executables
        # resolve the shared deps (libCANvenient/libcjson/libSDL3) relative to
        # their own location (bin/ + lib/ package layout).
        # NOTE: do NOT fix the ELF after linking with patchelf — the OHOS
        # kernel refuses to exec patchelf-modified binaries (EPERM).
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,-rpath,'$ORIGIN/../lib'"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        export_dir = os.path.join(self.source_folder, "export")
        deps = os.path.join(self.source_folder, "deps_linux")
        # executables (upstream builds them into <source>/export)
        copy(self, "CANopenTerm", src=export_dir, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "codb2json", src=export_dir, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "run_unit_tests", src=export_dir, dst=os.path.join(self.package_folder, "bin"))
        # shared runtime deps (built by the upstream ExternalProject step)
        copy(self, "libCANvenient.so", src=os.path.join(deps, "CANvenient-1.02_build"), dst=os.path.join(self.package_folder, "lib"))
        copy(self, "libcjson.so", src=os.path.join(deps, "CJSON-1.7.19_build"), dst=os.path.join(self.package_folder, "lib"))
        copy(self, "libSDL3.so", src=os.path.join(deps, "SDL3-3.4.12_build"), dst=os.path.join(self.package_folder, "lib"))
        # runtime data shipped upstream (codb/dbc/eds definitions + scripts)
        for d in ("codb", "dbc", "eds", "scripts", "tests"):
            copy(self, "*", src=os.path.join(export_dir, d), dst=os.path.join(self.package_folder, "share", "canopenterm", d))
        copy(self, "LICENSE.md", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.resdirs = ["share"]
