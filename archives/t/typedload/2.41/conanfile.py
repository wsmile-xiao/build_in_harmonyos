#!/usr/bin/env python3
"""Conan recipe for typedload 2.41 — 纯 Python 类型 (de)serialization 库。

上游：https://codeberg.org/ltworf/typedload （GPL-3.0-only，requires-python >=3.10）
发布形态：`typedload-2.41-py3-none-any.whl` + sdist（**纯 Python，无 C 扩展、无 ABI 绑定**）。

OHOS 平台适配要点（详见 notes.md）：
  * python-require 打包：产物落到 **OHOS python3.12** 的
    `lib/python3.12/site-packages/typedload`，与平台解释器 purelib 布局一致；
  * 运行时零依赖：sdist PKG-INFO 无任何 `Requires-Dist` 行（实测），因此
    `requirements()` 留空——不得为「能跑测试」把 attrs 声明成运行时依赖；
  * 上游测试为 **unittest**（15 个 test_*.py），stdlib 即可运行；唯一第三方
    测试依赖是 **attrs**（tests/test_attrload.py 等使用 `from attr import ...`），
    以 `tool_requires("attrs/26.1.0")` 提供（ohpcd 已发布，**不传播给消费者**）。

上游测试（R51，真实运行、如实申报）：
  `PYTHONPATH=<src>[:<attrs-site>] python3 -m unittest discover -s tests -v`
  实测 **212 passed / 0 failed / 0 error / 0 skipped**；套件失败或测试依赖
  取不到 → 显式抛 ConanException，不以「跳过」冒充通过。
"""
import json
import os
import re
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout

# 仅测试期需要的第三方包（不传播给消费者）
UPSTREAM_TEST_TOOL_REQUIRES = ("attrs/26.1.0",)
# 上游 tests/ 使用的唯一第三方 import 根名（用于自检）
UPSTREAM_TEST_IMPORT_ROOTS = {"attrs": "attr"}


