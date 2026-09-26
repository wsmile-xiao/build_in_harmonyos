#!/usr/bin/env python3
"""Conan recipe for pyenchant 3.3.0 — Enchant 拼写检查的 Python 绑定（纯 Python）。

**纯 Python（noarch）**：无 C/C++ 编译。pyenchant 3.x 通过 **ctypes** 在运行期
加载系统 `libenchant-2`（`enchant/_enchant.py`：优先 `PYENCHANT_LIBRARY_PATH`
环境变量，其次 `PYENCHANT_ENCHANT_PREFIX`，再退到 `ctypes.util.find_library`
逐个尝试 `libenchant-2` / `libenchant` / `libenchant-1`）。

**运行期依赖**：conan 包 `enchant/2.8.2`（ohpcd 已发布）。配方把该依赖的 `lib/`
目录通过 `PYENCHANT_LIBRARY_PATH` 与 `LD_LIBRARY_PATH` 暴露给运行期。

上游测试（R51 如实申报）：`tests/` 下 9 个文件。
"""
import os
import re
import subprocess
import sys
import uuid

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches

# 词典相关用例的允许清单。
#
# ⚠️ 根因不是「本机没装词典」，而是**依赖的 enchant/2.8.2 包不含任何 provider 插件**：
# `archives/e/enchant/2.8.2` 的 configure 显式禁用全部 provider
#   --without-aspell --without-hspell --without-hunspell
#   --without-nuspell --without-voikko --without-zemberek
# 故其产物里 `lib/` 下只有 libenchant-2.so*，**没有** enchant_hunspell.so 之类的
# provider；而 enchant 在运行期从 `//lib/enchant`（二进制内实测常量）加载 provider
# —— 该目录不存在，于是**任何词典都无法被加载**，即使把 en_US.dic/.aff 放进
# /usr/share/hunspell 也没用（无 provider 去读它）。
# 实测：本机 /usr/share/{hunspell,myspell,aspell} 均不存在；enchant 包内 0 个
# .dic/.aff；libenchant-2.so 内既无 hunspell/aspell 符号也无相关字符串。
# 因此凡需要真实词典（en_US 等）的用例必然失败/报错，报
# `enchant.errors.DictNotFoundError` / `DefaultLanguageNotFoundError`，或断言词典
# 存在的 AssertionError —— 属**上游 feature 裁剪（依赖方设计）**，非 pyenchant 缺陷。
# 逐项列出，命中才放行；出现清单外失败即报错。
ALLOWED_TEST_FAILURES = frozenset({
    # test_checker.py（Checker 需词典）
    "test_basic", "test_filters", "test_chunkers",
    "test_chunkers_and_filters", "test_filter_only", "test_chunkter_only",
    "test_unicode", "test_chararray", "test_pwl", "test_bug2785373",
    "test_replace_with_shorter_string", "test_replace_with_empty_string",
    # test_dict.py（Dict 需词典）
    "test_has_en_us", "test_check", "test_broker", "test_tag", "test_suggest",
    "test_suggest_hang_1", "test_unicode1", "test_session", "test_add_remove",
    "test_default_lang", "test_pickling",
    # 其它需词典的用例
    "test_docstrings", "test_can_use_multiprocessing",
    "test_dwpwl", "test_dwpwl_empty",
})


