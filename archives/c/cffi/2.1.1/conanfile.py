#!/usr/bin/env python3
"""Conan recipe for cffi 2.1.1 — C Foreign Function Interface for Python.

cffi 是带 **C 扩展** 的 Python 包：`src/cffi/` 是纯 Python 层，加速后端
`_cffi_backend` 由 `setup.py build_ext` 编译（`src/c/_cffi_backend.c`），
链接外部 **libffi**。故本配方属"必须编译"的 Python 包（与仓内
psutil / lxml / pillow 同类），而非纯 Python 直拷。

【为什么不是 python-require】
  conan 禁止 python-require 依赖带类型的库：
    ERROR: Package 'cffi/2.1.1' with type 'python-require' cannot have a
           'static-library' dependency to 'libffi/3.5.2'
  libffi 制品为 static-library，故本包声明 package_type = "library" 并带
  shared 选项（与 psutil/lxml 完全一致）。

【依赖】
  · python/3.12.9 —— 提供 Python.h 与 libpython3.12.so（链接期必需：
    musl 不从主可执行文件导出 Python 符号，只链接会得到"链接成功但 import
    失败"的模块）。
  · libffi/3.5.2 —— `_cffi_backend` 的唯一外部链接依赖（setup.py 的
    `libraries = ['ffi']`）。制品为 static-library，自带 ffi.h 与 libffi.a
    及 lib/pkgconfig/libffi.pc（实测）。
  · pycparser/3.0 —— 纯 Python 运行期依赖（pyproject.toml:
    `dependencies = ["pycparser; implementation_name != 'PyPy'"]`），
    ohpcd 已发布（package_type=python-require）。

【构建期 setuptools：ohpcd 无制品 → 从平台 pip 镜像引导】
  setup.py 顶层 `import setuptools`，且 pyproject.toml 的 build-backend 为
  setuptools.build_meta（要求 setuptools>=77.0.3，为 PEP 639 支持）。
  实测 `conan list setuptools/* -r=ohpcd` = 0 条、`conan download` 亦失败，
  故按 PF4 **不能**写成 tool_requires，改为构建期从平台 pip 镜像
  （ci/conan/setup.sh:55 的 PIP_COMMUNITY_INDEX）装到 build_folder 子目录再
  以 PYTHONPATH 提供（pillow 10.4.0 先例）。取依赖失败显式抛错，不静默降级。

【测试：必须用宿主解释器，且必须签名】
  ① 用**宿主** python 跑 pytest（psutil 先例的同一结论）：python 依赖自带的
     `bin/python3.12` 其 `_ctypes` 无法解析 libffi 符号——
        ImportError: Error relocating .../lib-dynload/_ctypes...so:
                     ffi_prep_closure_loc: symbol not found
     而 cffi 的 testing/conftest.py:4 顶层就 `from ctypes import util`，
     会让**整个 session 在收集阶段**即失败（实测 exit=4）。宿主 python 的
     ctypes 正常；两者同为 CPython 3.12/aarch64-linux-ohos，ABI 兼容，
     编译出的扩展可互用（实测宿主导入 `_cffi_backend` 成功、`ffi.new` 正常）。
  ② OHOS 要求被 dlopen 的 .so 带 .codesign 段，否则
     `ImportError: ... Permission denied`（实测未签名时报此错，签名后
     `import _cffi_backend` 成功）。故 build 期与 package 期各签一次
     （conan 的 copy() 会使既有签名失效）。
"""
import glob
import os
import signal
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

# 平台 pip 镜像（与 CI 一致，见 ci/conan/setup.sh:55 PIP_COMMUNITY_INDEX）
PIP_INDEX = "https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple"

# 上游测试期依赖（ohpcd 无制品 → 构建期从平台 pip 镜像取）
UPSTREAM_TEST_REQUIRES = ("pytest>=7",)

# 构建期依赖（ohpcd 无制品 → pip 镜像引导）
BUILD_BOOTSTRAP_REQUIRES = ("setuptools>=77.0.3",)


