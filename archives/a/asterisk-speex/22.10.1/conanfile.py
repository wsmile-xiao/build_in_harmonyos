#!/usr/bin/env python3
"""Conan recipe — asterisk-speex 22.10.1 (Asterisk codec_speex module).

Asterisk Speex codec module — codec_speex.so.
Uses the full Asterisk autotools build (configure + make). The source
tarball is the canonical Asterisk release; this recipe packages only the
Speex codec module.

codec_speex needs libspeex (speex/speex.h + speex_encode) and
libspeexdsp (speex/speex_preprocess.h + speex_preprocess_ctl). Both are
published on ohpcd as speex/1.2.1 and speexdsp/1.2.1; `generate()` copies
their include/lib/pkgconfig into a private prefix (build_folder/prefix),
rewrites the .pc prefix, then passes CPPFLAGS/LDFLAGS/PKG_CONFIG_PATH so
configure's AST_EXT_LIB_CHECK([SPEEX]/[SPEEXDSP]) succeed and menuselect
enables codec_speex.

Asterisk configure also hard-requires libedit (pkg-config probe), libuuid
(e2fsprogs), jansson >= 2.11 and sqlite3; menuselect's own configure
hard-requires libxml2 (its build needs xml2-config). Those deps are
provisioned the same way (from published ohpcd packages). format_ogg_speex
is excluded (it would need <ogg/ogg.h> / libogg); func_speex is not built
(only the codecs/ subdir is compiled). The packaged deliverable is exactly
codec_speex.so.
"""

import os
import shutil
import time

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, chdir, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

SYS_PREFIX = os.environ.get("DEFAULT_PREFIX") or os.path.join(os.path.expanduser("~"), "usr", "local")


def _copy_tree(src, dst):
    if os.path.isdir(src):
        os.makedirs(dst, exist_ok=True)
        for name in os.listdir(src):
            s = os.path.join(src, name)
            d = os.path.join(dst, name)
            if os.path.isdir(s):
                _copy_tree(s, d)
            else:
                os.makedirs(os.path.dirname(d), exist_ok=True)
                if not os.path.exists(d):
                    shutil.copy2(s, d)


def _ensure_dep_present(prefix, pkg_dirs, rels):
    """Copy header/lib files from a dependency package folder into the prefix.

    pkg_dirs: list of (pkg_dir, rel_path) pairs; rels: list of rel paths to verify.
    """
    missing = [r for r in rels if not os.path.exists(os.path.join(prefix, r))]
    if not missing:
        return
    for pkg_dir, rel in pkg_dirs:
        src = os.path.join(pkg_dir, rel)
        if os.path.exists(src):
            _copy_tree(src, os.path.join(prefix, rel))
    still = [r for r in rels if not os.path.exists(os.path.join(prefix, r))]
    if still:
        raise ConanInvalidConfiguration(
            "dependency provisioning did not provide: " + ", ".join(still))


def _fix_pc_prefix(pc_path, prefix):
    """Rewrite the .pc `prefix=` line to the private SYS_PREFIX.

    The packages' .pc files are built with `prefix=/` (or the package build
    prefix) which does not exist on the build machine; pkg-config would hand
    configure bogus -I/-L paths. Rewrite unconditionally.
    """
    if not os.path.isfile(pc_path):
        return
    import re as _re
    data = open(pc_path, encoding="utf-8", errors="replace").read()
    data = _re.sub(r"(?m)^prefix=.*$", f"prefix={prefix}", data, count=1)
    open(pc_path, "w", encoding="utf-8").write(data)


def _ensure_speex(prefix, speex_pkg_dir):
    """Provision speex into the private prefix (speex/speex.h + libspeex.a)."""
    inc = os.path.join(prefix, "include", "speex", "speex.h")
    libs = [os.path.join(prefix, "lib", "libspeex.a")]
    pcs = [os.path.join(prefix, "lib", "pkgconfig", "speex.pc")]
    if os.path.exists(inc) and all(os.path.exists(p) for p in libs + pcs):
        _fix_pc_prefix(pcs[0], prefix)
        return
    if not speex_pkg_dir or not os.path.isdir(speex_pkg_dir):
        raise ConanInvalidConfiguration(
            "speex not found in prefix and no speex dependency package folder available")
    _ensure_dep_present(prefix, [(speex_pkg_dir, "include"), (speex_pkg_dir, "lib")],
                        ["include/speex/speex.h", "lib/libspeex.a",
                         "lib/pkgconfig/speex.pc"])
    _fix_pc_prefix(pcs[0], prefix)


