#!/usr/bin/env python3
"""Conan recipe for setuptools 84.0.0 — Python packaging build backend.

HarmonyOS PC adaptation (路径 A 基础适配). setuptools is **pure Python**: the
payload is ``setuptools/`` + ``_distutils_hack/`` plus a ``distutils-precedence``
``.pth`` file, with **no runtime dependencies at all** (its third-party needs are
vendored under ``setuptools/_vendor/``: packaging / wheel / more_itertools /
jaraco.* / platformdirs / tomli / zipp / importlib_metadata). It is therefore a
"level 0" package for this archive: nothing to compile and nothing to require.

Why this package exists at all
------------------------------
``setuptools`` is the missing build-time dependency that made two consumers
fail, and it is **not** shipped by the conan ``python`` package (its
site-packages holds only ``README.txt``) nor previously published on ohpcd:

* greenlet/3.5.6 CI #10488 died with ``ModuleNotFoundError: No module named
  'setuptools'`` while executing ``setup.py``, because the recipe could only
  borrow a copy from whichever host path happened to exist — the build machine
  had ``<home>/usr/local/lib/python3.12/site-packages``, CI did not;
* the archived lxml / pillow / cppy recipes show the same workaround.

Publishing it on ohpcd turns that host-dependent borrowing into a declared,
reproducible dependency.

Two measured build details
--------------------------
* **Self-bootstrap, no host copy needed.** ``setup.py`` starts with
  ``import setuptools``; because the build runs with ``cwd`` inside the sdist
  root, that import resolves to the very source tree being built (measured:
  ``setuptools.__version__ == '84.0.0'`` with ``setuptools.__file__`` pointing
  into the extracted source). So the build does **not** depend on any
  pre-installed setuptools — which is precisely the trap above.

* **A ``dist-info`` is mandatory, not cosmetic.** ``setuptools/version.py``
  resolves the version through
  ``importlib.metadata.version('setuptools')``, so a payload consisting only of
  the ``setuptools/`` directory reports no version (and raises on access). The
  recipe therefore installs through upstream's own ``setup.py`` machinery, which
  materialises the metadata; a hand-copied tree was measured to fail
  ``import setuptools; setuptools.__version__``.

Test posture (R51, measured not assumed)
----------------------------------------
``setuptools`` has a real upstream pytest suite (``setuptools/tests``, 1012
tests collected on the device). It is run in ``build()`` with the upstream-declared
test extras. Those extras are numerous (pytest>=6, virtualenv, wheel, packaging,
jaraco.path/envs/text/functools/context, filelock, ini2toml, tomli-w, build,
pyproject-hooks, pytest-xdist, pytest-timeout, pytest-home, pytest-subprocess)
and are **not published on ohpcd** (probed: 0 recipes), so per PF4 they cannot be
declared as ``test_requires``; they are fetched from the platform pip mirror
during build instead, and the real counts are reported. If the fetch or the run
fails the failure is surfaced, never silently converted into a pass.
"""
import json
import os
import re
import shutil
import signal
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, save)
from conan.tools.layout import basic_layout

# 允许失败清单（R9）：仅列**平台环境性**失败，且逐项给出实测根因。清单外的
# 失败一律抛 ConanException 使 conan create 失败，杜绝"测试失败但构建成功"。
#
#   - test_wheel_mode（setuptools/tests/test_wheel.py:689）
#     `assert oct(stat.S_IMODE(script_sh.stat().st_mode)) == "0o777"` 实测得
#     '0o770'。根因是 **OHOS hmdfs 不忠实保存 POSIX mode 位**：实测对全新文件
#     chmod 0o777 → 0o770，且 "others" 三位被整体丢弃（0o500 → 0o660、
#     0o604 → 0o660、0o705 → 0o760），即权限位由文件系统按挂载策略重写，
#     用户态无法设置 0o777。该断言在 OHOS 上**不可能通过**，与 setuptools
#     适配无关。同源现象在本仓已有先例：meson 1.11.0.1 的
#     ALLOWED_TEST_FAILURES 含 test_install_umask / test_installed_modes /
#     test_installed_modes_extended（同属 OHOS 不保留 setgid/umask 语义）。
ALLOWED_TEST_FAILURES = frozenset({
    "test_wheel_mode",
})

# 单个用例的墙钟上限（交给 pytest-timeout 执行）。
#
# 上游套件在本环境约 1000 个用例、整体约 1095~1419s 跑完（CI 实测两次，
# elapsed 1095.9s / 1419.2s），均值 ~1.2s —— 故任何单个用例超过此值都属
# **停滞**而非"慢"。
#
# 为什么必须给：CI #60058 在进度 89% 处停滞，一路吃满外层 2400s 墙钟才被
# 截断，报告停在一行进度点、**没有任何 short summary 或 FAILURES 段**，
# 于是"哪个用例挂住"完全无从得知（机器人还把它误判成"源码下载超时"）。
# 给每个用例上限后，停滞的那个会被中断、记入 FAILURES 段（含 traceback 与
# 当时的调用栈）并带上用例名，套件继续跑完 —— 日志据此可直接定位。
PER_TEST_TIMEOUT = 300

