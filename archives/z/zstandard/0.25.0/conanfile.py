#!/usr/bin/env python3
"""Conan recipe for zstandard 0.25.0 — zstd 压缩的 Python 绑定（C 扩展）。

**C 扩展**包：`zstandard.backend_c`（另有 **Rust 后端** `zstandard.backend_rust`，
但上游默认关闭 —— `setup.py: RUST_BACKEND = False`，需显式 `--rust-backend`
才构建。**CI 无 Rust 工具链**（SKILL.md CI 能力矩阵），故本配方保持默认不触发）。

zstd C 库来源：上游默认**捆绑** `zstd/` 源码编译；本配方改用 conan 依赖
`zstd/1.5.7` + `setup.py --system-zstd`（`setup_zstd.get_c_extension` 在
`system_zstd=True` 时设 `libraries=["zstd"]` 且不再加捆绑头目录，头/库路径由
CFLAGS/LDFLAGS 提供）。

为什么走 `bdist_wheel` 两步而非直接 `pip install`：`--system-zstd` 是 setup.py
的 **argv 开关**（`sys.argv.remove("--system-zstd")`），pip 的 PEP517 构建路径
无法透传自定义 argv。故先 `setup.py bdist_wheel --system-zstd` 产出 wheel，
再 `pip install` 该 wheel（不再重建），确保扩展确实是链到 conan 的 zstd。
"""
import os
import re
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches

# 上游明示的取舍：`c-ext/python-zstandard.h` 里
#     #ifdef ZSTD_SINGLE_FILE
#     #include <zstd.c>
#     /* We use private APIs from pool.h. We can't rely on availability
#        of this header or symbols when linking against the system libzstd.
#        But we know it works when using the bundled single file library. */
#     #define HAVE_ZSTD_POOL_APIS
#     #else
#     #include <zdict.h> / <zstd.h>
#     #endif
# 而 `setup_zstd.py` 的 system_zstd 分支**不**加 `-DZSTD_SINGLE_FILE`。
# 故用 `--system-zstd` 时 `multi_compress_to_buffer`/`multi_decompress_to_buffer`
# 必然缺席 —— 这是**上游有意为之**（链接系统 libzstd 时无法依赖 pool.h 私有 API），
# 而上游 `test_features` 是按捆绑构建写的。本配方选择用 conan 的 zstd 依赖
# （不捆绑上游 zstd 源码），故该项据实列入允许清单，引上游注释为据。
ALLOWED_TEST_FAILURES = frozenset({"test_features"})


