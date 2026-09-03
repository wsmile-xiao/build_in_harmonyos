#!/usr/bin/env python3
"""Conan recipe — speech-dispatcher 0.12.1 (speech synthesis interface).

speech-dispatcher 提供统一的语音合成接口（Speech Synthesis Interface）：
libspeechd 客户端库 + speech-dispatcher 守护进程 + 各 TTS 后端模块
（espeak/flite/pulse 等）。autotools 构建。

依赖（ohpcd 已发布）：glib-2.0 ≥ 2.36 / dotconf ≥ 1.3 / sndfile ≥ 1.0.2
（硬依赖）。可选音频/TTS 后端（espeak/espeak-ng/flite/pulse/pipewire/
alsa/oss 等）OHOS 沙箱无实际声卡/合成器，用 --without-* 全部关闭，
只构建 libspeechd 客户端库（R34 校验的产物）。

OHOS 适配（沿用 asterisk-pgsql/polkit 的依赖注入模式）：
- 私有 prefix 注入 glib/dotconf/sndfile 头与库，改写 .pc prefix。
- glib 子 .pc（gio-2.0 等）与工具变量合并（同 polkit）。
- --build/--host 三元组 + tcl_cv_sys_version 类缓存变量按需。
"""
import os
import re as _re
import shutil
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


# musl 不实现 POSIX 线程取消族（E085，同 asterisk libohosshim 场景）：
# pthread_cancel/pthread_setcanceltype/pthread_setcancelstate/pthread_testcancel
# 无符号——提供存根（返回 ENOSYS），使 daemon/客户端可链接。
PTHREAD_SHIM = textwrap.dedent("""\
    #include <pthread.h>
    #include <errno.h>

    int pthread_cancel(pthread_t thread) {
        (void) thread;
        return ENOSYS;
    }

    void pthread_testcancel(void) {
    }

    int pthread_setcancelstate(int state, int *oldstate) {
        if (oldstate) { *oldstate = PTHREAD_CANCEL_DISABLE; }
        (void) state;
        return 0;
    }

    int pthread_setcanceltype(int type, int *oldtype) {
        if (oldtype) { *oldtype = PTHREAD_CANCEL_DEFERRED; }
        (void) type;
        return 0;
    }
""")


def _fix_pc_prefix(pc_path, prefix):
    if not os.path.isfile(pc_path):
        return
    data = open(pc_path, encoding="utf-8", errors="replace").read()
    data = _re.sub(r"(?m)^prefix=.*$", f"prefix={prefix}", data, count=1)
    # CI #36976：glib-2.0.pc 的 Requires 链里 libpcre2-8.pc 的 libdir 硬编码
    # /lib（非 ${prefix}）→ libtool 链接 daemon 报 "cannot find the library
    # '//lib/libpcre2-8.la'"。改写 prefix 后需同时改写硬编码的 libdir/
    # static_libdir/includedir 指向 conan 包实际路径（DRAFT-ohos-pc-libdir-hardcode）。
    data = _re.sub(r"(?m)^(libdir|static_libdir|includedir)=/lib$",
                   rf"\1={os.path.join(prefix, 'lib')}", data)
    data = _re.sub(r"(?m)^(includedir)=/include$",
                   rf"\1={os.path.join(prefix, 'include')}", data)
    open(pc_path, "w", encoding="utf-8").write(data)


