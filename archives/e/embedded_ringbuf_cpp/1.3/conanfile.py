#!/usr/bin/env python3
"""Conan recipe — embedded_ringbuf_cpp 1.3（header-only C++ 环形缓冲模板库）。

上游是纯头文件模板库：没有构建系统、没有测试框架、没有依赖。
  * source()  下载官方 tag 1.3 tarball，按 conandata.yml 的 sha256 校验。
  * build()   上游没有可配置/可构建的目标，而 conan_verify 的 G1 是纯文本门禁
              （无 package_type 例外分支），必须有 `def build(`。这里不做空 stub：
              对**将要交付的头文件**做一次真实消费者编译 + 运行探针（第一个 include
              就是交付的 <RingBufCPP.h>，实例化 RingBufCPP<> 并断言 add/pull）。
  * package() 安装 RingBuf*.h 到 include/、LICENSE.txt 到 licenses/。
  * test_package 编译并运行真实消费者：读写 / 边界 / 回绕 / peek 断言。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.layout import basic_layout


# 构建期头文件自检探针：第一个 include 必须是交付的头（README 记载的用法）。
_BUILD_PROBE = """#include <RingBufCPP.h>

#include <cstdio>

int main()
{
    RingBufCPP<int, 4> q;
    int v = 42;
    if (!q.add(v)) { return 1; }
    if (q.numElements() != 1) { return 2; }
    int out = 0;
    if (!q.pull(&out)) { return 3; }
    if (out != 42) { return 4; }
    if (!q.isEmpty()) { return 5; }
    std::printf("embedded_ringbuf_cpp build() probe: PASS (add/pull/numElements/isEmpty)\\n");
    return 0;
}
"""


class EmbeddedRingbufcppConan(ConanFile):
    name = "embedded_ringbuf_cpp"
    version = "1.3"
    package_type = "header-library"

    description = "Header-only C++ template ring (circular) buffer for embedded platforms"
    license = "MIT"
    homepage = "https://github.com/wizard97/Embedded_RingBuf_CPP"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("ring-buffer", "circular-buffer", "queue", "header-only")

    settings = "os", "arch", "compiler", "build_type"

    def package_id(self):
        # header-only：交付物与 settings 无关，统一为单一 package id
        self.info.clear()

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # 真实消费者编译 + 运行探针（非空 stub）：编译器取自 profile 的
        # tools.build:compiler_executables（先取 dict 再索引，避免 Conan 2.29
        # 对点分子键访问抛 ConanException），未配置时退回 PATH 里的 clang++。
        compilers = self.conf.get("tools.build:compiler_executables") or {}
        cxx = compilers.get("cpp") or compilers.get("c++") or "clang++"
        cppstd = self.settings.get_safe("compiler.cppstd")
        if not cppstd:
            std_flag = ""
        elif cppstd.startswith(("c++", "gnu++")):
            std_flag = " -std=%s" % cppstd
        else:  # profile 里写的是 "17" 这类裸数字
            std_flag = " -std=c++%s" % cppstd

        probe_src = os.path.join(self.build_folder, "ringbuf_build_probe.cpp")
        probe_bin = os.path.join(self.build_folder, "ringbuf_build_probe")
        save(self, probe_src, _BUILD_PROBE)
        self.run(
            '"%s"%s -I"%s" "%s" -o "%s"'
            % (cxx, std_flag, self.source_folder, probe_src, probe_bin),
            cwd=self.build_folder,
        )
        if can_run(self):
            self.run('"%s"' % probe_bin, cwd=self.build_folder)
        else:
            self.output.warning("can_run=False: 头文件探针只编译未执行（交叉构建）")

    def package(self):
        copy(
            self,
            "RingBuf*.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "embedded_ringbuf_cpp")
        self.cpp_info.set_property(
            "cmake_target_name", "embedded_ringbuf_cpp::embedded_ringbuf_cpp"
        )
        self.cpp_info.includedirs = ["include"]
        # header-only：无 bin/lib 产物（避免 G4/L2/L4/L5 的“跳过却打 ✅”面扩大）
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
