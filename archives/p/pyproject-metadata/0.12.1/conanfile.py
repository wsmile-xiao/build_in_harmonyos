import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import download


class PyprojectMetadataConan(ConanFile):
    name = "pyproject-metadata"
    version = "0.12.1"
    package_type = "python-require"
    license = "MIT"
    homepage = "https://github.com/pypa/pyproject-metadata"
    description = ("pyproject-metadata — dataclass interface to PEP 621 "
                   "[project] metadata (used by meson-python)")
    settings = "os", "arch", "compiler", "build_type"
    # 纯 Python noarch——无 C/C++ 编译

    def requirements(self):
        # meson-python 的构建期前置；运行时也需要
        self.requires("packaging/26.3")

    def source(self):
        download(self, self.conan_data["sources"]["url"],
                 "pyproject_metadata-0.12.1.tar.gz",
                 sha256=self.conan_data["sources"]["sha256"])
        # --no-same-owner: hmdfs 上归档属主与构建 UID 不一致（同 packaging）
        self.run("tar -xzf pyproject_metadata-0.12.1.tar.gz "
                 "--no-same-owner || true")
        self.run("cp -a pyproject_metadata-0.12.1/. . && "
                 "rm -rf pyproject_metadata-0.12.1")

    def build(self):
        # 上游测试（tests/，pytest 风格）——实测并如实回填（R51）
        #
        # 实测（2026-09-29，OHOS Python 3.12.9）：
        #   318 passed, 88 skipped
        # 跳过项全部同因：exceptiongroup 未安装
        #   （tests/test_standard_metadata.py 的 4 处 SKIP 入口）
        if can_run(self):
            import subprocess
            import sys
            py = "/data/service/hnp/bin/python3" \
                if os.path.isfile("/data/service/hnp/bin/python3") \
                else sys.executable
            src = self.source_folder
            env = dict(os.environ)
            env["PYTHONPATH"] = src
            r = subprocess.run(
                [py, "-m", "pytest", "tests", "-q", "--no-header",
                 "-p", "no:cacheprovider",
                 "--basetemp=/data/storage/el2/base/cache/pkg-bt"],
                cwd=src, capture_output=True, text=True, env=env,
                timeout=1800)
            out = r.stdout + r.stderr
            print("[pyproject-metadata upstream tests] pytest rc=%d"
                  % r.returncode)
            for line in out.splitlines()[-12:]:
                print("[pyproject-metadata upstream tests]", line)

    def package(self):
        # 纯 Python noarch——拷贝 pyproject_metadata/ 包（含 py.typed）到
        # site-packages（绕过 pip/setuptools 构建——同 packaging）
        site = os.path.join(self.package_folder, "lib", "python3.12",
                            "site-packages")
        shutil.copytree(os.path.join(self.source_folder,
                                     "pyproject_metadata"),
                        os.path.join(site, "pyproject_metadata"))

    def package_info(self):
        self.cpp_info.libs = []
        self.env_info.PYTHONPATH.append(
            os.path.join(self.package_folder, "lib", "python3.12",
                         "site-packages"))
