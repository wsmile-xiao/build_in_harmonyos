#!/usr/bin/env python3
"""Conan consumer test for libuninum 2.7 — Unicode 数字转换库。

两层消费者验证：
1. test.c：编译链接库 API，19 项断言（uninum.h 直接 #include <gmp.h>，
   gmp 的 include/lib 路径必须同时可见）；
2. test_cli.sh：被测包自带的 numconv CLI 端到端用例（Western→Arabic_Western
   完整多字符往返），验证 LP64 补丁（UTF8in 输入 / putu8s 输出）的实际可用性。
   CLI 通过 dependencies 元数据 + cpp_info.bindirs 定位，不依赖 PATH。
"""

import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class LibuninumTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "test.c", "test_cli.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compiler_executables.get("c")
        if not cc:
            raise ConanException(
                "tools.build:compiler_executables must define the C compiler"
            )

        uninum_info = self.dependencies[self.tested_reference_str].cpp_info
        # uninum.h 直接包含 <gmp.h>：消费者视角需要 gmp 的 include/lib
        gmp_info = self.dependencies["gmp"].cpp_info

        include_dirs = list(uninum_info.includedirs) + list(gmp_info.includedirs)
        lib_dirs = list(uninum_info.libdirs) + list(gmp_info.libdirs)
        libs = list(uninum_info.libs) + list(gmp_info.libs)
        system_libs = ["m"] if self.settings.os in ("Linux", "OHOS") else []

        include_flags = " ".join(f'-I"{d}"' for d in include_dirs)
        lib_flags = " ".join(f'-L"{d}"' for d in lib_dirs)
        link_flags = " ".join(f"-l{l}" for l in libs + system_libs)

        source = Path(self.source_folder, "test.c")
        output = Path(
            self.build_folder,
            "test_uninum.exe" if str(self.settings.os) == "Windows" else "test_uninum",
        )
        output.parent.mkdir(parents=True, exist_ok=True)

        self.run(
            f'"{cc}" -std=gnu99 {include_flags} "{source}" '
            f'{lib_flags} {link_flags} -o "{output}"'
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile-only consumer test")
            return
        exe = Path(
            self.build_folder,
            "test_uninum.exe" if str(self.settings.os) == "Windows" else "test_uninum",
        )
        self.run(f'"{exe}"', env="conanrun")

        # 消费者 CLI 端到端用例：定位被测包安装的 numconv（不依赖 PATH），
        # 断言 Western->Arabic_Western 完整多字符往返（LP64 补丁可用性验证）
        dep = self.dependencies[self.tested_reference_str]
        bindir = dep.cpp_info.bindirs[0] if dep.cpp_info.bindirs else "bin"
        numconv = Path(dep.package_folder, bindir, "numconv")
        if not numconv.is_file():
            raise ConanException(f"numconv not found in package: {numconv}")
        script = Path(self.source_folder, "test_cli.sh")
        self.run(f'sh "{script}" "{numconv}"', env="conanrun")
