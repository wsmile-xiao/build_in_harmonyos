#!/usr/bin/env python3
"""Conan consumer test for GNUstep SQLClient 1.9.0.

直接调用 clang 编译 ObjC 测试程序（与主配方验证过的工具链一致）。
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


class SQLClientTestConan(ConanFile):
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
        for _name, dep in self.dependencies.items():
            if not getattr(dep, "package_folder", None):
                continue
            include_flags.append(f"-I{self._path_of(dep, 'includedirs', 'include')}")
            lib_flags.append(f"-L{self._path_of(dep, 'libdirs', 'lib')}")
        objc_flags = "-fobjc-runtime=gcc -fblocks -fconstant-string-class=NSConstantString"
        cmd = (
            f'"{cc}" {objc_flags} '
            f'{" ".join(include_flags)} test_sqlclient.m '
            f'test_support.c '
            f'{" ".join(lib_flags)} '
            f'-lSQLClient -lgnustep-base -lPerformance -lobjc -lffi '
            f'-pthread -ldl -lm '
            f'-o test_sqlclient'
        )
        self.run(cmd)

    def test(self):
        executable = os.path.join(self.build_folder, "test_sqlclient")
        if not os.path.isfile(executable):
            raise ConanException(
                "test_sqlclient binary missing after build")
        ld_dirs = []
        for _name, dep in self.dependencies.items():
            if not getattr(dep, "package_folder", None):
                continue
            ld_dirs.append(self._path_of(dep, "libdirs", "lib"))
        ld_dirs += list(_OHOS_SYSTEM_LIBDIRS)
        ld_prefix = 'LD_LIBRARY_PATH="%s" ' % ":".join(ld_dirs)
        self.run(f'{ld_prefix}"{executable}"')