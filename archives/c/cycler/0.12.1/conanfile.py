import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get


class CyclerConan(ConanFile):
    name = "cycler"
    version = "0.12.1"
    package_type = "python-require"
    license = "BSD-3-Clause"
    homepage = "https://github.com/matplotlib/cycler"
    description = ("cycler — composable style cycles (pure Python, "
                   "zero runtime deps — matplotlib dependency)")
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"
    # PyPI requires_dist 核验：全部为 docs/tests extra（ipython/matplotlib/
    # pytest 等），运行时零依赖
    requires = []

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # pip metadata 构建在 CI 不可靠——copytree 源码到 staging
        # （**源外**目录——build 内 staging 递归复制教训）——纯 Python
        staging = "/data/storage/el2/base/cache/cycler-stage"
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder, staging,
            ignore=shutil.ignore_patterns(
                "*.egg-info", "setup.py", "setup.cfg",
                "pyproject.toml", "README*", "LICENSE*", "test*",
                "docs", "Makefile", "MANIFEST*", ".git", ".github"))

    def package(self):
        staging = "/data/storage/el2/base/cache/cycler-stage"
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        pyver = "python3.12"
        site = os.path.join(self.package_folder, "lib", pyver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        # cycler 顶层普通 layout（sdist 顶层 cycler/——非 src/——tar tzf
        # 核验确认）——复制 cycler/ 到 site-packages
        src_pkg = os.path.join(staging, "cycler")
        if not os.path.isdir(src_pkg):
            raise ConanException(f"cycler package missing: {src_pkg}")
        shutil.copytree(
            src_pkg, os.path.join(site, "cycler"),
            ignore=shutil.ignore_patterns("__pycache__"))

    def package_info(self):
        # python-require 类型——runtime 环境由 conanrun 提供
        self.cpp_info.libs = []
