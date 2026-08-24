import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get


class PythonDidlLiteConan(ConanFile):
    name = "python-didl-lite"
    version = "1.5.0"
    package_type = "python-require"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"
    # 运行时依赖（PyPI requires_dist 核验：defusedxml>=0.6.0——已发布
    # ohpcd 制品仓 defusedxml/0.7.1；pytest 仅 test extra 不打包）
    requires = "defusedxml/0.7.1"

    def source(self):
        get(self, **self.conan_data["sources"]["python-didl-lite"],
            strip_root=True)

    def build(self):
        # pip metadata 构建在 CI 不可靠（confspirator/toml/rfc3986 教训）
        # ——copytree 源码到 staging（**源外**目录——build 内 staging 在
        # source 下会递归复制自己）——Python 包源码直接复制，零编译
        staging = "/data/storage/el2/base/cache/didl-stage"
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder, staging,
            ignore=shutil.ignore_patterns(
                "*.egg-info", "setup.py", "setup.cfg",
                "pyproject.toml", "README*", "LICENSE*", "test*",
                "CHANGELOG*", "MANIFEST*", ".git"))

    def package(self):
        staging = "/data/storage/el2/base/cache/didl-stage"
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        pyver = "python3.12"
        site = os.path.join(self.package_folder, "lib", pyver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        # didl_lite 是顶层包布局（sdist 根 didl_lite/）——直接复制包目录
        shutil.copytree(os.path.join(staging, "didl_lite"),
                        os.path.join(site, "didl_lite"))

    def package_info(self):
        # python-require 类型——runtime 环境由 conanrun 提供
        self.cpp_info.libs = []
