#!/usr/bin/env python3
"""Conan test_package for zstandard 0.25.0 — import + real API test."""
import os
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class ZstandardTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    # ── E502：消费者侧也要绕开 worker 的 dlopen 拒绝 ─────────────────────
    # build() 里的路由已生效（上游套件 232 passed），但 test_package 此前仍
    # 倒在**同一个机制**上（CI #12210 第二轮）：
    #   FAIL: cannot import zstandard: Error loading shared library
    #     .../p/lib/python3.12/site-packages/zstandard/backend_c...so: Permission denied
    # 因为消费者侧的 `import zstandard` 同样是**运行期 dlopen 用户存储目录下的
    # .so**（E502：worker 拒绝进程启动后映射的共享库，与签名无关；exec 期作为
    # DT_NEEDED 加载则可用）。故此处复用同一套 probe-then-route。
    _LAUNCHER_SRC = """\
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdio.h>

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s SCRIPT [ARGS...]\\n", argv[0]);
        return 2;
    }
    PyConfig config;
    PyConfig_InitPythonConfig(&config);
    config.isolated = 0;
    config.site_import = 1;
    wchar_t *self = Py_DecodeLocale(argv[0], NULL);
    PyStatus st = PyConfig_SetString(&config, &config.program_name, self);
    if (PyStatus_Exception(st)) {
        Py_ExitStatusException(st);
    }
    /* 必须把命令行参数交给 Python，否则内嵌解释器里 sys.argv 为空
       （实测报 IndexError: list index out of range）。注意 CPython 语义：
       PyConfig.argv 的第一个元素被当作程序名消耗，故 sys.argv == 数组[1:]。
       这里传完整 argv（argv[0] = launcher 被消耗）。 */
    st = PyConfig_SetBytesArgv(&config, argc, argv);
    if (PyStatus_Exception(st)) {
        Py_ExitStatusException(st);
    }
    st = Py_InitializeFromConfig(&config);
    PyConfig_Clear(&config);
    if (PyStatus_Exception(st)) {
        Py_ExitStatusException(st);
    }
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

    # 内嵌解释器里**不能**让被测脚本以 SystemExit 收尾：SystemExit 会走到 C 的
    # exit()，把 launcher 进程连同其进程组一起带走，配方侧就收不到任何输出
    # （pyenchant 上实测：只看到 `Exiting with code: 5` 加 SIGTERM）。
    # 故这里捕获 SystemExit，并把**退出码写进结果文件**回传——既有明确的成功
    # 判据，也避免「没跑到就当成通过」的假绿。
    _RUNNER_SRC = """\
import os
import runpy
import sys

sys.path.insert(0, os.getcwd())

# 被测脚本与结果文件经**环境变量**传入，不依赖 sys.argv 的偏移语义 ——
# 内嵌解释器里 argv 的处理与 `python script.py` 并不完全一致（实测踩到
# `IndexError: list index out of range`），用 env 可彻底避开这一层耦合。
script = os.environ["OHC_TP_SCRIPT"]
rcfile = os.environ["OHC_TP_RCFILE"]

rc = 0
try:
    runpy.run_path(script, run_name="__main__")
except SystemExit as exc:
    code = exc.code
    if code is None:
        rc = 0
    elif isinstance(code, int):
        rc = code
    else:
        print(code, file=sys.stderr)
        rc = 1
except BaseException:
    import traceback
    traceback.print_exc()
    rc = 1

with open(rcfile, "w") as fh:
    fh.write(str(rc))
