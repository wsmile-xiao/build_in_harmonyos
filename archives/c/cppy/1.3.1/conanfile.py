import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class CppyConan(ConanFile):
    name = "cppy"
    version = "1.3.1"
    package_type = "python-require"
    license = "BSD-3-Clause"
    homepage = "https://github.com/nucleic/cppy"
    description = ("cppy — C++ header library for Python C extensions "
                   "(pure Python package, get_include() exposes cppy.h)")
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"
    # PyPI requires_dist 核验：仅 setuptools>=61.2（构建期，Python 自带）
    # ——无运行时外部依赖
    requires = []

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 补丁 0001：cppy/__init__.py 顶层 `from setuptools.command.build_ext
        # import build_ext` 强制依赖 setuptools——CI 沙箱 python3
        # （/data/service/hnp/bin/python3）无 setuptools，import cppy 报
        # "No module named 'setuptools'"（CI #34146 实测）——改为 try/
        # except 可选导入 + CppyBuildExt 继承回退 object，消费者
        # get_include() 不需要 setuptools
        apply_conandata_patches(self)

    def build(self):
        # pip metadata 构建在 CI 不可靠——copytree 源码到 staging
        # （**源外**目录——build 内 staging 递归复制教训）——纯 Python
        staging = "/data/storage/el2/base/cache/cppy-stage"
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder, staging,
            ignore=shutil.ignore_patterns(
                "*.egg-info", "setup.py", "setup.cfg",
                "pyproject.toml", "README*", "LICENSE*", "test*",
                "docs", "Makefile", "MANIFEST*", "CMakeLists.txt",
                "cmake", "releasenotes*", ".git", ".github"))

    def package(self):
        staging = "/data/storage/el2/base/cache/cppy-stage"
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        pyver = "python3.12"
        site = os.path.join(self.package_folder, "lib", pyver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        # cppy 顶层普通 layout（sdist 顶层 cppy/——非 src/——tar tzf
        # 核验确认）——复制 cppy/（含 include/cppy/*.h）到 site-packages
        src_pkg = os.path.join(staging, "cppy")
        if not os.path.isdir(src_pkg):
            raise ConanException(f"cppy package missing: {src_pkg}")
        shutil.copytree(
            src_pkg, os.path.join(site, "cppy"),
            ignore=shutil.ignore_patterns("__pycache__"))

    def package_info(self):
        # python-require 类型——runtime 环境由 conanrun 提供；
        # 头文件在 site-packages/cppy/include/cppy/（get_include() 返回）
        self.cpp_info.libs = []
