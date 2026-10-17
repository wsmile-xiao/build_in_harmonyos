#!/usr/bin/env python3
"""Conan recipe — importmagic 0.1.7 (pysetuptools, 纯 Python, 鸿蒙 PC 真机原生编译)

鸿蒙适配说明：
- 纯 Python 项目，无需 C 编译器
- 使用 pip install --no-deps 安装，跳过依赖检查
- 通过 python3 -c "import importmagic" 验证安装
"""
import os
import sys

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches


class ImportmagicConan(ConanFile):
    name = "importmagic"
    version = "0.1.7"
    description = "Python Import Magic - automagically add, remove and manage imports"
    license = "BSD"
    homepage = "https://github.com/alecthomas/importmagic"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 修复 Python 3.12+ 兼容性：distutils 已移除，替换为 sysconfig 兼容层
        index_py = os.path.join(self.source_folder, "importmagic", "index.py")
        if os.path.exists(index_py):
            with open(index_py) as f:
                content = f.read()
            # 用 sysconfig 兼容层替换 distutils.sysconfig
            compat_shim = """\
import sysconfig as _sysconfig
def _get_python_lib(*, standard_lib=False, plat_specific=False, prefix=None):
    kw = {}
    if prefix:
        kw['prefix'] = prefix
    if standard_lib:
        return _sysconfig.get_path('stdlib', vars=kw) if kw else _sysconfig.get_path('stdlib')
    elif plat_specific:
        return _sysconfig.get_path('platlib', vars=kw) if kw else _sysconfig.get_path('platlib')
    return _sysconfig.get_path('purelib', vars=kw) if kw else _sysconfig.get_path('purelib')
sysconfig = type(sys)('sysconfig')
sysconfig.get_python_lib = _get_python_lib
"""
            content = content.replace(
                "from distutils import sysconfig",
                compat_shim
            )
            with open(index_py, "w") as f:
                f.write(content)
            self.output.info("distutils.sysconfig fix applied (Python 3.12+ compat)")

    def build(self):
        apply_conandata_patches(self)
        # 纯 Python 项目：用 pip 安装到 build 目录
        self.run(f'python3 -m pip install --no-deps --prefix="{self.build_folder}" .')

    def package(self):
        self.run(f'python3 -m pip install --no-deps --prefix="{self.package_folder}" .')

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # 纯 Python 包不需要设置 builddirs
