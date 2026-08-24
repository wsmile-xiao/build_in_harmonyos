import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get


class ColoramaConan(ConanFile):
    name = "colorama"
    version = "0.4.6"
    package_type = "python-require"
    license = "BSD-3-Clause"
    homepage = "https://github.com/tartley/colorama"
    description = ("Cross-platform colored terminal text — awscli "
                   "dependency chain L1 (pure Python, zero deps)")
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"
    # 零依赖（PyPI requires_dist 核验：None）

    def source(self):
        get(self, **self.conan_data["sources"]["colorama"],
            strip_root=True)

    def build(self):
        # pip metadata 构建在 CI 不可靠——copytree 源码到 staging
        # （**源外**目录——build 内 staging 递归复制教训）——纯 Python
        staging = "/data/storage/el2/base/cache/colorama-stage"
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder, staging,
            ignore=shutil.ignore_patterns(
                "*.egg-info", "setup.py", "setup.cfg",
                "pyproject.toml", "README*", "LICENSE*", "test*",
                "CHANGELOG*", "MANIFEST*", ".git"))

    def package(self):
        staging = "/data/storage/el2/base/cache/colorama-stage"
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        pyver = "python3.12"
        site = os.path.join(self.package_folder, "lib", pyver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        # colorama 是顶层包布局——复制包目录（排除包内 tests/ 子目录）
        src_pkg = os.path.join(staging, "colorama")
        if not os.path.isdir(src_pkg):
            raise ConanException("colorama package missing in staging")
        dst_pkg = os.path.join(site, "colorama")
        shutil.copytree(
            src_pkg, dst_pkg,
            ignore=shutil.ignore_patterns("tests", "__pycache__"))

    def package_info(self):
        # python-require 类型——runtime 环境由 conanrun 提供
        self.cpp_info.libs = []
