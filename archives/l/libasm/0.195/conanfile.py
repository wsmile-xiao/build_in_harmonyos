#!/usr/bin/env python3
"""Conan recipe — libasm 0.195 (elfutils component, autotools).

libasm is the assembler library from the elfutils suite (sourceware.org).
This recipe builds the full elfutils 0.195 source (the tarball builds the
whole suite) and packages ONLY the libasm component:

  lib/libasm.so{,.1,-0.195.so}  lib/libasm.a
  include/elfutils/libasm.h  include/elfutils/version.h

elfutils/0.195 is required so that libasm.so.1's DT_NEEDED libelf.so.1 /
libdw.so.1 resolve from the published elfutils package at runtime, and the
<gelf.h>/<libelf.h> headers libasm.h includes are available to consumers.

The elfutils build/portability knowledge (musl error.h, libintl stub,
program_invocation_short_name, configure probe LD_LIBRARY_PATH, umask 077
on hmdfs, -Wno-error ordering after AM_CFLAGS) is shared with the already
published elfutils/0.195 recipe in archives/e/elfutils/0.195.
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


# ── OHOS install(1) shim (aircrack/1.7 → libsmf/1.3 merged precedent) ──
# OHOS has no coreutils install and elfutils' bundled config/install-sh does
# not support the GNU `-D` flag used by config/Makefile.am
# (install-data-local: `$(INSTALL_DATA) -D profile.sh ...`). HMFS also does
# not honour chmod. The shim ignores mode flags, creates leading dirs with
# mkdir -p and copies with cp(1).
_INSTALL_SHIM = r"""#!/bin/sh
is_dir=0
mk_leading=0
files=
while [ "$#" -gt 0 ]; do
  case "$1" in
    -d) is_dir=1 ;;
    -D) mk_leading=1 ;;
    -m) shift ;;
    -m?*|--mode=*) ;;
    -c|-p|-v|-s) ;;
    -g|-o|-t) shift ;;
    --) shift
        while [ "$#" -gt 0 ]; do files="$files $1"; shift; done
        break ;;
    -*) ;;
    *) files="$files $1" ;;
  esac
  shift
done
[ -z "$files" ] && exit 0
if [ "$is_dir" = 1 ]; then
  for d in $files; do mkdir -p "$d" || exit 1; done
  exit 0
fi
set -- $files
count=$#
[ "$count" -lt 2 ] && exit 0
if [ "$count" -ge 3 ]; then
  eval "dest=\${$count}"
  mkdir -p "$dest" || exit 1
elif [ "$mk_leading" = 1 ]; then
  eval "dest=\${$count}"
  mkdir -p "$(dirname "$dest")" || exit 1
