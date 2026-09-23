#!/usr/bin/env python3
"""Conan recipe for gir-to-d 0.23.3 — GObject introspection → D binding generator.

gir-to-d 读取 GObject Introspection 的 `.gir` 文件与 APILookup 描述文件，
生成对应的 D 语言绑定源码（gtk-d 生态的代码生成器）。产物是单个命令行
可执行文件 `girtod`，纯 D 语言实现（source/*.d + source/gtd/*.d）。

构建系统：上游同时提供三条路径——`dub.json`、`meson.build`、`GNUmakefile`。
本配方走 **GNUmakefile**：
  - 它只需要一个 D 编译器（`DC`，按 dmd→ldc→ldc2→gdc 顺序探测）；
  - 不依赖 `dub`（制品仓无该制品），也不受 dub 网络/registry 影响；
  - `meson.build` 用 `vcs_tag()` 取 git describe，而 tarball 无 `.git`，
    需额外处理，故不选。
已验证：用 ldc2 走 GNUmakefile 可直接产出 `girtod`。

工具链：**D 编译器不在框架支持的 LANG_ENUM 内**（c/cpp/rust/python/go/perl/
lua/nodejs/java/bash/mixed/other），设备侧也没有任何 D 工具链。本配方通过
`tool_requires("ldc/1.42.0")`（ohpcd 已发布，os=OHOS/arch=armv8）取得编译器：
该制品提供 `bin/ldc2`、`bin/ldmd2`、`lib/libdruntime-ldc.a`、
`lib/libphobos2-ldc.a` 与 `include/d/`（Phobos 源码），其 recipe 的
package_info 已注入 `DC`/`DMD`/`PATH`/`LD_LIBRARY_PATH`，故 ldc2 运行时能找到
它自己依赖的 `libLLVM.so.20.1`（由 `llvm/20.1.0` 提供，同为 ohpcd 制品）。

补丁：1 个（`patches/0001-opEquals-const-scope.patch`）。LDC 1.42.0 的 DMD
前端（v2.112.1）拒绝 `LinkedHashMap.opEquals` 的 `inout` 形式——当
core.internal.newaa 以 const 限定的 Key 实例化时，
`const(inout(Value[Key]))` 无法转换为所需的 `inout(const(Value[Key]))`。
改为现代 D 惯用的 `scope const` 形式，mutable 与 const 接收者均可用。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class GirToDConan(ConanFile):
    name = "gir-to-d"
    version = "0.23.3"
    description = ("gir-to-d — generate D bindings from GObject introspection "
                   "(.gir) files")
    # 上游 COPYING 为 GNU Lesser General Public License v3（源码头部与 dub.json
    # 均标注 LGPL-3.0，头部措辞为 "version 3 ... or (at your option) any later version"）
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/gtkd-developers/gir-to-d"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 产物是命令行可执行文件 girtod（非库）
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def build_requirements(self):
        # D 编译器工具链：ohpcd 已发布（os=OHOS, arch=armv8），作 application 供下游取用
        self.tool_requires("ldc/1.42.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        if not os.path.isfile(os.path.join(self.source_folder, "GNUmakefile")):
            raise ConanException(
                "upstream GNUmakefile not found — this recipe builds gir-to-d via "
                "the Makefile path (dub is unavailable on OHOS)")

        ldc = self.dependencies.build["ldc"]
        ldc_prefix = ldc.package_folder
        if not ldc_prefix:
            raise ConanException("ldc tool_requires provides no package_folder")

        # ldc2 默认的 import 搜索路径不可用（`object` not found），需显式给出
        # Phobos/druntime 源码目录。
        dc_include = os.path.join(ldc_prefix, "include", "d")
        if not os.path.isdir(dc_include):
            raise ConanException(f"ldc Phobos include dir missing: {dc_include}")
        ldc_lib = os.path.join(ldc_prefix, "lib")

        # GIR_TO_D_VERSION：GNUmakefile 的 VERSION 规则为
        # `git describe --tags || echo $(GIR_TO_D_VERSION)`。tarball 内无 .git，
        # 会回退到 Makefile 里写死的 v0.23.1；显式传本版本号，使二进制内嵌版本
        # 与包版本一致（更准确，非造假）。
        self.run(
            f'make -f GNUmakefile DC=ldc2 GIR_TO_D_VERSION=v{self.version} '
            f'DCFLAGS="-O -I{dc_include}" LDFLAGS="-L-L{ldc_lib}"',
            cwd=self.source_folder,
        )

        artifact = os.path.join(self.source_folder, "girtod")
        if not os.path.isfile(artifact):
            raise ConanException("girtod binary was not produced by the build")

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # 命令行工具：可执行文件装到 bin/
        copy(self, "girtod", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # 消费者可直接调用 girtod
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
