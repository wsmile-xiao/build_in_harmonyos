#!/usr/bin/env python3
"""test_package — veccore 0.8.1 消费者验证 + 鸿蒙特有测试。

本包是 header-only，无库可链，因此直接用上真机/CI 的 OHOS clang++ 编译两个
探针并运行（与已合入的 vdt 0.4.4 同一做法）：
- consumer_probe：消费者验证用例，只用公开头 <VecCore/VecCore> 与公开 API。
- ohos_probe：鸿蒙特有测试，校验 __OHOS__/VECCORE_ARM64 平台宏、OHOS libc 的
  posix_memalign 对齐分配，以及 VecCore 后端在 aarch64 上的实际计算路径。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class VeccoreTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv", "VirtualBuildEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _cxx(self):
        executables = self.conf.get("tools.build:compiler_executables", default={},
                                    check_type=dict) or {}
        cxx = executables.get("cpp") or os.environ.get("CXX")
        return (cxx or shutil.which("clang++") or shutil.which("c++")
                or "clang++")

    def build(self):
        pkg = self.dependencies["veccore"]
        includes = " ".join(
            "-I" + (p if os.path.isabs(p) else os.path.join(pkg.package_folder, p))
            for p in pkg.cpp_info.includedirs)
        cxx = self._cxx()
        for source, probe in (("consumer.cpp", "consumer_probe"),
                              ("test_veccore_ohos.cpp", "ohos_probe")):
            self.run("%s -std=c++17 -Wall %s -o %s %s" % (cxx, source, probe, includes),
                     env="conanbuild")

    def test(self):
        if not can_run(self):
            self.output.info("cross-building：只验编译，执行由真机 conan create 覆盖")
            return
        self.run("./consumer_probe", env="conanrun")
        self.run("./ohos_probe", env="conanrun")
