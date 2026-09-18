#!/usr/bin/env python3
"""Conan test_package — libloc-database 0-20260628-0345（数据包消费侧校验）。

数据包没有可执行产物，唯一的"消费"行为就是打开安装后的数据库。
因此 test() 调起 test_database.py，用消费者视角校验安装结果：
数据库是否存在、字节数/SHA256 是否与上游发布物一致、DB 魔数与头部
时间戳是否指向 2026-06-28 版本（等价于 libloc 库打开数据库时的校验）。
"""
import os

from conan import ConanFile


class LiblocDatabaseTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["libloc-database"]
        script = os.path.join(self.recipe_folder, "test_database.py")
        self.run(f'python3 "{script}" "{dep.package_folder}"')
