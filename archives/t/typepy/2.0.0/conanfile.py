import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get


class TypepyConan(ConanFile):
    name = "typepy"
    version = "2.0.0"
    package_type = "python-require"
    license = "MIT"
    homepage = "https://github.com/thombashi/typepy"
    description = ("typepy — pytablewriter dependency chain L2 (pure "
                   "Python, deps mbstrdecoder)")
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"
    # PyPI requires_dist 核验：mbstrdecoder<2,>=1.0.0 必需（python-dateutil/
    # packaging 为 datetime/test extra 不启用——纯 Python 无 C 扩展）
    requires = "mbstrdecoder/1.1.5"

    def source(self):
        get(self, **self.conan_data["sources"]["typepy"], strip_root=True)

    def build(self):
        # pip metadata 构建在 CI 不可靠——copytree 源码到 staging
        # （**源外**目录——build 内 staging 递归复制教训）——纯 Python
        staging = "/data/storage/el2/base/cache/typepy-stage"
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder, staging,
            ignore=shutil.ignore_patterns(
                "*.egg-info", "setup.py", "setup.cfg",
                "pyproject.toml", "README*", "LICENSE*", "test*",
                "docs", "make_test_cases.py", "Makefile", "MANIFEST*",
                ".git"))

    def package(self):
        staging = "/data/storage/el2/base/cache/typepy-stage"
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        pyver = "python3.12"
        site = os.path.join(self.package_folder, "lib", pyver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        # typepy 顶层普通 layout（sdist 顶层 typepy/——非 src/——
        # tar tzf 核验确认）——复制 typepy/ 到 site-packages
        src_pkg = os.path.join(staging, "typepy")
        if not os.path.isdir(src_pkg):
            raise ConanException(f"typepy package missing: {src_pkg}")
        shutil.copytree(
            src_pkg, os.path.join(site, "typepy"),
            ignore=shutil.ignore_patterns("__pycache__"))

    def package_info(self):
        # python-require 类型——runtime 环境由 conanrun 提供
        self.cpp_info.libs = []
