#!/usr/bin/env python3
"""Conan test_package for ccapi 7.10.1 — 消费测试验证 header-only 库。

用法: python3 test_ccapi.py <package_folder> <deps_include_dir1> ... --lib <openssl_libdir>
"""
from conan import ConanFile


class CcapiTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    requires = "openssl/3.5.6", "boost/1.90.0", "rapidjson/1.1.0"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 脚本与配方同目录（build_folder 即归档 test_package 目录）——
        # 直接运行，不做 copy（避免 test_package/test_package/ 嵌套污染）
        pkg_folder = self.dependencies["ccapi"].package_folder
        # airview P3：编译命令携带全部依赖搜索路径（与真实消费者一致）
        # ——include 目录（openssl/boost/rapidjson）+ openssl lib 目录
        inc_dirs = []
        for dep_name in ("openssl", "boost", "rapidjson"):
            dep = self.dependencies[dep_name]
            if dep.cpp_info.includedirs:
                inc_dirs.extend(dep.cpp_info.includedirs)
        # openssl libdir（-lssl -lcrypto 链接需要）
        openssl_lib = ""
        ossl = self.dependencies["openssl"]
        if ossl.cpp_info.libdirs:
            openssl_lib = ossl.cpp_info.libdirs[0]
        args = [pkg_folder] + inc_dirs + ["--lib", openssl_lib]
        quoted = " ".join('"%s"' % a for a in args)
        self.run("python3 test_ccapi.py %s" % quoted, env="conanrun")
