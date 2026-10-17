#!/usr/bin/env python3
"""Conan recipe for pngtools 1.2 on HarmonyOS PC."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualRunEnv
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PngtoolsConan(ConanFile):
    name = "pngtools"
    version = "1.2"
    description = "Command-line tools for inspecting and manipulating PNG files"
    license = "GPL-2.0-only"
    homepage = "https://github.com/mikalstill/pngtools"
    url = "https://github.com/mikalstill/pngtools"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # The standalone suite runner and its tiny stdlib compatibility layer are
    # exported with the recipe so build() can run the upstream tests without
    # requiring pip packages on the CI worker.
    exports_sources = (
        "test_package/generate_test_images.py",
        "test_package/run_upstream_tests.py",
        "test_package/shim/*",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libpng/1.6.58.2")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pngtools supports Linux and OHOS only, got %s"
                % self.settings.os
            )

    def layout(self):
        basic_layout(self)

    def generate(self):
        VirtualRunEnv(self).generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _quote(self, value):
        if os.name == "nt":
            return '"' + str(value).replace('"', '\\"') + '"'
        return shlex.quote(str(value))

    def _compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return str(executables.get("c") or "cc")

    def _dependency_flags(self):
        include_dirs = []
        library_dirs = []
        libraries = []
        system_libraries = []
        for name in ("libpng", "zlib"):
            if name not in self.dependencies:
                continue
            cpp_info = self.dependencies[name].cpp_info
            include_dirs.extend(cpp_info.includedirs)
            library_dirs.extend(cpp_info.libdirs)
            libraries.extend(cpp_info.libs)
            system_libraries.extend(cpp_info.system_libs)

        include_flags = ["-I" + str(path) for path in include_dirs]
        link_flags = ["-L" + str(path) for path in library_dirs]
        link_flags.extend("-l" + str(library) for library in libraries)
        link_flags.extend("-l" + str(library) for library in system_libraries)
        return include_flags, link_flags

    def _target_flags(self):
        flags = [
            str(flag)
            for flag in self.conf.get(
                "tools.build:cflags", default=[], check_type=list
            )
        ]
        return flags

    def _compile(self, output_name, sources, libraries=()):
        include_flags, link_flags = self._dependency_flags()
        command = [
            self._compiler(),
            "-std=c11",
            "-D_GNU_SOURCE",
            "-O2",
            "-Wall",
            "-Wextra",
            "-Werror",
        ]
        command.extend(self._target_flags())
        command.extend(include_flags)
        command.extend(sources)
        command.extend(["-o", output_name])
        command.extend(link_flags)
        command.extend(libraries)
        command.extend(
            str(flag)
            for flag in self.conf.get(
                "tools.build:exelinkflags", default=[], check_type=list
            )
        )
        self.run(
            " ".join(self._quote(item) for item in command),
            cwd=self.build_folder,
        )

    def build(self):
        source = self.source_folder
        self._compile(
            "pnginfo",
            [os.path.join(source, "pnginfo.c")],
            ["-lm"],
        )
        self._compile(
            "pngchunks",
            [os.path.join(source, "pngchunks.c")],
        )
        self._compile(
            "pngchunkdesc",
            [os.path.join(source, "pngchunkdesc.c")],
        )
        self._compile(
            "pngcp",
            [
                os.path.join(source, "pngcp.c"),
                os.path.join(source, "pngread.c"),
                os.path.join(source, "pngwrite.c"),
                os.path.join(source, "inflateraster.c"),
            ],
            ["-lm"],
        )

        runner = os.path.join(
            self.source_folder, "test_package", "run_upstream_tests.py"
        )
        self.run(
            'python3 "%s" --source "%s" --build-dir "%s"'
            % (runner, self.source_folder, self.build_folder),
            env="conanrun",
        )

    def package(self):
        for name in ("pnginfo", "pngchunks", "pngchunkdesc", "pngcp"):
            copy(
                self,
                name,
                self.build_folder,
                os.path.join(self.package_folder, "bin"),
            )

        copy(
            self,
            "COPYING",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "README.md",
            self.source_folder,
            os.path.join(self.package_folder, "share", "doc", "pngtools"),
        )

        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if os.path.exists(sign_tool) and os.path.exists(objcopy):
            for name in ("pnginfo", "pngchunks", "pngchunkdesc", "pngcp"):
                binary = os.path.join(self.package_folder, "bin", name)
                signed = binary + ".signed"
                self.run(
                    '%s --remove-section .codesign "%s"'
                    % (objcopy, binary),
                    quiet=True,
                )
                self.run(
                    '%s sign -inFile "%s" -outFile "%s" -selfSign 1'
                    % (sign_tool, binary, signed),
                    quiet=True,
                )
                os.replace(signed, binary)
                os.chmod(binary, 0o755)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
