#!/usr/bin/env python3
"""Conan recipe for Lighter 1.1.3.

Lighter corrects errors in and trims adapters from high-throughput sequencing
reads using a k-mer spectrum. Upstream builds a single ``lighter`` CLI from a
bare Makefile and links zlib (``File.h`` / ``Reads.h`` call gzopen/gzread for
gzipped FASTA/FASTQ input and output) plus pthreads.

Maintainer notes:
  * Upstream has NO install target and OHOS ships no coreutils ``install(1)``,
    so package() copies the artifact by hand (R16: still produced by
    ``conan create``, not hand-packaged).
  * R33: the compiler comes from ``tools.build:compiler_executables``; the
    Makefile hard-codes ``CXX = g++``, so we override it on the make line.
  * R9: ``make -j1`` (HMDFS).
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                           export_conandata_patches, get)
from conan.tools.layout import basic_layout


class LighterConan(ConanFile):
    name = "lighter"
    version = "1.1.3"
    description = ("K-mer spectrum based error correction and adapter "
                   "trimming tool for high-throughput sequencing reads")
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/mourisl/Lighter"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # Upstream File.h includes <zlib.h> and calls gzopen/gzread/gzwrite.
        self.requires("zlib/1.3.2")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "os=%s is not supported" % self.settings.os)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def export_sources(self):
        # The archive carries no patch today, so this is a no-op for now:
        # export_conandata_patches() only exports entries listed under the
        # "patches:" key of conandata.yml. It is kept so the recipe stays
        # patch-ready and passes the G1 completeness check (shape copied from
        # archives/l/ladybug/0.18.2/conanfile.py).
        export_conandata_patches(self)

    @staticmethod
    def _q(value):
        return shlex.quote(str(value).replace("\\", "/"))

    def _cxx(self):
        # conan 2.29.1: the ":c"/":cpp" sub-keys are not addressable through
        # conf.get(); read the whole mapping and pick the entry (R33).
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        return compilers.get("cpp", "clang++")

    def _zlib_flags(self):
        info = self.dependencies["zlib"].cpp_info
        includes = ["-I%s" % p for p in info.includedirs]
        libdirs = ["-L%s" % p for p in info.libdirs]
        libs = ["-l%s" % l for l in info.libs]
        libs += ["-l%s" % l for l in info.system_libs]
        return includes, libdirs, libs

    def build(self):
        # No-op while conandata.yml has no patches: section (conan just logs
        # 'No patches defined in conandata'); keeps the recipe patch-ready.
        apply_conandata_patches(self)
        includes, libdirs, libs = self._zlib_flags()
        # The Makefile compiles and links with CXXFLAGS and links with
        # LINKFLAGS = -lpthread -lz; overriding both on the make command line
        # gets the dependency search path onto the link step without touching
        # upstream sources.
        cxxflags = " ".join(["-Wall", "-O2", "-DNDEBUG", "-fsigned-char"] + includes)
        linkflags = " ".join(libdirs + ["-pthread"] + libs)
        args = " ".join([
            "CXX=" + self._q(self._cxx()),
            "CXXFLAGS=" + self._q(cxxflags),
            "LINKFLAGS=" + self._q(linkflags),
        ])
        self.run("make -j1 " + args, cwd=self.source_folder, env="conanbuild")

    def package(self):
        copy(self, "lighter", self.source_folder,
             os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        exe = os.path.join(self.package_folder, "bin", "lighter")
        if os.path.isfile(exe):
            os.chmod(exe, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.buildenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