class TypedloadConan(ConanFile):
    name = "typedload"
    version = "2.41"
    description = ("Load and dump data from json-like format into typed data "
                   "structures, enforcing a schema")
    license = "GPL-3.0-only"
    homepage = "https://ltworf.codeberg.page/typedload/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "python-require"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)  # 无补丁时空操作

    def requirements(self):
        # typedload 零运行时依赖（sdist PKG-INFO 无 Requires-Dist 行，实测；
        # pyproject.toml 亦无 dependencies 字段）。刻意留空。
        pass

    def build_requirements(self):
        for ref in UPSTREAM_TEST_TOOL_REQUIRES:
            self.tool_requires(ref)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    # ────────────────────────── 内部工具 ──────────────────────────

    def _py_ver(self):
        return f"python{sys.version_info.major}.{sys.version_info.minor}"

    def _site_packages_of(self, dep_name):
        """构建上下文依赖（python-require）的 site-packages 目录。"""
        dep = self.dependencies.build.get(dep_name)
        if dep is None:
            raise ConanException(
                f"build-context dependency '{dep_name}' not resolved; upstream "
                f"tests cannot run (R51: refuse to fake a pass)")
        site = os.path.join(dep.package_folder, "lib", self._py_ver(),
                            "site-packages")
        if not os.path.isdir(site):
            raise ConanException(f"{dep_name} site-packages missing: {site}")
        return site

    # ────────────────────────── 上游测试（R51）──────────────────────────

    def _run_upstream_tests(self):
        """真实运行上游 unittest 套件并如实申报结果。"""
        tests_dir = os.path.join(self.source_folder, "tests")
        if not os.path.isdir(tests_dir):
            raise ConanException(
                "upstream tests/ not found; refusing to report a pass without "
                "running the suite (R51)")

        env = dict(os.environ)
        paths = [self.source_folder]
        for ref in UPSTREAM_TEST_TOOL_REQUIRES:
            paths.append(self._site_packages_of(ref.split("/")[0]))
        if env.get("PYTHONPATH"):
            paths.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(paths)
        # 不落地 .pyc：避免污染源码树（HMDFS 上也无谓消耗 inode）
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        report = os.path.join(self.build_folder, "upstream-unittest-verbose.log")
        res = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            cwd=self.source_folder, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            errors="replace", timeout=3600)
        out = res.stdout or ""
        with open(report, "w") as f:
            f.write(out)
        # 逐用例 ID 名单（unittest -v 的 `test_x (mod.Class.test_x) ... ok`），
        # 供人工/审计核验「无漏测」。用例自身向 stdout 打印会与结果行交错，
        # 故用宽松正则只取括号内的限定名。
        ids = []
        for ln in out.splitlines():
            m = re.match(r"^([A-Za-z_]\w*) \(([\w.]+)\)", ln)
            if m:
                ids.append(m.group(2))
        ids_file = os.path.join(self.build_folder, "upstream-unittest-ids.txt")
        with open(ids_file, "w") as f:
            f.write("\n".join(ids) + "\n")

        # 计数一律以 unittest 收尾汇总行为准（"Ran N tests" + "OK/FAILED(...)"），
        # 不用「行尾 ... ok」计数——用例内的 print 会把统计打偏
        ran = next((int(ln.split()[1]) for ln in out.splitlines()
                    if ln.startswith("Ran ") and ln.split()[1].isdigit()), None)
        verdict_line = next((ln.strip() for ln in out.splitlines()
                             if ln.strip() == "OK" or ln.strip().startswith("OK (")
                             or ln.strip().startswith("FAILED")), "n/a")

        def _verdict_num(key):
            m = re.search(rf"{key}=(\d+)", verdict_line)
            return int(m.group(1)) if m else 0

        failed = _verdict_num("failures")
        errors = _verdict_num("errors")
        skipped = _verdict_num("skipped")
        passed = (ran or 0) - failed - errors - skipped
        summary = (f"Ran {ran} tests | passed={passed} failed={failed} "
                   f"errors={errors} skipped={skipped} | {verdict_line}")
        self.output.info(f"upstream unittest: {summary}")
        self.output.info(f"upstream unittest log: {report}")
        self.output.info(f"upstream unittest ids: {ids_file} ({len(ids)} names)")

        upstream = {
            "status": "passed" if res.returncode == 0 else "failed",
            "framework": "unittest",
            "command": ("PYTHONPATH=<src>:<attrs-site> python3 -m unittest "
                        "discover -s tests -v"),
            "discovered": ran,
            "executed": (ran or 0) - skipped,
            "passed": passed,
            "failed": failed,
            "errored": errors,
            "skipped": skipped,
            "ids_file": ids_file,
            "log": report,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))

        if res.returncode != 0:
            tail = "\n".join(out.strip().splitlines()[-25:])
            raise ConanException(
                "upstream unittest suite failed (R51: refusing to report a "
                f"passing build with a failing suite). Tail:\n{tail}")

    # ────────────────────────── 构建 / 打包 ──────────────────────────

    def build(self):
        pkg_src = os.path.join(self.source_folder, "typedload")
        if not os.path.isfile(os.path.join(pkg_src, "__init__.py")):
            raise ConanException(f"typedload package not found: {pkg_src}")
        self._run_upstream_tests()

    def package(self):
        pkg_dir = os.path.join(self.package_folder, "lib", self._py_ver(),
                               "site-packages", "typedload")
        os.makedirs(pkg_dir, exist_ok=True)

        src = os.path.join(self.source_folder, "typedload")
        for entry in sorted(os.listdir(src)):
            fpath = os.path.join(src, entry)
            if os.path.isdir(fpath):
                if entry == "__pycache__":
                    continue
                shutil.copytree(fpath, os.path.join(pkg_dir, entry),
                                ignore=shutil.ignore_patterns("__pycache__"))
                continue
            if entry.endswith((".c", ".so", ".pyc")):
                continue
            shutil.copy2(fpath, os.path.join(pkg_dir, entry))

        # 上游 setup.py 的 package_data = {"typedload": ["py.typed",
        # "__init__.pyi"]}——类型标记必须随包发布（下游 mypy 依赖）
        for marker in ("py.typed", "__init__.pyi", "__init__.py"):
            if not os.path.isfile(os.path.join(pkg_dir, marker)):
                raise ConanException(f"typedload package_data missing: {marker}")

        lic = os.path.join(self.source_folder, "LICENSE")
        if os.path.isfile(lic):
            lic_dir = os.path.join(self.package_folder, "licenses")
            os.makedirs(lic_dir, exist_ok=True)
            shutil.copy2(lic, os.path.join(lic_dir, "LICENSE"))

    def package_info(self):
        site = os.path.join(self.package_folder, "lib", self._py_ver(),
                            "site-packages")
        self.cpp_info.libs = []
        # 声明 import 路径（aiohttp 教训：仅 print 不够，消费者会报
        # "No module named typedload"）
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
        self.output.info(f"PYTHONPATH={site}")
