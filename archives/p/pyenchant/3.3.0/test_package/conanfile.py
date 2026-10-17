#!/usr/bin/env python3
"""Conan test_package for pyenchant 3.3.0 — import + real API test（R34）。

核心是验证 **ctypes → libenchant-2 的绑定真实可用**（本包唯一的集成风险）。

E502：OHOS worker 拒绝 dlopen/LD_PRELOAD **用户目录下**的共享库（**与 ELF 签名
无关**），而**同一文件作为 DT_NEEDED 在 exec 期加载则被接受**；且本机（交互设备
环境）更宽松，本地 dlopen 成功**不迁移**到 worker。本测试正是经 ctypes 加载
libenchant-2，故按 E502 做 **probe-then-route**：先探针，**仅在确实被策略拒绝时**
才改用**内嵌启动器**——把 libenchant-2.so 作为其自身 DT_NEEDED 链接进去，使该库
在进程启动时即已映射，随后 ctypes 按同一路径请求时命中的是已加载的映射。
"""
import os
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class PyenchantTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    # 与主配方 build() 阶段同一套内嵌启动器（那套已在 worker 上跑通）。
    # 用 PyConfig API 而非 Py_Initialize()：后者在「可执行文件路径推不出 prefix」
    # 时会让内嵌解释器找不到 stdlib。
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
    if (PyStatus_Exception(st)) { Py_ExitStatusException(st); }
    /* PyConfig.argv 的首元素被当作程序名消耗，故传完整 argv。 */
    st = PyConfig_SetBytesArgv(&config, argc, argv);
    if (PyStatus_Exception(st)) { Py_ExitStatusException(st); }
    st = Py_InitializeFromConfig(&config);
    PyConfig_Clear(&config);
    if (PyStatus_Exception(st)) { Py_ExitStatusException(st); }
    FILE *fp = fopen(argv[1], "r");
    if (!fp) { perror(argv[1]); Py_Finalize(); return 2; }
    int rc = PyRun_SimpleFileEx(fp, argv[1], 1);
    Py_Finalize();
    return rc == 0 ? 0 : 1;
}
"""

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _probe(self, python_exe, env, lib_file):
        """目标解释器能否直接 dlopen libenchant-2？返回 (accepted, policy_refused)。

        **必须区分两种失败**，否则会把无关故障当成策略拒绝而掩盖：
          - `policy_refused`：消息含 ``Permission denied``（E502）→ 才该改走 exec 期；
          - 其它（如 NEEDED 解析不到，消息含 ``needed by``）→ **不路由**，如实暴露。
        逐条短行输出、不截断多行 traceback（E502 明确要求）。
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
        """编一个把 libenchant-2.so 作为 DT_NEEDED 链接进去的内嵌 Python 启动器。"""
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

        src = os.path.join(build_dir, "ohc_tp_launcher.c")
        exe = os.path.join(build_dir, "ohc_tp_launcher")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write(self._LAUNCHER_SRC)
        cmd = [clang, "-Wno-deprecated-declarations", src, "-I", include_dir,
               libpython, lib_file,
               "-Wl,-rpath," + os.path.dirname(libpython), "-o", exe]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if res.returncode != 0:
            raise ConanException(
                "OHOS launcher compile failed: "
                + ((res.stdout or "") + (res.stderr or ""))[-400:])
        os.chmod(exe, 0o755)

        # 必须确认 libenchant-2 真进了 DT_NEEDED，否则 exec 期不会映射它，路由白做。
        chk = subprocess.run([objdump, "-d", exe], capture_output=True,
                             text=True, timeout=60)
        if "libenchant-2" not in (chk.stdout or ""):
            raise ConanException(
                "OHOS launcher: libenchant-2 did not land in the launcher's "
                "DT_NEEDED, so the runtime mapping would not happen:\n"
                + (chk.stdout or "")[-300:])
        return exe

    def test(self):
        if not can_run(self):
            return
        python_exe = sys.executable
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        pkg = self.dependencies["pyenchant"].package_folder
        site = os.path.join(pkg, "lib", py_ver, "site-packages")

        # PYENCHANT_LIBRARY_PATH 的语义是**库文件**路径，不是目录；传目录会被
        # dlopen 成目录并报 Permission denied。
        lib_dir = os.path.join(self.dependencies["enchant"].package_folder, "lib")
        lib_file = os.path.join(lib_dir, "libenchant-2.so")
        if not os.path.exists(lib_file):
            for name in sorted(os.listdir(lib_dir)):
                if name.startswith("libenchant-2.so"):
                    lib_file = os.path.join(lib_dir, name)
                    break

        # 整条依赖链的 lib 目录（enchant + glib + …）：libenchant-2.so 的 NEEDED
        # （libgio-2.0.so.0 等）必须在加载器搜索路径上。
        dep_dirs = []
        for dep in self.dependencies.values():
            for d in (getattr(dep.cpp_info, "libdirs", None) or []):
                if os.path.isdir(d) and d not in dep_dirs:
                    dep_dirs.append(d)
        ld = os.pathsep.join(dep_dirs + ["$LD_LIBRARY_PATH"])

        test_script = os.path.join(os.path.dirname(__file__), "test_pyenchant.py")

        env = dict(os.environ)
        env["PYTHONPATH"] = site
        env["LD_LIBRARY_PATH"] = os.pathsep.join(dep_dirs)
        accepted, policy_refused = self._probe(python_exe, env, lib_file)

        forced = os.environ.get("OHC_FORCE_LAUNCHER") == "1"
        if not accepted and not policy_refused:
            # 非策略拒绝 → 保持既有路径，让真实故障如实暴露，不掩盖。
            self.output.warning(
                "direct dlopen of libenchant-2 failed for a reason other than a "
                "loader policy refusal; staying on the direct path so the real "
                "error is not masked")

        if forced or (not accepted and policy_refused):
            launcher = self._build_launcher(python_exe, self.build_folder, lib_file)
            # 内嵌解释器必须知道 stdlib 在哪：launcher 是新建的可执行文件，按自身
            # 路径推 prefix 会落空 → `ModuleNotFoundError: No module named
            # 'encodings'`。故按运行本 test_package 的解释器显式给 PYTHONHOME
            # （该根下确有 stdlib 目录时才给；同批 zstandard 的同一课）。
            py_home = os.path.dirname(os.path.dirname(os.path.realpath(python_exe)))
            pyhome_arg = (f'PYTHONHOME="{py_home}" ' if os.path.isdir(
                os.path.join(py_home, "lib", py_ver)) else "")
            self.output.info(
                "loader refused dlopen of the user-directory library; running the "
                "consumer test through an exec-time launcher (E502)"
                + ("  [forced by OHC_FORCE_LAUNCHER]" if forced else ""))
            self.run(f'PYTHONPATH="{site}" {pyhome_arg}'
                     f'PYENCHANT_LIBRARY_PATH="{lib_file}" '
                     f'PYENCHANT_EXPECT_SITE="{site}" '
                     f'LD_LIBRARY_PATH="{ld}" '
                     f'"{launcher}" "{test_script}"', env="conanrun")
        else:
            self.run(f'PYTHONPATH="{site}" PYENCHANT_LIBRARY_PATH="{lib_file}" '
                     f'PYENCHANT_EXPECT_SITE="{site}" '
                     f'LD_LIBRARY_PATH="{ld}" '
                     f'{python_exe} "{test_script}"', env="conanrun")