def _ensure_speexdsp(prefix, speexdsp_pkg_dir):
    """Provision speexdsp into the private prefix (speex_preprocess.h + libspeexdsp.a)."""
    inc = os.path.join(prefix, "include", "speex", "speex_preprocess.h")
    libs = [os.path.join(prefix, "lib", "libspeexdsp.a")]
    pcs = [os.path.join(prefix, "lib", "pkgconfig", "speexdsp.pc")]
    if os.path.exists(inc) and all(os.path.exists(p) for p in libs + pcs):
        _fix_pc_prefix(pcs[0], prefix)
        return
    if not speexdsp_pkg_dir or not os.path.isdir(speexdsp_pkg_dir):
        raise ConanInvalidConfiguration(
            "speexdsp not found in prefix and no speexdsp dependency package folder available")
    _ensure_dep_present(prefix, [(speexdsp_pkg_dir, "include"), (speexdsp_pkg_dir, "lib")],
                        ["include/speex/speex_preprocess.h", "lib/libspeexdsp.a",
                         "lib/pkgconfig/speexdsp.pc"])
    _fix_pc_prefix(pcs[0], prefix)


def _ensure_libedit(prefix, edit_pkg_dir):
    """Provision libedit into the private prefix (Asterisk configure REQUIRES it)."""
    inc = os.path.join(prefix, "include", "histedit.h")
    libs = [os.path.join(prefix, "lib", "libedit.a")]
    pcs = [os.path.join(prefix, "lib", "pkgconfig", "libedit.pc")]
    if os.path.exists(inc) and all(os.path.exists(p) for p in libs + pcs):
        _fix_pc_prefix(pcs[0], prefix)
        return
    if not edit_pkg_dir or not os.path.isdir(edit_pkg_dir):
        raise ConanInvalidConfiguration(
            "libedit not found in prefix and no libedit dependency package folder available")
    _ensure_dep_present(prefix, [(edit_pkg_dir, "include"), (edit_pkg_dir, "lib")],
                        ["include/histedit.h", "include/editline/readline.h",
                         "lib/libedit.a", "lib/pkgconfig/libedit.pc"])
    _fix_pc_prefix(pcs[0], prefix)


def _ensure_libxml2(prefix, xml_pkg_dir):
    """Provision libxml2 into the private prefix (menuselect sub-configure REQUIRES it)."""
    inc = os.path.join(prefix, "include", "libxml2", "libxml", "parser.h")
    libs = [os.path.join(prefix, "lib", "libxml2.so")]
    pcs = [os.path.join(prefix, "lib", "pkgconfig", "libxml-2.0.pc")]
    if os.path.exists(inc) and all(os.path.exists(p) for p in libs + pcs):
        _fix_pc_prefix(pcs[0], prefix)
        return
    if not xml_pkg_dir or not os.path.isdir(xml_pkg_dir):
        raise ConanInvalidConfiguration(
            "libxml2 not found in prefix and no libxml2 dependency package folder available")
    pc_src = None
    for root, _, files in os.walk(xml_pkg_dir):
        if "libxml-2.0.pc" in files:
            pc_src = os.path.join(root, "libxml-2.0.pc")
            break
    if pc_src:
        pc_dir = os.path.join(prefix, "lib", "pkgconfig")
        os.makedirs(pc_dir, exist_ok=True)
        std_pc = os.path.join(pc_dir, "libxml-2.0.pc")
        if not os.path.exists(std_pc):
            shutil.copy2(pc_src, std_pc)
        _fix_pc_prefix(std_pc, prefix)
    _copy_tree(os.path.join(xml_pkg_dir, "include", "libxml2"),
               os.path.join(prefix, "include", "libxml2"))
    _ensure_dep_present(prefix, [(xml_pkg_dir, "lib")],
                        ["lib/libxml2.so"])


def _ensure_ncurses(prefix, ncurses_pkg_dir):
    """Provision ncurses into the private prefix (libedit.pc Libs.private=-ltinfo)."""
    have_w = os.path.exists(os.path.join(prefix, "lib", "libncursesw.a"))
    have_t = os.path.exists(os.path.join(prefix, "lib", "libtinfo.a"))
    if have_w and have_t:
        return
    if not ncurses_pkg_dir or not os.path.isdir(ncurses_pkg_dir):
        raise ConanInvalidConfiguration(
            "ncurses not found in prefix and no ncurses dependency package folder available")
    _copy_tree(os.path.join(ncurses_pkg_dir, "include"),
               os.path.join(prefix, "include"))
    _copy_tree(os.path.join(ncurses_pkg_dir, "lib"),
               os.path.join(prefix, "lib"))
    tinfo = os.path.join(prefix, "lib", "libtinfo.a")
    if not os.path.exists(tinfo) and os.path.exists(os.path.join(prefix, "lib", "libncursesw.a")):
        shutil.copy2(os.path.join(prefix, "lib", "libncursesw.a"), tinfo)


