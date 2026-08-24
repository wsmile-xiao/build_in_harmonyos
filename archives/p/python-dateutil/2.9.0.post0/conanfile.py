import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get


class PythonDateutilConan(ConanFile):
    name = "python-dateutil"
    version = "2.9.0.post0"
    package_type = "python-require"
    license = "Apache-2.0"
    homepage = "https://github.com/dateutil/dateutil"
    description = ("Date/time utilities for Python — awscli dependency "
                   "chain L1 (pure Python, dep: six)")
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"
    # 运行时依赖 six>=1.5（PyPI requires_dist 核验——已发布 ohpcd 6/1.17.0）
    requires = "six/1.17.0"

    def source(self):
        get(self, **self.conan_data["sources"]["python-dateutil"],
            strip_root=True)

    def build(self):
        # pip metadata 构建在 CI 不可靠——copytree 源码到 staging
        # （**源外**目录——build 内 staging 递归复制教训）——纯 Python
        staging = "/data/storage/el2/base/cache/dateutil-stage"
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder, staging,
            ignore=shutil.ignore_patterns(
                "*.egg-info", "setup.py", "setup.cfg",
                "pyproject.toml", "README*", "LICENSE*", "test*",
                "docs", "AUTHORS*", "CHANGELOG*", "MANIFEST*",
                ".github", ".git", "CODE_OF_CONDUCT*", "CONTRIBUTING*"))

    def package(self):
        staging = "/data/storage/el2/base/cache/dateutil-stage"
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        pyver = "python3.12"
        site = os.path.join(self.package_folder, "lib", pyver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        # dateutil 是 src layout（包位于 src/dateutil/——同 urllib3
        # 教训实测）——复制 src/dateutil 到 site-packages（排除 tests/）
        src_pkg = os.path.join(staging, "src", "dateutil")
        if not os.path.isdir(src_pkg):
            raise ConanException(f"dateutil package missing: {src_pkg}")
        shutil.copytree(
            src_pkg, os.path.join(site, "dateutil"),
            ignore=shutil.ignore_patterns("tests", "__pycache__"))
        # zoneinfo 数据（dateutil 时区库用——上游自带的 tzdata 文件）
        for extra in ("zoneinfo", "zoneinfo_rar.py"):
            src = os.path.join(src_pkg, extra)
            if os.path.exists(src):
                dst = os.path.join(site, "dateutil", extra)
                if os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)

    def package_info(self):
        # python-require 类型——runtime 环境由 conanrun 提供
        self.cpp_info.libs = []
