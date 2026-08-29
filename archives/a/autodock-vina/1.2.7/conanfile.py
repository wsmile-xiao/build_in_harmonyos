#!/usr/bin/env python3
"""Conan recipe for AutoDock Vina 1.2.7."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv


class AutodockVinaConan(ConanFile):
    name = "autodock-vina"
    version = "1.2.7"
    description = "Molecular docking and virtual screening engine"
    license = "Apache-2.0"
    homepage = "https://github.com/ccsb-scripps/AutoDock-Vina"
    url = "https://github.com/ccsb-scripps/AutoDock-Vina"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("AutoDock Vina supports Linux and OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds currently support armv8 only")

    def requirements(self):
        # Boost 1.90.0.1 supplies the compiled libraries; its package omits
        # two header-only directories required by Vina.
        self.requires("boost/1.90.0.1")

    def build_requirements(self):
        # The published 1.84.0 package retains the complete Boost header set.
        # Use it only as a build-context header provider; link against the
        # 1.90.0.1 host libraries above.
        self.tool_requires("boost/1.84.0")

    def layout(self):
        self.folders.source = "src"
        self.folders.build = "build"

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return executables.get("cpp") or os.environ.get("CXX") or "c++"

    def build(self):
        makefile = os.path.join(self.source_folder, "build", "linux", "release", "Makefile")
        boost = self.dependencies["boost"].package_folder
        boost_headers = self.dependencies.build["boost"].package_folder
        shell = os.environ.get("CONFIG_SHELL", "/bin/sh")
        if self.settings.os == "OHOS":
            shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

        with open(makefile, "r", encoding="utf-8") as handle:
            content = handle.read()
        content = content.replace("BASE=/usr", f"BASE={boost}")
        content = content.replace(
            "BOOST_INCLUDE = $(BASE)/include",
            f"BOOST_INCLUDE = {boost}/include {boost_headers}/include",
        )
        content = content.replace("C_PLATFORM=-static -pthread", "C_PLATFORM=-pthread")
        content = content.replace("GPP=g++", f"GPP={self._compiler()}")
        options = "C_OPTIONS= -O3 -DNDEBUG -std=c++14"
        if self.settings.os == "OHOS":
            # OHOS musl does not expose pthread cancellation APIs used by
            # Boost.Thread's default sleep implementation.
            options += " -DBOOST_SP_NO_PTHREAD_SETCANCELSTATE"
        content = content.replace("C_OPTIONS= -O3 -DNDEBUG -std=c++11", options)
        with open(makefile, "w", encoding="utf-8") as handle:
            handle.write(content)

        common = os.path.join(self.source_folder, "build", "makefile_common")
        with open(common, "r", encoding="utf-8") as handle:
            common_content = handle.read()
        # Boost.System became header-only in Boost 1.69; remove the obsolete
        # library from both dynamic and static LIBS definitions.
        common_content = common_content.replace(
            "-l boost_system${BOOST_LIB_VERSION} ", ""
        )
        common_content = common_content.replace(
            "${BASE}/lib/libboost_system${BOOST_LIB_VERSION}.a ", ""
        )
        common_content = common_content.replace(
            "INCFLAGS = -I $(BOOST_INCLUDE)",
            f"INCFLAGS = -I{boost}/include -I{boost_headers}/include",
        )
        common_content = common_content.replace(
            "LDFLAGS = -L$(BASE)/lib -L.",
            f"LDFLAGS = -L$(BASE)/lib -L. -Wl,-rpath,{boost}/lib",
        )
        with open(common, "w", encoding="utf-8") as handle:
            handle.write(common_content)

        build_dir = os.path.dirname(makefile)
        command = f'make -C "{build_dir}" -j2 SHELL="{shell}"'
        self.run(command, env="conanbuild")

    def package(self):
        release_dir = os.path.join(self.source_folder, "build", "linux", "release")
        copy(self, "vina", src=release_dir, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "vina_split", src=release_dir, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
