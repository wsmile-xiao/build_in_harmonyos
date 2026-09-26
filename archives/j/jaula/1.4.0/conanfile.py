#!/usr/bin/env python3
"""Conan recipe for jaula 1.4.0 - JAULA (JSON Analysis User Library Acronym).

A 2009-vintage C++ JSON lexer/parser (autoconf 2.61 + automake 1.10.1 +
bundled libtool 2.2.4). Built natively on HarmonyOS PC (clang 15, aarch64).

Key adaptation decisions (device-verified, see notes.md):
- the bundled config.sub (2008-01-16) rejects *-linux-ohos, so only
  --build=<gnu triple> is passed and --host is deliberately omitted;
- flex is reached as a host dependency for its *header only* (the installed
  public header jaula/jaula_lexan.h includes FlexLexer.h); it is NOT needed at
  link time - nm shows libjaula.a defines the jaulaFlexLexer methods itself
  (35 T / 0 U) and libfl.a holds none - and it is also a build tool, since the
  scanner is generated from .ll at build time;
- 0001-configure.patch relaxes two `umask 077` sites that make
  config.status unable to write its temp dir on HMDFS (E011/E114);
- compiler.cppstd is dropped because the public headers still use dynamic
  exception specifications (removed in C++17);
- only the library subdirectory is built/installed; examples/ and doc/ are
  left out on purpose (see build()/package() comments).
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class JaulaConan(ConanFile):
    name = "jaula"
    version = "1.4.0"
    description = ("JAULA - JSON Analysis User Library Acronym: a C++ JSON "
                   "lexical analyzer and parser built with flex/libtool")
    license = "LGPL-2.1-or-later"
    homepage = "https://sourceforge.net/projects/jaula"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def layout(self):
        basic_layout(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC
        # 本包 9 个公开头共 13 处使用**动态异常规范**（throw(Exception) /
        # throw(Bad_Data_Type) / throw(Name_Duplicated)），该语法在 C++17 已被移除。
        # 设备的 ohos-aarch64 profile 写死 compiler.cppstd=17，真机实测首错：
        #   jaula_value.h:110:45: error: ISO C++17 does not allow dynamic
        #   exception specifications [-Wdynamic-exception-spec]
        # 沿用 §12.53 家族既有修法：撤掉 cppstd 让 clang 15 回落到默认 gnu++14，
        # 比逐处删 13 行 throw(...) 更干净（后者会改动公开 API 声明面）。
        # 代价与边界记进 notes.md：消费者若强制 -std>=17 仍会失败，故 test_package
        # 的 CMakeLists 显式钉 CXX_STANDARD 11。
        self.settings.rm_safe("compiler.cppstd")

    def requirements(self):
        # 宿主依赖而非纯构建工具：公开头 jaula/jaula_lexan.h:65 直接
        # #include <FlexLexer.h>，且它经 jaula.h -> jaula_parse.h -> jaula_lexan.h
        # 传染到每一个消费者 ⇒ 消费者必须能取到 flex 的头，故建为宿主 requires。
        # 注意：**链接期并不需要 libfl**——真机 nm 实测 libjaula.a 的 40 条
        # FlexLexer 符号是 35 已定义(T)/0 未定义(U)（flex 随 %option c++ +
        # %option prefix="jaula" 把 jaulaFlexLexer 基类实现直接生成进本包目标码），
        # 而 libfl.a 内 FlexLexer 符号数为 0；configure 当时也报了
        # "checking lex library... none needed"，三处互证。
        self.requires("flex/2.6.4")

    def build_requirements(self):
        # jaula/Makefile.am 把 jaula_lexan.ll 声明为 nodist_*_SOURCES，扫描器 C++
        # 源码须由 flex 现场生成；configure.in 对 LEX != flex 与缺 FlexLexer.h 都是
        # AC_MSG_ERROR 硬失败，所以需要 build context 的 flex 可执行文件（PATH）。
        self.tool_requires("flex/2.6.4")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsToolchain 只负责按 settings 产出编译器与 *-FLAGS，
        # 不会把宿主依赖的 include/lib 注入 CPPFLAGS/LDFLAGS；jaula 的公开头
        # 公开头闭包依赖 flex 的 FlexLexer.h（链接期不需 -lfl，见 requirements() 注释），所以必须同时生成
        # AutotoolsDeps（其 conanautotoolsdeps.sh 由 conanbuild.sh 汇总），
        # 并在 build() 里用 env="conanbuild" 执行 configure。
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.generate()

    def _cc(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return compilers.get("c", "clang")

    def _cxx(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return compilers.get("cpp", "clang++")

    def build(self):
        apply_conandata_patches(self)
        # E544/E122：本包自带 config.sub 为 2008-01-16 版（case 风格），kernel-os 段
        # 不认 linux-ohos——本机直跑 `sh config.sub aarch64-unknown-linux-ohos` 逐字
        # 复现 "Invalid configuration ... machine `aarch64-unknown-linux' not
        # recognized"，而 aarch64-unknown-linux-gnu 原样回显。故只显式传 --build 的
        # gnu 三元组、不传 --host（OHOS 设备原生构建时 host 缺省等于 build），
        # 绕开 config.sub 对 host 的 OS 后缀校验，免 E007 源码补丁。
        # E386：CONFIG_SHELL/SHELL 就地钉 /bin/sh，避开 profile 指定的 hnp bash 在
        # HMDFS 构建目录 getcwd() 失败。
        # env="conanbuild"：让 AutotoolsToolchain 汇总的宿主依赖 flags（flex 的
        # -I<flex>/include 与 -L<flex>/lib）进入 configure 与 make，
        # AC_CHECK_HEADERS(FlexLexer.h) 才有机会通过。
        configure = os.path.join(self.source_folder, "configure")
        link_args = ("--enable-static --disable-shared" if not self.options.shared
                     else "--enable-shared --disable-static")
        self.run(
            'cd "{}" && CONFIG_SHELL=/bin/sh SHELL=/bin/sh /bin/sh "{}" '
            '--prefix="{}" --build=aarch64-unknown-linux-gnu '
            "CC={} CXX={} --disable-doc-gen {}".format(
                self.build_folder, configure, self.package_folder,
                self._cc(), self._cxx(), link_args,
            ),
            env="conanbuild",
        )
        autotools = Autotools(self)
        # 只构建库本体：顶层 SUBDIRS 由 configure.in 硬编码为 "doc jaula examples"。
        # examples/ 是演示程序（jparse.cc 使用 C++17 已移除的 std::auto_ptr，lextst
        # 又写死 -static），doc/ 在无 doxygen 时是空转目标；库与头文件的构建都不依赖
        # 这两个目录，故收敛到 jaula/ 子目录单独构建。
        #
        # AM_CXXFLAGS 这一命令行覆盖是为解 VPATH 下的自引用头：本包公开头一律写
        # #include <jaula/xxx.h>，只有"含 jaula/ 子目录的那一层"作 -I 才可解析；
        # automake 1.10 生成的 DEFAULT_INCLUDES 只有 "-I. -I$(srcdir) -I$(top_builddir)"
        # （in-tree 构建时 top_builddir 恰为 .. 才可蒙对），conan 的 VPATH 构建里
        # top_builddir 指向构建树，设备实测首错
        #   jaula_bad_data_type.h:32:10: fatal error: 'jaula/jaula_exception.h' file not found
        # 走 make 命令行变量（优先级高于 Makefile 内赋值）注入 -I<源码根>，
        # 既不改上游 Makefile.am，也不覆盖 CPPFLAGS 里来自 flex 的 -I。
        autotools.make(args=["-C", "jaula", "-j1",
                             "AM_CXXFLAGS=-I{}".format(self.source_folder)])

    def package(self):
        # 按产物实体拷贝、不跑 make install：顶层 doc/Makefile.in:551 起的
        # install-data-local 含 8 条无守卫的（第 552/553/559/560/561/567/568/569 行） `test -n "$(DOXYGEN)" && ...`，未启用
        # doxygen 时该短路式返回 1，会让整条 make install 链 Error 1；静态打包同时
        # 规避 libtool .so/.so.0/.so.0.0.0 三件套在 HMDFS 上的符号链接脆弱性。
        lib_dir = os.path.join(self.build_folder, "jaula", ".libs")
        if self.options.shared:
            copy(self, "libjaula.so*", src=lib_dir,
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        else:
            copy(self, "libjaula.a", src=lib_dir,
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        # 与上游 Makefile.am 一致：jaula.h 落 include/，其余 17 个落 include/jaula/
        # （公开头内部一律用 #include <jaula/xxx.h>，目录层级不可压平）。
        copy(self, "jaula.h", src=os.path.join(self.source_folder, "jaula"),
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "*.h", src=os.path.join(self.source_folder, "jaula"),
             dst=os.path.join(self.package_folder, "include", "jaula"),
             keep_path=False, excludes=["jaula.h"])
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["jaula"]
        # 本包的公开安装头把 flex 的 FlexLexer.h 写进了 include 闭包
        # （requirements() 注释里有 nm 与 configure 三处互证），因此只向消费者
        # 转递 flex 的**头目录**，不转递 libdirs/libs——链接期不需要 -lfl。
        # 设备实测：只声明 cpp_info.requires = ["flex::flex"] 时，CMakeDeps 生成的
        # jaula-release-armv8-data.cmake 里 jaula_INCLUDE_DIRS 只有本包 include/，
        # 消费者编译报 'FlexLexer.h' file not found（flex 同时占 build/host 两个
        # 上下文，跨上下文的 requires 传导不可靠）。故按依赖实体把 include 路径
        # 展开成绝对目录；注意 cpp_info.includedirs 取到的是**相对**依赖包目录的
        # 路径，必须用 package_folder 拼绝对，否则会按本包目录解析而静默指错。
        flex = self.dependencies["flex"]
        self.cpp_info.includedirs.extend(
            os.path.join(flex.package_folder, d)
            for d in flex.cpp_info.includedirs)