def _ensure_uuid(prefix, uuid_pkg_dir):
    """Provision libuuid into the private prefix (Asterisk configure REQUIRES uuid_generate_random)."""
    inc = os.path.join(prefix, "include", "uuid", "uuid.h")
    libs = [os.path.join(prefix, "lib", "libuuid.a")]
    pcs = [os.path.join(prefix, "lib", "pkgconfig", "uuid.pc")]
    if os.path.exists(inc) and all(os.path.exists(p) for p in libs + pcs):
        _fix_pc_prefix(pcs[0], prefix)
        return
    if not uuid_pkg_dir or not os.path.isdir(uuid_pkg_dir):
        raise ConanInvalidConfiguration(
            "uuid not found in prefix and no e2fsprogs dependency package folder available")
    _ensure_dep_present(prefix, [(uuid_pkg_dir, "include"), (uuid_pkg_dir, "lib")],
                        ["include/uuid/uuid.h", "lib/libuuid.a", "lib/pkgconfig/uuid.pc"])
    _fix_pc_prefix(pcs[0], prefix)


def _ensure_jansson(prefix, jansson_pkg_dir):
    """Provision jansson into the private prefix (Asterisk configure REQUIRES jansson >= 2.11)."""
    inc = os.path.join(prefix, "include", "jansson.h")
    libs = [os.path.join(prefix, "lib", "libjansson.so")]
    pcs = [os.path.join(prefix, "lib", "pkgconfig", "jansson.pc")]
    if os.path.exists(inc) and all(os.path.exists(p) for p in libs + pcs):
        _fix_pc_prefix(pcs[0], prefix)
        return
    if not jansson_pkg_dir or not os.path.isdir(jansson_pkg_dir):
        raise ConanInvalidConfiguration(
            "jansson not found in prefix and no jansson dependency package folder available")
    _ensure_dep_present(prefix, [(jansson_pkg_dir, "include"), (jansson_pkg_dir, "lib")],
                        ["include/jansson.h", "lib/libjansson.so", "lib/pkgconfig/jansson.pc"])
    _fix_pc_prefix(pcs[0], prefix)


def _ensure_sqlite3(prefix, sqlite_pkg_dir):
    """Provision sqlite3 into the private prefix (Asterisk configure REQUIRES SQLite3)."""
    inc = os.path.join(prefix, "include", "sqlite3.h")
    libs = [os.path.join(prefix, "lib", "libsqlite3.a")]
    pcs = [os.path.join(prefix, "lib", "pkgconfig", "sqlite3.pc")]
    if os.path.exists(inc) and all(os.path.exists(p) for p in libs):
        _ensure_sqlite3_pc(prefix)
        return
    if not sqlite_pkg_dir or not os.path.isdir(sqlite_pkg_dir):
        raise ConanInvalidConfiguration(
            "sqlite3 not found in prefix and no sqlite3 dependency package folder available")
    _ensure_dep_present(prefix, [(sqlite_pkg_dir, "include"), (sqlite_pkg_dir, "lib")],
                        ["include/sqlite3.h", "lib/libsqlite3.a"])
    _ensure_sqlite3_pc(prefix)


def _ensure_sqlite3_pc(prefix):
    """Generate a sqlite3.pc shim (sqlite3 package ships no .pc; configure probes it)."""
    pc_dir = os.path.join(prefix, "lib", "pkgconfig")
    os.makedirs(pc_dir, exist_ok=True)
    pc = os.path.join(pc_dir, "sqlite3.pc")
    if not os.path.exists(pc):
        with open(pc, "w", encoding="utf-8") as f:
            f.write("prefix=%s\n" % prefix)
            f.write("exec_prefix=${prefix}\nlibdir=${exec_prefix}/lib\n"
                    "includedir=${prefix}/include\nName: SQLite\n"
                    "Description: SQLite3 shim for Asterisk\n"
                    "Version: 3.49.1\nLibs: -L${libdir} -lsqlite3\n"
                    "Cflags: -I${includedir}\n")


