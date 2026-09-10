#!/usr/bin/env python3
"""Conan recipe for covtobed 1.3.5."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class CovtobedConan(ConanFile):
    name = "covtobed"
    version = "1.3.5"
    description = "Generate BED coverage tracks from sorted BAM alignment files"
    license = "MIT"
    homepage = "https://github.com/telatin/covtobed"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("bioinformatics", "bam", "bed", "coverage")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("bamtools/2.5.3")
        self.requires("zlib/1.3.1.1")

    def build_requirements(self):
        # The final upstream test uses Perl. The host Perl is enough for local
        # native validation; HarmonyOS workers consume the published OHOS tool.
        if str(self.settings.os) == "OHOS":
            self.tool_requires("perl/5.42.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = executables.get("cpp")
        if not cxx:
            raise ConanException(
                "tools.build:compiler_executables must define the cpp compiler"
            )
        if not os.path.isfile(cxx):
            raise ConanException(f"Conan C++ compiler not found: {cxx}")
        return cxx

    @staticmethod
    def _dependency_flags(dependency):
        info = dependency.cpp_info.aggregated_components()
        compile_flags = [f"-I{path}" for path in info.includedirs]
        compile_flags.extend(f"-D{define}" for define in info.defines)
        link_flags = [f"-L{path}" for path in info.libdirs]
        link_flags.extend(f"-l{library}" for library in info.libs)
        link_flags.extend(f"-l{library}" for library in info.system_libs)
        return compile_flags, link_flags

    def build(self):
        apply_conandata_patches(self)

        cxx = self._compiler()
        sources = [
            os.path.join(self.source_folder, "base.cpp"),
            os.path.join(self.source_folder, "OptionParser.cpp"),
        ]
        output = os.path.join(self.source_folder, "covtobed")
        flags = ["-std=c++11", "-O2", "-DNDEBUG"]
        if str(self.settings.compiler.libcxx) == "libc++":
            flags.append("-stdlib=libc++")
        bamtools_compile, bamtools_link = self._dependency_flags(
            self.dependencies["bamtools"]
        )
        zlib_compile, zlib_link = self._dependency_flags(self.dependencies["zlib"])
        flags.extend(bamtools_compile)
        flags.extend(zlib_compile)

        # Keep static libraries after the translation units for ELF linkers.
        command = [
            cxx,
            *flags,
            *sources,
            *bamtools_link,
            *zlib_link,
            "-o",
            output,
        ]
        quoted_command = " ".join(shlex.quote(item) for item in command)
        self.run(quoted_command, env="conanbuild")

        if str(self.settings.os) == "OHOS":
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        else:
            bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "bash"
        self.run(
            f"{shlex.quote(bash)} test/test.sh",
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package(self):
        copy(
            self,
            "covtobed",
            self.source_folder,
            os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "LICENSE",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
