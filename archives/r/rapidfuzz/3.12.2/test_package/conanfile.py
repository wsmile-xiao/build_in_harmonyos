#!/usr/bin/env python3
"""Conan test_package for rapidfuzz 3.12.2 — Python C extension consumer test.

层 2（消费者视角，R34）：test_rapidfuzz.py 用 conan 管理的 OHOS Python 3.12.9 真实
import 打包好的 rapidfuzz 并调用 fuzz / distance / process / utils 公开 API。

层 1（上游官方测试）：test_package/tests/ 是 rapidfuzz-3.12.2 sdist 中 tests/ 目录的
逐字副本（来源与清单见 MANIFEST.yml）。test() 用同一个解释器真实执行
`python3.12 -m pytest tests/ -q`，解析 pytest 自己输出的汇总行并打印
HMBS_UPSTREAM_TEST_RESULT，数字只来自真实命令输出，不伪造、不推断。

为什么上游 pytest 放在 test() 而不是 build()：
  * rapidfuzz 是 CPython 扩展，只有 package() 之后才落进
    lib/python3.12/site-packages，消费者视角的 import 就是上游用例的真实前提；
  * HMBS gate 只扫 test_package 阶段 stdout，且 conan create 命中缓存二进制时
    build() 会被整体跳过（pycairo/0.13.x 同款理由），marker 必须在 test() 发；
  * L1c 对整份 conan create 日志 grep "pytest"，本阶段输出同样满足该门禁；
  * airthings-ble / ld2410-ble / python-didl-lite 等既有包同为此模式。

解释器选择：必须用 self.dependencies["python"]（conan python/3.12.9）。扩展模块的
EXT_SUFFIX/SOABI 由 CMake FindPython 针对该解释器生成，换系统 python3 会直接
ImportError。pytest/hypothesis 为 py3-none-any 纯 Python 包，pip --target 装到临时
目录后用 PYTHONPATH 注入该解释器即可，谁的 pip 装的无所谓。

E212：CI worker 的 hmmac 安全标签可能拒绝 dlopen 用户路径下的 .so，消费者测试
失败时只有真正的动态加载拒绝才允许回退到 ELF 静态校验；上游 pytest 走真实 import，
失败即失败。
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualRunEnv


_E212_LOADER_CONTEXT = (
    "Error loading shared library",
    "Error relocating",
    "cannot open shared object file",
    "dlopen",
)
_E212_ERRNO_MARKERS = ("Permission denied", "EACCES")

# 上游测试根目录（相对本 conanfile.py），逐字拷贝自 sdist 的 tests/
_UPSTREAM_TESTS_DIR = "tests"
# 上游套件的硬依赖：test_hypothesis.py 顶层 `import hypothesis`，缺了整个收集都会炸
_PYTEST_MODULES = ("pytest", "hypothesis")
# 可选依赖（pytest.importorskip 门控）：装不上只跳过，如实告警
_NUMPY_MODULES = ("numpy",)
_PANDA_MODULES = ("pandas",)

# 默认 pip 配置之外的兜底索引（PyPI 官方镜像），仅在默认源拉不到时使用
_PIP_FALLBACK_INDEXES = ("https://pypi.tuna.tsinghua.edu.cn/simple",)


def _is_e212(text):
    """True only when the dynamic loader refused to load a packaged .so.

    Deliberately narrow: a failed assertion, a bad import or a missing symbol
    must stay a hard failure, otherwise the test would report success while the
    extension is unusable.
    """
    for line in str(text).splitlines():
        if not any(ctx in line for ctx in _E212_LOADER_CONTEXT):
            continue
        if any(m in line for m in _E212_ERRNO_MARKERS):
            return True
    return False


def _count(summary, word):
    """从 pytest 汇总行取 `N <word>`，取不到按 0 计（不猜）。"""
    m = re.search(r"(\d+)\s+" + word, summary)
    return int(m.group(1)) if m else 0


class RapidfuzzTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("python/3.12.9")
        # 上游 tests/ 里 16 项用例由 pytest.importorskip("numpy") 门控。OHOS 制品仓
        # 已发布 numpy/2.5.2（contourpy/1.2.1 主配方同款裸引用；audioflux/0.1.9 的
        # test_package 也直接 requires numpy），装上这 16 项才真正执行而不是 skip。
        self.requires("numpy/2.5.2")
        # libffi：python/3.12.9 依赖它，但它的 lib/ 不在本 test_package 依赖图的
        # LD_LIBRARY_PATH 里，导致 <py>/lib/python3.12/lib-dynload/_ctypes*.so
        # 载入失败（"ffi_prep_closure_loc: symbol not found"）→ pandas 无法 import
        # → 2 项 pd.NA 用例只能 importorskip 跳过。显式 requires 让其 lib/ 进搜索
        # 路径，_ctypes 正常载入，pandas 才有机会真正执行。
        self.requires("libffi/3.5.2")

    # ───────────────────────── environment helpers ─────────────────────────
    def _py_bin(self):
        return os.path.join(self.dependencies["python"].package_folder, "bin", "python3.12")

    def _lib_dirs(self):
        dirs = [os.path.join(self.dependencies["python"].package_folder, "lib")]
        for dep in self.dependencies.values():
            if dep.package_folder:
                dirs.append(os.path.join(dep.package_folder, "lib"))
        return dirs

    def _site_dirs(self):
        """所有依赖包里的 lib/python*/site-packages（rapidfuzz 自身 + numpy 等）。"""
        out = []
        for dep in self.dependencies.values():
            if dep.package_folder:
                out.extend(sorted(glob.glob(
                    os.path.join(dep.package_folder, "lib", "python*", "site-packages"))))
        # 去重但保持顺序
        seen, uniq = set(), []
        for d in out:
            if d not in seen:
                seen.add(d)
                uniq.append(d)
        return uniq

    def _target_env(self, pythonpath):
        """conan python/3.12.9 的运行环境（与消费者测试 self.run 的那套一致）。"""
        env = dict(os.environ)
        env["PYTHONHOME"] = self.dependencies["python"].package_folder
        env["LD_LIBRARY_PATH"] = os.pathsep.join(self._lib_dirs())
        # 空 PYTHONPATH 等于把 '' 塞进 sys.path（当前目录），显式清掉
        merged = list(pythonpath)
        if os.environ.get("PYTHONPATH"):
            merged.append(os.environ["PYTHONPATH"])
        if merged:
            env["PYTHONPATH"] = os.pathsep.join(merged)
        else:
            env.pop("PYTHONPATH", None)
        # 不往仓库目录里写 __pycache__（junk_check JC4）
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
        env["PIP_NO_INPUT"] = "1"
        return env

    def _probe_import(self, py_bin, env, modules):
        """真实起一个子进程 import，返回 (是否成功, 输出尾部)。"""
        try:
            r = subprocess.run(
                [py_bin, "-c", "import " + ", ".join(modules)],
                env=env, capture_output=True, timeout=300,
            )
        except Exception as exc:  # noqa: BLE001
            return False, repr(exc)
        detail = ((r.stdout or b"") + (r.stderr or b"")).decode(errors="replace")
        return r.returncode == 0, detail[-800:]

    def _pip_into(self, target, modules, indexes):
        """把纯 Python 包 pip 装进 target 临时目录，返回 (是否成功, 日志尾部)。

        轮询可用的解释器与索引：谁有 pip 谁装都行（产物是 py3-none-any 纯 Python），
        装完由 PYTHONPATH 注入真正的 conan python。失败就清空目录，不留半装残留。
        """
        os.makedirs(target, exist_ok=True)
        runners = []
        for cand in (sys.executable, shutil.which("python3"), self._py_bin()):
            if cand and os.path.isfile(cand) and cand not in runners:
                runners.append(cand)
        logs = []
        for runner in runners:
            for idx in ("",) + tuple(indexes):  # "" = 用环境默认 pip 配置
                cmd = [runner, "-m", "pip", "install", "--no-input",
                       "--disable-pip-version-check", "--no-compile",
                       "--target", target, *modules]
                if idx:
                    cmd += ["--index-url", idx]
                # 给别的解释器跑 pip 时不能带 PYTHONHOME（那是 conan python 的前缀）
                if runner == self._py_bin():
                    env = self._target_env([])
                else:
                    env = {k: v for k, v in os.environ.items() if k != "PYTHONHOME"}
                    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
                    env["PIP_NO_INPUT"] = "1"
                try:
                    r = subprocess.run(cmd, env=env, capture_output=True, timeout=300)
                except Exception as exc:  # noqa: BLE001
                    logs.append(f"{os.path.basename(runner)}[{idx or 'default'}] {exc!r}")
                    continue
                out = ((r.stdout or b"") + (r.stderr or b"")).decode(errors="replace")
                if r.returncode == 0:
                    self.output.info(
                        f"pip ok: {runner} -> {' '.join(modules)} "
                        f"({'default index' if not idx else idx})")
                    return True, out[-400:]
                logs.append(
                    f"{os.path.basename(runner)}[{idx or 'default'}] "
                    f"rc={r.returncode} {out[-260:].strip()}")
                shutil.rmtree(target, ignore_errors=True)
                os.makedirs(target, exist_ok=True)
        return False, " | ".join(logs)[-1500:]

    def _ensure_modules(self, py_bin, modules, site_dirs, required, indexes):
        """确保 conan python 能 import modules；成功则把注入目录追加到 site_dirs。"""
        ok, detail = self._probe_import(py_bin, self._target_env(site_dirs), modules)
        if ok:
            self.output.info(f"probe ok: {' '.join(modules)} already importable")
            return site_dirs, True

        target = tempfile.mkdtemp(prefix="rf-upstream-deps-")  # TMPDIR 下，不污染仓库
        pip_ok, log = self._pip_into(target, modules, indexes)
        if pip_ok:
            ok, detail = self._probe_import(
                py_bin, self._target_env(site_dirs + [target]), modules)
            if ok:
                return site_dirs + [target], True
            log = f"probe after pip install failed: {detail}"

        if not required:
            self.output.warning(
                f"optional deps unavailable: {' '.join(modules)}; {log[-600:]}")
            return site_dirs, False
        raise ConanException(
            f"无法让上游 pytest 依赖 {' '.join(modules)} 可导入，上游套件无法执行: {log}")

    # ───────────────────────── upstream pytest (layer 1) ─────────────────────────
    def _run_upstream_pytest(self, site):
        here = os.path.dirname(os.path.abspath(__file__))
        tests_dir = os.path.join(here, _UPSTREAM_TESTS_DIR)
        if not os.path.isdir(tests_dir):
            raise ConanException(
                f"上游 tests/ 未 vendor 到 test_package: {tests_dir}（见 MANIFEST.yml）")

        py_bin = self._py_bin()
        site_dirs = self._site_dirs()
        # 保险：被测包自己的 site-packages 必须排在最前（其他依赖的 PYTHONPATH 不能盖住它）
        if site not in site_dirs:
            site_dirs.insert(0, site)

        # numpy：conan 依赖已在 PYTHONPATH 上，只探测不额外装（OHOS 无 numpy 轮子）
        ok, detail = self._probe_import(py_bin, self._target_env(site_dirs), _NUMPY_MODULES)
        if ok:
            self.output.info("probe ok: numpy importable -> 16 项 numpy 用例将真实执行")
        else:
            self.output.warning(
                "numpy 不可导入，上游 16 项 importorskip(\"numpy\") 用例将跳过: "
                + detail.replace("\n", " "))

        # pytest + hypothesis：上游套件硬依赖（缺 hypothesis 无法收集）
        site_dirs, _ = self._ensure_modules(
            py_bin, _PYTEST_MODULES, site_dirs, required=True,
            indexes=_PIP_FALLBACK_INDEXES)

        # pandas：可选，只有 2 项用例门控（test_process.py 的 pd.NA / issue81）
        site_dirs, pd_ok = self._ensure_modules(
            py_bin, _PANDA_MODULES, site_dirs, required=False,
            indexes=_PIP_FALLBACK_INDEXES)
        if pd_ok:
            self.output.info("probe ok: pandas importable -> 2 项 pandas 用例将真实执行")

        cmd = [
            py_bin, "-m", "pytest", tests_dir,
            "-q", "--no-header", "--color=no",
            "-p", "no:cacheprovider",   # 不在仓库目录留 .pytest_cache
            "-o", "addopts=",           # sdist 的 pyproject 不在场，显式清空以防串味
        ]
        env = self._target_env(site_dirs)
        # hypothesis 的落盘目录挪到 TMPDIR
        env["HYPOTHESIS_STORAGE_DIRECTORY"] = tempfile.mkdtemp(prefix="rf-hypothesis-")

        self.output.info("running upstream pytest: " + " ".join(cmd))
        try:
            res = subprocess.run(cmd, env=env, cwd=here, capture_output=True,
                                 timeout=1800)
        except subprocess.TimeoutExpired:
            raise ConanException("上游 pytest 超时 (1800s)")

        out = ((res.stdout or b"") + (res.stderr or b"")).decode(errors="replace")
        # 原样回灌 CI 日志：L1b/L1c 的证据就在这里
        for line in out.splitlines():
            self.output.info(line)

        passed = _count(out, "passed")
        failed = _count(out, "failed")
        skipped = _count(out, "skipped")
        errors = _count(out, "errors?")  # 同时匹配 "N error" / "N errors"
        discovered = passed + failed + skipped + errors

        note = ""
        if skipped:
            note = ("skipped 用例由 pytest.importorskip 门控（numpy/pandas 在 OHOS 无可用"
                    "分发时按上游设计跳过），非用例失败")
        marker = {
            "status": "passed" if res.returncode == 0 else "failed",
            "framework": "pytest",
            "command": " ".join(cmd),
            "discovered": discovered,
            "executed": passed + failed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "errors": errors,
        }
        if note:
            marker["note"] = note
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))

        if discovered == 0:
            raise ConanException(
                f"上游 pytest 未收集到任何用例（可能收集期就炸了），输出尾部: {out[-600:]}")
        if res.returncode != 0:
            raise ConanException(
                f"上游 pytest 失败 (exit {res.returncode}): "
                f"{passed} passed, {failed} failed, {skipped} skipped, {errors} errors")
        self.output.info(
            f"upstream pytest: {passed} passed, {failed} failed, {skipped} skipped, "
            f"{errors} errors (discovered {discovered})")

    # ───────────────────────── E212 fallback ─────────────────────────
    def _elf_static_check(self, site):
        """E212 回退：CI hmmac 禁止 dlopen 用户路径时对打包产物做静态校验。"""
        rf_dir = os.path.join(site, "rapidfuzz")
        so_files = sorted(glob.glob(os.path.join(rf_dir, "**", "*.so"), recursive=True))
        if not so_files:
            raise Exception("No .so files found in rapidfuzz package")

        readelf = "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(readelf):
            readelf = "readelf"

        for so in so_files:
            hdr = subprocess.run([readelf, "-h", so], capture_output=True, text=True)
            if hdr.returncode != 0 or "ELF" not in hdr.stdout:
                raise Exception(f"{os.path.basename(so)} is not a valid ELF")
            if "AArch64" not in hdr.stdout:
                raise Exception(f"{os.path.basename(so)} is not AArch64")
            # On Linux, Python extensions resolve libpython symbols at runtime
            # via the interpreter, not by linking. So we only check that the
            # .so is a valid AArch64 ELF and exports the expected PyInit_ symbol.
            syms = subprocess.run([readelf, "-Ws", so], capture_output=True, text=True)
            name = os.path.splitext(os.path.basename(so))[0]
            pydot = name.split(".")[0]
            if f"PyInit_{pydot}" not in syms.stdout:
                raise Exception(f"{os.path.basename(so)} missing PyInit_{pydot}")
            self.output.info(f"  {os.path.basename(so)}: ELF+AArch64+PyInit OK")

        self.output.info(f"PASS (E212 fallback): {len(so_files)} .so files validated")

    # ───────────────────────── C extension gate ─────────────────────────
    # 名字与打包布局一致（CMake 把 _initialize_cpp 放在 distance/ 子包下）：
    #   顶层 rapidfuzz/  → fuzz_cpp / utils_cpp / process_cpp_impl
    #   distance/ 子包   → metrics_cpp / _initialize_cpp
    # 这些名字都没有纯 Python 兜底，`import rapidfuzz` 却在扩展载入失败时
    # 静默回退到 *_py 实现——CI #63465 就这样让消费者测试"通过"，而上游
    # pytest 收集期 16 个模块全部 ImportError。这里显式探测，失败即红，
    # 只有真正的 loader 拒绝（E212）才允许走静态校验回退。
    _CPP_MODULES = (
        "rapidfuzz.fuzz_cpp",
        "rapidfuzz.utils_cpp",
        "rapidfuzz.process_cpp_impl",
        "rapidfuzz.distance.metrics_cpp",
        "rapidfuzz.distance._initialize_cpp",
    )

    def _cpp_extension_gate(self, py_bin, site):
        """必须能真正 import 编译扩展；否则本包等于退化成纯 Python 实现。

        这些模块名没有纯 Python 兜底，`import rapidfuzz` 却在扩展载入失败时
        静默回退到 *_py 实现——CI #63465 就这样让消费者测试"通过"，而上游
        pytest 收集期 16 个模块全部 ImportError。这里显式探测，失败即红，
        只有真正的 loader 拒绝（E212）才允许走静态校验回退。

        逐个模块 import 并汇总**全部**失败原因：一次性串联 import 只会报出
        第一个错误，掩盖其余模块的真实状态（#63485 就这样把模块名写错却只
        看到一句 ModuleNotFoundError）。
        """
        env = self._target_env([site])
        code = (
            "import importlib\n"
            "bad = []\n"
            f"for _name in {list(self._CPP_MODULES)!r}:\n"
            "    try:\n"
            "        importlib.import_module(_name)\n"
            "    except Exception as _exc:\n"
            "        bad.append('%s -> %s: %s' % (_name, type(_exc).__name__, _exc))\n"
            "print('CPP_OK' if not bad else 'CPP_BAD')\n"
            "for _line in bad:\n"
            "    print('  ' + _line)\n"
        )
        try:
            proc = subprocess.run([py_bin, "-c", code], env=env,
                                  capture_output=True, timeout=300)
        except Exception as exc:  # noqa: BLE001
            return False, repr(exc)
        detail = ((proc.stdout or b"") + (proc.stderr or b"")).decode(errors="replace")
        if "CPP_OK" in detail:
            self.output.info(
                f"C extension gate: all {len(self._CPP_MODULES)} compiled modules importable")
            return True, detail
        return False, detail

    # ───────────────────────── test() ─────────────────────────
    def test(self):
        rf_pkg = self.dependencies["rapidfuzz"].package_folder
        site = os.path.join(rf_pkg, "lib", "python3.12", "site-packages")
        test_script = os.path.join(self.source_folder, "test_rapidfuzz.py")

        py = self.dependencies["python"]
        py_pkg = py.package_folder
        py_bin = os.path.join(py_pkg, "bin", "python3.12")
        ld_path = os.pathsep.join(self._lib_dirs())

        # 门禁：编译扩展必须真的能载入（CI #63465 的教训）
        cpp_ok, cpp_detail = self._cpp_extension_gate(py_bin, site)

        # 层 2: 真实消费者测试 —— conan 管理的 OHOS Python 3.12.9 直接 import 产物
        if cpp_ok:
            self.run(
                f'unset LD && '
                f'export PYTHONHOME="{py_pkg}" && '
                f'export LD_LIBRARY_PATH="{ld_path}" && '
                f'export PYTHONPATH="{site}:$PYTHONPATH" && '
                f'PYTHONDONTWRITEBYTECODE=1 '
                f'"{py_bin}" "{test_script}"',
            )
        else:
            for line in cpp_detail.splitlines():
                self.output.info(f"  cpp-gate: {line}")
            if _is_e212(cpp_detail):
                # E212：hmmac 拒绝 dlopen 用户路径 .so，只做打包产物静态校验
                self.output.warning("E212: falling back to ELF static validation")
                self._elf_static_check(site)
                raise ConanException(
                    "E212: 编译扩展被 hmmac 拒绝 dlopen，无法真实执行上游 pytest 套件"
                    "（本包已通过 ELF 静态校验，但不能宣称上游测试已执行）")
            raise ConanException(
                "编译扩展无法导入（等效于退化成纯 Python 实现，测试无意义）。\n"
                + cpp_detail[-1500:])

        # 层 1: 上游官方 pytest 套件（129 个测试函数 / 386 个参数化用例项）
        self._run_upstream_pytest(site)
