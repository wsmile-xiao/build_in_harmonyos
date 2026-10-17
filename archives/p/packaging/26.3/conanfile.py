import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import download


class PackagingConan(ConanFile):
    name = "packaging"
    version = "26.3"
    package_type = "python-require"
    license = "Apache-2.0 OR BSD-2-Clause"
    homepage = "https://github.com/pypa/packaging"
    description = ("packaging — Core utilities for Python packages "
                   "(versions, specifiers, markers, requirements, tags)")
    settings = "os", "arch", "compiler", "build_type"
    # 纯 Python noarch——无 C/C++ 编译

    def source(self):
        download(self, self.conan_data["sources"]["url"],
                 "packaging-26.3.tar.gz",
                 sha256=self.conan_data["sources"]["sha256"])
        self.run("tar -xzf packaging-26.3.tar.gz --no-same-owner || true")
        self.run("cp -a packaging-26.3/. . && rm -rf packaging-26.3")

    def build(self):
        # 上游测试（tests/ pytest 套件——31 个 test_*.py 文件）——
        # 实测并回填通过率（rule 4：本地实测真实用例数，不伪造）
        if can_run(self):
            import sys
            import subprocess
            py = "/data/service/hnp/bin/python3" \
                if os.path.isfile("/data/service/hnp/bin/python3") \
                else sys.executable
            test_dir = os.path.join(self.source_folder, "tests")
            src_dir = os.path.join(self.source_folder, "src")
            # 关键环境处理：
            # 1) filterwarnings=error 与 pytest 9.x 的
            #    PytestRemovedIn10Warning 冲突——--override-ini 覆盖
            #    （上游 pytest>=6.2，OHOS Python 3.12 用 9.x）
            # 2) tmp_path fixture 属主异常——--basetemp 可写目录
            #    （同 aiohttp/python-dotenv 教训）
            # 3) property 标记测试 opt-in（上游 addopts 默认 -m "not
            #    property"）——同样排除（427 deselected）
            # 4) 测试依赖 pretend/tomli_w/hypothesis 需安装（本地 pip
            #    装；CI 上配方内不装——测试数字以本地实测为准，如实
            #    记录；跳过项 requires a glibc-based Linux 环境差异）
            # 5) conan 沙箱 PATH 无 python3——绝对路径
            env = dict(os.environ)
            env["PYTHONPATH"] = src_dir
            r = subprocess.run(
                [py, "-m", "pytest", test_dir, "-q", "--no-header",
                 "-p", "no:cacheprovider", "--override-ini=filterwarnings=",
                 "-m", "not property",
                 "--basetemp=/data/storage/el2/base/cache/pkg-bt"],
                capture_output=True, text=True, env=env, timeout=1800)
            out = (r.stdout + r.stderr)
            print("[packaging upstream tests] pytest rc=%d" % r.returncode)
            for line in out.splitlines()[-12:]:
                print("[packaging upstream tests]", line)
            if r.returncode != 0:
                print("[packaging upstream tests] WARN: pytest rc=%d — "
                      "如实记录通过率（构建继续，同 vc 模式）" % r.returncode)

    def package(self):
        # 纯 Python noarch——拷贝 packaging/ 模块（含 py.typed）到
        # site-packages（绕过 pip/setuptools 构建——同 python-magic/rich）
        site = os.path.join(self.package_folder, "lib", "python3.12",
                            "site-packages")
        shutil.copytree(os.path.join(self.source_folder, "src",
                                     "packaging"),
                        os.path.join(site, "packaging"))

    def package_info(self):
        self.cpp_info.libs = []
        self.env_info.PYTHONPATH.append(
            os.path.join(self.package_folder, "lib", "python3.12",
                         "site-packages"))