# 上游 pyproject.toml [project.optional-dependencies].test 的等价集合（逐项
# 对齐，含 pytest 版本约束 ">= 6, != 8.1.*"）。这些包含 OHOS 制品仓未发布者，
# 故不能走 test_requires（PF4），只能构建期从平台 pip 镜像取。
UPSTREAM_TEST_REQUIRES = (
    "pytest>=6,!=8.1.*",
    "virtualenv>=13.0.0",
    "wheel>=0.44.0",
    "pip>=19.1",
    "packaging>=24.2",
    "jaraco.envs>=2.2",
    "jaraco.path>=3.7.2",
    "pytest-xdist>=3",
    "build>=1.0.3",
    "filelock>=3.4.0",
    "ini2toml>=0.14",
    "tomli-w>=1.0.0",
    "pytest-timeout",
    "pytest-home>=0.5",
    "pytest-subprocess",
    "pyproject-hooks!=1.1",
    # 上游 test extra 里以 jaraco.develop 带入的间接依赖，测试收集期需要
    "jaraco.text>=3.7",
    "jaraco.functools>=4",
    "more_itertools",
    "platformdirs",
    # 上游 pytest.ini:91 的 filterwarnings 项
    # `ignore:Couldn't import C tracer:coverage.exceptions.CoverageWarning`
    # 会 import coverage.exceptions；而上游把 coverage 只放在 **cover** extra
    # （pytest-cov）里，test extra 并不包含它。pytest.ini 首行是
    # `error`（警告即错误），于是 coverage 缺失时 pytest 配置期
    # apply_warning_filters 抛的 PytestConfigWarning 直接让 run 中止：
    #   pytest.PytestConfigWarning: Failed to import filter module 'coverage':
    #       ignore:Couldn't import C tracer:coverage.exceptions.CoverageWarning
    # 实测该中止发生在**收集之前**，输出里没有任何 FAILED 行 → 配方按 R9 如实
    # 报“运行器异常退出”。故 coverage 是**运行上游套件的硬依赖**，必须显式补上。
    "coverage",
    # 上游 test extra 末尾的 `jaraco.test>=5.5`。test extra 里它只为 py.typed
    # 而来，但实际是**收集期硬依赖**：setuptools/tests/compat/py39.py 顶层
    # `from jaraco.test.cpython import from_test_support, try_import`，缺它时
    # test_dist / test_find_packages / test_find_py_modules 三个文件收集即
    # ImportError → `Interrupted: 6 errors during collection`（实测）。
    "jaraco.test>=5.5",
)

# 本平台 CPython **不含 stdlib ``test`` 包**（实测 conan python/3.12.9 的
# ``lib/python3.12/`` 下没有 ``test/`` 目录）。而上游
# ``setuptools/tests/compat/py39.py`` 顶层这样取 os_helper：
#     from jaraco.test.cpython import from_test_support, try_import
#     os_helper = try_import('os_helper') or from_test_support('can_symlink')
# 其中 ``from_test_support()`` 内部是 ``import test.support``（jaraco.test 自己
# 的实现），所以**补上 jaraco.test 并不够**——真正缺的是 stdlib test 包。缺它时
# compat/py39.py 连同 3 个导入它的模块在**收集期**就失败：
#     E   ImportError: cannot import name 'os_helper' from
#         'setuptools.tests.compat.py39'
#     Interrupted: 4 errors during collection
# 故这里补一个最小 shim，只提供收集到的用例实际用到的唯一符号
# ``os_helper.can_symlink``（全套件仅 test_find_packages.py:113 与
# test_find_py_modules.py:44 两处 skipif 使用）。can_symlink 仍**真实探测**
# 文件系统能力，因此平台不支持符号链接时用例照旧被跳过，不会把失败掩盖成通过；
# 实测本平台符号链接可用，故这两个用例会真正执行（而非被跳过）。
#
# 布局按 ``test/support/os_helper.py`` 给全：``try_import('os_helper')`` 走的是
# ``import test.support.os_helper``，命中它就不会再落到
# ``from_test_support('can_symlink')``（后者同样需要 ``import test.support``）。
# **只在目标解释器确实没有 stdlib test 包时才安装**——PYTHONPATH 会排在 stdlib
# 之前，无条件铺 shim 会在健康平台上遮蔽真正的 test 包，反而让别的符号（如
# import_helper / script_helper）失效。
TEST_SUPPORT_SHIM_FILES = {
    "test/__init__.py": "",
    "test/support/__init__.py": "",
    "test/support/os_helper.py": '''"""Minimal stand-in for CPython's ``test.support.os_helper``.

The OHOS CPython this archive ships omits the stdlib ``test`` package entirely,
so upstream setuptools' ``tests/compat/py39.py`` cannot resolve ``os_helper``
through ``jaraco.test``. Only ``can_symlink`` is used by the collected suite,
and it is implemented faithfully: the result comes from a real ``os.symlink``
probe rather than a hard-coded answer, so the symlink cases are skipped only if
symlinks genuinely do not work here.
"""

import os
import shutil
import tempfile

_can_symlink = None


def can_symlink():
    global _can_symlink
    if _can_symlink is not None:
        return _can_symlink
    tmp = tempfile.mkdtemp(prefix="ohos-can-symlink-")
    src = os.path.join(tmp, "src")
    link = src + "-link"
    try:
        with open(src, "w"):
            pass
        os.symlink(src, link)
        can = True
    except (OSError, NotImplementedError, AttributeError):
        can = False
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    _can_symlink = can
    return can
''',
}


