#!/usr/bin/env python3
"""Conan recipe — minunit 0.0-git20230524-a0586569 (header-only C test framework).

minunit: a minimal unit testing framework for C (mu_assert / MU_TEST /
MU_RUN_SUITE macros, ~12KB single header).  Upstream is a rolling
master (default branch master, no releases; last push 2023-05) — the
package version is a dated master snapshot
(0.0-git20230524-a0586569, commit a0586569bd, 2023-05-24) following
the snapshot-version precedent.

Platform task: 开源鸿蒙PC专项积分赛-依赖 · minunit 0.0-git20230524-a0586569 (自导入, 5 火种).

Build system note: header-only — no build artifacts, package installs
minunit.h.  Settings keep all four keys (CI L0p gate requires
compiler/build_type even for header-only — DRAFT-header-only-package-spec).
R34 consumer verification compiles+runs a real MU_TEST_SUITE against
the installed header (test_package/test_minunit.py).
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, get


class MinunitConan(ConanFile):
    name = "minunit"
    version = "0.0-git20230524-a0586569"
    description = "minunit — minimal unit testing framework for C (single header)"
    license = "MIT"
    homepage = "https://github.com/siu/minunit"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # header-only,无编译产物——但 OHOS profile 要求 settings 含全部四项
    # (CI L0p 门禁;DRAFT-header-only-package-spec)
    settings = "os", "compiler", "build_type", "arch"
    def export_sources(self):
        copy(self, "upstream_test.py", src=self.recipe_folder,
             dst=self.export_sources_folder)

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Header-only is not a waiver for the upstream CI regression harness.
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        compiler = compilers.get("c") or shutil.which("gcc") or shutil.which("clang")
        if not compiler:
            raise RuntimeError("A C compiler is required for upstream minunit tests")
        script = os.path.join(self.source_folder, "upstream_test.py")
        output = os.path.join(self.build_folder, "upstream-test-output")
        self.run(f'"{sys.executable}" "{script}" "{self.source_folder}" '
                 f'"{output}" --compiler "{compiler}"', env="conanbuild")

    def package(self):
        # header-only:安装 minunit.h(单头文件)
        inc_dir = os.path.join(self.package_folder, "include")
        os.makedirs(inc_dir, exist_ok=True)
        shutil.copy(os.path.join(self.source_folder, "minunit.h"),
                    os.path.join(inc_dir, "minunit.h"))
        copy(self, "MIT-LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