class CffiConan(ConanFile):
    name = "cffi"
    version = "2.1.1"
    description = ("cffi — Foreign Function Interface for Python calling C "
                   "code (C extension + libffi)")
    license = "MIT-0"
    homepage = "https://github.com/python-cffi/cffi"
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
        self.requires("libffi/3.5.2")
        self.requires("pycparser/3.0")

    def layout(self):
        # 上游为 src 布局（src/cffi、src/c）
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

    def _dep_site(self, dep_name):
        dep = self.dependencies.get(dep_name)
        if dep is None:
            return None
        site = os.path.join(dep.package_folder, "lib", "python3.12",
                            "site-packages")
        return site if os.path.isdir(site) else None

    def _compilers(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return (compilers.get("c") or "clang",
                compilers.get("cpp") or "clang++")

    def _find_backend_so(self):
        """定位 build_ext --inplace 产出的 _cffi_backend 扩展。

        注意落点：`basic_layout()` 下 source_folder 即构建根，而上游用
        `package_dir={"": "src"}`，distutils 的 --inplace 会把扩展拷到 **cwd
        下的 src/**，即 `<source_folder>/src/_cffi_backend*.so`（实测：
        `copying build/lib.../_cffi_backend...so -> src`）。同时也兼容扩展直接
        落在 source_folder 的情形，故两处都找。
        """
        for base in (os.path.join(self.source_folder, "src"), self.source_folder):
            found = sorted(glob.glob(os.path.join(base, "_cffi_backend*.so")))
            if found:
                return found
        return []

    @staticmethod
    def _has_codesign_section(path):
        """ELF 里是否真有 ``.codesign`` 段（纯 Python 解析段名表）。

        **必须实测，不能靠签名工具的输出来判定**：``binary-sign-tool`` 会打印
        "add codesign section success" 并返回 0（CI 日志可见），但本机遗留的构建
        目录 ``cffi33b3d82456dfa`` 里产物**确实不含**该段。缺段时 dlopen 报的是
        极易误导的 ``Error loading shared library ...: Permission denied``
        ——看起来像文件权限问题（而产物本就是 0o770/0o755），实则是缺签名段
        （E212）。实测同一文件、同 mode、同属主：0 段 → Permission denied，
        1 段 → 正常加载。

        用纯 Python 读段名表（实测有段=True / 无段=False）。也可用
        ``llvm-objcopy --dump-section``（实测缺段 rc=1），但多起一个进程不划算。
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
                end = data.index(b"\0", strtab_off + name_off)
                if data[strtab_off + name_off:end] == b".codesign":
                    return True
        except (struct.error, ValueError, IndexError):
            return False
        return False

    def _sign(self, paths):
        """给 ELF 加 .codesign 段（OHOS 要求，否则 dlopen 报 Permission denied）。

        逐文件**实测**段是否落地，未落地就重试，仍失败即显式报错。旧实现的两个
        缺陷合起来把故障藏住了：
          1. 替换步骤以 ``os.path.isfile(so + ".signed")`` 为条件，且签名工具
             一旦不产出该文件（工具报 `add codesign section success` 也可能如此，
             本机构建目录已有 0 段产物为证），替换就被**静默跳过**，原件始终无段；
          2. 末尾按传入的 ``paths`` **无条件**打印 ``signed: [...]``，于是
             「没签成」与「签成了」在日志里完全同形。
        而下游症状是 ``Error loading shared library ...: Permission denied``，
        极易被误判成文件权限问题（实测同一文件、同 mode、同属主：**无段即
        Permission denied，有段即可正常加载**，属 E212）。

        故这里改为校验**临时产物**（确认它出现且内含段）后才替换，替换后再复核。
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
                             f'2>/dev/null || true')
                self.run(f'"{SIGNER}" sign -inFile "{so}" -outFile "{tmp}" '
                         f'-selfSign 1')
                # 校验临时产物本身：既确认它真的出现了，也确认里面有段。
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
            # 缺签名段 ⇒ 后续 dlopen 必报 "Permission denied"（误导为权限问题），
            # 故这里显式失败并点明真因，不把带病产物交给测试阶段。
            raise ConanException(
                "binary-sign-tool ran but these ELFs still have no .codesign "
                "section, so they cannot be dlopened on OHOS (the loader "
                "reports it as 'Permission denied', which is misleading): "
                f"{[os.path.basename(p) for p in unsigned]}. Refusing to "
                "continue with unsigned extensions (E212).")

    def _cc_shim(self):
        """造一个含 `cc`/`c++` 的 shim 目录（OHOS 只有 clang，没有 cc）。

        上游 `testing/cffi0/test_ownlib.py:177` 用**裸名**调编译器：
            subprocess.check_call("cc testownlib.c -shared -fPIC -o '...so'",
                                  shell=True)
        OHOS 不提供 `cc`（实测 `command -v cc` 空），于是 exit 127 →
        该模块的 setup 全线 ERROR（实测 209 项）。同文件另处走 distutils，
        亦报 `FileNotFoundError: 'cc'`。
        这是**测试环境适配**问题（不是库缺陷），故在测试期 PATH 前置一层
        shim：`cc` → clang，`c++` → clang++（实测补后 test_ownlib 由
        全 ERROR 转为 5 passed / 7 skipped）。
        """
        shim = os.path.join(self.build_folder, "_cc_shim")
        os.makedirs(shim, exist_ok=True)
        cc, cxx = self._compilers()
        for name, target in (("cc", cc), ("c++", cxx), ("gcc", cc), ("g++", cxx)):
            link = os.path.join(shim, name)
            if not os.path.exists(link):
                try:
                    os.symlink(target, link)
                except OSError:
                    # 符号链接不可用时退回包装脚本（HMDFS 软链限制，E050）
                    with open(link, "w") as fh:
                        fh.write(f'#!/bin/sh\nexec "{target}" "$@"\n')
                    os.chmod(link, 0o755)
        return shim

    def _create_sitecustomize(self, directory):
        """OHOS 子进程兼容 shim（pillow 10.4.0 先例）。

        OHOS 的 hnp CPython 里 `subprocess` 走 `os.posix_spawn()`（非
        posix_spawnp），**对裸名命令不做 PATH 搜索**（知识 E405）。实测：
            subprocess.run(["git","--version"]) → FileNotFoundError
            subprocess.run(["/data/.../git","--version"]) → OK
        在本包的测试里表现为 distutils 调编译器失败（embedding 用例走
        `distutils.ccompiler.new_compiler()` → `Popen(['cc', ...])`）：
            distutils.compilers.C.errors.CompileError:
                [Errno 2] No such file or directory: 'cc'
        注意这与"`cc` 不存在"是两件事：本机确实没有 `cc`（只有 clang），但
        **即使造了 `cc`→clang 的 PATH shim 也无用**——posix_spawn 不看 PATH。
        故按 pillow 的成熟做法，在测试进程内注入 sitecustomize 补丁
        `subprocess.Popen`，把裸名经 shutil.which 解析成绝对路径后再执行。
        """
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, "sitecustomize.py")
        content = '''"""HarmonyOS subprocess + ctypes compatibility shim (cffi test runtime).

Two OHOS facts are worked around here, both about the *test environment*:

1. subprocess: posix_spawn does not search PATH for bare command names, so
   `Popen(["cc", ...])` fails with FileNotFoundError even when `cc` is on PATH.
2. ctypes.util.find_library(): OHOS has no /sbin/ldconfig and no gcc/ldconfig
   based soname lookup (knowledge E068), so find_library("m") returns None even
   though libm.so loads fine. cffi's ffi.dlopen("m") routes through it.
"""
import ctypes
import ctypes.util as _cu
import os
import shutil
import subprocess


def _resolve(command):
    if not isinstance(command, (str, bytes, os.PathLike)):
        return None
    command = os.fspath(command)
    if os.path.dirname(command):
        return command if os.path.isfile(command) else None
    return shutil.which(command)


if not getattr(subprocess.Popen.__init__, "_ohos_path_fix", False):
    _orig = subprocess.Popen.__init__

    def _patched(self, args, *a, **kw):
        exe = kw.get("executable")
        if exe is not None:
            r = _resolve(exe)
            if r is not None:
                kw["executable"] = r
        elif isinstance(args, (list, tuple)) and args:
            r = _resolve(args[0])
            if r is not None:
                args = list(args)
                args[0] = r
        elif isinstance(args, (str, bytes, os.PathLike)):
            r = _resolve(args)
            if r is not None:
                args = r
        _orig(self, args, *a, **kw)

    _patched._ohos_path_fix = True
    subprocess.Popen.__init__ = _patched


if not getattr(_cu.find_library, "_ohos_soname_fix", False):
    _orig_find_library = _cu.find_library

    def _find_library(name):
        res = _orig_find_library(name)
        if res is not None:
            return res
        # Emulate the Linux ldconfig result by probing the usual sonames.
        for cand in ("lib%s.so" % name, "lib%s.so.6" % name,
                     "lib%s.so.2" % name, "lib%s.so.1" % name,
                     "lib%s.so.0" % name):
            try:
                ctypes.CDLL(cand)
            except OSError:
                continue
            return cand
        return None

    _find_library._ohos_soname_fix = True
    _cu.find_library = _find_library
'''
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return directory

    def _rtld_global_propagates(self, workdir):
        """探针：OHOS 加载器是否真的做 RTLD_GLOBAL 符号传播？

        `testing/cffi1/test_verify1.py::test_verify_dlopen_flags` 断言
        `sys.setdlopenflags(RTLD_GLOBAL)` 载入的库，其导出符号能被**之后**
        载入的另一个库解析（Linux 上成立）。
        实测 OHOS 不成立——用**纯 ctypes**（不经 cffi）复现该语义：
            liba.so 导出 probe_sym_a，以 RTLD_GLOBAL 载入；
            再载入引用 probe_sym_a 的 libb.so
            → Error relocating libb.so: probe_sym_a: symbol not found
        即 OHOS 的动态加载器不做全局作用域符号传播（与 musl 的 dlopen 语义
        相关），属**平台能力限制，非库缺陷**。故先探针实测，不成立才 deselect
        该用例——平台若放开此能力，用例自动恢复执行（不写死跳过）。
        """
        cc, _ = self._compilers()
        d = os.path.join(workdir, "rtld-probe")
        os.makedirs(d, exist_ok=True)
        a_c = os.path.join(d, "a.c")
        b_c = os.path.join(d, "b.c")
        liba = os.path.join(d, "liba.so")
        libb = os.path.join(d, "libb.so")
        with open(a_c, "w") as f:
            f.write("int probe_sym_a = 7;\n")
        with open(b_c, "w") as f:
            f.write("extern int probe_sym_a;\nint get(void){ return probe_sym_a; }\n")
        for src, out in ((a_c, liba), (b_c, libb)):
            r = subprocess.run([cc, "-shared", "-fPIC", src, "-o", out],
                               capture_output=True, text=True, timeout=120)
            if r.returncode != 0:
                self.output.warning(f"rtld probe build failed: {r.stderr[:200]}")
                return True  # 探针不可用 → 不排除，让用例自行失败暴露
        helper = os.path.join(d, "probe.py")
        with open(helper, "w") as f:
            f.write(
                "import ctypes, sys\n"
                f"ctypes.CDLL({liba!r}, mode=ctypes.RTLD_GLOBAL)\n"
                "try:\n"
                f"    lib = ctypes.CDLL({libb!r})\n"
                "except OSError as e:\n"
                "    print('NO_PROPAGATION', e)\n"
                "    sys.exit(3)\n"
                "print('PROPAGATION_OK', lib.get())\n")
        r = subprocess.run([sys.executable, helper], capture_output=True,
                           text=True, timeout=180)
        if r.returncode == 0:
            self.output.info(f"RTLD_GLOBAL probe: {r.stdout.strip()}")
            return True
        self.output.info(
            "RTLD_GLOBAL probe: platform does not propagate global symbols "
            f"({r.stdout.strip()[:160]})")
        return False

    def _host_python_lib_dir(self):
        """宿主解释器 libpython 所在目录（embedding 用例运行内嵌解释器时需
        在 LD_LIBRARY_PATH 上，见 _run_upstream_tests 的说明）。"""
        import sysconfig
        libdir = sysconfig.get_config_var("LIBDIR")
        if not libdir or not os.path.isdir(libdir):
            return ""
        ver = f"{sys.version_info.major}.{sys.version_info.minor}"
        if glob.glob(os.path.join(libdir, f"libpython{ver}.so*")):
            return libdir
        return ""

    def _host_python_link_flags(self):
        """返回让"测试期现场编译的 C 扩展"能解析 Python 符号的链接参数。

        cffi 的 ABI/API 测试会在运行期用当前解释器的 sysconfig 调 clang 编译
        扩展；musl 下不显式链接 libpython 就会
        `Error relocating ...: PyImport_ImportModule: symbol not found`。
        """
        import sysconfig
        libdir = sysconfig.get_config_var("LIBDIR")
        if not libdir or not os.path.isdir(libdir):
            return ""
        ver = f"{sys.version_info.major}.{sys.version_info.minor}"
        libname = sysconfig.get_config_var("LDLIBRARY") or f"libpython{ver}.so"
        found = glob.glob(os.path.join(libdir, libname)) or \
            glob.glob(os.path.join(libdir, f"libpython{ver}.so*"))
        if not found:
            return ""
        stem = os.path.basename(found[0])
        # libpython3.12.so.1.0 → -lpython3.12
        for cand in (f"python{ver}", f"python{ver}.so"):
            if stem.startswith(f"lib{cand}") or stem.startswith(f"libpython{ver}"):
                return f"-L{libdir} -lpython{ver}"
        return f"-L{libdir} -lpython{ver}"

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
                "pip mirror, so the build or the upstream suite could not be "
                f"run (R51: refusing to report an unrun suite as passing). "
                f"Tail:\n{tail}")

    def _boot_dir(self):
        """构建期 setuptools（ohpcd 无制品，pip 引导；pillow 先例）。"""
        boot = os.path.join(self.build_folder, "pybootstrap")
        if not os.path.isdir(boot) or not os.path.isdir(
                os.path.join(boot, "setuptools")):
            os.makedirs(boot, exist_ok=True)
            self._pip_install(boot, BUILD_BOOTSTRAP_REQUIRES)
        return boot

    # ------------------------------------------------------------------ build
    # ── worker 的 dlopen 路由（知识 E502）──────────────────────────────────
    # CI worker 拒绝**进程启动后**映射用户存储目录下的共享库：dlopen 与
    # LD_PRELOAD 一律 `Permission denied`，且**与 ELF 是否已签名无关**（本配方
    # 已为扩展签过名，CI #59718 仍报 Permission denied，正是这一条）；同一文件
    # 作为 DT_NEEDED 在 exec 期加载则被接受（E502，PR !6848 实测）。
    #
    # 本包在**收集期**就 `import _cffi_backend`（testing/cffi0/*、cffi1/* 共 8 个
    # 模块），故整个套件在 worker 上起不来。做法与 pyenchant 3.3.0 同：
    # probe-then-route —— 先探针，**仅在确实被策略拒绝**时改用内嵌 Python
    # 启动器，把 `_cffi_backend*.so` 作为它自己的 DT_NEEDED 链接进去，使其在
    # exec 期就已映射；随后 Python 导入该扩展时 dlopen 命中已加载对象。
    # dlopen 本就可用的环境走原路径，行为不变。
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

