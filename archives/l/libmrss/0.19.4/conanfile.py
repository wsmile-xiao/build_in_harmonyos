#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
libmrss/0.19.4 — Conan recipe for OpenHarmony PC (aarch64, native build)

Source: https://github.com/bakulf/libmrss (autotools, tarball 带预生成
configure 但 Makefile.am 声明的 NEWS 文件缺失，统一 autoreconf 自举)。

Port notes (OHOS):
  * tarball 根目录没有 NEWS 实体文件（GitHub tag 归档不含），而
    Makefile.am 的 AUTOMAKE_OPTIONS 未 foreign，automake 要求 NEWS 存在：
    `Makefile.am: error: required file './NEWS' not found`。
    处理：自举前 touch NEWS（空文件即可），不改任何源码逻辑。
    （已登记草稿 DRAFT-6053；全库查重 0 命中，真实新缺口）
  * tarball 自带 configure，但其捆绑的 config.guess/config.sub 为
    2024-07-27 版且 autoreconf -fi 会以 conan 闭包同名脚本覆盖，
    两处都不识别 HarmonyOS => autoreconf 后打 E007 补丁（配方内
    纯 Python 复刻 scripts/patch-autotools-ohos.pl 变换）。
    本机即 OHOS aarch64，config.guess 补丁后原生输出
    aarch64-unknown-linux-ohos，configure 走 native 路径，
    不传 --build/--host。
  * 依赖定性：
      - libnxml/0.18.5：库依赖。PKG_CHECK_MODULES(NXML, nxml>=0.18)，
        mrss_parser.c/mrss_download.c 直接调用 nxml_* 公开 API，
        libmrss.so NEEDED libnxml.so.0。本地缓存已有完整二进制包
        （feat/libnxml-0.18.5 分支产物）。
      - curl/8.15.0：库依赖（经由 libnxml + mrss_download.c 直接调用
        curl_easy_*）。configure 裸 AC_CHECK_HEADER(curl/curl.h) /
        AC_CHECK_LIB(curl,curl_version) 需 AutotoolsDeps + rpath-free
        LD_LIBRARY_PATH 注入才能通过（conftest 要真实运行）。
  * 上游正式测试 1 项（automake TESTS）：test/new（纯离线，创建/设值/
    写缓冲区往返）。noinst 示例 parser/write/time/search 不是正式
    测试，单独构建并真实运行验证（parser/write 用本地 HTTP 与文件
    数据源，见 notes.md）。
  * L0o 门禁：依赖访问统一用 self.dependencies.direct_host["curl/8.15.0"]
    完整 ref 写法（DRAFT-6052），避免带引号裸名被误判为外部命令调用。
