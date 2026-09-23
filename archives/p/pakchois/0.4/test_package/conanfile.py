#!/usr/bin/env python3
"""Conan test_package — pakchois 0.4（dlopen 探针模式）

直接编译 test.c（链接 -ldl），运行期 dlopen 被测包 lib/libpakchois.so 并
dlsym 真实导出符号 pakchois_module_load / pakchois_get_info /
pakchois_module_destroy（R34 反空壳，参照 p11-kit 0.25.5 test_package）。
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building


class PakchoisTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _cc(self):
        # R33: 编译器取自 conan conf（profile tools.build:compiler_executables），
        # 不要裸用 ${CC}。test_package 未用 AutotoolsToolchain，故手动读取。
        compilers = self.conf.get("tools.build:compiler_executables", default={},
                                  check_type=dict)
        cc = compilers.get("c") if compilers else None
        return cc or os.environ.get("CC") or "clang"

    def build(self):
        # 主配方的 os.environ["TMPDIR"] 经 conan create 同进程泄漏到 test_package，
        # 指向主包打包后已被 conan 删除的 build/_tmp；设备 /tmp 又是只读文件系统。
        # 显式指向本包可写 tmp（仓库惯例：celt / p11-kit-server）。
        _tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        dep = self.dependencies["pakchois"].cpp_info
        so = os.path.join(dep.libdirs[0], "libpakchois.so")
        cc = self._cc()
        self.run(f"{cc} test.c -o test_probe {inc} -DTARGET_SO='\"{so}\"' -ldl")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
