#!/usr/bin/env python3
"""test_package for telepathy-glib 0.8.1 — R34 实质产物校验 + 鸿蒙（OHOS）适配校验。

- 消费者程序（test_telepathy_glib.c）真实 include 公开头（含 _gen 生成头）并调用
  tp_g_value_slice_new_boolean / tp_strdiff / tp_errors_quark 等纯函数 API；
- 鸿蒙特有用例（≥1）：校验包内共享库为 **aarch64 ELF**（防止宿主/错误架构产物被
  误判为适配成功）+ 校验公开头与 _gen 生成头、pkg-config 元数据齐全。
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class TelepathyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        libdir = os.path.join(pkg, "lib")

        # ---- 鸿蒙（OHOS）适配校验：共享库必须是 aarch64 ELF ----
        so_path = None
        for name in sorted(os.listdir(libdir)):
            path = os.path.join(libdir, name)
            if (name.startswith("libtelepathy-glib.so.")
                    and os.path.isfile(path) and not os.path.islink(path)):
                so_path = path
                break
        assert so_path, "包内缺少 libtelepathy-glib.so.<version> 实体文件"
        with open(so_path, "rb") as fh:
            header = fh.read(20)
        assert header[:4] == b"\x7fELF", "libtelepathy-glib.so 不是 ELF 产物"
        e_machine = int.from_bytes(header[18:20], "little")
        assert e_machine == 0xB7, (
            "OHOS 适配校验失败：期望 aarch64(0xB7) ELF，实际 0x%X" % e_machine)
        self.output.info("OHOS 适配校验：libtelepathy-glib.so 为 aarch64 ELF ✓")

        hdr_dir = os.path.join(pkg, "include", "telepathy-1.0", "telepathy-glib")
        assert os.path.isfile(os.path.join(hdr_dir, "util.h")), "缺少公开头 telepathy-glib/util.h"
        assert os.path.isfile(os.path.join(hdr_dir, "errors.h")), "缺少公开头 telepathy-glib/errors.h"
        assert os.path.isdir(os.path.join(hdr_dir, "_gen")), "缺少 _gen/ 生成头目录（glib-mkenums 产物）"
        assert os.path.isfile(os.path.join(hdr_dir, "_gen", "telepathy-enums.h")), \
            "缺少 _gen/telepathy-enums.h 生成头"
        assert os.path.isfile(os.path.join(pkg, "lib", "pkgconfig", "telepathy-glib.pc")), \
            "缺少 pkg-config 元数据 telepathy-glib.pc"
        self.output.info("OHOS 适配校验：公开头（含 _gen 生成头）与 .pc 元数据齐全 ✓")

        # ---- R34：消费者程序真实链接并调用 API ----
        if not cross_building(self):
            bin_path = os.path.join(self.cpp.build.bindirs[0], "test_telepathy_glib")
            self.run(bin_path, env="conanrun")
