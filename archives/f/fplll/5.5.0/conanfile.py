#!/usr/bin/env python3
"""Conan recipe — fplll 5.5.0 (autotools)"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.files import apply_conandata_patches
from conan.tools.layout import basic_layout



class FplllConan(ConanFile):
    name = "fplll"
    version = "5.5.0"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        self.requires("gmp/6.3.0")
        self.requires("mpfr/4.2.2.1")

    def layout(self):
        basic_layout(self, src_folder=".")
        # **必须源码内构建**。fplll 的发布 tarball 自带一份作者本机 configure 的
        # `fplll/fplll_config.h`（里面 `#define FPLLL_WITH_QD 1`）。异地构建时
        # configure 在 build 目录生成正确的那份，但编译命中的是源码树里那份陈旧副本，
        # `--without-qd` 形同虚设 → `fatal error: 'qd/dd_real.h' file not found`。
        # 删掉它也不行：`enumerate_base.h` 用的是相对路径 `#include "../fplll_config.h"`，
        # 删了直接报文件不存在。源码内构建让生成的那份**原地覆盖**它，两个问题一起消失。
        self.folders.build = self.folders.source

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        tc.configure_args.append("--without-qd")
        tc.configure_args.append("--with-gmp={}".format(self.dependencies["gmp"].package_folder))
        tc.configure_args.append("--with-mpfr={}".format(self.dependencies["mpfr"].package_folder))
        # 环境里可能已有 LDFLAGS（设备与 CI worker 的 ~/.zshrc 都导出了
        # -L$HOME/usr/local/lib）。conan 对 LDFLAGS 用的是 **append**，自己的 -L 排在
        # 它**后面**；链接器按 -L 顺序取第一个命中的目录，于是 `-lfoo` 可能命中系统的
        # libfoo.so 而不是 conan 包里的 libfoo.a，configure 的 conftest 运行期就加载不到：
        #   Error loading shared library libffi.so.8: (needed by ./conftest)
        #   configure: error: cannot run C compiled programs.
        # （ecl 24.5.10 实撞；本机 unset LDFLAGS 能过、CI 不 unset 就挂，
        #   等于用调用方环境掩盖了 recipe 缺陷。）
        # 把依赖的 libdir **前置**，让 recipe 不再受环境 LDFLAGS 影响，本机与 CI 行为一致。
        # ⚠️ 必须只取**绝对路径**：被 skip 的传递依赖（无 package_folder）其
        # cpp_info.libdirs 会退化成相对的 "lib"，原样拼进去就是 `-Llib`，
        # libtool 链接时直接报：
        #   ./libtool: cd: lib: No such file or directory
        #   libtool: error: cannot determine absolute directory name of 'lib'
        # （m4rie 20250128 实撞。）
        import os as _os
        _env = tc.environment()
        _Lp = " ".join("-L{}".format(_d) for _ref, _dep in self.dependencies.items()
                       for _d in (_dep.cpp_info.libdirs or []) if _os.path.isabs(_d))
        if _Lp:
            _env.prepend("LDFLAGS", _Lp)
        # fplll 用 `long double` 做高精度浮点。aarch64 上 long double 是 **128 位四精度**，
        # 它的算术全靠 compiler-rt/libgcc 的软浮点内建（__addtf3/__multf3/__trunctfdf2…）。
        # 默认链接不带 builtins 库时，构建装包一路全绿，直到**加载** libfplll.so 才炸：
        #   Error relocating .../libfplll.so.9: __addtf3: symbol not found
        # 只往 LDFLAGS 里放 `-rtlib=compiler-rt` **没用**：这个库是 libtool 链出来的，
        # libtool 只把 -L/-l/-Wl,* 这类它认识的东西透传给链接命令，别的驱动级 flag 被丢掉
        # （实测第五轮日志里 `rtlib` 一次都没出现）。两手都要：
        #   ① 放进 CXXFLAGS —— libtool 链接时用的是 `$CXX $CXXFLAGS $LDFLAGS`，能带上；
        #   ② 直接把 builtins 归档的**绝对路径**加进 LDFLAGS —— libtool 把绝对路径的 .a
        #      当对象文件透传，不受它的 flag 过滤影响。路径由编译器自己报，不写死。
        tc.extra_cxxflags.append("-rtlib=compiler-rt")
        _env.append("LDFLAGS", "-rtlib=compiler-rt")
        _builtins = self._compiler_rt_builtins()
        if _builtins:
            _env.append("LDFLAGS", _builtins)
            self.output.info("compiler-rt builtins: %s" % _builtins)
        else:
            # 找不到就**直接失败**，不要只 warn 往下走：产物会「构建装包全绿、
            # 加载 .so 才炸」，而 CI 的报错停在 test_package，看着像测试写错了。
            # （实撞：本机 CC 有值所以找得到、CI 的 generate() 环境里没有 CC，
            #   于是同一份配方本机过、CI 挂 —— 这种「靠调用方环境掩盖缺陷」必须堵死。）
            raise ConanInvalidConfiguration(
                "找不到 compiler-rt 的 builtins 归档（libclang_rt.builtins*.a）。"
                "aarch64 的 long double 是 128 位四精度，缺 __addtf3/__multf3 这组软浮点内建，"
                "libfplll.so 一加载就报 symbol not found。")
        tc.generate(_env)

    def _compiler_rt_builtins(self):
        """找到 compiler-rt 的 builtins 归档绝对路径。

        **不能只认环境变量 CC**：conan 的 generate() 在 CI 上跑时环境里没有 CC
        （本机有，于是同一份配方本机过、CI 挂 —— 见 MR 评论里的实测）。
        依次试：conan 的 compiler_executables 配置 → CC/CXX 环境变量 →
        PATH 上的 clang → 设备上 hnp 的固定路径 → 直接在 OHOS SDK 里 glob。
        """
        import glob as _glob, os as _os, shutil as _shutil, subprocess as _sp

        cands = []
        _exe = self.conf.get("tools.build:compiler_executables", check_type=dict) or {}
        cands += [_exe.get("c"), _exe.get("cpp")]
        cands += [_os.environ.get("CC"), _os.environ.get("CXX")]
        cands += [_shutil.which("clang"), "/data/service/hnp/bin/clang"]
        for _c in cands:
            if not _c or not _os.path.isfile(_c.split()[0] if " " in _c else _c):
                continue
            try:
                _out = _sp.run([_c, "--print-libgcc-file-name", "-rtlib=compiler-rt"],
                               capture_output=True, text=True, timeout=60).stdout.strip()
            except (OSError, _sp.SubprocessError):
                continue
            if _out and _os.path.isfile(_out):
                return _out
        # 编译器问不出来就自己找：SDK 里的 aarch64-linux-ohos 那份
        roots = [_os.environ.get("OHOS_SDK", ""), "/data/service/hnp"]
        for _r in roots:
            if not _r or not _os.path.isdir(_r):
                continue
            hits = _glob.glob(_os.path.join(
                _r, "**", "lib", "clang", "*", "lib", "*ohos*", "libclang_rt.builtins*.a"),
                recursive=True)
            if hits:
                return sorted(hits)[-1]
        return ""

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # 发布 tarball（ftp.gnu.org 那类）里带现成的 configure，直接用；
        # 但 **GitHub 的 archive tarball 从不含 configure**（它只是 git tree 的快照，
        # configure 是 autoreconf 的产物、不进版本库），此时必须先自举。
        # 判在运行期而非生成期：同一份配方两种源都能用。
        import os as _os
        if not _os.path.isfile(_os.path.join(self.source_folder, "", "configure")):
            self.output.info("源码树无 configure（GitHub archive 常见），先 autoreconf 自举")
            # **必须在源码所在子目录里跑**：判定用的是 SRC_SUBDIR，执行也要一致。
            # 实测 libmspack/1.11：源码是 `libmspack/configure.ac`，在顶层 autoreconf
            # 直接报 `autoreconf: error: 'configure.ac' is required`。
            autotools.autoreconf(build_script_folder=_os.path.join(
                self.source_folder, ""))
        # ⚠️ umask / uname 这类对 configure 脚本本身的修补**必须在 autoreconf 之后**：
        # 自举会重新生成 configure，放在前面等于白改（改的是不存在的文件，
        # 或改完又被覆盖）。
        import glob as _glob, os as _os
        for _cfg in _glob.glob(_os.path.join(self.source_folder, '**', 'configure'), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        # 【skill: 默认删 .la】libtool 的 .la 里烤死 libdir 绝对路径，
        # conan 包按 prefix=/ 构建 → 里面写的是 '/lib'，下游 libtool 会去找
        # `//lib/libxxx.la` 而失败（graphviz 实撞）。链接信息 .pc/cpp_info 已提供。
        import glob as _glob, os as _os
        for _la in _glob.glob(_os.path.join(self.package_folder, "lib", "*.la")):
            _os.remove(_la)




    def package_info(self):
        self.cpp_info.includedirs = self._detect_include_dirs()
        self.cpp_info.libs = ['fplll']
        self.cpp_info.set_property("cmake_file_name", "fplll")
        self.cpp_info.set_property("cmake_target_name", "fplll::fplll")
        self.cpp_info.set_property("pkg_config_name", "fplll")



    # 与标准 C/C++ 头同名的文件名。含这类文件的子目录**不能**进 includedirs，
    # 否则它会被 -isystem 加进搜索路径、抢在真正的系统头前面被找到。
    _STD_HEADER_NAMES = {
        "time.h", "math.h", "string.h", "stdio.h", "stdlib.h", "assert.h",
        "errno.h", "signal.h", "limits.h", "float.h", "locale.h", "setjmp.h",
        "ctype.h", "wchar.h", "wctype.h", "complex.h", "fenv.h", "inttypes.h",
        "stdint.h", "stddef.h", "stdarg.h", "stdbool.h", "iso646.h", "uchar.h",
        "memory", "list", "array", "vector", "string", "map", "set", "queue",
        "stack", "algorithm", "functional", "utility", "thread", "mutex",
        "atomic", "chrono", "ranges", "format", "locale",
    }

    def _detect_include_dirs(self):
        """扫 include/ 下含头文件的一层子目录，连同 include 本身一起返回。

        很多库把公开头装在版本化子目录（pango-1.0 / glib-2.0 / freetype2 / cspice…），
        只声明 include 的话，消费方按上游惯用法 #include <pango/pango.h> 就找不到 ——
        而这个缺陷在**本包构建装包时完全不暴露**，要到下游编译才炸。

        ⚠️ 但展开必须避开**与标准头同名**的子目录，否则修一个缺陷造一个更坏的：
        fmt 的 include/fmt/ 里有 locale.h，一旦把该目录 -isystem 进去，
        libc++ 的 <__locale> 执行 #include <locale.h> 时会命中 fmt/locale.h，
        musl 真正的 locale.h 永远进不来 —— 下游任何 include <sstream> 的
        翻译单元都报 `use of undeclared identifier 'uselocale'`（spdlog 实撞）。
        消费方本来就写 #include <fmt/format.h>，只需要 include/ 这一层。
        """
        import os as _os
        base = _os.path.join(self.package_folder, "include")
        dirs = ["include"]
        if not _os.path.isdir(base):
            return dirs
        for name in sorted(_os.listdir(base)):
            sub = _os.path.join(base, name)
            if not _os.path.isdir(sub):
                continue
            # 只看子目录**直接**装的头：同名遮蔽只发生在直接被搜索的那一层。
            try:
                direct = _os.listdir(sub)
            except OSError:
                continue
            # **大小写不敏感比对**：鸿蒙设备的文件系统不区分大小写，
            # `#include <string.h>` 会命中 `Poco/String.h`。守卫原先是精确匹配，
            # POCO 的 CamelCase 头一个都没被认出来，include/Poco 照样进了搜索路径 ——
            # 于是 libc++ 的 cstring 包含到 Poco/String.h，编译当场崩（poco 1.15.3 实撞）。
            if any(f.lower() in self._STD_HEADER_NAMES for f in direct):
                continue
            for _root, _d, files in _os.walk(sub):
                if any(f.endswith((".h", ".hpp", ".hh", ".hxx")) for f in files):
                    dirs.append("include/" + name)
                    break
        return dirs

