#!/usr/bin/env python3
"""Conan recipe for mk-configure 0.27.0 (packaged as "mkc").

mk-configure is a build system on top of bmake (the portable NetBSD make).
It installs the "mkcmake" wrapper, the mkc_check_* / mkc_install helper
programs and the mkc.*.mk / mkc_imp.*.mk include library; it does not
produce a C/C++ library of its own.  Upstream project name is
"mk-configure", the package name used by this repository is "mkc".

OHOS notes:
  * bmake is needed both to build this package and to run mkcmake, therefore
    it is declared as build and as host requirement.
  * mk-configure 0.27.0 has no top-level configure script: the *.in files
    (mkcmake, mkc_check_version, ...) are substituted by mkc's own
    INTEXTS machinery during "bmake all", which bakes ${PREFIX}, ${AWK}
    and ${BMAKE} into the generated scripts.  build() and package() therefore
    use the same prefix (the package folder) and the same AWK.
  * AWK must be passed explicitly: the checked-in Makefile.inc probes
    /usr/xpg4/bin/awk, /usr/bin/awk and /bin/awk, none of which exists on
    HarmonyOS/OHOS.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class MkcConan(ConanFile):
    name = "mkc"
    version = "0.27.0"
    description = "mk-configure 0.27.0: build system on top of bmake (mkcmake)"
    license = "BSD-2-Clause"
    homepage = "https://github.com/cheusov/mk-configure"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("mkc is adapted for Linux and OHOS only")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # mkcmake is a thin wrapper around bmake, so bmake is a run-time need
        self.requires("bmake/20200710")

    def build_requirements(self):
        self.tool_requires("bmake/20200710")
        self.tool_requires("bmkdep/20140112")

    def layout(self):
        basic_layout(self)

    def source(self):
        # codeload URL carries no ".tar.gz" suffix, so pass the filename
        # explicitly to let conan detect the gzip compression.
        get(
            self,
            filename="mk-configure-0.27.0.tar.gz",
            **self.conan_data["sources"],
            strip_root=True,
        )

    def generate(self):
        VirtualBuildEnv(self).generate()
        env = Environment()
        bmake_pkg = self.dependencies.build["bmake"].package_folder
        # bmake needs its own sys.mk / mk includes to run at all
        env.define("MAKESYSPATH", os.path.join(bmake_pkg, "share", "mk"))
        env.append_path("PATH", self._tool_bin("bmake"))
        env.append_path("PATH", self._tool_bin("bmkdep"))
        env.vars(self, scope="build").save_script("ohc_mkc_build_env")
        # AWK baked into the packaged scripts: prefer GNU awk when present
        awk = shutil.which("gawk") or shutil.which("awk")
        self._awk = awk
        self._cc = None
        self._cxx = None
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        if compilers.get("c"):
            self._cc = compilers["c"]
        if compilers.get("cpp"):
            self._cxx = compilers["cpp"]

    def build(self):
        apply_conandata_patches(self)
        self._run_bmake("all")

    def package(self):
        self._run_bmake("install")

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        for env in (self.buildenv_info, self.runenv_info):
            env.append_path("PATH", os.path.join(self.package_folder, "bin"))

    # ------------------------------------------------------------------ #
    def _tool_bin(self, ref_name):
        return os.path.join(self.dependencies.build[ref_name].package_folder, "bin")

    def _bmake(self):
        return os.path.join(self._tool_bin("bmake"), "bmake")

    def _run_bmake(self, target):
        command = [self._bmake(), target, f"PREFIX={self.package_folder}"]
        if getattr(self, "_awk", None):
            command.append(f"AWK={self._awk}")
        if getattr(self, "_cc", None):
            command.append(f"CC={self._cc}")
        if getattr(self, "_cxx", None):
            command.append(f"CXX={self._cxx}")
        self.run(
            shlex.join(command),
            cwd=self.source_folder,
            env=["conanbuild", "ohc_mkc_build_env"],
        )
