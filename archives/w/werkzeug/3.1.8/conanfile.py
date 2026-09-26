#!/usr/bin/env python3
"""Conan recipe for Werkzeug 3.1.8 — WSGI web application library (pure Python).

上游 3.1.8 采用 **src 布局**（`src/werkzeug/`）与 flit_core 构建后端
（pyproject.toml: requires = ["flit_core<4"], build-backend =
flit_core.buildapi）。纯 Python 无编译产物，故 package() 直接把
`src/werkzeug` 拷入 site-packages。

与同族的 jinja2 3.1.6 相比，本包的测试侧有一个**决定性差异**（本配方因此
不能照抄 jinja2 的「PYTHONPATH 注入」法）：

  werkzeug 的上游套件含 dev_server 类用例（`@pytest.mark.dev_server`），
  它们通过 `tests/conftest.py` 的 DevServerClient **以子进程**启动真实开发
  服务器：

      env={**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONPATH": tmp_dir}

  该 env **整体覆盖** PYTHONPATH（只留测试的 tmp_path），且用
  `sys.executable` 作为解释器。于是子进程既看不到我们注入的
  PYTHONPATH，也必须在**解释器自身的 site-packages** 里找到被测包。
  更关键的是 werkzeug 自身在 `serving.py:813` 调用了

      importlib.metadata.version("werkzeug")

  ——即被测包必须带**发行版元数据**（.dist-info），仅有源码目录在
  PYTHONPATH 上是不够的（实测报 PackageNotFoundError: No package metadata
  was found for werkzeug，服务器起不来 → wait_ready() 死等 → 用例超时）。

  因此本配方按上游 tox（`runner = "uv-venv-lock-runner"`、`package =
  "wheel"`）的同一思路：构建期建一个**独立 venv**，把被测源码
  `pip install` 进去（同时得到包元数据），再安装上游声明的测试依赖，
  最后用该 venv 的 python 运行套件。这样：
    - 子进程继承 sys.executable = venv python → site-packages 命中被测包；
    - `importlib.metadata.version("werkzeug")` 正常返回 3.1.8；
    - 测试依赖与宿主环境彻底隔离（宿主 pytest 5.4.3 与 py3.12 不兼容，
      见 setuptools 84.0.0 / jinja2 3.1.6 先例）。

依赖：pyproject.toml `dependencies = ["markupsafe>=2.1.1"]` → 用 ohpcd 已发布
的 markupsafe/3.0.3。markupsafe 是 C 扩展（_speedups），只能由 Conan 提供，
故以 .pth 挂进 venv（子进程无法靠 PYTHONPATH 得到它）。

测试平台限制（R51 如实申报，非库缺陷）：
  `tests/test_serving.py::test_server[unix socket]` 需要为 AF_UNIX 服务器
  bind 一个路径型 socket。OHOS SELinux 策略禁止该操作（实测
  `PermissionError: [Errno 1] Operation not permitted`，工具链目录与
  HMDFS 目录均被拒，而 AF_UNIX 常量与 inotify 均正常），进程内自行退避为
  死等 → pytest-timeout 超时。该限制在仓内已有大量先例并登记为知识 **E024**
  （libfstrm / libmalcontent / kdbusaddons / carbon-c-relay 等同一处置）。
  本配方**先做探针实测**（`_unix_socket_bindable`）：能 bind 就照常跑该用例，
  不能 bind 才 deselect 并如实记录——不写死跳过，避免掩盖平台能力变化。
"""
import os
import re
import shutil
import socket as _socket
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get)
from conan.tools.layout import basic_layout

# 上游 pyproject.toml [dependency-groups] tests 中本套件真正需要的部分。
# （其余 dev/docs/typing 组与本套件无关；cffi/cryptography 为 https 用例所需。）
UPSTREAM_TEST_REQUIRES = (
    "pytest>=7",
    "pytest-timeout",
    "ephemeral-port-reserve",
    "watchdog",
    "cffi",
    "cryptography",
)

# 平台 pip 镜像（与 CI 一致，见 ci/conan/setup.sh:55 PIP_COMMUNITY_INDEX）
PIP_INDEX = "https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple"

