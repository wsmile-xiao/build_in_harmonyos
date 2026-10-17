"""bobcat test_package：编译并运行真实消费者。

消费者 test_bobcat.cpp 链接 bobcat 包，实质调用 6 个类（Exception/DateTime/
Pattern/String/Glob/Process）的公开 API 并对行为断言（含真实 fork/exec
子进程的 stdout 捕获），非 print-only 空壳测试。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class BobcatTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        bobcat = self.dependencies["bobcat"]
        include_dir = bobcat.cpp_info.includedirs[0]
        lib_dir = bobcat.cpp_info.libdirs[0]
        # 消费者按上游语言要求以 C++20 编译（bobcat 公共头使用 C++20 特性）
        # 注意：Conan 2.29 须先取 dict 再索引（点分子键 get 会抛 ConanException）
        cxx = (
            self.conf.get(
                "tools.build:compiler_executables", {}, check_type=dict
            )
            or {}
        ).get("cpp", "clang++")
        src = os.path.join(self.source_folder, "test_bobcat.cpp")
        exe = os.path.join(self.build_folder, "test_bobcat")
        self.run(
            f"{cxx} --std=c++20 -O1 '{src}' -I'{include_dir}' "
            f"-L'{lib_dir}' -lbobcat -pthread -Wl,-rpath,'{lib_dir}' "
            f"-o '{exe}'"
        )
        self.run(f"'{exe}'", env="conanrun")
