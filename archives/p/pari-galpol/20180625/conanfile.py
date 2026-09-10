#!/usr/bin/env python3
"""Conan recipe for pari-galpol 20180625 (GALPOL 数据库 v4.0, 鸿蒙 PC).

pari-galpol 是 **纯数据包**（Debian `Architecture: all`）：GALPOL 数据库，
定义有理数伽罗华扩张的多项式，覆盖 3657 个抽象群（阶 ≤ 143）、7194 个多项式，
供 PARI/GP 的 `galoisgetpol` 读取。群按 GAP4 SmallGroups 编号索引（数据归属，
不是依赖）。

上游没有任何可编译代码、没有 configure/Makefile/CMake：
- 官方源 `galpol.tgz`（= `galpol-4.0.tar.gz` = Debian `pari-galpol_4.0.orig.tar.gz`，
  三者 sha256 同为 562af283…bb01b）共 18483 个条目，全部位于 `data/galpol/` 下；
- 14681 个文件 = 3657 `real` + 3537 `complex` + 3657 `group` + 3657 `name`
  + 143 `nb` + 29 `non-wss` + 1 `README`，全为 ASCII 的 GP 文本；
  Makefile/configure/CMakeLists/.c/.h/.gp/.py/test 计数均为 0。
- Debian `debian/rules` 的 build 目标只 `touch build-stamp`，install 只
  `dh_install galpol /usr/share/pari` + 对 real/complex/group 做 `gzip`
  （**无 check/test 目标**；`debian/` 内亦无 `debian/tests/`，无 autopkgtest）。

所以本 recipe 的 "build" 是空操作，"install" 就是把 galpol/ 目录原样落到包内
res/ 下，由下游 gp 通过 `datadir` 读取。

上游测试入口不在包内，而是消费方 gp 的 `galoisgetpol`：本包适配期已用**已发布的
pari/2.17.4 二进制**对上表全部条目实跑 7337 项断言（143 个 `nb` 计数 +
3657 real + 3537 complex 的 `galoisgetpol(n,k,flag) == read(n/k/{real,complex})`
且 `poldegree == n`），命令与统计见 test_package/MANIFEST.yml 与 notes.md（原始逐用例
日志在本地 reports/，按仓库 .gitignore 的 `reports/` 条目不入 PR，可按上述命令复现）。
test_package 只做打包内容的字节级校验（R34），不冒充也不替代上游测试统计。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches, get)


class PariGalpolConan(ConanFile):
    name = "pari-galpol"
    version = "20180625"
    description = ("Galois polynomial database (GALPOL 4.0) for PARI/GP galoisgetpol, "
                   "all abstract groups of order up to 143 (2018-06-25 release)")
    license = "GPL-2.0-or-later"
    homepage = "https://pari.math.u-bordeaux.fr/galpol"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    # 纯数据包：不产出 .so/.a，也不产出可执行文件。与同族的 pari-seadata/20090618
    # 同型（application + 软件级 commands.json binary:false），确保 conan create
    # 真正执行 package()，产物 res/ 由 test_package 的字节级校验实质覆盖。
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    # R32: settings.os 判断用 in (...)，不能 == "Linux"
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pari-galpol is a data package; supported on Linux/OHOS")

    def export_sources(self):
        # 本包无补丁；标准补丁钩子，export_conandata_patches/apply_conandata_patches
        # 在 conandata 无 patches 段时为安全的空操作（与 pari-seadata 同族形态一致）。
        export_conandata_patches(self)

    def layout(self):
        # 让 self.source_folder 直接指向解包根（strip_root 后），路径可预测
        self.folders.source = "."

    def source(self):
        # 上游官方源（R39）：顶层目录 data/ 被 strip_root 去掉，
        # 得到 <src>/galpol/<order>/<index>/{real,complex,group,name} + <order>/nb
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 纯数据包：无 configure / 无编译 / 无链接 / 无上游可运行测试。
        # 上游 debian/rules 的 build 目标亦仅 `touch build-stamp`。
        apply_conandata_patches(self)

    def package(self):
        # 对应 Debian `dh_install galpol /usr/share/pari`：落到包内 res 树，
        # 保持 gp 期望的 `<datadir>/galpol/...` 相对布局。
        # 保留上游未压缩文件（PARI 可直读；不为 gzip 引入构建期工具）。
        src = os.path.join(self.source_folder, "galpol")
        dst = os.path.join(self.package_folder, "res", "pari", "galpol")
        copy(self, "*", src=src, dst=dst)
        # 许可证随附（上游 tarball 无独立 COPYING，README 内含 GPL-2.0+ 声明）
        copy(self, "README", src=src, dst=dst)

    def package_id(self):
        # 纯数据、与 arch/compiler/build_type 无关 → 单一 package_id，
        # 避免每个 profile 组合重复存储 28 MB 数据。
        self.info.clear()

    def package_info(self):
        # 无库、无二进制；通过 cpp_info.resdirs 暴露数据根（Conan 2 原生，避免
        # user_info 的 1.x 弃用告警）。下游把 gp 的 `datadir` 指到 <pkg>/res/pari
        # 即可让 galoisgetpol 命中 <datadir>/galpol/<order>/nb。
        self.cpp_info.libs = []
        self.cpp_info.resdirs = ["res"]
        # 自定义属性，方便下游直接取相对路径（get_property）。
        self.cpp_info.set_property("pari:galpol_rel", os.path.join(
            "res", "pari", "galpol"))
