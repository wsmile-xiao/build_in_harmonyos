#!/usr/bin/env python3
"""Conan recipe for the libxml2 command-line utilities."""

import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class Libxml2UtilsConan(ConanFile):
    name = "libxml2-utils"
    version = "2.15.3"
    description = "libxml2 XML command-line utilities (xmllint and xmlcatalog)"
    license = "MIT"
    homepage = "https://gitlab.gnome.org/GNOME/libxml2"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {"with_zlib": [True, False]}
    default_options = {"with_zlib": True}
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("libxml2-utils OHOS builds require armv8")

    def requirements(self):
        if self.options.with_zlib:
            self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ohos_toolchain(self):
        candidates = []
        user_toolchain = self.conf.get(
            "tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list
        )
        candidates.extend(user_toolchain)
        for env_name in ("OHOS_NDK_HOME", "OHOS_SDK_HOME", "OHOS_SDK_ROOT", "DEVECO_SDK_HOME"):
            sdk_root = os.environ.get(env_name, "").strip()
            if sdk_root:
                candidates.extend([
                    os.path.join(sdk_root, "build", "cmake", "ohos.toolchain.cmake"),
                    os.path.join(sdk_root, "ohos", "native", "build", "cmake", "ohos.toolchain.cmake"),
                ])

        # CI profiles may expose only the SDK LLVM runtime path.  Reconstruct
        # the adjacent native SDK root without assuming a worker-specific path.
        for library_dir in os.environ.get("LD_LIBRARY_PATH", "").split(os.pathsep):
            library_dir = library_dir.strip()
            if library_dir.startswith("+(path)"):
                library_dir = library_dir[len("+(path)"):]
            library_dir = os.path.normpath(library_dir)
            if os.path.basename(library_dir) == "lib" and os.path.basename(
                os.path.dirname(library_dir)
            ) == "llvm":
                native_root = os.path.dirname(os.path.dirname(library_dir))
                candidates.append(
                    os.path.join(native_root, "build", "cmake", "ohos.toolchain.cmake")
                )

        # Standard OHOS CI workers publish the SDK under this stable HNP root;
        # keep the glob narrow and independent of the installed SDK version.
        candidates.extend(sorted(glob.glob(
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"
        )))

        for program_files in (
            os.environ.get("ProgramFiles", ""),
            os.environ.get("ProgramW6432", ""),
            os.environ.get("ProgramFiles(x86)", ""),
        ):
            if program_files:
                candidates.append(
                    os.path.join(
                        program_files,
                        "Huawei",
                        "DevEco Studio",
                        "sdk",
                        "default",
                        "openharmony",
                        "native",
                        "build",
                        "cmake",
                        "ohos.toolchain.cmake",
                    )
                )
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        raise ConanInvalidConfiguration("OHOS NDK toolchain file was not found")

    def _ohos_archive_finish(self, toolchain_file):
        """Use llvm-ar to finish archives when the SDK omits llvm-ranlib."""
        native_root = os.path.dirname(
            os.path.dirname(os.path.dirname(toolchain_file))
        )
        candidates = [
            os.path.join(native_root, "llvm", "bin", "llvm-ar"),
            os.path.join(native_root, "llvm", "bin", "llvm-ar.exe"),
        ]
        for candidate in candidates:
            if os.path.isfile(candidate):
                return '"{}" s <TARGET>'.format(candidate.replace("\\", "/"))
        return "llvm-ar s <TARGET>"

    def build(self):
        apply_conandata_patches(self)
        build_dir = os.path.join(self.build_folder, "build-ohos")
        toolchain_file = self._ohos_toolchain()
        defs = [
            "-G Ninja",
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain_file),
            '-DCMAKE_C_ARCHIVE_FINISH="{}"'.format(
                self._ohos_archive_finish(toolchain_file)
            ),
            '-DCMAKE_CXX_ARCHIVE_FINISH="{}"'.format(
                self._ohos_archive_finish(toolchain_file)
            ),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",
            "-DBUILD_SHARED_LIBS=OFF",
            "-DLIBXML2_WITH_PROGRAMS=ON",
            "-DLIBXML2_WITH_TESTS=OFF",
            "-DLIBXML2_WITH_DOCS=OFF",
            "-DLIBXML2_WITH_PYTHON=OFF",
            "-DLIBXML2_WITH_ICU=OFF",
            "-DLIBXML2_WITH_LZMA=OFF",
            "-DLIBXML2_WITH_ICONV=OFF",
            "-DLIBXML2_WITH_ZLIB={}".format("ON" if self.options.with_zlib else "OFF"),
        ]
        if self.options.with_zlib:
            zlib = self.dependencies["zlib"].package_folder
            zlib_inc = os.path.join(zlib, "include")
            zlib_candidates = []
            for pattern in ("libz.a", "zlib.lib", "libz.lib", "libz.so"):
                zlib_candidates.extend(glob.glob(os.path.join(zlib, "lib", pattern)))
            if not zlib_candidates:
                raise ConanInvalidConfiguration("zlib package has no linkable library")
            defs.extend([
                '-DZLIB_INCLUDE_DIR="{}"'.format(zlib_inc),
                '-DZLIB_LIBRARY="{}"'.format(zlib_candidates[0]),
            ])
        self.run('cmake -B "{}" -S "{}" {}'.format(build_dir, self.source_folder, " ".join(defs)))
        self.run('cmake --build "{}" --parallel 2'.format(build_dir))

    def package(self):
        build_dir = os.path.join(self.build_folder, "build-ohos")
        for executable in ("xmllint", "xmlcatalog"):
            matches = glob.glob(os.path.join(build_dir, "**", executable), recursive=True)
            matches += glob.glob(os.path.join(build_dir, "**", executable + ".exe"), recursive=True)
            matches = [path for path in matches if os.path.isfile(path)]
            if not matches:
                raise ConanInvalidConfiguration("built utility not found: " + executable)
            copy(self, os.path.basename(matches[0]), src=os.path.dirname(matches[0]),
                 dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
