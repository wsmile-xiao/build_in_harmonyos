#!/usr/bin/env python3
"""test_package — mdspan 0.6.0 的真实消费者测试（OHOS aarch64）。

两个可执行（都由 `test()` 里的 `self.run(..., env="conanrun")` 真实执行）：

  1. `consumer`        — 只用**已安装的包**（find_package(mdspan) → std::mdspan）
                         走一遍上游公开 API：静态/动态 extents、layout_left/
                         layout_right/layout_stride、element access、submdspan、
                         mdarray 往返、constexpr 求值；并断言安装头内容指纹与
                         文件数（防「测试靶向文件 ≠ 交付文件」的假绿面）。
  2. `ohos_special_test` — 鸿蒙平台专项（`#ifdef __OHOS__` 真实逻辑，非空壳）：
                         字节序、mdspan ABI（standard layout / trivially copyable /
                         sizeof·alignof）、OHOS 堆上百万级元素视图读写、
                         工具链宏与 libc++ 能力探针。

计数口径与取数命令见同目录 MANIFEST.yml（四口径分列，不与上游分母混用）。
"""
import hashlib
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class MdspanTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # 内容指纹：对**真正被打包的那份** `include/experimental/mdspan` 取
        # sha256，并清点包内 experimental/ 文件数，经 CMake 缓存变量传给
        # consumer 与硬编码的上游源码值比对（§二.19：测试必须指向将安装的
        # 那一份并断言版本宏/内容指纹——本库无版本宏，故用内容指纹）。
        dep = self.dependencies["mdspan"]
        inc_dir = os.path.join(dep.package_folder, "include")
        hdr = os.path.join(inc_dir, "experimental", "mdspan")
        sha = ""
        if os.path.isfile(hdr):
            with open(hdr, "rb") as fh:
                sha = hashlib.sha256(fh.read()).hexdigest()
        n_files = sum(len(files) for _, _, files in os.walk(
            os.path.join(inc_dir, "experimental")))
        tc = CMakeToolchain(self)
        tc.cache_variables["MDSPAN_INSTALLED_HDR_SHA256"] = sha
        tc.cache_variables["MDSPAN_INSTALLED_FILECOUNT"] = n_files
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("can_run=False，跳过消费者执行")
            return
        bindir = self.cpp.build.bindirs[0]
        # 逐个直跑（PF3/R34：test() 必须 self.run 真实执行，非 cmake.test()）
        self.run(f'"{os.path.join(bindir, "consumer")}"', env="conanrun")
        self.run(f'"{os.path.join(bindir, "ohos_special_test")}"', env="conanrun")
