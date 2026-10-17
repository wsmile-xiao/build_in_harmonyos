import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.env import VirtualBuildEnv

# 与标准 C/C++ 头同名的文件名。含这些文件的目录**不得**进 -I 搜索路径，
# 否则会遮蔽标准库的同名头（fcl 的 fcl/common/time.h 遮蔽 <time.h> 实撞）。
_STD_HEADER_NAMES = {
    "time.h", "math.h", "string.h", "stdio.h", "stdlib.h", "assert.h", "errno.h",
    "signal.h", "limits.h", "float.h", "locale.h", "setjmp.h", "ctype.h", "wchar.h",
    "complex.h", "fenv.h", "inttypes.h", "stdint.h", "stddef.h", "stdarg.h",
    "memory", "list", "array", "vector", "string", "map", "set", "queue", "stack",
    "algorithm", "functional", "utility", "thread", "mutex", "atomic", "chrono",
}


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # PkgConfigDeps 让下面的 pkg-config 能找到依赖的 .pc。
    # **VirtualRunEnv / VirtualBuildEnv 必须一并写上**：显式给 generators 会
    # **替换**（而非追加）conan 的默认集，漏了 VirtualRunEnv 就没有 conanrun
    # 环境，test() 里 env="conanrun" 拿不到 LD_LIBRARY_PATH，
    # 表现为编译链接全过、跑起来报 `Error loading shared library ...`（实撞）。
    generators = "PkgConfigDeps", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 显式声明依赖：flint.pc 有 `Requires: gmp mpfr`，只有直接
        # requirements 才会让 PkgConfigDeps 生成对应的 .pc 供其引用。
        self.requires("gmp/6.3.0")
        self.requires("mpfr/4.2.2")

    def _resolve_cc(self):
        # 与 recipe 相同的解析链（R33，无硬编码路径）：
        # conf compiler_executables → VirtualBuildEnv 的 CC。
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c")
        if not cc:
            with VirtualBuildEnv(self).vars().apply():
                cc = os.environ.get("CC")
        if not cc:
            raise ConanException(
                "flint test_package: C compiler not found — set the "
                "tools.build:compiler_executables conf or the CC "
                "environment variable"
            )
        return cc

    def _pkgconfig(self, what):
        """跑 pkg-config 取 --cflags 或 --libs。取不到返回空串，由调用方回退。"""
        env = dict(os.environ)
        env["PKG_CONFIG_PATH"] = self.generators_folder + os.pathsep + env.get("PKG_CONFIG_PATH", "")
        exe = shutil.which("pkg-config", path=env.get("PATH", os.defpath))
        if not exe:
            return ""
        try:
            out = subprocess.run([exe, what, "flint"], capture_output=True,
                                 text=True, env=env, timeout=60)
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
        return ""

    def _pkgconfig_cflags(self):
        """优先用 pkg-config 取编译标志 —— 这才是真实消费方的用法。

        为什么不再手工从 cpp_info 拼 -I：那条路是打地鼠。头文件的实际位置
        有太多形态，而 conan 生成的 .pc 里这些路径本来就是齐的
        （flint.pc 的 Requires 会带出 gmp/mpfr 的 include）。
        取不到 .pc 时才回退到 cpp_info 拼装。
        """
        out = self._pkgconfig("--cflags")
        if out:
            self.output.info("test_package 用 pkg-config --cflags")
        else:
            self.output.warning("pkg-config --cflags 取不到，回退 cpp_info")
        return out

    def _collect_includes(self):
        """pkg-config 与「遍历依赖 cpp_info」**两者合并**，不是二选一。

        只用 pkg-config 会漏掉传递依赖的头（.pc 未必声明上游的 include）；
        只用 cpp_info 又会漏掉 .pc 里的 -D 宏等非路径 cflags。
        ⚠️ 必须遍历**传递依赖**：test_package 只 require 被测包本身，
        被测包的依赖（gmp/mpfr 等）默认在 host 视图里。
        """
        incs = []
        _pc = self._pkgconfig_cflags()
        if _pc:
            incs.extend(_pc.split())
        else:
            self.output.warning("pkg-config --cflags 取不到，仅用 cpp_info")
        _seen, _deps = set(), []
        for _view in ("host", None):
            try:
                _it = (self.dependencies.host if _view else self.dependencies).items()
            except AttributeError:
                continue
            for _r, _dd in _it:
                _k = str(_r.ref) if hasattr(_r, "ref") else str(_r)
                if _k in _seen:
                    continue
                _seen.add(_k)
                _deps.append((_r, _dd))
        for _ref, _d in _deps:
            _base = getattr(_d, "package_folder", None) or ""
            for _p in _d.cpp_info.includedirs:
                # 相对路径要用该依赖的 package_folder 补成绝对路径
                if not os.path.isabs(_p) and _base:
                    _p = os.path.join(_base, _p)
                if not os.path.isdir(_p):
                    continue
                incs.append("-I" + _p)
                # 有些库把头放在版本化子目录（如 include/eigen3/Eigen），补一层。
                # ⚠️ 但**绝不能**把含有与标准头同名文件的子目录加进搜索路径
                # （fcl 0.7.0 实撞：include/fcl/common/ 里有个 time.h，
                # 一旦上了 -I，<ctime> 就包到它而不是 C 库的 time.h）。
                for _name in sorted(os.listdir(_p)):
                    _sub = os.path.join(_p, _name)
                    if not os.path.isdir(_sub):
                        continue
                    _files = os.listdir(_sub)
                    # **大小写不敏感**：鸿蒙设备的文件系统不区分大小写，
                    # `#include <string.h>` 会命中 `Poco/String.h`（poco 实撞）。
                    if any(f.lower() in _STD_HEADER_NAMES for f in _files):
                        continue
                    # 两种都要展开：
                    #   ① 子目录里**直接**有头文件
                    #   ② 子目录里没有头文件，但它的下一层有（eigen：
                    #      include/eigen3/ 里只有 Eigen/ 和 unsupported/）
                    _direct = any(f.endswith((".h", ".hpp", ".hh", ".hxx")) for f in _files)
                    _nested = any(
                        os.path.isdir(os.path.join(_sub, _f))
                        and any(g.endswith((".h", ".hpp", ".hh", ".hxx"))
                                for g in os.listdir(os.path.join(_sub, _f))[:50])
                        for _f in _files
                        if not _f.startswith("."))
                    if not (_direct or _nested):
                        continue
                    incs.append("-I" + _sub)
        return " ".join(dict.fromkeys(incs))

    def build(self):
        dep = self.dependencies["flint"].cpp_info
        inc = self._collect_includes()
        # 优先 pkg-config --libs（理由同 cflags 分支）
        _pcl = self._pkgconfig("--libs")
        if _pcl:
            _libs = _pcl.split()
        else:
            # 回退必须覆盖**全部依赖**的库：gmp/mpfr 在制品仓是静态包，
            # 测试代码直接调用其符号（如 mpfr_set_d）时没有 -lmpfr/-lgmp
            # 就会 undefined reference（WSL 无 pkg-config 场景实撞）。
            # 顺序须满足静态库单遍链接：被测库在前，传递依赖按声明逆序
            # 在后（mpfr 依赖 gmp，更深的库靠后）。
            _libs = ["-l" + l for l in dep.libs]
            for _ref, _d in reversed(list(self.dependencies.items())[1:]):
                _libs += ["-l" + l for l in _d.cpp_info.libs]
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        link = " ".join(["-L" + p for p in libdirs] + _libs
                        + ["-Wl,-rpath," + p for p in libdirs])
        cc = self._resolve_cc()
        # C 测试**不能**收 C++ 标准开关（clang 报 not allowed with 'C'）。
        # musl 上还要用 gnu 方言：严格 ISO 方言不定义 _POSIX_C_SOURCE，
        # POSIX 函数（clock_gettime 等）在 musl 头里就不声明。
        self.run("{} -std=gnu99 test.c -o test_probe {} {}".format(cc, inc, link))

    def _ld_library_path(self):
        # **显式拼 LD_LIBRARY_PATH**，不能只依赖 conanrun：
        # VirtualRunEnv 生成的 conanrunenv 里 libdirs 可能是空的
        # （shared=False 发布的包 conan 视为静态、不写 libdirs），
        # 而链接期的 -Wl,-rpath 也不总起作用。
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        return os.pathsep.join(dict.fromkeys(libdirs))

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        ldpath = self._ld_library_path()
        self.run('export LD_LIBRARY_PATH="{}:${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"; ./test_probe'.format(ldpath),
                 env="conanrun")