def _drop_umask_077(path):
    try:
        data = open(path, "r", encoding="utf-8", errors="replace").read()
        if "umask 077" in data:
            open(path, "w", encoding="utf-8").write(data.replace("umask 077", "umask 022"))
    except Exception:
        pass


class AsteriskSpeexConan(ConanFile):
    name = "asterisk-speex"
    version = "22.10.1"
    description = "Asterisk Speex codec module (codec_speex.so)"
    license = "GPL-2.0-only"
    homepage = "https://www.asterisk.org/"
    url = "https://www.asterisk.org/"

    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*", "packaging/*"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"asterisk-speex does not support os={self.settings.os}")

    def requirements(self):
        # speex + speexdsp are what codec_speex links against; libedit/libuuid/
        # jansson/sqlite3 are hard requirements of the Asterisk main configure;
        # libxml2 is required by the menuselect sub-configure; ncurses provides
        # tinfo symbols referenced by libedit. All published on ohpcd.
        self.requires("speex/1.2.1")
        self.requires("speexdsp/1.2.1")
        self.requires("libedit/20240808")
        self.requires("libxml2/2.15.3")
        self.requires("ncurses/6.6")
        self.requires("e2fsprogs/1.47.4")
        self.requires("jansson/2.15.1.1")
        self.requires("sqlite3/3.49.1")

    def layout(self):
        basic_layout(self, src_folder="src")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        speex_pkg = None
        speexdsp_pkg = None
        edit_pkg = None
        xml_pkg = None
        ncurses_pkg = None
        uuid_pkg = None
        jansson_pkg = None
        sqlite_pkg = None
        try:
            speex_pkg = self.dependencies["speex"].package_folder
        except Exception:
            pass
        try:
            speexdsp_pkg = self.dependencies["speexdsp"].package_folder
        except Exception:
            pass
        try:
            edit_pkg = self.dependencies["libedit"].package_folder
        except Exception:
            pass
        try:
            xml_pkg = self.dependencies["libxml2"].package_folder
        except Exception:
            pass
        try:
            ncurses_pkg = self.dependencies["ncurses"].package_folder
        except Exception:
            pass
        try:
            uuid_pkg = self.dependencies["e2fsprogs"].package_folder
        except Exception:
            pass
        try:
            jansson_pkg = self.dependencies["jansson"].package_folder
        except Exception:
            pass
        try:
            sqlite_pkg = self.dependencies["sqlite3"].package_folder
        except Exception:
            pass
        _ensure_speex(self._prefix(), speex_pkg)
        _ensure_speexdsp(self._prefix(), speexdsp_pkg)
        _ensure_libedit(self._prefix(), edit_pkg)
        _ensure_libxml2(self._prefix(), xml_pkg)
        _ensure_ncurses(self._prefix(), ncurses_pkg)
        _ensure_uuid(self._prefix(), uuid_pkg)
        _ensure_jansson(self._prefix(), jansson_pkg)
        _ensure_sqlite3(self._prefix(), sqlite_pkg)

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--build=x86_64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-ohos",
            "--without-pjproject",
            "--with-pjproject-bundled=no",
        ])
        inc_dir = os.path.join(self._prefix(), "include")
        lib_dir = os.path.join(self._prefix(), "lib")
        pc_dir = os.path.join(lib_dir, "pkgconfig")
        if os.path.isdir(inc_dir):
            tc.configure_args.append(f"CPPFLAGS=-I{inc_dir}")
        if os.path.isdir(lib_dir):
            tc.configure_args.append(f"LDFLAGS=-L{lib_dir} -Wl,-rpath,{lib_dir}")
        tc.configure_args.append(f"PKG_CONFIG_PATH={pc_dir}")
        tc.generate()

    def _prefix(self):
        """Private dependency injection prefix (build_folder/prefix).

        CI workers and this machine share SYS_PREFIX (~/usr/local); injecting
        deps there pollutes the shared tree and different package revisions
        between machines cause unreproducible link failures. The private
        build_folder keeps every build self-contained.
        """
        return os.path.join(self.build_folder, "prefix")

    def _fs_env(self):
        tmpdir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        env.define("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # menuselect's MAKE_MENUSELECT hardcodes CC="cc" (BUILD_CC); no `cc` on OHOS
        env.define("CC", "/data/service/hnp/bin/clang")
        env.define("BUILD_CC", "/data/service/hnp/bin/clang")
        env.define("HOST_CC", "/data/service/hnp/bin/clang")
        return env

    def _configure_args(self) -> list:
        args = [
            "--prefix=/",
            "--build=x86_64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-ohos",
            "--without-pjproject",
            "--with-pjproject-bundled=no",
        ]
        inc_dir = os.path.join(self._prefix(), "include")
        lib_dir = os.path.join(self._prefix(), "lib")
        pc_dir = os.path.join(lib_dir, "pkgconfig")
        if os.path.isdir(inc_dir):
            args.append(f"CPPFLAGS=-I{inc_dir}")
        if os.path.isdir(lib_dir):
            args.append(f"LDFLAGS='-L{lib_dir} -Wl,-rpath,{lib_dir}'")
        args.append(f"PKG_CONFIG_PATH={pc_dir}")
        # --with-speex/--with-speexdsp make AST_EXT_LIB_CHECK emit
        #   SPEEX_INCLUDE=-I<prefix>/include, SPEEX_LIB=-L<prefix>/lib -lspeex -lm
        # exactly like the exploration-verified manual build.
        args.append(f"--with-speex={self._prefix()}")
        args.append(f"--with-speexdsp={self._prefix()}")
        # CI worker sandbox (hishell_hap domain) forbids running conftest
        # executables -> "checking whether the C compiler works... no".
        # ac_cv_prog_cc_works=yes skips that probe (cross-compiling makes all
        # AC_TRY_RUN no-ops; the .so product is not an executable).
        args.append("ac_cv_prog_cc_works=yes")
        return args

    def build(self):
        apply_conandata_patches(self)
        # HMDFS rejects 0600 temp files (MAC): umask 077 -> 022 in configure scripts.
        _drop_umask_077(os.path.join(self.source_folder, "configure"))
        _drop_umask_077(os.path.join(self.source_folder, "menuselect", "configure"))
        env = self._fs_env()
        # HMDFS avoidance (E052/E060): build in a work dir under build_folder
        # (conan's own cache dirs are not executable for config.status temp files).
        work = os.path.join(self.build_folder, "worktree")
        if os.path.exists(work):
            shutil.rmtree(work)
        os.makedirs(os.path.dirname(work), exist_ok=True)
        shutil.copytree(self.source_folder, work,
                        ignore=shutil.ignore_patterns(".tmp"))
        with env.vars(self, scope="build").apply():
            with chdir(self, work):
                # HMDFS intermittent issue: config.status first run can fail to
                # write ./confXXXXXX/subs1.awk (Permission denied); rerunning
                # succeeds. Retry configure, then rerun config.status.
                cfg = f"./configure {' '.join(self._configure_args())}"
                makeopts = os.path.join(work, "makeopts")
                for attempt in range(1, 4):
                    try:
                        self.run(cfg, env="conanbuild")
                    except Exception:
                        pass
                    if os.path.isfile(makeopts) and os.path.getsize(makeopts) > 1000:
                        break
                    time.sleep(5)
                    cs = os.path.join(work, "config.status")
                    if os.path.isfile(cs):
                        try:
                            self.run("./config.status", env="conanbuild")
                        except Exception:
                            pass
                    if os.path.isfile(makeopts) and os.path.getsize(makeopts) > 1000:
                        break
                cs = os.path.join(work, "config.status")
                if os.path.isfile(cs):
                    try:
                        self.run("./config.status", env="conanbuild")
                    except Exception:
                        time.sleep(3)
                        self.run("./config.status", env="conanbuild")
                # Pre-configure the menuselect sub-project (CC=clang + libxml2
                # via PKG_CONFIG_PATH), with HMDFS intermittent retries.
                ms_dir = os.path.join(work, "menuselect")
                if os.path.isfile(os.path.join(ms_dir, "configure")):
                    ms_mk = os.path.join(ms_dir, "makeopts")
                    pc_dir = os.path.join(self._prefix(), "lib", "pkgconfig")
                    for _ in range(3):
                        try:
                            self.run(
                                f"cd menuselect && "
                                f"CC=/data/service/hnp/bin/clang "
                                f"PKG_CONFIG_PATH={pc_dir} ./configure "
                                f"--build=x86_64-unknown-linux-gnu "
                                f"--host=aarch64-unknown-linux-ohos "
                                f"ac_cv_prog_cc_works=yes",
                                env="conanbuild",
                            )
                        except Exception:
                            pass
                        if os.path.isfile(ms_mk) and os.path.getsize(ms_mk) > 100:
                            break
                        time.sleep(3)
                        cs = os.path.join(ms_dir, "config.status")
                        if os.path.isfile(cs):
                            try:
                                self.run("cd menuselect && ./config.status",
                                         env="conanbuild")
                            except Exception:
                                pass
                        if os.path.isfile(ms_mk) and os.path.getsize(ms_mk) > 100:
                            break
                # Inject the exploration-verified makeopts/makedeps AFTER the
                # menuselect pre-configuration (otherwise the menuselect binary
                # regenerates a default makeopts that enables every module).
                # The injected file uses exclusion-list semantics: every codec
                # except codec_speex is disabled. Future timestamp prevents make
                # from regenerating it.
                for fn in ("menuselect.makeopts", "menuselect.makedeps"):
                    src = None
                    candidates = []
                    esf = getattr(self, "export_sources_folder", "") or ""
                    for base in (esf, self.source_folder):
                        if base:
                            candidates.append(os.path.join(base, "packaging", fn))
                    for cand in candidates:
                        if os.path.isfile(cand):
                            src = cand
                            break
                    if not src:
                        # 只允许从 exports_sources（packaging/*）解析；不引入本机路径兜底
                        raise FileNotFoundError(
                            f"{fn} 缺失：packaging/ 未随源导出"
                            f"（已尝试: {candidates}）")
                    dst = os.path.join(work, fn)
                    shutil.copy2(src, dst)
                    os.utime(dst, (time.time() + 86400 * 365,) * 2)
                # Generate the version/build headers the top-level Makefile
                # normally creates via `make include/asterisk/buildopts.h` etc.
                # (a bare `make -C codecs` skips the top-level makeopts targets).
                # buildopts.h is included by autoconfig.h -> asterisk.h.
                hdrs = [
                    "build_tools/make_buildopts_h > include/asterisk/buildopts.h",
                    "build_tools/make_build_h > include/asterisk/build.h",
                    "build_tools/make_defaults_h > defaults.h",
                ]
                for h in hdrs:
                    try:
                        self.run(f"cd {work} && ./{h}", env="conanbuild")
                    except Exception:
                        pass
                # Build only the codecs/ subdir. The module .so does not link
                # the asterisk core, so we skip main/ and utils entirely.
                pc_dir = os.path.join(self._prefix(), "lib", "pkgconfig")
                mk_vars = (f"BUILD_CC=/data/service/hnp/bin/clang "
                           f"PKG_CONFIG_PATH={pc_dir}")
                # ASTCFLAGS (user flags) carries -I<work>/include for asterisk.h;
                # SOLINK=-shared is required because the sub-make does not import
                # the top-level Makefile where SOLINK is normally defined.
                try:
                    self.run(f"make -j1 -C codecs SUBDIR=codecs ASTTOPDIR={work} "
                             f"ASTCFLAGS=-I{work}/include SOLINK=-shared "
                             f"{mk_vars} all", env="conanbuild")
                except Exception:
                    self.run(f"make -j1 -C codecs SUBDIR=codecs ASTTOPDIR={work} "
                             f"ASTCFLAGS=-I{work}/include SOLINK=-shared "
                             f"{mk_vars} codec_speex.so", env="conanbuild")
        # Copy the product back to source_folder for package() and debugging
        so_src = os.path.join(work, "codecs", "codec_speex.so")
        if os.path.isfile(so_src):
            dst_codecs = os.path.join(self.source_folder, "codecs")
            os.makedirs(dst_codecs, exist_ok=True)
            shutil.copy2(so_src, os.path.join(dst_codecs, "codec_speex.so"))

    def package(self):
        import glob
        candidates = [
            os.path.join(self.build_folder, "codecs", "codec_speex.so"),
            os.path.join(self.source_folder, "codecs", "codec_speex.so"),
        ]
        src_so = next((p for p in candidates if os.path.exists(p)), None)
        if src_so and os.path.isfile(src_so):
            copy(self, "codec_speex.so", src=os.path.dirname(src_so),
                 dst=os.path.join(self.package_folder, "lib", "asterisk", "modules"))
        else:
            # Fallback: make install then prune to only the speex module
            autotools = Autotools(self)
            env = self._fs_env()
            with env.vars(self, scope="build").apply():
                autotools.install(args=["-j1"])
            keep = os.path.join(self.package_folder, "lib", "asterisk", "modules", "codec_speex.so")
            for mod in glob.glob(os.path.join(self.package_folder, "lib", "asterisk", "modules", "*.so")):
                if os.path.abspath(mod) != os.path.abspath(keep):
                    try:
                        os.remove(mod)
                    except Exception:
                        pass
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib/asterisk/modules"]
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = []
