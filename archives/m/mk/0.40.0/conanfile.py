#!/usr/bin/env python3
"""Conan recipe for mk-configure 0.40.0 (packaged as "mk").

mk-configure is a build system on top of bmake (the portable NetBSD make).
It installs the "mkcmake" wrapper, the mkc_* helper programs and the
mkc.*.mk / mkc_imp.*.mk include library; it does not produce a C/C++ library
of its own.  Upstream project name is "mk-configure", the package name used
by this repository is "mk".

OHOS notes:
  * bmake is needed both to build this package and to run mkcmake, therefore
    it is declared as build and as host requirement.
  * mk-configure bakes ${PREFIX} into the generated scripts, so build() and
    package() use the same prefix (the package folder).
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout



class MkConan(ConanFile):
    name = "mk"
    version = "0.40.0"
    description = "mk-configure: build system on top of bmake (mkcmake)"
    license = "BSD-2-Clause"
    homepage = "https://github.com/cheusov/mk-configure"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("mk is adapted for Linux and OHOS only")

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
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        env = Environment()
        bmake_pkg = self.dependencies.build["bmake"].package_folder
        # bmake needs its own sys.mk / mk includes to run at all
        env.define("MAKESYSPATH", os.path.join(bmake_pkg, "share", "mk"))
        env.append_path("PATH", self._tool_bin("bmake"))
        env.append_path("PATH", self._tool_bin("bmkdep"))
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        if compilers.get("c"):
            env.define("USE_CC", compilers["c"])
        if compilers.get("cpp"):
            env.define("USE_CXX", compilers["cpp"])
        awk = shutil.which("gawk") or shutil.which("awk")
        if awk:
            env.define("USE_AWK", awk)
        env.vars(self, scope="build").save_script("ohc_mk_build_env")

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
        self.run(
            shlex.join(command),
            cwd=self.source_folder,
            env=["conanbuild", "ohc_mk_build_env"],
        )
