#!/usr/bin/env python3
"""db5.3 5.3.28 test_package —— 真实消费者（只用交付物）。

① C API 消费者用例（rule12 端到端业务流程）：test_db5.c 用交付的
   include/db.h + libdb-5.3.so（经 CMakeDeps 的 db5_3::db5_3 链接）跑
   事务型环境 → 事务提交写入 → 读回逐条比对 → 游标全量遍历（条数+键序）
   → 事务内删除 → 事务回滚（写入必须消失），共 14 项可核对结果。
② CLI 端到端链路：test_cli.py 用交付的 db_load 装载文本数据 → db_dump -p
   逐行比对 → db_stat -d 条数比对 → db_verify 必须成功；另有 4 条负例
   （损坏文件 / 非 DB 文件 / 不存在的目录 / hash 访问方法），共 15 项。
③ 适配自检（M）：test_layout.py 检查交付形态（库/头/14 个工具/许可/纯净性）。
④ 上游测试在 build() 里真跑（CuTest + test/tcl/test.tcl 驱动），见 conanfile.py
   与 manifest.yaml。

L1e 依据：本测试真依赖被测包——CI 把 lib/、include/ 移走后重跑 conan test 时，
C 部分编译必然失败、CLI 部分动态加载 libdb-5.3.so 也必然失败。
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout


class Db53TestConan(ConanFile):
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
        pkg = self.dependencies["db5.3"].package_folder
        if cross_building(self):
            self.output.info("cross-building：跳过宿主二进制的执行，只做交付形态自检")
        else:
            binary = os.path.join(self.cpp.build.bindirs[0], "test_db5")
            self.run(binary, env="conanrun")
            cli = os.path.join(self.source_folder, "test_cli.py")
            self.run("%s %s %s" % (sys.executable, cli, pkg), env="conanrun")
        layout = os.path.join(self.source_folder, "test_layout.py")
        self.run("%s %s %s" % (sys.executable, layout, pkg))
