#!/usr/bin/env python3
"""Conan test_package for gtkd 3.11.0 — consumer-side check (R34 真实 API).

以消费者视角使用**已打包**的 gtkd：用 D 编译器把一段真实 D 程序链接到包内的
静态库 `libgtkd-3.a`，**运行**它并校验输出。

为什么用 Python 驱动而不是 .d 源：
  ① CI 门禁 L0c / PF3 只认 `.c/.cpp/.cc/.cxx/.sh/.py`（D 源不在白名单）；
  ② D 程序需要「编译 → 运行」两步，且运行期依赖 GTK 的 .so 在
     LD_LIBRARY_PATH 上（gtkd 是 dlopen 型绑定），用脚本编排最直接。

env="conanrun" 注入是必需的：包侧 package_info() 声明的 runenv 与 gtk 依赖的
运行库路径都要靠它进入环境。
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class GtkdTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        # 编译 D 测试程序需要 D 编译器（与被测包同一 tool_requires）
        self.tool_requires("ldc/1.42.0")

    def test(self):
        pkg = self.dependencies["gtkd"].package_folder
        inc = os.path.join(pkg, "include", "d", "gtkd-3")
        libdir = os.path.join(pkg, "lib")

        # 载荷完整性：静态库 + D 导入源码缺一不可
        if not os.path.isfile(os.path.join(libdir, "libgtkd-3.a")):
            raise ConanException(f"libgtkd-3.a missing under {libdir}")
        if not os.path.isfile(os.path.join(inc, "gtk", "Version.d")):
            raise ConanException(f"gtkd D imports missing under {inc}")

        ldc = self.dependencies.build["ldc"].package_folder
        dc = os.path.join(ldc, "bin", "ldc2")
        if not os.path.isfile(dc):
            raise ConanException(f"ldc2 not found: {dc}")
        phobos = os.path.join(ldc, "include", "d")
        if not os.path.isdir(os.path.join(phobos, "std")):
            raise ConanException(f"ldc Phobos sources missing: {phobos}")

        script = os.path.join(os.path.dirname(__file__), "test_gtkd.py")
        if not os.path.isfile(script):
            raise ConanException(f"test_gtkd.py missing: {script}")

        env = {
            "GTKD_TEST_INC": inc,
            "GTKD_TEST_LIBDIR": libdir,
            "GTKD_TEST_DC": dc,
            "GTKD_TEST_PHOBOS": phobos,
            "GTKD_TEST_LDC_LIB": os.path.join(ldc, "lib"),
        }
        for k, v in env.items():
            os.environ[k] = v
        # 必须同时注入 **conanbuild 与 conanrun** 两套环境：
        #   · conanrun  —— 被测包与 gtk 依赖的运行库路径（D 程序运行期 dlopen GTK）
        #   · conanbuild—— ldc 是 tool_requires（构建上下文），其运行库路径
        #     （ldc/lib 与传递依赖 llvm/20.1.0 的 libLLVM.so）只出现在构建环境里。
        # 只用 conanrun 会让 ldc2 自身起不来（实测）：
        #   ldc2: _ZN4llvm11raw_ostream10resetColorEv: symbol not found
        self.run(f'python3 "{script}"', env=["conanbuild", "conanrun"])
