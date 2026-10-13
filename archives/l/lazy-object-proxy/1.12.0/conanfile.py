#!/usr/bin/env python3
"""Conan recipe for lazy-object-proxy 1.12.0 — fast, thorough lazy object proxy.

lazy_object_proxy 是带 **C 扩展** 的 Python 包：``src/lazy_object_proxy/`` 为
纯 Python 层（``simple``/``slots`` 两个实现），加速实现 ``cext`` 由
``setup.py build_ext`` 编译（``src/lazy_object_proxy/cext.c``，对 ``src/**/*.c``
做 glob），**无任何外部 C 库依赖**（只用 CPython API）。故本配方属
"必须编译"的 Python 包（与仓内 psutil / lxml / cffi 同类），而非纯 Python
直拷。

【为什么不是 python-require】
  conan 禁止 python-require 依赖带类型的库：
    ERROR: Package '...' with type 'python-require' cannot have a
           'static-library' dependency to 'libffi/...'
  python/3.12.9 传递带入 libffi（static-library），故本包声明
  package_type = "library" 并带 shared 选项（与 psutil/cffi 完全一致）。

【依赖】
  · python/3.12.9 —— 提供 Python.h 与 libpython3.12.so（链接期必需：
    musl 不从主可执行文件导出 Python 符号，只链接会得到"链接成功但 import
    失败"的模块——cffi 2.1.1 已实测该结论）。
  · 无运行期外部依赖（pyproject.toml: dependencies = []）。

【构建期 setuptools：ohpcd 无制品 → 从平台 pip 镜像引导】
  setup.py 顶层 `import setuptools`，且 pyproject.toml 的 build-backend 为
  setuptools.build_meta（requires: setuptools>=80、setuptools_scm>=8）。
  ohpcd 未发布 setuptools 制品，故按 PF4 **不能**写成 tool_requires，改为
  构建期从平台 pip 镜像（ci/conan/setup.sh 的 PIP_COMMUNITY_INDEX）装到
  build_folder 子目录再以 PYTHONPATH 提供（cffi/pillow 先例）。取依赖失败
  显式抛错，不静默降级。
  注意 setuptools_scm：sdist 自带 PKG-INFO 与已生成的
  ``src/lazy_object_proxy/_version.py``，且 pyproject 的
  ``[tool.setuptools_scm] fallback_version = "1.12.0"`` 兜底，脱离 git 环境
  也可正确得出版本号，无需额外处理。

【测试：用宿主解释器跑 + 双次签名】
  ① 用**宿主** python3 跑 pytest（psutil/cffi 先例的同一结论）：conan python
     依赖自带解释器的扩展模块在 OHOS 上存在符号解析问题；宿主 python
     （CPython 3.12，aarch64-linux-ohos）与 conan python ABI 兼容，编译出的
     扩展可互用。
  ② OHOS 要求被 dlopen 的 .so 带 .codesign 段，否则
     ``ImportError: ... Permission denied``。故 build 期与 package 期各签
     一次（conan 的 copy() 会使既有签名失效）。
  ③ 上游 pytest.ini 带 ``--doctest-modules``（对 src/ 里的模块跑 doctest）
     与 ``filterwarnings = error``；套件按 conftest 参数化
     slots/cext/simple × subclassed/normal，cext 参数直接验证本适配的
     C 扩展路径。

【上游测试实跑（R51）】
  ``tests/`` 两个模块 + src doctest，实跑统计进 PR 正文测试表。
"""
import glob
import os
import re
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

# OHOS 代码签名工具（HNP 自带）
SIGNER = "/data/service/hnp/bin/binary-sign-tool"
OBJCOPY = "/data/service/hnp/bin/llvm-objcopy"

# 平台 pip 镜像（与 CI 一致，见 ci/conan/setup.sh PIP_COMMUNITY_INDEX）
PIP_INDEX = "https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple"

# 上游测试期依赖（ohpcd 无制品 → 构建期从平台 pip 镜像取）
UPSTREAM_TEST_REQUIRES = ("pytest>=7", "pytest-benchmark")

# 构建期依赖（ohpcd 无制品 → pip 镜像引导；pyproject build-system 要求
# setuptools>=80、setuptools_scm>=8）
BUILD_BOOTSTRAP_REQUIRES = ("setuptools>=80", "setuptools_scm>=8")


