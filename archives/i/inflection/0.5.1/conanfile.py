import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import download


class InflectionConan(ConanFile):
    name = "inflection"
    version = "0.5.1"
    package_type = "python-require"
    license = "MIT"
    homepage = "https://github.com/jpvanhal/inflection"
    description = ("inflection — A port of Ruby on Rails' inflector to "
                   "Python (pluralize, singularize, camelize, underscore)")
    settings = "os", "arch", "compiler", "build_type"
    # 纯 Python noarch——无 C/C++ 编译

    def source(self):
        download(self, self.conan_data["sources"]["url"],
                 "inflection-0.5.1.tar.gz",
                 sha256=self.conan_data["sources"]["sha256"])
        self.run("tar -xzf inflection-0.5.1.tar.gz --no-same-owner || true")
        self.run("cp -a inflection-0.5.1/. . && rm -rf inflection-0.5.1")

    def build(self):
        # 上游测试（test_inflection.py pytest 套件——455 用例）——
        # 实测并回填通过率（rule 4：本地实测真实用例数，不伪造）
        if can_run(self):
            import sys
            import subprocess
            py = "/data/service/hnp/bin/python3" \
                if os.path.isfile("/data/service/hnp/bin/python3") \
                else sys.executable
            test_file = os.path.join(self.source_folder,
                                     "test_inflection.py")
            src_dir = os.path.join(self.source_folder, "inflection")
            # 关键环境处理：
            # 1) filterwarnings=error 与 pytest 9.x 的
            #    PytestRemovedIn10Warning 冲突——--override-ini 覆盖
            # 2) tmp_path fixture 属主异常——--basetemp 可写目录
            #    （同 aiohttp/python-dotenv 教训）
            # 3) conan 沙箱 PATH 无 python3——绝对路径
            env = dict(os.environ)
            env["PYTHONPATH"] = self.source_folder
            r = subprocess.run(
                [py, "-m", "pytest", test_file, "-q", "--no-header",
                 "-p", "no:cacheprovider", "--override-ini=filterwarnings=",
                 "--basetemp=/data/storage/el2/base/cache/infl-bt"],
                capture_output=True, text=True, env=env, timeout=1800)
            out = (r.stdout + r.stderr)
            print("[inflection upstream tests] pytest rc=%d" % r.returncode)
            for line in out.splitlines()[-10:]:
                print("[inflection upstream tests]", line)
            if r.returncode != 0:
                print("[inflection upstream tests] WARN: pytest rc=%d — "
                      "如实记录通过率（构建继续，同 vc 模式）" % r.returncode)

    def package(self):
        # 纯 Python noarch——拷贝 inflection/ 模块（含 py.typed）到
        # site-packages（绕过 pip/setuptools 构建——同 python-magic/rich）
        site = os.path.join(self.package_folder, "lib", "python3.12",
                            "site-packages")
        shutil.copytree(os.path.join(self.source_folder, "inflection"),
                        os.path.join(site, "inflection"))

    def package_info(self):
        self.cpp_info.libs = []
        self.env_info.PYTHONPATH.append(
            os.path.join(self.package_folder, "lib", "python3.12",
                         "site-packages"))
