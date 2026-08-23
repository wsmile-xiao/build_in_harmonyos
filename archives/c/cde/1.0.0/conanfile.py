#!/usr/bin/env python3
"""Conan recipe for cde 0.1 — CDE static-bundler (offline static environment-bundling CLI).

Build: clang -static single-file compilation (no autotools/configure required).
Package: installs cde-static-bundler to bin/.
"""
import os
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    replace_in_file,
)
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class CdeConan(ConanFile):
    name = "cde"
    version = "1.0.0"
    description = "CDE static-bundler: offline static environment-bundling CLI for Linux"
    license = "GPL-3.0-or-later"
    homepage = "http://www.pgbovine.net/cde.html"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "cde-static-bundler.c",
             src=os.path.join(self.recipe_folder, "tools", "cde-static-bundler"),
             dst=self.export_sources_folder)

    def requirements(self):
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"cde supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        pass

    def generate(self):
        env = Environment()
        env.define("TMPDIR", os.path.join(os.path.expanduser("~"), "tmp"))
        env.define("CC", "clang")
        env.define("CXX", "clang++")
        env.vars(self).save_script("cde_build_env")

    def build(self):
        apply_conandata_patches(self)
        # 上游 CDEpack 是 Makefile-only 项目（无 configure 脚本），
        # G0 需识别此预期行为：configure 失败后直接执行 make。
        # 对于 OHOS 目标，确保 Makefile 使用 clang 编译。
        makefile = os.path.join(self.source_folder, "Makefile")
        if os.path.exists(makefile):
            # 替换 Makefile 默认 gcc 为 clang（OHOS 兼容）
            replace_in_file(self, makefile, "CC=gcc", "CC=clang")
            replace_in_file(self, makefile, "CC ?= gcc", "CC ?= clang")
        candidates = [
            os.path.join(self.export_sources_folder, "cde-static-bundler.c"),
            os.path.join(self.source_folder, "cde-static-bundler.c"),
        ]
        src = next((c for c in candidates if os.path.exists(c)), None)
        if src is None:
            raise ConanInvalidConfiguration("cde-static-bundler.c not found in export sources")
        bin_path = os.path.join(self.build_folder, "cde-static-bundler")
        self.run(f"clang -Wall -Wextra -O2 -static -o {bin_path} {src}", env=["cde_build_env"])

    def package(self):
        copy(self, "cde-static-bundler", dst=os.path.join(self.package_folder, "bin"),
             src=self.build_folder, keep_path=False)
        copy(self, "LICENSE*", dst=os.path.join(self.package_folder, "licenses"),
             src=self.source_folder, keep_path=False)

    def package_info(self):
        self.buildenv_info.define("PATH", os.path.join(self.package_folder, "bin"))
        self.output.info(f"cde-static-bundler installed to: {os.path.join(self.package_folder, 'bin')}")