import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get


class UnicryptoConan(ConanFile):
    name = "unicrypto"
    version = "0.0.12"
    package_type = "python-require"
    license = "MIT"
    homepage = "https://github.com/skelsec/unicrypto"
    description = (
        "Unified interface for cryptographic algorithms (AES/DES/TDES/RC4 + "
        "hash/PBKDF2/HMAC/CMAC/KDF) with a self-contained pure-Python backend — "
        "pure-require, no external C-accelerated crypto dependency required")
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"
    # 上游 install_requires 声明 pycryptodomex（可选加速后端）。unicrypto 自带
    # 完整的纯 Python 后端（unricrypto.backends.pure，默认选中），无外部依赖
    # 即可工作 —— 本配方打包纯后端，自包含发布，避免引入 OHOS 未发布且需 C
    # 扩展编译的 pycryptodomex（外部加速后端不可用时回落 pure，功能等价）。

    def source(self):
        get(self, **self.conan_data["sources"]["unicrypto"], strip_root=True)

    def build(self):
        # python-require 零编译：copytree 源码到 staging（源外目录，避免递归
        # 复制自己），剔除构建/测试/文档类文件，纯拷贝安装（同 python-slugify
        # / python-dateutil 先例）。
        staging = "/data/storage/el2/base/cache/unicrypto-stage"
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder, staging,
            ignore=shutil.ignore_patterns(
                "*.egg-info", "setup.py", "setup.cfg",
                "pyproject.toml", "README*", "LICENSE*", "test*", "tests",
                "docs", "MANIFEST*", "PKG-INFO", ".git"))

    def package(self):
        staging = "/data/storage/el2/base/cache/unicrypto-stage"
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        pyver = "python3.12"
        site = os.path.join(self.package_folder, "lib", pyver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        # unicrypto 是顶层包布局（sdist 根 unicrypto/）——直接复制包目录
        src_pkg = os.path.join(staging, "unicrypto")
        if not os.path.isdir(src_pkg):
            raise ConanException(f"unicrypto package missing: {src_pkg}")
        shutil.copytree(
            src_pkg, os.path.join(site, "unicrypto"),
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    def package_info(self):
        # python-require 类型——runtime 环境由 conanrun 提供
        self.cpp_info.libs = []
