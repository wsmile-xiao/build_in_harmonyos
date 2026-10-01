#!/usr/bin/env python3
"""Conan test_package — kamailio-cpl L1 消费者视角测试。

cplc.so 由 kamailio 运行时 loadmodule 加载（cpl_init 要求 DB 绑定与 TM API，
需完整 kamailio 核心运行时），故消费者视角验证分两层：

  1) check_cplc.py         产物结构/平台合规：ELF aarch64、模块契约符号 exports、
                           NEEDED(libxml2/libc)、无 RPATH 泄漏、随包 cpl-06.dtd 与
                           许可证、模块内嵌的导出命令/参数契约名。
  2) check_cplc_runtime.py 运行时行为（OHOS 原生执行）：
                           a) 以 core 符号桩注入后真实 dlopen cplc.so，并解析
                              exports.name == "cplc"（loadmodule 契约）；
                           b) 以模块 cpl_parser.c 完全同一的 libxml2 API 路径
                              （xmlParseDTD / xmlParseDoc / xmlValidateDtd）校验
                              随包 cpl-06.dtd：合法脚本通过、非法脚本被拒。
"""
import os
import sys

from conan import ConanFile
from conan.tools.env import Environment


class KamailioCplTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 运行时用例直接用 libxml2 校验 CPL DTD（模块 cpl_parser.c 同 API），
        # 显式声明以保证 conanrun 运行时环境提供 libxml2.so.16。
        self.requires("libxml2/2.15.3.1")

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        modules_dir = os.path.join(package_folder, "lib", "kamailio", "modules")
        module = os.path.join(modules_dir, "cplc.so")
        dtd = os.path.join(modules_dir, "cpl-06.dtd")
        assert os.path.isfile(module), f"cplc.so not found at {module}"
        self.output.info(f"cplc.so found: {module}")

        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c") or "clang"

        env = Environment()
        env.define("KAMAILIO_CPL_MODULE", module)
        env.define("KAMAILIO_CPL_PACKAGE_FOLDER", package_folder)
        with env.vars(self).apply():
            self.run(f'"{sys.executable}" '
                     f'"{os.path.join(self.source_folder, "check_cplc.py")}"')

        self.run(f'"{sys.executable}" '
                 f'"{os.path.join(self.source_folder, "check_cplc_runtime.py")}" '
                 f'"{module}" "{dtd}" '
                 f'"{os.path.join(self.source_folder, "cpl", "valid_script.xml")}" '
                 f'"{os.path.join(self.source_folder, "cpl", "invalid_script.xml")}" '
                 f'"{cc}"', env="conanrun")
