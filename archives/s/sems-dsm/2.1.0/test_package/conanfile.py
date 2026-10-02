#!/usr/bin/env python3
"""Conan test_package — sems-dsm 鸿蒙特有消费者测试 (L1 + 鸿蒙 dlopen 用例)。

CI 通过 conan create 自动调用。test() 将插件 dsm.so 路径与随包 DSM 示例
图表路径注入环境变量，测试程序 dlopen 加载 + amci_exports 符号契约校验
+ 示例图表语法标记校验（真实消费，非纯断言空壳）。
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class SemsdsmTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # 显式以绝对路径注入 core/sip 静态库，供 CMakeLists 的
        # -Wl,--whole-archive 全量收录（INTERFACE 目标无法被包裹）；
        # libsems_sip.a 引用 libevent 符号（event_base_dispatch 等），
        # 静态 libevent 一并注入链接序
        dep = self.dependencies["sems-dsm"]
        libdir = dep.cpp_info.libdirs[0]
        lev = self.dependencies["libevent"]
        lev_libs = [os.path.join(lev.cpp_info.libdirs[0], f"libevent{suffix}.a")
                    for suffix in ("", "_core", "_extra", "_pthreads")]
        lev_libs = [p for p in lev_libs if os.path.exists(p)]
        cmake = CMake(self)
        cmake.configure(variables={"SEMS_CORE_A": f"{libdir}/libsems_core.a",
                                   "SEMS_SIP_A": f"{libdir}/libsems_sip.a",
                                   # CMake 列表语义：分号分隔，展开为多个链接项
                                   "LIBEVENT_A": ";".join(lev_libs),
                                   "SEMS_RESAMPLE_SRC": os.path.join(
                                       dep.package_folder, "share", "sems",
                                       "src", "resample")})
        cmake.build()

    def test(self):
        dep = self.dependencies["sems-dsm"]
        # ① 上游测试（R51/rule4 真实执行）：运行随包分发的 sems_tests
        #    （fct.h 单体程序，core/tests 10 个测试源文件编译而成，
        #    ctest 注册 1 项，内部 204 个断言级子测试——sems-opus 同源实证）
        sems_tests = os.path.join(dep.cpp_info.bindirs[0], "sems_tests")
        if not os.path.exists(sems_tests):
            import glob as _g
            cands = _g.glob(os.path.join(dep.package_folder, "**", "sems_tests"),
                            recursive=True)
            sems_tests = cands[0] if cands else sems_tests
        self.run(sems_tests, env="conanrun")
        # ② 鸿蒙特有消费者测试：dlopen 加载插件 + plugin_class_create 契约
        #    + DSM 图表语法校验
        plugin = os.path.join(dep.cpp_info.libdirs[0], "sems", "plug-in", "dsm.so")
        if not os.path.exists(plugin):
            cands = glob.glob(os.path.join(dep.package_folder, "**", "dsm.so"),
                              recursive=True)
            plugin = cands[0] if cands else plugin
        # 随包 DSM 状态机图表（apps/dsm/lib/*.dsm，消费者语义验证输入）
        chart = os.path.join(dep.package_folder, "share", "sems", "dsm", "charts")
        charts = sorted(glob.glob(os.path.join(chart, "*.dsm")))
        chart_path = charts[0] if charts else ""
        # whole-archive 宿主传递链接 libevent 等共享依赖：显式注入全部
        # 依赖包 libdir（conanrun 环境外兜底，musl 无 rpath 场景）
        libdirs = []
        for d in self.dependencies.values():
            libdirs.extend(d.cpp_info.libdirs)
        env = (f"SEMS_DSM_PLUGIN={plugin} SEMS_DSM_EXAMPLE={chart_path} "
               f"LD_LIBRARY_PATH={':'.join(libdirs)}:$LD_LIBRARY_PATH")
        self.run(f"{env} {os.path.join(self.cpp.build.bindirs[0], 'test_sems-dsm')}",
                 env="conanrun")