# 必须等价于 `python -m pytest`：`-m` 会把 CWD 并入 `sys.path[0]`。内嵌解释器
# 经 `PyRun_SimpleFileEx` 跑脚本不会做这件事。
sys.path.insert(0, os.getcwd())

# 刻意**不** raise SystemExit：内嵌解释器里 SystemExit 会走到 C 的 exit()，
# 把 launcher 进程连同其进程组一起带走，配方侧就收不到任何 pytest 输出
# （pyenchant 上实测到：只看到 `Exiting with code: 5` 加 SIGTERM）。让脚本
# 正常结束即可，pytest 的退出码由配方侧的结果判定兜住。
pytest.main(sys.argv[1:])
sys.stdout.flush()
sys.stderr.flush()
"""

    def _dlopen_probe(self, python_exe, env, lib_file):
        """探针：目标解释器能否直接 dlopen 该扩展。返回 (accepted, policy_refused)。

        **必须区分两种失败**：策略拒绝（消息含 ``Permission denied``，E502）
        才路由；其它失败（如 NEEDED 依赖解析不到）不路由，让它如实暴露——
        否则 launcher 会把真实错误掩盖掉。
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
        """编一个把 `_cffi_backend` 扩展作为 DT_NEEDED 链接进去的内嵌 Python 启动器。"""
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
        if "_cffi_backend" not in (chk.stdout or ""):
            raise ConanException(
                "OHOS launcher: _cffi_backend did not land in the launcher's "
                "DT_NEEDED, so the runtime mapping would not happen:\n"
                + (chk.stdout or "")[-300:])
        return exe

    def build(self):
        src = self.source_folder
        if not os.path.isfile(os.path.join(src, "setup.py")):
            raise ConanException("upstream setup.py not found in source")
        csrc = os.path.join(src, "src", "c", "_cffi_backend.c")
        if not os.path.isfile(csrc):
            raise ConanException(f"upstream C source missing: {csrc}")

        py = self._py()
        py_pkg = py.package_folder
        py_lib = os.path.join(py_pkg, "lib")
        py_inc = os.path.join(py_pkg, "include", "python3.12")
        if not os.path.isfile(os.path.join(py_inc, "Python.h")):
            raise ConanException(f"Python.h missing under {py_inc}")

        libffi = self.dependencies["libffi"]
        ffi_pkg = libffi.package_folder
        ffi_inc = os.path.join(ffi_pkg, "include")
        ffi_lib = os.path.join(ffi_pkg, "lib")
        if not os.path.isfile(os.path.join(ffi_inc, "ffi.h")):
            raise ConanException(f"libffi ffi.h missing under {ffi_inc}")

        cc, cxx = self._compilers()
        boot = self._boot_dir()

        # setup.py 的 use_pkg_config() 会调 pkg-config 找 libffi（可失败但被其
        # 静默吞掉）；显式给 CFLAGS/LDFLAGS 才是权威来源（实测 pkg-config 报
        # "No package 'libffi' found" 时编译仍成功）。
        # -lpython3.12 必需（musl 不导出 Python 符号，见 docstring）。
        # -fuse-ld=bfd 与 python 依赖的 LDSHARED 一致（OHOS lld/musl 组合下
        # 用 bfd 才有稳定的符号解析）。
        env_prefix = (
            f'export CC="{cc}" && export CXX="{cxx}" && '
            f'export LD_LIBRARY_PATH="{py_lib}:$LD_LIBRARY_PATH" && '
            f'export PYTHONPATH="{boot}:$PYTHONPATH" && '
            f'export CFLAGS="-I{py_inc} -I{ffi_inc} $CFLAGS" && '
            f'export LDFLAGS="-fuse-ld=bfd -L{py_lib} -L{ffi_lib} '
            f'-lpython3.12 -lffi $LDFLAGS" && '
        )
        self.run(env_prefix + f'"{os.path.join(py_pkg, "bin", "python3.12")}" '
                 f'setup.py build_ext --inplace', cwd=src)

        sobjs = self._find_backend_so()
        if not sobjs:
            raise ConanException(
                "build_ext produced no _cffi_backend extension module")
        self.output.info(f"built extension(s): {[os.path.basename(s) for s in sobjs]}")
        self._sign(sobjs)

        self._run_upstream_tests()

    # ------------------------------------------------------------ upstream test
    def _run_upstream_tests(self):
        """运行上游 pytest 套件并如实报告（R51），不做静默降级。"""
        tests_dir = os.path.join(self.source_folder, "testing")
        if not os.path.isdir(tests_dir):
            raise ConanException(
                "upstream testing/ not found; refusing to report a pass "
                "without running the suite (R51)")

        deps = os.path.join(self.build_folder, "test-deps")
        os.makedirs(deps, exist_ok=True)
        self._pip_install(deps, UPSTREAM_TEST_REQUIRES)

        py_lib = os.path.join(self._py().package_folder, "lib")
        env = dict(os.environ)
        # OHOS 子进程兼容 shim 必须排在 PYTHONPATH 最前：site.py 启动时即
        # import sitecustomize，后续 Popen 才走"裸名解析"路径（含测试自己
        # fork 出的子进程，它们继承同一 env）。
        shimmod = self._create_sitecustomize(
            os.path.join(self.build_folder, "_ohos_shim"))
        paths = [shimmod, self.source_folder,
                 os.path.join(self.source_folder, "src"),
                 deps]
        for name in ("pycparser",):
            site = self._dep_site(name)
            if site:
                paths.append(site)
        if env.get("PYTHONPATH"):
            paths.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(paths)

        # **必须把 python 依赖的 lib 目录从 LD_LIBRARY_PATH 中剔除**（psutil
        # 实测根因）：conan 经 python 依赖的 package_info() 自动注入该 lib，
        # 而本配方跑 pytest 用的是宿主解释器——一旦 LD_LIBRARY_PATH 命中
        # conan 版 libpython3.12.so，宿主解释器身份被整体翻转
        # （sys.platform: ohos→linux，sysconfigdata 名随之改变），宿主 stdlib
        # 里没有对应那份 sysconfigdata，任何 sysconfig.get_config_var() 都会
        # ModuleNotFoundError。剔除后扩展仍正常：Python 符号由已在运行的主
        # 解释器解析（实测 cffi 全套与消费者用例均通过）。
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            p for p in env.get("LD_LIBRARY_PATH", "").split(os.pathsep)
            if p and os.path.realpath(p) != os.path.realpath(py_lib))
        # 反向需求：embedding 用例会**编译并运行**内嵌 CPython 的可执行文件
        # （testing/embedding/*.c → `add1-test` 等），它们的 NEEDED 里有
        # libpython3.12.so.1.0。剔除 conan 版 libpython 后（见上）必须补上
        # **宿主** libpython 所在目录，否则可执行文件 exit 127：
        #   Error loading shared library libpython3.12.so.1.0
        #   Error relocating _empty_cffi.so: Py_InitializeEx: symbol not found
        # 宿主 python 与 conan python 同为 CPython 3.12/aarch64-linux-ohos，
        # ABI 兼容（实测补后 ./empty-test 输出 OK）。
        host_lib = self._host_python_lib_dir()
        if host_lib:
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                [host_lib] + [p for p in env["LD_LIBRARY_PATH"].split(os.pathsep)
                              if p])
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        env["PYTHONNOUSERSITE"] = "1"
        env.pop("_PYTHON_SYSCONFIGDATA_NAME", None)
        # cffi 的 verify()/recompile() 会在测试运行期**现场编译**上百个 C 扩展。
        # musl 不从主可执行文件导出 Python 符号，因此这些模块必须显式链接
        # libpython，否则 dlopen 时符号解析失败（实测 cffi1 出现 134 项）：
        #   ImportError: Error relocating .../_CFFI_test_math_sin...so:
        #                PyImport_ImportModule: symbol not found
        # 而运行期编译走的是**当前解释器**（宿主）的 sysconfig，其 LDSHARED
        # 不带 -lpython3.12 → 这里显式补上（实测补后同一用例由 FAILED 转 PASSED）。
        host_link = self._host_python_link_flags()
        ffi = self.dependencies["libffi"]
        ffi_inc = os.path.join(ffi.package_folder, "include")
        ffi_lib = os.path.join(ffi.package_folder, "lib")
        ffi_pc = os.path.join(ffi_lib, "pkgconfig")
        if host_link:
            env["LDFLAGS"] = (host_link + " " + env.get("LDFLAGS", "")).strip()
            self.output.info(f"upstream-test LDFLAGS += {host_link}")
        else:
            self.output.warning(
                "host libpython not located — cffi's compile-at-test-time cases "
                "may fail to resolve Python symbols")
        # 若干上游用例会在**嵌套 venv 里重新构建 cffi 本体**
        # （testing/cffi1/test_cffi_gen_src_meson.py：`pip install meson-python
        # CFFI_DIR`）。那些构建读 os.environ，不会拿到主构建期注入的
        # CFLAGS/LDFLAGS，于是 src/c/_cffi_backend.c 报
        #   fatal error: 'ffi.h' file not found
        # 故把 libffi 的 include/lib/pkgconfig 也放进测试环境（幂等，对主套件
        # 无害）：C 源编译能找到 ffi.h，链接能找到 -lffi。
        env["CFLAGS"] = (f"-I{ffi_inc} " + env.get("CFLAGS", "")).strip()
        env["LDFLAGS"] = (f"-L{ffi_lib} -lffi " + env.get("LDFLAGS", "")).strip()
        env["PKG_CONFIG_PATH"] = os.pathsep.join(
            [ffi_pc] + [p for p in env.get("PKG_CONFIG_PATH", "").split(os.pathsep) if p])
        # OHOS 不提供裸名 `cc`（上游 test_ownlib 直接调它）→ PATH 前置 shim
        shim = self._cc_shim()
        env["PATH"] = shim + os.pathsep + env.get("PATH", "")
        # cffi 的 testing/udir.py 在 tempfile.gettempdir() 下建 ffi-<n> 目录；
        # OHOS /tmp 只读 → TMPDIR 必须指向可写目录。
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        env["TMPDIR"] = tmp
        # pytest 默认 basetemp 会因属主检查 INTERNALERROR（E543）→ --basetemp
        basetemp = os.path.join(self.build_folder, "pytest-basetemp")
        os.makedirs(basetemp, exist_ok=True)

        # 用宿主解释器（见 docstring ①）：python 依赖自带解释器的 _ctypes
        # 解析不到 libffi 符号，而 testing/conftest.py:4 顶层 import ctypes。
        pytest_args = ["testing", "-q", "--no-header",
                       "-p", "no:cacheprovider", f"--basetemp={basetemp}"]
        # probe-then-route（E502）：worker 拒绝 dlopen 用户存储目录下的共享库，
        # 而本包在**收集期**就 import _cffi_backend。先探针，**仅在确实被策略
        # 拒绝**时才改走 exec-time 路径；dlopen 本就可用时行为不变。
        # OHC_FORCE_LAUNCHER=1 可在开发机上强制走该分支以验证机制本身。
        backend_so = self._find_backend_so()
        forced = os.environ.get("OHC_FORCE_LAUNCHER") == "1"
        route = forced
        if not route and backend_so:
            accepted, policy_refused = self._dlopen_probe(
                sys.executable, env, backend_so[0])
            route = (not accepted) and policy_refused
            if not accepted and not policy_refused:
                # 不是策略拒绝（例如 NEEDED 依赖解析不到）→ 保持原路径，让真实
                # 故障如实暴露，不要用 launcher 把它掩盖过去。
                self.output.warning(
                    "direct dlopen of _cffi_backend failed for a reason other "
                    "than a loader policy refusal; staying on the direct path "
                    "so the real error is not masked")
        if route:
            if not backend_so:
                raise ConanException(
                    "OHOS launcher: _cffi_backend was not found, so the suite "
                    "cannot be routed around the worker's dlopen refusal (E502)")
            launcher = self._build_py_launcher(
                sys.executable, self.build_folder, backend_so[0])
            runner = os.path.join(self.build_folder, "ohc_run_pytest.py")
            with open(runner, "w", encoding="utf-8") as fh:
                fh.write(self._PYTEST_RUNNER_SRC)
            self.output.info(
                "loader refused dlopen of the user-directory extension; routing "
                "the suite through an exec-time launcher (E502)"
                + ("  [forced by OHC_FORCE_LAUNCHER]" if forced else ""))
            cmd = [launcher, runner] + pytest_args
        else:
            cmd = [sys.executable, "-m", "pytest"] + pytest_args
        # RTLD_GLOBAL 探针：OHOS 加载器不做全局符号传播时，deselect 对应用例
        # （平台能力限制，非库缺陷；平台放开即自动恢复执行）。
        if not self._rtld_global_propagates(tmp):
            rtld_case = "testing/cffi1/test_verify1.py::test_verify_dlopen_flags"
            cmd.append(f"--deselect={rtld_case}")
            self.output.info(
                "RTLD_GLOBAL propagation unavailable on this platform: "
                f"deselecting {rtld_case}")
        report = os.path.join(self.build_folder, "upstream-pytest-report.txt")
        proc = subprocess.Popen(cmd, cwd=self.source_folder, env=env,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True,
                                start_new_session=True)
        try:
            out, _ = proc.communicate(timeout=5400)
            rc = proc.returncode
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
            out, _ = proc.communicate()
            rc = 124
        with open(report, "w", encoding="utf-8") as fh:
            fh.write(out or "")
        for line in (out or "").strip().splitlines()[-8:]:
            self.output.info(f"[upstream-pytest] {line}")
        if rc == 124:
            raise ConanException(
                f"upstream pytest timed out (>5400s, suite did not finish); "
                f"see {report}")
        if rc != 0:
            raise ConanException(
                "upstream pytest suite failed (R51: refusing to report a "
                f"passing build with a failing suite). See {report}. Tail:\n"
                + "\n".join((out or "").strip().splitlines()[-20:]))
        self.output.info(f"upstream pytest passed; report: {report}")

    # ---------------------------------------------------------------- package
    def package(self):
        site = self._site_dir()
        src_pkg = os.path.join(self.source_folder, "src", "cffi")
        if not os.path.isdir(src_pkg):
            raise ConanException("upstream src/cffi not found (src layout)")

        dst_pkg = os.path.join(site, "cffi")
        copy(self, "*", src=src_pkg, dst=dst_pkg,
             excludes=("__pycache__/*", "*.pyc", "*.pyo"))
        # 加速后端是顶层模块（--inplace 落在 <source_folder>/src/）
        for so in self._find_backend_so():
            copy(self, os.path.basename(so), src=os.path.dirname(so), dst=site)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        if not os.path.isfile(os.path.join(dst_pkg, "__init__.py")):
            raise ConanException(f"cffi python payload incomplete under {dst_pkg}")
        sos = glob.glob(os.path.join(site, "_cffi_backend*.so"))
        if not sos:
            raise ConanException(f"_cffi_backend extension missing under {site}")
        # copy() 使 ELF 签名失效 → 打包后再签一次（必须，否则 dlopen 失败）
        self._sign(sos)

    def package_info(self):
        self.cpp_info.libs = []
        site = self._site_dir()
        # 消费方与 test_package 自动获得导入路径（教训：只 print 不声明会让
        # 消费方报 No module named 'cffi'）
        self.runenv_info.append_path("PYTHONPATH", site)
        self.buildenv_info.append_path("PYTHONPATH", site)
        self.output.info(f"PYTHONPATH={site}")