class SetuptoolsConan(ConanFile):
    name = "setuptools"
    version = "84.0.0"
    description = ("setuptools — the Python packaging build backend "
                   "(distutils replacement; pip/build/wheel backend)")
    license = "MIT"
    homepage = "https://github.com/pypa/setuptools"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # 纯 Python，无 C/C++ 产物、不产生 bindirs → 无需 commands.json（R38）。
    # 亦无任何运行时依赖（三方依赖全部 vendored 在 setuptools/_vendor/），
    # 故 package_type 用 python-require 不会被类型契约拦住。
    package_type = "python-require"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # 零运行时依赖：setuptools 把 packaging/wheel/more_itertools/jaraco.*/
        # platformdirs/tomli/zipp/importlib_metadata 全部 vendored 在
        # setuptools/_vendor/ 内（实测目录内容）。消费者只需 PYTHONPATH。
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)  # 无补丁时空操作

    # ------------------------------------------------------------------ build
    def _py(self):
        """解释器：优先本包运行所用的 CPython。"""
        return sys.executable or "python3"

    def _stage_dir(self):
        return os.path.join(self.build_folder, "staging")

    def build(self):
        if not os.path.isfile(os.path.join(self.source_folder, "setup.py")):
            raise ConanException("upstream setup.py not found in source")
        if not os.path.isdir(os.path.join(self.source_folder, "setuptools")):
            raise ConanException("setuptools/ package directory not found")

        # 1) 自举构建 + 登台安装。
        #    cwd=源码根 → setup.py 的 `import setuptools` 解析到**源码树自身**
        #    （实测 __file__ 指向解包目录、__version__=84.0.0），因此不需要宿主
        #    预装 setuptools——这正是 greenlet CI #10488 栽的地方。
        #    走 setup.py（而非手工 copy）是必须的：setuptools/version.py 通过
        #    importlib.metadata.version('setuptools') 取版本，必须有 dist-info；
        #    实测纯 copy 的树会让 `setuptools.__version__` 取不到值。
        stage = self._stage_dir()
        os.makedirs(stage, exist_ok=True)
        self.run(
            f'"{self._py()}" setup.py install '
            f'--root="{stage}" --prefix=/usr '
            f'--single-version-externally-managed --record=/dev/null',
            cwd=self.source_folder)
        if not self._installed_site(stage):
            raise ConanException(
                f"setup.py install produced no site-packages under {stage}")

        # 2) R51：上游测试真实运行。
        self._run_upstream_tests()

    def _installed_site(self, stage):
        for root, dirs, _files in os.walk(stage):
            if os.path.basename(root) == "site-packages" or \
                    root.endswith(os.path.join("python3.12", "site-packages")):
                return root
            if "setuptools" in dirs and "_distutils_hack" in dirs:
                return root
        return None

    def _install_test_support_shim(self, py):
        """目标解释器缺 stdlib ``test`` 包时铺一层最小 shim，返回其目录。

        健康解释器（自带 test 包）返回 None，不改动 PYTHONPATH——避免遮蔽真包。
        判定用的是**目标解释器自身**的导入探测，而不是宿主或其他 Python 的能力，
        因为 run 用的就是 ``py``。
        """
        probe = subprocess.run(
            [py, "-c", "import test.support"],
            capture_output=True, text=True, timeout=120)
        if probe.returncode == 0:
            self.output.info("stdlib test.support available; no shim needed")
            return None

        shim = os.path.join(self.build_folder, "test-support-shim")
        for rel, content in TEST_SUPPORT_SHIM_FILES.items():
            path = os.path.join(shim, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)

        # 自检：装上 shim 后目标解释器必须能 import 到 os_helper 及其符号，
        # 否则宁可显式失败也不要把带病的收集结果当成通过（R51）。
        verify = subprocess.run(
            [py, "-c",
             "import test.support.os_helper as m; m.can_symlink()"],
            capture_output=True, text=True, timeout=120,
            env=dict(os.environ, PYTHONPATH=shim))
        if verify.returncode != 0:
            raise ConanException(
                "the platform Python has no stdlib test package and the "
                "test.support shim does not satisfy the upstream suite; "
                "refusing to report an unrun suite as passing (R51). Tail:\n"
                + ((verify.stdout or "") + (verify.stderr or "")
                   ).strip()[-800:])
        self.output.info(
            "stdlib test package absent in the target Python; installed "
            f"minimal test.support shim at {shim}")
        return shim

    @staticmethod
    def _site_packages_dir(py):
        """目标解释器**可写**的 site 目录（落 ``.pth`` 用）。

        ``.pth`` 只有在 **site 目录**里才会被 ``site`` 在启动期采纳，所以不能
        随便找个目录丢进去。但**系统** site-packages 在 CI 上不可写：平台
        解释器装在 ``/data/service/hnp/...``（只读）下，实测
        ``PermissionError: [Errno 13] ... _ohc_upstream_test_deps_0.pth``。

        故优先取 **user site**（``~/.local/lib/pythonX.Y/site-packages``）：
        同属 ``site`` 机制、启动期即生效（实测 PYTHONPATH 清空后仍可导入），
        且位于 ``$HOME`` 下可写。系统 site 目录可写时作为回退；两者都不可写
        才显式失败——不静默降级（R51）。
        """
        def _ask(code):
            probe = subprocess.run([py, "-c", code], capture_output=True,
                                   text=True, timeout=120)
            return (probe.stdout or "").strip()

        candidates = []
        # user site 被显式禁用时（-s/-I、PYTHONNOUSERSITE）写进去也不会生效，
        # 故先问解释器自己 ENABLE_USER_SITE，再取路径。
        if _ask("import site; print(1 if site.ENABLE_USER_SITE else 0)") == "1":
            candidates.append(_ask("import site; print(site.getusersitepackages())"))
        candidates.append(_ask("import site; print(site.getsitepackages()[0])"))

        tried = []
        for d in candidates:
            if not d or d == "None":
                continue
            tried.append(d)
            try:
                os.makedirs(d, exist_ok=True)
            except OSError:
                continue
            if os.path.isdir(d) and os.access(d, os.W_OK):
                return d
        raise ConanException(
            f"no writable site-packages directory for {py}; tried {tried}. The "
            f"upstream suite needs its test dependencies importable without "
            f"PYTHONPATH (R51)")

    def _expose_deps_without_pythonpath(self, py, dirs):
        """把测试依赖目录以 ``.pth`` 挂进目标解释器，使其**无需 PYTHONPATH**
        也可导入。返回已写入的 ``.pth`` 路径列表（调用方负责清理）。

        为什么必须这样：上游 ``setuptools/tests/fixtures.py`` 的 ``venv``
        fixture 用 ``with contexts.environment(PYTHONPATH=None)`` 跑子进程
        （防止被测 setuptools 经 PYTHONPATH 泄漏进新建 venv）。而本配方把全部
        测试依赖装在 ``--target`` 目录、**只靠 PYTHONPATH 暴露** → 子进程里
        ``python -m virtualenv`` 直接 ``No module named virtualenv``，venv 建不出
        → fixture setup 全灭。实测本机复现为
        ``subprocess.CalledProcessError: Command '[... '-m', 'virtualenv', ...]'``
        连带 28 个 ERROR，与 CI 的 45 个 ERROR 同一机制。

        ``.pth`` 是标准库的启动期机制：``site`` 初始化时逐行并入 ``sys.path``，
        与 PYTHONPATH 无关，故被清空也不受影响。用固定前缀命名以便幂等清理
        （含 conan 包缓存目录，避免污染解释器）。
        """
        site_dir = self._site_packages_dir(py)
        if not site_dir or not os.path.isdir(site_dir):
            raise ConanException(
                f"cannot locate site-packages of {py}; the upstream suite needs "
                f"its test dependencies importable without PYTHONPATH (R51)")
        written = []
        for idx, d in enumerate(dirs):
            if not d:
                continue
            path = os.path.join(site_dir, f"_ohc_upstream_test_deps_{idx}.pth")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(d + "\n")
            written.append(path)
        return written

    @staticmethod
    def _importable_without_pythonpath(py, module):
        """自检：清空 PYTHONPATH 后目标解释器仍能导入 ``module``。

        宁可显式失败，也不要把「fixture 全灭」当成正常结果（R51）。
        """
        env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
        probe = subprocess.run([py, "-c", f"import {module}"],
                               capture_output=True, text=True, timeout=180,
                               env=env)
        return probe.returncode == 0, (probe.stderr or "")[-400:]

    def _prebuild_distributions(self, py, deps):
        """预建 sdist/wheel，供上游 ``PRE_BUILT_*`` 逃生口使用。

        为什么必须这样做：上游 ``setuptools/tests/fixtures.py`` 的
        ``_build_distributions()`` 用 ``sys.executable -m build`` 构建发行版，
        而 ``build`` 默认创建**隔离环境**（stdlib ``venv``）。该路径在 OHOS 上
        失效——CI #59700 实测隔离解释器起不来：

            * Creating isolated environment: venv+pip...
            Could not find platform independent libraries <prefix>
            ModuleNotFoundError: No module named 'encodings'
            ERROR Backend subprocess exited when trying to invoke
                  get_requires_for_build_sdist

        连带 30+ 项清单外失败（``setuptools_sdist`` / ``setuptools_wheel`` /
        ``venv`` / ``venv_without_setuptools`` 等 session 级 fixture setup 全灭）。

        上游本就为此留了逃生口（``fixtures.py`` 的 ``prebuilt`` 分支：
        ``PRE_BUILT_SETUPTOOLS_SDIST`` / ``PRE_BUILT_SETUPTOOLS_WHEEL``），故这里
        用 ``--no-isolation`` 产出两份发行版喂给它——**不跳过任何用例、不改上游
        测试代码**，只是把「这两个文件怎么造出来」换成在本平台真能工作的方式。
        """
        outdir = os.path.join(self.build_folder, "prebuilt-dist")
        os.makedirs(outdir, exist_ok=True)
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(
            [deps] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
        proc = subprocess.run(
            [py, "-m", "build", "--no-isolation", "--outdir", outdir,
             self.source_folder],
            cwd=self.source_folder, env=env, capture_output=True, text=True,
            timeout=1800)
        if proc.returncode != 0:
            tail = "\n".join(((proc.stdout or "") + (proc.stderr or ""))
                             .strip().splitlines()[-20:])
            raise ConanException(
                "could not pre-build the setuptools sdist/wheel with "
                "`python -m build --no-isolation`; the upstream suite's "
                "setuptools_sdist/setuptools_wheel fixtures would fail "
                "wholesale (R51: refusing to report an unrun suite as "
                "passing). Tail:\n" + tail)
        names = sorted(os.listdir(outdir))
        sdist = next((os.path.join(outdir, f)
                      for f in names if f.endswith(".tar.gz")), None)
        wheel = next((os.path.join(outdir, f)
                      for f in names if f.endswith(".whl")), None)
        if not (sdist and wheel):
            raise ConanException(
                "`python -m build --no-isolation` produced no sdist+wheel in "
                f"{outdir}: {names}")
        self.output.info("pre-built distributions for the suite: "
                         f"{os.path.basename(sdist)}, {os.path.basename(wheel)}")
        return sdist, wheel

    def _libpython_link_env(self, py, env):
        """确保链接器能找到 `-lpython3.12`（CI #60316 实测）。

        上游套件里凡是要**构建 C 扩展**的用例全灭，报的是**链接期**失败：

            subprocess.CalledProcessError: Command '['/data/service/hnp/bin/clang',
                '-shared', '-L.', '-lpython3.12', '-L<LIBDIR>', ... ,
                'build/temp.../extension.o', '-o', 'build/lib.../extension.abi3.so']'
                returned non-zero exit status 1
            ld.lld: error: unable to find library -lpython3.12

        注意失败在**链接**而非编译：`extension.o` 已生成、`-I` 下的头文件可用。
        `-L<LIBDIR>` 与 `-lpython3.12` 都来自解释器自身 sysconfig 的 `LDSHARED`
        （实测本机：`clang -shared -L. -lpython3.12 -L<prefix>/lib -L<prefix>/lib`），
        故能否链上取决于该目录里**是否存在 dev 名**的 `libpythonX.Y.so`：
        只有带版本号的 `libpython3.12.so.1.0` 时，ld 就报
        `unable to find library -lpython3.12`（本机已逐字复现该报错）；
        补上 dev 名后同一命令链接成功。

        故这里把「确实含 dev 名的目录」补进 `LIBRARY_PATH` 与 `LDFLAGS`：
          * dev 名已就位 → 记录（便于比对），不改动行为；
          * 目录里只有带版本号的文件 → 在 build 目录建 dev 名符号链接，并把该
            目录前置进链接搜索路径；
          * 两者都没有 → 只告警，让 CI 日志直接暴露该事实，而不是静默失败。
        """
        probe = (
            "import json, sys, sysconfig\n"
            "def g(k):\n"
            "    try:\n"
            "        return sysconfig.get_config_var(k) or ''\n"
            "    except Exception:\n"
            "        return ''\n"
            "print(json.dumps({\n"
            "    'libdir': g('LIBDIR'), 'libpl': g('LIBPL'),\n"
            "    'ldshared': g('LDSHARED'), 'bldshared': g('BLDSHARED'),\n"
            "    'ldlibrary': g('LDLIBRARY'), 'instsoname': g('INSTSONAME'),\n"
            "    'prefix': sys.prefix, 'base_prefix': getattr(sys, 'base_prefix', ''),\n"
            "    'executable': sys.executable}))\n"
        )
        try:
            r = subprocess.run([py, "-c", probe], capture_output=True, text=True,
                               timeout=120)
            info = json.loads((r.stdout or "{}").strip().splitlines()[-1])
        except Exception as e:  # 探针失败也要留证据，不静默
            self.output.warning(
                f"[LIBPY] sysconfig probe failed: {type(e).__name__}: {str(e)[:160]}")
            return env

        ver = f"{sys.version_info.major}.{sys.version_info.minor}"
        dev = f"libpython{ver}.so"

        # 候选目录的**首要来源**是 LDSHARED/BLDSHARED 里的 -L —— 那正是
        # `-lpython3.12` 实际被搜索的路径。上一版只用了 LIBDIR/prefix，
        # worker 上三者皆非有效目录，于是 candidates=[] 修复完全没生效
        # （CI #60316 实测：`[LIBPY] ... candidates=[]`）。故这里以 -L 为主。
        cands = []
        for key in ("ldshared", "bldshared"):
            for d in re.findall(r"-L(\S+)", info.get(key) or ""):
                if os.path.isabs(d):
                    cands.append(d)
        for key in ("libdir", "libpl"):
            if info.get(key):
                cands.append(info[key])
        for key in ("prefix", "base_prefix"):
            if info.get(key):
                cands.append(os.path.join(info[key], "lib"))
        exe = info.get("executable") or ""
        if exe:
            # <prefix>/bin/pythonX.Y → <prefix>/lib
            cands.append(os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(exe))), "lib"))
        cands += [p for p in env.get("LIBRARY_PATH", "").split(os.pathsep) if p]
        cands = [d for d in dict.fromkeys(cands) if d and os.path.isdir(d)]

        found = None
        versioned = []
        for d in cands:
            if os.path.isfile(os.path.join(d, dev)):
                found = d
                break
            try:
                names = sorted(os.listdir(d))
            except OSError:
                continue
            for name in names:
                if name.startswith(dev + "."):
                    p = os.path.join(d, name)
                    if os.path.isfile(p):
                        versioned.append(p)
        if not found and not versioned:
            # 末路兜底：在候选目录里找任何 libpython*.so*（版本号可能不同）
            for d in cands:
                try:
                    names = sorted(os.listdir(d))
                except OSError:
                    continue
                for name in names:
                    if name.startswith("libpython") and ".so" in name:
                        p = os.path.join(d, name)
                        if os.path.isfile(p):
                            versioned.append(p)

        link_dir = found
        if not found and versioned:
            link_dir = os.path.join(self.build_folder, "libpython-link")
            os.makedirs(link_dir, exist_ok=True)
            lnk = os.path.join(link_dir, dev)
            try:
                if os.path.islink(lnk) or os.path.exists(lnk):
                    os.remove(lnk)
                os.symlink(versioned[0], lnk)
            except OSError as e:
                self.output.warning(f"[LIBPY] cannot link {lnk}: {e}")
                link_dir = None

        self.output.info(
            f"[LIBPY] dev-name={dev} found={found or 'none'} "
            f"versioned={versioned[:2] or 'none'} using={link_dir or 'none'} "
            f"candidates={cands}")
        if link_dir:
            env["LIBRARY_PATH"] = os.pathsep.join(
                [link_dir]
                + [p for p in env.get("LIBRARY_PATH", "").split(os.pathsep) if p])
            env["LDFLAGS"] = (env.get("LDFLAGS", "") + f" -L{link_dir}").strip()
        else:
            self.output.warning(
                f"[LIBPY] no dev-named {dev} found and none could be derived; "
                "C-extension tests linking -lpython will fail")
        return env

    def _run_upstream_tests(self):
        """运行上游 pytest 套件并如实报告（R51）。

        上游 test extra 的依赖未发布到 ohpcd（PF4 禁止写成 test_requires），
        故构建期从平台 pip 镜像取到独立目录，再以该目录为 PYTHONPATH 运行。
        失败**不静默降级**：取依赖失败或运行失败都显式输出并抛错，避免出现
        「测试没跑但构建成功」的状态脱节。
        """
        tests_dir = os.path.join(self.source_folder, "setuptools", "tests")
        if not os.path.isdir(tests_dir):
            raise ConanException(
                "upstream setuptools/tests not found; refusing to report "
                "a pass without running the suite (R51)")

        deps = os.path.join(self.build_folder, "test-deps")
        os.makedirs(deps, exist_ok=True)
        py = self._py()
        inst = subprocess.run(
            [py, "-m", "pip", "install", "--target", deps,
             "--break-system-packages", "--disable-pip-version-check",
             "--timeout", "120", "--retries", "3", *UPSTREAM_TEST_REQUIRES],
            capture_output=True, text=True, timeout=1800)
        if inst.returncode != 0:
            tail = "\n".join(((inst.stdout or "") + (inst.stderr or ""))
                             .strip().splitlines()[-12:])
            raise ConanException(
                "could not obtain upstream test dependencies from the platform "
                "pip mirror, so the upstream suite could not be run (R51: "
                "refusing to report an unrun suite as passing). Tail:\n" + tail)

        shim = self._install_test_support_shim(py)

        env = dict(os.environ)
        # 让「本沙箱无外网」成为**确定且快速**的事实（CI #60316 实测）。
        #
        # 失败形态：套件根本没跑到用例，5.76s 就死在**收集期**——
        #   ERROR collecting setuptools/tests/test_virtualenv.py
        #     setuptools/tests/test_virtualenv.py:45: in <module>
        #       @pytest.mark.skipif(not access_pypi(), reason="no network")
        #     setuptools/tests/test_virtualenv.py:33: in access_pypi
        #       urlopen('https://pypi.org', timeout=1)
        #   E   TimeoutError: The read operation timed out
        #
        # 关键在于 `access_pypi()` **只捕获 URLError**：
        #   except URLError: return False      # → 测试被 skip（上游的设计意图）
        # 而 CPython 的 urllib 只在 `h.request()` 那一步把 OSError 包成 URLError，
        # **`h.getresponse()` 在 try 之外**（urllib/request.py do_open）——所以
        # 「连得上但读超时」时抛的是裸 TimeoutError，**绕过**了该守卫，把一次
        # 「应被 skip」变成**收集期错误**，整个套件连跑都跑不起来。
        #
        # 指向一个**必然拒绝连接**的本地端口后，失败变成 ConnectionRefusedError，
        # 它在 `h.request()` 内被包成 URLError → `access_pypi()` 如实返回 False →
        # 网络用例按其**既有设计**被 skip（不是跳过判定的绕过，而是让该判定
        # 真正生效）。no_proxy 保留本机回环，避免影响需要本地 socket 的用例。
        # 实测（本机）：基线 urlopen 返回 OK；指向 127.0.0.1:9 后 0.05s 内
        # URLError(ConnectionRefusedError)。
        env["http_proxy"] = env["https_proxy"] = env["all_proxy"] = \
            "http://127.0.0.1:9"
        env["no_proxy"] = "localhost,127.0.0.1,::1"
        env["PYTHONPATH"] = os.pathsep.join(
            ([shim] if shim else []) + [deps, self.source_folder]
            + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))

        # 上游 fixture 会清空 PYTHONPATH 跑子进程（见 _expose_deps_without_
        # pythonpath 的说明），故依赖必须另有不依赖 PYTHONPATH 的暴露途径，
        # 否则 `python -m virtualenv` 找不到 virtualenv、venv 建不出、fixture
        # 全灭（实测 28 个 ERROR）。
        pths = self._expose_deps_without_pythonpath(py, [deps])
        try:
            ok, err = self._importable_without_pythonpath(py, "virtualenv")
            if not ok:
                raise ConanException(
                    "upstream test deps are not importable without PYTHONPATH "
                    "after installing .pth hooks; the venv/build fixtures would "
                    "fail wholesale (R51: refusing to report an unrun suite as "
                    "passing). Import probe stderr:\n" + err)
            # 上游 fixtures.py 用 `python -m build` 构建 sdist/wheel，而 build
            # 默认建**隔离环境**；该路径在 OHOS 上失效（见 _prebuild_distributions
            # 的说明）→ 用上游自带的 PRE_BUILT_* 逃生口喂入配方预建的产物。
            sdist, wheel = self._prebuild_distributions(py, deps)
            env["PRE_BUILT_SETUPTOOLS_SDIST"] = sdist
            env["PRE_BUILT_SETUPTOOLS_WHEEL"] = wheel
            # 给用例体内的 pip 一个**本地 wheelhouse**。
            #
            # 为什么必须有：上游 test_namespaces 的两个用例在**用例体内**用 pip 安装
            # 一个本地包（`pip install <pkg> -t <dir>`），PEP 517 构建隔离要从索引取
            # `setuptools>=40.8.0`。而本配方的代理把外网挡死（让「无外网」成为确定
            # 事实），worker 上 pip **没有配置文件**、`pip config list` 为空，故按
            # `no_proxy` 放行镜像这条路在 worker 上取不到 host（CI #60818 实测：
            # 日志无 `[net]` 行，`127.0.0.1:9` 的 Connection refused 依旧）。
            #
            # 决定性证据（本机，逐字复刻死代理环境）：
            #   仅死代理 + 无 find-links            → `Could not find a version ...`
            #   + PIP_FIND_LINKS=<只含 wheel 的目录> → `Successfully installed`
            #   同上且把索引指向不可达地址          → 仍 `Successfully installed`
            # 即**不依赖任何网络**即可满足隔离需求。喂的正是本配方上一行刚预建好的
            # 那份 wheel，不引入新下载。只放 wheel（不放同目录的 sdist）：否则 pip
            # 可能挑中 sdist 去重建，反而又需要 setuptools。
            house = os.path.join(self.build_folder, "test-wheelhouse")
            os.makedirs(house, exist_ok=True)
            whl = os.path.join(house, os.path.basename(wheel))
            if not os.path.exists(whl):
                shutil.copy2(wheel, whl)
            env["PIP_FIND_LINKS"] = house
            env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
            self.output.info(
                f"[net] local wheelhouse for in-test pip: {house} "
                f"({', '.join(sorted(os.listdir(house)))})")
            # 测试用例按**裸名**调编译器（实测 `FileNotFoundError: 'clang'`
            # 连带 3× CompileError）：POSIX 下 posix_spawn 不搜 PATH（E405）。
            # 传入 profile 里的**绝对路径** CC/CXX 即可，distutils 优先读它们。
            compilers = (self.conf.get("tools.build:compiler_executables",
                                       default={}, check_type=dict) or {})
            for var, key in (("CC", "c"), ("CXX", "cpp")):
                exe = compilers.get(key)
                if exe:
                    env[var] = exe
                    self.output.info(f"upstream-test {var}={exe}")

            # 构建 C 扩展的用例要在**链接期**解析 `-lpython3.12`（该标志来自
            # 解释器自己的 LDSHARED）。dev 名缺失时 ld 报
            # `unable to find library -lpython3.12` —— 见 _libpython_link_env。
            env = self._libpython_link_env(py, env)

            self._run_pytest_suite(py, env)
        finally:
            # 必须清理：这些 ``.pth`` 落在**用户级** site-packages
            # （``~/.local/lib/pythonX.Y/site-packages``，见 _site_packages_dir
            # 为何不用系统目录），指向本次构建目录。构建目录随后被删，留下
            # 悬空路径条目会污染同一用户下的其他构建。
            for p in pths:
                try:
                    os.remove(p)
                except OSError:
                    pass

    def _run_pytest_suite(self, py, env):
        """跑上游 pytest 并如实判定（R51）；失败细节留给 CI 日志。"""
        # OHOS：新建文件/目录属主被文件系统强制显示为挂载属主（20001006），
        # 与进程 uid 不一致，pytest 默认 <tmp>/pytest-of-<user> 属主检查必然
        # INTERNALERROR；--basetemp 走 _given_basetemp 分支绕过该检查
        # （meson 1.11.0.1 先例）。
        # 叶子 basetemp 放在**自建的唯一父目录**下：pytest 的 getbasetemp() 在
        # 给了 basetemp 时走 `if exists(): rm_rf()` + `mkdir()`（**无**
        # exist_ok，`_pytest/tmpdir.py:158`）。OHOS 上 rm_rf 可能未真正删净
        # （错误被 on_rm_rf_error 吞掉），随后的 mkdir 即抛
        # `FileExistsError: [Errno 17] File exists`（pyenchant #12208 实测同款）。
        # 父目录全新 ⇒ 叶子必不存在 ⇒ 不走 rm_rf 分支。
        bt_parent = os.path.join(self.build_folder,
                                 f"pytest-basetemp-{os.getpid()}")
        os.makedirs(bt_parent, exist_ok=True)
        basetemp = os.path.join(bt_parent, "bt")
        env["TMPDIR"] = os.path.join(self.build_folder, "tmp")
        os.makedirs(env["TMPDIR"], exist_ok=True)

        report = os.path.join(self.build_folder, "upstream-pytest-report.txt")
        # 用**上游自带的** uses_network 标记排除联网用例，而不是把它们塞进
        # ALLOWED_TEST_FAILURES。构建沙箱无外网（CI 日志：已知不可达
        # ftp.gnu.org 等），这些用例会以 urlopen 失败告终，且属"环境无法提供
        # 网络"而非适配缺陷。实测证据：完整套件里
        # test_apply_pyproject_equivalent_to_setupcfg[...]（标记 uses_network，
        # 内部 retrieve_file → urlopen github raw）在两次运行中结果不稳定
        # （一次通过、一次 failing），正是网络可用性抖动的表现；其断言本身
        # 与 OHOS 无关。用上游标记排除可消除该不确定性，且不掩盖真实缺陷。
        # --timeout / --timeout-method=signal 必须显式给：pytest-timeout 虽在
        # 依赖集里，但此前从未把 --timeout 传给 pytest（那条 `--timeout 120` 是
        # **pip** 的参数），于是**没有任何单用例上限** —— CI #60058 里一个停滞
        # 的用例直接吃满外层 2400s，报告停在一行进度点、无 summary，无从定位。
        # signal 法（OHOS 上 SIGALRM/ITIMER_REAL 可用，已实测）是**抛异常**让该
        # 用例记为失败、套件继续跑完；thread 法是 os._exit(1)，会把整轮带走
        # （werkzeug 上踩过），故显式选 signal。
        cmd = [py, "-m", "pytest", "setuptools/tests", "-q", "--no-header",
               "-p", "no:cacheprovider", f"--basetemp={basetemp}",
               "-m", "not uses_network",
               f"--timeout={PER_TEST_TIMEOUT}", "--timeout-method=signal"]
        proc = subprocess.Popen(cmd, cwd=self.source_folder, env=env,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True,
                                start_new_session=True)
        try:
            out, _ = proc.communicate(timeout=2400)
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            import signal
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
            out, _ = proc.communicate()
            rc = 124
        with open(report, "w", encoding="utf-8") as fh:
            fh.write(out)
        # 成功时只留尾部提示；**失败时把失败明细打全**。理由：报告文件留在
        # worker 上、事后取不到，而 CI 日志本身还会再截断一次。此前只打末 8
        # 行，于是 45 个 ERROR 的 traceback（真正致因，如 fixture 内子进程的
        # stderr）在日志里完全看不到，排查只能靠猜。pytest `-q` 把 traceback
        # 放在 `=== FAILURES/ERRORS ===` 段，`short test summary info` 在末尾，
        # 故按「摘要行 + 失败段」摘录，而非单纯取尾部。
        if rc == 0:
            for line in out.strip().splitlines()[-8:]:
                self.output.info(f"[upstream-pytest] {line}")
        else:
            for line in self._failure_excerpt(out):
                self.output.error(f"[upstream-pytest] {line}")
        if rc == 124:
            raise ConanException(
                f"upstream pytest timed out (>2400s, suite did not finish); "
                f"see {report}")
        if rc != 0:
            # R9：失败不得被吞掉。解析失败用例并对比 ALLOWED_TEST_FAILURES——
            # 仅当**全部**失败都在清单内（平台环境性）才放行；清单外失败、
            # 或运行器异常退出导致解析不到失败项，均抛错使 conan create 失败。
            failed = self._parse_test_failures(out)
            if not failed:
                raise ConanException(
                    f"upstream pytest 运行器异常退出（exit={rc}），且未解析到"
                    f"失败用例，详见: {report}")
            unexpected = sorted(failed - ALLOWED_TEST_FAILURES)
            if unexpected:
                self.output.error(
                    f"上游 pytest 存在清单外失败: {unexpected}，详见: {report}")
                raise ConanException(
                    f"上游 pytest 失败（清单外 {len(unexpected)} 项）: "
                    f"{unexpected}，详见: {report}")
            self.output.warning(
                f"上游 pytest 存在 {len(failed)} 项已知平台环境性失败（均在"
                f"允许清单内）: {sorted(failed)}")
        self.output.info(f"upstream pytest passed; report: {report}")

    @staticmethod
    def _parse_test_failures(test_out):
        """从 pytest 输出中解析失败用例名（形如 ``FAILED path::name``）。

        返回不含前后端的用例名集合，以便与 ALLOWED_TEST_FAILURES 比较。
        """
        names = set()
        for line in (test_out or "").splitlines():
            line = line.strip()
            m = re.match(r"^(?:FAILED|ERROR)\s+(\S+)", line)
            if not m:
                continue
            node = m.group(1).rstrip(":")
            # 形如 setuptools/tests/test_wheel.py::test_wheel_mode[...]
            name = node.rsplit("::", 1)[-1]
            names.add(name.split("[", 1)[0])
        return names

    @staticmethod
    def _failure_excerpt(test_out, max_lines=400):
        """摘出足以定位根因的失败明细，供 CI 日志留存。

        取三部分而非单纯看尾部（``-q`` 的 traceback 不在尾部）：
          1. ``=== FAILURES ===`` / ``=== ERRORS ===`` 段 —— 含每个用例的
             traceback 与嵌套子进程的 stderr，**真正的致因在这里**；
          2. ``FAILED`` / ``ERROR`` 摘要行；
          3. 末尾计数行。
        超长时保留失败段的**开头**（最早、通常最典型）并附省略标记。
        """
        lines = (test_out or "").splitlines()
        picked, in_fail = [], False
        for line in lines:
            if re.match(r"^=+ (FAILURES|ERRORS) =+", line):
                in_fail = True
            elif re.match(r"^=+ [A-Z]", line):
                in_fail = False
            if in_fail:
                picked.append(line)
        for line in lines:
            if (re.match(r"(FAILED|ERROR) ", line)
                    or line.startswith("short test summary info")) \
                    and line not in picked:
                picked.append(line)
        for line in lines[-5:]:
            if line not in picked:
                picked.append(line)
        if len(picked) > max_lines:
            keep_head = max_lines - 30
            picked = (picked[:keep_head]
                      + [f"... [{len(picked) - keep_head - 25} more lines "
                         f"elided; full report on the build worker] ..."]
                      + picked[-25:])
        return picked

    # ---------------------------------------------------------------- package
    def _site_dir(self):
        return os.path.join(self.package_folder, "lib", "python3.12",
                            "site-packages")

    def package(self):
        site = self._site_dir()
        stage = self._stage_dir()
        installed = self._installed_site(stage)
        if not installed:
            raise ConanException(
                f"no installed site-packages found under {stage}")
        # 按登台树原样落入包内（含 setuptools/、_distutils_hack/、
        # distutils-precedence.pth 与 setuptools-*.dist-info）。
        copy(self, "*", src=installed, dst=site)

        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        # 载荷完整性校验：目录、hack 模块、.pth、以及**元数据目录**缺一不可。
        # 元数据缺失会让 setuptools/version.py 的
        # importlib.metadata.version('setuptools') 取不到版本（见模块 docstring）。
        #
        # 元数据目录两种布局都接受：`setup.py install` 产出 **egg-info**
        # （setuptools-84.0.0-py3.12.egg-info），PEP 517 wheel 安装才产出
        # dist-info。两者都受 importlib.metadata 识别——实测 egg-info 布局下
        # version('setuptools') == '84.0.0'、setuptools.__version__ == '84.0.0'
        # 均正常，故不可只认 dist-info（初版硬性要求 dist-info，导致
        # package() 误报 payload incomplete）。
        missing = [p for p in ("setuptools", "_distutils_hack",
                               "distutils-precedence.pth")
                   if not os.path.exists(os.path.join(site, p))]
        meta_dirs = [d for d in os.listdir(site)
                     if d.startswith("setuptools-")
                     and (d.endswith(".dist-info") or d.endswith(".egg-info"))]
        if not meta_dirs:
            missing.append("setuptools-*.dist-info|setuptools-*.egg-info")
        if missing:
            raise ConanException(
                f"setuptools payload incomplete, missing: {missing}")

    def package_info(self):
        # 纯 Python 模块：无 C/C++ 库可链接（R26 静态链接不适用）
        self.cpp_info.libs = []
        site = self._site_dir()
        # 用 runenv_info/buildenv_info 声明导入路径，使消费者（以及用
        # tool_requires 取它的构建型包）无需自行拼 PYTHONPATH。
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
        self.output.info(f"PYTHONPATH={site}")
