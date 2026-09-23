#!/usr/bin/env python3
"""Conan recipe — libmatheval 1.1.11 (GNU autotools; shared/static C library).

C library for parsing and evaluating symbolic mathematical expressions
(function of one or more variables) and their derivatives. GNU libmatheval
1.1.11 ships a generated `configure` + libtool (ltmain.sh bundled), so no
autoreconf/automake/libtool tool_requires are needed.

OHOS 适配要点（详见 knowledge/drafts/DRAFT-libmatheval-1.1.11-*.kv）：
  1. 显式 --build/--host=<aarch64>-unknown-linux-gnu：设备 HMFS 上老 config.guess
     的 mktemp 探针会写 dummy.c 报 Permission denied（"unable to guess system
     type"），而本包自带的 2013 config.sub **不认 -musl 拼写**（只认 linux-gnu），
     故用 linux-gnu 拼写；build==host → 原生模式，conftest 可直接运行。
  2. configure.in 无条件调用 GUILE_FLAGS→GUILE_PROGS，其中 guile / guile-config
     任一缺失都是**致命错**（"guile required but not found" / "guile-config
     required but not found"，2026-09-08 CI #42525 实测死在 guile 上），即便
     guile 对核心库纯属可选（仅 tests/matheval.c 引用 libguile.h）。
     配方在 build 阶段给 guile/guile-config/guile-tools 各写一个"空探针 stub"
     （compile/link 都只 exit 0、无输出），经 GUILE/GUILE_CONFIG/GUILE_TOOLS
     环境变量预置成绝对路径给 configure，绕开 PATH 搜索。
  3. 上游 `make check` 依赖的测试驱动 tests/matheval.c **无条件 #include
     <libguile.h>** 且调用 guile 1.8/2.0 时代 API（scm_sizet/scm_makfrom0str…），
     guile 2.2（本仓已适配版本）已移除 → autotest 套件无法编译运行。故构建只进
     lib 子目录（make SUBDIRS=lib），并在 test_package 里用 C API 逐条复现
     upstream tests/*.at 的数值 oracle（同表达式、同期望值），作为 L1 门禁。
  4. flex 生成的 scanner.c 引用 yywrap，而 OHOS 无 libfl（AC_PROG_LEX 判
     "none needed"）→ .so 带未定义 yywrap，lld --no-allow-shlib-undefined 下
     消费者链接失败。source() 里往 xmath.c 追加恒真 yywrap()，库自包含。
  5. package() 的 make install 必须走 conan Autotools 运行器，裸 subprocess.run
     在 HMFS package() 阶段 getcwd 会崩（详见下方 build/package 注释）。
  6. lib/node.c 的 node_get_length() 数 number 节点的 %g 字符数靠写 tmpfile()
     探测；设备 libc 的 tmpfile() 要可写 P_tmpdir（/tmp），HMFS 没有 → 返回
     NULL → count=0，纯数字树 get_string 全空（2026-09-09 CI #42548 test_package
     实测 d(x+2)/dx 期望 "1" 得 ""）。source() 里改为 snprintf 到栈上 buffer 数
     字符，语义等价、不再依赖临时文件。
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
import os
import glob

required_conan_version = ">=2.0"


class LibmathevalConan(ConanFile):
    name = "libmatheval"
    version = "1.1.11"
    package_type = "library"

    description = (
        "GNU library to parse and evaluate symbolic expressions and their "
        "derivatives: strings of one or more variables, operators and "
        "elementary/transcendental functions."
    )
    homepage = "https://www.gnu.org/software/libmatheval/"
    license = "GPL-3.0-or-later"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("math", "expression", "parser", "derivative", "autotools", "c")

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # flex 生成的 scanner.c 引用 yywrap，而 OHOS 上 configure 的 AC_PROG_LEX 判定
        # "none needed"（无 libfl.a，LEXLIB 空）→ libmatheval.so 留下未定义 yywrap；
        # lld 默认 --no-allow-shlib-undefined，任何消费者链接都报
        # `undefined reference to yywrap`（2026-09-09 test_package 实测）。给库本体
        # 补一个恒真（返回 1 = 无更多输入）的 yywrap 定义，做到自包含。
        _xmath = os.path.join(self.source_folder, "lib", "xmath.c")
        if os.path.isfile(_xmath):
            with open(_xmath, "a", encoding="utf-8") as _f:
                _f.write(
                    "\n/* OHOS adaptation: flex scanner.c references yywrap but no libfl "
                    "exists; provide a self-contained always-true yywrap. */\n"
                    "int yywrap(void) { return 1; }\n"
                )

        # node_get_length() 数 number 节点的 %g 字符数靠 tmpfile() 探测；设备 libc
        # tmpfile() 需可写 P_tmpdir(/tmp)，HMFS 无 → 返回 NULL，count=0，纯数字树
        # get_string 全空（test_package 实测 d(x+2)/dx 期望 "1" 得 ""）。改 snprintf
        # 到栈上 buffer，语义等价（同 libc %g），不再依赖临时文件。
        _node = os.path.join(self.source_folder, "lib", "node.c")
        if os.path.isfile(_node):
            with open(_node, encoding="utf-8") as _f:
                _text = _f.read()
            _decl_old = (
                "\tFILE           *file;\t/* Temporary file. */\n"
                "\tint             count;\t/* Count of bytes written to above file. */\n"
                "\tint             length;\t/* Length of above string. */\n"
            )
            _decl_new = (
                "\tint             count;\t/* Count of bytes written to above file. */\n"
                "\tint             length;\t/* Length of above string. */\n"
                "\tchar            number_buf[64];\t/* OHOS: %g length staging. */\n"
            )
            _body_old = (
                "\t\tfile = tmpfile();\n"
                "\t\tif (file) {\n"
                "\t\t\tif ((count =\n"
                '\t\t\t     fprintf(file, "%g", node->data.number)) >= 0)\n'
                "\t\t\t\tlength += count;\n"
                "\t\t\tfclose(file);\n"
                "\t\t}\n"
            )
            _body_new = (
                "\t\t/* OHOS adaptation: upstream counted the %g characters of a number\n"
                "\t\t * node via tmpfile(); the device libc tmpfile() needs a writable\n"
                "\t\t * P_tmpdir (/tmp) which does not exist on HMFS, so it returns NULL\n"
                "\t\t * and pure-number get_string (e.g. d(x+2)/dx -> \"1\") came back\n"
                "\t\t * empty. Count into a stack buffer instead (same %g semantics). */\n"
                "\t\tif ((count = snprintf(number_buf, sizeof(number_buf),\n"
                '\t\t\t     "%g", node->data.number)) < 0)\n'
                "\t\t\tcount = 0;\n"
                "\t\tlength += count;\n"
            )
            if _decl_old in _text:
                _text = _text.replace(_decl_old, _decl_new)
            if _body_old in _text:
                _text = _text.replace(_body_old, _body_new)
            with open(_node, "w", encoding="utf-8") as _f:
                _f.write(_text)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 2013 config.guess 在 HMFS 上 mktemp 探针失败 + config.sub 不认 -musl：
        # 显式给 build/host（build==host → 原生模式，跳过 config.guess，纯 shell
        # 的 config.sub 只校验我们给的 linux-gnu 三元组，不落盘）。
        _arch = str(self.settings.arch)
        _triple = {
            "aarch64": "aarch64-unknown-linux-gnu",
            "armv8": "aarch64-unknown-linux-gnu",
            "x86_64": "x86_64-unknown-linux-gnu",
            "x86": "i686-unknown-linux-gnu",
        }.get(_arch)
        if _triple:
            tc.configure_args.append("--build={}".format(_triple))
            tc.configure_args.append("--host={}".format(_triple))
        # 安装目标直接就是 conan package 目录（make install 无 DESTDIR）。
        tc.configure_args.append("--prefix={}".format(self.package_folder))
        # shared/static 二选一：与 option 对齐。
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # (0) 设备默认 TMPDIR(HMDFS /storage…) 上临时文件权限受限；指到可写可执行
        #     的 build 目录（libtool/m4 conftest 兜底）。
        _tmp = os.path.join(self.build_folder, "_tmp")
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp

        # (1) guile 空探针 stub：configure 无 --without-guile。configure.in 的
        #     GUILE_PROGS（GUILE_FLAGS 强制 require）会先 AC_PATH_PROG guile，
        #     找不到即 as_fn_error "guile required but not found"（2026-09-08 CI
        #     #42525 实测：只 stub 了 guile-config/guile-tools，漏了 guile 本身，
        #     configure 死在 "checking for guile... no"）。给三个工具都写一个
        #     compile/link 只 exit 0、无输出的脚本，经 GUILE/GUILE_CONFIG/
        #     GUILE_TOOLS 环境变量预置成绝对路径 → AC_PATH_PROG 走 user-override
        #     分支直接接受，GUILE_CFLAGS/GUILE_LDFLAGS 置空且不触发 PATH 搜索。
        #     上游仅 tests/matheval.c 引用 libguile.h，lib/（本次构建的核心库）
        #     完全不碰 guile，空 stub 安全。
        probe_dir = os.path.join(self.build_folder, "_probe")
        os.makedirs(probe_dir, exist_ok=True)
        for tool in ("guile", "guile-config", "guile-tools"):
            probe = os.path.join(probe_dir, tool)
            with open(probe, "w", encoding="utf-8") as f:
                f.write("#!/bin/sh\n# empty probe stub (libmatheval OHOS)\nexit 0\n")
            os.chmod(probe, 0o755)
            os.environ[tool.upper().replace("-", "_")] = probe

        # (2) libtool 生成的 configure 会以 umask 077 建归档目录（HMFS 上装完不可读/
        #     拷贝失败的老问题），按仓内惯例改为 022。对 source/build 两侧都做
        #     （幂等 replace），configure 运行前兜底。
        _roots = {self.source_folder, self.build_folder}
        for _root in _roots:
            for _cfg in glob.glob(os.path.join(_root, "**", "configure"), recursive=True):
                try:
                    with open(_cfg, encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                except OSError:
                    continue
                if "umask 077" in text:
                    with open(_cfg, "w", encoding="utf-8") as f:
                        f.write(text.replace("umask 077", "umask 022"))

        # (3) parser.c/parser.h/scanner.c 为 tarball 自带生成物；touch 保证其比
        #     parser.y/scanner.l 新，make 不会去调 flex/bison（设备上没有）。
        for _name in ("parser.c", "parser.h", "scanner.c"):
            for _root in _roots:
                _p = os.path.join(_root, "lib", _name)
                if os.path.isfile(_p):
                    os.utime(_p, None)

        autotools = Autotools(self)
        autotools.configure()

        # 只构建 lib 子目录：tests/ 的 matheval 驱动需 libguile.h（guile 2.2 无
        # 该 API），doc/ 需 makeinfo；都用 automake SUBDIRS 变量覆盖跳过。
        autotools.make(args=["SUBDIRS=lib", "-j1"])

    def package(self):
        # make install 直接写入 configure 时指定的 --prefix（= package_folder），
        # libtool 生成正确的 soname 符号链接链（libmatheval.so / .so.1 / .so.1.0.0）。
        # SUBDIRS=lib 只装库与头；libmatheval.pc 是顶层 pkgconfig_DATA，单独装。
        # 注意：必须走 conan 的 Autotools 运行器（autotools.make），不能用裸
        # subprocess.run(make,...)——2026-09-08 CI #42529 实测，package() 阶段裸
        # subprocess 起的 make 里每个 libtool --mode=install 的 bash 子进程都会
        # getcwd 失败（shell-init: error retrieving current directory），../libtool
        # 从 / 解析成 /libtool → Error 127。conan 运行器在 package() 阶段 cwd 正常
        # （libksba 同栈 CI 已过）。
        _tmp = os.path.join(self.build_folder, "_tmp")
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp
        autotools = Autotools(self)
        autotools.make(target="install", args=["SUBDIRS=lib", "-j1"])
        autotools.make(target="install-pkgconfigDATA")

    def package_info(self):
        self.cpp_info.libs = ["matheval"]
        self.cpp_info.set_property("cmake_file_name", "libmatheval")
        self.cpp_info.set_property("cmake_target_name", "libmatheval::libmatheval")
        self.cpp_info.set_property("pkg_config_name", "libmatheval")
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = ["include"]
