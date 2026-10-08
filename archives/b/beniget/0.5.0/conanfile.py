import json
import os
import re
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import download

# 平台 pip 镜像（与 CI 一致，见 ci/conan/setup.sh:55 PIP_COMMUNITY_INDEX）
PIP_INDEX = "https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple"
# 上游测试期依赖：CI 的 hnp python3 不自带 pytest（实测 `No module named
# pytest`），ohpcd 亦无制品 → 构建期从平台 pip 镜像取（cffi/chardet 先例）。
UPSTREAM_TEST_REQUIRES = ("pytest>=7",)


class BenigetConan(ConanFile):
    name = "beniget"
    version = "0.5.0"
    package_type = "python-require"
    license = "BSD-3-Clause"
    homepage = "https://github.com/serge-sans-paille/beniget"
    description = ("beniget — extract semantic information about static Python "
                   "code (def-use chains over gast AST; pythran dependency)")
    settings = "os", "arch", "compiler", "build_type"
    # 纯 Python noarch——无 C/C++ 编译（实测 beniget/ 下仅 4 个 .py）

    def requirements(self):
        # 上游 requirements.txt 的唯一硬依赖：gast >= 0.7.0
        self.requires("gast/0.7.0")

    def _pip_install(self, py, target, requirements):
        """从平台 pip 镜像装依赖到 target（失败即抛错，不静默降级）。"""
        import subprocess
        cmd = [py, "-m", "pip", "install", "--target", target,
               "--break-system-packages", "--disable-pip-version-check",
               "--timeout", "120", "--retries", "3",
               "--index-url", PIP_INDEX, *requirements]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        if res.returncode != 0:
            tail = "\n".join(((res.stdout or "") + (res.stderr or ""))
                             .strip().splitlines()[-12:])
            raise ConanException(
                "could not obtain the test dependency (pytest) from the "
                "platform pip mirror, so the upstream suite could not be run "
                "(R51: refusing to report an unrun suite as passing). "
                "Tail:\n%s" % tail)

    def _test_requires_dir(self, py):
        """构建期 pytest 目录（ohpcd 无制品，pip 镜像引导）。

        用**将运行测试的那个解释器**装，避免 ABI/版本错配。
        """
        d = os.path.join(self.build_folder, "pytest-reqs")
        if not os.path.isdir(os.path.join(d, "pytest")):
            os.makedirs(d, exist_ok=True)
            self._pip_install(py, d, UPSTREAM_TEST_REQUIRES)
        return d

    def source(self):
        download(self, self.conan_data["sources"]["url"], "beniget-0.5.0.tar.gz",
                 sha256=self.conan_data["sources"]["sha256"])
        # --no-same-owner: hmdfs 上归档属主与构建 UID 不一致（同 packaging）
        self.run("tar -xzf beniget-0.5.0.tar.gz --no-same-owner || true")
        self.run("cp -a beniget-0.5.0/. . && rm -rf beniget-0.5.0")

    def build(self):
        # 上游测试（tests/，pytest 风格，实测 562 例）——真实执行并如实上报
        if not can_run(self):
            return
        tests_dir = os.path.join(self.source_folder, "tests")
        if not os.path.isdir(tests_dir):
            self.output.warning("[beniget] upstream tests/ absent — suite "
                                "cannot be run")
            return
        import subprocess
        py = "/data/service/hnp/bin/python3" \
            if os.path.isfile("/data/service/hnp/bin/python3") else sys.executable
        env = dict(os.environ)
        paths = [self.source_folder]
        # beniget 运行期 import gast（AST 抽象层）——缺它即 ModuleNotFoundError
        try:
            paths.append(os.path.join(
                self.dependencies["gast"].package_folder,
                "lib", "python3.12", "site-packages"))
        except Exception as exc:
            self.output.warning("[beniget] gast path unavailable: %s" % exc)
        # pytest 非 CI 镜像自带（实测 `No module named pytest`）→ 平台 pip 装
        paths.insert(0, self._test_requires_dir(py))
        if env.get("PYTHONPATH"):
            paths.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(paths)
        # TMPDIR 可能只读（HMBS readonly_tmp）→ 统一走构建目录内 tmp
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        for v in ("TMPDIR", "TMP", "TEMP"):
            env.setdefault(v, tmp)
        r = subprocess.run(
            [py, "-m", "pytest", "tests", "-q", "--no-header",
             "-p", "no:cacheprovider", "--assert=plain", "-rs",
             "--basetemp=" + os.path.join(tmp, "pytest-bt")],
            cwd=self.source_folder, capture_output=True, text=True, env=env,
            timeout=1800)
        out = r.stdout + r.stderr
        print("[beniget upstream tests] pytest rc=%d" % r.returncode)
        for line in out.splitlines()[-25:]:
            print("[beniget upstream tests]", line)
        marker = {"status": "passed" if r.returncode == 0 else "failed",
                  "framework": "pytest", "command": "python -m pytest tests -q",
                  "discovered": 0, "executed": 0, "passed": 0,
                  "failed": 0, "skipped": 0}
        marker.update(self._parse_pytest_summary(out))
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=%s"
                         % json.dumps(marker, ensure_ascii=False))
        self._upstream_marker = marker

    @staticmethod
    def _parse_pytest_summary(out):
        """解析 pytest 收尾统计行（如 `562 passed in 1.88s`）。"""
        for line in reversed(out.splitlines()):
            nums = dict((w, int(n)) for n, w in re.findall(
                r"(\d+)\s+(passed|failed|skipped|error|errors|xfailed|xpassed)",
                line))
            if ("passed" in nums or "failed" in nums
                    or "error" in nums or "errors" in nums):
                passed = nums.get("passed", 0) + nums.get("xpassed", 0)
                failed = (nums.get("failed", 0) + nums.get("error", 0)
                          + nums.get("errors", 0))
                skipped = nums.get("skipped", 0) + nums.get("xfailed", 0)
                return {"discovered": passed + failed + skipped,
                        "executed": passed + failed,
                        "passed": passed, "failed": failed,
                        "skipped": skipped}
        return {}

    def package(self):
        # 纯 Python noarch——拷贝 beniget/ 包到 site-packages
        # （绕过 pip/setuptools 构建——同 packaging/cloudpickle）
        site = os.path.join(self.package_folder, "lib", "python3.12",
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        shutil.copytree(os.path.join(self.source_folder, "beniget"),
                        os.path.join(site, "beniget"), dirs_exist_ok=True)
        # 上游测试结果 marker 随包交付，供 test_package 复发
        marker = getattr(self, "_upstream_marker", None)
        if marker:
            import json
            dest = os.path.join(self.package_folder, "res",
                                "upstream_test_result.json")
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "w", encoding="utf-8") as fh:
                json.dump(marker, fh, ensure_ascii=False, indent=2)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        site = os.path.join(self.package_folder, "lib", "python3.12",
                            "site-packages")
        # Conan 2 的 runenv_info（不是 1.x 的 env_info——后者只告警不生效）
        self.runenv_info.append_path("PYTHONPATH", site)
        # gast 的 package_info 不暴露 PYTHONPATH，而 beniget 运行期要 import 它
        try:
            self.runenv_info.append_path(
                "PYTHONPATH",
                os.path.join(self.dependencies["gast"].package_folder,
                             "lib", "python3.12", "site-packages"))
        except Exception as exc:
            self.output.warning("[beniget] cannot propagate gast PYTHONPATH: %s"
                                % exc)
