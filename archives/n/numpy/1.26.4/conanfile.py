#!/usr/bin/env python3
"""Conan recipe for numpy 1.26.4 — C-extension array computing library.

numpy is built with meson-python (mesonpy backend, C extension). Uses
Cython + meson-python at build time (pip resolves automatically). Runtime
has no hard deps (self-contained; C extension .so in site-packages).
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class NumpyConan(ConanFile):
    name = "numpy"
    version = "1.26.4"
    description = "Fundamental package for array computing in Python"
    license = "BSD-3-Clause"
    homepage = "https://numpy.org/"
    url = ""

    # C 扩展 Python 库（meson 构建）——settings 含 os/arch/compiler
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # CI 的 files.pythonhosted.org 访问极慢（0.05-0.14 MB/s——比本地
        # 1.47 MB/s 慢 10-30 倍——conan 默认 http timeout 内下载不完——
        # 'Read timed out' 实测 #6386——URL 正确非 URL 问题）——conandata
        # URL 已换清华镜像（pypi.tuna.tsinghua.edu.cn——CI 访问快——同一
        # sdist sha256 不变）+ http timeout 加大 600s（CI 慢速下载兜底）
        self.conf_info.define("core.net.http:timeout", 600)
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        python_exe = sys.executable
        src_dir = self.source_folder
        # staging 移到源码目录外（tabulate 教训：conan 2 build_folder 即
        # 源码目录——setuptools flat-layout / meson 检测冲突）
        staging = os.path.abspath(
            os.path.join(self.build_folder, os.pardir, "staging"))
        os.makedirs(staging, exist_ok=True)

        # 先装好 numpy 构建依赖（Cython<3.1 + meson-python + ninja——numpy
        # 约束 Cython<3.1；系统 3.2.9 超限）
        self.run(
            # 不装 ninja：pip install ninja 需 CMake 源码构建（ninja 1.13.0
            # sdist）——CI 链接测试程序时 lld 崩溃（libxml2.so.16 加载失败
            # ——xmlFreeDoc symbol not found——OHOS SDK lld 动态依赖问题
            # 实测 #6386）——系统 ninja 已有（/data/service/hnp/bin/ninja
            # ——下方 NINJA 环境变量注入 meson-python）
            f'{python_exe} -m pip install --break-system-packages '
            # CI 的 pip 社区索引（pypi.cnb.cool）只镜像到 Cython 3.3.0——
            # 不满足 numpy 1.26.4 的 Cython<3.1 约束——为此固定从公共
            # PyPI 拉取构建依赖（Cython 3.0.x 与 meson-python 0.15.x）
            f'--index-url https://pypi.org/simple '
            f'--timeout 120 --retries 3 setuptools wheel "Cython<3.1" '
            f'"meson-python>=0.15.0,<0.16.0"',
        )
        # numpy 1.26.4 用 mesonpy（meson-python）——pip install 自动拉取
        # Cython/meson-python 并编译 C 扩展（aarch64）。staging 在源码
        # 目录外避免 meson/setuptools 检测冲突。
        # meson 报 'Unknown linker(s): llvm-ar/ar/gar' 实测（PATH 首个 ar
        # 不被 meson 识别）——显式注入 AR=/data/service/hnp/bin/llvm-ar；
        # 'Unknown compiler(s): cython/cython3' 实测（meson 靠 PATH 找
        # cython 命令）——PATH 前置 cython 目录（usr/local/bin）；
        # PermissionError: /usr/local/bin/ninja 实测（当前 uid 对 usr/local
        # /bin 无写权限，meson-python 尝试写 ninja 被拒）——PATH 前置
        # /data/service/hnp/bin（系统 ninja 存在且可读）——meson-python
        # 用系统 ninja，不再尝试写 usr/local/bin；--no-build-isolation
        # 用当前环境（已装 Cython<3.1/meson-python/ninja）
        # PermissionError: /usr/local/bin/ninja 实测（posix_spawn 执行
        # ninja --version 被拒——usr/local/bin/ninja 权限 rwxrwx--- 属主
        # 20001006，当前 uid 20020085 无执行权限）——meson-python 支持
        # NINJA 环境变量（_env_ninja_command 优先 NINJA）——注入系统
        # ninja（/data/service/hnp/bin/ninja → ninja.org 1.13.1 可执行）；
        # --no-build-isolation 用当前环境（已装 Cython<3.1/meson-python）
        # OHOS 的 python subprocess PATH 查找普遍 ENOENT（clang/cython
        # 均实测——posix_spawn 对 PATH 前缀目录的命令找不到——绝对路径
        # 执行成功、shutil.which 成功）——patch vendored-meson 的
        # detect.py：defaults['cython'] 候选改为绝对路径（meson 检测
        # cython -V 用绝对路径——绕过 PATH 查找 ENOENT）
        import shutil as _shutil
        # CI 的 cython 装到 .local/bin（pip 用户安装——profile PATH 只有
        # usr/local/bin——shutil.which 失败实测 #6386）——候选路径查找
        # （usr/local/bin + .local/bin——存在且可执行即用）
        _cy = _shutil.which("cython")
        if not _cy:
            for _cd in ("/storage/Users/currentUser/usr/local/bin/cython",
                        "/storage/Users/currentUser/.local/bin/cython",
                        "/data/service/hnp/python.org/python_3.12/bin/cython"):
                if os.path.exists(_cd) and os.access(_cd, os.X_OK):
                    _cy = _cd
                    break
        # 系统 pip 安装的 cython 可执行脚本 shebang 常指向构建机路径
        # （`#!/python3/bin/python3.12` 在本机不存在——`cython -V` 直接
        # ENOENT）——生成 wrapper `cython -> python3 -m cython`，vendored
        # meson detect.py 的 defaults['cython'] 直接使用它。
        _cy_wrap = os.path.join(self.build_folder, "cython-wrap", "cython")
        os.makedirs(os.path.dirname(_cy_wrap), exist_ok=True)
        with open(_cy_wrap, "w") as f:
            f.write("#!/bin/sh\nexec %s -m cython \"$@\"\n" % python_exe)
        os.chmod(_cy_wrap, 0o755)
        _cy = _cy_wrap
        # _detect 独立定义（_cy 找不到时 sanity check patch 也要用——
        # UnboundLocalError 实测 #6386）
        _detect = os.path.join(
            src_dir, "vendored-meson", "meson", "mesonbuild",
            "compilers", "detect.py")
        if _cy:
            _ds = open(_detect).read()
            _old_d = "defaults['cython'] = ['cython', 'cython3']"
            _new_d = ("defaults['cython'] = ['" + _cy
                      + "', 'cython', 'cython3']  # [ohos] abs path")
            if _old_d in _ds:
                _ds = _ds.replace(_old_d, _new_d, 1)
                open(_detect, "w").write(_ds)
                self.output.info(f"meson cython default -> {_cy}")
            else:
                self.output.warning("detect.py cython anchor not found")
        else:
            self.output.warning("cython not found via shutil.which")
        # meson 的编译器 sanity check（编译+运行 hello——'Executables
        # created by c compiler are not runnable' 实测——OHOS 沙箱不能运行
        # cross 编译的测试程序；MESONPY_CROSS_FILE 实测未生效（meson 命令
        # 无 --cross-file）——patch vendored-meson detect.py：跳过 sanity
        # check（cross 编译不验证可运行性——meson 继续）
        _ds = open(_detect).read()
        _old_sc = "if not skip_sanity_check:"
        _new_sc = "if False:  # [ohos] skip sanity check (not runnable)"
        if _old_sc in _ds:
            _ds = _ds.replace(_old_sc, _new_sc, 1)
            open(_detect, "w").write(_ds)
            self.output.info("meson sanity check skipped")
        else:
            self.output.warning("sanity check anchor not found")
        # meson 的 sizeof 测试（cc.sizeof——编译+运行测试程序——OHOS
        # 沙箱不能运行——'Could not run sizeof test binary' 实测
        # numpy/core/meson.build:113）——patch 为 aarch64 LP64 硬编码
        # （int=4/long=8/long long=8/float=4/double=8/long double=8/
        # off_t=8/Py_intptr_t=8/PY_LONG_LONG=8——绕过运行测试程序）
        _core = os.path.join(src_dir, "numpy", "core", "meson.build")
        _cs_core = open(_core).read()
        _old_sizeof = """foreach symbol_type: types_to_check
  cdata.set(symbol_type[0], cc.sizeof(symbol_type[1]))