fi
cp -f "$@" || exit 1
exit 0
"""


class LibasmConan(ConanFile):
    name = "libasm"
    version = "0.195"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        # 把 conandata.yml patches: 段列出的补丁文件导出到 build 环境
        # （仓库 5000+ 配方的标准形态；用属性 exports_sources=... 也能导出，
        #   但 conan-verify G1 门禁与 CI L0 检查按本形态识别）
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        # elfutils 本体提供 libelf/libdw 运行时与 gelf.h/libelf.h 头。
        # libasm.so.1 的 DT_NEEDED 是 libelf.so.1 —— 由 elfutils 包解析。
        self.requires("elfutils/0.195", transitive_headers=True, transitive_libs=True)
        # 构建 elfutils 源码树所需的基座依赖（与 elfutils/0.195 配方一致）
        self.requires("zlib/1.3.1.1")
        self.requires("zstd/1.5.7")
        self.requires("bzip2/1.0.8")
        self.requires("xz/5.6.2")
        self.requires("argp-standalone/1.5.0")
        self.requires("musl-fts/1.2.7")
        self.requires("musl-obstack/1.2.3")

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--build=aarch64-unknown-linux-musl")
        tc.configure_args.append("--host=aarch64-unknown-linux-musl")
        tc.configure_args.append("--disable-nls")
        tc.configure_args.append("--disable-werror")
        tc.configure_args.append("--enable-libdebuginfod=dummy")
        tc.configure_args.append("--disable-debuginfod")
        tc.configure_args.append("--with-zstd")
        tc.configure_args.append("--program-prefix=eu-")
        # musl 需要的三项（与 elfutils/0.195 配方、Alpine APKBUILD 一致）：
        #   _GNU_SOURCE      —— musl 在此宏下才暴露 program_invocation_short_name
        #   FNM_EXTMATCH=0   —— musl 的 fnmatch.h 没这个宏
        #   -Wno-error       —— CFLAGS 在 automake 编译行里排在 AM_CFLAGS 之后，
        #                      可覆盖 AM_CFLAGS 里写死的 -Werror
        tc.extra_cflags.append("-D_GNU_SOURCE")
        tc.extra_cflags.append("-DFNM_EXTMATCH=0")
        tc.extra_cflags.append("-Wno-error")
        tc.extra_cxxflags.append("-D_GNU_SOURCE")
        tc.extra_cxxflags.append("-Wno-error")

        # ── 依赖的 -I / -L / -l 必须经环境变量喂给 configure ──
        # elfutils 的 configure 用 AC_CHECK_LIB 类探测（如 --with-zstd 会试链 -lzstd），
        # 不给路径就报 `configure: error: missing -lzstd for --with-zstd`。
        _inc, _lib, _l = [], [], []
        for _ref, _dep in self.dependencies.items():
            ci = _dep.cpp_info
            for _p in ci.includedirs or []:
                _inc.append("-I" + _p)
            for _p in ci.libdirs or []:
                _lib.append("-L" + _p)
            for _n in ci.libs or []:
                _l.append("-l" + _n)
        os.environ["CPPFLAGS"] = " ".join(_inc) + " " + os.environ.get("CPPFLAGS", "")
        os.environ["LDFLAGS"] = " ".join(_lib) + " " + os.environ.get("LDFLAGS", "")
        # 三个 musl 垫片（argp / fts / obstack）提供 glibc 才有的符号，
        # elfutils 源码直接调它们，必须显式进 LIBS，否则链接期 undefined。
        os.environ["LIBS"] = " ".join(_l) + " " + os.environ.get("LIBS", "")
        self.output.info("CPPFLAGS=%s" % os.environ["CPPFLAGS"][:200])
        self.output.info("LDFLAGS=%s" % os.environ["LDFLAGS"][:200])
        self.output.info("LIBS=%s" % os.environ["LIBS"][:200])
        # configure 会**编译并运行**探测程序，链上共享库垫片后运行时找不到 .so
        # → `configure: error: cannot run C compiled programs.`
        # 用 LD_LIBRARY_PATH（只影响构建期进程执行，不进产物 RPATH）。
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
        if not os.path.isfile(os.path.join(self.source_folder, "", "configure")):
            self.output.info("源码树无 configure（GitHub archive 常见），先 autoreconf 自举")
            autotools.autoreconf()
        # ⚠️ umask / uname 这类对 configure 脚本本身的修补必须在 autoreconf 之后。
        # config.status 的临时目录用 `umask 077 && mktemp -d`（E011），hmdfs 下
        # 权限 700 导致 "can't create ./confXXX/subs1.awk: Permission denied"。
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
        # ── OHOS install-shim 安装（见 _INSTALL_SHIM）──
        shim_path = os.path.join(self.build_folder, "install-shim.sh")
        with open(shim_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(_INSTALL_SHIM)
        self.run(
            'make install DESTDIR="{pf}" INSTALL="/bin/sh {shim}" INSTALL_DATA=\'$(INSTALL)\''
            .format(pf=self.package_folder, shim=shim_path),
            cwd=self.build_folder, env="conanbuild")

        # ── 只保留 libasm 组件 ──
        # 移除整套构建产出的其他库与 eu-* 工具（保留 libasm*）
        for pat in ("lib/libelf*", "lib/libdw*", "lib/libebl*", "lib/libdebuginfod*"):
            for f in glob.glob(os.path.join(self.package_folder, pat)):
                if os.path.islink(f) or os.path.isfile(f):
                    try:
                        os.remove(f)
                    except OSError:
                        pass
        for name in ("libelf", "libdw", "libdwelf", "libdwfl", "libdwfl_stacktrace",
                     "debuginfod", "elf-knowledge", "known-dwarf"):
            for f in glob.glob(os.path.join(self.package_folder, "include", "elfutils", name + ".h")):
                try:
                    os.remove(f)
                except OSError:
                    pass
        _rm = os.path.join(self.package_folder, "bin")
        if os.path.isdir(_rm):
            import shutil
            shutil.rmtree(_rm, ignore_errors=True)
        _rm = os.path.join(self.package_folder, "lib", "pkgconfig")
        if os.path.isdir(_rm):
            import shutil
            shutil.rmtree(_rm, ignore_errors=True)
        # 签名（dlopen/链接加载需要 .codesign；conan install 复制会破坏链接器自签）
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        import glob as _glob
        targets = []
        for pat in ("lib", "lib/**"):
            targets += _glob.glob(os.path.join(self.package_folder, pat, "libasm*.so*"), recursive=True)
        targets = [t for t in targets if os.path.isfile(t) and not os.path.islink(t) and self._is_elf(t)]
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.libs = ["asm"]
        self.cpp_info.set_property("cmake_file_name", "libasm")
        self.cpp_info.set_property("cmake_target_name", "libasm::libasm")
        self.cpp_info.set_property("pkg_config_name", "libasm")
        # 不写 self.cpp_info.requires = ["elfutils"]：Conan 2 的 cpp_info.requires
        # 只能引用**同包内部** components，引用依赖包会报
        #   package_info(): requires to other internal components not defined
        # 依赖库（libelf/libdw）的链接传播已由 requirements() 的
        # transitive_headers=True + transitive_libs=True 完成（消费者链接
        # -lasm 时会自动带上 -lelf/-ldw，且 libasm.h -> <gelf.h> 头闭包可用）。
