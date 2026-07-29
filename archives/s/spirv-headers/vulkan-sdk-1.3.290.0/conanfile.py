#!/usr/bin/env python3
"""Conan recipe for SPIRV-Headers vulkan-sdk-1.3.290.0."""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
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
    description = "Machine-readable SPIR-V headers and grammar files"
    license = "MIT"
    homepage = "https://github.com/KhronosGroup/SPIRV-Headers"
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)

        cmake = CMake(self)
        cmake.configure(
            variables={
                "SPIRV_HEADERS_ENABLE_TESTS": True,
                "SPIRV_HEADERS_ENABLE_INSTALL": True,
                "CMAKE_INSTALL_PREFIX": self._staging_folder,
                "CMAKE_INSTALL_INCLUDEDIR": "include",
                "CMAKE_INSTALL_DATADIR": "share",
            }
        )
        cmake.build()
        self.run(
            'cmake --install "{}" --prefix "{}"'.format(
                self.build_folder, self._staging_folder
            )
        )

        self._build_upstream_consumer(
            "find_package",
            os.path.join(self.source_folder, "tests", "find_package"),
            "upstream-find-package",
        )
        self._build_upstream_consumer(
            "pkg_config",
            os.path.join(self.source_folder, "tests", "pkg_config"),
            "upstream-pkg-config",
        )

    def package(self):
        copy(self, "*", src=self._staging_folder, dst=self.package_folder)
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

    @property
    def _staging_folder(self):
        return os.path.join(self.build_folder, "upstream-install")

    def _build_upstream_consumer(self, test_name, source_folder, build_name):
        build_folder = os.path.join(self.build_folder, build_name)
        toolchain_file = os.path.join(
            self.generators_folder, "conan_toolchain.cmake"
        )
        args = [
            f'-S "{source_folder}"',
            f'-B "{build_folder}"',
            f'-DCMAKE_TOOLCHAIN_FILE="{toolchain_file}"',
            f'-DCMAKE_PREFIX_PATH="{self._staging_folder}"',
        ]
        environment = None

        if test_name == "find_package":
            args.append("-DCMAKE_POLICY_VERSION_MINIMUM=3.5")
            args.append(
                '-DSPIRV-Headers_DIR="{}"'.format(
                    os.path.join(
                        self._staging_folder,
                        "share",
                        "cmake",
                        "SPIRV-Headers",
                    )
                )
            )
        else:
            args.append("-DPKG_CONFIG_USE_CMAKE_PREFIX_PATH=ON")
            environment = Environment()
            environment.define_path(
                "PKG_CONFIG_PATH",
                os.path.join(self._staging_folder, "share", "pkgconfig"),
            )

        if environment is None:
            self.run("cmake " + " ".join(args))
        else:
            with environment.vars(self).apply():
                self.run("cmake " + " ".join(args))
        self.run(f'cmake --build "{build_folder}"')

    def _make_pkg_config_relocatable(self):
        pc_file = os.path.join(
            self.package_folder, "share", "pkgconfig", "SPIRV-Headers.pc"
        )
        if not os.path.isfile(pc_file):
            raise ConanException(
                "Upstream install did not create SPIRV-Headers.pc"
            )

        lines = load(self, pc_file).splitlines()
        include_lines = [
            index
            for index, line in enumerate(lines)
            if line.startswith("includedir=")
        ]
        if len(include_lines) != 1:
            raise ConanException(
                "SPIRV-Headers.pc must define includedir exactly once"
            )
        lines[include_lines[0]] = "includedir=${pcfiledir}/../../include"
        save(self, pc_file, "\n".join(lines) + "\n")
