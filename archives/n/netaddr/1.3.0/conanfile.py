import os
import shutil

from conan import ConanFile
from conan.tools.files import get


class NetaddrConan(ConanFile):
    name = "netaddr"
    version = "1.3.0"
    package_type = "python-require"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"]["netaddr"], strip_root=True)

    def build(self):
        # pip install 的 metadata 构建在 CI 环境不可靠（同 confspirator/
        # toml/rfc3986 教训）——copytree 源码到 staging（**源外**目录——
        # build 内 staging 在 source 下会递归复制自己）——Python 包源码
        # 直接复制，零编译。netaddr/tests 是包内子包（保留——同
        # confspirator.tests 教训）
        staging = "/data/storage/el2/base/cache/netaddr-stage"
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder, staging,
            ignore=shutil.ignore_patterns(
                "*.egg-info", "setup.py", "setup.cfg",
                "pyproject.toml", "README*", "LICENSE*", "tox.ini",
                "docs", ".git"))

    def package(self):
        staging = "/data/storage/el2/base/cache/netaddr-stage"
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        pyver = "python3.12"
        site = os.path.join(self.package_folder, "lib", pyver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        shutil.copytree(os.path.join(staging, "netaddr"),
                        os.path.join(site, "netaddr"))

    def package_info(self):
        # python-require 类型——runtime 环境由 conanrun 提供
        self.cpp_info.libs = []