endforeach
cdata.set('NPY_SIZEOF_OFF_T', cc.sizeof('off_t', prefix: '#include <sys/types.h>'))
cdata.set('NPY_SIZEOF_PY_INTPTR_T',
  cc.sizeof('Py_intptr_t', dependencies: py_dep, prefix: '#include <Python.h>'))
cdata.set('NPY_SIZEOF_PY_LONG_LONG',
  cc.sizeof('PY_LONG_LONG', dependencies: py_dep, prefix: '#include <Python.h>'))"""
        _new_sizeof = """# [ohos] aarch64 LP64 硬编码（OHOS 沙箱不能运行 sizeof 测试程序——
# 'Could not run sizeof test binary' 实测；本地 C 编译运行实测确认：
# int=4 long=8 long long=8 float=4 double=8 long double=16 off_t=8
# Py_intptr_t=8 PY_LONG_LONG=8）
cdata.set('NPY_SIZEOF_INT', 4)
cdata.set('NPY_SIZEOF_LONG', 8)
cdata.set('NPY_SIZEOF_LONGLONG', 8)
cdata.set('NPY_SIZEOF_SHORT', 2)
cdata.set('NPY_SIZEOF_FLOAT', 4)
cdata.set('NPY_SIZEOF_DOUBLE', 8)
cdata.set('NPY_SIZEOF_LONGDOUBLE', 16)
cdata.set('NPY_SIZEOF_OFF_T', 8)
cdata.set('NPY_SIZEOF_PY_INTPTR_T', 8)
cdata.set('NPY_SIZEOF_PY_LONG_LONG', 8)"""
        if _old_sizeof in _cs_core:
            _cs_core = _cs_core.replace(_old_sizeof, _new_sizeof, 1)
            open(_core, "w").write(_cs_core)
            self.output.info("numpy sizeof tests hardcoded (aarch64)")
        else:
            self.output.warning("sizeof anchor not found")
        # line 144：struct complex 类型 sizeof（cc.sizeof 运行测试程序——
        # 实测确认：struct{float}=8 struct{double}=16 struct{long double}=32）
        _old_cx = ("cdata.set(symbol_type[1], "
                   "cc.sizeof(f'struct {@ftype@ __x; @ftype@ __y;}'))")
        _new_cx = ("cdata.set(symbol_type[1], "
                   "{'float': 8, 'double': 16, 'long double': 32}[ftype])"
                   "  # [ohos] hardcoded aarch64")
        if _old_cx in _cs_core:
            _cs_core = _cs_core.replace(_old_cx, _new_cx, 1)
            open(_core, "w").write(_cs_core)
            self.output.info("numpy complex sizeof hardcoded")
        else:
            self.output.warning("complex sizeof anchor not found")
        # long double 格式检测（运行 C 测试程序测字节表示——OHOS 沙箱
        # 不能运行——longdouble_format UNDEFINED → error 'No long double
        # representation'——aarch64 实测 long double=16（IEEE quad LE）——
        # patch error 分支为强制 'IEEE_QUAD_LE'——cdata.set10(
        # 'HAVE_LDOUBLE_IEEE_QUAD_LE', true)——npy_fpmath.h 的 #error 不触发
        _old_ld = "if longdouble_format == 'UNKNOWN' or longdouble_format == 'UNDEFINED'\n  error('Unknown long double format of size: ' + cc.sizeof('long double').to_string())"
        _new_ld = ("if longdouble_format == 'UNKNOWN' or "
                   "longdouble_format == 'UNDEFINED'\n"
                   "  longdouble_format = 'IEEE_QUAD_LE'  # [ohos] aarch64 "
                   "forced (run test unavailable)")
        if _old_ld in _cs_core:
            _cs_core = _cs_core.replace(_old_ld, _new_ld, 1)
            open(_core, "w").write(_cs_core)
            self.output.info("numpy long double format forced IEEE_QUAD_LE")
        else:
            self.output.warning("long double format anchor not found")
        # cdata.set10('HAVE_LDOUBLE_' + longdouble_format, true)——固定为
        # HAVE_LDOUBLE_IEEE_QUAD_LE（longdouble_format 在检测失败时可能
        # 不是预期值——config.h 宏未生效——npy_fpmath.h 仍 #error 实测）
        _old_cd = "cdata.set10('HAVE_LDOUBLE_' + longdouble_format, true)"
        _new_cd = "cdata.set10('HAVE_LDOUBLE_IEEE_QUAD_LE', true)  # [ohos]"
        if _old_cd in _cs_core:
            _cs_core = _cs_core.replace(_old_cd, _new_cd, 1)
            open(_core, "w").write(_cs_core)
            self.output.info("numpy HAVE_LDOUBLE_IEEE_QUAD_LE forced")
        else:
            self.output.warning("cdata long double anchor not found")
        # mandatory_math_funcs 检测（cc.has_function——链接测试——CI 的
        # lld/libxml2 崩溃（同 ninja 安装失败——'Function sin not found'
        # 实测 #6386））——libm/complex/stdlib 标准函数 OHOS 一定有——
        # patch 3 组检测为 if false（硬编码存在——跳过链接测试）
        _mf = [
            ("if not cc.has_function(func, prefix: '#include <math.h>', "
             "dependencies: m_dep)", "if false  # [ohos] libm funcs assumed"),
            ("if not cc.has_function(func, prefix: '#include <complex.h>', "
             "dependencies: m_dep)", "if false  # [ohos] complex funcs assumed"),
            ("if not cc.has_function(func, prefix: '#include <stdlib.h>')",
             "if false  # [ohos] stdlib funcs assumed"),
        ]
        for _o_mf, _n_mf in _mf:
            if _o_mf in _cs_core:
                _cs_core = _cs_core.replace(_o_mf, _n_mf, 1)
                open(_core, "w").write(_cs_core)
                self.output.info("numpy mandatory funcs check skipped")
            else:
                self.output.warning("math funcs anchor not found")
        # 生成 meson cross file（OHOS——meson 认为 cross 编译不运行测试
        # 程序——'Executables are not runnable' 实测修复）
        _cf = "/data/storage/el2/base/cache/np-cross.ini"
        with open(_cf, "w") as _f:
            _f.write(
                "[host_machine]\n"
                "system = 'ohos'\n"
                "cpu_family = 'aarch64'\n"
                "cpu = 'aarch64'\n"
                "endian = 'little'\n"
                "\n[binaries]\n"
                "c = '/data/service/hnp/bin/clang'\n"
                "cpp = '/data/service/hnp/bin/clang++'\n"
                "ar = '/data/service/hnp/bin/llvm-ar'\n"
                # ld.lld here is the `lld --code-sign` wrapper: linking through it
                # produces the platform-trusted .codesign signature at link time.
                "c_ld = '/data/service/hnp/bin/ld.lld'\n"
                "cpp_ld = '/data/service/hnp/bin/ld.lld'\n"
                "cython = '" + (_cy or "/storage/Users/currentUser/usr/local/bin/cython")
                + "'\n")
        self.output.info("meson cross file generated (OHOS)")
        import subprocess as _sp
        # LDFLAGS 的 -lpython3.12 路径动态获取：CI 的 python（/data/service/
        # hnp/bin/python3）libpython3.12.so 实际路径可能不在 sysconfig LIBDIR
        # （meson 的 python 依赖 -L/usr/local/lib 找不到——CI 'unable to find
        # library -lpython3.12' 实测 #6386）——ctypes.util.find_library 动态
        # 找实际路径（CI 运行时返回 CI 的 libpython 位置——本地返回本地的）
        # CI python 进程实际加载的 libpython（/proc/self/maps——python_exe
        # 子进程的 maps——PyType_IsSubtype 匹配（CI python 加载的 libpython
        # 才有该符号——扩展链接它符号解析成功——LD_LIBRARY_PATH 修复后仍
        # 失败实测 #6386：usr/local/lib 软链的推导 libpython 与 CI python
        # 不匹配）——maps 优先（最准确——本地实测可行）
        _libpy = _sp.check_output(
            [python_exe, "-c",
             "import os; "
             "print([l.split()[-1] for l in open('/proc/self/maps') "
             "if 'libpython3.12' in l][0])"],
            text=True).strip()
        if not _libpy or not os.path.isfile(_libpy):
            _libpy = _sp.check_output(
                [python_exe, "-c",
                 "import ctypes.util; "
                 "print(ctypes.util.find_library('python3.12') or '')"],
                text=True).strip()
        if not _libpy:
            # find_library 在 CI 可能返回空（OHOS 机制——软链跳过链接仍
            # 失败实测 #6386）——从 python 的 prefix/base_prefix 动态推导
            # libpython3.12.so 路径（sysconfig prefix/base + LIBDIR 候选）
            _info = _sp.check_output(
                [python_exe, "-c",
                 "import sysconfig, sys; "
                 "print(sysconfig.get_config_var('prefix'), "
                 "sys.base_prefix, sysconfig.get_config_var('LIBDIR'))"],
                text=True).strip().split()
            for _p in _info:
                for _suf in ("/lib/libpython3.12.so",
                             "/lib/libpython3.12.so.1.0"):
                    _c = _p + _suf
                    if os.path.isfile(_c):
                        _libpy = _c
                        break
                if _libpy:
                    break
        if _libpy:
            _libdir = os.path.dirname(_libpy)
        else:
            _libdir = _sp.check_output(
                [python_exe, "-c",
                 "import sysconfig; "
                 "print(sysconfig.get_config_var('LIBDIR'))"],
                text=True).strip()
        # meson 的 python 依赖链接固定用 -L/storage/Users/currentUser/
        # usr/local/lib（环境 LDFLAGS 不被 meson 链接采用实测 #6386——
        # 链接命令只有 meson 的 -L——CI 'unable to find library
        # -lpython3.12'）——把 CI 的 libpython 实际路径软链到
        # usr/local/lib/libpython3.12.so（meson 的 -L 能找到——链接成功；
        # 本地 find_library 返回的正是该路径——跳过不破坏）
        _lp_target = "/storage/Users/currentUser/usr/local/lib/libpython3.12.so"
        if _libpy and os.path.abspath(_libpy) != _lp_target:
            _lp_dir = os.path.dirname(_lp_target)
            os.makedirs(_lp_dir, exist_ok=True)
            if os.path.exists(_lp_target) or os.path.islink(_lp_target):
                os.remove(_lp_target)
            os.symlink(_libpy, _lp_target)
            self.output.info(
                f"symlinked libpython -> {_libpy} (meson -L found)")
        self.output.info(f"python libpython dir: {_libdir}")
        self.run(
            # LD_LIBRARY_PATH 加 OHOS SDK llvm/lib（lld 依赖 libxml2.so.16
            # ——CI 'Error loading shared library libxml2.so.16: (needed by
            # .../llvm/bin/lld)' + 'Unable to detect linker' 实测 #6386——
            # lld 是 clang 的默认链接器——加载 libxml2 成功才不崩溃）
            f'LD_LIBRARY_PATH=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib:${{LD_LIBRARY_PATH:-}} '
            f'PATH={os.path.dirname(python_exe)}:/storage/Users/currentUser/.local/bin:/data/service/hnp/bin:$PATH '
            f'AR=/data/service/hnp/bin/llvm-ar '
            f'NINJA=/data/service/hnp/bin/ninja '
            f'CC=/data/service/hnp/bin/clang '
            f'CXX=/data/service/hnp/bin/clang++ '
            # numpy C 扩展（_multiarray_umath.so）加载时 PyType_IsSubtype
            # symbol not found 实测（Python C API 符号——OHOS Python 进程
            # 未导出/扩展未链接 libpython）——LDFLAGS 显式链接
            # libpython3.12（sysconfig LIBDIR=/usr/local/lib）
            f'LDFLAGS="-fuse-ld=/data/service/hnp/bin/ld.lld -L{_libdir} -lpython3.12" '
            # meson 报 'Executables created by c compiler are not runnable'
            # 实测（meson 认为 native build——sanity check 运行编译的测试
            # 程序——OHOS 沙箱不能运行）——生成 meson cross file
            # （[host_machine] OHOS——meson 认为 host≠build 的 cross 编译
            # ——不尝试运行测试程序）+ MESONPY_CROSS_FILE 环境变量
            # （meson-python 读它做 --cross-file）
            f'MESONPY_CROSS_FILE=/data/storage/el2/base/cache/np-cross.ini '
            f'{python_exe} -m pip install --break-system-packages --no-deps '
            f'--no-build-isolation --ignore-installed '
            f'--prefix="{staging}" "{src_dir}"',
        )

    def package(self):
        # Copy staged site-packages + bin（含 C 扩展 .so）
        staging = os.path.abspath(
            os.path.join(self.build_folder, os.pardir, "staging"))
        py_ver = self._py_ver()
        site_dst = os.path.join(
            self.package_folder, "lib", py_ver, "site-packages"
        )
        bin_dst = os.path.join(self.package_folder, "bin")

        site_src = None
        for candidate in (
            os.path.join(staging, "lib", py_ver, "site-packages"),
            os.path.join(staging, "lib", py_ver, "dist-packages"),
            os.path.join(staging, "local", "lib", py_ver, "site-packages"),
            os.path.join(staging, "local", "lib", py_ver, "dist-packages"),
        ):
            if os.path.isdir(candidate) and os.path.isdir(
                os.path.join(candidate, "numpy")
            ):
                site_src = candidate
                break
        if site_src is None:
            raise Exception(
                f"numpy site-packages not found under staging={staging}"
            )
        copy(self, "*", src=site_src, dst=site_dst)

        for bin_src in (
            os.path.join(staging, "bin"),
            os.path.join(staging, "local", "bin"),
        ):
            if os.path.isdir(bin_src):
                copy(self, "*", src=bin_src, dst=bin_dst)

        # Plan-1 experiment (2026-09-11): do NOT re-sign after packaging. The
        # toolchain linker (ld.lld --code-sign, forced via cross-file c_ld/
        # cpp_ld and -fuse-ld) already produces the platform-trusted .codesign
        # signature at link time; overwriting it with binary-sign-tool
        # -selfSign may be rejected by the CI sandbox loader. Opt back in with
        # OHOS_POST_SIGN=1.
        if os.environ.get("OHOS_POST_SIGN") == "1":
            self._sign_ohos_shared_libs()

    def _sign_ohos_shared_libs(self):
        """OHOS only executes code-signed ELF; dlopen of an unsigned .so fails
        with EACCES ("Permission denied"), which numpy wraps as its misleading
        "you should not try to import numpy from its source directory" message.
        The CI worker's compiler does not auto code-sign (unlike the local
        Harmony toolchain wrapper), so the packaged numpy C-extensions must be
        signed explicitly here — same pattern already used by the nzbget recipe.
        Verified on device: strip .codesign -> import fails EACCES; re-sign via
        binary-sign-tool -selfSign 1 -> import numpy OK.
        """
        if str(self.settings.os) != "OHOS":
            return
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(sign_tool):
            self.output.warning(
                "binary-sign-tool not found at %s; packaged .so will not load "
                "on OHOS (EACCES)" % sign_tool)
            return
        signed = 0
        for root, _dirs, files in os.walk(self.package_folder):
            for name in files:
                if not (name.endswith(".so") or ".so." in name):
                    continue
                path = os.path.join(root, name)
                try:
                    if os.path.isfile(objcopy):
                        self.run('"%s" --remove-section .codesign "%s" || true'
                                 % (objcopy, path))
                    self.run('"%s" sign -inFile "%s" -outFile "%s.signed" '
                             '-selfSign 1' % (sign_tool, path, path))
                    out = path + ".signed"
                    if os.path.exists(out):
                        shutil.move(out, path)
                        signed += 1
                except Exception as e:  # noqa: BLE001 - best-effort, keep building
                    self.output.warning("OHOS sign failed for %s: %s" % (path, e))
                try:
                    os.chmod(path, 0o755)
                except PermissionError:
                    pass
        self.output.info("OHOS code-signed %d shared libraries" % signed)

    def _py_ver(self):
        return f"python{sys.version_info.major}.{sys.version_info.minor}"

    def package_info(self):
        site = os.path.join(
            self.package_folder, "lib", self._py_ver(), "site-packages"
        )
        self.output.info(f"PYTHONPATH += {site}")
        self.env_info.PYTHONPATH.append(site)
