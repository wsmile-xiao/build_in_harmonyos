#!/usr/bin/env python3
"""test_package — vdt 0.4.4 消费者验证 + 鸿蒙专项测试。

构建并运行两个独立探针：
- consumer_probe：消费者验证用例——仅使用 vdt 公开头文件与公开 API 编译、
  链接 libvdt.so 并实际运行（模拟业务上层组件的正常消费方式）。
- ohos_special_probe：鸿蒙专项测试——校验 __OHOS__ 平台宏、NEON 向量化
  路径与数组签名导出符号在 OHOS 工具链下实际可用。
"""
import os
import shutil
from conan import ConanFile
from conan.tools.build import cross_building


class VdtTestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["vdt"]
        incs = []
        for p in dep.cpp_info.includedirs:
            incs.append("-I" + os.path.join(dep.package_folder, p) if not os.path.isabs(p) else "-I" + p)
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        libdirs = [os.path.join(dep.package_folder, p) if not os.path.isabs(p) else p
                   for p in libdirs]
        libs = " ".join("-l" + l for l in dep.cpp_info.libs)
        cc = os.environ.get("CXX") or shutil.which("c++") or "clang++"
        inc = " ".join(dict.fromkeys(incs))
        ld = " ".join(["-L" + p for p in dict.fromkeys(libdirs)])
        rpath = " ".join(["-Wl,-rpath," + p for p in dict.fromkeys(libdirs)])
        self.run(f"{cc} -std=c++17 consumer.cpp -o consumer_probe {inc} {ld} {rpath} {libs}")
        self.run(f"{cc} -std=c++17 test_vdt_ohos.cpp -o ohos_special_probe {inc} {ld} {rpath} {libs}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        # 两个探针都用 -Wl,-rpath,<pkg>/lib 链接，且 conanrun 会带出
        # LD_LIBRARY_PATH；因此直接运行即可，不依赖 CI worker 专有的
        # /data/service/hnp/bin/bash（真机上该路径不存在，实测 Error 127）。
        self.run("./consumer_probe", env="conanrun")
        self.run("./ohos_special_probe", env="conanrun")
