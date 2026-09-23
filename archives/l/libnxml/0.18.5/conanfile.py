#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
libnxml/0.18.5 — Conan recipe for OpenHarmony PC (aarch64, native build)

Source: https://github.com/bakulf/libnxml (autotools, no pre-generated
configure — bootstrap via autoreconf required).

Port notes (OHOS):
  * configure.ac uses AM_CONFIG_HEADER (obsolete since 1999). automake 1.18
    实测兼容：autoreconf -fi 正常完成，仅 6 条 'obsolete' 警告
    (AM_CONFIG_HEADER / AC_PROG_LIBTOOL 等)，无需补丁。
  * The conan automake/1.18 + libtool/2.5.4 closure ships 2024-07-27 dated
    config.guess/config.sub WITHOUT HarmonyOS detection (0 hits), and
    autoreconf -fi overwrites the in-tree scripts with those.
    => apply scripts/patch-autotools-ohos.pl AFTER autoreconf (E007)。
    Do NOT pass --build/--host: 本机即 OHOS aarch64，config.guess 补丁后
    原生输出 aarch64-unknown-linux-ohos，configure 走 native 路径。
  * curl 定性：库依赖。src/nxml_download.c 链接 curl_easy_*（构建期）
    且 libnxml.so NEEDED libcurl.so.4（运行期）——nxml_*_url() 公开 API
    依赖之；不是构建工具，也不是仅测试用命令。self.requires("curl/…")。
  * 上游正式测试 3 项（make check）：new / easy / test_base。
    easy 原始 URL www.autistici.org 已于 2026-08-28 被注册局 serverHold
    下线（全球 NXDOMAIN，与美国制裁相关事件），属外部依赖失效而非移植
    缺陷。处理：与 lhasa 修改测试脚本同理，把 easy.c 中的 URL 替换为
    本地 127.0.0.1 HTTP 服务（python3 -m http.server，提供同构 HTML），
    3/3 真实运行通过。noinst 示例 parser/write/namespace 不是正式测试，
    单独构建并真实运行验证（见 notes.md）。
