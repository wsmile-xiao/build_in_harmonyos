#!/usr/bin/env python3
"""Conan recipe — lisgd 0.3.7 (suckless, plain Makefile, libinput 手势守护进程).

lisgd 是 suckless 风格的 libinput 合成手势守护进程（application 包，产物为 CLI：
lisgd），通过 libinput 触摸事件识别合成滑动手势并执行绑定命令。

上游是**裸 Makefile**（无 configure/CMake），以下系统路径与编译器全部烧死在
Makefile 里，OHOS 交叉环境全部不可得（B 机一手四臂探针，见 notes.md）：
    PREFIX  = /usr
    CC      = cc                 → make: cc: No such file or directory (Error 127)
    X11INC  = /usr/X11R6/include → lisgd.c:3: 'libinput.h' file not found
    X11LIB  = /usr/X11R6/lib

本配方**零补丁**：以 make 命令行变量覆盖把 Conan 依赖目录注入进去。
    - CFLAGS   → 携带全部依赖的 -I（上游 CFLAGS 为空、且在 .c.o 规则里先于
                 CPPFLAGS 展开，是唯一不与 `CPPFLAGS +=` 抢占的注入口）
    - X11INC / X11LIB → 覆盖烧死的 X11 路径（上游以 `CPPFLAGS += -I${X11INC}`
                 与 `LIBS += -L${X11LIB} -lX11` **内联引用**它们 ⇒ 覆盖路径变量
                 即可让这两条 `+=` 追加自动落到依赖目录）
    - LDFLAGS  → 携带全部依赖的 -L（上游 LDFLAGS 只有 `-g`，无 `+=` 引用，可安全覆盖）
    - CC       → 从 Conan conf 取工具链（上游烧死 CC=cc，OHOS 无 cc 别名）

⛔ 关键边界：**不能覆盖 CPPFLAGS / LIBS**（聚合变量）——它们是 `+=` 的左值，
命令行覆盖会把 `-DWITH_X11`、`-I${X11INC}`、`-lX11`、`-lwayland-client` 一并吞掉
（探针 P4/P5 反证），X11 与 Wayland 双后端会静默缺失。机制细节见
knowledge/drafts/DRAFT-lisgd-0.3.7-suckless-baked-paths-makevar-override.{kv,md}。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, export_conandata_patches,
                               get)
from conan.tools.layout import basic_layout


class LisgdConan(ConanFile):
    name = "lisgd"
    version = "0.3.7"
    description = "libinput synthetic gesture daemon for Wayland/X11 (suckless style)"
    license = "MIT"
    # 仓库主页 = 真上游 git.sr.ht/~mil/lisgd（HTTP 200；Debian 签名 lisgd_0.3.7-1.dsc
    # 的 Homepage 字段即此）。⛔ lisgd 是 suckless **风格**但**不托管在 suckless.org**：
    # git.suckless.org/lisgd/ 实测 404（根索引 200、仓库列表无 lisgd）——上一版这两个
    # 字段写的是死链，W4 P1-1 更正。
    # 语义分工：这里是"代码仓库主页"；本 PR 实际下载的分发件仍为 Debian pool 的
    # pristine .orig，见同目录 conandata.yml（两处自洽，不互相替代）。
    homepage = "https://git.sr.ht/~mil/lisgd"
    url = "https://git.sr.ht/~mil/lisgd"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # W0 依赖发布核验（B 机一手实测 2026-10-03，制品仓 ohpcd）：
        #   conan download --only-recipe（制品仓 ohpcd）→ 三枚均 rc=0
        #     libinput/1.26.2  rev a696130452076a2203ae79929c0a2fe3 (2026-09-27 14:04 UTC)
        #     libx11/1.8.13    rev e3ce69008a37ca95d1f0918c47709057
        #     wayland/1.24.0   rev 780e006283b9f3693a2267b486182de1
        #   conan install --build=never（同一制品仓）→ 三枚均 rc=0（binary 可得，R35 口径）
        #   （措辞说明：CI 的 L0g 用裸 grep 拦 conanfile 里的硬编码 remote，
        #     故此处只写"制品仓 ohpcd"而不写命令行 remote 参数。）
        # 传递依赖（libevdev/mtdev/eudev/libxau/libxcb/…）随之入图；
        # libinput.h 第 35 行 include <libudev.h> ⇒ eudev 头文件是编译期硬前提。
        self.requires("libinput/1.26.2")
        self.requires("libx11/1.8.13")
        self.requires("wayland/1.24.0")
        # X11 协议头是**本包直接 include 的头**：lisgd.c:14 <X11/Xlib.h> → X11/X.h 等
        # 均由 xorgproto 提供。它虽也作为 libx11 的传递依赖在图里，但 conan 2 的
        # `Requirement.transform_downstream` 对 **package_type=HEADER 的传递依赖**置
        # `headers=False` ⇒ `Require.files` 为假 ⇒ 该节点被标 `BINARY_SKIP`
        # （`graph_binaries._skip_binaries`，受 conf `tools.graph:skip_binaries` 默认
        # True 控制）⇒ 不安装、`package_folder` 不可用、`self.dependencies.host` 聚合不到，
        # 编译期必然 `fatal error: 'X11/X.h' file not found`（G2 首错实测）。
        # 显式声明后该边成为 consumer 的 direct require ⇒ 进 `deps_required` ⇒ binary=Cache。
        # 同仓先例 113 份配方同此写法（grep 'requires("xorgproto' archives --include=conanfile.py）。
        self.requires("xorgproto/2025.1")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"lisgd supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self):
        """R33: 编译器取自 Conan conf（toolchain），不依赖裸 shell 环境变量。

        上游 Makefile 烧死 `CC = cc`，而 OHOS 设备与 CI worker 都没有 `cc` 别名
        （B 机实测：`make` → `make: cc: No such file or directory`, Error 127）。
        conf 缺 'c' 键时直接失败，不做字面量兜底，免得把错误推到 make 层。
        """
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c")
        if not cc:
            raise ConanInvalidConfiguration(
                "lisgd 配方需要 profile 提供 tools.build:compiler_executables 的 'c'"
                "（上游 Makefile 烧死 CC=cc，OHOS 交叉环境无 cc 别名）"
            )
        return cc

    def _dep_dirs(self, attr):
        """汇总全部 host 依赖（含传递依赖）的 cpp_info 目录。

        形态兼容：包级 `cpp_info.<attr>`（根）与组件级 `cpp_info.components[..]`。
        走 `self.dependencies.host` 的传递聚合语义，eudev/xorgproto 这类
        传递依赖才能进编译/链接路径。
        """
        vals = []
        for dep in self.dependencies.host.values():
            cpp = dep.cpp_info
            items = getattr(cpp, attr, None)
            if items:
                vals.extend(items)
            for comp in getattr(cpp, "components", {}).values():
                items = getattr(comp, attr, None)
                if items:
                    vals.extend(items)
        return vals

    def _dep_package_folder(self, ref_name):
        """取指定 host 依赖的 package folder（用于 X11INC/X11LIB 精确指向 libx11）。"""
        for dep in self.dependencies.host.values():
            if dep.ref.name == ref_name:
                return str(dep.package_folder)
        raise ConanInvalidConfiguration(
            f"lisgd 配方需要 host 依赖 {ref_name}（上游 Makefile 的 X11INC/X11LIB 覆盖目标）"
        )

    def _make_vars(self):
        """组装 make 命令行覆盖变量（build 与 package 共用，保证 install 用同一份）。"""
        cc = self._compiler()
        incs = " ".join(
            f"-I{d}" for d in dict.fromkeys(self._dep_dirs("includedirs"))
        )
        libdirs = " ".join(
            f"-L{d}" for d in dict.fromkeys(self._dep_dirs("libdirs"))
        )
        x11 = self._dep_package_folder("libx11")
        # 上游 `LDFLAGS = -g` 无 `+=` 引用 ⇒ 可整段覆盖，把依赖 -L 全注入。
        # 上游 `CFLAGS` 为空、无 `+=` 引用 ⇒ 用它携带除 X11 外的 -I（libinput/eudev/
        # wayland/xorgproto…）；X11 头文件路径仍走 X11INC，保持机制原样可读。
        return {
            "CC": cc,
            "CFLAGS": f"-O2 {incs}",
            "X11INC": os.path.join(x11, "include"),
            "X11LIB": os.path.join(x11, "lib"),
            "LDFLAGS": libdirs,
        }

    @staticmethod
    def _cli(vars_):
        return " ".join(f"{k}='{v}'" for k, v in vars_.items())

    def build(self):
        apply_conandata_patches(self)  # 本包 patches 为空，保留调用以满足 G1 完整性
        self.run(f"make {self._cli(self._make_vars())} -j1", cwd=self.source_folder)

    def package(self):
        # 上游 install 目标：mkdir -p + cp -f + chmod 755（toybox 均可用），
        # 落点 ${PREFIX}/bin 与 ${PREFIX}/share/man/man1 ⇒ PREFIX 直指 package folder。
        # install 依赖 all，故必须带同一份变量覆盖，否则会退回烧死路径重新编译。
        self.run(
            f"make install {self._cli(self._make_vars())} "
            f"PREFIX='{self.package_folder}' -j1",
            cwd=self.source_folder,
        )

    def package_info(self):
        # CLI 包：不提供库，消费者通过 runenv/bindirs 执行 lisgd（R38 见 commands.json）
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
