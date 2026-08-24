import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get


class Urllib3Conan(ConanFile):
    name = "urllib3"
    version = "2.7.0"
    package_type = "python-require"
    license = "MIT"
    homepage = "https://github.com/urllib3/urllib3"
    description = ("HTTP client library for Python — awscli dependency "
                   "chain L1 (pure Python, zero required deps)")
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"
    # 零必需依赖（PyPI requires_dist 核验：brotli/h2/pysocks/zstd 均
    # 仅 extra 可选，默认不启用）

    def source(self):
        get(self, **self.conan_data["sources"]["urllib3"],
            strip_root=True)

    def build(self):
        # pip metadata 构建在 CI 不可靠——copytree 源码到 staging
        # （**源外**目录——build 内 staging 递归复制教训）——纯 Python
        staging = "/data/storage/el2/base/cache/urllib3-stage"
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder, staging,
            ignore=shutil.ignore_patterns(
                "*.egg-info", "setup.py", "setup.cfg",
                "pyproject.toml", "README*", "LICENSE*", "test*",
                "dummyserver", "docs", "CHANGES*", "uv.lock",
                "MANIFEST*", ".git"))

    def package(self):
        staging = "/data/storage/el2/base/cache/urllib3-stage"
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        pyver = "python3.12"
        site = os.path.join(self.package_folder, "lib", pyver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        # urllib3 2.7.0 是 src layout（sdist 内包位于 src/urllib3/——
        # 实测 staging 里只有 src 子目录）——复制 src/urllib3 到 site-packages
        src_pkg = os.path.join(staging, "src", "urllib3")
        if not os.path.isdir(src_pkg):
            raise ConanException(f"urllib3 package missing: {src_pkg}")
        shutil.copytree(
            src_pkg, os.path.join(site, "urllib3"),
            ignore=shutil.ignore_patterns("test", "__pycache__"))

    def package_info(self):
        # python-require 类型——runtime 环境由 conanrun 提供
        self.cpp_info.libs = []
