#!/usr/bin/env python3
"""Conan test_package — consumer-level verification for openslide 4.0.1.

Builds a small C consumer program against the installed openslide package and
verifies the library API on a synthetic tiled TIFF (generic-TIFF slide):
  - openslide_detect_vendor() recognizes the slide
  - openslide_open() returns non-NULL and openslide_get_error() is clean
  - openslide_get_level_count() >= 1
  - openslide_get_level_dimensions() matches the image size
  - openslide_read_region() returns clean status and nonzero pixels
  - openslide_close() completes
This is an L1 smoke test: it fails if the headers or the shared object are
unusable on OHOS.  The program is executed for real - a non-zero exit status
fails the build (the shared object must be loadable by the dynamic loader).
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration


class OpenslideTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    exports_sources = "test_openslide.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        self.folders.build = "build"
        self.folders.generators = "build"

    def build(self):
        incs, libdirs = [], []
        for _ref, _d in self.dependencies.items():
            pkg_dir = _d.package_folder
            for p in _d.cpp_info.includedirs:
                if not p:
                    continue
                if not os.path.isabs(p) and not pkg_dir:
                    continue
                incs.append("-I" + (p if os.path.isabs(p) else os.path.join(pkg_dir, p)))
            for p in _d.cpp_info.libdirs:
                if not p:
                    continue
                if not os.path.isabs(p) and not pkg_dir:
                    continue
                libdirs.append("-L" + (p if os.path.isabs(p) else os.path.join(pkg_dir, p)))
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = executables.get("c", "clang")
        src = os.path.join(self.source_folder, "test_openslide.c")
        self.run(
            f"{cc} {src} -o test_openslide "
            + " ".join(incs) + " " + " ".join(libdirs)
            + " -lopenslide"
        )

    def test(self):
        libpaths = []
        for _ref, _d in self.dependencies.items():
            pkg_dir = _d.package_folder
            for p in _d.cpp_info.libdirs:
                if not p:
                    continue
                if not os.path.isabs(p) and not pkg_dir:
                    continue
                ap = p if os.path.isabs(p) else os.path.join(pkg_dir, p)
                if ap not in libpaths:
                    libpaths.append(ap)
        ld_library_path = ":".join(libpaths)
        # 保留系统搜索路径（/system/lib64 等），避免 musl 加载器丢失系统库
        ambient = os.environ.get("LD_LIBRARY_PATH", "")
        if ambient:
            ld_library_path = ld_library_path + ":" + ambient
        # 真实执行：消费者程序必须能被动态加载器载入并跑完断言。
        # 退出码 127 = 加载器拒绝共享库（例如 ELF 代码签名失效），
        # 同样属于产物不可用，必须让构建失败而不是静默通过。
        rc = self.run(
            f"LD_LIBRARY_PATH={shlex.quote(ld_library_path)} ./test_openslide",
            ignore_errors=True,
        )
        if rc == 0:
            return
        if rc == 127:
            raise ConanInvalidConfiguration(
                "test_openslide could not be executed (exit status 127): the "
                "OHOS dynamic loader refused to load the installed "
                "libopenslide.so.1. Check the ELF code signature of the "
                "installed shared object (it must be the unmodified linker "
                "output)."
            )
        raise ConanInvalidConfiguration(
            f"test_openslide exited with status {rc} (non-environment failure)"
        )
