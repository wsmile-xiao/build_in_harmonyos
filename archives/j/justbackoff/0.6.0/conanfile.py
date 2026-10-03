#!/usr/bin/env python3
"""Conan recipe for justbackoff 0.6.0 — "Simple backoff algorithm in Python".

上游：https://github.com/alexferl/justbackoff（历史路径 admiralobvious/justbackoff）
tag `v0.6.0` = commit b8ca3e58074959e0bb5cf937752c39396e4fa8cd，PyPI 发布于 2020-05-02。

HarmonyOS PC（aarch64）适配结论 —— 零源码补丁：
  * 纯 Python noarch 包：源码只有 `justbackoff/__init__.py`（唯一 import 是标准库
    `random`），无 C/C++ 扩展、无 ABI/浮点/平台分支代码。OHOS 上由平台 CPython 3.12
    解释执行，行为与上游一致（R40 不适用：非图形/多媒体/系统底层类库，不存在需要
    "实质适配"的平台分支；R32 的 settings.os 分支在本配方不存在）。
  * package() 直接把 `justbackoff/` 拷入 `<pkg>/lib/python3.12/site-packages/`
    （pip/setuptools 构建在本环境不可用；与同仓 jinja2/3.1.6、appdirs/1.4.4、
    jmespath/1.1.0 的 python-require 形态一致）。
  * package_info() 同时注入 runenv_info 与 buildenv_info 的 PYTHONPATH
    （aiohttp 教训：只 print 不够，消费者会报 "No module named justbackoff"）。
  * R38：上游 setup.py 无 `scripts=`、无 console_scripts/entry_points，
    `packages=["justbackoff"]` 为纯库包，无 bin/ 产物 → 不创建 commands.json。

上游测试（R51）：`tests/test_backoff.py`（unittest 风格，TestBackoff 6 个用例）。
上游声明的运行器是 **pytest**（.travis.yml `script: pytest --cov=./justbackoff`；
Makefile `test: ${PYTHON} -m pytest`；setup.cfg `[aliases] test=pytest`），
故 build() 内以 pytest 真实运行该套件，并逐用例输出到 build 日志。
宿主解释器无 pytest，测试运行器从平台 pip 镜像取到独立目录
（ci/conan/setup.sh:55 PIP_COMMUNITY_INDEX，同 jinja2/3.1.6 先例）；
取依赖失败或套件失败一律显式抛 ConanException —— 不以跳过/静默降级冒充通过。
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches, export_conandata_patches, get)
from conan.tools.layout import basic_layout

# 平台 pip 镜像（与 CI 一致，见 ci/conan/setup.sh:55 PIP_COMMUNITY_INDEX）
PIP_INDEX = "https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple"

# 上游声明的测试运行器（.travis.yml / Makefile / setup.cfg 三处一致为 pytest）
UPSTREAM_TEST_REQUIRES = ("pytest>=7",)


class JustbackoffConan(ConanFile):
    name = "justbackoff"
    version = "0.6.0"
    description = ("Simple backoff algorithm in Python "
                   "(pure Python, zero runtime dependencies)")
    license = "MIT"
    homepage = "https://github.com/alexferl/justbackoff"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    package_type = "python-require"

    def export_sources(self):
        # 本包 patches 为空（conandata.yml `patches: {}`）——两处调用为空操作，
        # 仅保持与归档规范/同仓 python-require 先例（appdirs、jinja2）一致。
        export_conandata_patches(self)

    def requirements(self):
        # 上游 setup.py 无 install_requires；sdist PKG-INFO 与 wheel METADATA
        # 均无 Requires-Dist（grep rc=1）；PyPI requires_dist 为空；
        # 包源码仅 `import random`（标准库）→ 零第三方运行期依赖。
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # 包载荷：PyPI 官方分发件
        get(self, **self.conan_data["sources"]["justbackoff"], strip_root=True)
        # 上游测试：官方仓库 tag tarball（sdist 未打包 tests/）
        upstream = os.path.join(self.source_folder, "upstream")
        os.makedirs(upstream, exist_ok=True)
        get(self, **self.conan_data["sources"]["upstream_tests"],
            destination=upstream, strip_root=True)
        apply_conandata_patches(self)

    def _obtain_pytest(self):
        """从平台 pip 镜像取上游测试运行器到独立目录（宿主解释器无 pytest）。"""
        deps = os.path.join(self.build_folder, "test-deps")
        os.makedirs(deps, exist_ok=True)
        inst = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--target", deps,
             "--break-system-packages", "--disable-pip-version-check",
             "--timeout", "120", "--retries", "3",
             "--index-url", PIP_INDEX, *UPSTREAM_TEST_REQUIRES],
            capture_output=True, text=True, timeout=1800)
        if inst.returncode != 0:
            tail = "\n".join(((inst.stdout or "") + (inst.stderr or ""))
                             .strip().splitlines()[-12:])
            raise ConanException(
                "could not obtain the upstream test runner (pytest) from the "
                "platform pip mirror, so the upstream suite could not be run "
                "(R51: refusing to report an unrun suite as passing). Tail:\n"
                + tail)
        return deps

    def _run_upstream_tests(self):
        """运行上游 pytest 套件并如实输出逐用例结果（R51）。"""
        upstream = os.path.join(self.source_folder, "upstream")
        tests_dir = os.path.join(upstream, "tests")
        if not os.path.isfile(os.path.join(tests_dir, "test_backoff.py")):
            raise ConanException(
                "upstream tests/test_backoff.py not found; refusing to report "
                "a pass without running the suite (R51)")

        deps = self._obtain_pytest()

        env = dict(os.environ)
        paths = [deps, self.source_folder]
        if env.get("PYTHONPATH"):
            paths.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(paths)
        # 屏蔽宿主插件自动加载（宿主 site-packages 插件可能与 py3.12 不兼容）
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        # OHOS：新建目录属主被文件系统强制显示为挂载属主，pytest 默认
        # <tmp>/pytest-of-<user> 的属主检查会 INTERNALERROR；--basetemp 走
        # _given_basetemp 分支绕过（jinja2/3.1.6 先例，见其 notes）。
        basetemp = os.path.join(self.build_folder, "pytest-basetemp")
        os.makedirs(basetemp, exist_ok=True)
        env["TMPDIR"] = os.path.join(self.build_folder, "tmp")
        os.makedirs(env["TMPDIR"], exist_ok=True)

        report = os.path.join(self.build_folder, "upstream-pytest-report.txt")
        res = subprocess.run(
            [sys.executable, "-m", "pytest", "tests", "-v", "--no-header",
             "-p", "no:cacheprovider", f"--basetemp={basetemp}"],
            cwd=upstream, env=env, capture_output=True, timeout=600)
        out = (res.stdout or b"").decode(errors="ignore")
        err = (res.stderr or b"").decode(errors="ignore")
        with open(report, "w") as f:
            f.write(out + "\n" + err)
        for line in out.splitlines():
            s = line.strip()
            if "::" in s or "passed" in s or "failed" in s:
                self.output.info(f"upstream pytest: {s}")
        summary = out.strip().splitlines()[-1] if out.strip() else "n/a"
        self.output.info(f"upstream pytest rc={res.returncode} — {summary}")
        if res.returncode != 0:
            tail = "\n".join((out + err).strip().splitlines()[-15:])
            raise ConanException(
                "upstream pytest suite failed (R51: refusing to report a "
                f"passing build with a failing suite). Tail:\n{tail}")

    def build(self):
        module = os.path.join(self.source_folder, "justbackoff", "__init__.py")
        if not os.path.isfile(module):
            raise ConanException(f"justbackoff module not found: {module}")
        self._run_upstream_tests()

    def package(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        os.makedirs(site, exist_ok=True)
        src = os.path.join(self.source_folder, "justbackoff")
        dst = os.path.join(site, "justbackoff")
        shutil.copytree(src, dst,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        if not os.path.isfile(os.path.join(dst, "__init__.py")):
            raise ConanException(f"justbackoff package missing under {dst}")

    def package_info(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        # python-require 包无本地库产物（同 jmespath/1.1.0 形态）
        self.cpp_info.libs = []
        # 声明 import 路径（aiohttp 教训：仅 print 不够，消费者导入会失败）
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
        self.output.info(f"PYTHONPATH={site}")
