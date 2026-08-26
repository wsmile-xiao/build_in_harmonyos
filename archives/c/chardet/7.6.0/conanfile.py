import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get


class ChardetConan(ConanFile):
    name = "chardet"
    version = "7.6.0"
    package_type = "python-require"
    license = "MIT"
    homepage = "https://github.com/chardet/chardet"
    description = ("Universal character encoding detector (pure Python, "
                   "zero deps)")
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"
    # PyPI requires_dist 核验：None（零依赖——纯 Python）

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # pip metadata 构建在 CI 不可靠——copytree 源码到 staging
        # （**源外**目录——build 内 staging 递归复制教训）——纯 Python
        staging = "/data/storage/el2/base/cache/chardet-stage"
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder, staging,
            ignore=shutil.ignore_patterns(
                "*.egg-info", "setup.py", "setup.cfg",
                "pyproject.toml", "README*", "LICENSE*", "test*",
                "docs", "scripts", "hatch_build_cython.py", "prek.toml",
                "CLAUDE.md", "CONTEXT.md", ".git"))

    def package(self):
        staging = "/data/storage/el2/base/cache/chardet-stage"
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        pyver = "python3.12"
        site = os.path.join(self.package_folder, "lib", pyver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        # chardet 7.6.0 src 布局（sdist 顶层 src/chardet/——非顶层——
        # tar tzf 核验确认）——复制 src/chardet/ 到 site-packages
        src_pkg = os.path.join(staging, "src", "chardet")
        if not os.path.isdir(src_pkg):
            raise ConanException(f"chardet package missing: {src_pkg}")
        shutil.copytree(
            src_pkg, os.path.join(site, "chardet"),
            ignore=shutil.ignore_patterns("__pycache__"))

    def package_info(self):
        # python-require 类型——runtime 环境由 conanrun 提供
        self.cpp_info.libs = []
