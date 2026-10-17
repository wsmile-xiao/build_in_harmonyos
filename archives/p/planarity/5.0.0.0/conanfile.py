#!/usr/bin/env python3
"""Conan recipe for planarity 5.0.0.0 — Edge Addition Planarity Suite.

上游：https://github.com/graph-algorithms/edge-addition-planarity-suite
产物：libplanarity 图算法库（平面性判定 / 平面嵌入 / Kuratowski 障碍子图隔离 /
      平面绘制）+ planarity 命令行工具 + 公共头文件 + pkg-config 文件 + 手册页。

语言/构建：纯 C，autotools。源码包内已附带生成好的 `configure`，无需 autoreconf。
依赖：无（configure.ac 只有 AC_PROG_CC / AC_PROG_INSTALL / AC_CHECK_HEADERS，
      全部为 libc 头文件；W0 依赖清单 = none）。

OHOS 适配（patches/，均由 refresh-patch --auto 从编辑追踪器生成）：
  0001-c-planarityApp-planarityCommandLine.c.patch
      上游 CLI 只认单横线选项（`-h`/`-help`），`--help`/`--version` 落入
      "Unsupported command line" 分支并返回 -1（实测 rc=255）→ Conan L2 冒烟门禁
      （依次尝试 `--version` / `--help`）失败。补丁增加 `--help` 别名与单行
      `--version` 输出（知识库 E503，jshn 先例）。
  0002-config.guess.patch / 0003-config.sub.patch
      GNU config.guess/config.sub 无 HarmonyOS 分支，`uname -s` = HarmonyOS
      无法匹配任何已知系统 → configure 报 "cannot guess build type"。
      用官方 scripts/patch-autotools-ohos.pl 打补丁后 config.guess 输出
      aarch64-unknown-linux-ohos（知识库 E007）；仅新增 POSIX shell 分支，
      不含平台宏。
  0004-configure.patch
      configure 生成 config.status 时用 `umask 077 && mktemp -d ./confXXXXXX`；
      HMDFS 强制新目录 setgid 且把属主映射为共享属主，drwx--S--- 目录连创建者
      都写不进去 → "can't create ./confXXXXXX/subs1.awk: Permission denied"。
      补丁把两处 umask 077 改为 022（知识库 E011/E129）。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class PlanarityConan(ConanFile):
    name = "planarity"
    version = "5.0.0.0"
    description = ("图的平面性判定/平面嵌入/Kuratowski 障碍子图隔离与平面绘制算法套件 "
                   "— libplanarity 图算法库 + planarity 命令行工具")
    license = "BSD-3-Clause"
    homepage = "https://github.com/graph-algorithms/edge-addition-planarity-suite"
    url = "https://github.com/graph-algorithms/edge-addition-planarity-suite"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # libtool 默认同时产出共享库与静态库；按 shared 选项显式二选一，
        # 避免包内同时出现两种形态导致 package_id / 消费者链接歧义。
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()
        # 无 requirements 时是 no-op；保留以覆盖未来补依赖的场景
        # （缺 AutotoolsDeps 时 configure 的 AC_CHECK_LIB 会假绿，见模板说明）。
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # -j1：本机 make 的 fifo jobserver 在 HMDFS 上被拒（EPERM 噪声），
        # 且共享设备需要并发卫生（notes/device-facts.md §一.13）。
        autotools.make(args=["-j1"])
        # R51/W3：上游测试套件（autotools TESTS = test-samples.sh →
        # `./planarity -test <srcdir>/c/samples`）在 build() 内真实执行，
        # `make check` 失败即 build 失败，保证干净轮日志里带上游测试证据。
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # libtool .la 记录构建期绝对路径（libdir=...），会让包不可重定位；删掉。
        rm(self, "*.la", self.package_folder)

    def package_info(self):
        self.cpp_info.libs = ["planarity"]
        self.cpp_info.bindirs = ["bin"]
        # 安装的 pc 文件名为 libplanarity.pc（Name: planarity）
        self.cpp_info.set_property("pkg_config_name", "libplanarity")
        self.cpp_info.set_property("cmake_file_name", "planarity")
        self.cpp_info.set_property("cmake_target_name", "planarity::planarity")