class ZstandardConan(ConanFile):
    name = "zstandard"
    version = "0.25.0"
    description = "Zstandard bindings for Python"
    license = "BSD-3-Clause"
    homepage = "https://github.com/indygreg/python-zstandard"
    url = ""

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # C 扩展链到 conan 的 zstd（--system-zstd）
        self.requires("zstd/1.5.7")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _py_ver(self):
        return f"python{sys.version_info.major}.{sys.version_info.minor}"

    def _staging_dir(self):
        """wheel 的安装目标目录（`pip install --target`）。

        用 `--target` 而非 `--prefix`：后者依赖 `<prefix>/lib/pythonX.Y/...`
        布局，实测装完 staging 仍为空（未落到预期位置）；`--target` 语义明确，
        内容直接平铺进该目录（含 .dist-info），打包时整目录拷入 site-packages。
        该目录放在 `build_folder` 下（仅作拷贝目标，不参与 setuptools 包发现 ——
        zstandard 的构建在它生成之前就已完成）。
        """
        return os.path.join(self.build_folder, "_wheel_target")

    def _zstd_dirs(self):
        dep = self.dependencies["zstd"]
        return (os.path.join(dep.package_folder, "include"),
                os.path.join(dep.package_folder, "lib"))

    def _abs_compiler_paths(self):
        """绝对路径的 C/C++ 编译器。

        根因：OHOS 上 `os.posix_spawn()` **不做 PATH 查找**（只有 `posix_spawnp()`
        才做），而 CPython 的 `subprocess` 恰好走 posix_spawn → **裸名 exec 一律
        `FileNotFoundError`**。上游 `make_cffi.py` 用 distutils 的 compiler
        （`customize_compiler()` honors CC，见其 :45/:53 注释）跑
        `Popen(['clang', '-E', ...])` 预处理 zstd 头 → CI 实测
        `FileNotFoundError: [Errno 2] No such file or directory: 'clang'`，
        build() 直接失败（本地因环境另有 posix_spawn 覆盖而侥幸通过，掩盖了该问题）。

        故优先取 conan profile 的 `tools.build:compiler_executables`（CI 的
        ohos-aarch64 profile 已声明 `{'c': '/data/service/hnp/bin/clang', ...}`），
        退到 `shutil.which()`（Python 自行查 PATH，不依赖 exec）。
        """
        conf = {}
        try:
            conf = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
        except Exception:
            conf = {}
        cc = conf.get("c") or shutil.which("clang") or "clang"
        cxx = conf.get("cpp") or shutil.which("clang++") or "clang++"
        return cc, cxx

    def _sign_if_needed(self, path):
        """OHOS loader 只接受**已签名**的 ELF —— 对构建产物做鸿蒙自签名。

        CI #59696 实测：未签名的 `backend_c…so` 被 loader 拒载
          ImportError: Error loading shared library .../backend_c.cpython-312-aarch64-linux-ohos.so: Permission denied
        → 25 个测试文件收集期全错。本地 dev 域不校验 ELF 签名，故此前「本地绿」。
        非 ELF（如 .py）跳过；签名工具不存在时告警跳过（非 OHOS 环境下 loader
        不校验签名，产物仍可用）。
        """
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not (os.path.isfile(objcopy) and os.path.isfile(signer)):
            self.output.warning(
                f"signing tools unavailable; leaving {path} unsigned "
                f"(only OHOS loaders enforce ELF signatures)")
            return
        try:
            with open(path, "rb") as fh:
                if fh.read(4) != b"\x7fELF":
                    return
        except OSError:
            return
        mode = os.stat(path).st_mode
        tmp = f"{path}.signing"
        try:
            shutil.copy2(path, tmp)
            self.run(f'"{objcopy}" --remove-section .codesign "{tmp}" || true')
            self.run(f'"{signer}" sign -inFile "{tmp}" -outFile "{tmp}" -selfSign 1')
            os.chmod(tmp, mode)
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    def _sign_built_extensions(self, *bases):
        """对给定目录树下的所有 .so 产物签名（源码树 inplace 副本 + 装进包的那份）。"""
        signed = 0
        for base in bases:
            if not base or not os.path.isdir(base):
                continue
            for root, _dirs, files in os.walk(base):
                for f in files:
                    if ".so" in f:
                        self._sign_if_needed(os.path.join(root, f))
                        signed += 1
        self.output.info(f"signing pass done over {signed} .so file(s)")

    # ── worker 的 dlopen 路由（知识 E502）──────────────────────────────────
    # CI #59696 曾把「加载被拒」判为**未签名**（故加了 _sign_if_needed），但
    # CI #59718/#12210 显示：**签名已确实生效**（日志 `signing pass done over
    # 8 .so file(s)`，且含随后报拒的那条确切路径）后仍报
    #   ImportError: Error loading shared library .../backend_c...so: Permission denied
    # 说明签名不是决定因素。真因是 E502：worker 拒绝**进程启动之后**映射用户存储
    # 目录下的共享库（dlopen / LD_PRELOAD），**与签名是否有效无关**；同一文件作为
    # DT_NEEDED 在 **exec 期**加载则被接受（PR !6848 实测）。
    #
    # 故 probe-then-route：先探针，**仅在确实被策略拒绝**时编译一个内嵌 Python
    # 启动器，把该扩展作为其自身 DT_NEEDED 链接进去，经它跑套件 —— 扩展在 exec
    # 期即已映射，pytest 收集期 `import zstandard.backend_c` 命中已加载对象。
    # dlopen 本就可用的环境走原路径、行为不变。参考实现
    # archives/b/barvinok/0.41.9/conanfile.py。
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

# 必须等价于 `python -m pytest`：`-m` 会把 CWD 并入 `sys.path[0]`。内嵌解释器
# 经 `PyRun_SimpleFileEx` 跑脚本不会做这件事。
sys.path.insert(0, os.getcwd())

