#!/usr/bin/env python3
"""jaraco.collections 5.1.0 — 纯 Python 集合模型库（MIT，无编译）。

依赖情况（判定依据见 conandata.yml 与 notes.md）：
  * 运行期确实 `import jaraco.text`：`jaraco/collections/__init__.py:13`，并在第 453 行用
    `jaraco.text.FoldedCase(key)` —— 不是可选依赖；
  * jaraco.text 自身要求 jaraco.context>=4.1、jaraco.functools、more_itertools、typer-slim；
  * 制品仓**没有** jaraco.text / jaraco.functools / jaraco.context（两种拼写 × 多版本
    `conan install` 实测均 Unable to find，`archives/` 下亦无）→ 本配方把这 3 个**纯 Python
    小模块**随包捆绑进 site-packages（各自 URL+sha256 钉死在 conandata 的 `vendored`），
    已发布的 `more-itertools` 仍走 Conan requires。
  * **R36 张力如实披露**：更彻底的做法是先单独提 jaraco.context / jaraco.functools /
    jaraco.text 三个配方再声明 requires；本轮为交付本库采用捆绑，notes.md 有替代路线。

构建/测试：上游自带 pytest 套件（tests/），build() 内真跑并统计通过/失败（不把失败写成通过）。
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get

SITE = ("lib", "python3", "site-packages")


class JaracoCollectionsConan(ConanFile):
    name = "jaraco.collections"
    version = "5.1.0"
    package_type = "application"
    license = "MIT"
    homepage = "https://github.com/jaraco/jaraco.collections"
    description = ("jaraco.collections — models and classes for collections "
                   "(pure Python, no compile)")
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"
    # 已发布的运行期依赖（jaraco.functools / jaraco.text 都用到 more_itertools）
    requires = "more-itertools/11.1.0"

    def _dep_site(self, name):
        dep = self.dependencies[name]
        return os.path.join(dep.package_folder, *SITE)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        for name, spec in self.conan_data["vendored"].items():
            get(self, url=spec["url"], sha256=spec["sha256"],
                filename=os.path.basename(spec["url"]),
                destination=os.path.join(self.source_folder, "_vendored", name),
                strip_root=True)

    # ── 上游测试（pytest） ────────────────────────────────────────────────
    def build(self):
        vendored = [os.path.join(self.source_folder, "_vendored", n)
                    for n in self.conan_data["vendored"]]
        pythonpath = os.pathsep.join([self.source_folder] + vendored
                                     + [self._dep_site("more-itertools")])
        log = os.path.join(self.build_folder, "pytest.log")
        self.run('bash -c "cd %s && PYTHONPATH=%s python3 -m pytest -q tests '
                 '> %s 2>&1"' % (self.source_folder, pythonpath, log),
                 ignore_errors=True)
        with open(log, "r", errors="replace") as fh:
            text = fh.read()
        if "No module named pytest" in text or "No module named 'pytest'" in text:
            # ── CI worker 的 HNP python3 没有 pytest（实测）→ 用 stdlib 直接调用上游
            #    test_* 函数：仍然**真跑**上游用例，只是不经过 pytest 框架。
            #    本库上游套件只有一个用例（tests/test_collections.py::test_always_lower_keys_dict）。
            runner = os.path.join(self.build_folder, "_run_tests_nopytest.py")
            with open(runner, "w") as fh:
                fh.write(
                    "import importlib.util, os, sys, traceback\n"
                    "sys.path.insert(0, os.getcwd())\n"
                    "spec = importlib.util.spec_from_file_location(\n"
                    "    'tc', os.path.join('tests', 'test_collections.py'))\n"
                    "mod = importlib.util.module_from_spec(spec)\n"
                    "spec.loader.exec_module(mod)\n"
                    "names = sorted(n for n in dir(mod) if n.startswith('test_'))\n"
                    "passed = failed = 0\n"
                    "for n in names:\n"
                    "    try:\n"
                    "        getattr(mod, n)()\n"
                    "        print('PASS', n)\n"
                    "        passed += 1\n"
                    "    except Exception:\n"
                    "        print('FAIL', n)\n"
                    "        traceback.print_exc()\n"
                    "        failed += 1\n"
                    "print('NO_PYTEST_RESULT passed=%d failed=%d total=%d'\n"
                    "      % (passed, failed, len(names)))\n")
            rlog = os.path.join(self.build_folder, "nopytest.log")
            self.run('bash -c "cd %s && PYTHONPATH=%s python3 %s > %s 2>&1"'
                     % (self.source_folder, pythonpath, runner, rlog),
                     ignore_errors=True)
            text2 = open(rlog, "r", errors="replace").read()
            m = re.search(r"NO_PYTEST_RESULT passed=(\d+) failed=(\d+) total=(\d+)", text2)
            if not m:
                raise ConanInvalidConfiguration(
                    "[upstream tests] 无 pytest，且 stdlib 回退跑未产出结果（视为不成立）：\n"
                    + "\n".join(text2.splitlines()[-15:]))
            p2, f2, t2 = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if t2 == 0:
                raise ConanInvalidConfiguration(
                    "[upstream tests] stdlib 回退跑未发现任何 test_* 函数 —— 拒绝宣称成功")
            if f2:
                raise ConanInvalidConfiguration(
                    "[upstream tests] stdlib 回退跑出现真实失败 %d/%d：\n%s"
                    % (f2, t2, "\n".join(text2.splitlines()[-15:])))
            self.output.info(
                "[upstream tests] 环境无 pytest → stdlib 直接调用上游用例："
                "passed=%d failed=%d total=%d（真跑，非跳过）" % (p2, f2, t2))
            return
        tail = "\n".join(text.splitlines()[-25:])
        # 统计：pytest 结尾形如 "12 passed, 1 skipped in 0.42s"
        passed = sum(int(m) for m in re.findall(r"(\d+) passed", text))
        failed = sum(int(m) for m in re.findall(r"(\d+) failed", text))
        errors = sum(int(m) for m in re.findall(r"(\d+) error", text))
        if "ModuleNotFoundError" in text or "ImportError" in text:
            raise ConanInvalidConfiguration(
                "[upstream tests] 上游测试因缺少模块而无法运行（视为不成立，不算通过）：\n" + tail)
        if failed or errors:
            raise ConanInvalidConfiguration(
                "[upstream tests] 上游用例失败（真实失败，非环境阻塞）：\n" + tail)
        if not passed:
            raise ConanInvalidConfiguration(
                "[upstream tests] 未解析到 pytest 通过计数（可能未真正运行）：\n" + tail)
        self.output.info("[upstream tests] pytest: passed=%d failed=%d errors=%d"
                         % (passed, failed, errors))
        for line in text.splitlines()[-6:]:
            self.output.info("    " + line)

    # ── 打包 ──────────────────────────────────────────────────────────────
    def package(self):
        dest = os.path.join(self.package_folder, *SITE)
        # 本体模块
        shutil.copytree(os.path.join(self.source_folder, "jaraco", "collections"),
                        os.path.join(dest, "jaraco", "collections"),
                        dirs_exist_ok=True)
        # 捆绑的运行期依赖（各自 jaraco/<mod>）
        for name, spec in self.conan_data["vendored"].items():
            mod = spec["module"].replace("/", os.sep)
            src = os.path.join(self.source_folder, "_vendored", name, mod)
            if not os.path.isdir(src):
                raise ConanInvalidConfiguration(
                    "捆绑依赖 %s 的模块目录未找到：%s" % (name, src))
            shutil.copytree(src, os.path.join(dest, mod), dirs_exist_ok=True)
        # 许可证与说明（保持可追溯）
        for name in ("LICENSE",):
            p = os.path.join(self.source_folder, name)
            if os.path.isfile(p):
                shutil.copyfile(p, os.path.join(self.package_folder, name))

    def package_info(self):
        self.cpp_info.libs = []
