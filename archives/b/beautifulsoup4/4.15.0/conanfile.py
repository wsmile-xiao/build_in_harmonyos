import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get


class Beautifulsoup4Conan(ConanFile):
    name = "beautifulsoup4"
    version = "4.15.0"
    package_type = "python-require"
    license = "MIT"
    homepage = "https://www.crummy.com/software/BeautifulSoup/"
    description = ("HTML/XML parser for Python (soupsieve/typing-extensions "
                   "deps — pure Python, no C extension)")
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"
    # PyPI requires_dist 核验：soupsieve>=1.6.1 / typing-extensions>=4.0.0
    # 必需（cchardet/chardet/charset-normalizer/html5lib/lxml 均为可选
    # extra 不启用——纯 Python 无 C 扩展）
    requires = "soupsieve/2.4.1", "typing-extensions/4.16.0"

    def source(self):
        get(self, **self.conan_data["sources"]["beautifulsoup4"],
            strip_root=True)

    def build(self):
        # pip metadata 构建在 CI 不可靠——copytree 源码到 staging
        # （**源外**目录——build 内 staging 递归复制教训）——纯 Python
        staging = "/data/storage/el2/base/cache/bs4-stage"
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder, staging,
            ignore=shutil.ignore_patterns(
                "*.egg-info", "setup.py", "setup.cfg",
                "pyproject.toml", "README*", "LICENSE*", "test*",
                "docs", "CHANGES*", "MANIFEST*", ".git"))

    def package(self):
        staging = "/data/storage/el2/base/cache/bs4-stage"
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        pyver = "python3.12"
        site = os.path.join(self.package_folder, "lib", pyver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        # beautifulsoup4 顶层普通 layout（sdist 顶层 bs4/——非 src/——
        # tar tzf 核验确认）——复制 bs4/ 到 site-packages（tests/ 已被
        # build 的 ignore "test*" 忽略——不打包测试）
        src_pkg = os.path.join(staging, "bs4")
        if not os.path.isdir(src_pkg):
            raise ConanException(f"bs4 package missing: {src_pkg}")
        shutil.copytree(
            src_pkg, os.path.join(site, "bs4"),
            ignore=shutil.ignore_patterns("__pycache__"))

    def package_info(self):
        # python-require 类型——runtime 环境由 conanrun 提供
        self.cpp_info.libs = []
