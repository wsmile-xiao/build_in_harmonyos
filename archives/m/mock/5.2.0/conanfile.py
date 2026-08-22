import os
import shutil

from conan import ConanFile
from conan.tools.files import get


class MockConan(ConanFile):
    name = "mock"
    version = "5.2.0"
    package_type = "python-require"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"]["mock"], strip_root=True)

    def build(self):
        # pip metadata 构建在 CI 不可靠（confspirator/toml/rfc3986/
        # text-unidecode 教训）——copytree 源码到 staging（**源外**目录）
        # ——Python 包源码直接复制，零编译。
        # mock/tests 是包内子包（保留——同 netaddr.tests 教训）
        staging = "/data/storage/el2/base/cache/mock-stage"
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder, staging,
            ignore=shutil.ignore_patterns(
                "*.egg-info", "setup.py", "setup.cfg",
                "pyproject.toml", "README*", "LICENSE*", "docs",
                ".git"))

    def package(self):
        staging = "/data/storage/el2/base/cache/mock-stage"
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        pyver = "python3.12"
        site = os.path.join(self.package_folder, "lib", pyver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        # mock 包顶层（含 mock/tests 包内子包）
        shutil.copytree(os.path.join(staging, "mock"),
                        os.path.join(site, "mock"))

    def package_info(self):
        # python-require 类型——runtime 环境由 conanrun 提供
        self.cpp_info.libs = []