class LazyObjectProxyConan(ConanFile):
    name = "lazy-object-proxy"
    version = "1.12.0"
    description = ("lazy-object-proxy — a fast and thorough lazy object "
                   "proxy (Python, C extension backend)")
    license = "BSD-2-Clause"
    homepage = "https://github.com/ionelmc/python-lazy-object-proxy"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    # L0p：OHOS profile 需要 os/compiler/build_type/arch 四项
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("python/3.12.9")

    def layout(self):
        # 上游为 src 布局（src/lazy_object_proxy）
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    # ---------------------------------------------------------------- helpers
    def _py(self):
        return self.dependencies["python"]

    def _site_dir(self):
        return os.path.join(self.package_folder, "lib", "python3.12",
                            "site-packages")

    def _compilers(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return (compilers.get("c") or "clang",
                compilers.get("cpp") or "clang++")

    def _find_cext_so(self):
        """定位 build_ext --inplace 产出的 cext 扩展。

        落点：`basic_layout()` 下 source_folder 即构建根，上游用
        `package_dir={"": "src"}`，distutils 的 --inplace 会把扩展拷到 **cwd
        下的 src/lazy_object_proxy/**（与 cffi 先例相同）。兼容扩展直接落
        source_folder 的情形，两处都找。
        """
        for base in (os.path.join(self.source_folder, "src",
                                  "lazy_object_proxy"),
                     self.source_folder):
            found = sorted(glob.glob(os.path.join(base, "cext*.so")))
            if found:
                return found
        return []

    @staticmethod
    def _has_codesign_section(path):
        """ELF 里是否真有 ``.codesign`` 段（纯 Python 解析段名表）。

        **必须实测，不能靠签名工具的输出来判定**：``binary-sign-tool`` 会打印
        "add codesign section success" 并返回 0，但产物可能不含该段（cffi
        先例实测）。缺段时 dlopen 报的是极易误导的
        ``Error loading shared library ...: Permission denied``（E212）。
        """
        import struct
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError:
            return False
        if data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 1:
            return False  # 非 64 位小端 ELF
        try:
            e_shoff, = struct.unpack_from("<Q", data, 0x28)
            e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", data, 0x3a)
            if not e_shoff or not e_shnum:
                return False
            strtab_off, = struct.unpack_from(
                "<Q", data, e_shoff + e_shstrndx * e_shentsize + 0x18)
            for i in range(e_shnum):
                off = e_shoff + i * e_shentsize
                name_off, = struct.unpack_from("<I", data, off)
                end = data.index(b"\x00", strtab_off + name_off)
                if data[strtab_off + name_off:end] == b".codesign":
                    return True
        except (struct.error, ValueError, IndexError):
            return False
        return False

    def _sign(self, paths):
        """给 ELF 加 .codesign 段（OHOS 要求，否则 dlopen 报 Permission denied）。

        逐文件**实测**段是否落地，未落地就重试，仍失败即显式报错（对齐 cffi
        先例的强化实现：校验临时产物后替换、替换后复核）。
        """
        if not os.path.isfile(SIGNER):
            self.output.warning(
                f"{SIGNER} not found — the extension will fail to dlopen on "
                "OHOS/HMDFS (E212)")
            return
        signed, unsigned = [], []
        for so in paths:
            if not os.path.isfile(so):
                continue
            name = os.path.basename(so)
            ok = False
            for attempt in range(1, 4):
                tmp = so + ".signed"
                try:
                    os.remove(tmp)
                except OSError:
                    pass
                if os.path.isfile(OBJCOPY):
                    self.run(f'"{OBJCOPY}" --remove-section .codesign "{so}" '
                             f'|| true')
                self.run(f'"{SIGNER}" sign -inFile "{so}" -outFile "{tmp}" '
                         f'-selfSign 1')
                if not os.path.isfile(tmp):
                    self.output.warning(
                        f"signer produced no {os.path.basename(tmp)} "
                        f"(attempt {attempt}/3) for {name}")
                    continue
                if not self._has_codesign_section(tmp):
                    self.output.warning(
                        f"signed artifact has no .codesign section "
                        f"(attempt {attempt}/3) for {name}")
                    continue
                os.replace(tmp, so)
                os.chmod(so, 0o755)
                if self._has_codesign_section(so):
                    ok = True
                    break
                self.output.warning(
                    f"{name} lost its .codesign section during replace "
                    f"(attempt {attempt}/3)")
            (signed if ok else unsigned).append(so)
        if signed:
            self.output.info(
                f"signed: {[os.path.basename(p) for p in signed]}")
        if unsigned:
            raise ConanException(
                "binary-sign-tool ran but these ELFs still have no .codesign "
                "section, so they cannot be dlopened on OHOS (the loader "
                "reports it as 'Permission denied', which is misleading): "
                f"{[os.path.basename(p) for p in unsigned]}. Refusing to "
                "continue with unsigned extensions (E212).")

    def _pip_install(self, target, requirements):
        """从平台 pip 镜像装依赖到 target（失败即抛错）。"""
        cmd = [sys.executable, "-m", "pip", "install", "--target", target,
               "--break-system-packages", "--disable-pip-version-check",
               "--timeout", "120", "--retries", "3",
               "--index-url", PIP_INDEX, *requirements]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        if res.returncode != 0:
            tail = "\n".join(((res.stdout or "") + (res.stderr or ""))
                             .strip().splitlines()[-12:])
            raise ConanException(
                "could not obtain build/test dependencies from the platform "
                f"pip mirror ({requirements}). Tail:\n" + tail)
        return target

    def _bootstrap_build_tools(self):
        """构建期引导 setuptools/setuptools_scm 到 build_folder（pillow/cffi 先例）。"""
        boot = os.path.join(self.build_folder, "build-boot")
        os.makedirs(boot, exist_ok=True)
        self._pip_install(boot, BUILD_BOOTSTRAP_REQUIRES)
        return boot

    # ---------------------------------------------------------------- build
    def build(self):
        src = self.source_folder
        if not os.path.isfile(os.path.join(src, "setup.py")):
            raise ConanException("upstream setup.py not found in source")
        csrc = os.path.join(src, "src", "lazy_object_proxy", "cext.c")
        if not os.path.isfile(csrc):
            raise ConanException(f"upstream C source missing: {csrc}")

        py = self._py()
        py_pkg = py.package_folder
        py_lib = os.path.join(py_pkg, "lib")
        py_inc = os.path.join(py_pkg, "include", "python3.12")
        if not os.path.isfile(os.path.join(py_inc, "Python.h")):
            raise ConanException(f"Python.h missing under {py_inc}")

        cc, cxx = self._compilers()
        boot = self._bootstrap_build_tools()

        # 用 conan python 依赖自带的解释器跑 setup.py（其 sysconfig 与
        # 注入的 CFLAGS/LDFLAGS 一致）；-lpython3.12 必需（musl 不导出
        # Python 符号，见 docstring）；-fuse-ld=bfd 与 python 依赖的
        # LDSHARED 一致（OHOS lld/musl 组合下用 bfd 才有稳定的符号解析）。
        env_prefix = (
            f'export CC="{cc}" && export CXX="{cxx}" && '
            f'export LD_LIBRARY_PATH="{py_lib}:$LD_LIBRARY_PATH" && '
            f'export PYTHONPATH="{boot}:$PYTHONPATH" && '
            f'export CFLAGS="-I{py_inc} $CFLAGS" && '
            f'export LDFLAGS="-fuse-ld=bfd -L{py_lib} -lpython3.12 -Wl,-rpath,{py_lib} $LDFLAGS" && '
        )
        self.run(env_prefix + f'"{os.path.join(py_pkg, "bin", "python3.12")}" '
                 f'setup.py build_ext --inplace', cwd=src)

        sobjs = self._find_cext_so()
        if not sobjs:
            raise ConanException(
                "build_ext produced no cext extension module")
        self.output.info(f"built extension(s): {[os.path.basename(s) for s in sobjs]}")
        self._sign(sobjs)

        self._run_upstream_tests()

    # ------------------------------------------------------------ upstream test
    def _run_upstream_tests(self):
        """运行上游 pytest 套件并如实报告（R51），不做静默降级。"""
        tests_dir = os.path.join(self.source_folder, "tests")
        if not os.path.isdir(tests_dir):
            raise ConanException(
                "upstream tests/ not found; refusing to report a pass without "
                "running the suite (R51)")

        deps = os.path.join(self.build_folder, "test-deps")
        os.makedirs(deps, exist_ok=True)
        self._pip_install(deps, UPSTREAM_TEST_REQUIRES)

        # 用 conan python 自带解释器跑 pytest（与 build() 里跑 setup.py
        # 同款环境，CI 已实证可用）。两轮 CI 实测证明宿主解释器路径不可行：
        # ①注入 LD_LIBRARY_PATH → 宿主解释器加载 conan libpython 即崩
        # （exit=127，异构 libpython 缺宿主符号）；②靠 cext DT_RUNPATH
        # 磁盘加载 → CI 宿主环境 dlopen 551 ImportError。conan 解释器 +
        # LD_LIBRARY_PATH=conan pylib 下 cext 加载正常（本地实测
        # Proxy(lambda:41)+1==42）。PYTHONPATH = 测试依赖 + src 布局
        # 纯 Python 层 + 刚构建出的扩展（--inplace 落在 src/lazy_object_proxy/ 下）。
        py_pkg = self._py().package_folder
        py_bin = os.path.join(py_pkg, "bin", "python3.12")
        py_lib = os.path.join(py_pkg, "lib")
        if not os.path.isfile(py_bin):
            raise ConanException(f"conan python interpreter missing: {py_bin}")
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(
            [deps, os.path.join(self.source_folder, "src")]
            + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            [py_lib] + ([env["LD_LIBRARY_PATH"]]
                        if env.get("LD_LIBRARY_PATH") else []))
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        env["PYTHONNOUSERSITE"] = "1"

        report = os.path.join(self.build_folder, "pytest-report.log")
        cmd = [py_bin, "-m", "pytest",
               "-p", "no:cacheprovider",
               "-p", "benchmark",
               "--basetemp", os.path.join(self.build_folder, "pytest-basetemp"),
               "-q", "--no-header"]
        proc = subprocess.run(cmd, cwd=self.source_folder, env=env,
                              capture_output=True, text=True, timeout=3600)
        out = (proc.stdout or "") + (proc.stderr or "")
        with open(report, "w", encoding="utf-8") as fh:
            fh.write(out)
        self.output.info(f"pytest exit={proc.returncode}; report: {report}")
        tail = "\n".join(out.strip().splitlines()[-25:])
        if tail:
            for line in tail.splitlines():
                self.output.info(f"pytest | {line}")

        if proc.returncode != 0:
            failed = self._parse_test_failures(out)
            raise ConanException(
                f"upstream pytest failed (exit={proc.returncode}, "
                f"{len(failed)} failing nodes: {sorted(failed)[:20]}); "
                f"report: {report}")

        self.output.info("upstream pytest passed")

    @staticmethod
    def _parse_test_failures(test_out):
        names = set()
        for line in (test_out or "").splitlines():
            m = re.match(r"^(?:FAILED|ERROR)\s+(\S+)", line.strip())
            if not m:
                continue
            node = m.group(1).rstrip(":")
            name = node.rsplit("::", 1)[-1]
            names.add(name.split("[", 1)[0])
        return names

    # ------------------------------------------------------------ package
    def package(self):
        site = self._site_dir()
        src_pkg = os.path.join(self.source_folder, "src", "lazy_object_proxy")
        if not os.path.isdir(src_pkg):
            raise ConanException("upstream src/lazy_object_proxy not found (src layout)")

        dst_pkg = os.path.join(site, "lazy_object_proxy")
        copy(self, "*", src=src_pkg, dst=dst_pkg,
             excludes=("__pycache__/*", "*.pyc", "*.pyo", "*.egg-info/*",
                       "*.egg-info"))
        # 加速实现是 lazy_object_proxy 包内模块（--inplace 落在 src 布局包目录）
        for so in self._find_cext_so():
            copy(self, os.path.basename(so), src=os.path.dirname(so), dst=dst_pkg)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        if not os.path.isfile(os.path.join(dst_pkg, "__init__.py")):
            raise ConanException(f"python payload incomplete under {dst_pkg}")
        sos = glob.glob(os.path.join(dst_pkg, "cext*.so"))
        if not sos:
            raise ConanException(f"cext extension missing under {dst_pkg}")
        # copy() 使 ELF 签名失效 → 打包后再签一次（必须，否则 dlopen 失败）
        self._sign(sos)

    def package_info(self):
        self.cpp_info.libs = []
        site = self._site_dir()
        # 消费方与 test_package 自动获得导入路径（教训：只 print 不声明会让
        # 消费方报 No module named lazy_object_proxy）
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
        self.output.info(f"PYTHONPATH={site}")
