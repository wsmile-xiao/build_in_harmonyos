#!/usr/bin/env python3
"""Conan recipe — dmenu 5.4 (suckless, plain Makefile).

dmenu 是 suckless 的 X11 动态菜单程序（application 包，产物为 CLI：
dmenu / dmenu_path / dmenu_run / stest）。

上游 config.mk 把系统路径与编译器烧死（CC=cc、X11INC=/usr/X11R6/include、
FREETYPEINC=/usr/include/freetype2），OHOS 交叉环境全部不可得：
  - `make`            → make: cc: No such file or directory (Error 127)
  - `make CC=clang`   → dmenu.c:11:10: fatal error: 'X11/Xlib.h' file not found
本配方以 make 命令行变量覆盖（CC / INCS / LIBS / PREFIX / MANPREFIX）注入
Conan 依赖路径，零补丁完成适配；install 目标使用 cp -f（toybox 可用），
man 页 sed 替换 VERSION 正常工作。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class DmenuConan(ConanFile):
    name = "dmenu"
    version = "5.4"
    description = "suckless dynamic menu for X (dmenu, dmenu_path, dmenu_run, stest)"
    license = "MIT"
    homepage = "https://tools.suckless.org/dmenu/"
    url = "https://git.suckless.org/dmenu"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # W0 已核验：两者均已在 ohpcd 制品仓发布（conan download --only-recipe 通过）
        # 注：不带 libxinerama——其配方（1.1.5/1.1.6）钉死 libx11/6.4.0（SONAME 风格
        # 兼容包），与 libxft 钉死的 libx11/1.8.13 在同一依赖图中硬冲突。
        # Xinerama 是上游自带的可选特性（config.mk "comment if you don't want it"），
        # build() 以 XINERAMAFLAGS=/XINERAMALIBS= 置空禁用（gtk2 同因先例）。
        self.requires("libx11/1.8.13")
        self.requires("libxft/2.3.9")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"dmenu supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self):
        """R33: 编译器取自 Conan conf（toolchain），不依赖裸 shell 环境变量。

        不回退到字面量编译器名：上游 config.mk 烧死 `CC = cc`，而 OHOS 设备与 CI worker
        都没有 `cc` 别名，conf 缺 `c` 键时静默兜底只会把失败推到 `make: cc: Not found`。
        """
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c")
        if not cc:
            raise ConanInvalidConfiguration(
                "dmenu 配方需要 profile 提供 tools.build:compiler_executables 的 'c'"
                "（上游 config.mk 烧死 CC=cc，OHOS 交叉环境无 cc 别名）"
            )
        return cc

    def _dep_dirs(self, attr):
        """汇总全部 host 依赖（含传递）的 cpp_info 路径；兼容包级与组件级两种形态。

        前提：链接集里出现的 -lfontconfig 等库由 libxft 的**传递**依赖提供路径，本方法依赖
        `self.dependencies.host` 的传递聚合语义（而非只遍历 direct_requirements）。
        """
        vals = []
        for dep in self.dependencies.host.values():
            cpp = dep.cpp_info
            items = getattr(cpp, attr, None)
            if items:
                vals.extend(items)
                continue
            for comp in getattr(cpp, "components", {}).values():
                items = getattr(comp, attr, None)
                if items:
                    vals.extend(items)
        return vals

    def build(self):
        apply_conandata_patches(self)  # 本包 patches 为空，保留调用以满足 G1 完整性
        cc = self._compiler()
        incs = " ".join(f"-I{d}" for d in self._dep_dirs("includedirs"))
        libs = " ".join(f"-L{d}" for d in self._dep_dirs("libdirs"))
        # 链接集保持上游原样（去掉 -lXinerama，Xinerama 已禁用）
        libs = (libs + " -lX11 -lfontconfig -lXft").strip()
        # 命令行变量覆盖 config.mk 中烧死的 X11INC/X11LIB/FREETYPEINC（经 INCS/LIBS 生效）；
        # XINERAMAFLAGS=/XINERAMALIBS= 置空 = 上游自带的可选特性关闭（libxinerama
        # 配方钉 libx11/6.4.0，与 libxft 的 1.8.13 图冲突，见 requirements 注释）
        self.run(
            f"make CC={cc} INCS='{incs}' LIBS='{libs}' "
            f"XINERAMAFLAGS= XINERAMALIBS= -j1",
            cwd=self.source_folder,
        )

    def package(self):
        # 上游 install 使用 cp -f/mkdir/chmod（toybox 可用），直接以 PREFIX 指向包目录
        self.run(
            f"make install PREFIX={self.package_folder} "
            f"MANPREFIX={os.path.join(self.package_folder, 'share', 'man')} "
            f"-j1",
            cwd=self.source_folder,
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        # application 包不提供库；消费者通过 runenv/bindirs 执行 CLI
