#!/usr/bin/env python3
"""Conan recipe for pari-nflistdata 20220729 (鸿蒙 PC / OHOS aarch64).

pari-nflistdata 是 **纯数据包**（Debian `Architecture: all`，`Multi-Arch: foreign`）：
PARI/GP 的数域表，供 gp 的 `nflist` 函数读取。内容为三类 ASCII 表，共 678 个文件
（8845045 字节），全部位于上游 tarball 的 `data/nflistdata/` 下：

  - 650 个 `<degree>/<index>/QT`：Q(T) 上正则扩张的通用多项式，度 2..15
    （度 12 最多，301 个），供 `nflist([n,k], 't)` 读取；
  - 27 个 `5/4/...`：A5（=5T4）五次数域表，分 Jones–Roberts（`0/0..5`、`2/0`）
    与 Allombert–Page（`0cond/0..9`、`2cond/0..9`）两套 × 两种签名；
  - 1 个 `README`（上游发布说明，含 GPL-2+ 声明与完备性边界）。

上游没有任何可编译代码与包内测试（实证计数见 notes.md「构建/测试入口核验」）：
Makefile/configure/CMakeLists/.c/.h/.gp/.py/.sh 命中 **0**；Debian `debian/rules`
的 build 目标只有 `dh_testdir; touch build-stamp`，install 只有
`dh_install nflistdata /usr/share/pari` + 对 >4096 字节的文件 `gzip`，**无 check/test
目标**，`debian/` 内亦无 `debian/tests/`（无 autopkgtest）。

因此本 recipe 的 "build" 是**确定性数据校验**（跑 test_package 里的同一验证器，
损坏下载在 create 中途即失败），"install" 就是把 `nflistdata/` 目录树**按原层级**
落到包内 `res/pari/nflistdata/`，由下游 gp 通过 `default(datadir, "<pkg>/res/pari")`
读取（gp 内部路径模板实证为 `%s/nflistdata/%ld/%ld/QT` 与 `%s/nflistdata/%ld/%ld/%ld%s/%ld`）。

不做 Debian 那步 gzip：PARI 直读未压缩表，省掉构建期对 gzip 的依赖与运行期解压分支。

上游测试入口在消费方 gp：`nflist`。适配期用**制品仓已发布的 pari/2.17.4.1 二进制**
（OHOS arm64 的 bin/gp）对打包产物实跑 685 项断言（650 QT 逐文件 round-trip +
8 项 A5 / A5(6) 功能级语义断言 + 27 个 A5 分片逐文件归因），结果 665 PASS / 0 FAIL /
20 SKIP，逐用例名与结果见 ../upstream-test-cases.txt，命令、断言定义与 SKIP 根因见
test_package/MANIFEST.yml。test_package 只做打包内容字节级校验（R34），
不替代也不冒充上游测试统计。
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)


class PariNflistdataConan(ConanFile):
    name = "pari-nflistdata"
    version = "20220729"
    description = ("PARI/GP nflist database: number fields with prescribed Galois "
                   "groups (A5 / A5(6) tables and regular Q(T)-extensions for "
                   "degrees up to 15), 2022-07-29 release")
    license = "GPL-2.0-or-later"
    homepage = "https://pari.math.u-bordeaux.fr/packages.html#nflistdata"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    # 纯数据包：不产出 .so/.a，也不产出可执行文件。与同族 pari-galpol/20180625、
    # pari-seadate-big/20170418 同型（application + 软件级 commands.json
    # binary:false），确保 conan create 真正执行 package()，产物 res/ 由
    # test_package 的字节级校验实质覆盖。
    package_type = "application"
    # L0p 要求 settings 四项齐全；package_id() 清空后所有 profile 共用同一 noarch 包。
    settings = "os", "arch", "compiler", "build_type"

    # R32: settings.os 判断用 in (...)，不能 == "Linux"
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pari-nflistdata is a data package; supported on Linux/OHOS")

    def export_sources(self):
        # 本包无补丁；标准补丁钩子在 conandata 无 patches 段时是安全空操作
        # （与同族 pari-galpol/pari-seadata 形态一致）。
        export_conandata_patches(self)
        # 验证器随配方导出，build() 才能对**解包后的上游树**跑同一套断言。
        copy(self, "test_pari_nflistdata.py",
             src=os.path.join(self.recipe_folder, "test_package"),
             dst=os.path.join(self.export_sources_folder, "test_package"))

    def layout(self):
        # self.source_folder 直接指向解包根（strip_root 后），路径可预测
        self.folders.source = "."

    def source(self):
        # 上游官方源（R39）。tarball 顶层唯一目录是 data/，strip_root 去掉它，
        # 得到 <src>/nflistdata/<degree>/<index>/QT + <src>/nflistdata/README
        # —— 与 Debian dpkg-source（--strip-components=1）后的 `nflistdata/` 同形。
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # 确定性数据校验（R34：数据包没有可调用 API，完整性校验替代编译 smoke test）。
        # 用 sys.executable 而非裸 python3，不依赖 PATH（R33）。
        validator = os.path.join(self.export_sources_folder, "test_package",
                                 "test_pari_nflistdata.py")
        self.run('"%s" "%s" --source-root "%s"'
                 % (sys.executable, validator, self.source_folder))

    def package(self):
        # 对应 Debian `dh_install nflistdata /usr/share/pari`：落到包内 res 树，
        # **保留上游层级**（gp 按 <datadir>/nflistdata/<deg>/<idx>/QT 直接寻址，
        # 与扁平的 galdata 不同，这里 keep_path 不可关）。
        src = os.path.join(self.source_folder, "nflistdata")
        dst = os.path.join(self.package_folder, "res", "pari", "nflistdata")
        copy(self, "*", src=src, dst=dst)

    def package_id(self):
        # 纯数据、与 arch/compiler/build_type 无关 → 单一 package_id，
        # 避免 8.8 MB 数据按 profile 组合重复存储。
        self.info.clear()

    def package_info(self):
        # 无库、无二进制；通过 cpp_info.resdirs 暴露数据根（Conan 2 原生，
        # 不用 1.x 的 user_info）。下游接线口径与 pari-galpol 一致：把 gp 的
        # `default(datadir, …)` 指到 <pkg>/res/pari，nflist 即可命中
        # <datadir>/nflistdata/<deg>/<idx>/QT。
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["res"]
        self.cpp_info.set_property(
            "pari:nflistdata_rel", os.path.join("res", "pari", "nflistdata"))
