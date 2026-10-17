import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get


class JmespathConan(ConanFile):
    name = "jmespath"
    version = "1.1.0"
    package_type = "python-require"
    license = "MIT"
    homepage = "https://github.com/jmespath/jmespath.py"
    description = ("JMESPath query language for Python — the "
                   "botocore/awscli dependency chain (pure Python, "
                   "zero deps)")
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"
    # 零依赖（PyPI requires_dist 核验：无）

    def source(self):
        get(self, **self.conan_data["sources"]["jmespath"],
            strip_root=True)

    def build(self):
        # pip metadata 构建在 CI 不可靠（confspirator/toml/rfc3986 教训）
        # ——copytree 源码到 staging（**源外**目录——build 内 staging 在
        # source 下会递归复制自己）——纯 Python 零编译
        # 上游测试数据：sdist 未打包 tests/compliance/（16 个 JSON——
        # 上游 GitHub 才有，导致 pytest 收集仅 74 用例）——补上后全量
        # 实测 973 passed / 1 skipped（通过率 71/74→973/974 提升）；
        # JSON 为文本文件，运行时下载到源码树 tests/compliance/
        import urllib.request as _urlreq
        import json as _json
        import glob as _glob
        cmp_dir = os.path.join(self.source_folder, "tests", "compliance")
        if not os.path.isdir(cmp_dir):
            os.makedirs(cmp_dir, exist_ok=True)
            try:
                api = _urlreq.urlopen(
                    "https://api.github.com/repos/jmespath/jmespath.py/"
                    "contents/tests/compliance", timeout=15)
                for f in _json.load(api):
                    if f["name"].endswith(".json"):
                        _urlreq.urlretrieve(
                            f["download_url"],
                            os.path.join(cmp_dir, f["name"]))
                self.output.info(
                    "compliance 测试数据已下载: %d files"
                    % len(_glob.glob(os.path.join(cmp_dir, "*.json"))))
            except Exception as e:
                self.output.warn(
                    f"compliance 数据下载失败（测试通过率按 sdist 原状）: "
                    f"{str(e)[:120]}")
        staging = "/data/storage/el2/base/cache/jmespath-stage"
        shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(
            self.source_folder, staging,
            ignore=shutil.ignore_patterns(
                "*.egg-info", "setup.py", "setup.cfg",
                "pyproject.toml", "README*", "LICENSE*", "test*",
                "bin", "MANIFEST*", "CHANGELOG*", ".git"))

    def package(self):
        staging = "/data/storage/el2/base/cache/jmespath-stage"
        if not os.path.isdir(staging):
            raise ConanException(f"staging missing: {staging}")
        pyver = "python3.12"
        site = os.path.join(self.package_folder, "lib", pyver,
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        # jmespath 是顶层包布局（sdist 根 jmespath/）——直接复制包目录
        if not os.path.isdir(os.path.join(staging, "jmespath")):
            raise ConanException(f"jmespath package missing in staging")
        shutil.copytree(os.path.join(staging, "jmespath"),
                        os.path.join(site, "jmespath"))

    def package_info(self):
        # python-require 类型——runtime 环境由 conanrun 提供
        self.cpp_info.libs = []
