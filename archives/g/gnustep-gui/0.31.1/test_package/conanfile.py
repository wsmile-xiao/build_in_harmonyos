#!/usr/bin/env python3
"""Conan consumer test for gnustep-gui 0.31.1.

不使用 CMake: 本机 OHOS 环境 /data/service/hnp/bin/cmake 启动时需要系统
libc++_shared.so, 在干净 conan 构建环境中加载失败 (Error relocating)。
直接调用 clang 编译链接 ObjC 测试程序, 与主配方验证过的工具链一致。
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualRunEnv

# OHOS 系统运行库目录（本平台硬编码，来源: OHOS NDK 默认安装布局），
# 与主配方 conanfile.py 中 _OHOS_SYSTEM_LIBDIRS 保持一致。
_OHOS_SYSTEM_LIBDIRS = (
    "/system/lib64",
    "/system/lib64/ndk",
    "/data/storage/el1/bundle/libs/arm64",
)


class GnustepGuiTestConan(ConanFile):
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
        """解析编译器可执行文件（R33: 不硬编码单个绝对路径）。

        本机 OHOS 适配版 Conan 的 conf 白名单不含 tools.build:compiler_executable
        （直接 conf.get 会抛 'does not exist in configuration list'），故：
        1) 优先取环境变量 CC（AutotoolsToolchain/工具链注入）；
        2) 其次在 PATH 中探测 clang（CI 上 make 即以 clang 调用）；
        3) 再按候选路径探测（与 _resolve_shell 相同的 OHOS worker 兜底）；
        4) 均缺失时显式报错，不静默回退。
        """
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
            f'{" ".join(include_flags)} test_gnustep_gui.m gsbackend_stub.m '
            f'test_support.c '
            f'{" ".join(lib_flags)} '
            f'-lgnustep-gui -lgnustep-base -lobjc -lffi -pthread -ldl -lm '
            f'-o test_gnustep_gui'
        )
        self.run(cmd)

    def test(self):
        executable = os.path.join(self.build_folder, "test_gnustep_gui")
        if not os.path.isfile(executable):
            # R9 防伪造: 测试二进制缺失属于构建失败, 显式抛错而非静默通过
            raise ConanException(
                "test_gnustep_gui binary missing after build")
        # conanrunenv 的 LD_LIBRARY_PATH 仅含 conan 依赖库目录, 不含系统
        # libc++_shared.so; 显式用命令前缀补全全部依赖库 + 系统库路径
        ld_dirs = []
        for _name, dep in self.dependencies.items():
            if not getattr(dep, "package_folder", None):
                continue
            ld_dirs.append(self._path_of(dep, "libdirs", "lib"))
        ld_dirs += list(_OHOS_SYSTEM_LIBDIRS)
        ld_prefix = 'LD_LIBRARY_PATH="%s" ' % ":".join(ld_dirs)
        self.run(f'{ld_prefix}"{executable}"')
