import os
import shutil

from conan import ConanFile
from conan.tools.files import get


class Rfc3986Conan(ConanFile):
    name = "rfc3986"
    version = "2.0.0"
    package_type = "python-require"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"]["rfc3986"], strip_root=True)

    def build(self):
        # pip install 的 metadata 构建在 CI 环境不可靠（同 confspirator/
        # toml 教训——setup 老配置 + 新 setuptools）——copytree 源码到
        # staging（**源外**目录——build 内 staging 在 source 下会递归复制
        # 自己）——Python 包源码直接复制，零编译
        staging = "/data/storage/el2/base/cache/rfc3986-stage"
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder, staging,
            ignore=shutil.ignore_patterns(
                "*.egg-info", "tests", "setup.py", "setup.cfg",
                "pyproject.toml", "README*", "LICENSE*", "tox.ini",
                ".git"))

    def package(self):
        staging = "/data/storage/el2/base/cache/rfc3986-stage"
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        pyver = "python3.12"
        site = os.path.join(self.package_folder, "lib", pyver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        # rfc3986 是 src layout——包在 staging/src/rfc3986（非顶层）
        shutil.copytree(os.path.join(staging, "src", "rfc3986"),
                        os.path.join(site, "rfc3986"))

    def package_info(self):
        # python-require 类型——runtime 环境由 conanrun 提供
        self.cpp_info.libs = []
