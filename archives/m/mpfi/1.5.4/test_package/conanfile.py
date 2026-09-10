import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import cross_building

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
    # **VirtualRunEnv 必须写上**：显式给 generators 会替换 conan 默认集，
    # 漏了就没有 conanrun 环境，test() 里 env="conanrun" 拿不到
    # LD_LIBRARY_PATH —— 编译链接全过、跑起来 `Error loading shared library`。
    generators = "PkgConfigDeps", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # mpfi 头直接 #include <mpfr.h> / <gmp.h>：显式 require，
        # 不依赖被测包 .pc 的传递声明完整性（fcl 实撞教训）。
        self.requires("mpfr/4.2.2.1")
        self.requires("gmp/6.3.0.1")

    def _pkgconfig(self, what):
        """跑 pkg-config 取 --cflags/--libs；取不到返回空串由调用方回退。"""
        pc = "mpfi"
        env = dict(os.environ)
        env["PKG_CONFIG_PATH"] = self.generators_folder + os.pathsep + env.get("PKG_CONFIG_PATH", "")
        exe = shutil.which("pkg-config", path=env.get("PATH", os.defpath))
        if not exe:
            for _cand in ("/data/service/hnp/bin/pkg-config", "/usr/bin/pkg-config"):
                if os.path.isfile(_cand) and os.access(_cand, os.X_OK):
                    exe = _cand
                    break
        if not exe:
            return ""
        try:
            out = subprocess.run([exe, what, pc], capture_output=True,
                                 text=True, env=env, timeout=60)
            if out.returncode == 0 and out.stdout.strip():
                return out.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pass
        return ""

    def _collect_includes(self):
        """pkg-config --cflags 与遍历传递依赖 cpp_info **两者合并**（不是二选一）：
        只用 pkg-config 会漏传递依赖的头（fcl 实撞：fcl.pc 不含 eigen include）；
        只用 cpp_info 会漏 .pc 里的 -D 宏。"""
        dep = self.dependencies["mpfi"].cpp_info
        incs = []
        _pc = self._pkgconfig("--cflags")
        if _pc:
            self.output.info("test_package 用 pkg-config --cflags")
            incs.extend(_pc.split())
        else:
            self.output.warning("pkg-config --cflags 取不到，回退 cpp_info")
        # 遍历传递依赖：.host 视图带 transitive 但漏 header-only 包；
        # .items() 含 header-only 但 includedirs 可能是未展开相对路径。两者都走。
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
                if not os.path.isabs(_p) and _base:
                    _p = os.path.join(_base, _p)
                if not os.path.isdir(_p):
                    continue
                incs.append("-I" + _p)
        return " ".join(dict.fromkeys(incs))

    def build(self):
        dep = self.dependencies["mpfi"].cpp_info
        inc = self._collect_includes()
        # 库目录：静态包没有 libdirs 时给空串，同一模板兼容两种形态
        libdir = dep.libdirs[0] if dep.libdirs else ""
        so = os.path.join(libdir, "libmpfi.so") if libdir else ""
        arch = os.path.join(libdir, "libmpfi.a") if libdir else ""
        cc = os.environ.get("CC", "clang")
        # C 测试不能收 C++ 标准开关；musl 需要 gnu 方言（POSIX 声明）。
        std_flag = "-std=gnu99"
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        # 优先 pkg-config --libs（真实消费方式）；拿不到再从 cpp_info 拼。
        _pcl = self._pkgconfig("--libs")
        _libs = _pcl.split() if _pcl else ["-l" + l for l in dep.libs]
        link = " ".join(["-L" + p for p in libdirs] + _libs
                        + ["-Wl,-rpath," + p for p in libdirs] + ["-lm"])
        common = f"{cc} {std_flag} {inc}"
        # 消费者测试 + 鸿蒙特有测试（TARGET_SO/TARGET_A 注入制品路径）
        self.run(f"{common} test.c -o test_probe "
                 f"-DTARGET_SO='\"{so}\"' -DTARGET_A='\"{arch}\"' {link}")
        self.run(f"{common} test_ohos.c -o test_ohos "
                 f"-DTARGET_SO='\"{so}\"' -DTARGET_A='\"{arch}\"' {link}")

    def test(self):
        # 本机为 OHOS 目标机（self-hosted）：cross_building 为 False，测试真跑。
        # 交叉构建时也无静默跳过：编译+链接本身已在 build() 验证，
        # 这里只在确属交叉且无法执行时降级，并显式说明。
        if cross_building(self):
            self.output.warning("cross-building：test 二进制无法在本机执行，"
                                "仅验证了编译+链接（上游 159 个 make check 已在 "
                                "build() 阶段于目标机真跑）")
            return
        # 用 /bin/sh -c（本机布局无 /data/service/hnp/bin/bash；POSIX sh 足够）。
        # 显式拼 LD_LIBRARY_PATH，不只依赖 conanrun（pango 实撞：
        # conanrunenv 的 libdirs 可能为空，-rpath 也不总生效）。
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        ldpath = os.pathsep.join(dict.fromkeys(libdirs))
        for bin_name in ("test_probe", "test_ohos"):
            self.run(
                f"/bin/sh -c 'export LD_LIBRARY_PATH=\"{ldpath}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}\"; ./{bin_name}'",
                env="conanrun")
