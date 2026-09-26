#!/usr/bin/env python3
"""Conan recipe — kic 2.4c (Enhanced KIC 版图编辑器, wrcad, autotools).

X11 交互式版图编辑器 + 一组无显示依赖的命令行转换工具
（ciftokic / kictocif / kictostr / strtokic / strmtext / kicscale / kichelp）。
OHOS 适配要点：
  - config.sub 三元组补丁（0001）与 X 库路径补丁（0002）
  - configure 上游硬编码 CFLAGS="-O -Wall"，make 阶段需以
    "上游值 + 依赖头文件路径" 覆盖（保留 -DUSE_OLD_MALLOC 上游语义：
    nmalloc 自研分配器整体编译排除，统一走系统 malloc/free）
  - -I 注入 xorgproto（X.h 与 Xlib.h 分属 xorgproto / libx11 两个包）
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class KicConan(ConanFile):
    name = "kic"
    version = "2.4c"
    description = "kic 2.4c (Enhanced KIC 版图编辑器 — X11 交互式 IC 版图绘制与 CIF/GDS 转换工具集)"
    license = "KIC 公有领域许可（见源码 README，自由分发，禁止转售）"
    homepage = "http://www.wrcad.com/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # X11 客户端库（ohpcd 已发布，conan download 验证通过）
        # Xlib.h 在 libx11 包内；X.h/Xatom.h 等基础头在传递依赖 xorgproto 包内
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 交叉编译三元组；--build 与 --host 相同：设备原生工具链构建，
        # 避免老 config.guess（2013）在 HarmonyOS 宿主上探测失败
        tc.configure_args.append("--build=aarch64-linux-ohos")
        tc.configure_args.append("--host=aarch64-linux-ohos")
        tc.generate()

    def _x11_paths(self):
        x11 = self.dependencies["libx11"]
        pkg = x11.package_folder
        inc = os.path.join(pkg, x11.cpp_info.includedirs[0])
        lib = os.path.join(pkg, x11.cpp_info.libdirs[0])
        return inc, lib

    def _dep_includes(self):
        out = []
        for dep in self.dependencies.values():
            for inc in dep.cpp_info.includedirs:
                out.append(os.path.join(dep.package_folder, inc))
        return out

    def build(self):
        apply_conandata_patches(self)
        x11_inc, x11_lib = self._x11_paths()
        # configure：X11 头/库由 --x-includes/--x-libraries 注入
        # （AC_PATH_XTRA 生成 X_CFLAGS/X_LIBS 并写入 xmfb 等 Makefile）
        self.run(
            f"./configure --build=aarch64-linux-ohos --host=aarch64-linux-ohos "
            f"--prefix={self.package_folder} "
            f"--x-includes={x11_inc} --x-libraries={x11_lib}",
            env="conanbuild", cwd=self.source_folder,
        )
        # 上游 configure.in 硬编码 CFLAGS（忽略环境变量），因此 make 阶段
        # 覆盖 CFLAGS = 上游字面值 + 依赖头文件路径：
        #   -DUSE_OLD_MALLOC 为上游语义（nmalloc 编译排除，走系统 malloc）；
        #   -I 注入 xorgproto（X.h）与 libx11（Xlib.h）等依赖头文件目录。
        cflags = "-O -Wall -DUSE_OLD_MALLOC -DHAVE_SYS_IOCTL_H"
        for inc in self._dep_includes():
            cflags += f" -I{inc}"
        # in-source 构建（上游 autoconf 2.63 无 VPATH 支持）
        self.run(
            f"make -j1 -C src/bin CFLAGS='{cflags}'",
            env="conanbuild", cwd=self.source_folder,
        )
        # INSTALL_USER 置空：上游默认 -o root -g bin，CI worker 非 root 会失败
        self.run(
            f"make -C src/bin install prefix={self.package_folder} INSTALL_USER=",
            env="conanbuild", cwd=self.source_folder,
        )

    def package(self):
        pass  # build() 内 make install 已落位（bin/ 与 lib/kic/ 启动文件）

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        # 运行期启动文件目录（kic_tech/ltab 等），消费者通过该 conf 定位
        self.conf_info.define("user.kic:libdir", os.path.join("lib", "kic"))
