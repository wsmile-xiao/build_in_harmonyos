#!/usr/bin/env python3
"""Conan recipe for SPIRV-Headers vulkan-sdk-1.3.290.0."""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    load,
    save,
)


class SpirvHeadersConan(ConanFile):
    name = "spirv-headers"
    version = "vulkan-sdk-1.3.290.0"
    description = "Machine-readable SPIR-V headers and JSON grammar files"
    license = "MIT"
    homepage = "https://github.com/KhronosGroup/SPIRV-Headers"
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD", "Macos", "Windows"):
            raise ConanInvalidConfiguration(
                "spirv-headers supports Linux/OHOS/FreeBSD/Macos/Windows; current OS: {}".format(
                    self.settings.os
                )
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def build(self):
        apply_conandata_patches(self)
        install_prefix = os.path.join(self.build_folder, "upstream-install")
        root_build = self._root_build_folder()
        self._cmake_configure(
            self.source_folder,
            root_build,
            [
                "-DSPIRV_HEADERS_ENABLE_TESTS=ON",
                "-DSPIRV_HEADERS_ENABLE_INSTALL=ON",
                '-DCMAKE_INSTALL_INCLUDEDIR="include"',
                '-DCMAKE_INSTALL_DATADIR="share"',
                f'-DCMAKE_INSTALL_PREFIX="{install_prefix}"',
            ],
        )
        self.run(f'cmake --build "{root_build}"')
        self.run(f'cmake --install "{root_build}"')

        self._build_upstream_consumer(
            "find_package", install_prefix, "upstream-find-package"
        )
        self._build_upstream_consumer(
            "pkg_config", install_prefix, "upstream-pkg-config"
        )

        absolute_prefix = os.path.join(
            self.build_folder, "upstream-install-absolute"
        )
        absolute_build = os.path.join(
            self.build_folder, "upstream-absolute-install"
        )
        self._cmake_configure(
            self.source_folder,
            absolute_build,
            [
                "-DSPIRV_HEADERS_ENABLE_TESTS=OFF",
                "-DSPIRV_HEADERS_ENABLE_INSTALL=ON",
                f'-DCMAKE_INSTALL_PREFIX="{absolute_prefix}"',
                f'-DCMAKE_INSTALL_INCLUDEDIR="{os.path.join(absolute_prefix, "include")}"',
                '-DCMAKE_INSTALL_DATADIR="share"',
            ],
        )
        self.run(f'cmake --install "{absolute_build}"')
        self._build_upstream_consumer(
            "pkg_config", absolute_prefix, "upstream-pkg-config-absolute"
        )

    def package(self):
        self.run(
            'cmake --install "{}" --prefix "{}"'.format(
                self._root_build_folder(), self.package_folder
            )
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        self._make_pkg_config_relocatable()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "SPIRV-Headers")
        self.cpp_info.set_property(
            "cmake_target_name", "SPIRV-Headers::SPIRV-Headers"
        )
        self.cpp_info.set_property("pkg_config_name", "SPIRV-Headers")

    def package_id(self):
        self.info.clear()

    def _root_build_folder(self):
        return os.path.join(self.build_folder, "upstream-add-subdirectory")

    def _cmake_configure(self, source_folder, build_folder, definitions):
        args = [
            f'-S "{source_folder}"',
            f'-B "{build_folder}"',
            f"-DCMAKE_BUILD_TYPE={self.settings.build_type}",
        ]
        generator = self.conf.get(
            "tools.cmake.cmaketoolchain:generator", default=None
        )
        if generator:
            args.extend(["-G", f'"{generator}"'])
        if str(self.settings.os) == "OHOS":
            ohos_arch = {
                "armv8": "arm64-v8a",
                "armv7": "armeabi-v7a",
                "x86_64": "x86_64",
            }.get(str(self.settings.arch))
            if not ohos_arch:
                raise ConanInvalidConfiguration(
                    f"Unsupported OHOS architecture: {self.settings.arch}"
                )
            compilers = self.conf.get(
                "tools.build:compiler_executables",
                default={},
                check_type=dict,
            ) or {}
            c_compiler = compilers.get("c")
            compiler_bin = os.path.dirname(c_compiler) if c_compiler else ""
            cmake_ar = compilers.get("ar")
            cmake_ranlib = compilers.get("ranlib")
            if not cmake_ar and compiler_bin:
                cmake_ar = os.path.join(compiler_bin, "llvm-ar")
            if not cmake_ranlib and compiler_bin:
                cmake_ranlib = os.path.join(compiler_bin, "llvm-ranlib")
            if not cmake_ar or not cmake_ranlib:
                raise ConanInvalidConfiguration(
                    "OHOS build requires tools.build:compiler_executables to "
                    "provide ar/ranlib, or an absolute c compiler path that "
                    "allows llvm-ar/llvm-ranlib to be inferred"
                )
            args.extend(
                [
                    f'-DCMAKE_TOOLCHAIN_FILE="{self._ohos_toolchain()}"',
                    f"-DOHOS_ARCH={ohos_arch}",
                    f'-DCMAKE_AR="{cmake_ar}"',
                    f'-DCMAKE_RANLIB="{cmake_ranlib}"',
                ]
            )
        args.extend(definitions)
        self.run("cmake " + " ".join(args))

    def _build_upstream_consumer(self, test_name, prefix, build_name):
        source_folder = os.path.join(self.source_folder, "tests", test_name)
        build_folder = os.path.join(self.build_folder, build_name)
        definitions = [
            f'-DCMAKE_PREFIX_PATH="{prefix}"',
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
        ]
        environment = None
        if test_name == "find_package":
            definitions.append(
                '-DSPIRV-Headers_DIR="{}"'.format(
                    os.path.join(prefix, "share", "cmake", "SPIRV-Headers")
                )
            )
        elif test_name == "pkg_config":
            definitions.append("-DPKG_CONFIG_USE_CMAKE_PREFIX_PATH=ON")
            environment = Environment()
            environment.define_path(
                "PKG_CONFIG_PATH", os.path.join(prefix, "share", "pkgconfig")
            )

        if environment is None:
            self._cmake_configure(source_folder, build_folder, definitions)
        else:
            with environment.vars(self).apply():
                self._cmake_configure(source_folder, build_folder, definitions)
        self.run(f'cmake --build "{build_folder}"')

    def _ohos_toolchain(self):
        configured = self.conf.get(
            "tools.cmake.cmaketoolchain:user_toolchain",
            default=[],
            check_type=list,
        )
        ndk_home = os.environ.get("OHOS_NDK_HOME", "")
        candidates = list(configured)
        if ndk_home:
            candidates.append(
                os.path.join(ndk_home, "build", "cmake", "ohos.toolchain.cmake")
            )
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        matches = sorted(
            glob.glob(
                "/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"
            )
        )
        if matches:
            return matches[-1]
        raise ConanInvalidConfiguration(
            "OHOS CMake toolchain not found; set OHOS_NDK_HOME or the Conan user_toolchain conf"
        )

    def _make_pkg_config_relocatable(self):
        pc_file = os.path.join(
            self.package_folder, "share", "pkgconfig", "SPIRV-Headers.pc"
        )
        if not os.path.isfile(pc_file):
            raise ConanException("upstream install did not produce SPIRV-Headers.pc")
        lines = load(self, pc_file).splitlines()
        include_lines = [
            index for index, line in enumerate(lines) if line.startswith("includedir=")
        ]
        if len(include_lines) != 1:
            raise ConanException("SPIRV-Headers.pc must define includedir exactly once")
        lines[include_lines[0]] = "includedir=${pcfiledir}/../../include"
        save(self, pc_file, "\n".join(lines) + "\n")
