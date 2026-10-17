#!/usr/bin/env python3
"""Conan recipe for qbootctl 0.2.2.

qbootctl is a pure-C CLI tool (Meson) that manages Qualcomm A/B boot
slots: it reads/writes GPT boot attributes, queries /proc/cmdline and
uses UFS BSG ioctls. All of those need root + real hardware.

The production binary (bin/qbootctl) keeps upstream semantics exactly:
no mock code, no runtime switch. meson also builds a separate test-only
target bin/qbootctl-test with -DQBOOTCTL_TESTING, whose backend is a
pure in-memory mock (no device access) used exclusively by test_package
(see patches/0001-meson.build.patch + 0002-qbootctl.c.patch).
"""

import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class QbootctlConan(ConanFile):
    name = "qbootctl"
    version = "0.2.2"
    description = "Qualcomm bootctrl HAL port for Linux — A/B boot slot management CLI"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/linux-msm/qbootctl"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: OHOS + Linux are the only supported targets.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"qbootctl only supports Linux-like OS, got: {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        self._inject_meson_archiver(tc)
        tc.generate()

    def _inject_meson_archiver(self, tc):
        # 【OHOS 必需】conan 的 MesonToolchain 不把 tools.build:compiler_executables
        # 里的 ar/ranlib 写进 native file，meson 便按裸名 llvm-ar 探测归档器；CI
        # PATH 上没有 llvm-ar 时 meson configure 直接失败
        # （ERROR: Unknown linker(s): [['llvm-ar']]）。这里把 ar/ranlib 全路径注入
        # tc（在 tc.generate() 前完成），不污染 PATH。（opus 1.4 / dav1d 1.5.0 实证）
        if str(self.settings.os) != "OHOS":
            return
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        ar = executables.get("ar") or ""
        ranlib = executables.get("ranlib") or ""
        # profile 通常只给 c/cpp：从 c 编译器绝对路径同目录推导 llvm-ar / llvm-ranlib。
        if not ar:
            cc = executables.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                cand = os.path.join(bindir, "llvm-ar")
                if os.path.isfile(cand):
                    ar = cand
                    rlc = os.path.join(bindir, "llvm-ranlib")
                    if os.path.isfile(rlc):
                        ranlib = rlc
        if not ar or not os.path.isfile(ar):
            raise ConanException(
                "Required OHOS archiver 'ar' is missing: cannot resolve llvm-ar "
                "from tools.build:compiler_executables "
                f"(c compiler: {executables.get('c')!r})"
            )
        tc.ar = ar
        if ranlib and os.path.isfile(ranlib):
            tc.binaries["ranlib"] = ranlib

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        # meson.install() installs only install:true targets -> the
        # production bin/qbootctl. qbootctl-test (QBOOTCTL_TESTING) is
        # install:false in meson.build, so it is copied to a test-only
        # location inside the package and never exposed through
        # cpp_info.bindirs; the production package ships only the real
        # qbootctl binary plus LICENSE.
        meson = Meson(self)
        meson.install()
        copy(
            self,
            "qbootctl-test",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "test"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        # CLI tool only: no libraries or headers are produced.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
