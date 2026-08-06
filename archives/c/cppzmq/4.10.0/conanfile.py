#!/usr/bin/env python3
"""Conan recipe for cppzmq 4.10.0 — header-only C++ binding for ZeroMQ."""
import os
import textwrap

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.files import copy, get, save, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class CppzmqConan(ConanFile):
    name = "cppzmq"
    version = "4.10.0"
    description = "Header-only C++ binding for ZeroMQ (0MQ)"
    license = "MIT"
    homepage = "https://github.com/zeromq/cppzmq"
    url = "https://github.com/zeromq/cppzmq"

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("zeromq/4.3.5")

    def package_id(self):
        self.info.clear()

    def validate(self):
        if self.settings.compiler.cppstd:
            check_min_cppstd(self, "11")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "zmq*.hpp", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))

        self._create_cmake_module_alias_targets(
            os.path.join(self.package_folder, self._module_file_rel_path),
            {
                "cppzmq": "cppzmq::cppzmq",
                "cppzmq-static": "cppzmq::cppzmq",
            }
        )

    def _create_cmake_module_alias_targets(self, module_file, targets):
        content = ""
        for alias, aliased in targets.items():
            content += textwrap.dedent(f"""\
                if(TARGET {aliased} AND NOT TARGET {alias})
                    add_library({alias} INTERFACE IMPORTED)
                    set_property(TARGET {alias} PROPERTY INTERFACE_LINK_LIBRARIES {aliased})
                endif()
            """)
        save(self, module_file, content)

    @property
    def _module_file_rel_path(self):
        return os.path.join("lib", "cmake", f"conan-official-{self.name}-targets.cmake")

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "cppzmq")
        self.cpp_info.set_property("cmake_target_name", "cppzmq")
        self.cpp_info.set_property("cmake_target_aliases", ["cppzmq-static"])
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
