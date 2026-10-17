#!/usr/bin/env python3
"""Conan recipe — knowthelist 2.3.1 (Qt5 qmake 派对音乐播放器 GUI 应用, HarmonyOS PC aarch64).

- 上游: https://github.com/knowthelist/knowthelist (tag v2.3.1)
- 构建: qmake + make (Qt5 core/gui/xml/sql/widgets + gstreamer-1.0/taglib/alsa)
- 依赖: qt/5.15.19 (提供 qmake 与 Qt5 模块), gstreamer/1.28.3, taglib/1.13.1, alsa-lib/1.2.16
- 说明:
  * qmake 交叉编译检测会禁用 pkg-config，必须传 QMAKE_PKG_CONFIG=pkg-config 显式启用。
  * 依赖的 .pc 由 PkgConfigDeps 在 build_folder 私有 prefix 生成（R49），不碰系统目录。
  * qt 包未随附 lrelease，.qm 翻译由本配方在 build() 中生成合法空翻译文件
    （Qt5 qm 头 v3、0 context/0 message），应用回退英文界面（上游主语言），不影响功能。
  * src.pro 的 PKGCONFIG 需求 gstreamer-1.0（包名 gstreamer），配方生成 gstreamer-1.0.pc 别名。
"""
import os
import shutil
import struct

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class KnowthelistConan(ConanFile):
    name = "knowthelist"
    version = "2.3.1"
    description = "knowthelist — Qt5 party music player (DJ mode / mixed mode)"
    license = "LGPL-3.0"
    homepage = "https://knowthelist.github.io/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt5: qmake + core/gui/xml/sql/widgets 模块
        self.requires("qt/5.15.19")
        # 媒体/标签/音频后端
        self.requires("gstreamer/1.28.3")
        self.requires("taglib/1.13.1")
        self.requires("alsa-lib/1.2.16")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R49: 依赖注入全部指向 build_folder 私有 prefix（PkgConfigDeps 生成可重定位 .pc）
        PkgConfigDeps(self).generate()

        # src.pro 的 PKGCONFIG += gstreamer-1.0，但包名为 gstreamer → 生成 gstreamer-1.0.pc 别名
        src_pc = os.path.join(self.generators_folder, "gstreamer.pc")
        alias_pc = os.path.join(self.generators_folder, "gstreamer-1.0.pc")
        if os.path.isfile(src_pc) and not os.path.isfile(alias_pc):
            shutil.copy2(src_pc, alias_pc)

    def _build_env(self):
        """构建环境：qmake 工具链 + 私有 prefix 依赖注入（R49）。

        使用 Environment().vars(self).apply() 上下文（与 qt5-qtimageformats 同模式），
        不用 save_script("conanbuild")——后者会覆盖 Conan 自身的聚合 env 脚本导致
        自引用无限递归（qmake SIGSEGV）。
        """
        qt = self.dependencies["qt"]
        env = Environment()
        # PATH 前置 qt bin（qmake/moc/uic/rcc）与工具链 clang 目录
        env.prepend_path("PATH", os.path.join(qt.package_folder, "bin"))
        env.prepend_path("PATH", "/data/service/hnp/bin")
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(qt.package_folder, "lib"))
        # 生成器目录 = PkgConfigDeps 私有 prefix（R49）
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        return env

    def _generate_qm(self):
        """qt 包未随附 lrelease，生成合法空 .qm（Qt5 qm v3 头，0 context/0 message）。

        上游 TRANSLATIONS 只在构建期被 rcc 嵌入资源；空翻译文件可正常被
        QTranslator::load() 接受，界面回退英文（上游缺省语言）。
        """
        header = struct.pack(">IHHIII", 0x3A1C7D16, 3, 0, 0, 0, 0)
        locale_dir = os.path.join(self.source_folder, "locale")
        if not os.path.isdir(locale_dir):
            return
        generated = 0
        for name in sorted(os.listdir(locale_dir)):
            if not name.endswith(".ts"):
                continue
            qm_path = os.path.join(locale_dir, name[:-3] + ".qm")
            with open(qm_path, "wb") as fh:
                fh.write(header)
            generated += 1
        self.output.info("generated %d empty .qm translation files (no lrelease in qt pkg)" % generated)

    def _run_prefix(self):
        """内联 PATH 前缀（posixsignalmanager 先例，同依赖 qt/5.15.19 且 CI 通过）。

        qmake 探测编译器（Cannot run target compiler 'clang++'）走的是 PATH 解析，
        不读 CC/CXX 环境变量。部分 CI worker 的 PATH 不含 /data/service/hnp/bin，
        且 conan Environment().vars(self).apply() 注入在该类 worker 上不可靠
        （PR #11153 构建 #51439 实证）。在 run 命令内联前缀可同时保证
        qt bin（qmake/moc/uic/rcc）与工具链 clang 目录可达。
        """
        qt = self.dependencies["qt"]
        return "PATH=%s/bin:/data/service/hnp/bin:$PATH " % qt.package_folder

    def build(self):
        apply_conandata_patches(self)
        self._generate_qm()

        qt = self.dependencies["qt"]
        qmake = os.path.join(qt.package_folder, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise RuntimeError("qmake not found in qt package: %s" % qmake)
        src_dir = os.path.join(self.source_folder, "src")
        if not os.path.isfile(os.path.join(src_dir, "src.pro")):
            raise RuntimeError("src/src.pro not found in %s" % self.source_folder)

        # qmake 交叉编译检测会禁用 pkg-config → 显式 QMAKE_PKG_CONFIG=pkg-config
        # R33/R57: 环境由 _build_env() 提供，且 run 命令内联 PATH 前缀双保险
        with self._build_env().vars(self).apply():
            self.run(self._run_prefix() + '"%s" QMAKE_PKG_CONFIG=pkg-config src.pro' % qmake,
                     cwd=src_dir)
            self.run(self._run_prefix() + "make -j1", cwd=src_dir)

    def package(self):
        src_dir = os.path.join(self.source_folder, "src")
        # make install INSTALL_ROOT -> package/usr/{bin,share}; 再归一化 usr/* -> package 根。
        # STRIP=true：qmake 生成 Makefile 的 install_target 会 -$(STRIP) 剥离安装的 ELF，
        # 但 HMDFS 上 strip 后的二进制不可执行（Operation not permitted，acetoneiso 同款坑）
        # → 用 no-op true 覆盖 strip 步骤。
        with self._build_env().vars(self).apply():
            self.run(self._run_prefix() + 'make install INSTALL_ROOT="%s" STRIP=true' % self.package_folder,
                     cwd=src_dir)
        usr = os.path.join(self.package_folder, "usr")
        if os.path.isdir(usr):
            for sub in ("bin", "share", "lib", "etc"):
                sub_src = os.path.join(usr, sub)
                if os.path.isdir(sub_src):
                    sub_dst = os.path.join(self.package_folder, sub)
                    os.makedirs(sub_dst, exist_ok=True)
                    for entry in os.listdir(sub_src):
                        shutil.move(os.path.join(sub_src, entry),
                                    os.path.join(sub_dst, entry))
            shutil.rmtree(usr, ignore_errors=True)

        # 确保可执行位（INSTALL_ROOT 安装的二进制 qmake qinstall 已设 0755，兜底确认）
        binary = os.path.join(self.package_folder, "bin", "knowthelist")
        if os.path.isfile(binary):
            os.chmod(binary, 0o755)

    def package_info(self):
        # 应用包：无库文件供下游链接，仅 bin 目录
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
