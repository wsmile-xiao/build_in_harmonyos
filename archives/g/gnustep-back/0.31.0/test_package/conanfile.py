#!/usr/bin/env python3
"""Conan consumer test for gnustep-back 0.31.0 (headless backend).

不使用 CMake: 本机 OHOS 环境 cmake 启动需系统 libc++_shared.so 而加载失败。
直接调用 clang 编译链接 ObjC 测试程序，与主配方验证过的工具链一致。
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualRunEnv

_OHOS_SYSTEM_LIBDIRS = (
    "/system/lib64",
    "/system/lib64/ndk",
    "/data/storage/el1/bundle/libs/arm64",
)


class GnustepBackTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()

    def _path_of(self, dep, cpp_attr, fallback):
        values = getattr(dep.cpp_info, cpp_attr)
        if values:
            value = values[0]
            if os.path.isabs(value):
                return value
            return os.path.join(dep.package_folder, value)
        return os.path.join(dep.package_folder, fallback)

    def _compiler(self):
        cc = os.environ.get("CC")
        if cc:
            return cc
        cc = shutil.which("clang")
        if cc:
            return cc
        for candidate in ("/data/service/hnp/bin/clang", "/usr/bin/clang"):
            if os.path.exists(candidate):
                return candidate
        raise ConanException(
            "clang compiler not found; set CC env or ensure clang is in PATH")

    def build(self):
        cc = self._compiler()
        include_flags = []
        lib_flags = []
        libs = []
        for _name, dep in self.dependencies.items():
            if not getattr(dep, "package_folder", None):
                continue
            include_flags.append(f"-I{self._path_of(dep, 'includedirs', 'include')}")
            lib_flags.append(f"-L{self._path_of(dep, 'libdirs', 'lib')}")
        # 显式链接: 被测 back 库 + 其依赖链
        libs.extend(["-lgnustep-back", "-lgnustep-gui", "-lgnustep-base",
                     "-lobjc", "-lffi"])
        objc_flags = "-fobjc-runtime=gcc -fblocks -fconstant-string-class=NSConstantString"
        cmd = (
            f'"{cc}" {objc_flags} '
            f'{" ".join(include_flags)} test_gnustep_back.m '
            f'test_support.c '
            f'{" ".join(lib_flags)} '
            f'{" ".join(libs)} -pthread -ldl -lm '
            f'-o test_gnustep_back'
        )
        self.run(cmd)

    def test(self):
        executable = os.path.join(self.build_folder, "test_gnustep_back")
        if not os.path.isfile(executable):
            raise ConanException(
                "test_gnustep_back binary missing after build")
        ld_dirs = []
        for _name, dep in self.dependencies.items():
            if not getattr(dep, "package_folder", None):
                continue
            ld_dirs.append(self._path_of(dep, "libdirs", "lib"))
        ld_dirs += list(_OHOS_SYSTEM_LIBDIRS)
        ld_prefix = 'LD_LIBRARY_PATH="%s" ' % ":".join(ld_dirs)
        self.run(f'{ld_prefix}"{executable}"')