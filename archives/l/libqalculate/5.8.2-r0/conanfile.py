#!/usr/bin/env python3
"""Conan recipe — libqalculate 5.8.2-r0 (Autotools).

libqalculate 是多用途桌面计算器库（任意精度/符号计算/单位换算），
同时构建 qalc 命令行工具。Autotools 构建。

OHOS 适配（参考 main 上已合入的 libgsf/libgsf 同类先例）:
- config.guess: 添加 HarmonyOS 检测（aarch64-HarmonyOS -> aarch64-unknown-linux-gnu）
- configure: 跳过 IT_PROG_INTLTOOL 的 XML::Parser(perl) 检查（OHOS 无该模块，
  且 data/*.xml.in 用 intltool-merge shim 生成）；移除 umask 077（HMDFS 限制）
- util.cc: pthread_cancel/pthread_setcancelstate/pthread_setcanceltype 在 OHOS
  musl 上不可用，用 HAVE_PTHREAD_* 宏守卫（feature detection 生成 pthread_compat.h）
- intltool-merge: cmd-pkgs 工具缺 XML::Parser 依赖 -> 写 shim（去 _ 翻译标记）

⚠️ 不用 AutotoolsDeps/VirtualRunEnv（cddlib 同坑）：
AutotoolsDeps 会把 conan 依赖的 -l 全塞进 LIBS，configure 早期 conftest
（cross-compiling 检查）也链上依赖库，运行期找不到 conan 缓存 .so -> $?=127
"cannot run C compiled programs"；VirtualRunEnv(scope=build) 又把 conan 依赖
lib 目录放进 LD_LIBRARY_PATH，llvm lld 自身依赖 SDK 的 libxml2.so.16 会被
conan libxml2.so.16 劫持（SONAME 相同符号集不同）-> "Error relocating lld"。
libqalculate 的 configure 检查（AC_CHECK_LIB gmp/mpfr/readline 仅链接不运行、
PKG_CHECK_MODULES libxml-2.0 走 pkg-config）不需要运行期依赖库，
依赖路径用 include/lib flag 手动注入即可。
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

# cmd-pkgs 预编译工具（intltool/gettext 供 IT_PROG_INTLTOOL 检查）
TOOL_PKGS = [
    ("intltool", "0.51.0", "bin/intltool-update"),
    ("gettext", "0.22.5", "bin/msgfmt"),
]
# cmd-pkgs 包安装前缀（与 CI 环境一致）
GTK_PREFIX = os.path.expanduser("~/usr/local")


class LibqalculateConan(ConanFile):
    name = "libqalculate"
    version = "5.8.2-r0"
    description = ("A multi-purpose desktop calculator library with arbitrary "
                   "precision, symbolic calculation, unit conversion and more")
    license = "GPL-2.0-or-later"
    homepage = "https://qalculate.github.io/"
    url = "https://github.com/Qalculate/libqalculate"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # libqalculate configure.ac 对 gmp/mpfr 的 AC_CHECK_LIB 是硬错误，
        # libxml-2.0 用 PKG_CHECK_MODULES 硬检查；readline 缺头不硬错误但
        # qalc CLI 需要 readline 增强 -> 全部 requires（制品仓均已发布）
        self.requires("gmp/6.3.0")
        self.requires("mpfr/4.2.2")
        self.requires("libxml2/2.15.3")
        self.requires("readline/8.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # pkg-config .pc（PkgConfigDeps 生成 libxml-2.0.pc 等，供 configure 的
        # PKG_CHECK_MODULES 使用；配合 build() 里 os.environ 注入 PKG_CONFIG_PATH）
        PkgConfigDeps(self).generate()

        # intltool-merge shim 目录 PATH 前置（configure 的 AC_PATH_PROG 找到
        # shim，data/Makefile 用 $(INTLTOOL_MERGE) 指向它）
        shim_dir = os.path.join(self.build_folder, "_intltool_shim")
        os.makedirs(shim_dir, exist_ok=True)
        env = Environment()
        env.prepend_path("PATH", shim_dir)
        env.vars(self).save_script("intltool_shim")

        # 依赖 include/lib 路径手动注入（不用 AutotoolsDeps，避免 LIBS 污染
        # configure 早期 conftest；cddlib 实撞记录见模块 docstring）
        tc = AutotoolsToolchain(self)
        # libcurl/ICU 可选依赖（制品仓未发布）-> 关闭
        tc.configure_args.append("--without-libcurl")
        tc.configure_args.append("--without-icu")
        _env = tc.environment()
        for _ref, _dep in self.dependencies.items():
            _inc = " ".join("-I{}".format(_d)
                            for _d in (_dep.cpp_info.includedirs or [])
                            if os.path.isabs(_d))
            if _inc:
                _env.prepend("CPPFLAGS", _inc)
                _env.prepend("CXXFLAGS", _inc)
                _env.prepend("CFLAGS", _inc)
            _lp = " ".join("-L{}".format(_d)
                           for _d in (_dep.cpp_info.libdirs or [])
                           if os.path.isabs(_d))
            if _lp:
                _env.prepend("LDFLAGS", _lp)
        tc.generate(_env)

    def _install_cmd_pkg(self, name, version, prefix, marker):
        """从 cmd-pkgs 下载安装预编译工具到 prefix（gnumeric 同款模式）。"""
        if os.path.isfile(os.path.join(prefix, marker)):
            self.output.info(f"{name} already installed at {prefix}")
            return
        import ssl
        import tarfile
        import urllib.request
        from io import BytesIO
        fname = f"{name}-{version}-ohos-aarch64.tar.gz"
        url = ("https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/"
               f"download/pkgs/{fname}")
        self.output.info(f"Installing {name} {version} from cmd-pkgs")
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(url, context=ctx, timeout=600) as resp:
            data = resp.read()
        with tarfile.open(fileobj=BytesIO(data), mode="r:gz") as tf:
            os.makedirs(prefix, exist_ok=True)
            tf.extractall(prefix)
        self.output.info(f"  Installed {name} {version} from cmd-pkgs")

    def _ensure_build_tools(self):
        """IT_PROG_INTLTOOL 硬性要求 intltool + GNU gettext 三工具。"""
        for name, version, marker in TOOL_PKGS:
            if os.path.isfile(os.path.join(GTK_PREFIX, marker)):
                self.output.info(f"{name} already installed at {GTK_PREFIX}")
                continue
            self._install_cmd_pkg(name, version, GTK_PREFIX, marker)

    def _write_intltool_shim(self):
        """替代 intltool-merge：去掉 .xml.in 里的 _ 翻译标记（XML::Parser 不可用）。
        data/Makefile 调用形如: intltool-merge -x -u -c cache po $< $@
        → 最后一个参数是 output，倒数第二个是 input。

        ⚠️ 必须覆盖 $HOME/usr/local/bin/intltool-merge（cmd-pkgs 安装的真实
        工具）：CI 干净环境下 configure 的 AC_PATH_PROG 会优先命中该路径（profile
        buildenv PATH 前置 /usr/local/bin），PATH 里新增的 shim 目录优先级不够，
        导致 data/*.xml 生成时仍调用真实 intltool-merge → XML::Parser 报错。
        本地探索阶段正是手动覆盖该文件才通过，配方需复刻同一路径。"""
        # 1) 覆盖 $HOME/usr/local/bin/intltool-merge（备份原文件）
        bin_dir = os.path.join(GTK_PREFIX, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        real_merge = os.path.join(bin_dir, "intltool-merge")
        if os.path.exists(real_merge) and not os.path.exists(real_merge + ".cmdpkgs"):
            os.rename(real_merge, real_merge + ".cmdpkgs")
            self.output.info("backed up original intltool-merge -> .cmdpkgs")
        script = (
            "#!/bin/sh\n"
            "input=\"\"\n"
            "output=\"\"\n"
            "for arg in \"$@\"; do\n"
            "    input=\"$output\"\n"
            "    output=\"$arg\"\n"
            "done\n"
            "[ -n \"$input\" ] && [ -n \"$output\" ] || exit 1\n"
            "perl -pe 's/<(\\/?)_([a-zA-Z][a-zA-Z0-9_]*)>/<$1$2>/g' \"$input\" > \"$output\"\n"
        )
        with open(real_merge, "w") as f:
            f.write(script)
        os.chmod(real_merge, 0o755)
        self.output.info("Wrote intltool-merge shim to " + real_merge)
        # 2) 同时写入 build 目录 shim 目录（PATH 兜底）
        shim_dir = os.path.join(self.build_folder, "_intltool_shim")
        os.makedirs(shim_dir, exist_ok=True)
        shim2 = os.path.join(shim_dir, "intltool-merge")
        with open(shim2, "w") as f:
            f.write(script)
        os.chmod(shim2, 0o755)

    def _write_pthread_compat(self):
        """feature detection：OHOS musl 无 pthread_cancel ->
        pthread_compat.h 不定义 HAVE_PTHREAD_* 宏，util.cc 守卫块被编译掉。

        ⚠️ 检测编译必须加 -Werror=implicit-function-declaration：OHOS 头文件
        里没有 pthread_cancel/pthread_setcancelstate 声明，C 语法允许隐式声明
        （仅警告），若不加 -Werror 会误判"可用"而定义 HAVE_PTHREAD_*=1，
        导致 util.cc 的调用不被守卫、OHOS musl 编译报 symbol not found。"""
        src = os.path.join(self.source_folder, "libqalculate")
        os.makedirs(src, exist_ok=True)
        test_c = (
            '#include <pthread.h>\n'
            'int main(){pthread_cancel(0);'
            'pthread_setcancelstate(0,0);'
            'pthread_setcanceltype(0,0);return 0;}\n'
        )
        test_file = os.path.join(self.build_folder, "_pthread_test.c")
        header = os.path.join(src, "pthread_compat.h")
        with open(test_file, "w") as f:
            f.write(test_c)
        try:
            self.run(f"$CC -Werror=implicit-function-declaration -c "
                     f"{test_file} -o /dev/null 2>/dev/null",
                     env="conanbuild")
            with open(header, "w") as f:
                f.write("#pragma once\n")
                f.write("#define HAVE_PTHREAD_CANCEL 1\n")
                f.write("#define HAVE_PTHREAD_SETCANCELSTATE 1\n")
                f.write("#define HAVE_PTHREAD_SETCANCELTYPE 1\n")
            self.output.info("pthread_cancel available -> HAVE_PTHREAD_* on")
        except Exception:
            with open(header, "w") as f:
                f.write("#pragma once\n")
                f.write("/* pthread_cancel not available on this platform */\n")
            self.output.info("pthread_cancel unavailable -> HAVE_PTHREAD_* off")

    def _fix_la_files(self):
        """依赖 .la 的 libdir='//lib'（conan 包 prefix=/ 拼接错误）——libtool
        创建 libqalculate.la 时按 libdir 读取依赖 .la 失败（sed //lib/...）。

        注意：dependency_libs 中的交叉引用（如 mpfr.la 引用 libgmp.la）必须
        解析到**真正拥有该 .la 的包**的 lib 目录，不能一律替换成当前包自己的
        lib 目录（否则指向自身包内不存在的 libgmp.la）。先收集全部依赖包内
        .la 的真实路径注册表，再按 basename 做全局替换。"""
        import re as _re
        # 1) 收集所有依赖包 lib 目录下的 .la：basename -> 完整真实路径
        la_registry = {}
        for _ref, _dep in self.dependencies.items():
            dep_pkg = _dep.package_folder
            if not dep_pkg:
                continue
            dep_lib = os.path.join(dep_pkg, "lib")
            if not os.path.isdir(dep_lib):
                continue
            for la_name in os.listdir(dep_lib):
                if la_name.endswith(".la"):
                    la_registry[la_name] = os.path.join(dep_lib, la_name)
        # 2) 修正每个 .la 的 libdir 与 dependency_libs 引用
        for la_path in la_registry.values():
            with open(la_path, "r", encoding="utf-8", errors="replace") as f:
                lac = f.read()
            own_lib = os.path.dirname(la_path)
            fixed = lac.replace("libdir='//lib'", f"libdir='{own_lib}'")
            for base, real in la_registry.items():
                # 规范 //lib/<basename> 引用 -> 真正所属包路径
                fixed = fixed.replace(f"//lib/{base}", real)
                # 兜底：上轮/其他配方可能已把 //lib 替换成错误包路径，
                # 若该 basename 并不属于当前 own_lib 则纠正为真实路径
                if not real.startswith(own_lib):
                    fixed = fixed.replace(f"{own_lib}/{base}", real)
            if fixed != lac:
                with open(la_path, "w", encoding="utf-8") as f:
                    f.write(fixed)
                self.output.info(f"patched {os.path.basename(la_path)}: "
                                 f"libdir/deps -> {own_lib}")

    def build(self):
        self._ensure_build_tools()
        self._write_intltool_shim()
        self._write_pthread_compat()
        apply_conandata_patches(self)
        self._fix_la_files()
        # LD_LIBRARY_PATH 注入（libgsf 模式：os.environ 直接注入，buildenv
        # 沙箱不生效）。必须显式提供构建期运行库路径，实测三条：
        #   1. lld(clang 调用) 自身依赖 SDK 的 libxml2.so.16 -> SDK llvm/lib
        #      必须在 conan 依赖目录【之前】，否则加载 conan libxml2.so.16
        #      （SONAME 相同符号集不同）-> "Error relocating lld" 崩溃；
        #   2. fixpo 等构建期 C++ 工具依赖 libc++_shared.so -> /system/lib64
        #      或 SDK llvm/lib/aarch64-linux-ohos 必须显式给出（conanbuild
        #      沙箱环境不会自动带），否则 "symbol not found" 加载失败；
        #   3. conftest 运行期需要 conan 依赖 gmp/mpfr/readline 等 .so
        #      （AutotoolsDeps 会把 -l 塞进链接行 -> 运行需找库）。
        import itertools as _it
        sdk_llvm_lib = ("/data/service/hnp/ohos-sdk.org/"
                        "ohos-sdk_26.0.0.18/ohos/native/llvm/lib")
        sdk_ohos_lib = os.path.join(sdk_llvm_lib, "aarch64-linux-ohos")
        _lib_dirs = [sdk_llvm_lib, sdk_ohos_lib, "/system/lib64", "/system/lib"]
        for _ref, _dep in self.dependencies.items():
            for _lp in (_dep.cpp_info.libdirs or []):
                if os.path.isabs(_lp) and _lp not in _lib_dirs:
                    _lib_dirs.append(_lp)
        _prev = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            list(_it.chain(_lib_dirs, ([_prev] if _prev else []))))
        self.output.info("LD_LIBRARY_PATH=" + os.environ["LD_LIBRARY_PATH"])
        # PKG_CONFIG_PATH 注入（libgsf 模式：os.environ 直接注入，buildenv 在
        # conanbuild 沙箱不生效）：PkgConfigDeps 生成的 .pc 在 build 目录，
        # 依赖包 pkgconfig 目录也加入
        _pkg_dirs = []
        for _ref, _dep in self.dependencies.items():
            for _lp in (_dep.cpp_info.libdirs or []):
                if os.path.isabs(_lp):
                    _pkg_dirs.append(os.path.join(_lp, "pkgconfig"))
        os.environ["PKG_CONFIG_PATH"] = os.pathsep.join(_pkg_dirs)
        self.output.info("PKG_CONFIG_PATH=" + os.environ["PKG_CONFIG_PATH"])
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # libtool 默认生成 .la（libdir 烤死绝对路径）-> 删除
        la = os.path.join(self.package_folder, "lib", "libqalculate.la")
        if os.path.exists(la):
            os.unlink(la)
            self.output.info("removed libqalculate.la")

    def package_info(self):
        self.cpp_info.libs = ["qalculate"]
        self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.requires = ["gmp::gmp", "mpfr::mpfr",
                                  "libxml2::libxml2", "readline::readline"]