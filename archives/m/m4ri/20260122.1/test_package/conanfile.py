import os

# 与标准 C/C++ 头同名的文件名。含这些文件的目录**不得**进 -I 搜索路径，
# 否则会遮蔽标准库的同名头（fcl 的 fcl/common/time.h 遮蔽 <time.h> 实撞）。
_STD_HEADER_NAMES = {
    "time.h", "math.h", "string.h", "stdio.h", "stdlib.h", "assert.h", "errno.h",
    "signal.h", "limits.h", "float.h", "locale.h", "setjmp.h", "ctype.h", "wchar.h",
    "complex.h", "fenv.h", "inttypes.h", "stdint.h", "stddef.h", "stdarg.h",
    "memory", "list", "array", "vector", "string", "map", "set", "queue", "stack",
    "algorithm", "functional", "utility", "thread", "mutex", "atomic", "chrono",
}
import shutil
import subprocess
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # PkgConfigDeps 让下面的 pkg-config 能找到依赖的 .pc。
    # **VirtualRunEnv / VirtualBuildEnv 必须一并写上**：显式给 generators 会
    # **替换**（而非追加）conan 的默认集，漏了 VirtualRunEnv 就没有 conanrun 环境，
    # test() 里 env="conanrun" 拿不到 LD_LIBRARY_PATH，
    # 表现为编译链接全过、跑起来报 `Error loading shared library ...`（实撞）。
    generators = "PkgConfigDeps", "VirtualRunEnv", "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("libpng/1.6.58")


    def _pkgconfig(self, what):
        """跑 pkg-config 取 --cflags 或 --libs。取不到返回空串，由调用方回退。"""
        pc = "m4ri" or "m4ri"
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

    def _pkgconfig_cflags(self):
        """优先用 pkg-config 取编译标志 —— 这才是真实消费方的用法。

        为什么不再手工从 cpp_info 拼 -I：那条路是打地鼠。头文件的实际位置
        有太多形态，而各包 cpp_info 的声明完整度参差：
          · pango   头在 include/pango-1.0/
          · glib    头在 include/glib-2.0/，**而 glibconfig.h 在 lib/glib-2.0/include/**（lib 侧！）
          · fribidi 头在 include/fribidi/
        逐条加扫描规则永远追不上；而 conan 生成的 .pc 里这些路径本来就是齐的。
        取不到 .pc 时才回退到 cpp_info 拼装。
        """
        out = self._pkgconfig("--cflags")
        if out:
            self.output.info("test_package 用 pkg-config --cflags")
        else:
            self.output.warning("pkg-config --cflags 取不到，回退 cpp_info")
        return out

    def build(self):
        dep = self.dependencies["m4ri"].cpp_info
        # pkg-config 的 --cflags 与「遍历依赖 cpp_info」**两者合并**，不是二选一。
        # 只用 pkg-config 会漏掉传递依赖的头：被测库的 .pc 未必声明上游的 include。
        #   fcl 0.7.0 实撞：fcl.pc 不含 eigen 的 include，test.cpp 报
        #   `fatal error: 'Eigen/Dense' file not found` —— 而库本体明明编译成功了。
        # 只用 cpp_info 又会漏掉 .pc 里的 -D 宏等非路径 cflags，所以两者都要。
        incs = []
        _pc = self._pkgconfig_cflags()
        if _pc:
            incs.extend(_pc.split())
        else:
            self.output.warning("pkg-config --cflags 取不到，仅用 cpp_info")
        # ⚠️ 必须遍历**传递依赖**：self.dependencies.items() 默认只给直接依赖，
        # 而 test_package 只 require 被测包本身 —— 被测包的依赖（eigen/boost 等）
        # 一个都遍历不到。
        #   orocos-kdl 1.5.1 实撞：编译命令里只有 kdl 自己的 -I，报
        #   `'Eigen/Core' file not found`；我连改三轮 include 展开逻辑都没治好，
        #   因为根本不是展开的问题，是**这些依赖压根没进循环**。
        # host 视图带 transitive；老 conan 没有该属性时退回直接依赖。
        # 两个视图**都要遍历**并去重：
        #   · .host 带传递依赖，但**漏 header-only 包**
        #   · .items() 有 header-only 包，但对它们 includedirs 是**未展开的相对路径**
        # eigen 实撞（fcl 0.7.0）：.host 里根本没有 eigen；.items() 里有，
        # 但 includedirs 是 ['include'] 而非绝对路径 —— 直接用会得到一个
        # 指向当前目录的 `-Iinclude`，编译时报 'Eigen/Core' file not found。
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
                if not os.path.isdir(_p):
                    continue
                # 有些库把头放在版本化子目录（如 include/eigen3/Eigen），补一层。
                # ⚠️ 但**绝不能**把含有与标准头同名文件的子目录加进搜索路径：
                #   fcl 0.7.0 实撞——include/fcl/common/ 里有个 time.h，
                #   一旦上了 -I，libc++ 的 <ctime> 就会包到它而不是 C 库的 time.h，
                #   报 `no member named 'system_clock' in namespace 'std::chrono'`，
                #   看上去像 fcl 源码有问题，实则是我们把搜索路径污染了。
                for _name in sorted(os.listdir(_p)):
                    _sub = os.path.join(_p, _name)
                    if not os.path.isdir(_sub):
                        continue
                    _files = os.listdir(_sub)
                    # **大小写不敏感**：鸿蒙设备的文件系统不区分大小写，
                    # `#include <string.h>` 会命中 `Poco/String.h`。精确匹配认不出
                    # CamelCase 头，include/Poco 照样上 -I，libc++ 的 cstring 就包到它，
                    # 之后 <mutex>/<ctime> 连环塌（poco 1.15.3 实撞，报的却是
                    # `use of undeclared identifier 'CLOCK_MONOTONIC'` 这种看着不相干的错）。
                    if any(f.lower() in _STD_HEADER_NAMES for f in _files):
                        continue
                    # 两种都要展开：
                    #   ① 子目录里**直接**有头文件
                    #   ② 子目录里没有头文件，但它的下一层有（eigen 就是这样：
                    #      include/eigen3/ 里只有 Eigen/ 和 unsupported/ 两个目录，
                    #      真正的头在 include/eigen3/Eigen/Core。
                    #      只认①会漏掉它，报 'Eigen/Core' file not found —— 实撞三次）
                    _direct = any(f.endswith((".h", ".hpp", ".hh", ".hxx")) for f in _files)
                    _nested = any(
                        os.path.isdir(os.path.join(_sub, _f))
                        and any(g.endswith((".h", ".hpp", ".hh", ".hxx", ""))
                                for g in os.listdir(os.path.join(_sub, _f))[:50])
                        for _f in _files
                        if not _f.startswith("."))
                    if not (_direct or _nested):
                        continue
                    incs.append("-I" + _sub)
        inc = " ".join(dict.fromkeys(incs))
        # **header-only 包没有 libdirs**（cpp_info.libdirs = []），无条件取 [0] 会
        # IndexError，整个 test_package 在 build() 里崩掉 —— 而包本身是好的。
        # 没有库目录时 TARGET_SO 给空串：纯头文件测试用不到它，
        # 而留着这个宏是为了让同一份模板对两类包都能编。
        libdir = dep.libdirs[0] if dep.libdirs else ""
        so = os.path.join(libdir, "libm4ri.so") if libdir else ""
        cc = os.environ.get("CC", "clang")
        # C 测试**不能**收 C++ 标准开关（clang 报 not allowed with 'C'）。
        # musl 上还要用 gnu 方言：严格 ISO 方言不定义 _POSIX_C_SOURCE，
        # POSIX 函数（clock_gettime 等）在 musl 头里就不声明。
        std_flag = "-std=gnu99"
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        # 优先 pkg-config --libs（理由同 cpp 分支）；保留 -ldl 供 dlopen 探针用。
        _pcl = self._pkgconfig("--libs")
        _libs = _pcl.split() if _pcl else ["-l" + l for l in dep.libs]
        link = " ".join(["-L" + p for p in libdirs] + _libs
                        + ["-Wl,-rpath," + p for p in libdirs] + ["-ldl"])
        self.run(f"{cc} {std_flag} test.c -o test_probe {inc} -DTARGET_SO='\"{so}\"' {link}")
        # HarmonyOS PC 专项测试：OHOS AArch64 目标属性宏 + m4ri 核心 API
        # （mul/rank/transpose/add、跨 64 位字边界、PNG 文件往返）真实运行，
        # 与通用 test.c 互补；编译开关与 link 完全同一路径（真实消费方式）。
        self.run(f"{cc} {std_flag} test_ohos.c -o test_ohos {inc} {link}")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        if False:
            self.output.info("skip_test_run：GUI/app 库只验编译+链接")
            return
        # **显式拼 LD_LIBRARY_PATH**，不能只依赖 conanrun：
        # VirtualRunEnv 生成的 conanrunenv 里 libdirs 可能是空的（本仓已记录：
        # shared=False 发布的包 conan 视为静态、不写 libdirs，但包里确实装了 .so），
        # 而链接期的 -Wl,-rpath 也不总起作用。
        # 症状是编译链接全过、一跑就 `Error loading shared library ...`（pango 实撞）。
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        ldpath = os.pathsep.join(dict.fromkeys(libdirs))
        # 不再额外包一层 bash：self.run 本就经 /bin/sh 执行（本机实撞证据：
        # /data/service/hnp/bin/bash 不存在时，报错方正是 /bin/sh —— Error 127）。
        # 以前取 CONFIG_SHELL 绝对路径是为了转义环境变量，POSIX sh 原生就支持
        # ${VAR:+:$VAR} 展开，无需 bash。
        self.run(f'export LD_LIBRARY_PATH="{ldpath}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"; ./test_probe',
                 env="conanrun")
        # musl 运行时真实验证（CI #65698 教训）：OHOS Clang + musl 目标不保证
        # 预定义 __MUSL__，宏断言不可靠；改对**最终链接产物**做 ELF 级检查。
        self._verify_musl_elf(os.path.join(self.build_folder, "test_ohos"))
        # HarmonyOS PC 专项测试与通用探针同一环境运行（显式 LD_LIBRARY_PATH）。
        self.run(f'export LD_LIBRARY_PATH="{ldpath}${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"; ./test_ohos',
                 env="conanrun")

    def _verify_musl_elf(self, exe):
        """对最终链接出的测试可执行文件做 musl/AArch64 ELF 真实检查。

        用 readelf -l（binutils）读 Program Header 拿 PT_INTERP——不依赖裸
        `file` 命令（其输出格式随版本/locale 漂移），不写死 CI 本机路径
        （readelf 经 shutil.which 从 PATH 找，找不到则 FAIL 而非静默跳过）。
        musl 的判据是 PT_INTERP 指向 musl 动态加载器；GLIBC_* 版本符号依赖
        一旦出现即说明链错到了 glibc。
        """
        import re as _re
        if not os.path.isfile(exe):
            self.output.error("musl ELF 检查：找不到 %s" % exe)
            raise ConanException("musl ELF 检查失败：二进制不存在")

        readelf = shutil.which("readelf")
        if readelf is None:
            self.output.error("musl ELF 检查：PATH 中找不到 readelf")
            raise ConanException("musl ELF 检查失败：无 readelf")

        def _readelf(args):
            return subprocess.run([readelf] + args + [exe],
                                  capture_output=True, text=True, timeout=120)

        checks = []  # (名称, 通过与否)——聚齐后统一报告

        # ---- 1) ELF64 + EM_AARCH64：readelf -h 的 Class/Machine 行 ----
        # readelf 的字段值按列对齐，Class/Machine 前有大量空格，不能锚定行首。
        out_h = _readelf(["-h"])
        if out_h.returncode != 0:
            self.output.error("readelf -h 失败：%s" % out_h.stderr.strip())
            raise ConanException("musl ELF 检查失败：readelf -h 不可用")
        hdr = out_h.stdout
        checks.append(("ELF64", _re.search(r"Class:\s+ELF64\b", hdr) is not None))
        checks.append(("EM_AARCH64", _re.search(r"Machine:\s+AArch64\b", hdr) is not None))

        # ---- 2) PT_INTERP == /lib/ld-musl-aarch64.so.1（musl 判据） ----
        # INTERP 段本身那行只给 offset，动态加载器路径在
        # 「[Requesting program interpreter: ...]」注释行里。
        out_l = _readelf(["-l"])
        if out_l.returncode != 0:
            self.output.error("readelf -l 失败：%s" % out_l.stderr.strip())
            raise ConanException("musl ELF 检查失败：readelf -l 不可用")
        m = _re.search(r"\[Requesting program interpreter:\s*(\S+?)\]", out_l.stdout)
        interp = m.group(1) if m else ""
        checks.append(("PT_INTERP == /lib/ld-musl-aarch64.so.1",
                       interp == "/lib/ld-musl-aarch64.so.1"))

        # ---- 3) 无 GLIBC_* 版本符号依赖（链到 glibc 即败） ----
        out_v = _readelf(["--version-info"])
        checks.append(("无 GLIBC_* 版本依赖", "GLIBC_" not in out_v.stdout))

        failed = [name for name, ok in checks if not ok]
        for name, ok in checks:
            (self.output.info if ok else self.output.error)(
                ("PASS" if ok else "FAIL") + ": musl ELF " + name)
        if failed:
            raise ConanException("musl ELF 检查失败：%s（PT_INTERP 实测 %r）"
                                 % (", ".join(failed), interp))
