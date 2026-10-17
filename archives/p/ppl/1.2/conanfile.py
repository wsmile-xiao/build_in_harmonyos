#!/usr/bin/env python3
"""Conan recipe — ppl 1.2 (autotools)"""
from conan import ConanFile
from conan.tools.files import get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.files import apply_conandata_patches
from conan.tools.layout import basic_layout



class PplConan(ConanFile):
    name = "ppl"
    version = "1.2"
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
        # **必须是带 C++ 接口（gmpxx）的那一版**：PPL 的系数类型就是 mpz_class，
        # configure 的 GMP 检查直接 `#include <gmpxx.h>` 并链 `-lgmpxx`。
        # 制品仓里 gmp/6.3.0 那个二进制是**静态且不含 gmpxx**（只有 libgmp.a + gmp.h），
        # 用它 configure 报的是 `Cannot find GMP version 4.1.3 or higher` ——
        # 措辞像版本太老，实际是 gmpxx.h 根本不存在（config.log 里才看得到真话）。
        # 6.3.0.1 的二进制是 shared 且带 libgmpxx.so.4 + gmpxx.h。
        self.requires("gmp/6.3.0.1")
        # glpk 只被 ppl_lpsol 这个 demo 用到，库本身不需要；引它进来只会多一处版本冲突面。

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        # PPL 1.2 用了 `std::auto_ptr`，C++17 把它**删了**（不是弃用，是移除）：
        #   error: no member named 'auto_ptr' in namespace 'std'
        # profile 定的是 c++17，不去动它；libc++ 提供了开关把被移除的老设施放回来。
        # 两个宏都给：新 libc++ 用聚合的那个，老一点的用单项那个。
        tc.extra_defines.append("_LIBCPP_ENABLE_CXX17_REMOVED_AUTO_PTR")
        tc.extra_defines.append("_LIBCPP_ENABLE_CXX17_REMOVED_FEATURES")
        tc.configure_args.append("--enable-coefficients=mpz")
        tc.configure_args.append("--disable-fpmath")
        tc.configure_args.append("--enable-interfaces=c,c++")
        tc.configure_args.append("--with-gmp={}".format(self.dependencies["gmp"].package_folder))
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
        # PPL 的 GMP 检查是 **AC_RUN_IFELSE**（编译并**运行**一个 C++ 程序，比对
        # gmpxx.h 与 libgmpxx 的版本/limb 位数）。链接过了不算数 —— 跑起来还得
        # 加载到 libgmpxx.so/libgmp.so，否则 configure 只报一句
        #   checking for the GMP library version 4.1.3 or above... no
        #   configure: error: Cannot find GMP version 4.1.3 or higher.
        # 措辞像「找不到 GMP」，真因是**运行期**找不到（编译期是找到了的）。
        # 两手都要：LD_LIBRARY_PATH 给 conftest 跑起来用，-rpath 给最终产物用。
        _libdirs = [_d for _ref, _dep in self.dependencies.items()
                    for _d in (_dep.cpp_info.libdirs or []) if _os.path.isabs(_d)]
        if _libdirs:
            _env.define("LD_LIBRARY_PATH", ":".join(_libdirs))
            _env.prepend("LDFLAGS", " ".join("-Wl,-rpath,%s" % _d for _d in _libdirs))
        tc.generate(_env)

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
        self.cpp_info.libs = ['ppl', 'ppl_c']
        self.cpp_info.set_property("cmake_file_name", "ppl")
        self.cpp_info.set_property("cmake_target_name", "ppl::ppl")
        self.cpp_info.set_property("pkg_config_name", "ppl")



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

