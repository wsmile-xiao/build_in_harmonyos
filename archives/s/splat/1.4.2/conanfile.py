#!/usr/bin/env python3
"""Conan recipe for SPLAT! 1.4.2."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.layout import basic_layout


class SplatConan(ConanFile):
    name = "splat"
    version = "1.4.2"
    description = "RF signal propagation, loss, and terrain analysis tools"
    license = "GPL-2.0-or-later"
    homepage = "https://www.qsl.net/kd2bd/splat.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("bzip2/1.0.8")
        self.requires("zlib/1.3.1")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"SPLAT! supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _compiler(self, language):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = executables.get(language)
        if not compiler:
            raise ConanInvalidConfiguration(
                f"profile must set tools.build:compiler_executables:{language}"
            )
        return compiler

    @staticmethod
    def _quote(value):
        return shlex.quote(str(value))

    def _dependency_flags(self):
        includes = []
        libdirs = []
        libraries = []
        for name in ("bzip2", "zlib"):
            info = self.dependencies[name].cpp_info
            includes.extend(f"-I{path}" for path in info.includedirs)
            libdirs.extend(f"-L{path}" for path in info.libdirs)
            libraries.extend(f"-l{lib}" for lib in info.libs)
            libraries.extend(f"-l{lib}" for lib in info.system_libs)
        return includes, libdirs, libraries

    def _run_compile(self, compiler, output, sources, extra_libraries=None):
        includes, libdirs, libraries = self._dependency_flags()
        cflags = ["-O2", "-fPIE"] + includes
        ldflags = ["-Wl,-z,relro,-z,now", "-pie"] + libdirs
        command = [compiler] + cflags + sources + ldflags
        command += extra_libraries or []
        command += ["-o", output]
        self.run(" ".join(self._quote(item) for item in command), cwd=self.source_folder,
                 env="conanbuild")

    def build(self):
        cxx = self._compiler("cpp")
        cc = self._compiler("c")
        save(
            self,
            os.path.join(self.source_folder, "splat.h"),
            "#define MAXPAGES 4\n#define HD_MODE 0\n",
        )
        self._run_compile(cxx, "splat", ["itwom3.0.cpp", "splat.cpp"], ["-lm", "-lbz2"])
        save(
            self,
            os.path.join(self.source_folder, "splat.h"),
            "#define MAXPAGES 4\n#define HD_MODE 1\n",
        )
        self._run_compile(
            cxx, "splat-hd", ["itwom3.0.cpp", "splat.cpp"], ["-lm", "-lbz2"]
        )
        utilities = os.path.join(self.source_folder, "utils")
        builds = (
            ("citydecoder", "citydecoder.c", []),
            ("usgs2sdf", "usgs2sdf.c", []),
            ("srtm2sdf", "srtm2sdf.c", ["-lbz2"]),
            ("fontdata", "fontdata.c", ["-lz"]),
            ("bearing", "bearing.c", ["-lm"]),
        )
        for output, source, libs in builds:
            self._run_compile(
                cc,
                os.path.join("utils", output),
                [os.path.join("utils", source)],
                libs,
            )

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        for executable in ("splat", "splat-hd"):
            copy(self, executable, self.source_folder, bindir, keep_path=False)
        for executable in ("citydecoder", "usgs2sdf", "srtm2sdf", "fontdata", "bearing"):
            copy(self, executable, os.path.join(self.source_folder, "utils"), bindir,
                 keep_path=False)
        source_srtm = os.path.join(bindir, "srtm2sdf")
        if os.path.isfile(source_srtm):
            with open(source_srtm, "rb") as src, open(os.path.join(bindir, "srtm2sdf-hd"), "wb") as dst:
                dst.write(src.read())
        for executable in os.listdir(bindir):
            os.chmod(os.path.join(bindir, executable), 0o755)
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "splat.1", os.path.join(self.source_folder, "docs", "english", "man"),
             os.path.join(self.package_folder, "share", "man", "man1"), keep_path=False)
        copy(self, "*", os.path.join(self.source_folder, "sample_data"),
             os.path.join(self.package_folder, "share", "splat", "sample_data"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        bindir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.prepend_path("PATH", bindir)
        self.runenv_info.prepend_path("PATH", bindir)
