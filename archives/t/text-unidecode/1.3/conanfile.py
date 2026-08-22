import os
import shutil

from conan import ConanFile
from conan.tools.files import get


class TextUnidecodeConan(ConanFile):
    name = "text-unidecode"
    version = "1.3"
    package_type = "python-require"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"]["text-unidecode"],
            strip_root=True)

    def build(self):
        # pip metadata 构建在 CI 不可靠（confspirator/toml/rfc3986 教训）
        # ——copytree 源码到 staging（**源外**目录——build 内 staging 在
        # source 下会递归复制自己）——Python 包源码直接复制，零编译
        staging = "/data/storage/el2/base/cache/tud-stage"
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder, staging,
            ignore=shutil.ignore_patterns(
                "*.egg-info", "setup.py", "setup.cfg",
                "pyproject.toml", "README*", "LICENSE*", "test*",
                ".git"))

    def package(self):
        staging = "/data/storage/el2/base/cache/tud-stage"
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        pyver = "python3.12"
        site = os.path.join(self.package_folder, "lib", pyver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        # text-unidecode 是 src layout——包在 staging/src/text_unidecode
        shutil.copytree(os.path.join(staging, "src", "text_unidecode"),
                        os.path.join(site, "text_unidecode"))

    def package_info(self):
        # python-require 类型——runtime 环境由 conanrun 提供
        self.cpp_info.libs = []
