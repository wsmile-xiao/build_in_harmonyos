#!/usr/bin/env python3
"""Conan recipe for djstub 0.7 (Makefile)."""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class DjstubConan(ConanFile):
    name = "djstub"
    version = "0.7"
    description = "DJGPP-compatible stub manipulation tools"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/stsp/djstub"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)
        copy(
            self,
            "ohos-script-launcher.c",
            src=self.recipe_folder,
            dst=self.export_sources_folder,
        )

    def build_requirements(self):
        # Smaller C is packaged separately and supplies the DOS-target compiler.
        self.tool_requires("smallerc/1.0.2")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def _build_environment(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compiler_executables.get("c") or "clang"
        smallerc_root = self.dependencies.build["smallerc"].package_folder
        parts = [f"CC={shlex.quote(cc)}", f"SMPATH={shlex.quote(smallerc_root)}"]

        cflags = self.conf.get("tools.build:cflags", default=[], check_type=list)
        if cflags:
            parts.append(f"CFLAGS={shlex.quote(' '.join(cflags))}")
        ldflags = self.conf.get("tools.build:exelinkflags", default=[], check_type=list)
        if ldflags:
            parts.append(f"LDFLAGS={shlex.quote(' '.join(ldflags))}")
        return " ".join(parts)

    def build(self):
        apply_conandata_patches(self)
        source = shlex.quote(self.source_folder)
        build_env = self._build_environment()
        self.run(f"{build_env} make -C {source} -j1", env="conanbuild")

        # Upstream has no test target. Exercise version reporting and stub creation.
        executable = os.path.join(self.source_folder, "djstubify")
        smoke_file = os.path.join(self.build_folder, "djstub-smoke.exe")
        self.run(f"{shlex.quote(executable)} --version", env="conanbuild")
        self.run(
            f"{shlex.quote(executable)} -g -o {shlex.quote(smoke_file)} "
            f"-l {shlex.quote(executable)}",
            env="conanbuild",
        )
        self.run(
            f"{shlex.quote(executable)} -i {shlex.quote(smoke_file)}",
            env="conanbuild",
        )
        if self.settings.os == "OHOS":
            compiler_executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
            cc = compiler_executables.get("c") or "clang"
            launcher_source = os.path.join(
                self.source_folder, "ohos-script-launcher.c"
            )
            launcher = os.path.join(self.build_folder, "djstub-script-launcher")
            self.run(
                f"{shlex.quote(cc)} -O2 -Wall -Wextra "
                f"-o {shlex.quote(launcher)} {shlex.quote(launcher_source)}",
                env="conanbuild",
            )

    def package(self):
        bin_folder = os.path.join(self.package_folder, "bin")
        copy(
            self,
            "djstubify",
            src=self.source_folder,
            dst=bin_folder,
            keep_path=False,
        )
        scripts = ("djstrip", "djlink", "djelfextract")
        if self.settings.os == "OHOS":
            script_folder = os.path.join(self.package_folder, "libexec", "djstub")
            for script in scripts:
                copy(
                    self,
                    script,
                    src=self.source_folder,
                    dst=script_folder,
                    keep_path=False,
                )
            launcher = os.path.join(self.build_folder, "djstub-script-launcher")
            os.makedirs(bin_folder, exist_ok=True)
            for script in scripts:
                shutil.copy2(launcher, os.path.join(bin_folder, script))
        else:
            for script in scripts:
                copy(
                    self,
                    script,
                    src=self.source_folder,
                    dst=bin_folder,
                    keep_path=False,
                )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "README.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "res"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