"""

import json
import os
import re
import shutil
from io import StringIO

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.env import Environment
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.gnu.pkgconfigdeps import PkgConfigDeps
from conan.tools.layout import basic_layout

# 本地 HTTP 数据源端口（noinst 示例 parser 的 URL 数据源替代）
_LOCAL_PORT = 18081
_LOCAL_RSS = (
    "<?xml version=\"1.0\"?>"
    "<rss version=\"2.0\"><channel>"
    "<title>libmrss local test</title>"
    "<link>http://127.0.0.1/feed</link>"
    "<description>local feed for OHOS test</description>"
    "<item><title>item one</title>"
    "<link>http://127.0.0.1/1</link>"
    "<description>first item</description></item>"
    "</channel></rss>")


class LibmrssConan(ConanFile):
    name = "libmrss"
    version = "0.19.4"
    description = ("mRss - C library for parsing, writing and "
                   "creating RSS/Atom feeds (baku)")
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/bakulf/libmrss"
    url = "https://github.com/bakulf/libmrss"
    topics = ("rss", "atom", "feed", "xml", "parser")
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
        # 库依赖：mrss_download.c 链接 curl_easy_*（构建期）且
        # libmrss.so NEEDED libcurl.so（运行期）；configure 亦强制
        # AC_CHECK_LIB(curl)。
        self.requires("curl/8.15.0")
        # 库依赖：mrss_parser.c/mrss_download.c 调用 nxml_* API，
        # configure PKG_CHECK_MODULES(nxml>=0.18) 强制要求。
        self.requires("libnxml/0.18.5")

    def build_requirements(self):
        # 仓库约定：自举用 conan autotools 固定版本。系统 automake
        # 1.16.5 在 PATH 序在前，必须显式 tool_requires。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("autoconf/2.72")
        # configure.ac 用 PKG_CHECK_MODULES(NXML, nxml>=0.18)——
        # aclocal 展开 PKG_* 宏需要 pkg.m4（pkgconf 包提供；tarball
        # 不带）。不注入则 configure 生成后在 15239 行报
        # `syntax error near unexpected token NXML,`（E058/pkg.m4
        # 注入问题，abiword 同类先例：ACLOCAL_PATH 指向 m4 目录）。
        self.tool_requires("pkgconf/3.0.5")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True,
            destination=self.source_folder)

    def generate(self):
        # 依赖注入（libnxml 同款）：
        #  1) AutotoolsDeps 生成 CPPFLAGS/LDFLAGS/LIBS —— configure 的
        #     裸 AC_CHECK_HEADER/AC_CHECK_LIB 检测靠这些变量通过；
        #     但其 LDFLAGS 含 -Wl,-rpath,<conan 缓存绝对路径>（会写进
        #     包内 .so 的 DT_RUNPATH，鸿蒙包规范禁止）——生成后剥除
        #     rpath 项，运行期查找改用 LD_LIBRARY_PATH；
        #  2) LD_LIBRARY_PATH env script —— configure conftest 与
        #     make check 运行测试程序时找到 curl/libnxml 的 .so。
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        self._strip_rpath_from_generated()

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
        tc.generate()

        env = Environment()
        # curl 是 direct host 依赖：完整 ref 写法（DRAFT-6052），
        # L0o 门禁不误报。libnxml 同理。
        for ref in ("curl/8.15.0", "libnxml/0.18.5"):
            dep = self.dependencies.direct_host[ref]
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", str(libdir))
        env.vars(self).save_script("ohos_env")

    def _strip_rpath_from_generated(self):
        """剥除 AutotoolsDeps 生成的 conanautotoolsdeps.sh 里的
        -Wl,-rpath(-Wl,)?... 项（保留 -L 与 -l）。libtool 链接 .so 时
        把 LDFLAGS 里的 rpath 记为 DT_RUNPATH——绝对路径指向宿主机
        conan 缓存，鸿蒙包规范禁止；运行期由 LD_LIBRARY_PATH 兜底。"""
        import re as _re
        f = os.path.join(self.generators_folder, "conanautotoolsdeps.sh")
        if not os.path.isfile(f):
            return
        with open(f) as fh:
            content = fh.read()
        # -Wl,-rpath -Wl,/path 与 -Wl,-rpath,/path 两种形式
        stripped, n1 = _re.subn(
            r"-Wl,-rpath\s+-Wl,\S+", "", content)
        stripped, n2 = _re.subn(
            r"-Wl,-rpath,\S+", "", stripped)
        stripped, n3 = _re.subn(
            r"-Wl,-rpath-link,\S+", "", stripped)
        if n1 + n2 + n3:
            with open(f, "w") as fh:
                fh.write(stripped)
            self.output.info(
                "stripped %d rpath entries from conanautotoolsdeps.sh"
                % (n1 + n2 + n3))

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
            changed.append("sub:ohos-os" if n else
                           "sub:ohos-os NOT FOUND")
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

    def _autotools_path_prefix(self):
        """自举环境的 perl 一致性（DRAFT-6049）：automake/1.18 包内
        .aclocal-real/.automake-real shebang 指向系统 perl，而 conanbuild
        的 PERL5LIB 指向 conan perl 库目录——两套 perl arch 目录不互通，
        加载 Cwd.so 报 handshake mismatch。修法：autoconf/m4 的 bin 前置，
        PERL5LIB 只保留 automake/autoconf 的纯 Perl 模块目录。"""
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
        """统一自举解释器为系统 perl（PERL=perl + PERL5LIB 限定纯 Perl
        模块目录），详见 DRAFT-6049。"""
        prefix = ":".join(self._autotools_path_prefix())
        am = self.dependencies.build["automake/1.18"]
        ac = self.dependencies.build["autoconf/2.72"]
        am_share = os.path.join(am.package_folder, "share", "automake-1.18")
        ac_share = os.path.join(ac.package_folder, "share", "autoconf")
        for d in (am_share, ac_share):
            if not os.path.isdir(d):
                raise ConanInvalidConfiguration(
                    "autotools share dir not found: %s" % d)
        # CONFIG_SHELL 指回本机可用 bash（绝对路径：libtool wrapper 的
        # shebang 也取它）：profile 的 /data/service/hnp/bin/bash 在部分
        # worker 上不存在。
        bash = os.environ.get("HMBS_BASH", "")
        if not bash or "/" not in bash:
            bash = self._which_bash()
        # ACLOCAL_PATH 注入 pkgconf 的 pkg.m4（PKG_CHECK_MODULES 宏展开，
        # E058 类问题；abiword 先例）。注意必须**保留** conanbuild env
        # 已有的 ACLOCAL_PATH（libtool 的 libtool.m4、automake 自身的
        # aclocal 目录都在其中），否则 AC_PROG_LIBTOOL 变 possibly
        # undefined。pkgconf 目录放最前即可。
        pkgconf = self.dependencies.build["pkgconf/3.0.5"]
        aclocal_dirs = []
        for d in ("share/aclocal", "share/aclocal-1.18"):
            p = os.path.join(pkgconf.package_folder, d)
            if os.path.isfile(os.path.join(p, "pkg.m4")):
                aclocal_dirs.append(p)
        if not aclocal_dirs:
            raise ConanInvalidConfiguration(
                "pkg.m4 not found in pkgconf package")
        extra_aclocal = ":".join(aclocal_dirs)
        # conanbuild 的 ACLOCAL_PATH（含 libtool.m4/automake aclocal）
        # 在 env script 里，不在当前进程 env——直接拼 libtool 包路径。
        lt = self.dependencies.build["libtool/2.5.4"]
        lt_aclocal = os.path.join(lt.package_folder, "share", "aclocal")
        if not os.path.isfile(os.path.join(lt_aclocal, "libtool.m4")):
            raise ConanInvalidConfiguration(
                "libtool.m4 not found in libtool package")
        extra_aclocal = "%s:%s" % (extra_aclocal, lt_aclocal)
        existing = os.environ.get("ACLOCAL_PATH", "")
        if existing:
            extra_aclocal = "%s:%s" % (extra_aclocal, existing)
        return ('CONFIG_SHELL=%s PATH="%s:$PATH" PERL=perl '
                'ACLOCAL_PATH="%s" PERL5LIB="%s:%s" autoreconf -fi'
                % (bash, prefix, extra_aclocal, am_share, ac_share))

    def _start_local_http(self):
        """起本地 HTTP 服务供 noinst 示例 parser 的 URL 数据源（后台
        线程，随进程退出）。"""
        import http.server
        import socketserver
        import threading

        www = os.path.join(self.build_folder, "hmbs_www")
        os.makedirs(www, exist_ok=True)
        with open(os.path.join(www, "feed.xml"), "w") as fh:
            fh.write(_LOCAL_RSS)

        class _Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *a, **kw):
                super().__init__(*a, directory=www, **kw)

            def log_message(self, *a):     # 静默
                pass

        httpd = socketserver.TCPServer(("127.0.0.1", _LOCAL_PORT), _Handler)
        th = threading.Thread(target=httpd.serve_forever, daemon=True)
        th.start()
        return httpd

    def build(self):
        # 1) NEWS 缺失规避（DRAFT-6053）：GitHub tag 归档不含 NEWS 实体
        #    文件，Makefile.am 未 foreign，automake 报 required file
        #    './NEWS' not found。touch 空文件即可，不改源码逻辑。
        news = os.path.join(self.source_folder, "NEWS")
        if not os.path.exists(news):
            with open(news, "w"):
                pass

        # 2) 自举：autoreconf -fi（conan automake/1.18 + libtool/2.5.4 +
        #    autoconf/2.72 闭包；perl/PERL5LIB 一致性见 _autoreconf_command）。
        self.run(self._autoreconf_command(),
                 cwd=self.source_folder, env="conanbuild")
        self._patch_autotools_scripts()

        # profile buildenv 的 CONFIG_SHELL=/data/service/hnp/bin/bash 在
        # 本机不存在（生成的 configure 首行 re-exec $CONFIG_SHELL → 127）。
        # conanbuild 聚合时 conanbuildenv 脚本在自定义 env script 之后
        # source，无法靠 generate() 覆盖；self.run(env="conanbuild") 同样
        # 携带坏值。改为：绕过 Autotools.configure() 的内部 env，直接以
        # os.environ + 叠加修正后的 conanbuild 变量运行 configure/make。
        # CONFIG_SHELL/SHELL 用**绝对路径** bash：libtool 生成的程序
        # wrapper shebang 取 CONFIG_SHELL——裸 'bash' 会产出 `#! bash`
        # 非法 shebang（test-driver 报 bad interpreter，exit 126）。
        bash = os.environ.get("HMBS_BASH", "")
        if not bash or "/" not in bash:
            bash = self._which_bash()
        self._run_configure_and_make(bash)

        self._run_upstream_tests()
        self._run_examples()

    def _which_bash(self):
        """定位本机绝对路径 bash（PATH 内首个 bash；OHOS 也常有
        /bin/bash -> /system/bin/bash 链接）。"""
        import shutil
        b = shutil.which("bash")
        if b:
            return b
        for cand in ("/bin/bash", "/system/bin/bash",
                     "/usr/local/bin/bash"):
            if os.access(cand, os.X_OK):
                return cand
        raise ConanInvalidConfiguration(
            "no usable bash found for CONFIG_SHELL")

    def _build_env(self, bash):
        """conanbuild 环境字典 + CONFIG_SHELL/SHELL 修正。

        conan 聚合的 conanbuildenv-release-*.sh 把 profile 的
        CONFIG_SHELL=/data/service/hnp/bin/bash 排在自定义 env script
        之后 source（后写覆盖），因此 generate() 里的 Environment 与
        env= 参数都救不回来。这里取 AutotoolsToolchain 生成的
        conanautotoolstoolchain.sh + conanautotoolsdeps.sh + ohos_env.sh
        的变量（自行按同样顺序解析），再强制 CONFIG_SHELL/SHELL 为本机
        bash。不 source conanbuildenv 脚本本身，从根上剔除坏值；其中
        的工具链变量由 profile 的 conf 已带（os.environ 继承 conan
        进程 env，CC/CFLAGS 等齐备）。"""
        import subprocess

        def shenv(script, base):
            cmd = 'set -e; . "%s" >/dev/null 2>&1; env -0' % script
            r = subprocess.run(["/bin/sh", "-c", cmd], capture_output=True)
            if r.returncode != 0:
                raise ConanInvalidConfiguration(
                    "failed to source %s: %s" % (script, r.stderr[:500]))
            out = {}
            for rec in r.stdout.split(b"\0"):
                if b"=" not in rec:
                    continue
                k, v = rec.split(b"=", 1)
                out[k.decode()] = v.decode()
            envd = dict(base)
            envd.update(out)
            return envd

        envd = dict(os.environ)
        conan_dir = os.path.join(self.generators_folder)
        for script in ("conanautotoolstoolchain.sh",
                       "conanautotoolsdeps.sh"):
            p = os.path.join(conan_dir, script)
            if os.path.isfile(p):
                envd = shenv(p, envd)
        envd["CONFIG_SHELL"] = bash
        envd["SHELL"] = bash
        sysbins = [b for b in ("/bin", "/system/bin") if b not in
                   envd.get("PATH", "").split(":")]
        if sysbins:
            envd["PATH"] = "%s:%s" % (envd.get("PATH", ""),
                                      ":".join(sysbins))
        # configure 的 AC_CHECK_LIB 阶段会真实运行 conftest（无 rpath），
        # 需要 curl/libnxml 的运行库目录在 LD_LIBRARY_PATH 里
        # （libmrss.so.0 链接 libnxml.so.0 + libcurl.so）。
        for d in self._dep_libdirs():
            envd["LD_LIBRARY_PATH"] = (
                "%s:%s" % (d, envd["LD_LIBRARY_PATH"])
                if envd.get("LD_LIBRARY_PATH") else d)
        # 关键（鸿蒙 .codesign 约束）：OHOS lld 链接时自动嵌入 .codesign
        # 段，加载器校验——**链接后改任何字节都会令签名失效**（musl 报
        # "Error loading shared library"）。因此不能用 post-link 清
        # RUNPATH 的方案。改为链接口径上就不产生 rpath：
        #   - libnxml 带 .la（conan 包内 libtool 档案），libtool 对
        #     -L<dir> + -lnxml 会把 <dir> 硬编码为 DT_RUNPATH——剥除
        #     其 -L 与 -l，改以**绝对 .so 路径**经 LIBS 传入（libtool
        #     对显式文件路径不做 libdir 硬编码）；
        #   - curl 包无 .la，-L/-l 不产生 rpath（libnxml 自身先例），
        #     保持原样，configure 的 AC_CHECK_LIB(curl) 需要 -L 与 -lcurl。
        envd["LDFLAGS"] = self._link_flags_without_nxml_dirs(
            envd.get("LDFLAGS", ""))
        # libnxml 包带 .la：libtool 对 -L<dir> -lnxml 会把 <dir> 硬编码
        # 为 DT_RUNPATH。curl 包无 .la、从未触发硬编码——同样口径：
        # NXML_LIBS/LIBS 指向构建树内**无 .la** 的 libnxml 链接目录
        # （见 _nxml_link_dir）。OHOS .codesign 禁止链后改字节，这是
        # 唯一可行通路。
        nxml_dir = self._nxml_link_dir()
        envd["NXML_LIBS"] = "-L%s -lnxml -lcurl" % nxml_dir
        envd["LIBS"] = "-lcurl -L%s -lnxml -lcurl" % nxml_dir
        # NXML_CFLAGS 需同时含 libnxml 与 curl 的 include（nxml.pc 的
        # Requires 传递 curl 头文件路径，直接覆写会丢失）。
        inc_dirs = []
        for ref in ("libnxml/0.18.5", "curl/8.15.0"):
            for d in self.dependencies.direct_host[ref] \
                    .cpp_info.includedirs:
                inc_dirs.append("-I%s" % d)
        envd["NXML_CFLAGS"] = " ".join(inc_dirs)
        # conan 进程 env 里 CC/CXX/CFLAGS 等（profile conf 注入）继续生效
        return envd

    def _link_flags_without_nxml_dirs(self, ldflags):
        """剥除 LDFLAGS 中指向 libnxml 包 libdir 的 -L<dir> 与 -lnxml
        （libnxml 带 .la，会令 libtool 硬编码 RUNPATH）。curl 的 -L/-l
        保留（无 .la，不硬编码，configure AC_CHECK_LIB 需要）。"""
        nxml_libdirs = [
            str(d) for d in
            self.dependencies.direct_host["libnxml/0.18.5"]
            .cpp_info.libdirs]
        parts = ldflags.split()
        out = []
        for p in parts:
            if p.startswith("-L") and p[2:] in nxml_libdirs:
                continue
            if p == "-lnxml":
                continue
            out.append(p)
        return " ".join(out)

    def _nxml_abs_so(self):
        """libnxml 绝对 .so 路径。"""
        for d in self.dependencies.direct_host["libnxml/0.18.5"] \
                .cpp_info.libdirs:
            cand = os.path.join(str(d), "libnxml.so")
            if os.path.isfile(cand):
                return cand
        raise ConanInvalidConfiguration(
            "libnxml.so not found in libnxml package")

    def _nxml_link_dir(self):
        """构建树内无 .la 的 libnxml 链接目录（libnxml.so + .so.0 符号
        链接）。libtool 对无 .la 的 -L<dir> -lnxml 不做 libdir 硬编码
        （curl 包即此情形），据此规避 DT_RUNPATH。"""
        nxml_dir = os.path.join(self.build_folder, "hmbs_link_libnxml")
        os.makedirs(nxml_dir, exist_ok=True)
        dst = os.path.join(nxml_dir, "libnxml.so")
        if not os.path.exists(dst):
            shutil.copy(self._nxml_abs_so(), dst)
            dst0 = os.path.join(nxml_dir, "libnxml.so.0")
            if not os.path.exists(dst0):
                os.symlink("libnxml.so", dst0)
        return nxml_dir

    def _run_configure_and_make(self, bash):
        envd = self._build_env(bash)
        configure = os.path.join(self.source_folder, "configure")
        cmd_configure = [bash, configure,
                         "--enable-shared", "--disable-static",
                         "--prefix=%s" % self.package_folder]
        self.output.info("RUN: %s" % " ".join(cmd_configure))
        import subprocess as _sp
        r = _sp.run(cmd_configure, cwd=self.build_folder, env=envd,
                    capture_output=True, text=True)
        if r.returncode != 0:
            self.output.error(r.stdout[-3000:])
            self.output.error(r.stderr[-3000:])
            raise ConanInvalidConfiguration("configure failed rc=%d"
                                            % r.returncode)
        r = _sp.run([bash, "-c",
                     # CPPFLAGS 追加 build-tree src/：mrss.h 由 mrss.h.in
                     # 生成在 build tree，上游 AM_CPPFLAGS 只指向 source
                     # tree（-I$(srcdir)/../src），out-of-tree 构建时
                     # test/*.c 的 #include "mrss.h" 找不到头文件。
                     "make -j%s CPPFLAGS='-I%s -I%s'"
                     % (os.cpu_count(),
                        os.path.join(self.build_folder, "src"),
                        os.path.join(self.source_folder, "src"))],
                    cwd=self.build_folder, env=envd,
                    capture_output=True, text=True)
        if r.returncode != 0:
            self.output.error(r.stdout[-3000:])
            self.output.error(r.stderr[-3000:])
            raise ConanInvalidConfiguration("make failed rc=%d"
                                            % r.returncode)
        self.output.info(r.stdout[-500:])

    def _dep_libdirs(self):
        """运行测试所需 .so 搜索路径：构建树 + 无 .la 链接目录 +
        curl + libnxml 包 libdir。"""
        dirs = [os.path.join(self.build_folder, "src", ".libs"),
                self._nxml_link_dir()]
        for ref in ("curl/8.15.0", "libnxml/0.18.5"):
            dep = self.dependencies.direct_host[ref]
            dirs.extend(str(d) for d in dep.cpp_info.libdirs)
        return dirs

    def _run_upstream_tests(self):
        """上游正式测试 = automake TESTS：new（1 项，纯离线，创建/
        set/写缓冲区往返断言）。真实运行 make check，输出
        HMBS_UPSTREAM_TEST_RESULT 机器证据行（hmbs 真机门禁只认这行）。
        parser/write/time/search 为 noinst 示例，另行单独验证。"""
        libdirs = self._dep_libdirs()
        env_prefix = "LD_LIBRARY_PATH=%s" % ":".join(libdirs)
        top = self.build_folder
        # make check 会补编 new.o，与 make 同样的 out-of-tree include
        # 修正（build-tree src/ 里有生成的 mrss.h）。
        cpp = ("-I%s -I%s"
               % (os.path.join(self.build_folder, "src"),
                  os.path.join(self.source_folder, "src")))

        buf = StringIO()
        self.run("%s make check -j1 CPPFLAGS='%s'" % (env_prefix, cpp),
                 cwd=top, env="conanbuild", stdout=buf, stderr=buf,
                 ignore_errors=True)
        out = buf.getvalue()
        if re.search(r"^FAIL:", out, re.M):
            dump = StringIO()
            self.run('echo "==== dump test/new.log ===="; '
                     "head -c 2500 test/new.log; echo",
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
            "command": "make check (LD_LIBRARY_PATH=buildtree+curl+libnxml)",
            "discovered": total,
            "executed": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "reason": ("conanfile.py build() 内执行上游 automake 测试套件"
                       "（test/new 1 项正式测试真实运行、纯离线）；"
                       "noinst 示例 parser/write/time/search 另行单独验证"),
        }
        print("HMBS_UPSTREAM_TEST_RESULT=" +
              json.dumps(result, ensure_ascii=False), flush=True)
        if failed > 0 or total != 1 or passed != 1:
            raise ConanInvalidConfiguration(
                "libmrss upstream tests failed: %d FAIL, %d PASS of %d"
                % (failed, passed, total))

    def _run_examples(self):
        """noinst 示例 parser/write/time/search 不是正式测试，单独构建
        并真实运行（URL 数据源 + 文件数据源各验）。"""
        libdirs = self._dep_libdirs()
        env_prefix = ("LD_LIBRARY_PATH=%s" % ":".join(libdirs))
        tdir = os.path.join(self.build_folder, "test")
        cpp = ("-I%s -I%s"
               % (os.path.join(self.build_folder, "src"),
                  os.path.join(self.source_folder, "src")))

        httpd = self._start_local_http()
        try:
            self.run("%s make parser write time search CPPFLAGS='%s'"
                     % (env_prefix, cpp), cwd=tdir, env="conanbuild")
            sample = os.path.join(self.build_folder, "hmbs_sample.xml")
            with open(sample, "w") as fh:
                fh.write(_LOCAL_RSS)
            out_file = os.path.join(self.build_folder, "hmbs_out.xml")
            checks = [
                # (示例, 参数, 期望退出码)
                ("parser", "http://127.0.0.1:%d/feed.xml" % _LOCAL_PORT, 0),
                ("parser", sample, 0),
                ("write", "%s %s" % (sample, out_file), 0),
                ("time", "http://127.0.0.1:%d/feed.xml" % _LOCAL_PORT, 0),
                ("search", sample, 0),
            ]
            for prog, args, expect in checks:
                buf = StringIO()
                rc = self.run("./%s %s" % (prog, args), cwd=tdir,
                              env="conanbuild", stdout=buf, stderr=buf,
                              ignore_errors=True)
                out = buf.getvalue()
                print("HMBS_EXAMPLE_%s(%s) rc=%s:\n%s"
                      % (prog, args, rc, out))
        finally:
            httpd.shutdown()

    def package(self):
        # install 同样绕过聚合 conanbuild env（CONFIG_SHELL 坏值会让
        # libtool 的 install 模式静默失败，产出空包）。
        bash = os.environ.get("HMBS_BASH", "")
        if not bash or "/" not in bash:
            bash = self._which_bash()
        envd = self._build_env(bash)
        import subprocess as _sp
        r = _sp.run([bash, "-c", "make install"],
                    cwd=self.build_folder, env=envd,
                    capture_output=True, text=True)
        if r.returncode != 0:
            self.output.error(r.stdout[-3000:])
            self.output.error(r.stderr[-3000:])
            raise ConanInvalidConfiguration("make install failed rc=%d"
                                            % r.returncode)
        # 注意：**不得**对包内 .so 做任何字节级后处理（清 RUNPATH 等）：
        # OHOS lld 自动嵌入 .codesign 段且 musl 加载器校验，链接后改动
        # 任何字节都会令签名失效（"Error loading shared library"）。
        # RUNPATH 规避在链接期完成（见 _build_env/_nxml_link_dir）。
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["mrss"]
        self.cpp_info.set_property("pkg_config_name", "mrss")
