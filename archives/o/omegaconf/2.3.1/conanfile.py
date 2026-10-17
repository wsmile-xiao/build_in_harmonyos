import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get


class OmegaconfConan(ConanFile):
    name = "omegaconf"
    version = "2.3.1"
    package_type = "python-require"
    license = "BSD-3-Clause"
    homepage = "https://github.com/omry/omegaconf"
    description = ("Flexible configuration system for Python — "
                   "antlr4/yaml deps (pure Python, no C extension)")
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"
    # PyPI requires_dist 核验：antlr4-python3-runtime==4.9.* /
    # PyYAML>=5.1.0（dataclasses 仅 py3.6——OHOS 3.12 不需要）——
    # PyYAML 的 conan 包名是 pyyaml（制品仓 pyyaml/6.0.2——非 yaml）
    requires = "antlr4-python3-runtime/4.9.3", "pyyaml/6.0.2"

    def source(self):
        get(self, **self.conan_data["sources"]["omegaconf"],
            strip_root=True)

    def build(self):
        # pip metadata 构建在 CI 不可靠——copytree 源码到 staging
        # （**源外**目录——build 内 staging 递归复制教训）——纯 Python
        staging = "/data/storage/el2/base/cache/omegaconf-stage"
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder, staging,
            ignore=shutil.ignore_patterns(
                "*.egg-info", "setup.py", "setup.cfg",
                "pyproject.toml", "README*", "LICENSE*", "test*",
                "docs", "CHANGES*", "MANIFEST*", ".git"))

    def package(self):
        staging = "/data/storage/el2/base/cache/omegaconf-stage"
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        pyver = "python3.12"
        site = os.path.join(self.package_folder, "lib", pyver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        # omegaconf 顶层普通 layout（sdist 顶层 omegaconf/——非 src/——
        # tar tzf 核验确认）——复制 omegaconf/ 到 site-packages
        src_pkg = os.path.join(staging, "omegaconf")
        if not os.path.isdir(src_pkg):
            raise ConanException(f"omegaconf package missing: {src_pkg}")
        shutil.copytree(
            src_pkg, os.path.join(site, "omegaconf"),
            ignore=shutil.ignore_patterns("__pycache__"))

    def package_info(self):
        # python-require 类型——runtime 环境由 conanrun 提供
        self.cpp_info.libs = []
