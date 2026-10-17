#!/usr/bin/env python3
"""Conan recipe for libfishcamp 1.2.

libfishcamp is the Fishcamp Starfish camera driver library, shipped as a single
subproject inside the INDI 3rdparty monorepo. This recipe vendors the 3 source
files (fishcamp.c / fishcamp.h / fishcamp_common.h) plus the LGPL license
directly from the official v2.2.4 GitHub tag — the INDI framework is NOT needed
to build it (see patches/). The only real dependency is libusb-1.0.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import download, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout


class LibfishcampConan(ConanFile):
    name = "libfishcamp"
    version = "1.2"
    description = "Fishcamp Starfish camera driver library (INDI 3rdparty)"
    license = "LGPL-2.0-or-later"
    homepage = "https://github.com/indilib/indi-3rdparty"
    url = "https://github.com/indilib/indi-3rdparty"

    # This recipe replaces upstream's INDI-dependent CMakeLists.txt with a
    # minimal self-contained one. Use exports_sources (not exports) so the file
    # reaches the source folder. The patches/ directory is also exported here
    # (alongside the export_sources() method which exports conandata patches),
    # guaranteeing the dependency-drop patch travels with the recipe.
    exports_sources = "CMakeLists.txt", "patches"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # R32: OHOS platform compatibility — only Linux-family OSes are supported.
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libfishcamp is only supported on Linux/OHOS, not {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libusb-1.0 is the only real build/runtime dependency.
        self.requires("libusb/1.0.27")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # conandata lists individual official source files (no monorepo download).
        # These are plain .c/.h/.LIB files, NOT archives, so we use download()
        # rather than get() (get() always unzips and would raise BadZipFile).
        for src in self.conan_data["sources"]:
            download(self, src["url"], src["filename"], sha256=src["sha256"])
        # Our minimal libusb-only CMakeLists.txt is provided via exports_sources,
        # which Conan 2 places directly into the source folder (no upstream
        # CMakeLists.txt is downloaded, so there is nothing to overwrite).

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: build a static lib by default (shared libs managed by Conan).
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        # E002: OHOS mounts /tmp read-only, so clang's temp files fail there.
        # Use the HMBS task temp dir (/data/storage/el2/base/cache) which is
        # writable AND supports mkfifo (needed by make's parallel jobserver);
        # fall back to a build-folder subdir if it is unavailable.
        tmp = None
        for var in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR"):
            v = os.environ.get(var)
            if v and os.path.isdir(v):
                tmp = v
                break
        if tmp is None:
            tmp = os.path.join(self.build_folder, "tmp_hmbs")
            try:
                os.makedirs(tmp, exist_ok=True)
            except OSError:
                pass
        for var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[var] = tmp
        cmake = CMake(self)
        cmake.configure()
        # R: conan self.run() 输出流继承 → 编译器静默失败（无诊断）。
        # 每步绑定日志文件，避免输出经管道丢失；真实错误可查 build.log。
        # Force serial build: make's parallel jobserver triggers a silent clang
        # failure on this OHOS/clang-15 host, so build single-threaded.
        with open(os.path.join(self.build_folder, "build.log"), "w") as logf:
            cmake.build(build_tool_args=["-j1"], stdout=logf, stderr=logf)

    def package(self):
        cmake = CMake(self)
        with open(os.path.join(self.build_folder, "install.log"), "w") as logf:
            cmake.install(stdout=logf, stderr=logf)
        # LGPL license compliance.
        copy(self, "COPYING.LIB", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["fishcamp"]
        self.cpp_info.includedirs = ["include"]
        # Consumer-facing CMake names: CMakeDeps generates fishcampConfig.cmake
        # exposing the fishcamp::fishcamp imported target (the CMake project
        # target is named "fishcamp").
        self.cpp_info.set_property("cmake_file_name", "fishcamp")
        self.cpp_info.set_property("cmake_target_name", "fishcamp::fishcamp")
        # libusb is a transitive requirement for consumers. Reference it in the
        # repo-standard form (libusb::libusb) so CMakeDeps propagates the
        # libusb-1.0::libusb-1.0 imported target to consumers.
        self.cpp_info.requires = ["libusb::libusb"]
