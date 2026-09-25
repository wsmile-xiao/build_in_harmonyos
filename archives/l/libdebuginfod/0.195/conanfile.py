#!/usr/bin/env python3
"""Conan recipe — libdebuginfod 0.195 (elfutils 源内 debuginfod 客户端库, autotools).

elfutils 0.195 发布 tarball 内含 debuginfod 子树:libdebuginfod 客户端库
(debuginfod-client.c, 纯 C, libcurl 后端)、debuginfod-find 客户端工具与
debuginfod 服务端(debuginfod.cxx, libmicrohttpd+sqlite3+libarchive)。
本包交付客户端库与 debuginfod-find;服务端随构建产出,供上游测试套件
(run-debuginfod-*.sh,服务端跑本机回环)真实执行。

同源说明:与 elfutils/0.195 同一上游 tarball,但 elfutils 配方显式
`--enable-libdebuginfod=dummy --disable-debuginfod`(交付里无 debuginfod);
本包是该组件的真实交付(先例:gtest_main 之于 gtest,单独立项)。
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.gnu import PkgConfigDeps


class LibdebuginfodConan(ConanFile):
    name = "libdebuginfod"
    version = "0.195"
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
        # 客户端库链接 elfutils 的 libelf(elf_version/elf_begin 等符号),
        # 运行时由 elfutils 包提供
        self.requires("elfutils/0.195")
        # ── elfutils 树 configure/编译所需(与 elfutils/0.195 配方一致) ──
        self.requires("zlib/1.3.1.1")
        self.requires("zstd/1.5.7")
        self.requires("bzip2/1.0.8")
        self.requires("xz/5.6.2")
        self.requires("argp-standalone/1.5.0")
        self.requires("musl-fts/1.2.7")
        self.requires("musl-obstack/1.2.3")
        # ── 客户端:PKG_CHECK_MODULES([libcurl],[libcurl >= 7.29.0]) ──
        self.requires("curl/8.15.0")
        # ── 服务端:configure 判定串要求 have_jsonc+HAVE_CXX11+libarchive+sqlite3
        #    全 yes(configure.ac:944),外加 libmicrohttpd>=0.9.33(920 行)。
        #    服务端是上游测试套件的运行前提(33 个 run-debuginfod-*.sh 走本机回环)。
        self.requires("json-c/0.17")
        self.requires("libmicrohttpd/1.0.1")
        self.requires("sqlite3/3.49.1")
        self.requires("libarchive/3.8.7")

    def build_requirements(self):
        # PKG_CHECK_MODULES 需要 pkg-config 工具(设备 clean 环境无,制品仓有)
        self.tool_requires("pkgconf/3.0.6")

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        # configure 用 PKG_CHECK_MODULES 探测 libcurl/libmicrohttpd/sqlite3/libarchive,
        # 必须让 pkg-config 能看到 conan 生成的 .pc(PkgConfigDeps 落在 generators 目录)
        PkgConfigDeps(self).generate()
        gen = self.generators_folder
        os.environ["PKG_CONFIG_PATH"] = gen + ":" + os.environ.get("PKG_CONFIG_PATH", "")

        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        tc.configure_args.append("--disable-nls")
        tc.configure_args.append("--disable-werror")
        # 与 elfutils 配方的关键差异:真客户端 + 服务端(测试套件需要)
        tc.configure_args.append("--enable-libdebuginfod=libcurl")
        tc.configure_args.append("--enable-debuginfod")
        tc.configure_args.append("--with-zstd")
        # 不加 --program-prefix:交付二进制保持上游名 debuginfod-find / debuginfod
        # musl 三件套(与 elfutils 配方同源结论):
        tc.extra_cflags.append("-D_GNU_SOURCE")
        tc.extra_cflags.append("-DFNM_EXTMATCH=0")
        tc.extra_cflags.append("-Wno-error")
        tc.extra_cxxflags.append("-D_GNU_SOURCE")
        tc.extra_cxxflags.append("-Wno-error")

        # ── 依赖的 -I / -L / -l 经环境变量喂给 configure(elfutils 配方同款结论:
        #    AC_CHECK_LIB 类探测不认 toolchain 内的路径,必须走 os.environ) ──
        _inc, _lib, _l = [], [], []
        for _ref, _dep in self.dependencies.items():
            ci = _dep.cpp_info
            for _p in ci.includedirs or []:
                _inc.append("-I" + _p)
            for _p in ci.libdirs or []:
                _lib.append("-L" + _p)
            for _n in ci.libs or []:
                _l.append("-l" + _n)
        # musl 无 error.h,而 elfutils 上游测试程序大量调用 error()/error_at_line():
        # 注入一个 glibc 兼容 shim 头(仅构建期可见,不进交付物)
        shimdir = os.path.join(self.generators_folder, "musl-shim")
        os.makedirs(shimdir, exist_ok=True)
        with open(os.path.join(shimdir, "error.h"), "w", encoding="utf-8") as fh:
            fh.write(
"""#ifndef _MUSL_ERROR_H_SHIM
#define _MUSL_ERROR_H_SHIM
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>

static unsigned int error_message_count = 0;
static int error_one_per_line = 0;

