#!/usr/bin/env python3
"""Conan recipe — indelible 1.03 (direct compile)."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class IndelibleConan(ConanFile):
    name = "indelible"
    version = "1.03"
    description = "Flexible simulator of biological sequence evolution (nucleotide, amino-acid, codon with indels)."
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/evolbioinfo/indelible"
    url = "https://github.com/evolbioinfo/indelible"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("indelible is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self)

    def source(self):
        # conandata.yml 有两个条目且 sha 不同（主源 kloetzl 提交锁定包 +
        # 官方 abacus 原归档回退），不能用 get(**sources[0]) 单 sha 语义；
        # 逐个尝试，全部失败时抛出最后一个错误以保留真实诊断。
        last_error = None
        for entry in self.conan_data["sources"]:
            try:
                get(self, url=entry["url"], sha256=entry["sha256"],
                    strip_root=True)
                return
            except Exception as e:  # noqa: BLE001 - fallback to next source
                last_error = e
        raise last_error

    def _resolve_cxx(self):
        # R33：编译器取自 Conan conf，不依赖 shell 环境变量。
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = compilers.get("cpp") or compilers.get("c")
        if cxx and os.path.exists(cxx):
            return cxx
        found = shutil.which("clang++") or shutil.which("c++")
        if found:
            return found
        if cxx:
            return cxx
        return "c++"

    def _opt_flags(self):
        if str(self.settings.build_type) == "Debug":
            return ["-O0", "-g"]
        return ["-O2", "-DNDEBUG"]

    def build(self):
        apply_conandata_patches(self)
        # 不走 autoreconf：conan perl 5.42.2 与宿主 perl ABI 冲突，
        # 宿主 /data/service/hnp/bin/autoreconf 起不来
        # （Cwd.so: Perl_my_cxt_init symbol not found, exit 255）。
        # 上游官方构建本就是单命令直编（src/README.txt：
        # g++ -o indelible indelible.cpp -lm，于 src/ 内执行）；
        # kloetzl 树的 configure.ac 仅做无害探测（libm/cos、
        # limits.h、floor/pow/sqrt），不生成 config.h，源码无
        # config.h 引用，直编与 autotools 产物等价
        # （zimg 3.0.6 同型先例：缺 autoreconf 时直接编译）。
        cxx = self._resolve_cxx()
        out = os.path.join(self.build_folder, "indelible")
        flags = " ".join(self._opt_flags())
        self.run(f'"{cxx}" {flags} -Isrc src/indelible.cpp -o "{out}" -lm',
                 cwd=self.source_folder)
        # No upstream test suite to run here: upstream 1.03 ships no
        # tests/ directory and no check/test/ctest target (see
        # test_package/MANIFEST.yml upstream_test_audit). Nothing to omit.

    def package(self):
        copy(self, "indelible", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "indelible.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)
        copy(self, "*", src=os.path.join(self.source_folder, "help"),
             dst=os.path.join(self.package_folder, "share", "doc",
                              "indelible", "help"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