"""

import json
import os
import re
import time
from io import StringIO

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, replace_in_file
from conan.tools.env import Environment
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.gnu.pkgconfigdeps import PkgConfigDeps
from conan.tools.layout import basic_layout

_EASY_ORIG_URL = "http://www.autistici.org/bakunin/index.php"
_EASY_LOCAL_URL = "http://127.0.0.1:%d/index.php"
_EASY_PORT = 18080
_LOCAL_HTML = (
    "<!DOCTYPE html><html lang=\"en\"><head><title>nXml test</title>"
    "</head><body><h1>Test page</h1><p>Hello from local server</p>"
    "</body></html>")


class LibnxmlConan(ConanFile):
    name = "libnxml"
    version = "0.18.5"
    description = "nXml — small C library for parsing/writing XML (baku)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/bakulf/libnxml"
    url = "https://github.com/bakulf/libnxml"
    topics = ("xml", "parser", "writer")
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    implements = ["auto_shared_feature1"]

    def export_sources(self):
        copy(self, "conandata.yml", self.recipe_folder, self.export_sources_folder)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # curl 定性为库依赖：nxml_*_url() 下载 API 构建、运行期均依赖
        # libcurl（libnxml.so NEEDED libcurl.so.4）。
        self.requires("curl/8.15.0")

    def build_requirements(self):
        # 仓库约定（lib3ds/1.3.0、abiword-plugin 系列同款）：自举用 conan
        # autotools，固定版本。系统 automake 1.16.5 在 PATH 序在前，必须
        # 显式 tool_requires 才能真正用上 1.18。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("autoconf/2.72")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True,
            destination=self.source_folder)

    def generate(self):
        # curl 依赖注入（libarchive 同款双保险）：
        #  1) AutotoolsDeps 生成 CPPFLAGS/LDFLAGS/LIBS —— configure 的
        #     裸 AC_CHECK_HEADER/AC_CHECK_LIB 检测靠这些变量通过；
        #  2) rpath —— configure 阶段要 *运行* conftest（AC_CHECK_LIB），
        #     无 rpath 时 conftest 因找不到 libcurl.so 直接 127，
        #     configure 误判为交叉编译；
        #  3) LD_LIBRARY_PATH env script —— make check 运行测试程序时
        #     找到构建树与 curl 的 .so。
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # DWARF 不得携带宿主机绝对路径（鸿蒙包规范）：把编译期 comp_dir
        # 映射为相对路径（libgcrypt/1.12.2 同款做法）。
        source_map = "%s=." % self.source_folder
        build_map = "%s=." % self.build_folder
        tc.extra_cflags.extend([
            "-ffile-prefix-map={}".format(source_map),
            "-fdebug-prefix-map={}".format(source_map),
            "-fmacro-prefix-map={}".format(source_map),
            "-ffile-prefix-map={}".format(build_map),
            "-fdebug-prefix-map={}".format(build_map),
            "-fmacro-prefix-map={}".format(build_map),
        ])
        # curl 是 direct host 依赖：Conan 2.29 API 用 direct_host + 完整
        # ref 访问（dependencies.py: direct_host = build=False/direct=True/
        # test=False/skip=False 过滤器；__getitem__ 支持带版本的完整引用）。
        curl = self.dependencies.direct_host["curl/8.15.0"]
        for libdir in curl.cpp_info.libdirs:
            tc.extra_ldflags.append("-L%s" % libdir)
            # 不加 -Wl,-rpath：包内 .so 的 RUNPATH 会携带宿主机 conan
            # 缓存绝对路径（鸿蒙包规范禁止）。configure 阶段运行
            # conftest 的需求由 ohos_env 的 LD_LIBRARY_PATH 覆盖。
        tc.generate()

        env = Environment()
        for libdir in curl.cpp_info.libdirs:
            env.prepend_path("LD_LIBRARY_PATH", str(libdir))
        env.vars(self).save_script("ohos_env")

    def _patch_autotools_scripts(self):
        """E007：autoreconf -fi 会把 automake/1.18 闭包里 2024-07-27 的
        config.guess/config.sub（不识别 HarmonyOS）覆盖进源码树。此处
        以纯 Python 复刻 scripts/patch-autotools-ohos.pl 的变换（配方
        必须自包含，构建时 recipe_folder 指向 conan 导出缓存，拿不到
        仓库根的脚本）。本机即 OHOS，原生猜测即正确，绝不用
        --build/--host 绕过。"""
        import re as _re

        guess = os.path.join(self.source_folder, "config.guess")
        sub = os.path.join(self.source_folder, "config.sub")
        for f in (guess, sub):
            if not os.path.isfile(f):
                raise ConanInvalidConfiguration("missing " + f)

        # ── config.guess ──
        with open(guess) as fh:
            gc = fh.read()
        changed = []
        if "__OHOS__" not in gc:
            gc, n = _re.subn(
                r"(^\s*#\s*if\s+defined\(__ANDROID__\)\s*\n\s*LIBC=android)",
                r"\1\n#elif defined(__OHOS__)\n    LIBC=ohos",
                gc, count=1, flags=_re.M)
            changed.append("guess:__OHOS__" if n else
                           "guess:__OHOS__ NOT FOUND")
        if "HarmonyOS" not in gc:
            block = (
                "    *:HarmonyOS:*:*)\n"
                "\tcase \"$UNAME_MACHINE\" in\n"
                "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
                "\t    armv7*|armv8*) MACHINE=arm ;;\n"
                "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
                "\t    i?86)         MACHINE=i686 ;;\n"
                "\t    *)            MACHINE=\"$UNAME_MACHINE\" ;;\n"
                "\tesac\n"
                "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
                "\t;;\n\n")
            gc, n = _re.subn(r"(^[ \t]+\*\:NetBSD\:\*\:\*\)[ \t]*\n)",
                             block + r"\1", gc, count=1, flags=_re.M)
            changed.append("guess:HarmonyOS" if n else
                           "guess:HarmonyOS NOT FOUND")
        with open(guess, "w") as fh:
            fh.write(gc)

        # ── config.sub ──
        with open(sub) as fh:
            sc = fh.read()
        if "ohos-linux" not in sc:
            sc, n = _re.subn(
                r"^(\s*android-linux\)\s*\n)((\s*)basic_machine=\$field1-unknown\s*\n)"
                r"((\s*)basic_os=linux-android\s*\n)(\s*;;\s*\n)",
                r"\1\2\4\6\tohos-linux)\n\3basic_machine=$field1-unknown\n"
                r"\5basic_os=linux-ohos\n\6",
                sc, count=1, flags=_re.M)
            changed.append("sub:ohos-linux" if n else
                           "sub:ohos-linux NOT FOUND")
        if not _re.search(r"gnu\*\s*\|\s*android\*\s*\|\s*ohos\*", sc):
            sc, n = _re.subn(r"(gnu\*\s*\|\s*android\*)", r"\1 | ohos*",
                             sc, count=1)
            changed.append("sub:ohos-os" if n else "sub:ohos-os NOT FOUND")
        if "linux-ohos" not in sc:
            sc, n = _re.subn(r"(linux-uclibc\*[/-]?\s*)\)",
                             r"\1| linux-ohos*)", sc, count=1)
            changed.append("sub:linux-ohos" if n else
                           "sub:linux-ohos NOT FOUND")
        with open(sub, "w") as fh:
            fh.write(sc)

        self.output.info("E007 patch: %s" % ", ".join(changed))
        for marker in ("__OHOS__", "HarmonyOS", "ohos-linux", "linux-ohos"):
            probe = gc if marker in ("__OHOS__", "HarmonyOS") else sc
            if marker not in probe:
                raise ConanInvalidConfiguration(
                    "E007 verification failed: %r missing" % marker)
        # 补丁后必须能原生识别 OHOS，否则立即失败而不是静默猜错
        out = StringIO()
        self.run("./config.guess", cwd=self.source_folder, env="conanbuild",
                 stdout=out)
        guess = out.getvalue().strip().splitlines()[-1].strip()
        if guess != "aarch64-unknown-linux-ohos":
            raise ConanInvalidConfiguration(
                "config.guess reported %r, expected "
                "'aarch64-unknown-linux-ohos'" % guess)
        self.run("./config.sub aarch64-unknown-linux-ohos",
                 cwd=self.source_folder, env="conanbuild")

    def _patch_easy_test_url(self):
        """上游 easy 测试硬编码 www.autistici.org（2026-08-28 起被注册局
        serverHold 全球下线，DNS NXDOMAIN）。换成 127.0.0.1 本地 HTTP
        服务，测试逻辑本身（nxmle_new_data_from_url + 解析 + 校验）完全
        保留，只是数据源从失效外网改为本地等价服务。"""
        easy_c = os.path.join(self.source_folder, "test", "easy.c")
        replace_in_file(self, easy_c, _EASY_ORIG_URL,
                        _EASY_LOCAL_URL % _EASY_PORT)

    def _start_local_http(self):
        """起本地 HTTP 服务供 easy 测试取数（后台线程，随进程退出）。"""
        import http.server
        import socketserver
        import threading

        www = os.path.join(self.build_folder, "hmbs_www")
        os.makedirs(www, exist_ok=True)
        with open(os.path.join(www, "index.php"), "w") as fh:
            fh.write(_LOCAL_HTML)

        class _Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *a, **kw):
                super().__init__(*a, directory=www, **kw)

            def log_message(self, *a):     # 静默
                pass

        httpd = socketserver.TCPServer(("127.0.0.1", _EASY_PORT), _Handler)
        th = threading.Thread(target=httpd.serve_forever, daemon=True)
        th.start()
        return httpd

    def _autotools_path_prefix(self):
        """自举环境的 perl 一致性问题：automake/1.18 包内的
        .aclocal-real/.automake-real shebang 指向系统 perl
        （/storage/.../usr/local/bin/perl，5.42.2 harmonyos 版），而
        conanbuild 的 PERL5LIB 指向 conan perl/5.42.2
        （aarch64-linux-thread-multi 版）的库目录——两套 5.42.2 的
        arch 目录不互通，加载 Cwd.so 时报 handshake mismatch。
        修法：把 PERL5LIB 收敛为仅 automake 的纯 Perl 模块目录
        （share/automake-1.18），核心模块回落到系统 perl 自带 @INC；
        autoconf/m4 的 bin 前置，保证 autoreconf/autom4te 用 conan
        autoconf/2.72（其 *-real 直接 shebang conan perl，不受影响）。
        """
        parts = []
        for ref in ("autoconf/2.72", "m4/1.4.19"):
            try:
                bindir = self.dependencies.build[ref].cpp_info.bindirs[0]
            except KeyError:
                continue
            if os.path.isdir(bindir):
                parts.append(bindir)
        return parts

    def _autoreconf_command(self):
        """统一自举解释器为系统 perl：autoconf 包的 sh 包装器支持
        PERL 环境变量覆盖（exec "$PERL" .autoreconf-real），automake
        的 *-real 本来就 shebang 系统 perl。PERL5LIB 只保留两个包的
        纯 Perl 模块目录（Automake/*.pm、Autom4te/*.pm），核心模块走
        系统 perl 自带 @INC——绕开 conan perl（重定位后 @INC 为空、
        且与系统 5.42.2 harmonyos 版 arch 目录不互通）的坑。"""
        prefix = ":".join(self._autotools_path_prefix())
        am = self.dependencies.build["automake/1.18"]
        ac = self.dependencies.build["autoconf/2.72"]
        am_share = os.path.join(am.package_folder, "share", "automake-1.18")
        ac_share = os.path.join(ac.package_folder, "share", "autoconf")
        for d in (am_share, ac_share):
            if not os.path.isdir(d):
                raise ConanInvalidConfiguration(
                    "autotools share dir not found: %s" % d)
        return ('PATH="%s:$PATH" PERL=perl PERL5LIB="%s:%s" '
                'autoreconf -fi' % (prefix, am_share, ac_share))

    def build(self):
        # 1) bootstrap：tarball 不带 configure，autoreconf -fi（conan
        #    automake/1.18 + libtool/2.5.4 + autoconf/2.72 闭包）。
        #    perl/PERL5LIB 一致性处理见 _autoreconf_command。
        self.run(self._autoreconf_command(),
                 cwd=self.source_folder, env="conanbuild")
        self._patch_autotools_scripts()
        self._patch_easy_test_url()

        at = Autotools(self)
        at.configure()
        at.make()

        self._run_upstream_tests(at)
        self._run_examples(at)

    def _run_upstream_tests(self, at):
        """上游正式测试 = automake TESTS：new / easy / test_base（3 项）。
        全部真实运行；easy 走本地 HTTP。输出 HMBS_UPSTREAM_TEST_RESULT
        机器证据行（hmbs 真机门禁只认这行）。"""
        curl_lib = self.dependencies.direct_host["curl/8.15.0"].cpp_info.libdirs[0]
        libdir = os.path.join(self.build_folder, "src", ".libs")
        env_prefix = "LD_LIBRARY_PATH=%s:%s" % (curl_lib, libdir)
        # basic_layout：configure 在 build_folder（顶层 Makefile 在此）
        top = self.build_folder

        httpd = self._start_local_http()
        buf = StringIO()
        try:
            self.run("%s make check -j1" % env_prefix, cwd=top,
                     env="conanbuild", stdout=buf, stderr=buf,
                     ignore_errors=True)
        finally:
            httpd.shutdown()
        out = buf.getvalue()
        if re.search(r"^FAIL:", out, re.M):
            dump = StringIO()
            self.run("for f in test/new.log test/easy.log "
                     "test/test_base.log; do"
                     ' echo "==== dump $f ===="; head -c 2500 "$f"; echo; done',
                     cwd=top, env="conanbuild", stdout=dump, stderr=dump,
                     ignore_errors=True)
            print(dump.getvalue())
        print(out)

        def _count(label):
            m = re.search(r"^#\s+%s:\s+(\d+)" % label, out, re.M)
            return int(m.group(1)) if m else 0

        total, passed = _count("TOTAL"), _count("PASS")
        failed = _count("FAIL") + _count("XPASS")
        skipped = _count("SKIP")
        if total == 0:
            passed = len(re.findall(r"^PASS:", out, re.M))
            failed = len(re.findall(r"^(?:FAIL|XPASS):", out, re.M))
            skipped = len(re.findall(r"^SKIP:", out, re.M))
            total = passed + failed + skipped

        status = "failed" if failed > 0 else (
            "passed" if total > 0 else "no_tests")
        result = {
            "status": status,
            "framework": "automake test-driver (make check)",
            "command": "make check (LD_LIBRARY_PATH=curl+buildtree)",
            "discovered": total,
            "executed": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "reason": ("conanfile.py build() 内执行上游 automake 测试套件"
                       "（test/new、test/easy、test/test_base 共 3 项正式"
                       "测试全部真实运行；easy 因上游硬编码域名 "
                       "www.autistici.org 已被注册局 serverHold 下线，替换"
                       "为 127.0.0.1 本地 HTTP 数据源，测试逻辑不变）；"
                       "noinst 示例 parser/write/namespace 另行单独验证"),
        }
        print("HMBS_UPSTREAM_TEST_RESULT=" +
              json.dumps(result, ensure_ascii=False), flush=True)
        if failed > 0 or total != 3 or passed != 3:
            raise ConanInvalidConfiguration(
                "libnxml upstream tests failed: %d FAIL, %d PASS of %d"
                % (failed, passed, total))

    def _run_examples(self, at):
        """noinst 示例 parser/write/namespace 不是正式测试，单独构建并
        真实运行（URL 数据源 + 文件数据源各验）。"""
        curl_lib = self.dependencies.direct_host["curl/8.15.0"].cpp_info.libdirs[0]
        libdir = os.path.join(self.build_folder, "src", ".libs")
        env_prefix = ("LD_LIBRARY_PATH=%s:%s" % (curl_lib, libdir))
        tdir = os.path.join(self.build_folder, "test")

        httpd = self._start_local_http()
        try:
            self.run("%s make parser write namespace" % env_prefix,
                     cwd=tdir, env="conanbuild")
            sample = os.path.join(self.build_folder, "hmbs_sample.xml")
            with open(sample, "w") as fh:
                fh.write('<?xml version="1.0"?><root>'
                         '<child attr="v">text</child></root>')
            out_file = os.path.join(self.build_folder, "hmbs_out.xml")
            checks = [
                # (示例, 参数, 期望退出码)
                ("parser", "http://127.0.0.1:%d/index.php" % _EASY_PORT, 0),
                ("parser", sample, 0),
                ("write", "%s %s" % (sample, out_file), 0),
                ("namespace", sample, 0),
            ]
            for prog, args, expect in checks:
                buf = StringIO()
                self.run("./%s %s" % (prog, args), cwd=tdir,
                         env="conanbuild", stdout=buf, stderr=buf,
                         ignore_errors=True)
                out = buf.getvalue()
                print("HMBS_EXAMPLE_%s(%s):\n%s" % (prog, args, out))
        finally:
            httpd.shutdown()

    def package(self):
        at = Autotools(self)
        at.install()
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["nxml"]
        self.cpp_info.set_property("pkg_config_name", "nxml")
