"""Mash 2.3 CLI for aarch64 HarmonyOS PC."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.layout import basic_layout


class MashConan(ConanFile):
    name = "mash"
    version = "2.3"
    description = "Fast genome and metagenome distance estimation"
    license = "BSD-3-Clause"
    homepage = "https://github.com/marbl/Mash"
    url = ""
    topics = ("bioinformatics", "genomics", "cli")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("OHOS", "Linux"):
            raise ConanInvalidConfiguration("Mash is validated on OHOS and Linux")

    def requirements(self):
        self.requires("capnproto/1.3.0")
        self.requires("gsl/2.8")
        self.requires("zlib/1.3.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        source = self.conan_data["sources"][str(self.version)]
        get(self, **source, filename="mash-2.3.tar.gz", strip_root=True)

    def generate(self):
        # R33: read the actual OHOS SDK compilers from the Conan profile.
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        if not compilers.get("c") or not compilers.get("cpp"):
            raise ConanInvalidConfiguration("OHOS profile must define C and C++ compilers")
        VirtualBuildEnv(self).generate()

    def build(self):
        src = self.source_folder
        apply_conandata_patches(self)
        capnp = self.dependencies["capnproto"].package_folder
        gsl = self.dependencies["gsl"].package_folder
        zlib = self.dependencies["zlib"].package_folder
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        cc, cxx = compilers["c"], compilers["cpp"]
        toolbin = os.path.dirname(cc)
        ar = os.path.join(toolbin, "llvm-ar")
        ranlib = os.path.join(toolbin, "llvm-ranlib")

        # The release tag has configure.ac and Makefile.in, but no configure.
        self.run("env -u CONFIG_SHELL SHELL=/bin/sh autoconf", cwd=src, env="conanbuild")
        # E011/E114: HMDFS cannot create Autoconf's mode-0700 scratch dir.
        replace_in_file(self, os.path.join(src, "configure"), "umask 077 && ", "")
        self.run(
            f"env -u CONFIG_SHELL SHELL=/bin/sh "
            f"CC={shlex.quote(cc)} CXX={shlex.quote(cxx)} "
            f"CPPFLAGS={shlex.quote('-I' + os.path.join(zlib, 'include'))} "
            f"./configure --with-capnp={shlex.quote(capnp)} "
            f"--with-gsl={shlex.quote(gsl)} "
            f"--prefix={shlex.quote(self.package_folder)}",
            cwd=src, env="conanbuild",
        )

        # Upstream assumes GNU libstdc++ and system zlib/pthread.  OHOS SDK
        # clang++ supplies libc++; use the pinned Conan zlib static archive.
        makefile = os.path.join(src, "Makefile")
        old = "-lstdc++ -lz -lm -lpthread"
        new = shlex.quote(os.path.join(zlib, "lib", "libz.a")) + " -lm"
        replace_in_file(self, makefile, old, new)

        args = " ".join(
            f"{key}={shlex.quote(value)}"
            for key, value in (("CC", cc), ("CXX", cxx), ("AR", ar), ("RANLIB", ranlib))
        )
        self.run(f"make -j2 {args}", cwd=src, env="conanbuild")
        # Upstream's test target runs four reference-output comparisons.
        gsl_lib = shlex.quote(os.path.join(gsl, "lib"))
        self.run(
            f"env LD_LIBRARY_PATH={gsl_lib} timeout 300 make test {args}",
            cwd=src, env="conanbuild",
        )

    def package(self):
        copy(self, "mash", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "mash*.1", src=os.path.join(self.source_folder, "doc", "man"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
