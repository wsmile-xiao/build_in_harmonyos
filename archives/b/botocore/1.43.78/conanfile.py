import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get


class BotocoreConan(ConanFile):
    name = "botocore"
    version = "1.43.78"
    package_type = "python-require"
    license = "Apache-2.0"
    homepage = "https://github.com/boto/botocore"
    description = ("AWS SDK for Python (low-level) — boto3/s3transfer "
                   "dependency chain L1 (pure Python, deps "
                   "jmespath/python-dateutil/urllib3)")
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"
    # PyPI requires_dist 核验：jmespath>=0.7.1,<2 / python-dateutil>=2.1,<3
    # / urllib3>=1.25.4,<3,!=2.2.0（awscrt 为可选 crt extra 不启用——
    # 纯 Python 无 C 扩展）
    # python-dateutil 用 ohpcd/main 的实际版本 2.9.0.post0（2.9.0 不存在
    # ——'not resolved in remotes' 实测）
    requires = "jmespath/1.1.0", "python-dateutil/2.9.0.post0", "urllib3/2.7.0"

    def source(self):
        # CI 的 files.pythonhosted.org 访问极慢（同 numpy #6386——conan
        # 默认 http timeout 内下载不完 16MB——'Read timed out' 实测 #6576）
        # ——http timeout 调大 300s（CI 慢速下载完成）
        self.conf_info.define("core.net.http:timeout", 300)
        get(self, **self.conan_data["sources"]["botocore"],
            strip_root=True)

    def build(self):
        # pip metadata 构建在 CI 不可靠——copytree 源码到 staging
        # （**源外**目录——build 内 staging 递归复制教训）——纯 Python
        staging = "/data/storage/el2/base/cache/botocore-stage"
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder, staging,
            ignore=shutil.ignore_patterns(
                # 注意：不能忽略 "docs"——botocore.docs 是 session import
                # 的模块（botocore/docs/ 子目录——ignore_patterns 的模式
                # 匹配所有层级——'No module named botocore.docs' 实测——
                # 顶层 docs/（README 类）会被复制但无害（package 只复制
                # botocore/）
                "*.egg-info", "setup.py", "setup.cfg",
                "pyproject.toml", "README*", "LICENSE*", "test*",
                "CHANGES*", "MANIFEST*", ".git"))

    def package(self):
        staging = "/data/storage/el2/base/cache/botocore-stage"
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        pyver = "python3.12"
        site = os.path.join(self.package_folder, "lib", pyver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        # botocore 顶层普通 layout（sdist 顶层 botocore/——非 src/——
        # tar tzf 核验确认）——复制 botocore/ 到 site-packages
        src_pkg = os.path.join(staging, "botocore")
        if not os.path.isdir(src_pkg):
            raise ConanException(f"botocore package missing: {src_pkg}")
        shutil.copytree(
            src_pkg, os.path.join(site, "botocore"),
            ignore=shutil.ignore_patterns("__pycache__"))

    def package_info(self):
        # python-require 类型——runtime 环境由 conanrun 提供
        self.cpp_info.libs = []