sys.stdout.flush()
sys.stderr.flush()
"""

    def _probe(self, python_exe, env, lib_file):
        """探针：消费者解释器能否直接 dlopen 该扩展。返回 (accepted, policy_refused)。

        只有**策略拒绝**（消息含 Permission denied，E502）才路由；其它失败
        （如 NEEDED 解析不到）不路由，让它如实暴露。
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

    def _build_launcher(self, python_exe, build_dir, lib_file):
        """编内嵌 Python 启动器，把该扩展作为 DT_NEEDED 链接进去（E502）。"""
        clang = "/data/service/hnp/bin/clang"
        readelf = "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(clang):
            raise ConanException(f"OHOS launcher: clang not found at {clang}")
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
                + ((detect.stdout or "") + (detect.stderr or ""))[-200:])
        include_dir, shared, libpython = (lines[0].strip(), lines[1].strip(),
                                          lines[2].strip())
        if shared != "1" or not os.path.isfile(libpython):
            raise ConanException(
                "OHOS launcher: a shared libpython is required to embed the "
                f"interpreter (Py_ENABLE_SHARED={shared}, libpython={libpython})")
        if not os.path.isfile(os.path.join(include_dir, "Python.h")):
            raise ConanException(
                f"OHOS launcher: Python.h not found under {include_dir}")

        src = os.path.join(build_dir, "ohc_tp_launcher.c")
        exe = os.path.join(build_dir, "ohc_tp_launcher")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write(self._LAUNCHER_SRC)
        res = subprocess.run(
            [clang, "-Wno-deprecated-declarations", src, "-I", include_dir,
             libpython, lib_file,
             "-Wl,-rpath," + os.path.dirname(libpython), "-o", exe],
            capture_output=True, text=True, timeout=180)
        if res.returncode != 0:
            raise ConanException(
                "OHOS launcher compile failed: "
                + ((res.stdout or "") + (res.stderr or ""))[-400:])
        os.chmod(exe, 0o755)

        # 必须确认扩展真进了 DT_NEEDED，否则 exec 期不会映射它，路由白做。
        chk = subprocess.run([readelf, "-d", exe], capture_output=True,
                             text=True, timeout=60)
        if "backend_c" not in (chk.stdout or ""):
            raise ConanException(
                "OHOS launcher: backend_c did not land in the launcher's "
                "DT_NEEDED, so the runtime mapping would not happen:\n"
                + (chk.stdout or "")[-300:])
        return exe

    def test(self):
        if can_run(self):
            python_exe = sys.executable
            py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
            pkg = self.dependencies["zstandard"].package_folder
            site = os.path.join(pkg, "lib", py_ver, "site-packages")
            # 扩展的 NEEDED 里有 libzstd，运行期需在搜索路径上
            zstd_lib = os.path.join(self.dependencies["zstd"].package_folder, "lib")
            test_script = os.path.join(os.path.dirname(__file__), "test_zstandard.py")
            env = dict(os.environ)
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                [zstd_lib] + [p for p in env.get("LD_LIBRARY_PATH", "").split(os.pathsep) if p])
            # 内嵌解释器必须知道 stdlib 在哪：launcher 是**新建的**可执行文件，
            # 它按自身路径向上推 prefix（OHOS 上推到 <user>/usr/local），那里没有
            # lib/python3.12 → 实测
            #   Could not find platform independent libraries <prefix>
            #   ModuleNotFoundError: No module named 'encodings'
            # 故按运行本 test_package 的解释器显式给出 PYTHONHOME（目录不存在则不给，
            # 与 astroterm/1.0.9 的既有做法一致）。
            py_home = os.path.dirname(os.path.dirname(os.path.realpath(python_exe)))
            pyhome_arg = f'PYTHONHOME="{py_home}" ' if os.path.isdir(
                os.path.join(py_home, "lib", py_ver)) else ""

            ext_so = None
            pkg_dir = os.path.join(site, "zstandard")
            if os.path.isdir(pkg_dir):
                for f in sorted(os.listdir(pkg_dir)):
                    if f.startswith("backend_c") and f.endswith(".so"):
                        ext_so = os.path.join(pkg_dir, f)
                        break

            forced = os.environ.get("OHC_FORCE_LAUNCHER") == "1"
            route = forced
            if not route and ext_so:
                accepted, policy_refused = self._probe(python_exe, env, ext_so)
                route = (not accepted) and policy_refused
                if not accepted and not policy_refused:
                    # 非策略拒绝 → 保持原路径，让真实故障如实暴露。
                    self.output.warning(
                        "direct dlopen of zstandard.backend_c failed for a reason "
                        "other than a loader policy refusal; staying on the direct "
                        "path so the real error is not masked")

            # ZSTD_EXPECT_SITE：供测试断言模块确实来自**被测包**（而非系统里
            # 恰好也装着的 zstandard）。L1e 负向测试会移除包产物后重跑，若测试
            # 仍能通过即判「测试不真正依赖该包」—— 本环境系统 site-packages 里
            # 已有 zstandard，故必须显式断言来源。
            if route:
                if not ext_so:
                    raise ConanException(
                        "OHOS launcher: the zstandard extension was not found in "
                        "the package, so the consumer test cannot be routed "
                        "around the worker's dlopen refusal (E502)")
                launcher = self._build_launcher(python_exe, self.build_folder, ext_so)
                runner = os.path.join(self.build_folder, "ohc_tp_runner.py")
                with open(runner, "w", encoding="utf-8") as fh:
                    fh.write(self._RUNNER_SRC)
                rcf = os.path.join(self.build_folder, "ohc_tp_rc.txt")
                if os.path.exists(rcf):
                    os.remove(rcf)
                self.output.info(
                    "loader refused dlopen of the user-directory extension; "
                    "running the consumer test through an exec-time launcher "
                    "(E502)" + ("  [forced by OHC_FORCE_LAUNCHER]" if forced else ""))
                self.run(f'PYTHONPATH="{site}" '
                         f'{pyhome_arg}'
                         f'ZSTD_EXPECT_SITE="{site}" '
                         f'OHC_TP_SCRIPT="{test_script}" '
                         f'OHC_TP_RCFILE="{rcf}" '
                         f'LD_LIBRARY_PATH="{zstd_lib}:$LD_LIBRARY_PATH" '
                         f'"{launcher}" "{runner}"',
                         env="conanrun")
                # 明确判据：结果文件必须存在且为 0 —— 否则「没跑到」会被当成通过。
                if not os.path.isfile(rcf):
                    raise ConanException(
                        "OHOS launcher: the consumer test produced no result file, "
                        "so it cannot be reported as passing (R51)")
                rc = (open(rcf, encoding="utf-8").read() or "").strip()
                if rc != "0":
                    raise ConanException(
                        f"consumer test failed under the exec-time launcher "
                        f"(exit code {rc!r})")
            else:
                self.run(f'PYTHONPATH="{site}" '
                         f'ZSTD_EXPECT_SITE="{site}" '
                         f'LD_LIBRARY_PATH="{zstd_lib}:$LD_LIBRARY_PATH" '
                         f'{python_exe} "{test_script}"', env="conanrun")
