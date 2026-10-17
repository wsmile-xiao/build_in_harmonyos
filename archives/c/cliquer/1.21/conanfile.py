#!/usr/bin/env python3
"""Conan recipe — cliquer 1.21 (autotools)"""
from conan import ConanFile
from conan.tools.files import get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.files import apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout



class CliquerConan(ConanFile):
    name = "cliquer"
    version = "1.21"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # CI worker 镜像只有 autoconf 套件，缺 automake/aclocal 与 libtoolize；
        # autoreconf -fi 需要 三者齐全（abiword-plugin-docbook/3.0.8 先例）。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        tc.generate()

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
        autotools.install(args=["-j1"])
        # 【skill: 默认删 .la】libtool 的 .la 里烤死 libdir 绝对路径，
        # conan 包按 prefix=/ 构建 → 里面写的是 '/lib'，下游 libtool 会去找
        # `//lib/libxxx.la` 而失败（graphviz 实撞）。链接信息 .pc/cpp_info 已提供。
        import glob as _glob, os as _os
        for _la in _glob.glob(_os.path.join(self.package_folder, "lib", "*.la")):
            _os.remove(_la)
        self._sign_binaries()


    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 代码签名是**鸿蒙专有**动作，用的两个工具都在 OHOS 设备的 /data/service/hnp/bin 下。
        # 在别的 profile（如 os=Linux）上它们根本不存在：
        # objcopy 那步有 `|| true` 兜底，但 binary-sign-tool 那步没有——
        # self.run() 会失败，整个 conan create 在 package 阶段崩掉。
        # 守卫写在方法内而不是各调用点：4 个构建系统模板都会调它，
        # 写在这里只有一处、且以后新增调用点自动覆盖。
        # opencascade 7.9.3 MR 评审实撞。
        if self.settings.os != "OHOS":
            return
        # 鸿蒙 PC XPM 要求 dlopen 的 .so 和被 exec 的可执行文件都要代码签名，否则报 Permission denied /
        # Operation not permitted。签名是内容哈希（存 .codesign 节），**链接之后再改字节就失效**：
        # meson install 抹 RUNPATH（原地涂 X）、libtool relink、strip/objcopy/patchelf 都属此列。
        # 注意**复制不会破坏签名**（哈希随内容一起复制走，2026-08-04 真机对照实验实测）。
        # ① lib/ 的 .so  ② bin/ 的 ELF 可执行文件（llvm-config/xxx CLI 等）——产可执行文件的包必须签 bin。
        import glob, os
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):   # 只签真实 ELF，跳版本化 .so 的软链（否则对同一目标重复签）
                continue
            self.run('env -u LD_LIBRARY_PATH {oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('env -u LD_LIBRARY_PATH {sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.includedirs = self._detect_include_dirs()
        self.cpp_info.libs = ['cliquer']
        self.cpp_info.set_property("cmake_file_name", "cliquer")
        self.cpp_info.set_property("cmake_target_name", "cliquer::cliquer")
        self.cpp_info.set_property("pkg_config_name", "libcliquer")



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

