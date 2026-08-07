#!/usr/bin/env python3
"""Conan recipe for ADMesh 0.98.5."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import copy, get, save
from conan.tools.layout import basic_layout


class AdmeshConan(ConanFile):
    name = "admesh"
    version = "0.98.5"
    description = "C library and CLI for processing triangulated solid meshes"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/admesh/admesh"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} is not supported")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _tools(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = executables.get("c")
        if not compiler:
            if cross_building(self):
                raise ConanInvalidConfiguration(
                    "cross builds require tools.build:compiler_executables[c]"
                )
            compiler = "cc"
        compiler_dir = os.path.dirname(compiler)
        ar_name = "llvm-ar.exe" if os.name == "nt" else "llvm-ar"
        archiver = os.path.join(compiler_dir, ar_name) if compiler_dir else "ar"
        if not os.path.isfile(archiver):
            archiver = "ar"
        return compiler, archiver

    def _conf_flags(self, name):
        values = self.conf.get(name, default=[], check_type=list)
        return " ".join(str(value) for value in values)

    def build(self):
        compiler, archiver = self._tools()
        save(
            self,
            os.path.join(self.build_folder, "config.h"),
            '#define VERSION "0.98.5"\n',
        )
        build_flags = {
            "Debug": "-O0 -g",
            "Release": "-O2 -DNDEBUG",
            "RelWithDebInfo": "-O2 -g -DNDEBUG",
            "MinSizeRel": "-Os -DNDEBUG",
        }
        build_type_flags = build_flags.get(str(self.settings.build_type), "")
        common = (
            '-std=gnu99 -Wall -Wextra -fPIC -DVERSION=\\"0.98.5\\" '
            f'{build_type_flags} '
            f'{self._conf_flags("tools.build:cflags")} '
            f'-I"{self.build_folder}" '
            f'-I"{os.path.join(self.source_folder, "src")}"'
        )
        object_files = []
        for source_name in (
            "connect.c",
            "normals.c",
            "shared.c",
            "stlinit.c",
            "stl_io.c",
            "util.c",
        ):
            source = os.path.join(self.source_folder, "src", source_name)
            obj = os.path.join(self.build_folder, source_name + ".o")
            self.run(f'"{compiler}" {common} -c "{source}" -o "{obj}"', env=["conanbuild"])
            object_files.append(obj)

        library = os.path.join(self.build_folder, "libadmesh.a")
        quoted_objects = " ".join(f'"{path}"' for path in object_files)
        self.run(f'"{archiver}" rcs "{library}" {quoted_objects}', env=["conanbuild"])

        cli_source = os.path.join(self.source_folder, "src", "admesh.c")
        cli = os.path.join(self.build_folder, "admesh")
        self.run(
            f'"{compiler}" {common} -fPIE "{cli_source}" "{library}" '
            f'{self._conf_flags("tools.build:exelinkflags")} -lm -o "{cli}"',
            env=["conanbuild"],
        )

    def package(self):
        copy(self, "COPYING", self.source_folder, os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "stl.h", os.path.join(self.source_folder, "src"), os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "libadmesh.a", self.build_folder, os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "admesh", self.build_folder, os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "admesh.1", self.source_folder, os.path.join(self.package_folder, "share", "man", "man1"), keep_path=False)
        if os.name != "nt":
            os.chmod(os.path.join(self.package_folder, "bin", "admesh"), 0o755)

    def package_info(self):
        self.cpp_info.libs = ["admesh"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "admesh")
        self.cpp_info.set_property("cmake_target_name", "admesh::admesh")
        self.cpp_info.set_property("pkg_config_name", "admesh")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