static void error(int status, int errnum, const char *format, ...)
{
    va_list ap;
    fflush(stdout);
    fprintf(stderr, "%s: ", program_invocation_short_name);
    if (errnum)
        fprintf(stderr, "%s: ", strerror(errnum));
    va_start(ap, format);
    vfprintf(stderr, format, ap);
    va_end(ap);
    fputc('\\n', stderr);
    error_message_count++;
    if (status)
        exit(status);
}

static void error_at_line(int status, int errnum, const char *filename,
                          unsigned int line_number, const char *format, ...)
{
    va_list ap;
    fflush(stdout);
    fprintf(stderr, "%s:%u: ", filename, line_number);
    if (errnum)
        fprintf(stderr, "%s: ", strerror(errnum));
    va_start(ap, format);
    vfprintf(stderr, format, ap);
    va_end(ap);
    fputc('\\n', stderr);
    error_message_count++;
    if (status)
        exit(status);
}
#endif
""")
        _inc.insert(0, "-I" + shimdir)
        os.environ["CPPFLAGS"] = " ".join(_inc) + " " + os.environ.get("CPPFLAGS", "")
        os.environ["LDFLAGS"] = " ".join(_lib) + " " + os.environ.get("LDFLAGS", "")
        os.environ["LIBS"] = " ".join(_l) + " " + os.environ.get("LIBS", "")
        self.output.info("CPPFLAGS=%s" % os.environ["CPPFLAGS"][:200])
        self.output.info("LDFLAGS=%s" % os.environ["LDFLAGS"][:200])
        # 构建期探测程序要能跑到共享依赖(musl-fts/musl-obstack/.so),
        # 用 LD_LIBRARY_PATH(不进产物,不烤路径)
        _ldpath = ":".join(_p for _dep in
                           (d for _r, d in self.dependencies.items())
                           for _p in (_dep.cpp_info.libdirs or []))
        if _ldpath:
            os.environ["LD_LIBRARY_PATH"] = _ldpath + ":" + os.environ.get("LD_LIBRARY_PATH", "")
            self.output.info("构建期 LD_LIBRARY_PATH=%s" % os.environ["LD_LIBRARY_PATH"][:200])
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        import os as _os
        if not _os.path.isfile(_os.path.join(self.source_folder, "configure")):
            self.output.info("源码树无 configure,先 autoreconf 自举")
            autotools.autoreconf()
        # hmdfs 陷阱:configure 脚本内 umask 077 会污染生成文件权限(elfutils 配方同款修补,
        # 必须在 autoreconf 之后做)
        for _cfg in glob.glob(os.path.join(self.source_folder, "**", "configure"), recursive=True):
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
        src = self.source_folder
        bld = self.build_folder
        os.makedirs(os.path.join(self.package_folder, "bin"), exist_ok=True)
        os.makedirs(os.path.join(self.package_folder, "lib"), exist_ok=True)
        os.makedirs(os.path.join(self.package_folder, "include"), exist_ok=True)
        # debuginfod.h 由 configure 从 debuginfod.h.in 生成于构建目录
        hdr = os.path.join(bld, "debuginfod", "debuginfod.h")
        if os.path.isfile(hdr):
            shutil.copy2(hdr, os.path.join(self.package_folder, "include", "debuginfod.h"))
        # 客户端库(libtool 产物在 .libs;版本化 .so 连同真实文件一起拷)
        libdir = os.path.join(bld, "debuginfod", ".libs")
        if not os.path.isdir(libdir):
            # libtool 布局可能不同:在构建树里搜真实产物
            cands = []
            for root, dirs, files in os.walk(bld):
                for f in files:
                    if f.startswith("libdebuginfod.so") or f == "libdebuginfod.a":
                        cands.append(root)
            if not cands:
                raise ConanException("构建树中找不到 libdebuginfod 产物")
            libdir = cands[0]
            self.output.info("libdebuginfod 产物目录: %s" % libdir)
        for name in os.listdir(libdir):
            if name == "libdebuginfod.a" or name.startswith("libdebuginfod.so"):
                srcf = os.path.join(libdir, name)
                dst = os.path.join(self.package_folder, "lib", name)
                if os.path.islink(srcf):
                    if os.path.lexists(dst):
                        os.remove(dst)
                    os.symlink(os.readlink(srcf), dst)
                else:
                    shutil.copy2(srcf, dst)
        # 客户端工具
        for tool in ("debuginfod-find",):
            p = os.path.join(bld, "debuginfod", tool)
            if os.path.isfile(p):
                shutil.copy2(p, os.path.join(self.package_folder, "bin", tool))
        # 服务端二进制一并交付(同一子树的组成物;测试与本地场景需要)
        srv = os.path.join(bld, "debuginfod", "debuginfod")
        if os.path.isfile(srv):
            shutil.copy2(srv, os.path.join(self.package_folder, "bin", "debuginfod"))
        # 鸿蒙 PC XPM:.so 与被 exec 的 ELF 都要自签(elfutils 配方同款)
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
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
            if os.path.islink(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.libs = ["debuginfod"]
        self.cpp_info.set_property("cmake_file_name", "libdebuginfod")
        self.cpp_info.set_property("cmake_target_name", "libdebuginfod::libdebuginfod")
        self.cpp_info.set_property("pkg_config_name", "libdebuginfod")
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            self.buildenv_info.define_path("PATH", bindir)