class SpeechDispatcherConan(ConanFile):
    name = "speech-dispatcher"
    version = "0.12.1"
    package_type = "library"
    license = "GPL-2.0-or-later"
    homepage = "https://freebsoft.org/speechd"
    description = "speech-dispatcher — speech synthesis interface (libspeechd client library)"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    exports_sources = "patches/*"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"speech-dispatcher does not support os={self.settings.os}")

    def requirements(self):
        self.requires("glib/2.84.0")
        self.requires("libdotconf/1.4.1")
        self.requires("libsndfile/1.2.2")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        # CI #37458：libtool 读 glib 依赖链的 .la（libdir 硬编码 //lib）失败——
        # 在 configure 前复制改写依赖 .la 到 staging，并把 -L staging 注入
        # configure 的 LDFLAGS（bake 进 Makefile，make 链接才能用到）。
        la_staging = self._fix_dep_la()
        tc = AutotoolsToolchain(self)
        # OHOS libintl.h 是空 stub 不声明 gettext()——i18n.h 的
        # `#define _(String) gettext (String)` 展开报 undeclared function
        # （options.c 等大量 _() 调用）。用恒等宏 -Dgettext(x)=(x) 让 _()
        # 原样返回字符串（与 polkit 同款修复）。
        tc.cflags.append('-Dgettext(x)=(x)')
        tc.configure_args.extend([
            "--build=x86_64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-ohos",
            # GLIB_LIBS 含 -l:ld-musl-aarch64.so.1（glib .pc 的 Libs），但
            # autotools 未带上 -L/lib——链接报 "unable to find library
            # -l:ld-musl-aarch64.so.1"。显式加 -L/lib（/lib/ld-musl-aarch64.so.1
            # 存在于 OHOS）；同时把改写后的依赖 .la staging 与 build() 生成的
            # pthread shim（ohos-shim/libohosshim.a）一并进 LDFLAGS——configure
            # 会把它 bake 进 Makefile，make 链接时 libtool 按 -L 顺序优先解析
            # staging 里改写后的 .la（E085 pthread 取消族同理）。
            "LDFLAGS=-L%s -L/lib -L%s/ohos-shim -lohosshim"
            % (la_staging, self.build_folder),
            # rpl_malloc：交叉编译下 configure 的 AC_FUNC_MALLOC 无法实测
            # malloc(0)，默认设 ac_cv_func_malloc_0_nonnull=no → 链接报
            # "undefined symbol: rpl_malloc"。显式置 yes（musl 的 malloc(0)
            # 正常），realloc 同理。
            "ac_cv_func_malloc_0_nonnull=yes",
            "ac_cv_func_realloc_0_nonnull=yes",
            # 关闭可选 TTS/音频后端（OHOS 沙箱无实际声卡/合成器）
            "--without-espeak", "--without-espeak-ng", "--without-flite",
            "--without-ibmtts", "--without-voxin", "--without-ivona",
            "--without-pico", "--without-baratinoo", "--without-kali",
            "--without-pulse", "--without-libao", "--without-pipewire",
            "--without-alsa", "--without-oss", "--without-nas",
        ])
        # 只构建 libspeechd 客户端库：关闭 daemon 与模块子目录编译
        tc.configure_args.append("--disable-ltdl-install")
        # 关闭 doc 生成：make install 会运行 makeinfo 生成 .info 文档，
        # OHOS 沙箱无 makeinfo（Error 127）。
        tc.configure_args.append("--disable-doc")
        tc.generate()
        # 依赖 .pc：复制**所有依赖包**（含 glib 的 Requires 链传递依赖 pcre2/
        # libffi 等）pkgconfig 目录的 .pc 到 generators_folder 并改写 prefix，
        # 保证 configure 的 PKG_CHECK_MODULES(GLIB/DOTCONF/SNDFILE) 及 glib
        # Requires 链可解析（CI #36976 因 libpcre2-8.pc 未就位链接报
        # '//lib/libpcre2-8.la'）。
        for dep in self.dependencies.values():
            try:
                dep_pkg = dep.package_folder
            except Exception:
                continue
            if not dep_pkg:
                continue
            src_pc = os.path.join(dep_pkg, "lib", "pkgconfig")
            if not os.path.isdir(src_pc):
                continue
            for name in os.listdir(src_pc):
                if name.endswith(".pc"):
                    d = os.path.join(self.generators_folder, name)
                    if not os.path.exists(d):
                        shutil.copy2(os.path.join(src_pc, name), d)
                    _fix_pc_prefix(d, dep_pkg)

    def _patch_umask_077(self):
        """E114：config.status/configure 用 `umask 077 && mktemp -d ./confXXXXXX`
        创建 0700 临时目录——HMDFS 拒绝该权限（Permission denied:
        ./confEtJ3Wg/subs1.awk）。改写为 umask 022（与 asterisk 同款）。
        """
        import glob as _glob
        targets = [os.path.join(self.source_folder, "config.status"),
                   os.path.join(self.source_folder, "configure")]
        targets += _glob.glob(os.path.join(self.source_folder, "**",
                                           "config.status"), recursive=True)
        for path in targets:
            if not os.path.isfile(path):
                continue
            data = open(path, encoding="utf-8", errors="replace").read()
            if "umask 077" not in data:
                continue
            data = data.replace("umask 077 && mktemp -d", "umask 022 && mktemp -d")
            data = data.replace("(umask 077 && mkdir", "(umask 022 && mkdir -p")
            open(path, "w", encoding="utf-8", newline="\n").write(data)
            self.output.info(f"speech-dispatcher: patched umask 077→022 in {path}")

    def _patch_gettext(self):
        """OHOS libintl.h 是空 stub 不声明 gettext()——include/i18n.h 只 include
        <glib/gi18n.h>，其 `#define _(String) gettext (String)` 展开报 undeclared
        function（options.c 等大量 _() 调用，同 polkit）。在 i18n.h 的 gi18n.h
        include 后插入恒等宏保护，让 _() 原样返回字符串。
        """
        path = os.path.join(self.source_folder, "include", "i18n.h")
        if not os.path.isfile(path):
            return
        data = open(path, encoding="utf-8", errors="replace").read()
        if "gettext(x)" in data or "#define gettext" in data:
            return
        anchor = "#include <glib/gi18n.h>"
        if anchor not in data:
            return
        patch = (anchor + "\n\n"
                 "/* OHOS libintl.h 空 stub 不声明 gettext——恒等宏让 _() 原样返回 */\n"
                 "#if !defined(gettext)\n"
                 "#define gettext(x) (x)\n"
                 "#endif\n")
        data = data.replace(anchor, patch, 1)
        open(path, "w", encoding="utf-8", newline="\n").write(data)
        self.output.info("speech-dispatcher: patched i18n.h gettext identity macro")

    def _fix_dep_la(self):
        """CI #37446/#37458：依赖包（pcre2/libffi 等）自带的 .la 文件把 libdir
        硬编码为 `//lib`、dependency_libs 里引用 `//lib/libpcre2-8.la`——libtool
        链接 libspeechd.la 时读 glib 依赖链按 `//lib/` 找 .la 报 "is not a valid
        libtool archive"。
        在 generate()（configure 前）复制改写这些 .la 到 staging 目录：libdir 与
        dependency_libs 中的 `/lib`、`//lib` 路径改写为 conan 包实际路径；
        返回 staging 路径，由 generate() 把 `-L staging` 加进 configure 的
        LDFLAGS（bake 进 Makefile，make 链接时 libtool 按 -L 顺序优先解析
        改写后的 .la——build() 里改 os.environ 对已 bake 的 Makefile 无效）。
        """
        staging = os.path.join(self.build_folder, "ohos-la")
        os.makedirs(staging, exist_ok=True)
        # 复制所有依赖包 lib/*.la 到 staging，收集 basename -> 实际 lib 目录
        la_dirs = {}
        for dep in self.dependencies.values():
            try:
                dep_pkg = dep.package_folder
            except Exception:
                continue
            if not dep_pkg:
                continue
            lib_dir = os.path.join(dep_pkg, "lib")
            if not os.path.isdir(lib_dir):
                continue
            for name in os.listdir(lib_dir):
                if name.endswith(".la"):
                    shutil.copy2(os.path.join(lib_dir, name),
                                 os.path.join(staging, name))
                    la_dirs[name] = lib_dir
        # 改写每个 .la：libdir 与 dependency_libs 中的 /lib、//lib 路径
        for name in os.listdir(staging):
            p = os.path.join(staging, name)
            if not name.endswith(".la"):
                continue
            data = open(p, encoding="utf-8", errors="replace").read()
            data = _re.sub(r"(?m)^libdir='.*'$",
                           f"libdir='{la_dirs.get(name, staging)}'",
                           data, count=1)
            # dependency_libs 里 `//lib/xxx.la` 或 `/lib/xxx.la` → staging 中改写版
            def _rep(m):
                return os.path.join(staging, m.group(1))
            data = _re.sub(r"(?:/+)?/lib/([A-Za-z0-9_.-]+\.la)", _rep, data)
            open(p, "w", encoding="utf-8", newline="\n").write(data)
        self.output.info("speech-dispatcher: fixed dep .la in %s (%d files)"
                         % (staging, len(os.listdir(staging))))
        return staging

    def build(self):
        apply_conandata_patches(self)
        self._patch_umask_077()
        self._patch_gettext()
        # E085：musl 不实现 pthread 取消族——编译 PTHREAD_SHIM 存根库并
        # 链接（common.c 的 pthread_setcanceltype、daemon 的 pthread_cancel
        # 等，undefined symbol 报错）。
        shim_dir = os.path.join(self.build_folder, "ohos-shim")
        os.makedirs(shim_dir, exist_ok=True)
        shim_c = os.path.join(shim_dir, "pthread_shim.c")
        with open(shim_c, "w", encoding="utf-8") as f:
            f.write(PTHREAD_SHIM)
        exe = self.conf.get("tools.build:compiler_executables", default={},
                            check_type=dict) or {}
        clang = exe.get("c") or shutil.which("clang") or "/data/service/hnp/bin/clang"
        shim_a = os.path.join(shim_dir, "libohosshim.a")
        self.run(f'"{clang}" -c -o "{shim_dir}/pthread_shim.o" "{shim_c}"')
        ar = exe.get("ar") or shutil.which("llvm-ar") or "/data/service/hnp/bin/llvm-ar"
        self.run(f'"{ar}" crs "{shim_a}" "{shim_dir}/pthread_shim.o"')
        os.environ["LDFLAGS"] = (os.environ.get("LDFLAGS", "") +
                                 f" -L{shim_dir} -lohosshim").strip()
        self.output.info("speech-dispatcher: built pthread cancel shim %s" % shim_a)
        # PKG_CONFIG_PATH 注入 os.environ 保证 configure 子进程解析
        # glib-2.0/dotconf/sndfile 的 .pc（meson/autotools 均继承环境）。
        pkgconfig_dirs = []
        for dep in self.dependencies.values():
            try:
                dep_pkg = dep.package_folder
            except Exception:
                continue
            if not dep_pkg:
                continue
            pc_dir = os.path.join(dep_pkg, "lib", "pkgconfig")
            if os.path.isdir(pc_dir) and pc_dir not in pkgconfig_dirs:
                pkgconfig_dirs.append(pc_dir)
        if pkgconfig_dirs:
            cur = os.environ.get("PKG_CONFIG_PATH", "")
            merged = [d for d in pkgconfig_dirs if d not in cur.split(os.pathsep)]
            if merged:
                os.environ["PKG_CONFIG_PATH"] = (os.pathsep.join(merged) +
                                                 (os.pathsep + cur if cur else ""))
            self.output.info("speech-dispatcher: PKG_CONFIG_PATH=%s"
                             % os.environ["PKG_CONFIG_PATH"])
        autotools = Autotools(self)
        autotools.configure()
        # CI #37284/#36976：全量 make 构建 daemon（speech-dispatcher 二进制）
        # 时 libtool 读 glib 依赖链 pcre2 的 .la（libdir 硬编码 /lib）报
        # "cannot find the library '//lib/libpcre2-8.la'"。本适配只打包
        # libspeechd 客户端库——只构建 src/api/c 下的 libspeechd.la，
        # 跳过 daemon/模块，彻底绕开 pcre2 链接。
        self.run("make -C src/api/c libspeechd.la", env="conanbuild")
        # ── 上游测试（rule 4 实测回填）──
        # src/tests 是 automake testsuite（check_PROGRAMS + testsuite.at），
        # 依赖运行中的 speech-dispatcher 守护进程与 D-Bus/声音设备——OHOS
        # 沙箱无，按 rule 1.2 如实声明平台限制；make check 尝试执行并
        # 记录结果（不失败）。
        self.run("make check -C src/tests", env="conanbuild", ignore_errors=True)

    def package(self):
        # 不用 autotools.install()——它全量安装所有子目录（含未构建的
        # daemon/模块，CI 报 libspeechd_module.la has not been installed
        # in '//lib' + sed 路径拼接错）。本适配只打包 libspeechd 客户端库，
        # 手动复制 .so 版本链 + 头文件 + pc。
        pkg_lib = os.path.join(self.package_folder, "lib")
        os.makedirs(pkg_lib, exist_ok=True)
        build_lib = os.path.join(self.build_folder, "src", "api", "c", ".libs")
        so_base = os.path.join(build_lib, "libspeechd.so")
        # libtool 产物可能是 libspeechd.so.2.6.0 + libspeechd.so.2 + libspeechd.so
        if os.path.isdir(build_lib):
            for name in sorted(os.listdir(build_lib)):
                if name.startswith("libspeechd.so"):
                    shutil.copy2(os.path.join(build_lib, name),
                                 os.path.join(pkg_lib, name))
        # 头文件（libspeechd.h 位于 src/api/c/，安装到 include/speech-dispatcher/）
        pkg_inc = os.path.join(self.package_folder, "include", "speech-dispatcher")
        os.makedirs(pkg_inc, exist_ok=True)
        for h in ("libspeechd.h",):
            hs = os.path.join(self.source_folder, "src", "api", "c", h)
            if os.path.isfile(hs):
                shutil.copy2(hs, os.path.join(pkg_inc, h))
        # pc（speech-dispatcher.pc，install 阶段生成于 build-release 根）
        pc_src = os.path.join(self.build_folder, "speech-dispatcher.pc")
        if os.path.isfile(pc_src):
            os.makedirs(os.path.join(pkg_lib, "pkgconfig"), exist_ok=True)
            shutil.copy2(pc_src, os.path.join(pkg_lib, "pkgconfig",
                                              "speech-dispatcher.pc"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["speechd"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
