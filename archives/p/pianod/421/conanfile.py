#!/usr/bin/env python3
"""Conan recipe — pianod 421 (upstream package name: pianod2) (autotools, application).

pianod2 is a multi-source, network-controlled music player daemon
(Pandora + local filesystem + tone generator) with an embedded web client.
Upstream is SVN-hosted; r421 (2026-02-03) is the current stable release.

OHOS adaptation notes (see notes.md for evidence):
  * configure/config.sub: HarmonyOS triple  -> patches/ (E007/E072/E160/E268)
  * mktemp -d on HMDFS yields an unwritable 0700 dir -> build-local shim (E114)
  * AC_FUNC_MALLOC cross-compile false negative -> ac_cv_* cache overrides (DRAFT rpl_malloc)
  * gstreamer .pc is published as ``gstreamer.pc``; configure asks for
    ``gstreamer-1.0`` -> alias .pc generated below
  * ohpcd ncurses ships only wide-char libs (libncursesw.a); configure
    hard-codes ``-lncurses`` -> local lib alias dir
"""
import glob
import os
import re
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, load, replace_in_file, save
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

_MKTEMP_SHIM = r"""#!/bin/sh
# HMDFS-safe mktemp shim (knowledge E114).
# system mktemp -d creates drwx--S--- dirs on HMDFS which the owner cannot
# write into (chmod is ignored), breaking autoconf's config.status.
# Plain mkdir produces drwxrws--x which works, so reproduce mktemp with mkdir.
isdir=0
unlink_out=0
tpl=""
for a in "$@"; do
    case "$a" in
        -d) isdir=1 ;;
        -u) unlink_out=1 ;;
        -q) : ;;
        -*) : ;;
        *)  tpl="$a" ;;
    esac
done
[ -n "$tpl" ] || tpl="tmp.XXXXXX"
case "$tpl" in
    *XXXXXX*) : ;;
    *) tpl="$tpl.XXXXXX" ;;
esac
head="${tpl%%XXXXXX*}"
tailpart="${tpl#*XXXXXX}"
i=0
while [ $i -lt 60 ]; do
    i=$((i+1))
    r=$(od -An -tx1 -N6 /dev/urandom 2>/dev/null | tr -d ' \n')
    [ -n "$r" ] || r="$$i$$"
    out="$head$r$tailpart"
    if [ $isdir -eq 1 ]; then
        mkdir "$out" 2>/dev/null && { [ $unlink_out -eq 1 ] && rmdir "$out"; echo "$out"; exit 0; }
    else
        if [ ! -e "$out" ]; then
            : > "$out" 2>/dev/null && { [ $unlink_out -eq 1 ] && rm -f "$out"; echo "$out"; exit 0; }
        fi
    fi
done
exit 1
"""