# 刻意**不** raise SystemExit：内嵌解释器里 SystemExit 会走到 C 的 exit()，
# 把 launcher 进程连同其进程组一起带走，配方侧就收不到任何 pytest 输出
# （pyenchant 上实测到：只看到 `Exiting with code: 5` 加 SIGTERM）。
pytest.main(sys.argv[1:])
sys.stdout.flush()
sys.stderr.flush()
"""

    def _find_extension_so(self, src_dir):
        """源码树里 pytest 将导入的那个扩展（rootdir 插入使其遮蔽 staging）。"""
        base = os.path.join(src_dir, "zstandard")
        if not os.path.isdir(base):
            return None
        for f in sorted(os.listdir(base)):
            if f.startswith("backend_c") and f.endswith(".so"):
                return os.path.join(base, f)
        return None

    def _dlopen_probe(self, python_exe, env, lib_file):
        """探针：目标解释器能否直接 dlopen 该扩展。返回 (accepted, policy_refused)。

        **必须区分两种失败**：策略拒绝（消息含 ``Permission denied``，E502）才
        路由；其它失败（如 NEEDED 解析不到）不路由，让它如实暴露。
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
        """编一个把 `backend_c` 扩展作为 DT_NEEDED 链接进去的内嵌 Python 启动器。"""
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

        # 必须确认扩展真的进了 DT_NEEDED：否则 exec 期不会映射它，路由白做。
        chk = subprocess.run([objdump, "-d", exe], capture_output=True,
                             text=True, timeout=60)
        if "backend_c" not in (chk.stdout or ""):
            raise ConanException(
                "OHOS launcher: backend_c did not land in the launcher's "
                "DT_NEEDED, so the runtime mapping would not happen:\n"
                + (chk.stdout or "")[-300:])
        return exe

    @staticmethod
    def _shell_quote(word):
        return "'" + word.replace("'", "'\\''") + "'"

    def build(self):
        apply_conandata_patches(self)
        python_exe = sys.executable
        src_dir = self.source_folder
        staging = self._staging_dir()
        wheels = os.path.join(self.build_folder, "wheels")
        os.makedirs(staging, exist_ok=True)
        os.makedirs(wheels, exist_ok=True)

        self.run(f'{python_exe} -m pip install --break-system-packages '
                 f'--timeout 120 --retries 3 setuptools wheel pytest hypothesis')

        zstd_inc, zstd_lib = self._zstd_dirs()
        env = dict(os.environ)
        # 供 distutils 找到 conan 的 zstd 头/库（system_zstd 分支不再自带头目录）
        env["CFLAGS"] = f'-I{zstd_inc} ' + env.get("CFLAGS", "")
        env["LDFLAGS"] = f'-L{zstd_lib} -lzstd ' + env.get("LDFLAGS", "")
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            [zstd_lib] + [p for p in env.get("LD_LIBRARY_PATH", "").split(os.pathsep) if p])

        # 把 toolchain 钉成**绝对路径**（根因见 _abs_compiler_paths 的 docstring）：
        # 上游 make_cffi.py 走 distutils compiler 的 `Popen([clang, '-E', ...])`，
        # 裸名 clang 在 OHOS 上无法 exec（CI 实测 build() 失败）。
        cc, cxx = self._abs_compiler_paths()
        env["CC"] = cc
        env["CXX"] = cxx
        env["LDSHARED"] = f"{cc} -shared"
        env["LDCXXSHARED"] = f"{cxx} -shared"
        self.output.info(f"absolute toolchain: CC={cc} CXX={cxx}")

        # 兜底：构建过程还会调用其它工具（ar/ranlib/strip/ld…），同样是裸名。
        # 给被调用的解释器挂一个只含 sitecustomize.py 的 PYTHONPATH，让它关掉
        # posix_spawn 快路径（回退 fork+exec，会正常查 PATH）。
        pyshim = os.path.join(self.build_folder, "_pyshim")
        os.makedirs(pyshim, exist_ok=True)
        with open(os.path.join(pyshim, "sitecustomize.py"), "w") as fh:
            fh.write(
                "# OHOS: posix_spawn() lacks PATH lookup; force the fork+exec path.\n"
                "import subprocess\n"
                "try:\n"
                "    subprocess._USE_POSIX_SPAWN = False\n"
                "except Exception:\n"
                "    pass\n")
        env["PYTHONPATH"] = os.pathsep.join(
            [pyshim] + [p for p in env.get("PYTHONPATH", "").split(os.pathsep) if p])

        # 1) 用 --system-zstd 产出 wheel（扩展链到 conan 的 zstd）
        #    用 subprocess 而非 self.run(env=...)：后者对 env 形态要求苛刻
        #    （须为字符串列表），且实测其环境未能把 CFLAGS 送达编译器
        #    （报 c-ext/python-zstandard.h: 'zdict.h' file not found）；而同一份
        #    env 用 subprocess 传 dict 已手工验证可编译成功。
        r = subprocess.run(
            [python_exe, "setup.py", "bdist_wheel", "--system-zstd", "-d", wheels],
            cwd=src_dir, env=env, capture_output=True, text=True, timeout=1800)
        if r.returncode != 0:
            raise ConanException(
                "bdist_wheel --system-zstd failed:\n"
                + ((r.stdout or "") + (r.stderr or ""))[-2000:])
        whls = [f for f in os.listdir(wheels) if f.endswith(".whl")]
        if not whls:
            raise ConanException(f"bdist_wheel produced no wheel under {wheels}")
        self.output.info(f"built wheel(s): {whls}")

        # 1b) 再把扩展就地放到源码树（复用上面已编译的目标文件，很快）。
        #     原因：跑上游测试时 pytest 会把 rootdir 插入 sys.path，源码树的
        #     `zstandard/` 会遮蔽 staging 里已安装的那份 —— 而源码树若无
        #     backend_c 扩展，即报 ModuleNotFoundError: No module named
        #     'zstandard.backend_c'（实测 28 个收集错误）。
        r = subprocess.run(
            [python_exe, "setup.py", "build_ext", "--inplace", "--system-zstd"],
            cwd=src_dir, env=env, capture_output=True, text=True, timeout=1800)
        if r.returncode != 0:
            raise ConanException(
                "build_ext --inplace --system-zstd failed:\n"
                + ((r.stdout or "") + (r.stderr or ""))[-2000:])

        # 2) 把 wheel 装进目标目录（--target：内容平铺，语义明确）
        for w in whls:
            self.run(f'{python_exe} -m pip install --break-system-packages --no-deps '
                     f'--target="{staging}" "{os.path.join(wheels, w)}"')
        if not os.path.isdir(os.path.join(staging, "zstandard")):
            raise ConanException(
                f"wheel install produced no zstandard package under {staging}")

        # 3) 签名：OHOS loader 只接受已签名 ELF。必须同时覆盖
        #    （a）源码树里的 inplace 副本（pytest 的 rootdir 插入会让测试导入它）
        #    （b）装进包/staging 的那份（消费方要用）
        self._sign_built_extensions(src_dir, staging)

        self._run_upstream_tests(python_exe, src_dir, staging, zstd_lib, env)

    def _run_upstream_tests(self, python_exe, src_dir, staging, zstd_lib,
                            base_env=None):
        """运行上游套件并如实判定（R51），不做静默降级。

        base_env：build() 里已修好的环境（含绝对路径 CC/CXX/LDSHARED 与
        posix_spawn pyshim）。**必须继承**，否则测试阶段的解释器又回到
        「裸名 exec 失败」的 CI 状态（实测：丢弃后 28 个测试文件全数 ERROR）。
        """
        env = dict(base_env or os.environ)
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            [zstd_lib] + [p for p in env.get("LD_LIBRARY_PATH", "").split(os.pathsep) if p])
        # 让测试直接 import staging 里已安装的 zstandard；**保留** base_env 里的
        # pyshim（置后，不覆盖）
        env["PYTHONPATH"] = os.pathsep.join(
            [staging, src_dir]
            + [p for p in env.get("PYTHONPATH", "").split(os.pathsep) if p])
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        # 打开上游默认关闭的慢测试/fuzz 用例。上游用
        #   @unittest.skipUnless("ZSTD_SLOW_TESTS" in os.environ, "ZSTD_SLOW_TESTS not set")
        # 把 fuzzing 组（3 个文件 / 43 个用例）**默认关掉**；不开则它们永远只记 skip。
        # 本仓要求「上游套件真实跑」（R51/规则 4），故显式打开而不是接受默认 skip。
        # 代价：本机实测该组约 236s（不开时全套约 2s），组内 timeout=1800s 有充足余量。
        # 同时配方已补装 hypothesis —— 缺它时那 3 个文件会在**模块导入处**直接
        # `raise unittest.SkipTest`，即使设了本变量也不会执行。
        env["ZSTD_SLOW_TESTS"] = "1"
        pytest_args = ["tests", "-q", "--assert=plain", "-p", "no:cacheprovider"]
        # probe-then-route（E502）：worker 拒绝 dlopen 用户存储目录下的共享库，
        # 而本包在**收集期**就 import zstandard.backend_c。先探针，**仅在确实被
        # 策略拒绝**时才改走 exec-time 路径；dlopen 本就可用时行为不变。
        # OHC_FORCE_LAUNCHER=1 可在开发机上强制走该分支以验证机制本身。
        ext_so = self._find_extension_so(src_dir)
        forced = os.environ.get("OHC_FORCE_LAUNCHER") == "1"
        route = forced
        if not route and ext_so:
            accepted, policy_refused = self._dlopen_probe(python_exe, env, ext_so)
            route = (not accepted) and policy_refused
            if not accepted and not policy_refused:
                # 不是策略拒绝（例如 NEEDED 解析不到）→ 保持原路径，让真实故障
                # 如实暴露，不要用 launcher 把它掩盖过去。
                self.output.warning(
                    "direct dlopen of zstandard.backend_c failed for a reason "
                    "other than a loader policy refusal; staying on the direct "
                    "path so the real error is not masked")
        if route:
            if not ext_so:
                raise ConanException(
                    "OHOS launcher: the zstandard extension was not found, so "
                    "the suite cannot be routed around the worker's dlopen "
                    "refusal (E502)")
            launcher = self._build_py_launcher(
                python_exe, self.build_folder, ext_so)
            runner = os.path.join(self.build_folder, "ohc_run_pytest.py")
            with open(runner, "w", encoding="utf-8") as fh:
                fh.write(self._PYTEST_RUNNER_SRC)
            self.output.info(
                "loader refused dlopen of the user-directory extension; routing "
                "the suite through an exec-time launcher (E502)"
                + ("  [forced by OHC_FORCE_LAUNCHER]" if forced else ""))
            cmd = " ".join([self._shell_quote(launcher), self._shell_quote(runner)]
                           + [self._shell_quote(a) for a in pytest_args])
        else:
            cmd = f'{python_exe} -m pytest tests -q --assert=plain -p no:cacheprovider'
        proc = subprocess.run(cmd, shell=True, cwd=src_dir, env=env,
                              capture_output=True, text=True, timeout=1800)
        out = (proc.stdout or "") + (proc.stderr or "")
        bad = set()
        for line in out.splitlines():
            m = re.match(r"^(?:FAILED|ERROR)\s+(\S+)", line)
            if m:
                bad.add(m.group(1).rsplit("::", 1)[-1])
        unexpected = sorted(bad - ALLOWED_TEST_FAILURES)
        summary = [l for l in out.splitlines() if re.search(r"\d+ (passed|failed)", l)]
        if unexpected:
            raise ConanException(
                f"upstream zstandard suite has failures outside the allow-list: "
                f"{unexpected} (R51: refusing to report a passing build with a "
                f"failing suite). Tail:\n" + "\n".join(out.splitlines()[-30:]))
        if bad:
            self.output.warning(
                f"上游套件有 {len(bad)} 项失败（system-zstd 构建缺 pool API，"
                f"上游有意为之，已在允许清单内）: {sorted(bad)}")
        self.output.info("upstream pytest: " + (summary[-1] if summary else "no summary"))

    def package(self):
        staging = self._staging_dir()
        py_ver = self._py_ver()
        site_dst = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        if not os.path.isdir(os.path.join(staging, "zstandard")):
            raise ConanException(
                f"zstandard package not found under wheel target {staging}")
        # --target 的内容是平铺的（zstandard/ + zstandard-*.dist-info/），整目录拷入
        copy(self, "*", src=staging, dst=site_dst)

    def package_info(self):
        site = os.path.join(self.package_folder, "lib", self._py_ver(), "site-packages")
        self.output.info(f"PYTHONPATH += {site}")
        self.env_info.PYTHONPATH.append(site)
        # 消费者运行期需要 libzstd（扩展的 NEEDED）
        self.env_info.LD_LIBRARY_PATH.append(self._zstd_dirs()[1])
