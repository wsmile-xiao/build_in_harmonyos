#!/usr/bin/env python3
"""Conan recipe — mdns 1.4.3 (header-only C library, mjansson/mdns).

上游形态
--------
GitHub tag `1.4.3` 归档（`mdns-1.4.3/`）只有 14 个文件：

    mdns.h        单头实现库（全部 `static inline`，1618 行，公开 mDNS/DNS-SD API）
    mdns.c        上游**演示程序**（`main()`，discovery/query/service/dump 四种模式）
    CMakeLists.txt  INTERFACE 库 + 可选 example（`MDNS_BUILD_EXAMPLE`，默认 ON）
    cmake/Config.cmake.in  CMake 包配置模板
    README.md CHANGELOG LICENSE .clang-format .gitattributes .gitignore .github/

* 上游**没有 `tests/` 目录**，CMakeLists 里 0 处 `enable_testing()`/`add_test()`（grep 实证），
  `mdns.c` 是演示程序而非测试目标 —— 上游测试总数 N=0（四口径清点见
  `reports/test-report.md`）。
* 无第三方依赖：`mdns.h` 只 `#include` libc 头（stdint/stddef/stdlib/string/fcntl/unistd/
  sys/socket/netinet/in），`grep -n pthread mdns.{c,h}` 为 0 命中，OHOS 侧不注入任何
  system_lib（Conan Center 配方对 Linux/FreeBSD 追加的 `pthread` 同样无调用面，不搬运）。

为什么按 header-only 打包
------------------------
`mdns.h` 自带全部实现，安装面只有 `mdns.h` + LICENSE；上游 CMake 的 install 规则同样只装
`mdns.h` 与 CMake 包配置文件，不产生 `.a`/`.so`。因此 `package_type = "header-library"`：
无编译阶段、`package_id()` 清空（单一包 id），与上游安装面和 Conan Center
（`package_type = "header-library"`）一致。

`copy()` 的 src/dst 一律用 `os.path.join(...)` 绝对路径（相对路径会解析到 build 目录，
已知前例同款坑）。R34：test_package 仍必须真实调用公开 API（见 `test_package/test.c`）。
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class MdnsConan(ConanFile):
    name = "mdns"
    version = "1.4.3"
    description = "Public domain mDNS/DNS-SD library in C (header-only, single file)"
    license = "Unlicense"
    homepage = "https://github.com/mjansson/mdns"
    url = ""  # CI fills this

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # header-only：仅应用 conandata 声明的补丁（本包 patches: {}，无补丁）
        apply_conandata_patches(self)

    def package(self):
        # 安装面 = mdns.h（上游 CMake install(FILES mdns.h)）+ LICENSE
        copy(
            self,
            "mdns.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_id(self):
        self.info.clear()  # 无编译产物 → 单一 package_id

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "mdns")
        self.cpp_info.set_property("cmake_target_name", "mdns::mdns")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        # mdns.h 仅用 libc（sockets/字符串），OHOS 上无需注入 system_lib