class Pianod2Conan(ConanFile):
    name = "pianod"
    version = "421"
    description = ("pianod2 r421 - multi-source, network-controlled music player "
                   "daemon (Pandora, local files, tone generator) with web client")
    license = "MIT"
    author = "OpenHarmonyPCDeveloper"
    homepage = "https://deviousfish.com/pianod"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # curl (not libcurl/8.5.0: that binary is built with CURL_USE_OPENSSL=OFF,
        # which breaks Pandora https:// requests at runtime).
        self.requires("curl/8.15.0.1")
        # football's TLS transport (src/football/fb_transport_openssl.c) + curl backend
        self.requires("openssl/3.5.6.1")
        # media engine; --with-engine=gstreamer (ffmpeg branch avoided: 13 transitive deps)
        self.requires("gstreamer/1.28.3")
        # filesystem source audio metadata
        self.requires("taglib/1.13.1")
        # coloured diagnostics / unit-test helpers
        self.requires("ncurses/6.6")
        # zlib/1.3.1.1 pin: gstreamer->glib2 and taglib both pin zlib/1.3.1, curl pins 1.3.1.1
        self.requires("zlib/1.3.1.1", override=True)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ---------------------------------------------------------------- helpers

    def _alias_dir(self):
        return os.path.join(self.build_folder, "deps-alias")

    def _shim_dir(self):
        return os.path.join(self.build_folder, "bin-shim")

    def _write_mktemp_shim(self):
        """E114: autoconf's config.status cannot use HMDFS mktemp -d output."""
        shim_dir = self._shim_dir()
        os.makedirs(shim_dir, exist_ok=True)
        save(self, os.path.join(shim_dir, "mktemp"), _MKTEMP_SHIM)
        os.chmod(os.path.join(shim_dir, "mktemp"), 0o755)
        return shim_dir

    def _write_pkgconfig_aliases(self):
        """configure probes ``gstreamer-1.0``; the package emits ``gstreamer.pc``."""
        alias_pc = os.path.join(self.build_folder, "pkgconfig-alias")
        os.makedirs(alias_pc, exist_ok=True)
        found = glob.glob(os.path.join(self.build_folder, "**", "*.pc"), recursive=True)
        by_name = {os.path.basename(p): p for p in found}
        # alias: copy <src>.pc -> <dst>.pc, rewriting only the Name: line
        for src_name, dst_name in (("gstreamer.pc", "gstreamer-1.0.pc"),):
            src = by_name.get(src_name)
            if not src:
                continue
            with open(src, "r", encoding="utf-8") as handle:
                body = handle.read()
            body = body.replace("Name: gstreamer\n", "Name: gstreamer-1.0\n")
            with open(os.path.join(alias_pc, dst_name), "w", encoding="utf-8") as handle:
                handle.write(body)
        return alias_pc, sorted({os.path.dirname(p) for p in found})

    def _write_ncurses_alias(self):
        """ohpcd ncurses ships libncursesw.a only; configure hardcodes -lncurses."""
        lib_dir = os.path.join(self._alias_dir(), "lib")
        os.makedirs(lib_dir, exist_ok=True)
        if "ncurses" not in self.dependencies:
            return lib_dir
        pkg_lib = os.path.join(self.dependencies["ncurses"].package_folder, "lib")
        for narrow, wide in (("libncurses.a", "libncursesw.a"),
                             ("libpanel.a", "libpanelw.a"),
                             ("libmenu.a", "libmenuw.a"),
                             ("libform.a", "libformw.a")):
            src = os.path.join(pkg_lib, wide)
            dst = os.path.join(lib_dir, narrow)
            if os.path.exists(src) and not os.path.exists(dst):
                shutil.copy2(src, dst)
        return lib_dir

    def _neutralize_hmdfs_mktemp(self):
        """E114: on HMDFS ``mktemp -d`` yields a drwx--S--- dir that even its owner
        cannot write into (chmod is ignored), so autoconf's config.status dies on
        ``./confXXXXXX/subs1.awk: Permission denied``.  configure already carries a
        plain-``mkdir`` fallback that works, so short-circuit the mktemp branch.
        config.status is generated by configure, so it inherits the fix."""
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            replace_in_file(self, configure_path,
                            'mktemp -d "./confXXXXXX"',
                            'false "./confXXXXXX"')

    def _dep_includedirs(self):
        """Include dirs published by every dependency (components included).

        configure resolves headers through pkg-config, but pianod2's Makefile.am
        forwards ${<pkg>_CFLAGS} only for the pianod target - src/common/
        http_test.cpp includes <curl/curl.h> with no -I of its own.  Passing
        CPPFLAGS on the configure command line is what makes autoconf bake the
        include dirs into @CPPFLAGS@ of every generated Makefile.
        """
        dirs = []
        for dep in self.dependencies.values():
            infos = [dep.cpp_info] + list((dep.cpp_info.components or {}).values())
            for info in infos:
                for rel in info.includedirs or []:
                    path = os.path.join(dep.package_folder, rel)
                    if os.path.isdir(path) and path not in dirs:
                        dirs.append(path)
        return dirs

    def _dep_libdirs(self):
        """Dependency libdirs + the local narrow-ncurses alias dir."""
        dirs = [os.path.join(self._alias_dir(), "lib")]
        for dep in self.dependencies.values():
            for rel in dep.cpp_info.libdirs or []:
                path = os.path.join(dep.package_folder, rel)
                if os.path.isdir(path):
                    dirs.append(path)
        return dirs

    # ---------------------------------------------------------------- build

    def generate(self):
        # conan's Autotools.install() drives `make install DESTDIR=<package_folder>`,
        # so the configured prefix must be relative to that staging root - an
        # absolute build-tree prefix would be appended under DESTDIR and bury the
        # binaries under <pkg>/storage/...  Dependency injection stays inside the
        # build folder (R49); nothing is written to a shared /usr/local.
        prefix = "/"
        alias_lib = self._write_ncurses_alias()
        shim_dir = self._write_mktemp_shim()
        alias_pc, pc_dirs = self._write_pkgconfig_aliases()

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--prefix={}".format(prefix),
            "--with-engine=gstreamer",
            "--with-tls=openssl",
            # AC_FUNC_MALLOC/AC_FUNC_REALLOC cannot run the probe when cross building and
            # default to "no", which swaps malloc for the absent gnulib rpl_malloc.
            "ac_cv_func_malloc_0_nonnull=yes",
            "ac_cv_func_realloc_0_nonnull=yes",
        ])
        tc.extra_ldflags.append("-L{}".format(alias_lib))
        # pianod2 mixes C (football) and C++ units and its Makefile.am does not
        # forward dependency include dirs for the helper programs, so inject them
        # into both language flag sets - autoconf bakes them into @CFLAGS@ /
        # @CXXFLAGS@ of every generated Makefile.
        for path in self._dep_includedirs():
            tc.extra_cflags.append("-I{}".format(path))
            tc.extra_cxxflags.append("-I{}".format(path))
        tc.generate()

        # AutotoolsDeps is deliberately NOT used: it injects every dependency
        # (including the shared libcurl) into autoconf's run-if-compiled probe,
        # and when that probe cannot resolve libcurl.so the configure script dies
        # with "cannot run C compiled programs".  PkgConfigDeps .pc files already
        # carry -I/-L/-l, which is all configure's DF_CHECK_LIBRARY probes need.
        PkgConfigDeps(self).generate()

        env = Environment()
        env.prepend("PATH", shim_dir)
        pkg_path = os.path.pathsep.join([alias_pc] + pc_dirs)
        env.prepend("PKG_CONFIG_PATH", pkg_path)
        env.vars(self).save_script("pianod2_ohos_env")

    def build(self):
        apply_conandata_patches(self)
        # E490: HMDFS 解包/打补丁会丢掉 autotools helper 的可执行位，恢复之
        for script in ("configure", "config.guess", "config.sub", "install-sh",
                       "missing", "compile", "depcomp", "test-driver", "ar-lib"):
            path = os.path.join(self.source_folder, script)
            if os.path.isfile(path):
                os.chmod(path, 0o755)
        self._neutralize_hmdfs_mktemp()
        # Belt and braces: the generated conanbuild script carries these, but the
        # autotools scripts shell out to mktemp/pkg-config directly.
        os.environ["PATH"] = "{}{}{}".format(
            self._shim_dir(), os.path.pathsep, os.environ.get("PATH", ""))
        alias_pc, pc_dirs = self._write_pkgconfig_aliases()
        os.environ["PKG_CONFIG_PATH"] = os.path.pathsep.join(
            [alias_pc] + pc_dirs + [os.environ.get("PKG_CONFIG_PATH", "")])
        # autoconf runs part of its probes (cross-compile check included); libcurl is
        # shipped shared by ohpcd, so expose the dependency libdirs during the build.
        os.environ["LD_LIBRARY_PATH"] = os.path.pathsep.join(
            self._dep_libdirs() + [os.environ.get("LD_LIBRARY_PATH", "")])
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # R51: 上游 automake 测试套件在同一构建环境里真实执行（7 个 TESTS）。
        # pianod_unittest 是 AT&T ksh93 脚本，OHOS 无 ksh93，它自带的守卫会
        # 以 automake 约定的 exit 77 上报 SKIP，因此 make check 整体返回 0。
        autotools.make(target="check", args=["-j1"])
        self._report_upstream_assertions()

    def _report_upstream_assertions(self):
        """把 automake 落在 *.log 里的断言级结果提升到构建日志。

        没有这一步，构建日志里只有用例级的 PASS/FAIL，报告中的
        "43 / 573 / 600 / 34 / 1261" 之类数字将无原始行可查（R51 禁止）。
        """
        pattern = re.compile(
            r"(tests run|tests? performed|tests? passed|^Passed:|^ok:|^SKIP|^FAIL|^# (TOTAL|PASS|SKIP|FAIL|XFAIL|ERROR):)",
            re.I)
        logs = []
        for root, _, files in os.walk(self.build_folder):
            for name in files:
                # automake writes <test>.log plus test-suite.log next to the Makefile
                if not name.endswith(".log") or name in ("config.log", "config.status.log"):
                    continue
                if name == "test-suite.log" or name.endswith((".test-suite.log",)) \
                        or "_test" in name or name.startswith(("tagreader", "json_format")) \
                        or name.endswith((".trs.log",)):
                    logs.append(os.path.join(root, name))
        total = 0
        for path in sorted(logs):
            for line in load(self, path).splitlines():
                line = line.strip()
                if line and pattern.search(line):
                    rel = os.path.relpath(path, self.build_folder)
                    self.output.info("[upstream-test] {}| {}".format(rel, line))
                    total += 1
        self.output.info("[upstream-test] forwarded {} assertion/summary lines".format(total))

    def package(self):
        autotools = Autotools(self)
        # installs into $DESTDIR (= package_folder) following the "/" prefix:
        #   bin/{pianod,piano,runmix}  share/man/man1/*  share/pianod/html/*
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        # application package: no libs, only executables
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
        # The recipe installs with --prefix=/ so that conan's DESTDIR-based
        # `make install` lands flat in <pkg>/bin and <pkg>/share.  The price is
        # that the compiled-in DEFAULT_WWWDIR ("//share/pianod/html") cannot be
        # package-relative, so hand consumers the real client dir through the
        # run environment (pianod -c "$PIANOD_CLIENTDIR").
        self.runenv_info.define_path(
            "PIANOD_CLIENTDIR", os.path.join(self.package_folder, "share", "pianod", "html"))