# AF_UNIX 路径型 socket 受限时排除的用例（探针判定后才生效；平台限制 E024）
AF_UNIX_TEST = "tests/test_serving.py::test_server[unix socket]"


class WerkzeugConan(ConanFile):
    name = "werkzeug"
    version = "3.1.8"
    description = "The comprehensive WSGI web application library"
    license = "BSD-3-Clause"
    homepage = "https://github.com/pallets/werkzeug"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # L0p：OHOS profile 需要 os/compiler/build_type/arch 四项
    settings = "os", "arch", "compiler", "build_type"
    package_type = "python-require"

    def export_sources(self):
        export_conandata_patches(self)  # 无补丁时空操作

    def requirements(self):
        # pyproject.toml: dependencies = ["markupsafe>=2.1.1"]
        # ohpcd 已发布 markupsafe/3.0.3（满足 >=2.1.1）。
        self.requires("markupsafe/3.0.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    # ---------------------------------------------------------------- helpers

    def _dep_site_packages(self, dep_name):
        """Resolve a python-require dependency's site-packages directory."""
        dep = self.dependencies.get(dep_name)
        if dep is None:
            return None
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(dep.package_folder, "lib", py_ver, "site-packages")
        return site if os.path.isdir(site) else None

    def _run(self, cmd, extra_env=None, **kwargs):
        """Run a command in the recipe's build environment (TMPDIR is writable)."""
        env = dict(os.environ)
        # OHOS /tmp 只读：pip / venv / 构建后端一律需要可写 TMPDIR
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        env["TMPDIR"] = tmp
        env.pop("PYTHONPATH", None)  # 防止宿主 PYTHONPATH 串扰 venv
        # PYTHONHOME 会把解释器的 stdlib 定位整个带偏：对 venv 内的解释器而言，
        # 一旦继承到它，`sys.prefix` 就不再指向 venv，进而取不到 stdlib 而直接
        # 起不来（`init_fs_encoding ... No module named 'encodings'`）。此处一并
        # 清掉，保证 venv 按自己的 pyvenv.cfg 正常定位。
        env.pop("PYTHONHOME", None)
        if extra_env:
            # 只有确实需要时才显式放回 PYTHONPATH（如以 -m 调 virtualenv）。
            env.update(extra_env)
        kwargs.setdefault("env", env)
        kwargs.setdefault("capture_output", True)
        kwargs.setdefault("text", True)
        result = subprocess.run(cmd, **kwargs)
        return result

    def _unix_socket_bindable(self, directory):
        """Probe whether an AF_UNIX path socket can be bound here (knowledge E024)."""
        if not hasattr(_socket, "AF_UNIX"):
            return False
        probe = os.path.join(directory, ".af-unix-probe.sock")
        try:
            if os.path.exists(probe):
                os.unlink(probe)
        except OSError:
            pass
        sock = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
        try:
            sock.bind(probe)
            return True
        except OSError as exc:
            self.output.info(f"AF_UNIX path-socket bind probe failed: {exc}")
            return False
        finally:
            sock.close()
            try:
                os.unlink(probe)
            except OSError:
                pass

    # ------------------------------------------------------------ test runner

    def _build_test_venv(self):
        """Create an isolated venv with the package-under-test + test deps.

        Returns (python_executable, site_packages_dir).

        OHOS 的 Python 往往**没有可用的 ensurepip**（`_bundled` wheel 缺失），
        而 `python -m venv` 默认会调 `ensurepip --upgrade --default-pip` 装 pip，
        于是径直失败：
            Error: Command '[...]/bin/python3', '-m', 'ensurepip', '--upgrade',
                   '--default-pip']' returned non-zero exit status 1
        本机开发解释器自带该 wheel、CI worker 的不带，所以「本地全绿、CI 全红」。
        本仓已有两处同一结论：trove-classifiers（“OHOS Python lacks ensurepip”
        → `venv --without-pip`）与 acme-tiny-pyc（“venv 内部 ensurepip 在 CI
        环境不可用”）。

        因此这里**只用一条构造路径**：`venv --without-pip` 先把隔离解释器建出来
        （完全绕开 ensurepip），pip 再由**外层**解释器的 pip 装进 venv 的
        site-packages。`venv --without-pip` 不产出可用解释器时，才退到
        **virtualenv**（与本包 test 依赖中已声明的那项同源，且是另一套实现）。
        每一步都当场验证：解释器能否启动、自举的 pip 是否真能用。测试的真实性
        不变——仍是同一个隔离 venv 跑同一套上游用例，只是 pip 的来源换了。
        """
        venv_dir = os.path.join(self.build_folder, "test-venv")
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        py = os.path.join(venv_dir, "bin", "python")
        site = os.path.join(venv_dir, "lib", py_ver, "site-packages")

        def build_with(cmd, label, extra_env=None):
            """建 venv 并**当场验证解释器能启动**；返回是否可用。

            关键：`venv` 返回 0、`bin/python` 也在，**不等于**该解释器能跑。
            CI 上出现过「目录齐全却起不来」：
                Fatal Python error: init_fs_encoding: failed to get the Python
                codec of the filesystem encoding
                ModuleNotFoundError: No module named 'encodings'
            所以要在这里实测启动，不能用 rc/file 存在性代替——否则坏的 venv 会
            一路带到后面某次 pip 调用才爆，把「venv 没建好」伪装成「pip 不可用」。
            """
            shutil.rmtree(venv_dir, ignore_errors=True)
            res = self._run(cmd, timeout=900, extra_env=extra_env)
            if res.returncode != 0 or not os.path.isfile(py):
                self.output.info(
                    f"{label}: did not produce a usable interpreter "
                    f"(rc={res.returncode})")
                return False
            boot = self._run(
                [py, "-c", "import encodings, sys; print(sys.prefix)"],
                timeout=300)
            if boot.returncode != 0:
                self.output.info(
                    f"{label}: interpreter cannot start — {self._tail(boot)}")
                return False
            self.output.info(
                f"{label}: interpreter ready ({(boot.stdout or '').strip()})")
            return True

        # 路径 1：`venv --without-pip` —— 完全绕开不可靠的 ensurepip（缺
        # `_bundled` wheel）。pip 反正由外层解释器自举进来，venv 自带与否无关。
        if not build_with([sys.executable, "-m", "venv", "--without-pip",
                           venv_dir], "venv --without-pip"):
            # 路径 2：**virtualenv**。它与 stdlib 的 `venv` 是两套独立实现
            # （env 布局、pyvenv.cfg 写法、stdlib 定位都不同），是本包 test 依赖
            # 里已声明的一项，故是真正不同的兜底而非重复。
            tools = os.path.join(self.build_folder, "venv-tool")
            os.makedirs(tools, exist_ok=True)
            res = self._run(
                [sys.executable, "-m", "pip", "install", "--target", tools,
                 "--disable-pip-version-check", "--timeout", "120",
                 "--retries", "3", "--index-url", PIP_INDEX, "virtualenv"],
                timeout=900)
            if res.returncode != 0:
                raise ConanException(
                    "neither `venv` nor virtualenv could be obtained for the "
                    "test environment, so the upstream suite cannot be run "
                    f"(R51). Tail:\n{self._tail(res)}")
            # --no-seed：不种 pip（我们自行自举），也免去对 wheel 的依赖。
            # PYTHONPATH 平时被 _run 清掉，这里显式放回以便 `-m virtualenv`。
            if not build_with([sys.executable, "-m", "virtualenv", "--no-seed",
                               venv_dir], "virtualenv --no-seed",
                              extra_env={"PYTHONPATH": tools}):
                raise ConanException(
                    "could not create a usable test virtualenv with `venv` or "
                    "virtualenv (R51: refusing to report an unrun suite as "
                    "passing).")

        # pip 由**外层**解释器自举进 venv 的 site-packages：venv 自身此刻没有 pip
        # （--without-pip / --no-seed），无法自举。--target 落到 venv 的
        # site-packages 后，venv 内 `python -m pip` 即可正常使用。
        os.makedirs(site, exist_ok=True)
        res = self._run(
            [sys.executable, "-m", "pip", "install", "--no-deps",
             "--disable-pip-version-check", "--timeout", "120",
             "--retries", "3", "--index-url", PIP_INDEX,
             "--target", site, "pip"], timeout=900)
        if res.returncode != 0:
            raise ConanException(
                "pip could not be bootstrapped into the test venv, so the "
                f"upstream suite cannot be run (R51). Tail:\n{self._tail(res)}")
        check_pip = self._run([py, "-m", "pip", "--version"], timeout=300)
        if check_pip.returncode != 0:
            raise ConanException(
                "bootstrapped pip is not usable inside the test venv "
                f"(R51). Tail:\n{self._tail(check_pip)}")

        # 测试依赖（上游 dependency-groups tests 的子集）
        res = self._run(
            [py, "-m", "pip", "install", "--disable-pip-version-check",
             "--timeout", "120", "--retries", "3",
             "--index-url", PIP_INDEX, *UPSTREAM_TEST_REQUIRES],
            timeout=1800)
        if res.returncode != 0:
            raise ConanException(
                "could not obtain the upstream test dependencies from the "
                "platform pip mirror, so the upstream suite could not be run "
                f"(R51). Tail:\n{self._tail(res)}")

        # 被测包本体：装进 venv 才能同时得到 site-packages 落位与发行版元数据
        # （dev_server 子进程会用 importlib.metadata.version("werkzeug")）。
        res = self._run(
            [py, "-m", "pip", "install", "--no-deps",
             "--disable-pip-version-check", "--timeout", "120", "--retries", "3",
             self.source_folder],
            timeout=1800)
        if res.returncode != 0:
            raise ConanException(
                "could not install the package under test into the test venv: "
                f"{self._tail(res)}")

        # markupsafe 是 C 扩展，只能由 Conan 提供 → 以 .pth 挂进 venv
        ms_site = self._dep_site_packages("markupsafe")
        if ms_site is None:
            raise ConanException("markupsafe site-packages not found")
        pth = os.path.join(site, "zz-conan-markupsafe.pth")
        with open(pth, "w") as f:
            f.write(ms_site + "\n")

        check = self._run(
            [py, "-c",
             "import werkzeug, markupsafe, importlib.metadata as m;"
             "print(werkzeug.__file__); print(m.version('werkzeug'))"],
            timeout=300)
        if check.returncode != 0:
            raise ConanException(
                "test venv cannot import the package under test or its "
                f"dependency: {self._tail(check)}")
        self.output.info("test venv ready: " + " | ".join(
            (check.stdout or "").strip().splitlines()))

        return py, site

    # ── worker 的 dlopen 路由（知识 E502）──────────────────────────────────
    # CI #59932 的失败明细（`_failure_excerpt` 带出来的）显示三个失败用例其实
    # 同一个根因：
    #   test_server[https] / test_ssl_object → dev-server 起不来 → wait_ready 超时
    #   test_ssl_dev_cert → TypeError: Using ad-hoc certificates requires the
    #                       cryptography library.
    # 后者是**直接证据**：`from cryptography import x509` 抛了 ImportError。
    # 而 cryptography **在 venv 里装着**（实测 50.0.1，且此前非 https 用例都能
    # 跑），其编译扩展 `cryptography/hazmat/bindings/_rust.abi3.so`：
    #   · 带 `.codesign` 段（实测）→ 不是「未签名」；
    #   · 位于用户存储目录、且是**运行期 dlopen** 的形态 → 正是 E502 的适用面：
    #     worker 拒绝**进程启动之后**映射用户存储目录下的共享库，**与签名无关**；
    #     同一文件作为 DT_NEEDED 在 **exec 期**加载则被接受。
    #
    # 故 probe-then-route：先探针，**仅在确实被策略拒绝**时，编一个内嵌 Python
    # 启动器（把该扩展作为**它自己**的 DT_NEEDED 链接进去），经它跑套件 ——
    # 扩展在 exec 期即已映射，`from cryptography import x509` 时命中已加载对象。
    # 启动器放在 venv/bin/ 并把自己的路径作为 program_name，故**仍采纳该 venv**
    # （实测：sys.prefix = venv、导入到 venv 的 cryptography 50.0.1）。
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
    /* 把 program_name 指向**自身**（位于 venv/bin/），使 CPython 按 pyvenv.cfg
     * 采纳该 venv —— 否则内嵌解释器会退回系统 prefix，导到系统的 cryptography
     * 而非 venv 里那份（实测差别：50.0.0 vs 50.0.1）。 */
    PyConfig config;
    PyConfig_InitPythonConfig(&config);
    config.isolated = 0;
    config.site_import = 1;
    wchar_t *self = Py_DecodeLocale(argv[0], NULL);
    PyStatus st = PyConfig_SetString(&config, &config.program_name, self);
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

    _PYTEST_RUNNER_SRC = """\
import os
import sys

import pytest

# 必须等价于 `python -m pytest`：`-m` 会把 CWD 并入 `sys.path[0]`。内嵌解释器
# 经 `PyRun_SimpleFileEx` 跑脚本不会做这件事。
sys.path.insert(0, os.getcwd())

# 刻意**不** raise SystemExit：内嵌解释器里 SystemExit 会走到 C 的 exit()，
# 把 launcher 进程连同其进程组一起带走，配方侧就收不到任何 pytest 输出
# （pyenchant 实测：只看到 `Exiting with code: 5` 加 SIGTERM）。
pytest.main(sys.argv[1:])
sys.stdout.flush()
sys.stderr.flush()
"""

    @staticmethod
    def _find_crypto_rust_so(site):
        """venv 里 cryptography 的编译扩展（导入时必须 dlopen 的那一个）。"""
        base = os.path.join(site, "cryptography", "hazmat", "bindings")
        if not os.path.isdir(base):
            return None
        for f in sorted(os.listdir(base)):
            if f.startswith("_rust") and f.endswith(".so"):
                return os.path.join(base, f)
        return None

    def _dlopen_probe(self, python_exe, env, lib_file):
        """探针：目标解释器能否直接 dlopen 该扩展。返回 (accepted, policy_refused)。

        **必须区分两种失败**：策略拒绝（消息含 ``Permission denied``，E502）才
        路由；其它失败（如 NEEDED 解析不到）不路由，让它如实暴露。
        每次尝试输出一行短判决（E502 明确要求：不要把多行 traceback 头截断）。
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
        res = self._run([python_exe, "-c", probe, lib_file], extra_env=env)
        lines = ((res.stdout or "") + (res.stderr or "")).splitlines()
        for line in lines:
            if line.startswith("OHCDLOPEN"):
                self.output.info(line[:140])
        accepted = res.returncode == 0
        policy_refused = (not accepted) and any(
            "Permission denied" in line
            for line in lines if line.startswith("OHCDLOPEN MSG"))
        return accepted, policy_refused

    def _build_py_launcher(self, python_exe, venv_dir, lib_file):
        """编内嵌 Python 启动器（链接该扩展为 DT_NEEDED），落在 venv/bin/ 内。

        落在 venv/bin/ 是**必须的**：启动器把自己的路径作为 program_name，
        CPython 据此向上找 pyvenv.cfg，从而采纳该 venv（实测）。
        """
        objcopy = "/data/service/hnp/bin/llvm-readelf"
        clang = "/data/service/hnp/bin/clang"
        if not os.path.isfile(clang):
            raise ConanException(f"OHOS launcher: clang not found at {clang}")
        detect = self._run(
            [python_exe, "-c",
             "import os, sys, sysconfig\n"
             "root = os.path.dirname(os.path.dirname("
             "os.path.realpath(sys.executable)))\n"
             "print(sysconfig.get_paths()['include'])\n"
             "print(sysconfig.get_config_var('Py_ENABLE_SHARED'))\n"
             "print(os.path.join(root, 'lib', "
             "sysconfig.get_config_var('LDLIBRARY') or ''))\n"],
            dict(os.environ))
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

        src = os.path.join(self.build_folder, "ohc_py_launcher.c")
        exe = os.path.join(venv_dir, "bin", "ohc_pytest_launcher")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write(self._OHOS_PY_LAUNCHER_SRC)
        cmd = [clang, "-Wno-deprecated-declarations", src, "-I", include_dir,
               libpython, lib_file,
               "-Wl,-rpath," + os.path.dirname(libpython), "-o", exe]
        res = self._run(cmd)
        if res.returncode != 0:
            raise ConanException(
                "OHOS launcher compile failed: "
                + ((res.stdout or "") + (res.stderr or ""))[-400:])
        os.chmod(exe, 0o755)

        # 必须确认扩展真进了 DT_NEEDED：否则 exec 期不会映射它，路由白做。
        chk = self._run([objcopy, "-d", exe])
        if "_rust" not in (chk.stdout or ""):
            raise ConanException(
                "OHOS launcher: the cryptography extension did not land in the "
                "launcher's DT_NEEDED, so the runtime mapping would not happen:\n"
                + (chk.stdout or "")[-300:])
        return exe

    def _tail(self, res, lines=15):
        text = (res.stdout or "") + (res.stderr or "")
        return "\n".join(text.strip().splitlines()[-lines:])

    @staticmethod
    def _failure_excerpt(test_out, max_lines=400):
        """摘出足以定位根因的失败明细，供 CI 日志留存。

        只打印尾部是不够的：``-q`` 下尾部永远是计数与收尾的 warning，**不含**
        ``=== FAILURES ===`` / ``=== ERRORS ===`` 段——而每个用例的 traceback、
        嵌套子进程的 stderr 全在那一段里。CI #59717 就这么丢了 3 个失败用例的
        身份（日志尾部只有 ``PytestUnraisableExceptionWarning``），而完整报告
        写在 worker 的构建目录里、随之被清理，事后无从追查。

        取三部分而非单纯看尾部：
          1. ``=== FAILURES ===`` / ``=== ERRORS ===`` 段（**真正的致因在这里**）；
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

    def _run_upstream_tests(self):
        """Run the upstream pytest suite and report it truthfully (R51)."""
        tests_dir = os.path.join(self.source_folder, "tests")
        if not os.path.isdir(tests_dir):
            raise ConanException(
                "upstream tests/ not found; refusing to report a pass without "
                "running the suite (R51)")

        py, site = self._build_test_venv()

        # basetemp 用短路径：AF_UNIX 路径型 socket 有 ~108 字节的 sun_path 上限，
        # 而 conan 的 build_folder 路径本身很长（实测容器内 >108 字符），
        # 直接用 build_folder/basetemp 会让 unix socket 用例先撞 ENAMETOOLONG，
        # 掩盖真正的平台原因（E024: SELinux 拒绝 bind → EPERM）。放在 HOME 下
        # 可让探针与用例都落在短路径上，得到准确的失败根因。
        home = os.path.expanduser("~")
        if not (home and os.path.isdir(home) and os.access(home, os.W_OK)):
            home = self.build_folder
        basetemp = os.path.join(home, f".ohc-pytest-basetemp-werkzeug-{self.version}")
        if os.path.isdir(basetemp):
            shutil.rmtree(basetemp, ignore_errors=True)
        os.makedirs(basetemp, exist_ok=True)

        # `--timeout-method=signal`（**不是 thread**）：上游 `conftest.py:198`
        # 的 `wait_ready()` 是无界 `while True`，dev server 子进程一旦起不来
        # 就是**挂死**而非失败。两种方法的收尾语义完全不同：
        #   - `thread`：pytest-timeout dump 栈后调 `os._exit(1)` —— 直接把
        #     **整个 run** 杀掉，输出只剩 `+++ Timeout +++`，**没有用例名、
        #     没有失败清单、没有任何结果**（CI #54059 正是如此，日志无法归因）；
        #   - `signal`：把挂死变成该用例的一次**普通失败**
        #     （`Failed: Timeout (>120.0s) from pytest-timeout`），run 继续，
        #     其余用例结果完整保留。实测对照：同一挂死用例在 signal 下产出
        #     `FAILED ... - Failed: Timeout (>8.0s) from pytest-timeout.`。
        # 仓内先例：afl-utils 1.35a 同样用 `--timeout-method=signal`。
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"  # 只显式加载 timeout 插件
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        env["TMPDIR"] = tmp

        pytest_flags = ["-q", "--no-header",
                        "-p", "no:cacheprovider", "-p", "timeout",
                        "--timeout=120", "--timeout-method=signal",
                        f"--basetemp={basetemp}"]

        # probe-then-route（E502）：worker 拒绝 dlopen 用户存储目录下的共享库，
        # 而 cryptography 的 `_rust.abi3.so` 正是**运行期 dlopen** 的形态。
        # 先探针，**仅在确实被策略拒绝**时才改走 exec-time 路径；dlopen 本就可用
        # 时行为不变（走原来的 `-m pytest`）。OHC_FORCE_LAUNCHER=1 可在开发机上
        # 强制走该分支以验证机制本身。
        crypto_so = self._find_crypto_rust_so(site)
        forced = os.environ.get("OHC_FORCE_LAUNCHER") == "1"
        route = forced
        if not route and crypto_so:
            accepted, policy_refused = self._dlopen_probe(py, env, crypto_so)
            route = (not accepted) and policy_refused
            if not accepted and not policy_refused:
                # 不是策略拒绝（例如 NEEDED 解析不到）→ 保持原路径，让真实故障
                # 如实暴露，不要用 launcher 把它掩盖过去。
                self.output.warning(
                    "direct dlopen of cryptography's _rust extension failed for "
                    "a reason other than a loader policy refusal; staying on the "
                    "direct path so the real error is not masked")
        if route:
            if not crypto_so:
                raise ConanException(
                    "OHOS launcher: cryptography's _rust extension was not "
                    "found, so the suite cannot be routed around the worker's "
                    "dlopen refusal (E502)")
            venv_dir = os.path.dirname(os.path.dirname(py))
            launcher = self._build_py_launcher(py, venv_dir, crypto_so)
            runner = os.path.join(self.build_folder, "ohc_run_pytest.py")
            with open(runner, "w") as fh:
                fh.write(self._PYTEST_RUNNER_SRC)
            self.output.info(
                "loader refused dlopen of the user-directory cryptography "
                "extension; routing the suite through an exec-time launcher "
                "(E502)" + ("  [forced by OHC_FORCE_LAUNCHER]" if forced else ""))
            entry = [launcher, runner]
        else:
            entry = [py, "-m", "pytest"]

        cmd = entry + ["tests"] + pytest_flags

        # AF_UNIX 探针：能 bind 才照常跑 unix socket 用例（E024 平台限制）
        deselected = []
        bindable = self._unix_socket_bindable(basetemp)
        if bindable:
            self.output.info("AF_UNIX path-socket bind works: running all cases")
        else:
            deselected.append(AF_UNIX_TEST)
            cmd.append(f"--deselect={AF_UNIX_TEST}")
            self.output.info(
                "AF_UNIX path-socket bind refused by the platform (E024): "
                f"deselecting {AF_UNIX_TEST}")

        report = os.path.join(self.build_folder, "upstream-pytest-report.txt")
        rc, out, err = self._run_pytest(py, cmd, env)
        with open(report, "w") as f:
            f.write(out + "\n" + err)

        summary = self._pytest_summary(out)
        self.output.info(f"upstream pytest: {summary}"
                         + (f" (deselected: {', '.join(deselected)})"
                            if deselected else ""))

        if rc != 0:
            timed_out, failed = self._timeout_only_failures(out)
            # 定向重跑（**仅一次**，且**仅当失败全部是超时**）：CI worker 在资源
            # 饥饿时会偶发地起不来 dev-server 子进程（同一 PR 连续三次构建分别
            # 栽在 `mkdir: resource temporarily unavailable`、`curl: No such file
            # or directory`、以及本次的 pytest 超时，均属基础设施侧瞬时状态）。
            # 这种超时**不是**库缺陷，但也不能"跳过"了事：此处对**超时的那些
            # 用例**按 node id 原样重跑一次——所有用例仍真实执行、不跳过、不改
            # 断言；重跑仍超时才失败，并把两次结果一并写入报告。
            if timed_out and len(timed_out) == len(failed):
                self.output.warning(
                    f"上游套件有 {len(timed_out)} 个用例超时（疑 worker 资源受限）: "
                    f"{timed_out}；按 node id 定向重跑一次")
                retry_cmd = [py, "-m", "pytest", *timed_out, "-q", "--no-header",
                             "-p", "no:cacheprovider", "-p", "timeout",
                             "--timeout=120", "--timeout-method=signal",
                             f"--basetemp={basetemp}"]
                rc2, out2, err2 = self._run_pytest(py, retry_cmd, env)
                with open(report, "a") as f:
                    f.write("\n\n===== targeted retry of timed-out tests =====\n"
                            + out2 + "\n" + err2)
                if rc2 == 0:
                    self.output.info(
                        "定向重跑通过（" + self._pytest_summary(out2) + "）；"
                        "首次超时判定为 worker 资源受限，已写入报告 "
                        f"{report}")
                    return
                excerpt2 = "\n".join(
                    self._failure_excerpt(out2 + "\n" + err2))
                self.output.error(
                    "定向重跑仍失败（已写入报告），失败明细:\n" + excerpt2)

            excerpt = "\n".join(self._failure_excerpt(out + "\n" + err))
            raise ConanException(
                "upstream pytest suite failed (R51: refusing to report a "
                "passing build with a failing suite). Full output: "
                f"{report}\nbasetemp (dev-server logs): {basetemp}\n"
                f"Failure detail (FAILURES/ERRORS sections first, then the "
                f"summary lines):\n{excerpt}")

    def _run_pytest(self, py, cmd, env):
        """Run one pytest invocation; returns (returncode, stdout, stderr)."""
        res = subprocess.run(cmd, cwd=self.source_folder, env=env,
                             capture_output=True, timeout=7200)
        out = (res.stdout or b"").decode(errors="ignore")
        err = (res.stderr or b"").decode(errors="ignore")
        return res.returncode, out, err

    @staticmethod
    def _timeout_only_failures(out):
        """Parse ``FAILED`` lines; return (timed_out_node_ids, all_failed_node_ids).

        pytest-timeout under ``--timeout-method=signal`` reports a hang as an
        ordinary failure: ``FAILED <nodeid> - Failed: Timeout (>120.0s) ...``.
        Callers use the two lists to decide whether **every** failure is a
        timeout (→ transient hang) rather than a real assertion failure.
        """
        timed_out, failed = [], []
        for line in (out or "").splitlines():
            m = re.match(r"^FAILED\s+(\S+)", line.strip())
            if not m:
                continue
            node = m.group(1)
            failed.append(node)
            if "Timeout" in line:
                timed_out.append(node)
        return timed_out, failed

    @staticmethod
    def _pytest_summary(out):
        """Extract the trailing pytest tally line (e.g. '967 passed, 1 skipped')."""
        m = re.search(r"^=*\s*((?:\d+ (?:passed|failed|error|errors|skipped|"
                      r"xfailed|xpassed|deselected|warning|warnings|"
                      r"subtests?)(?:, )?)+).*$", out, re.M)
        if m:
            return m.group(1).strip()
        return out.strip().splitlines()[-1] if out.strip() else "n/a"

    # ------------------------------------------------------------- lifecycle

    def build(self):
        if not os.path.isdir(os.path.join(self.source_folder, "src", "werkzeug")):
            raise ConanException("upstream src/werkzeug not found (src layout)")
        self._run_upstream_tests()

    def package(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        pkg_dir = os.path.join(site, "werkzeug")
        # src 布局：源码在 <src>/werkzeug
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*", src=os.path.join(self.source_folder, "src", "werkzeug"),
             dst=pkg_dir,
             excludes=("__pycache__/*", "*.pyc", "*.pyo"))
        if not os.path.isfile(os.path.join(pkg_dir, "__init__.py")):
            raise ConanException(f"werkzeug package missing under {pkg_dir}")

        # 最小 .dist-info：werkzeug/serving.py:813 在构造 WSGI server 时调用
        # `importlib.metadata.version("werkzeug")`——仅把源码放进 site-packages
        # 会报 PackageNotFoundError（实测：dev server 起不来）。纯复制策略下
        # 无 PEP 517 构建产物，故按 cookiecutter 2.7.1 先例手写最小元数据。
        dist_info = os.path.join(site, f"werkzeug-{self.version}.dist-info")
        os.makedirs(dist_info, exist_ok=True)
        with open(os.path.join(dist_info, "METADATA"), "w", encoding="utf-8") as f:
            f.write("Metadata-Version: 2.1\n")
            f.write("Name: werkzeug\n")
            f.write(f"Version: {self.version}\n")
            f.write("Summary: The comprehensive WSGI web application library.\n")
            f.write("License: BSD-3-Clause\n")
        with open(os.path.join(dist_info, "RECORD"), "w", encoding="utf-8") as f:
            f.write("")  # RECORD 允许为空

    def package_info(self):
        py_ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        # 声明 import 路径（aiohttp 教训：仅 print 不够，会让 CI 报
        # "No module named ..."）
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
        self.output.info(f"PYTHONPATH={site}")
