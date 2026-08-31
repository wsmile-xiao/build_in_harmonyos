#!/usr/bin/env python3
"""Conan recipe — collectd 5.12.0 (header-only 依赖包)

collectd 是系统统计收集守护进程。本配方不构建 collectd 主程序，仅打包
插件 API 头文件（src/daemon/plugin.h 及其依赖链），供 collectd-apk 等
插件编译使用（collectd-apk 的 Makefile 用 -I<core> + #include <daemon/plugin.h>）。

关键点：
  - collectd.h 的 gnulib_config.h 仅在 WIN32 下引入，config.h 受
    HAVE_CONFIG_H 保护（不定义则跳过）——header-only 打包无需 configure 产物
  - plugin.h 依赖 collectd.h / configfile.h / utils/metadata/meta_data.h /
    utils_time.h；configfile.h 依赖 liboconfig/oconfig.h，按 -I 结构打包
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class CollectdConan(ConanFile):
    name = "collectd"
    version = "5.12.0"
    description = "System statistics collection daemon (plugin API headers)"
    license = "GPL-2.0-only"
    homepage = "https://collectd.org"
    url = "https://github.com/collectd/collectd"

    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def package(self):
        src = self.source_folder
        inc = os.path.join(self.package_folder, "include")
        # daemon/ 头文件（plugin.h 及依赖）
        copy(self, "*.h",
             src=os.path.join(src, "src", "daemon"),
             dst=os.path.join(inc, "collectd", "core", "daemon"))
        # daemon 头文件同时放一层到 core/ 顶层：上游 meta_data.h 等位于
        # utils/metadata/ 子目录，其 `#include "collectd.h"` 依赖 -I<core>
        # 顶层可解析（plugin.h 的相对 include 走 daemon/ 自身目录）
        copy(self, "collectd.h",
             src=os.path.join(src, "src", "daemon"),
             dst=os.path.join(inc, "collectd", "core"))
        copy(self, "configfile.h",
             src=os.path.join(src, "src", "daemon"),
             dst=os.path.join(inc, "collectd", "core"))
        copy(self, "utils_time.h",
             src=os.path.join(src, "src", "daemon"),
             dst=os.path.join(inc, "collectd", "core"))
        # globals.h：collectd.h 在 core/ 顶层 #include "globals.h"（相对引用
        # 走 -I<core> 顶层），须与 collectd.h 同级放置（daemon/ 下已有副本）
        copy(self, "globals.h",
             src=os.path.join(src, "src", "daemon"),
             dst=os.path.join(inc, "collectd", "core"))
        # utils/metadata/meta_data.h（plugin.h 依赖，按 -I<core> 结构）
        copy(self, "meta_data.h",
             src=os.path.join(src, "src", "utils", "metadata"),
             dst=os.path.join(inc, "collectd", "core", "utils", "metadata"))
        # liboconfig/oconfig.h（configfile.h 依赖）
        copy(self, "oconfig.h",
             src=os.path.join(src, "src", "liboconfig"),
             dst=os.path.join(inc, "collectd", "core", "liboconfig"))

    def package_info(self):
        # consumers 以 -I<include/collectd/core> 使用 #include <daemon/plugin.h>
        self.cpp_info.includedirs = ["include/collectd/core"]
