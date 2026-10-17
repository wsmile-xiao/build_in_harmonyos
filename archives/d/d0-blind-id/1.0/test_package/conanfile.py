#!/usr/bin/env python3
"""d0-blind-id 1.0 test_package —— 真实消费者（C，只用交付的库与头）。

① 完整消费者用例（平台 rule12）：test_d0_blind_id.c 用交付的
   libd0_blind_id.so + libd0_rijndael.so 跑
   - **NIST FIPS-197 官方 AES 测试向量**（AES-128/192/256）逐字节比对 + 解密往返；
   - 盲身份协议全流程：RSA 私钥 → 公钥指纹/序列化 → 私有 ID 模数/请求/应答/完成
     → 公钥 ID 交换 → 签名/验签 → 盲身份认证（挑战/应答/验证）→ DH 会话密钥一致；
   - 负例：篡改签名、篡改认证应答必须判为无效。
   共 35 项可核对结果。
② 上游没有测试套件（仓库里只有 main.c 的演示/基准程序），因此 build() 里跑的是
   **上游自带的 blind_id 演示程序**（在它的循环体里跑完同一套协议全流程）——
   这一点在 manifest.yaml / notes.md / PR 描述里如实声明。
③ 适配自检（M）见 test_layout.py。

本测试真依赖被测包：CI 的 L1e 会把 lib/、include/ 移走后重跑 conan test，届时编译
必然失败。
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class D0BlindIdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译 + 链接（原生构建时才跑用例）")
        else:
            binary = os.path.join(self.cpp.build.bindirs[0], "test_d0_blind_id")
            self.run(binary, env="conanrun")
        layout = os.path.join(self.source_folder, "test_layout.py")
        self.run("%s %s %s" % (sys.executable, layout,
                               self.dependencies["d0-blind-id"].package_folder))