class PyenchantConan(ConanFile):
    name = "pyenchant"
    version = "3.3.0"
    description = "Python bindings for the Enchant spellchecking system"
    license = "LGPL-2.1"
    homepage = "https://pyenchant.github.io/pyenchant/"
    url = ""

    # 纯 Python noarch：无编译器需求
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # 运行期经 ctypes 加载 libenchant-2，由该 conan 依赖提供
        self.requires("enchant/2.8.2")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _py_ver(self):
        return f"python{sys.version_info.major}.{sys.version_info.minor}"

    def _staging_dir(self):
        """staging 落在**源码树之外**。

        pyenchant 的 `setup.cfg` 用 `packages = find:`（自动发现）；若 staging/
        与源码同级，可能被一并纳入包发现。而 conan 下 `source_folder` 与
        `build_folder` 相同，故取 `source_folder` 的**父目录**作为落点。
        """
        return os.path.join(
            os.path.dirname(os.path.normpath(self.source_folder)),
            "_staging_" + self.name)

    def _dep_lib_dirs(self):
        """所有（含**传递**）依赖的 lib 目录。

        `libenchant-2.so` 自身还依赖 glib（`libgio-2.0.so.0` / `libglib-2.0.so.0`；
        enchant/2.8.2 的 conaninfo 里 requires `glib/2.84.Z`）。故仅把 enchant 自己的
        lib 放进 LD_LIBRARY_PATH 不够 —— 实测报
        "Error loading shared library libgio-2.0.so.0: (needed by .../libenchant-2.so)"。
        把整条依赖链的 lib 目录都前置才能让加载器解析这些 NEEDED。
        """
        dirs = []
        for dep in self.dependencies.values():
            for libdir in (getattr(dep.cpp_info, "libdirs", None) or []):
                if os.path.isdir(libdir) and libdir not in dirs:
                    dirs.append(libdir)
        return dirs

    def _enchant_lib_dir(self):
        return os.path.join(self.dependencies["enchant"].package_folder, "lib")

    def _enchant_lib_file(self):
        """`PYENCHANT_LIBRARY_PATH` 的语义是**库文件路径**，不是目录。

        `enchant/_enchant.py` 的 `from_env_var()` 是 `assert os.path.exists(p)`
        后**原样返回**该值，随后 `ctypes.cdll.LoadLibrary(p)` —— 传目录会变成
        dlopen 一个目录，报 `Error loading shared library <dir>: Permission
        denied`（实测踩到）。（另一个环境变量 `PYENCHANT_ENCHANT_PREFIX` 走
        `from_prefix()`，但那是 Windows 的 `<prefix>/bin/libenchant-2.dll`
        布局，Linux 不适用。）

        优先取无版本后缀的 `.so`（加载器按 soname 解析到实体文件），退到带版本
        号的实体文件。
        """
        lib_dir = self._enchant_lib_dir()
        cand = os.path.join(lib_dir, "libenchant-2.so")
        if os.path.exists(cand):
            return cand
        if os.path.isdir(lib_dir):
            for name in sorted(os.listdir(lib_dir)):
                if name.startswith("libenchant-2.so"):
                    return os.path.join(lib_dir, name)
        return cand

    # ── OHOS worker 的 dlopen 路由（知识 E502）─────────────────────────────
    # CI worker 拒绝**进程启动后**映射用户存储目录下的共享库：dlopen 与
    # LD_PRELOAD 一律 `Permission denied`，且**与 ELF 签名是否有效无关**；
    # 同一文件作为 DT_NEEDED 在 exec 期加载则被接受（E502，PR !6848 实测；
    # 原文特别强调「本地 dlopen 成功不能推论到 worker」）。
    #
    # pyenchant 恰是「运行期 ctypes 按路径 dlopen」的形态，故在此做
    # probe-then-route：先探针；**仅当确实被拒**时改用内嵌 Python 启动器，把
    # libenchant-2 作为 DT_NEEDED 链接进去，使其在 exec 期即已映射——随后
    # pyenchant 的 `ctypes.cdll.LoadLibrary(<同一路径>)` 命中已加载对象，
    # 不再触发新的映射。dlopen 本就可用的环境（开发机）走原路径，行为不变。
    # 参考实现：archives/b/barvinok/0.41.9/conanfile.py。
    _OHOS_PY_LAUNCHER_SRC = """\
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdio.h>

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s SCRIPT [ARGS...]\\n", argv[0]);
        return 2;
    }
    Py_Initialize();
    wchar_t **wargv = PyMem_RawMalloc(sizeof(wchar_t *) * (size_t)argc);
    if (!wargv) {
        Py_Finalize();
        return 2;
    }
    for (int i = 1; i < argc; ++i)
        wargv[i - 1] = Py_DecodeLocale(argv[i], NULL);
    PySys_SetArgvEx(argc - 1, wargv, 0);
    for (int i = 1; i < argc; ++i)
        PyMem_RawFree(wargv[i - 1]);
    PyMem_RawFree(wargv);
    FILE *fp = fopen(argv[1], "r");
    if (!fp) {
        perror(argv[1]);
        Py_Finalize();
        return 2;
    }
    int rc = PyRun_SimpleFileEx(fp, argv[1], 1);
    Py_Finalize();
    return rc == 0 ? 0 : 1;
}
"""

    _PYTEST_RUNNER_SRC = """\
import os
import sys

import pytest

# 必须等价于 `python -m pytest`：`-m` 会把 CWD 并入 `sys.path[0]`，而被测包
# `enchant/` 就在源码树根（= 运行目录）下。内嵌解释器经 `PyRun_SimpleFileEx`
# 执行脚本不会做这件事，实测缺这一步即
# `ModuleNotFoundError: No module named 'enchant'`（收集期 8 个 ERROR）。
sys.path.insert(0, os.getcwd())

# 刻意**不** raise SystemExit：内嵌解释器里 SystemExit 会走到 C 的 exit()，
# 让 launcher 进程连同其进程组直接消失 —— 实测配方侧收不到任何 pytest 输出，
# 只看到 `ERROR: Exiting with code: 5` 并伴随 SIGTERM（连结果守卫都来不及跑）。
# 让脚本正常结束即可；pytest 的退出码由配方侧「无汇总行即失败」的守卫兜住。
pytest.main(sys.argv[1:])
sys.stdout.flush()
sys.stderr.flush()
"""

    def _dlopen_probe(self, python_exe, env, lib_file):
        """探针：目标解释器能否直接 dlopen 该库。返回 (accepted, policy_refused)。

        **必须区分两种失败**，否则会把无关故障误当成策略拒绝而掩盖掉：
          - `policy_refused=True`：失败原因是加载器策略拒绝（E502，消息含
            ``Permission denied``）——这才该改走 exec-time 路径；
          - 其它失败（如 NEEDED 依赖解析不到，消息形如 ``needed by``、
            errno 为 None）：说明环境本身有问题，**不路由**，让它如实暴露。

        逐条短行输出（不截断多行 traceback），便于在 CI 日志里定位「哪个文件、
        什么 errno」——E502 明确要求的形态。
        """
        probe = (
            "import ctypes, sys\n"
            "p = sys.argv[1]\n"
            "try:\n"
            "    ctypes.CDLL(p)\n"
            "except OSError as exc:\n"
            "    print('OHCDLOPEN REFUSED errno=%s ...%s' % (exc.errno, p[-58:]))\n"
            "    print('OHCDLOPEN MSG ...%s' % str(exc)[-70:])\n"
            "    sys.exit(1)\n"
            "print('OHCDLOPEN OK ...%s' % p[-58:])\n"
        )
        res = subprocess.run([python_exe, "-c", probe, lib_file],
                             capture_output=True, text=True, env=env, timeout=120)
        lines = ((res.stdout or "") + (res.stderr or "")).splitlines()
        for line in lines:
            if line.startswith("OHCDLOPEN"):
                self.output.info(line[:140])
        accepted = res.returncode == 0
        policy_refused = (not accepted) and any(
            "Permission denied" in line
            for line in lines if line.startswith("OHCDLOPEN MSG"))
        return accepted, policy_refused

    def _build_py_launcher(self, python_exe, build_dir, lib_file):
        """编一个把 libenchant-2 作为 DT_NEEDED 链接进去的内嵌 Python 启动器。"""
        objdump = "/data/service/hnp/bin/llvm-readelf"
        clang = "/data/service/hnp/bin/clang"
        detect = subprocess.run(
            [python_exe, "-c",
             "import os, sys, sysconfig\n"
             "root = os.path.dirname(os.path.dirname("
             "os.path.realpath(sys.executable)))\n"
             "print(sysconfig.get_paths()['include'])\n"
             "print(sysconfig.get_config_var('Py_ENABLE_SHARED'))\n"
             "print(os.path.join(root, 'lib', "
             "sysconfig.get_config_var('LDLIBRARY') or ''))\n"],
            capture_output=True, text=True, timeout=60)
        lines = (detect.stdout or "").splitlines()
        if detect.returncode != 0 or len(lines) < 3:
            raise ConanException(
                "OHOS launcher: python layout probe failed: "
                + (detect.stderr.strip()[-150:] or detect.stdout[-150:]))
        include_dir, shared, libpython = (lines[0].strip(), lines[1].strip(),
                                         lines[2].strip())
        if shared != "1" or not os.path.isfile(libpython):
            raise ConanException(
                "OHOS launcher: a shared libpython is required to embed the "
                f"interpreter (Py_ENABLE_SHARED={shared}, libpython={libpython})")
        if not os.path.isfile(os.path.join(include_dir, "Python.h")):
            raise ConanException(
                f"OHOS launcher: Python.h not found under {include_dir}")
        if not os.path.isfile(clang):
            raise ConanException(f"OHOS launcher: clang not found at {clang}")

        src = os.path.join(build_dir, "ohc_py_launcher.c")
        exe = os.path.join(build_dir, "ohc_py_launcher")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write(self._OHOS_PY_LAUNCHER_SRC)
        cmd = [clang, "-Wno-deprecated-declarations", src, "-I", include_dir,
               libpython, lib_file,
               "-Wl,-rpath," + os.path.dirname(libpython), "-o", exe]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if res.returncode != 0:
            raise ConanException(
                "OHOS launcher compile failed: "
                + ((res.stdout or "") + (res.stderr or ""))[-400:])
        os.chmod(exe, 0o755)

        # 必须确认 libenchant 真的进了 DT_NEEDED：否则 exec 期不会映射它，
        # 整个路由就白做（参考实现同样做这一步自校验）。
        chk = subprocess.run([objdump, "-d", exe], capture_output=True,
                             text=True, timeout=60)
        if "libenchant-2.so" not in (chk.stdout or ""):
            raise ConanException(
                "OHOS launcher: libenchant-2.so did not land in the launcher's "
                "DT_NEEDED, so the runtime mapping would not happen:\n"
                + (chk.stdout or "")[-300:])
        return exe

    def build(self):
        apply_conandata_patches(self)
        python_exe = sys.executable
        src_dir = self.source_folder
        staging = self._staging_dir()
        os.makedirs(staging, exist_ok=True)

        self.run(f'{python_exe} -m pip install --break-system-packages '
                 f'--timeout 120 --retries 3 setuptools wheel pytest')
        self.run(f'{python_exe} -m pip install --break-system-packages --no-deps '
                 f'--prefix="{staging}" "{src_dir}"')
        self._run_upstream_tests(python_exe, src_dir)

    @staticmethod
    def _parse_pytest_summary(out):
        """只从 pytest 的**权威短摘要**段解析失败集合。

        为什么不能对整份输出做正则：traceback、fixture 错误段与警告文本里都可能
        出现形如 ``ERROR <name>`` 的行。CI #12208 实测踩到 —— 配方报出清单外失败
        ``['test_add', 'test_unicodefn']``，但 pytest 的权威短摘要里 28 条
        失败/错误**全部**在允许清单内，这两个用例其实是**通过**状态（`35 passed`
        里就含它们）。把范围收敛到短摘要即可消除这一类**假阳性**。

        注意这**不是放宽判定**：短摘要才是 pytest 自己的结论；把范围放宽到整份
        输出反而会让 traceback 里的名字参与判定。

        返回 ``(bad, nodeids, count_line)``：
          - ``bad``：失败/错误用例名集合（取 ``::`` 最后一段，兼容
            ``file.py::Class::method``）；
          - ``nodeids``：失败/错误的完整 nodeid 列表（便于在日志里精确定位）；
          - ``count_line``：``N failed, M passed, ...`` 汇总行（全绿时也有）。
        若**既无**短摘要段**又无**计数行 → 套件没跑完，抛错（R51：不允许
        「什么都没验证」却报成功）。
        """
        lines = out.splitlines()
        count_line = ""
        for line in reversed(lines):
            if re.search(r"\d+ (?:passed|failed|error)", line):
                count_line = line
                break
        # 短摘要段可能出现多次，取**最后一次**（最终结论）
        idx = [i for i, l in enumerate(lines) if "short test summary info" in l]
        nodeids = []
        bad = set()
        if idx:
            for line in lines[idx[-1] + 1:]:
                m = re.match(r"^(?:FAILED|ERROR)\s+(\S+)", line)
                if m:
                    nodeid = m.group(1)
                    nodeids.append(nodeid)
                    bad.add(nodeid.rsplit("::", 1)[-1])
        elif not count_line:
            # 连短摘要和计数行都没有 = 套件**没有真正跑完**。实测踩到过：内嵌
            # launcher 分支下 pytest 收集到 0 个用例（exit code 5 =
            # NO_TESTS_COLLECTED），两样都为空 —— 此时判成功就是一次**假绿**。
            raise ConanException(
                "upstream pytest printed neither a short test summary nor a result "
                "count, so the suite did not run to completion (R51: refusing to "
                "report a passing build with nothing verified). Tail:\n"
                + "\n".join(lines[-30:]))
        # 一致性护栏：短摘要里解析到的**条目数**不得少于计数行里的 failed+errors，
        # 否则说明解析漏项 —— 少报失败即假绿（R51）。
        # 这里比的是条目数而非去重后的名字数：`test_check` 在 test_dict.py 与
        # test_pwl.py 各有一个，去重会少 1。
        n_failed = n_errors = 0
        if count_line:
            mf = re.search(r"(\d+) failed", count_line)
            me = re.search(r"(\d+) error", count_line)
            n_failed = int(mf.group(1)) if mf else 0
            n_errors = int(me.group(1)) if me else 0
        if len(nodeids) < n_failed + n_errors:
            raise ConanException(
                f"upstream pytest reported {n_failed} failed + {n_errors} errors "
                f"but only {len(nodeids)} failure/error entries could be parsed "
                "from the short summary, so some failures would go unreported "
                f"(R51). Summary line: {count_line!r}")
        return bad, nodeids, count_line

    def _run_upstream_tests(self, python_exe, src_dir):
        """运行上游套件并如实判定（R51），不做静默降级。"""
        env = dict(os.environ)
        # 让 ctypes 能找到 libenchant-2：PYENCHANT_LIBRARY_PATH 是 pyenchant 的
        # 首选查找途径；LD_LIBRARY_PATH 作为通用兜底（libenchant 自身还依赖
        # 其它库，如 libglib，故把依赖 lib 目录前置）。
        lib_dir = self._enchant_lib_dir()
        env["PYENCHANT_LIBRARY_PATH"] = self._enchant_lib_file()
        # 整条依赖链的 lib 目录（enchant + glib + …），否则 libenchant-2.so 的
        # NEEDED（libgio-2.0.so.0 等）解析不到
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            self._dep_lib_dirs()
            + [p for p in env.get("LD_LIBRARY_PATH", "").split(os.pathsep) if p])
        # 本机 pytest 环境两处与本任务无关的缺陷（详见 notes.md）：typeguard
        # 插件与 pytest 版本不兼容；断言重写抛 TypeError。均绕开。
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        # **必须显式给 --basetemp**：不给时 pytest 走 `tempfile.gettempdir()` →
        # `pytest-of-<user>` 那条分支，并在建目录后做属主检查
        # （`_pytest/tmpdir.py:198`）：
        #   OSError: The temporary directory .../pytest-of-100 is not owned by
        #            the current user. Fix this and try again.
        # 而 OHOS 上**新建目录的属主一律被文件系统显示为挂载属主**
        # （CI 为 100 / 本机实测为 20001006），与进程 uid 不符 → 该检查必然触发，
        # 使 `tests/test_pwl.py` 全部 6 个用例在 setup 阶段 ERROR（CI #12208 的
        # 3 个清单外失败 `test_add`/`test_pwl`/`test_unicodefn` 即由此而来）。
        # 给 `--basetemp` 则走另一分支，**不做属主检查**。
        # 本仓其它配方（setuptools / werkzeug / meson 1.11.0.1）早已这样做。
        #
        # ⚠️ 但**不能让该目录预先存在**（CI #12208 第二轮实测）：
        # `_pytest/pathlib.py:ensure_reset_dir()` 对已存在路径执行
        #     if path.exists(): rm_rf(path)      # on_rm_rf_error 会**吞掉**删除错误
        #     path.mkdir()                       # ← 无 exist_ok
        # OHOS 上 `rm_rf` 可能未真正删净（错误被 on_rm_rf_error 吸收），随后
        # `mkdir()` 即抛
        #     FileExistsError: [Errno 17] File exists
        # 且 `getbasetemp()` 是**惰性**调用，异常落在第一个真正用到 `tmp_path` 的
        # 用例上（实测 `ERROR tests/test_pwl.py::test_check - FileExistsError`），
        # 同时把 `test_add` 变成清单外失败。故改为给一个**唯一且不预创建**的路径，
        # 让 pytest 走朴素的 `mkdir()` 分支（`rm_rf` 不会执行）。
        # 叶子路径放在**我们自己新建**的唯一父目录下：pytest 的 `getbasetemp()`
        # 在给了 basetemp 时走 `if exists(): rm_rf()` + `mkdir()`（**无**
        # exist_ok）。父目录全新 ⇒ 叶子必不存在 ⇒ 完全不走 rm_rf 那条路，只剩
        # 一次必然成功的 mkdir。CI #12208 实测到 `FileExistsError: [Errno 17]
        # File exists` 落在 `getbasetemp()`（`_pytest/tmpdir.py:158` 的 mkdir），
        # 即出自 rm_rf 之后仍存在的那条路。
        bt_parent = os.path.join(
            self.build_folder,
            "pytest-basetemp-" + str(os.getpid()) + "-" + uuid.uuid4().hex[:8])
        os.makedirs(bt_parent)
        basetemp = os.path.join(bt_parent, "bt")
        pytest_args = (f"tests -q --assert=plain -p no:cacheprovider "
                       f"--basetemp={basetemp}")
        # probe-then-route（E502）：worker 拒绝 dlopen 用户存储目录下的 .so，
        # 而 pyenchant 正是运行期按路径 ctypes 加载 libenchant-2。故先探针，
        # **仅在确实被拒**时改走 exec-time 路径。OHC_FORCE_LAUNCHER=1 可在
        # 开发机上强制走该分支——本地 dlopen 本就可用，探针不会触发，而这条
        # 分支的机制只能这样在本地验证。
        forced = os.environ.get("OHC_FORCE_LAUNCHER") == "1"
        route = forced
        if not route:
            accepted, policy_refused = self._dlopen_probe(
                python_exe, env, env["PYENCHANT_LIBRARY_PATH"])
            route = (not accepted) and policy_refused
            if not accepted and not policy_refused:
                # 不是策略拒绝（例如 NEEDED 依赖解析不到）→ 保持原路径，让真实
                # 故障如实暴露，不要用 launcher 把它掩盖过去。
                self.output.warning(
                    "direct dlopen of libenchant-2 failed for a reason other "
                    "than a loader policy refusal; staying on the direct path "
                    "so the real error is not masked")
        if route:
            launcher = self._build_py_launcher(
                python_exe, self.build_folder, env["PYENCHANT_LIBRARY_PATH"])
            runner = os.path.join(self.build_folder, "ohc_run_pytest.py")
            with open(runner, "w", encoding="utf-8") as fh:
                fh.write(self._PYTEST_RUNNER_SRC)
            self.output.info(
                "loader refused dlopen of the user-directory library; routing "
                "the suite through an exec-time launcher (E502)"
                + ("  [forced by OHC_FORCE_LAUNCHER]" if forced else ""))
            cmd = f'{launcher} {runner} {pytest_args}'
        else:
            cmd = f'{python_exe} -m pytest {pytest_args}'
        proc = subprocess.run(cmd, shell=True, cwd=src_dir, env=env,
                              capture_output=True, text=True, timeout=1800)
        out = (proc.stdout or "") + (proc.stderr or "")
        # 只认 pytest 的**权威短摘要**（详见 _parse_pytest_summary 的说明）：
        # 对整份输出做正则会把 traceback/段落标题里的名字也算进来，CI #12208
        # 因此把**通过**的 test_add / test_unicodefn 误报为清单外失败。
        bad, nodeids, count_line = self._parse_pytest_summary(out)
        unexpected = sorted(bad - ALLOWED_TEST_FAILURES)
        if unexpected:
            unexpected_ids = [n for n in nodeids
                              if n.rsplit("::", 1)[-1] in set(unexpected)]
            raise ConanException(
                f"upstream pyenchant suite has failures outside the allow-list: "
                f"{unexpected} (R51: refusing to report a passing build with a "
                f"failing suite). Node ids: {unexpected_ids}. Tail:\n"
                + "\n".join(out.splitlines()[-30:]))
        if bad:
            self.output.warning(
                f"上游套件有 {len(bad)} 项失败/错误（依赖的 enchant 包无 provider "
                f"插件，任何词典都无法加载，已在允许清单内）: {sorted(bad)}")
        self.output.info("upstream pytest: " + count_line)

    def package(self):
        staging = self._staging_dir()
        py_ver = self._py_ver()
        site_dst = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        bin_dst = os.path.join(self.package_folder, "bin")

        site_src = None
        for candidate in (
            os.path.join(staging, "lib", py_ver, "site-packages"),
            os.path.join(staging, "lib", py_ver, "dist-packages"),
            os.path.join(staging, "local", "lib", py_ver, "site-packages"),
            os.path.join(staging, "local", "lib", py_ver, "dist-packages"),
        ):
            if os.path.isdir(candidate) and os.path.isdir(
                    os.path.join(candidate, "enchant")):
                site_src = candidate
                break
        if site_src is None:
            raise ConanException(
                f"pyenchant site-packages not found under staging={staging}")
        copy(self, "*", src=site_src, dst=site_dst)

        for bin_src in (os.path.join(staging, "bin"), os.path.join(staging, "local", "bin")):
            if os.path.isdir(bin_src):
                copy(self, "*", src=bin_src, dst=bin_dst)

    def package_info(self):
        site = os.path.join(self.package_folder, "lib", self._py_ver(), "site-packages")
        self.output.info(f"PYTHONPATH += {site}")
        self.env_info.PYTHONPATH.append(site)
        # 消费者也需要能找到 libenchant-2（注意：是**库文件路径**，非目录）
        self.env_info.PYENCHANT_LIBRARY_PATH = self._enchant_lib_file()
        self.env_info.LD_LIBRARY_PATH.append(self._enchant_lib_dir())
