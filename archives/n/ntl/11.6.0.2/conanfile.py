#!/usr/bin/env python3
"""Conan recipe for NTL 11.6.0."""
import os
import shlex

from conan import ConanFile
from conan.tools.env import VirtualRunEnv
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run, cross_building
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class NtlConan(ConanFile):
    name = "ntl"
    version = "11.6.0.2"
    description = "High-performance portable C++ number theory library"
    license = "LGPL-2.1-or-later"
    homepage = "https://libntl.org"
    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("NTL supports Linux and OHOS")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def requirements(self):
        self.requires("gmp/6.3.0.1")

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        # NTL 的 configure 会**编译并运行** CheckGMP 探测程序；gmp/6.3.0.1 是共享库，
        # 不给运行期库路径就报：
        #   Error loading shared library libgmp.so.10: (needed by ./CheckGMP)
        #   Error: NTL_GMP_LIP set but GMP not available
        # 报错指向「GMP 不可用」，实为加载器找不到 .so。scope="build" 让它并入 conanbuild。
        VirtualRunEnv(self).generate(scope="build")
        AutotoolsToolchain(self).generate()

    def build(self):
        # autoconf 的 config.status 用 `umask 077` 建临时目录，这套文件系统上会导致
        #   ./config.status: ./confXXXX/subs1.awk: Permission denied
        #   config.status: error: could not setup config files machinery
        # 报的是权限，实为 umask 太严。SHARED=on 才会踩到——它要先自建 libtool，
        # 而 libtool-build/configure 是从 libtool-origin/ **构建时复制**的，
        # 所以必须在跑 NTL 的 configure 之前就把源码树里的都改掉。
        # ⚠️ 一律用别名导入：函数内 `import os` 会把 os 变成 build() 的局部名，
        # 这行之前任何 os.xxx 都 UnboundLocalError，且报错点在别处、看不出关联。
        import glob as _glob, os as _os
        for _cfg in _glob.glob(_os.path.join(self.source_folder, "**", "configure"),
                               recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as _f:
                    _text = _f.read()
            except OSError:
                continue
            if "umask 077" in _text:
                with open(_cfg, "w", encoding="utf-8") as _f:
                    _f.write(_text.replace("umask 077", "umask 022"))

        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        ar = executables.get("ar", "llvm-ar")
        ranlib = executables.get("ranlib", "llvm-ranlib")
        configure_args = [
            f"PREFIX={shlex.quote(self.package_folder)}",
            # **必须出共享库**：sage 的 ntl 绑定是**一组独立的扩展 .so**
            # （ntl_ZZ_p / ntl_ZZ_pContext / ntl_ZZX …）。静态链接时每个 .so 各揣
            # 一份 NTL 全局状态：ntl_ZZ_pContext 设好的模数上下文，ntl_ZZ_p 根本看不见，
            # 于是拿未初始化的模数做运算 → **SIGSEGV**。
            # 实撞（2026-08-14）：passagemath-ntl 10.8.7，ZZ_p 模乘三种写法全崩，
            # 而无跨模块状态的 ZZX / GF2X 一切正常——正是这个机制的指纹。
            # 官方 musllinux wheel 打包 libntl-*.so.45 佐证：上游就是动态链接。
            "SHARED=on",
            "NATIVE=off",
            "TUNE=generic",
            # GMP 后端：Sage / passagemath 生态的标配。
            # 关掉它（=off）时 NTL/ZZ.h 会额外定义一个向后兼容的遗留函数
            #     #ifndef NTL_GMP_LIP
            #     inline long digit(const ZZ& a, long k)
            #     #endif
            # 它与 CPython 3.12 的 `typedef uint32_t digit`（longintrepr.h:43）撞名，
            # Cython 生成的 `const digit* = __Pyx_PyLong_Digits(x)` 就报
            #     error: reference to 'digit' is ambiguous
            # passagemath-ntl 10.8.7 实撞 380 处。开 GMP 后端即根治，且性能更好。
            "NTL_GMP_LIP=on",
            # 开了 NTL_GMP_LIP 就必须告诉 NTL 的 configure 去哪找 GMP，
            # 否则它直接报：
            #   Error: NTL_GMP_LIP set but GMP not available
            #          -- set DEF_PREFIX or GMP_PREFIX to point to location of GMP
            "GMP_PREFIX=" + self.dependencies["gmp"].package_folder,
            "NTL_GF2X_LIB=off",
            "NTL_THREADS=on",
            "NTL_SAFE_VECTORS=on",
            "NTL_STD_CXX11=on",
            "ENABLE_RPATH=off",
            'CXX="$CXX"',
            'CXXFLAGS="$CXXFLAGS"',
            'CPPFLAGS="$CPPFLAGS"',
            'LDFLAGS="$LDFLAGS"',
            f"AR={shlex.quote(str(ar))}",
            f"RANLIB={shlex.quote(str(ranlib))}",
        ]
        if self.settings.os == "OHOS":
            # 128 位除法等**编译器内建函数**（__udivti3 …）在 compiler-rt 里。
            # 静态库时由最终可执行文件补上，所以 SHARED=off 从没暴露；共享库则会
            # 带着未定义符号出厂，运行期直接
            #   Error relocating libntl.so.45: __udivti3: symbol not found
            #
            # ⚠️ 两个「看着该管用」的做法都**实证无效**，别再试：
            #   ① LDFLAGS 里加 -rtlib=compiler-rt
            #   ② LIBTOOL_LINK_FLAGS=-Wc,-rtlib=compiler-rt（NTL 文档给的钩子，
            #      确实落进了 makefile:43，但照样没用）
            # 原因是 libtool 建共享库时用 **-nostdlib** 自己拼全套链接行，
            # `-rtlib=` 这类**驱动层选项**在那条命令里不起任何作用。
            # 唯一有效的是把 builtins 归档**当普通文件参数**放上链接行 ——
            # makefile:397 的 $(LDLIBS) 正在那个位置。
            # 不用 LIBTOOL_LINK_LIBS：它一旦显式赋值，NTL_THREADS=on 自动加的
            # -lpthread 就被顶掉（doc/config.txt:502-509）。
            from io import StringIO
            _cc = self.conf.get("tools.build:compiler_executables",
                                default={}, check_type=dict).get("c", "clang")
            _buf = StringIO()
            self.run(f"{_cc} -rtlib=compiler-rt -print-libgcc-file-name",
                     stdout=_buf, env="conanbuild")
            _rt = (_buf.getvalue().strip().splitlines() or [""])[-1].strip()
            if not _rt or not _os.path.isfile(_rt):
                raise ConanInvalidConfiguration(
                    f"找不到 compiler-rt builtins 归档（clang 报 {_rt!r}）——"
                    "共享库会缺 __udivti3，装出来的 wheel 一运行就崩")
            # 默认值是 -lm，覆盖时必须带上，否则数学函数欠链接
            configure_args.append("LDLIBS=" + shlex.quote(f"-lm {_rt}"))
        source_dir = os.path.join(self.source_folder, "src")
        cross_prefix = "CONAN_CROSS_BUILDING=1 " if cross_building(self) else ""
        # SHARED=on 时 NTL 会**先自建 libtool**，而那个 configure 走 config.guess ——
        # 鸿蒙 PC 上 `uname -s` 报 HarmonyOS，猜不出来直接
        #   configure: error: cannot guess build type; you must specify one
        # 给显式三元组即跳过猜测（NTL 自带的 config.sub 2024 版认得 *-linux-ohos）。
        if self.settings.os == "OHOS":
            _arch = {"armv8": "aarch64", "x86_64": "x86_64"}.get(
                str(self.settings.arch), str(self.settings.arch))
            _triple = f"{_arch}-unknown-linux-ohos"
            cross_prefix += (f"NTL_LIBTOOL_CONFIG_ARGS="
                             f"{shlex.quote(f'--build={_triple} --host={_triple}')} ")
        self.run(
            cross_prefix + "./configure " + " ".join(configure_args),
            cwd=source_dir,
            env="conanbuild",
        )
        self.run("make -j1", cwd=source_dir, env="conanbuild")
        if can_run(self):
            self.run(
                "bash -c 'set -o pipefail; "
                "(while sleep 120; do "
                "echo \"[ntl] upstream tests still running\"; done) & heartbeat=$!; "
                "make check 2>&1 | tee ntl-check.log; status=${PIPESTATUS[0]}; "
                "kill $heartbeat 2>/dev/null || true; "
                "wait $heartbeat 2>/dev/null || true; "
                "if grep -q \"^bad \" ntl-check.log; then exit 1; fi; "
                "exit $status'",
                cwd=source_dir,
                env="conanbuild",
            )

    def package(self):
        source_dir = os.path.join(self.source_folder, "src")
        self.run("make install", cwd=source_dir, env="conanbuild")
        copy(
            self,
            "copying.txt",
            src=os.path.join(self.source_folder, "doc"),
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["ntl"]
        self.cpp_info.set_property("cmake_file_name", "ntl")
        self.cpp_info.set_property("cmake_target_name", "ntl::ntl")
        self.cpp_info.set_property("pkg_config_name", "ntl")
        self.cpp_info.system_libs = ["m", "pthread"]
