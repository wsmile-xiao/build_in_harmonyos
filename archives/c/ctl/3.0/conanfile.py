#!/usr/bin/env python3
"""Conan recipe — ctl 3.0 (header-only template container library).

ctl（rurban/ctl）是纯头文件的 C 模板容器库（类似 C++ STL vector/list/
string/set 等的 C 实现）：整个库就是 ctl/*.h 共 10 个头文件，消费者
`#define P` + `#define T <type>` 后 `#include <vec.h>` 即可实例化容器。
不产出 lib/ 制品，无 configure/make install 流程（上游仅 Makefile 用于
func/perf 测试与 examples）。

来源：rurban/ctl 官方 tag `3.0` 的官方 tag archive（codeload.github.com
官方 tarball），conandata.yml 带官方归档 SHA-256。
对齐同仓先例：drwav 0.14.5、dr_mp3 0.7.2（header-only 打包）。
"""
from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout
import os

required_conan_version = ">=2.0"


class CtlConan(ConanFile):
    name = "ctl"
    version = "3.0"
    package_type = "header-library"

    description = (
        "Header-only C template container library (vector/list/deque/string/"
        "set/unordered_set/stack/queue/priority_queue), MIT licensed."
    )
    homepage = "https://github.com/rurban/ctl"
    license = "MIT"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("container", "header-only", "template", "c", "stl")

    # R32: settings.os 判断须使用 in ("Linux", "OHOS")；此处保持四元组以过 L0p。
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def export_sources(self):
        export_conandata_patches(self)

    def package_id(self):
        # Header-only：所有构建配置产出相同包。
        self.info.clear()

    def source(self):
        # 官方源：rurban/ctl 官方 tag `3.0` 的官方 tag archive
        # （codeload.github.com 官方 tarball）。codeload 响应 Content-Type
        # 与 URL basename 无 .tar.gz 后缀，需显式 filename 让解包按
        # .tar.gz 识别（drwav 同仓先例 E276）。strip_root=True 解包后
        # 源码根目录即 ctl 仓库内容。
        src = dict(self.conan_data["sources"][self.version])
        src["filename"] = "ctl-3.0.tar.gz"
        get(self, **src, strip_root=True)

    def build(self):
        # Header-only：不编译库制品；当前无补丁（apply_conandata_patches
        # 为 no-op，保留调用以通过配方完整性门禁）。上游测试由 Adapt 阶段
        # 按确认的执行策略补充（tests/func/* 用例，见 notes.md 台账）。
        apply_conandata_patches(self)
        pass

    def package(self):
        # 安装全部 10 个头文件到 include/（消费者 `#include <vec.h>` 等）。
        copy(self, "*.h", src=os.path.join(self.source_folder, "ctl"),
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # Header-only：无链接产物。
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = []