#!/usr/bin/env python3
"""Compile and run an fltk consumer against the OHOS package.

两类验证：

1. 产物可被真实消费 —— 用 clang++ 编译并链接一个只依赖非 GUI API 的
   消费者程序，然后**真的运行**它。FLTK 的 utf8/filename/Text_Buffer
   代码路径都不接触 X display，因此可以在没有显示设备的沙箱里跑出断言，
   不需要 show()/run()。
2. 平台特有行为 —— fl_utf8locale() 是纯 getenv 启发式（不查真实 C
   locale），用不同 LC_ALL 多次调用同一程序做差分断言；单进程内验证不
   了，因为结果被缓存在函数内 static 里。

libfltk.a 是静态库，链接顺序必须是
    消费者 → fltk_images → fltk → X11/dl/m → libc++，
且 fltk-config --libs 不含 X11 项，需要消费侧显式补 -lX11。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class FltkTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        fltk = self.dependencies["fltk"]
        x11 = self.dependencies["libx11"]
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        # profile 里 C++ 编译器登记的键是 "cpp"
        cxx = compilers.get("cpp", "clang++")

        source = os.path.join(self.source_folder, "test_fltk.cxx")
        exe = os.path.join(self.build_folder, "test_fltk")
        fltk_inc = os.path.join(fltk.package_folder, "include")
        fltk_lib = os.path.join(fltk.package_folder, "lib")
        x11_lib = os.path.join(x11.package_folder, "lib")

        self.run(
            '"{}" -std=c++17 "{}" -I"{}" -L"{}" -lfltk_images -lfltk '
            '-L"{}" -lX11 -ldl -lm -lc++ -lc++abi -o "{}"'.format(
                cxx, source, fltk_inc, fltk_lib, x11_lib, exe
            ),
            env="conanbuild",
        )

        # bin/ 下的 fltk-config 是包对外承诺的产物之一，单独验一次
        config = os.path.join(fltk.package_folder, "bin", "fltk-config")
        if not os.path.isfile(config):
            raise ConanException(
                "fltk package is missing bin/fltk-config: {}".format(config)
            )

        if not can_run(self):
            self.output.info("cross-build detected: skipping the run step")
            return

        self.run('"{}" --version'.format(config), env="conanrun")
        self.run('"{}"'.format(exe), env="conanrun")
        # 平台特有差分断言：fl_utf8locale() 只看 getenv
        self.run('LC_ALL=C "{}" --expect-utf8locale 0'.format(exe), env="conanrun")
        self.run('LC_ALL=C.UTF-8 "{}" --expect-utf8locale 1'.format(exe), env="conanrun")
        self.run(
            'LC_ALL=en_US.UTF-8 "{}" --expect-utf8locale 1'.format(exe), env="conanrun"
        )
