#!/usr/bin/env python3
"""Conan recipe — singular 4.4.1 (autotools)"""
import os
from conan import ConanFile
from conan.tools.files import get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.files import apply_conandata_patches
from conan.tools.layout import basic_layout
from conan.tools.gnu import AutotoolsDeps, PkgConfigDeps
from conan.tools.env import VirtualRunEnv



class SingularConan(ConanFile):
    name = "singular"
    version = "4.4.1"
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
        self.requires("ntl/11.6.0")
        self.requires("flint/3.2.2")
        self.requires("readline/8.3")
        # 必须用 4.2.2.1：4.2.2 装出的 libmpfr.la 里 dependency_libs 烤死了
        # //lib/libgmp.la（不存在），libtool 链 libsingular_resources.la 时报
        # "'//lib/libgmp.la' is not a valid libtool archive"。4.2.2.1 只是补删了 .la。
        self.requires("mpfr/4.2.2.1", force=True)
        self.requires("cddlib/0.94m")
        self.requires("gmp/6.3.0.1", force=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        # AutotoolsDeps 把依赖的 -l 全塞进链接行，于是 configure 的 conftest
        # **链上了这些依赖**；而 --build == --host 时 autoconf 判本机构建，
        # 要**运行** conftest。加载器找不到依赖 .so 就是 $? = 127，
        # configure 却报成「cannot run C compiled programs / 若要交叉编译请用 --host」——
        # 指向完全错误的方向（hwloc 2.14.0 实撞，config.log:145-152）。
        # 故必须把依赖 libdir 写进 build 期 LD_LIBRARY_PATH。
        VirtualRunEnv(self).generate(scope="build")
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        tc.configure_args.append("--disable-doc")
        tc.configure_args.append("--disable-polymake")
        tc.configure_args.append("--without-python")
        tc.configure_args.append("--disable-gfanlib")
        # Singular 用 AC_CONFIG_SUBDIRS 递归跑 omalloc/factory 等子 configure。
        # conan 只把 LDFLAGS 放进**环境变量**，而子 configure 拿到的链接命令里
        # 一个 -L 都没有（只剩 -lflint -lgmp … 全部 unable to find library），
        # 说明 LDFLAGS 没能传下去。写成 configure_args 才会进 ac_configure_args
        # 并原样转发给每个子 configure。
        _L = " ".join("-L{}".format(d) for dep in self.dependencies.values()
                      for d in dep.cpp_info.libdirs)
        tc.configure_args.append("LDFLAGS={}".format(_L))
        # omalloc 的 configure 里还有第二处编译器可用性检查（configure:20017），
        # 来自 AX_PROG_CC_FOR_BUILD 宏，它用的是 _FOR_BUILD 变量族：
        #   ac_link='$CC_FOR_BUILD -o conftest $CFLAGS_FOR_BUILD $CPPFLAGS_FOR_BUILD \
        #            $LDFLAGS_FOR_BUILD conftest.c $LIBS'
        # 注意最后是**普通的 $LIBS**（我们设过，一长串 -lflint -lgmp …），
        # 而 $LDFLAGS_FOR_BUILD 没人设 → 一个 -L 都没有，于是：
        #   ld.lld: error: unable to find library -lflint …（十几条）
        #   configure: error: C compiler cannot create executables
        # 这个报错极具误导性——看着像工具链坏了，其实只是缺搜索路径。
        # 本包是原生构建（build == host），把同一份 -L 给 _FOR_BUILD 即可。
        tc.configure_args.append("LDFLAGS_FOR_BUILD={}".format(_L))
        # 环境里可能已有 LDFLAGS（设备与 CI worker 的 ~/.zshrc 都导出了
        # -L$HOME/usr/local/lib）。conan 用的是 append，自己的 -L 会排在它**后面**；
        # 链接器按 -L 顺序取第一个命中的目录，于是 -lffi 命中系统的 libffi.so
        # （SONAME libffi.so.8）而不是 conan 包里的 libffi.a，conftest 运行期加载不到：
        #   Error loading shared library libffi.so.8: (needed by ./conftest)
        #   configure: error: cannot run C compiled programs.
        # 把 conan 的 libdir **前置**，让 recipe 不再受环境 LDFLAGS 影响
        # —— 这样本机与 CI 行为一致，不必靠调用方 unset。
        _env = tc.environment()
        _Lp = " ".join("-L{}".format(_d) for _ref, _dep in self.dependencies.items()
                       for _d in _dep.cpp_info.libdirs)
        if _Lp:
            _env.prepend("LDFLAGS", _Lp)
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
        import glob, os
        for _cfg in glob.glob(os.path.join(self.source_folder, '**', 'configure'), recursive=True):
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
        # Makefile.am 的 install-data-local 用 `tar -jx` 解 doc/doc.tbz2；
        # 鸿蒙的 tar 是 toybox 的，-j 要外部 bzip2 applet 而它没有：
        #   toybox: Unknown command toybox
        #   tar: had errors
        #   mv: bad .../singular.info: No such file or directory  → install 整体失败
        # 该 target 由 `if test -e $(srcdir)/doc/doc.tbz2` 保护，删掉这个
        # 文档压缩包即整段跳过。我们本来就 --disable-doc，不装文档无损失。
        _tbz = os.path.join(self.source_folder, "doc", "doc.tbz2")
        if os.path.isfile(_tbz):
            os.remove(_tbz)
        autotools.install(args=["-j1"])
        # 【skill: 默认删 .la】libtool 的 .la 里烤死 libdir 绝对路径，
        # conan 包按 prefix=/ 构建 → 里面写的是 '/lib'，下游 libtool 会去找
        # `//lib/libxxx.la` 而失败（graphviz 实撞）。链接信息 .pc/cpp_info 已提供。
        import glob as _glob, os as _os
        for _la in _glob.glob(_os.path.join(self.package_folder, "lib", "*.la")):
            _os.remove(_la)




    def package_info(self):
        self.cpp_info.includedirs = self._detect_include_dirs()
        self.cpp_info.libs = ['Singular', 'polys', 'singular_resources', 'factory', 'omalloc']
        self.cpp_info.set_property("cmake_file_name", "singular")
        self.cpp_info.set_property("cmake_target_name", "singular::singular")
        self.cpp_info.set_property("pkg_config_name", "Singular")



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
        import os
        base = os.path.join(self.package_folder, "include")
        dirs = ["include"]
        if not os.path.isdir(base):
            return dirs
        for name in sorted(os.listdir(base)):
            sub = os.path.join(base, name)
            if not os.path.isdir(sub):
                continue
            # 只看子目录**直接**装的头：同名遮蔽只发生在直接被搜索的那一层。
            try:
                direct = os.listdir(sub)
            except OSError:
                continue
            # **大小写不敏感比对**：鸿蒙设备的文件系统不区分大小写，
            # `#include <string.h>` 会命中 `Poco/String.h`。守卫原先是精确匹配，
            # POCO 的 CamelCase 头一个都没被认出来，include/Poco 照样进了搜索路径 ——
            # 于是 libc++ 的 cstring 包含到 Poco/String.h，编译当场崩（poco 1.15.3 实撞）。
            if any(f.lower() in self._STD_HEADER_NAMES for f in direct):
                continue
            for _root, _d, files in os.walk(sub):
                if any(f.endswith((".h", ".hpp", ".hh", ".hxx")) for f in files):
                    dirs.append("include/" + name)
                    break
        return dirs

