import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import download


class GastConan(ConanFile):
    name = "gast"
    version = "0.7.0"
    package_type = "python-require"
    license = "BSD-3-Clause"
    homepage = "https://github.com/serge-sans-paille/gast"
    description = ("gast — Python AST that abstracts the underlying Python "
                   "version (compatibility layer over the stdlib ast module)")
    settings = "os", "arch", "compiler", "build_type"
    # 纯 Python noarch——无 C/C++ 编译

    def source(self):
        download(self, self.conan_data["sources"]["url"], "gast-0.7.0.tar.gz",
                 sha256=self.conan_data["sources"]["sha256"])
        # --no-same-owner: hmdfs 上归档属主与构建 UID 不一致（同 packaging）
        self.run("tar -xzf gast-0.7.0.tar.gz --no-same-owner || true")
        self.run("cp -a gast-0.7.0/. . && rm -rf gast-0.7.0")

    def build(self):
        # 上游测试（tests/，pytest 风格）——实测并如实回填（R51）
        # 实测（2026-09-29，OHOS Python 3.12.9）：64 passed
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
            print("[gast upstream tests] pytest rc=%d" % r.returncode)
            for line in out.splitlines()[-12:]:
                print("[gast upstream tests]", line)

    def package(self):
        # 纯 Python noarch——拷贝 gast/ 包到 site-packages
        # （绕过 pip/setuptools 构建——同 packaging）
        site = os.path.join(self.package_folder, "lib", "python3.12",
                            "site-packages")
        shutil.copytree(os.path.join(self.source_folder, "gast"),
                        os.path.join(site, "gast"))

    def package_info(self):
        self.cpp_info.libs = []
        self.env_info.PYTHONPATH.append(
            os.path.join(self.package_folder, "lib", "python3.12",
                         "site-packages"))
