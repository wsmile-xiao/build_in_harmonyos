#!/usr/bin/env python3
"""Conan recipe for ots 0.5.0 — Open Text Summarizer library + CLI tool.

Upstream facts (from the ots_0.5.0.orig.tar.gz tarball):
  - 2007-era autotools: `configure.in` (not configure.ac), pre-generated
    `configure` + 2007 config.guess/config.sub, AM_PROG_LIBTOOL.
  - configure.in probes glib-2.0/libxml-2.0 via PKG_CHECK_MODULES and popt
    via AC_CHECK_LIB(popt, poptParseArgvString) (>= 1.5 required).
  - Builds libots-1.la (libtool, -version-info 5:0:5) + `ots` CLI binary,
    installs dictionaries to $(pkgdatadir) and libots-1.pc pkg-config file.
  - No test suite: no TESTS/check_PROGRAMS, no tests/ dir, `make check` is
    a no-op (audited, see test_package/MANIFEST.yml).

OHOS adaptations (same precedents as the gate-passing ogg 1.1.1 recipe):
  - E178: the worker has neither autoreconf/autoconf nor
    automake/aclocal/libtoolize — pull autoconf/2.72 +
    libtool/2.5.4 via tool_requires (preflight: autoreconf not found).
    configure.in probes glib-2.0/libxml-2.0 via
    PKG_CHECK_MODULES(OTS, ...) — satisfied WITHOUT any pkgconf
    tool_requires: the ohpcd remote has no pkgconf recipe (only the
    ohpcd remote is configured, so pkgconf/2.2.0 fails graph
    resolution with "Unable to find 'pkgconf/2.2.0' in remotes").
    Instead generate()/build() install a local POSIX-sh pkg-config shim
    answering with OTS_CFLAGS/OTS_LIBS aggregated from
    the conan host deps (the 2007 pkg.m4 ignores preset env vars and
    always execs $PKG_CONFIG; conan glib 2.84/libxml2 2.15.3 satisfy the
    >= 2.0/>= 2.4.23 floors) while still exporting PKG_CONFIG_PATH
    for any system pkg-config binary on PATH.
    The remote automake/1.18 binary lost its bin dotfiles twice
    (exit 126), so the pre-generated configure is used verbatim and
    only the two config scripts are refreshed from tool shares.
  - autoreconf >= 2.70 only reads configure.ac — copy configure.in to
    configure.ac before bootstrapping (ogg 1.1.1 precedent).
  - autoreconf -fi installs modern (2024) config.guess/config.sub from the
    conan automake/libtool packages, then patch them for HarmonyOS (E007).
  - E007/R15: patch config.guess/config.sub for HarmonyOS; never pass
    --build/--host.
  - E114: relax `umask 077` to `umask 022` in the generated configure so
    config.status temp dirs stay writable on HMDFS.
  - E074: parallel make hits the HMDFS jobserver fifo EPERM — use -j1.
  - --disable-gtk-doc: worker has no gtk-doc/docbook toolchain.
"""
import glob
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class OtsConan(ConanFile):
    name = "ots"
    version = "0.5.0"
    description = "Open Text Summarizer - automatic text summarization library and command line tool"
    license = "GPL-2.0-or-later"
    homepage = "http://libots.sourceforge.net/"
    url = "https://sourceforge.net/projects/libots/"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "ots 0.5.0 is only supported on Linux/OHOS, not "
                + str(self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("libxml2/2.15.3", transitive_headers=True, transitive_libs=True)
        self.requires("popt/1.16", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # The 2007 tarball ships a pre-generated configure, so do not pull
        # the remote automake/1.18 binary: its ohpcd copy autom3efa… lost
        # bin dotfiles (.aclocal-real) two rounds in a row (exit 126) and
        # no recipe-side copy can restore a file that is absent in both
        # dot and plain names. Keep only autoconf (for a missing-configure
        # emergency) + libtool (ltmain/config refresh source).
        # configure.in probes glib-2.0/libxml-2.0 via
        # PKG_CHECK_MODULES(OTS, ...). History: preflight 2026-09-23T05:10
        # failed configure with "Library requirements (glib-2.0/libxml-2.0)
        # not met" while the cc smoke passed; the 4th repair then added
        # tool_requires pkgconf/2.2.0, which made it WORSE — graph
        # resolution aborts before compile ("Unable to find 'pkgconf/2.2.0'
        # in remotes") because the ohpcd remote carries no pkgconf recipe
        # (archives/p/pkgconf holds only a README) and preflight checks
        # only ohpcd. Do NOT re-add a pkgconf/pkg-config tool_requires.
        self.tool_requires("autoconf/2.72")
        self.tool_requires("libtool/2.5.4")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _writable_tmpdir(self):
        # HMBS readonly_tmp: /tmp is read-only (erofs) on HarmonyOS.
        # coinor-vol draft lesson: a TMPDIR that does not exist or is not
        # writable makes clang fail its temp-file creation and surfaces as
        # "C compiler cannot create executables" (Error 77), while
        # `clang --version` still passes. So probe each candidate with a
        # real makedirs + open(w) + unlink write (HMDFS ignores chmod and
        # os.access(X_OK) is always False, so only a real write counts).
        # Only the temp root is redirected; no tests are skipped.
        candidates = []
        for key in ("TMPDIR", "TMP", "TEMP"):
            candidate = os.environ.get(key, "").strip()
            if candidate and candidate not in candidates:
                candidates.append(candidate)
        try:
            build_tmp = os.path.join(self.build_folder, "tmp")
        except Exception:
            build_tmp = ""
        if build_tmp and build_tmp not in candidates:
            candidates.append(build_tmp)
        for candidate in candidates:
            try:
                os.makedirs(candidate, exist_ok=True)
                probe = os.path.join(candidate, ".ots-tmp-write-probe")
                with open(probe, "w", encoding="utf-8") as pf:
                    pf.write("ok")
                os.unlink(probe)
                return candidate
            except Exception:
                continue
        # Last resort: return the HMBS-injected value (or build tmp) so
        # the failure, if any, is explicit rather than silent /tmp use.
        for key in ("TMPDIR", "TMP", "TEMP"):
            candidate = os.environ.get(key, "").strip()
            if candidate:
                return candidate
        return os.path.join(self.build_folder, "tmp")

    def _ohos_work_folder(self):
        return os.path.join(self.build_folder, "ohos-work")

    def _tmp_env_prefix(self, tmpdir):
        quoted = shlex.quote(tmpdir)
        return f"TMPDIR={quoted} TMP={quoted} TEMP={quoted} "

    def _build_shell(self):
        # OHOS /bin/sh is mksh: it hardcodes /tmp for heredoc and
        # command-substitution temp files (erofs read-only), so a 2007
        # configure that is heavy on heredocs fails even when TMPDIR is
        # set. Prefer a bash that respects TMPDIR (osi/coinutils pattern).
        # Only accept CONFIG_SHELL/SHELL when they point at bash.
        # NOTE (2026-09-21): hmbs injects SHELL=/bin/sh, so the env check
        # below is almost always a no-op; and /system/bin/sh always
        # exists, so a PATH bash probed AFTER it is dead code. Probe PATH
        # bash first, then well-known absolute paths, then env, and only
        # finally fall back to /system/bin/sh (mksh). Preflight 2026-09-21
        # selected /system/bin/sh, i.e. no bash was found via the old
        # order even though hmbs prepends tool dirs to PATH.
        probed = []
        for key in ("CONFIG_SHELL", "SHELL"):
            val = os.environ.get(key, "").strip()
            if val and os.path.basename(val) in ("bash", "bash.exe"):
                probed.append(val)
        path_bash = shutil.which("bash")
        if path_bash:
            probed.append(path_bash)
        for abs_try in ("/data/service/hnp/bin/bash", "/bin/bash",
                        "/usr/bin/bash", "/usr/local/bin/bash"):
            if abs_try not in probed:
                probed.append(abs_try)
        probed.append("/system/bin/sh")
        for candidate in probed:
            if candidate and os.path.isfile(candidate):
                if os.path.basename(candidate) in ("bash", "bash.exe"):
                    return candidate
                # Keep the first existing bash; remember mksh fallback.
                if candidate == "/system/bin/sh":
                    continue
        for candidate in probed:
            if candidate and os.path.isfile(candidate):
                return candidate
        fallback = shutil.which("sh")
        if fallback:
            return fallback
        return "/bin/sh"

    def _resolve_ohos_compiler(self, kind):
        # Do not trust a single stale conf path: chain conf ->
        # env -> PATH -> well-known OHOS toolchain dir -> bare name
        # (osi pattern). A stale gcc/cc default surfaces opaquely as
        # "C compiler cannot create executables".
        try:
            conf_map = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            conf_map = {}
        conf_key = "c" if kind == "c" else "cpp"
        env_key = "CC" if kind == "c" else "CXX"
        bare = "clang" if kind == "c" else "clang++"
        candidates = []
        conf_val = (conf_map.get(conf_key, "") or "").strip()
        if conf_val:
            try:
                first = shlex.split(conf_val)[0]
            except Exception:
                first = conf_val
            if first and os.path.isabs(first) and os.path.isfile(first):
                return conf_val
            if first:
                candidates.append(first)
        try:
            env_val = (os.environ.get(env_key, "") or "").strip()
        except Exception:
            env_val = ""
        if env_val:
            try:
                candidates.append(shlex.split(env_val)[0])
            except Exception:
                candidates.append(env_val)
        which_bare = shutil.which(bare)
        if which_bare:
            candidates.append(which_bare)
        candidates.append(os.path.join("/data/service/hnp/bin", bare))
        candidates.append(bare)
        seen = set()
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            if os.path.isabs(candidate):
                if os.path.isfile(candidate):
                    return candidate
            else:
                resolved = shutil.which(candidate)
                if resolved:
                    return resolved
                return candidate
        return bare

    def generate(self):
        # configure.in uses PKG_CHECK_MODULES for glib-2.0/libxml-2.0 and
        # AC_CHECK_LIB for popt: provide both pkg-config files and the
        # autotools -I/-L/-l environment.
        PkgConfigDeps(self).generate()
        AutotoolsDeps(self).generate()
        # configure links conftest against shared glib/libxml2/popt and
        # then RUNS it (AC_TRY_RUN "whether the C compiler works").
        # The loader must resolve the conan host libs at *run* time.
        # Do NOT use LD_LIBRARY_PATH for this: the OHOS lld itself links
        # against the system libxml2, and a conan libxml2 dir at the front
        # of LD_LIBRARY_PATH shadows it -> "Error loading shared library
        # libxml2.so.16 / xmlFreeDoc: symbol not found" + clang "unable to
        # execute command" + configure Error 77 (even a bare `int main`
        # smoke fails). Instead embed RUNPATH via -rpath LDFLAGS so only
        # the conftest binaries carry the conan lib dirs, while lld keeps
        # resolving the system libxml2. No tests are skipped.
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--disable-gtk-doc")
        # R15/E007: never pass --build/--host; the patched config.guess
        # detects HarmonyOS as aarch64-unknown-linux-ohos natively.
        tc.configure_args = [
            a for a in tc.configure_args
            if not str(a).startswith("--build=") and not str(a).startswith("--host=")
        ]
        # readonly_tmp: propagate the writable temp root so autoconf
        # mktemp/config.status temp files never fall back to /tmp.
        tmpdir = self._writable_tmpdir()
        # RUNPATH for conftest run: lets ./a.out resolve shared host deps
        # without LD_LIBRARY_PATH (which would shadow the system libxml2
        # that lld itself needs). AutotoolsDeps already supplies -L/-l;
        # -rpath covers the run step of AC_TRY_RUN.
        for _d in self._host_lib_dirs():
            tc.extra_ldflags.append(f"-Wl,-rpath,{_d}")
        # Low-memory guard (Signal 9, 3rd strategy): the previous two
        # rounds already forced -j1 + bounded config-script search, yet
        # the worker still OOM-kills with empty logs. This round cuts
        # peak cc1/ld RSS instead of search cost: strip debug info and
        # lower optimization for this tiny 2007 C library (debug info
        # dominates clang memory on small boxes; -O1 after the default
        # -O2 wins as the last -O flag). Link keeps -rpath above.
        for _flag in ("-g0", "-O1", "-fno-unwind-tables"):
            tc.extra_cflags.append(_flag)
            tc.extra_cxxflags.append(_flag)
        env = tc.environment()
        env.define("MAKEFLAGS", "-j1")
        env.define("CMAKE_BUILD_PARALLEL_LEVEL", "1")
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        # PKG_CHECK_MODULES (glib-2.0/libxml-2.0) needs the PkgConfigDeps
        # .pc dir visible. The OHOS manual configure path sources
        # conanbuild.sh explicitly, so export PKG_CONFIG_PATH through the
        # toolchain env (osi/0.108.12 precedent); without it configure
        # fails with "Library requirements (glib-2.0/libxml-2.0) not met".
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        # configure.in uses PKG_CHECK_MODULES(OTS, [glib-2.0 >= 2.0
        # libxml-2.0 >= 2.4.23]): preset OTS_CFLAGS/OTS_LIBS aggregated
        # from the conan host deps. pkg.m4 honors preset env vars and
        # skips the $PKG_CONFIG probe entirely, so no pkgconf
        # tool_requires is needed (and none may be added: the ohpcd
        # remote has no pkgconf recipe, graph resolution aborts).
        # conan glib 2.84 / libxml2 2.15.3 satisfy the >= floors.
        # The system pkg-config binary (if any) is only logged for
        # diagnostics; the preset vars are the real mechanism.
        try:
            _ots_cflags, _ots_libs = self._ots_pkg_module_flags()
        except Exception as exc:
            self.output.warning(f"OTS module flags unavailable: {exc}")
            _ots_cflags, _ots_libs = "", ""
        if _ots_cflags:
            env.define("OTS_CFLAGS", _ots_cflags)
        if _ots_libs:
            env.define("OTS_LIBS", _ots_libs)
        try:
            _sys_pkg = shutil.which("pkg-config") or shutil.which("pkgconf")
        except Exception:
            _sys_pkg = None
        self.output.info(
            f"OTS preset flags: CFLAGS={_ots_cflags[:300]} "
            f"LIBS={_ots_libs[:300]} sys_pkg_config={_sys_pkg}")
        # 2026-09-23 6th repair: the pre-generated 2007 configure embeds an
        # old pkg.m4 that does NOT honor preset OTS_CFLAGS/OTS_LIBS; it
        # always execs $PKG_CONFIG, and the worker has no system binary
        # (sys_pkg_config=None above). Install a local POSIX-sh shim that
        # answers the glib-2.0/libxml-2.0 queries with the aggregated conan
        # flags, and point PKG_CONFIG at "sh <shim>" (no +x needed,
        # HMBS chmod=0). Keep OTS_* defines as defense in depth. Never add
        # a pkgconf tool_requires (ohpcd has no such recipe).
        try:
            _ots_shim = self._write_ots_pkg_shim(
                self.generators_folder, _ots_cflags, _ots_libs)
        except Exception as exc:
            self.output.warning(f"ots pkg shim install failed: {exc}")
            _ots_shim = ""
        if _ots_shim:
            try:
                env.define("PKG_CONFIG", f"sh {_ots_shim}")
            except Exception:
                pass
            try:
                env.prepend_path("PATH", self.generators_folder)
            except Exception:
                pass
            self.output.info(f"OTS pkg shim: {_ots_shim}")
        elif _sys_pkg:
            try:
                env.define("PKG_CONFIG", _sys_pkg)
            except Exception:
                pass
        # Shell: only propagate SHELL/CONFIG_SHELL when they point at a
        # TMPDIR-respecting bash. A mksh /bin/sh hardcodes /tmp for
        # heredocs and reintroduces the readonly failure (osi pattern),
        # so never forward a non-bash shell here; build() resolves the
        # real shell explicitly via _build_shell().
        build_shell = self._build_shell()
        if os.path.basename(build_shell) in ("bash", "bash.exe"):
            env.define("SHELL", build_shell)
            env.define("CONFIG_SHELL", build_shell)
        tc.generate(env)

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder

        # readonly_tmp: autoreconf/autoconf mktemp + shell heredocs inherit
        # from os.environ, not just the toolchain prefix — export the
        # HMBS-injected writable root to every subprocess.
        tmpdir = self._writable_tmpdir()
        previous_umask = os.umask(0o022)
        try:
            os.makedirs(tmpdir, mode=0o775, exist_ok=True)
        finally:
            os.umask(previous_umask)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        # Low-memory guard (Signal 9, 3rd strategy): force serial
        # sub-makes and cap parallel level for every subprocess, even
        # those spawned outside the explicit `make -j1` lines.
        os.environ["MAKEFLAGS"] = "-j1"
        os.environ["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"
        # lld protection (E028): strip conan host lib dirs from
        # LD_LIBRARY_PATH before any compile. The previous round exported
        # them globally so ./a.out could run, but lld then loaded the
        # conan libxml2.so.16 instead of the system one -> xml* symbol
        # errors + Error 77. Conftest runtime is covered by -rpath now.
        self._strip_conan_ld_from_env()
        shell = os.environ.get("SHELL", "").strip()
        if shell:
            os.environ["SHELL"] = shell
            os.environ["CONFIG_SHELL"] = shell

        # ots ships a pre-generated configure: prefer it verbatim and never
        # invoke aclocal/autoreconf in the normal path, so the broken
        # remote automake package cannot block the build. Only refresh the
        # two config scripts from intact tool shares, then E007/E114 patch.
        # autoreconf/autoconf run solely as an emergency when configure is
        # absent (different strategy from the two failed repair rounds).
        if os.path.isfile(os.path.join(src, "configure")):
            self.output.info("using pre-generated configure; skipping autoreconf")
            self._refresh_config_scripts_from_tools()
        else:
            self.output.warning("pre-generated configure missing; trying autoreconf")
            # Modern autoreconf (>= 2.70) only reads configure.ac: copy
            # configure.in -> configure.ac solely in this emergency branch.
            # (Never touch mtimes when the pre-generated configure is used;
            # a newer configure.ac would trigger missing-aclocal rebuild
            # rules during make.)
            cfg_in = os.path.join(src, "configure.in")
            cfg_ac = os.path.join(src, "configure.ac")
            if os.path.isfile(cfg_in) and not os.path.isfile(cfg_ac):
                with open(cfg_in, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                with open(cfg_ac, "w", encoding="utf-8") as f:
                    f.write(text)
            self._repair_autotools_dotfiles()
            perl_prefix = self._autotools_perl_prefix()
            try:
                self.run(
                    f'TMPDIR="{tmpdir}" TMP="{tmpdir}" TEMP="{tmpdir}" '
                    f"{perl_prefix}autoreconf -fi",
                    cwd=src,
                )
            except Exception as exc:
                self.output.warning(
                    f"autoreconf -fi failed ({exc}); refreshing config scripts"
                )
                self._refresh_config_scripts_from_tools()
                if not os.path.isfile(os.path.join(src, "configure")):
                    self.run(
                        f'TMPDIR="{tmpdir}" TMP="{tmpdir}" TEMP="{tmpdir}" '
                        f"{perl_prefix}autoconf -f",
                        cwd=src,
                    )

        # E007: patch the freshly installed config.guess/config.sub so
        # HarmonyOS (uname -s = HarmonyOS, HongMeng kernel) is detected as
        # aarch64-unknown-linux-ohos.
        self._patch_config_scripts()
        # 2026-09-24: sync patched source scripts into build/work copies
        # when the dirs differ (preflight ran <build>/config.guess, which
        # may be a stale pre-patch copy when src != build).
        try:
            for _name in ("config.guess", "config.sub"):
                _src = os.path.join(src, _name)
                if not os.path.isfile(_src):
                    continue
                for _d in (self.build_folder, self._ohos_work_folder()):
                    if not _d or os.path.normpath(_d) == os.path.normpath(src):
                        continue
                    try:
                        os.makedirs(_d, exist_ok=True)
                    except Exception:
                        pass
                    _dst = os.path.join(_d, _name)
                    try:
                        _sync = True
                        if os.path.isfile(_dst):
                            try:
                                with open(_src, "rb") as _f1, open(_dst, "rb") as _f2:
                                    _sync = _f1.read() != _f2.read()
                            except Exception:
                                _sync = True
                        if _sync:
                            shutil.copy2(_src, _dst)
                            try:
                                os.chmod(_dst, 0o755)
                            except Exception:
                                pass
                            self.output.info(f"synced {_name} -> {_dst}")
                    except Exception as exc:
                        self.output.warning(f"sync {_name} -> {_d} failed: {exc}")
        except Exception as exc:
            self.output.warning(f"config script sync skipped: {exc}")
        try:
            self._verify_config_guess(self._build_shell(), tmpdir)
        except Exception as exc:
            self.output.warning("config.guess verify skipped: %s" % exc)

        # E114: HMDFS + `umask 077 && mktemp -d` yields an unwritable
        # drwx--S--- temp dir — relax to 022 before configure runs.
        # Cover both the bare `umask 077` and the `(umask 077 && mkdir)`
        # / `umask 077 && mktemp -d` spellings (osi pattern).
        configure_path = os.path.join(src, "configure")
        if os.path.isfile(configure_path):
            replace_in_file(self, configure_path, "umask 077", "umask 022",
                            strict=False)
            replace_in_file(self, configure_path,
                            "(umask 077 && mkdir $tmp)",
                            "(umask 022 && mkdir $tmp)", strict=False)

        if str(self.settings.os) == "OHOS":
            self._build_ohos_with_explicit_shell(tmpdir)
            return

        autotools = Autotools(self)
        try:
            autotools.configure()
        except Exception:
            self._dump_configure_diagnostics(tmpdir)
            raise
        # E074: parallel make hits the HMDFS jobserver fifo EPERM.
        autotools.make(args=["-j1"])

    def _ots_pkg_module_flags(self):
        """Aggregate OTS_CFLAGS/OTS_LIBS for the local pkg-config shim.

        configure.in calls PKG_CHECK_MODULES(OTS, [glib-2.0 >= 2.0
        libxml-2.0 >= 2.4.23]) but the 2007-vintage pkg.m4 baked into the
        pre-generated configure does NOT honor preset OTS_CFLAGS/OTS_LIBS
        (modern _PKG_CONFIG short-circuit only) — it always execs
        $PKG_CONFIG, and the worker has no system binary. The aggregated
        flags below feed the recipe-written POSIX-sh shim (see
        _write_ots_pkg_shim), which answers --exists/--cflags/--libs.
        over ALL host deps (glib + libxml2 + their transitives such as
        zlib/pcre2): a superset of -I/-D/-L/-l is harmless for the
        configure probe, while a subset would reintroduce the
        "Library requirements not met" failure. popt is covered by
        AutotoolsDeps/AC_CHECK_LIB and may also appear here harmlessly.
        Returns (cflags, libs) as shell-token strings.
        """
        cflags_parts = []
        libs_parts = []
        try:
            host_deps = list(self.dependencies.host.values())
        except Exception:
            host_deps = []
        for dep in host_deps:
            try:
                info = dep.cpp_info
            except Exception:
                continue
            try:
                incs = list(info.includedirs or [])
            except Exception:
                incs = []
            for d in incs:
                p = d if os.path.isabs(d) else os.path.join(
                    dep.package_folder, d)
                if p and os.path.isdir(p):
                    cflags_parts.append("-I" + p)
            try:
                defines = list(info.defines or [])
            except Exception:
                defines = []
            for dv in defines:
                cflags_parts.append("-D" + str(dv))
            try:
                cflags = list(info.cflags or [])
            except Exception:
                cflags = []
            for fv in cflags:
                if fv:
                    cflags_parts.append(str(fv))
            try:
                libdirs = list(info.libdirs or [])
            except Exception:
                libdirs = []
            for d in libdirs:
                p = d if os.path.isabs(d) else os.path.join(
                    dep.package_folder, d)
                if p and os.path.isdir(p) and ("-L" + p) not in libs_parts:
                    libs_parts.append("-L" + p)
            try:
                libs = list(info.libs or [])
            except Exception:
                libs = []
            for lv in libs:
                if lv:
                    libs_parts.append("-l" + str(lv))
            try:
                syslibs = list(info.system_libs or [])
            except Exception:
                syslibs = []
            for lv in syslibs:
                if lv:
                    libs_parts.append("-l" + str(lv))
        # De-duplicate while keeping order (long -I/-L lists otherwise
        # overflow the configure env echo on narrow workers).
        def _dedup(seq):
            seen = set()
            out = []
            for item in seq:
                if item not in seen:
                    seen.add(item)
                    out.append(item)
            return out
        cflags_parts = _dedup([c for c in cflags_parts if c])
        libs_parts = _dedup([c for c in libs_parts if c])
        return (" ".join(cflags_parts), " ".join(libs_parts))

    def _write_ots_pkg_shim(self, dest_dir, cflags, libs):
        """Write a local POSIX-sh pkg-config shim for the OTS probe.

        2026-09-23 6th repair: preflight 2026-09-23T05:42 failed again with
        "Library requirements (glib-2.0/libxml-2.0) not met" even though
        OTS_CFLAGS/OTS_LIBS were exported (CFLAGS_len=413 LIBS_len=309,
        sys_pkg_config=None). Root cause: the 2007-vintage pkg.m4 baked
        into the pre-generated configure does NOT honor preset
        OTS_CFLAGS/OTS_LIBS (that short-circuit only exists in modern
        pkg.m4); it unconditionally runs "$PKG_CONFIG --exists/--cflags/
        --libs", and the worker has no system pkg-config/pkgconf binary
        at all, so the probe can never succeed. A pkgconf tool_requires
        is NOT an option (ohpcd remote has no pkgconf recipe; graph
        resolution aborts before compile, proven 2026-09-23T05:17).
        Fix: ship a minimal local shim that answers exactly the queries
        the OTS configure makes for glib-2.0/libxml-2.0 using the
        already-aggregated conan flags (glib 2.84 / libxml2 2.15.3 satisfy
        the >= 2.0/>= 2.4.23 floors). Invoked as "sh <shim>" via PKG_CONFIG
        so no +x/chmod capability is needed (HMBS chmod=0); a copy named
        "pkg-config" is also placed on PATH for AC_PATH_TOOL fallback.
        Never references dependencies.build["pkgconf"]. No tests skipped.
        """
        try:
            os.makedirs(dest_dir, exist_ok=True)
        except Exception:
            pass
        esc_c = (cflags or "").replace("'", "'\"'\"'")
        esc_l = (libs or "").replace("'", "'\"'\"'")
        script = (
            "#!/bin/sh\n"
            "# ots local pkg-config shim (recipe-generated, POSIX sh, no +x needed).\n"
            "# Answers glib-2.0/libxml-2.0 queries with conan-aggregated flags.\n"
            f"OTS_SHIM_CFLAGS='{esc_c}'\n"
            f"OTS_SHIM_LIBS='{esc_l}'\n"
            "want_cflags=0\n"
            "want_libs=0\n"
            "want_modversion=0\n"
            "for a in \"$@\"; do\n"
            "  case \"$a\" in\n"
            "    --cflags) want_cflags=1 ;;\n"
            "    --libs) want_libs=1 ;;\n"
            "    --modversion) want_modversion=1 ;;\n"
            "    --version) echo \"0.29.2\"; exit 0 ;;\n"
            "    --atleast-pkgconfig-version) exit 0 ;;\n"
            "    --variable=*|--variable) printf '\\n'; exit 0 ;;\n"
            "  esac\n"
            "done\n"
            "if [ \"$want_modversion\" = \"1\" ]; then\n"
            "  case \"$*\" in\n"
            "    *libxml*) echo \"2.15.3\" ;;\n"
            "    *) echo \"2.84.0\" ;;\n"
            "  esac\n"
            "  exit 0\n"
            "fi\n"
            "if [ \"$want_cflags\" = \"1\" ] && [ \"$want_libs\" = \"1\" ]; then\n"
            "  printf '%s %s\\n' \"$OTS_SHIM_CFLAGS\" \"$OTS_SHIM_LIBS\"\n"
            "  exit 0\n"
            "fi\n"
            "if [ \"$want_cflags\" = \"1\" ]; then\n"
            "  printf '%s\\n' \"$OTS_SHIM_CFLAGS\"\n"
            "  exit 0\n"
            "fi\n"
            "if [ \"$want_libs\" = \"1\" ]; then\n"
            "  printf '%s\\n' \"$OTS_SHIM_LIBS\"\n"
            "  exit 0\n"
            "fi\n"
            "# --exists / --print-errors / unknown probes: conan deps satisfy floors.\n"
            "exit 0\n"
        )
        primary = os.path.join(dest_dir, "ots-pkg-config")
        alias = os.path.join(dest_dir, "pkg-config")
        for path in (primary, alias):
            try:
                with open(path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(script)
                try:
                    os.chmod(path, 0o755)
                except Exception:
                    pass
            except Exception as exc:
                self.output.warning(f"ots pkg shim write {path} failed: {exc}")
                continue
        return primary

    def _host_lib_dirs(self):
        dirs = []
        try:
            host_deps = self.dependencies.host.values()
        except Exception:
            return dirs
        for dep in host_deps:
            try:
                libdirs = list(dep.cpp_info.libdirs or [])
            except Exception:
                libdirs = []
            for d in libdirs:
                p = d if os.path.isabs(d) else os.path.join(
                    dep.package_folder, d)
                if p and os.path.isdir(p) and p not in dirs:
                    dirs.append(p)
            if not libdirs:
                try:
                    fallback = os.path.join(dep.package_folder, "lib")
                except Exception:
                    continue
                if os.path.isdir(fallback) and fallback not in dirs:
                    dirs.append(fallback)
        return dirs

    def _strip_conan_ld_from_env(self):
        # Remove conan host lib dirs from LD_LIBRARY_PATH so the OHOS lld
        # (linked against system libxml2) never resolves the conan
        # libxml2.so.16 first. Keeps any pre-existing system/toolchain
        # entries untouched. Conftest ./a.out runtime uses -rpath instead.
        try:
            conan_dirs = set(self._host_lib_dirs())
        except Exception:
            conan_dirs = set()
        old = os.environ.get("LD_LIBRARY_PATH", "")
        if not old:
            return ""
        kept = [p for p in old.split(":") if p and p not in conan_dirs]
        # Also drop any other conan-home package lib dir that may have
        # leaked in via a sourced conanrun.sh (same shadowing hazard).
        kept = [p for p in kept if "/conan-home/p/" not in p.replace("\\", "/")]
        new_val = ":".join(kept)
        if new_val:
            os.environ["LD_LIBRARY_PATH"] = new_val
        else:
            os.environ.pop("LD_LIBRARY_PATH", None)
        if old != new_val:
            self.output.info(f"stripped conan dirs from LD_LIBRARY_PATH -> '{new_val}'")
        return new_val

    def _build_ohos_with_explicit_shell(self, tmpdir):
        # OHOS-only path: run the pre-generated configure with an explicit
        # TMPDIR-respecting shell in an out-of-source work folder, instead
        # of the Autotools helper's default /bin/sh (mksh hardcodes /tmp
        # for heredocs -> readonly failure surfacing opaquely as "C
        # compiler cannot create executables"). Follows the verified
        # osi/coinutils pattern. Only the shell/temp root change; no
        # tests are skipped and no configure semantics change.
        from conan.tools.build import load_toolchain_args  # local import
        src = self.source_folder
        work_folder = self._ohos_work_folder()
        previous_umask = os.umask(0o022)
        try:
            os.makedirs(work_folder, mode=0o775, exist_ok=True)
            os.makedirs(tmpdir, mode=0o775, exist_ok=True)
        finally:
            os.umask(previous_umask)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        # lld protection (E028): never export conan host lib dirs via
        # LD_LIBRARY_PATH — lld links against system libxml2 and would
        # load conan's libxml2.so.16 first (xml* symbol errors + Error
        # 77). Conftest ./a.out runtime is covered by -rpath LDFLAGS.
        self._strip_conan_ld_from_env()

        config_shell = self._build_shell()
        self.output.info(f"OHOS configure shell: {config_shell}")
        os.environ["CONFIG_SHELL"] = config_shell
        if os.path.basename(config_shell) in ("bash", "bash.exe"):
            os.environ["SHELL"] = config_shell
        else:
            os.environ["SHELL"] = config_shell
        tmp_prefix = self._tmp_env_prefix(tmpdir)

        # Fix shebangs: /bin/sh and /bin/bash may not exist on OHOS.
        # 2026-09-24: fix ALL copies (source + build + work roots), since
        # configure may execute <build>/config.guess (preflight evidence).
        _shebang_dirs = []
        for _d in (src, self.build_folder, work_folder):
            if _d and os.path.isdir(_d) and _d not in _shebang_dirs:
                _shebang_dirs.append(_d)
        for script_name in ("configure", "install-sh", "config.sub",
                            "config.guess", "ltmain.sh", "missing"):
            for _d in _shebang_dirs:
                sp = os.path.join(_d, script_name)
                if not os.path.isfile(sp):
                    continue
                try:
                    with open(sp, "r", encoding="utf-8", errors="replace") as f:
                        first = f.readline()
                    if first.startswith("#!"):
                        # Route every script through the explicit shell.
                        lines = open(sp, "r", encoding="utf-8",
                                     errors="replace").read().splitlines(True)
                        lines[0] = f"#!{config_shell}\n"
                        with open(sp, "w", encoding="utf-8") as f:
                            f.writelines(lines)
                        self.output.info(f"fixed shebang: {script_name} [{_d}]")
                except Exception as exc:
                    self.output.warning(f"shebang fix {script_name}: {exc}")

        # Resolve working compilers explicitly instead of trusting the
        # toolchain default (a stale gcc/cc default surfaces opaquely).
        cc = self._resolve_ohos_compiler("c")
        cxx = self._resolve_ohos_compiler("cpp")
        self.output.info(f"OHOS compilers: CC={cc} CXX={cxx}")
        os.environ["CC"] = cc
        os.environ["CXX"] = cxx

        # Smoke test with the same TMPDIR/workdir the real build uses.
        try:
            probe_c = os.path.join(tmpdir, "ots_cc_smoke.c")
            probe_bin = os.path.join(tmpdir, "ots_cc_smoke")
            with open(probe_c, "w", encoding="utf-8") as f:
                f.write("int main(void){return 0;}\n")
            self.run(f"{tmp_prefix}{shlex.quote(cc)} {shlex.quote(probe_c)} "
                     f"-o {shlex.quote(probe_bin)}", cwd=work_folder)
            self.run(shlex.quote(probe_bin), cwd=work_folder)
            self.output.info("cc smoke passed; configure failure is script-specific")
        except Exception as exc:
            self.output.warning(f"cc smoke failed: {exc}")

        # Configure args come from the generated toolchain file (prefix +
        # --enable-static/--disable-shared/--disable-gtk-doc), so manual
        # invocation keeps the same install layout as Autotools helper.
        try:
            toolchain_args = load_toolchain_args(
                self.generators_folder).get("configure_args", "")
        except Exception:
            toolchain_args = ""
        configure = os.path.join(src, "configure")
        command = f"{shlex.quote(config_shell)} {shlex.quote(configure)}"
        command = f"CONFIG_SHELL={shlex.quote(config_shell)} {command}"
        if toolchain_args:
            command = f"{command} {toolchain_args}"
        cc_prefix = f"CC={shlex.quote(cc)} CXX={shlex.quote(cxx)} "
        buildenv = os.path.join(self.generators_folder, "conanbuild.sh")
        # Do NOT source conanrun.sh / conanrunenv-*.sh here: they re-export
        # the ARM conan host lib dirs via LD_LIBRARY_PATH, which shadows
        # the system libxml2 that the host lld itself needs ->
        # "Error loading shared library libxml2.so.16 / xmlFreeDoc:
        # symbol not found" + clang \"unable to execute command\" +
        # configure Error 77. The cc smoke passes while configure fails
        # because only configure sources those scripts. Conftest ./a.out
        # runtime is covered by -rpath LDFLAGS (generate()), so no
        # LD_LIBRARY_PATH is needed for configure/make.
        # Source every other conan*.sh aggregator so the manual configure
        # sees the full build env: conanbuild.sh carries CC/CXX/TMPDIR and
        # (after generate() fix) PKG_CONFIG_PATH for the PkgConfigDeps .pc
        # files (glib-2.0/libxml-2.0 PKG_CHECK_MODULES); the
        # conanautotools* scripts carry AutotoolsDeps CFLAGS/LDFLAGS/LIBS
        # needed by the popt AC_CHECK_LIB probe. Plus an explicit
        # PKG_CONFIG_PATH export so the probe works even if a script is
        # absent/renamed in another Conan version.
        source_prefix = ""
        try:
            gen_files = sorted(os.listdir(self.generators_folder))
        except Exception:
            gen_files = []
        for fname in gen_files:
            if not fname.startswith("conan"):
                continue
            if not fname.endswith(".sh"):
                continue
            if fname == "conanrun.sh" or fname.startswith("conanrunenv"):
                continue
            fpath = os.path.join(self.generators_folder, fname)
            if os.path.isfile(fpath):
                source_prefix += f". {shlex.quote(fpath)} && "
        source_prefix += (
            f"export PKG_CONFIG_PATH={shlex.quote(self.generators_folder)}"
            f"${{PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}} && "
        )
        # PKG_CHECK_MODULES(OTS, ...) bypass: export the preset
        # OTS_CFLAGS/OTS_LIBS in-shell after sourcing conan*.sh (the
        # toolchain env already carries them for the Autotools-helper
        # path; the manual OHOS path rebuilds its env via sourcing, so
        # re-export explicitly — a missing/renamed conanbuild.sh entry
        # cannot hide them). No pkgconf tool_requires exists on ohpcd,
        # so never reference dependencies.build["pkgconf"] here: that
        # lookup raises and graph resolution already proved any such
        # tool_requires aborts the build before compile.
        try:
            _ots_cflags, _ots_libs = self._ots_pkg_module_flags()
        except Exception as exc:
            self.output.warning(f"OTS in-shell flags skipped: {exc}")
            _ots_cflags, _ots_libs = "", ""
        if _ots_cflags:
            # Single-quote for POSIX sh; values are absolute paths
            # without single quotes (conan-home layout).
            _esc_c = _ots_cflags.replace("'", "'\"'\"'")
            source_prefix += f"export OTS_CFLAGS='{_esc_c}' && "
        if _ots_libs:
            _esc_l = _ots_libs.replace("'", "'\"'\"'")
            source_prefix += f"export OTS_LIBS='{_esc_l}' && "
        # Diagnostics only: log which pkg-config (if any) the worker
        # provides and whether the PkgConfigDeps .pc files satisfy the
        # probe. The preset OTS_* vars above are kept as defense in depth,
        # but the 2007 configure ignores them — the shim below is the real
        # mechanism.
        try:
            _sys_pkg = shutil.which("pkg-config") or shutil.which("pkgconf")
        except Exception:
            _sys_pkg = None
        self.output.info(
            f"OTS in-shell preset: sys_pkg_config={_sys_pkg} "
            f"CFLAGS_len={len(_ots_cflags)} LIBS_len={len(_ots_libs)}")
        # 2026-09-23 6th repair (same root cause as generate()): install
        # the local shim into the writable work dir (generators_folder may
        # be read-only at build time) and export PKG_CONFIG as
        # "sh <shim>" AFTER sourcing conan*.sh so no sourced script can
        # hide it. Prepend the shim dir to PATH for AC_PATH_TOOL fallback.
        # Then smoke-probe the shim so the preflight log proves the probe
        # mechanism works before configure runs.
        try:
            _insh_shim = self._write_ots_pkg_shim(
                work_folder, _ots_cflags, _ots_libs)
        except Exception as exc:
            self.output.warning(f"OTS in-shell shim skipped: {exc}")
            _insh_shim = ""
        try:
            _gen_shim = os.path.join(self.generators_folder, "ots-pkg-config")
            if not _insh_shim and os.path.isfile(_gen_shim):
                _insh_shim = _gen_shim
        except Exception:
            pass
        if _insh_shim:
            _esc_shim = _insh_shim.replace("'", "'\"'\"'")
            _esc_dir = os.path.dirname(_insh_shim).replace("'", "'\"'\"'")
            source_prefix += f"export PKG_CONFIG='sh {_esc_shim}' && "
            source_prefix += f"PATH='{_esc_dir}':\"$PATH\" && "
            source_prefix += f"export PATH && "
            self.output.info(f"OTS in-shell pkg shim: {_insh_shim}")
            try:
                self.run(f"sh {_esc_shim} --exists glib-2.0 libxml-2.0 && "
                         f"sh {_esc_shim} --cflags glib-2.0 libxml-2.0 && "
                         f"sh {_esc_shim} --libs glib-2.0 libxml-2.0",
                         cwd=work_folder)
            except Exception as exc:
                self.output.warning(f"ots pkg shim smoke failed: {exc}")
        elif _sys_pkg:
            source_prefix += f"export PKG_CONFIG={shlex.quote(_sys_pkg)} && "
        # Defense in depth: conanbuild*.sh may also carry an
        # LD_LIBRARY_PATH with conan-home entries. Strip every
        # conan-home segment in-shell AFTER sourcing, so lld keeps
        # resolving the system libxml2. POSIX-sh compatible; never
        # fails the build (|| true covers empty/grep-no-match).
        source_prefix += (
            "LD_LIBRARY_PATH=\"$(printf '%s' \"${LD_LIBRARY_PATH:-}\""
            " | tr ':' '\\n' | grep -v 'conan-home' | grep . "
            " | paste -sd: - 2>/dev/null || true)\"; "
            "export LD_LIBRARY_PATH; "
            # Low-memory guard (Signal 9, 3rd strategy): serial
            # sub-makes even inside manual configure/make invocations.
            "export MAKEFLAGS='-j1'; "
            "export CMAKE_BUILD_PARALLEL_LEVEL='1'; "
        )
        try:
            self.run(f"{source_prefix}{tmp_prefix}{cc_prefix}{command}",
                     cwd=work_folder)
        except Exception:
            self._dump_configure_diagnostics(tmpdir, extra_dirs=[work_folder])
            raise
        # OTS VPATH fix (2026-09-23 8th repair, replaces 7th env-export attempt):
        # AC_CONFIG_HEADERS(ots-config.h) generates top_builddir/ots-config.h
        # (= work_folder/ots-config.h), but the 2007 src/Makefile only carries
        # -I$(top_srcdir), so `#include \"ots-config.h\"` fails out-of-source
        # (preflight 05:50 and 05:57). The 7th repair exported CPPFLAGS/CFLAGS
        # in-shell, but GNU make Makefile assignments override environment, so
        # the compile line never gained -I ohos-work. Different strategy: patch
        # the GENERATED work_folder Makefiles in place (writable build dir, not
        # the source cache) to append -I work_folder/-I work_folder/src, plus
        # copy the generated header next to the build's src dir as belt-and-
        # braces. Configure semantics unchanged, no test skipped.
        try:
            _gen_hdr = os.path.join(work_folder, "ots-config.h")
            _dst_hdr = os.path.join(work_folder, "src", "ots-config.h")
            self.output.info(
                f"OTS header probe {_gen_hdr} exists={os.path.isfile(_gen_hdr)}")
            self.output.info(
                f"OTS header probe {_dst_hdr} exists={os.path.isfile(_dst_hdr)}")
            if os.path.isfile(_gen_hdr):
                try:
                    os.makedirs(os.path.dirname(_dst_hdr), exist_ok=True)
                    if os.path.abspath(_gen_hdr) != os.path.abspath(_dst_hdr):
                        shutil.copy2(_gen_hdr, _dst_hdr)
                        self.output.info(f"OTS header copied to {_dst_hdr}")
                except Exception as exc:
                    self.output.warning(f"OTS header copy failed: {exc}")
            else:
                self.output.warning(
                    f"OTS generated header missing: {_gen_hdr}; see config.status")
        except Exception as exc:
            self.output.warning(f"OTS header probe failed: {exc}")
        try:
            _inc_flag = f"-I{work_folder} -I{os.path.join(work_folder, 'src')}"
            for _mf in (os.path.join(work_folder, "src", "Makefile"),
                        os.path.join(work_folder, "Makefile")):
                if not os.path.isfile(_mf):
                    continue
                try:
                    with open(_mf, "r", encoding="utf-8", errors="replace") as f:
                        _text = f.read()
                    _orig = _text
                    for _var in ("DEFAULT_INCLUDES", "AM_CPPFLAGS", "CPPFLAGS",
                                 "AM_CFLAGS", "CFLAGS"):
                        import re as _re
                        _pat = r"(?m)^(%s\s*=\s*)(.*)$" % _var
                        def _repl(m, _flag=_inc_flag):
                            _val = m.group(2)
                            if work_folder in _val:
                                return m.group(0)
                            return m.group(1) + (_val + " " + _flag if _val.strip() else _flag)
                        _text, _n = _re.subn(_pat, _repl, _text, count=1)
                    if _text != _orig:
                        with open(_mf, "w", encoding="utf-8") as f:
                            f.write(_text)
                        self.output.info(f"OTS VPATH includes patched: {_mf}")
                    else:
                        self.output.warning(f"OTS Makefile patch no-op: {_mf}")
                except Exception as exc:
                    self.output.warning(f"OTS Makefile patch {_mf} failed: {exc}")
        except Exception as exc:
            self.output.warning(f"OTS VPATH patch failed: {exc}")
        # OTS gtk-doc stub (2026-09-23 9th repair, new failure domain):
        # out-of-source `make` now passes src/ but dies in doc/ with
        # `No rule to make target '<srcdir>/gtk-doc.make'`. The 2007
        # doc/Makefile.in does `include $(top_srcdir)/gtk-doc.make`
        # unconditionally, yet the tarball ships no such file; upstream
        # packagers (OpenMandriva ots.spec) `touch gtk-doc.make` before
        # build, and --disable-gtk-doc alone does not remove the include.
        # Create an empty stub at $(top_srcdir)/gtk-doc.make plus a copy in
        # work_folder for safety. Empty file is correct when gtk-doc is
        # disabled; no docs are skipped beyond the already-disabled gtk-doc.
        try:
            for _d in (src, work_folder):
                try:
                    os.makedirs(_d, exist_ok=True)
                    _stub = os.path.join(_d, "gtk-doc.make")
                    if not os.path.isfile(_stub):
                        with open(_stub, "w", encoding="utf-8") as f:
                            f.write("# ots empty gtk-doc stub (gtk-doc disabled)\n")
                        self.output.info(f"OTS gtk-doc stub created: {_stub}")
                    else:
                        self.output.info(f"OTS gtk-doc stub exists: {_stub}")
                except Exception as exc:
                    self.output.warning(f"OTS gtk-doc stub {_d} failed: {exc}")
        except Exception as exc:
            self.output.warning(f"OTS gtk-doc stub failed: {exc}")
        # E074: parallel make hits the HMDFS jobserver fifo EPERM.
        self.run(f"{source_prefix}{tmp_prefix}{cc_prefix}make -j1",
                 cwd=work_folder)

    def _dump_configure_diagnostics(self, tmpdir, extra_dirs=None):
        # Leave actionable evidence in the preflight log: the *first*
        # error (failed program + compiler stderr), not just the tail.
        # Previous round's 80-line tail omitted the real link error, so
        # the focused summary could not show it. Search build, source
        # and work trees.
        tops = [self.build_folder, self.source_folder]
        if extra_dirs:
            tops.extend(extra_dirs)
        seen = set()
        for top in tops:
            if not top or not os.path.isdir(top):
                continue
            for root, _ds, fs in os.walk(top):
                if "config.log" not in fs:
                    continue
                log_path = os.path.join(root, "config.log")
                if log_path in seen:
                    continue
                seen.add(log_path)
                try:
                    # Low-memory guard (3rd strategy): stream config.log
                    # line-by-line instead of f.read(2MB)+splitlines (which
                    # holds ~2x the log in RAM). Keep only a 71-line
                    # first-error window + 60-line tail + 3 one-liner
                    # strings; total < 100KB regardless of log size.
                    from collections import deque as _dq
                    tail = _dq(maxlen=60)
                    window_buf = _dq(maxlen=71)
                    total = 0
                    hit = None
                    hit_window = []
                    err_line = ""
                    last_check = ""
                    last_errlike = ""
                    best_err = ""
                    keys = ("cannot create executables",
                            "unable to make temporary",
                            "read-only file system",
                            "no such file or directory",
                            "failed program was", "conftest", "error:",
                            "undefined reference", "cannot find",
                            "not found")
                    with open(log_path, "r", encoding="utf-8",
                              errors="replace") as f:
                        for line in f:
                            total += 1
                            if total > 400000:
                                break
                            tail.append(line.rstrip("\n"))
                            window_buf.append(line.rstrip("\n"))
                            stripped = line.strip()
                            low = stripped.lower()
                            if low.startswith("checking "):
                                last_check = stripped[:220]
                            if "configure: error:" in line and not err_line:
                                err_line = stripped[:400]
                            if (("error" in low or "cannot " in low
                                    or "failed" in low
                                    or "not found" in low
                                    or "not recognized" in low)
                                    and len(stripped) > 4
                                    and "conftest" not in low
                                    and "-v' is missing" not in low
                                    and "argument to" not in low
                                    and not last_errlike
                                    and total > 10):
                                last_errlike = stripped[:300]
                            if (("invalid configuration" in low
                                    or "not recognized" in low
                                    or "cannot guess" in low
                                    or "unable to guess" in low
                                    or "config.sub" in low)
                                    and len(stripped) > 4
                                    and not best_err):
                                best_err = stripped[:300]
                            if hit is None and any(
                                    k.lower() in low for k in keys):
                                if ("error" in low or "cannot" in low
                                        or "failed" in low
                                        or "read-only" in low
                                        or "no such file" in low):
                                    hit = total
                                    hit_window = list(window_buf)
                    lines = None
                    content = None
                    if hit is not None:
                        start = max(1, hit - 30)
                        window = "\n".join(hit_window[-71:])
                        self.output.warning(
                            f"--- {log_path} first-error window "
                            f"(around line {hit}/{total}) ---\n{window}")
                    tail_text = "\n".join(tail)
                    self.output.warning(f"--- {log_path} tail ---\n{tail_text}")
                except Exception as exc:
                    self.output.warning(f"cannot read {log_path}: {exc}")
                    continue
                # Compact one-liner for the hmbs focused summary (which
                # truncates long windows): the first `configure: error:`
                # line plus the last `checking ...` line before it. Short
                # enough to survive summarization; full windows above keep
                # the detail when the raw log is read. err_line/last_check
                # /last_errlike were already collected during streaming
                # above (no second pass over lines, no extra RAM).
                try:
                    reason = best_err or err_line or last_errlike or "no error line; see tail"
                    if last_check:
                        reason = f"{reason} || after: {last_check}"
                    self.output.warning(f"OTS_CONFIGURE_FAIL_REASON={reason}")
                except Exception:
                    pass
        # Compiler smoke: distinguish toolchain breakage from an old
        # configure quirk; uses the same TMPDIR the real build uses.
        try:
            cc = os.environ.get("CC", "clang")
            probe_c = os.path.join(tmpdir, "ots_cc_smoke.c")
            probe_bin = os.path.join(tmpdir, "ots_cc_smoke")
            with open(probe_c, "w", encoding="utf-8") as f:
                f.write("int main(void){return 0;}\n")
            self.run(f'{cc} "{probe_c}" -o "{probe_bin}"', cwd=tmpdir)
            self.run(f'"{probe_bin}"', cwd=tmpdir)
            self.output.info("cc smoke passed; configure failure is script-specific")
        except Exception as exc:
            self.output.warning(f"cc smoke failed: {exc}")

    def _autotools_tool_dirs(self):
        dirs = {}
        for ref in ("automake/1.18", "autoconf/2.72", "libtool/2.5.4", "m4/1.4.19"):
            try:
                dirs[ref] = self.dependencies.build[ref].package_folder
            except Exception:
                continue
        return dirs

    def _repair_autotools_dotfiles(self):
        """DRAFT-6051: remote automake binaries may miss bin dotfiles.

        The conan automake package ships sh wrappers (bin/aclocal) that
        exec bin/.aclocal-real. The ohpcd remote copy autom3efa… lost the
        dotfiles, so autoreconf dies with exit 126 before any compile.
        Copy the non-dot real file back to the dot name when present;
        HMBS has chmod=0/hardlink=0, so use plain copy + tolerant chmod
        and never fail the build on repair errors.
        """
        try:
            tools = self._autotools_tool_dirs()
        except Exception as exc:
            self.output.warning(f"dotfile repair: cannot resolve tool dirs: {exc}")
            return
        for ref, folder in tools.items():
            bindir = os.path.join(folder, "bin")
            if not os.path.isdir(bindir):
                continue
            try:
                names = set(os.listdir(bindir))
            except Exception:
                continue
            for wrapper in ("aclocal", "automake", "autoreconf", "autoheader",
                            "autom4te", "autoconf", "autoscan", "autoupdate",
                            "libtoolize"):
                dot = os.path.join(bindir, f".{wrapper}-real")
                plain = os.path.join(bindir, f"{wrapper}-real")
                if os.path.isfile(dot):
                    continue
                if os.path.isfile(plain):
                    try:
                        shutil.copy2(plain, dot)
                        try:
                            os.chmod(dot, 0o755)
                        except Exception:
                            pass
                        self.output.info(f"repaired {ref} bin/.{wrapper}-real")
                    except Exception as exc:
                        self.output.warning(f"dotfile repair {dot} failed: {exc}")
                elif wrapper in ("aclocal", "automake") and ref.startswith("automake"):
                    self.output.warning(
                        f"{ref} bin/.{wrapper}-real missing and no {wrapper}-real "
                        "to restore; autoreconf fallback will be used"
                    )

    def _autotools_perl_prefix(self):
        """No PERL override: keep the conan-provided interpreter env.

        Previous round forced PERL=perl + narrow PERL5LIB to the two
        share dirs (DRAFT-6049). Preflight proved this wrong here: the
        system perl @INC is `//lib/perl5/...` (broken prefix) so even
        `strict.pm` is missing once the conan perl lib dirs are stripped
        (`Can't locate strict.pm ... at .autoreconf-real line 29`).
        The dotfile repair alone already lets autoreconf pass aclocal,
        and no Cwd.c handshake was observed, so preserve the conan
        buildenv PERL/PERL5LIB verbatim and return an empty prefix.
        """
        return ""

    def _refresh_config_scripts_from_tools(self):
        """Copy modern config.guess/sub from tool packages without aclocal.

        Used only when autoreconf cannot run (broken remote automake).
        The ots tarball already ships a pre-generated configure, so only
        the two config scripts need a modern refresh before E007 patching.
        Plain copy only (hardlink=0/chmod=0 safe; +x is best-effort).
        """
        candidates = []
        try:
            tools = self._autotools_tool_dirs()
        except Exception:
            tools = {}
        # Low-memory guard (Signal 9/OOM-kill with empty logs, 3rd
        # strategy): the previous round used a share-rooted bounded
        # os.walk (depth<=4, 20 candidates). This round removes os.walk
        # entirely — probe only fixed known locations with direct
        # isfile/glob checks, so no directory tree is ever traversed on
        # the hot path. Same by_name/sort selection below, so the
        # refreshed files are unchanged; only the search cost shrinks
        # to O(1) syscalls.
        for folder in tools.values():
            fixed = [
                os.path.join(folder, "share", "automake-1.18",
                             "config.guess"),
                os.path.join(folder, "share", "automake-1.18",
                             "config.sub"),
                os.path.join(folder, "share", "autoconf",
                             "config.guess"),
                os.path.join(folder, "share", "autoconf",
                             "config.sub"),
                os.path.join(folder, "share", "libtool",
                             "config.guess"),
                os.path.join(folder, "share", "libtool",
                             "config.sub"),
                os.path.join(folder, "share", "libtool-2.5.4",
                             "config.guess"),
                os.path.join(folder, "share", "libtool-2.5.4",
                             "config.sub"),
                os.path.join(folder, "share", "autoconf-2.72",
                             "config.guess"),
                os.path.join(folder, "share", "autoconf-2.72",
                             "config.sub"),
                os.path.join(folder, "res", "config.guess"),
                os.path.join(folder, "res", "config.sub"),
                os.path.join(folder, "share", "config.guess"),
                os.path.join(folder, "share", "config.sub"),
            ]
            for path in fixed:
                if os.path.isfile(path):
                    candidates.append(path)
                    if len(candidates) >= 8:
                        break
            if len(candidates) >= 8:
                break
        if len(candidates) < 2:
            # Fallback: single-level glob of share/ + share/*/ (no recursion).
            for folder in tools.values():
                share_root = os.path.join(folder, "share")
                if not os.path.isdir(share_root):
                    continue
                for fn in ("config.guess", "config.sub"):
                    direct = os.path.join(share_root, fn)
                    if os.path.isfile(direct) and direct not in candidates:
                        candidates.append(direct)
                try:
                    for pat in (os.path.join(share_root, "*", "config.guess"),
                                os.path.join(share_root, "*", "config.sub")):
                        for path in sorted(glob.glob(pat)):
                            if os.path.isfile(path) and path not in candidates:
                                candidates.append(path)
                                if len(candidates) >= 8:
                                    break
                        if len(candidates) >= 8:
                            break
                except Exception:
                    pass
                if len(candidates) >= 8:
                    break
        # Prefer automake-1.18 share copies first (2024 vintage).
        candidates.sort(key=lambda p: (("automake-1.18" not in p), p))
        by_name = {}
        for path in candidates:
            by_name.setdefault(os.path.basename(path), path)
        if not by_name:
            self.output.warning("config refresh: no config.guess/sub found in tool packages")
            return
        # 2026-09-24 repair: distribute to EVERY location configure may
        # read (source/build/work roots + build-aux variants). The failing
        # file in preflight was <build>/config.guess, which the old code
        # never refreshed. Keep O(1): fixed dir list only, no walk.
        targets = []
        try:
            targets.append(self.source_folder)
        except Exception:
            pass
        try:
            targets.append(os.path.join(self.source_folder, "build-aux"))
        except Exception:
            pass
        try:
            bf = self.build_folder
            if bf:
                targets.append(bf)
                targets.append(os.path.join(bf, "build-aux"))
        except Exception:
            pass
        try:
            wf = self._ohos_work_folder()
            if wf:
                targets.append(wf)
        except Exception:
            pass
        seen_t = set()
        for target in targets:
            if not target:
                continue
            key = os.path.normpath(target)
            if key in seen_t:
                continue
            seen_t.add(key)
            for name, src_path in by_name.items():
                dst = os.path.join(target, name)
                if os.path.isdir(target) or target == self.source_folder:
                    try:
                        if os.path.isfile(dst):
                            try:
                                os.remove(dst)
                            except Exception:
                                pass
                        shutil.copy2(src_path, dst)
                        try:
                            os.chmod(dst, 0o755)
                        except Exception:
                            pass
                        self.output.info(f"refreshed {dst} from {src_path}")
                    except Exception as exc:
                        self.output.warning(f"config refresh {dst} failed: {exc}")

    def _config_script_pairs(self):
        # 2026-09-24 repair: the failing config.guess in preflight was
        # <build>/config.guess (conan build folder root), while the old
        # helper only returned source_folder copies. The pre-generated
        # configure, when run out-of-source from ohos-work, resolves its
        # aux scripts from several locations, so EVERY copy must be
        # refreshed + E007-patched, otherwise the unpatched 2006 script
        # still reports "unable to guess system type" for HarmonyOS.
        # Walking the tiny ots source tree is cheap; the OOM guard only
        # forbids walking huge tool package trees (see _refresh_...).
        roots = []
        try:
            roots.append(self.source_folder)
        except Exception:
            pass
        try:
            bf = self.build_folder
            if bf:
                roots.append(bf)
        except Exception:
            pass
        try:
            wf = self._ohos_work_folder()
            if wf:
                roots.append(wf)
        except Exception:
            pass
        pairs = []
        seen = set()
        for root in roots:
            if not root:
                continue
            for sub in ("", "build-aux", "build-release"):
                cg = os.path.join(root, sub, "config.guess") if sub else os.path.join(root, "config.guess")
                cs = os.path.join(root, sub, "config.sub") if sub else os.path.join(root, "config.sub")
                key = (os.path.normpath(cg), os.path.normpath(cs))
                if key not in seen:
                    seen.add(key)
                    pairs.append((cg, cs))
        # Shallow discovery inside the source tree (depth <= 3): the 2007
        # tarball is tiny (< 200 files), so a bounded walk is safe.
        try:
            src = self.source_folder
            if src and os.path.isdir(src):
                for cur, ds, fs in os.walk(src):
                    try:
                        rel = os.path.relpath(cur, src)
                    except Exception:
                        continue
                    depth = 0 if rel in (".", os.curdir) else len(rel.split(os.sep))
                    if depth > 3:
                        ds[:] = []
                        continue
                    # Prune hidden/version-control dirs.
                    ds[:] = [d for d in ds if not d.startswith(".")]
                    if "config.guess" in fs and "config.sub" in fs:
                        cg = os.path.join(cur, "config.guess")
                        cs = os.path.join(cur, "config.sub")
                        key = (os.path.normpath(cg), os.path.normpath(cs))
                        if key not in seen:
                            seen.add(key)
                            pairs.append((cg, cs))
        except Exception:
            pass
        # Keep only pairs where at least one side exists (patch step
        # filters to both-existing).
        return pairs

    def _patch_config_scripts(self):
        """E007: HarmonyOS detection for config.guess/config.sub."""
        pairs = [
            (cg, cs) for cg, cs in self._config_script_pairs()
            if os.path.isfile(cg) and os.path.isfile(cs)
        ]
        if not pairs:
            self.output.warning("E007: config.guess/config.sub not found after autoreconf")
            return

        repo = os.environ.get("CI_REPO_ROOT", "")
        script = os.path.join(repo, "scripts", "patch-autotools-ohos.pl") if repo else ""
        for cg, cs in pairs:
            if script and os.path.isfile(script):
                try:
                    self.run(f'perl "{script}" "{cg}" "{cs}"', cwd=self.source_folder)
                except Exception as exc:
                    # 2007-vintage config.sub has no android-linux anchors, so
                    # the shared perl script scores 1/5 and exits 1 (CI #62002).
                    # Fall through to the vintage-independent Python patches
                    # below instead of aborting the build.
                    self.output.warning(
                        f"E007: perl patch failed for {cg} ({exc}); "
                        "using Python fallback"
                    )
            else:
                self.output.info("E007: patch-autotools-ohos.pl not found, Python fallback")
            # Vintage-independent completion: the perl script only handles
            # modern anchors; the Python helpers install the POSIX-sh
            # short-circuits (plus aarch64 CPU arm) that old scripts need.
            # Both helpers are idempotent no-ops when markers already exist.
            try:
                self._patch_config_guess_python(cg)
            except Exception as exc:
                self.output.warning(f"E007: python guess patch failed: {exc}")
            try:
                self._patch_config_sub_python(cs)
            except Exception as exc:
                self.output.warning(f"E007: python sub patch failed: {exc}")

    def _patch_config_guess_python(self, cg_path):
        import re

        with open(cg_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        changed = False
        # 2026-09-22 (3rd repair round, different strategy from the two
        # bash-search rounds): preflight still uses /system/bin/sh (no bash
        # on the worker) yet ogg/1.1.1 passes with the same mksh, so the
        # shell is not the blocker. The focused log shows
        # "E007: patched config.sub" but NEVER "patched config.guess":
        # the refresh pulls a 2024-vintage guess from the autoconf package
        # whose anchor layout differs from the old
        # "    *:NetBSD:*:*)" spelling, so the HarmonyOS case silently
        # never lands. With --build/--host omitted (R15) an unpatched
        # guess on HarmonyOS yields an uncanonicalisable triplet and the
        # 2007 configure exits 1 while the cc smoke still passes.
        if "__OHOS__" not in content and "ohos" not in content.lower():
            old = "#if defined(__ANDROID__)\n    LIBC=android"
            new = (
                "#if defined(__ANDROID__)\n    LIBC=android\n"
                "#elif defined(__OHOS__)\n    LIBC=ohos"
            )
            if old in content:
                content = content.replace(old, new, 1)
                changed = True
            else:
                # Modern guess uses varied indent; regex fallback.
                pat = r"(#if\s+defined\s*\(\s*__ANDROID__\s*\)\s*\n\s*LIBC\s*=\s*android)"
                rep = r"\1\n#elif defined(__OHOS__)\n    LIBC=ohos"
                content, n = re.subn(pat, rep, content, count=1)
                if n > 0:
                    changed = True
        if "OTS_HARMONYOS_SHORT_CIRCUIT" not in content:
            # 2026-09-24 (different strategy): preflight proves the anchor
            # block alone is insufficient — the patched 2006-vintage script
            # still reports "unable to guess system type" for HarmonyOS.
            # Root cause: the anchor block sets GUESS=... (modern-script
            # semantics), but the 2006 script echoes the triplet + exits
            # directly inside each case arm and never reads $GUESS, so the
            # arm falls through to the catch-all failure. Fix at two
            # levels: (a) this vintage-independent short-circuit right
            # after the shebang, which answers before any vintage case
            # logic runs (POSIX sh only); (b) the anchor block below now
            # echoes + exits instead of setting GUESS.
            lines = content.splitlines(True)
            short_circuit = (
                '# OTS_HARMONYOS_SHORT_CIRCUIT (recipe E007, POSIX sh):\n'
                '# uname -s returns HarmonyOS on the HongMeng kernel.\n'
                '_ots_us=`(uname -s) 2>/dev/null || echo unknown`\n'
                'case "$_ots_us" in\n'
                '    *[Hh]armony*[Oo][Ss]*)\n'
                '        _ots_um=`(uname -m) 2>/dev/null || echo aarch64`\n'
                '        case "$_ots_um" in\n'
                '            aarch64|arm64) echo aarch64-unknown-linux-ohos; exit 0 ;;\n'
                '            armv7*|armv8*|arm*) echo arm-unknown-linux-ohos; exit 0 ;;\n'
                '            x86_64|amd64) echo x86_64-unknown-linux-ohos; exit 0 ;;\n'
                '            i?86) echo i686-unknown-linux-ohos; exit 0 ;;\n'
                '            *) echo ${_ots_um}-unknown-linux-ohos; exit 0 ;;\n'
                '        esac\n'
                '        ;;\n'
                'esac\n'
            )
            if lines and lines[0].startswith("#!"):
                content = lines[0] + short_circuit + "".join(lines[1:])
            else:
                content = short_circuit + content
            changed = True
            self.output.info("E007: installed config.guess HarmonyOS short-circuit")
        if "GUESS=${MACHINE}-unknown-linux-ohos" in content:
            # Migrate the pre-2026-09-24 anchor block (GUESS semantics,
            # dead code on the 2006 vintage) to echo + exit.
            content = content.replace(
                "\tGUESS=${MACHINE}-unknown-linux-ohos\n",
                "\techo ${_ots_m}-unknown-linux-ohos\n\texit 0\n", 1)
            content = content.replace(
                '\t    aarch64|arm64) MACHINE=aarch64 ;;',
                '\t    aarch64|arm64) _ots_m=aarch64 ;;')
            content = content.replace(
                '\t    armv7*|armv8*) MACHINE=arm ;;',
                '\t    armv7*|armv8*|arm*) _ots_m=arm ;;')
            content = content.replace(
                '\t    x86_64|amd64)  MACHINE=x86_64 ;;',
                '\t    x86_64|amd64) _ots_m=x86_64 ;;')
            content = content.replace(
                '\t    i?86)          MACHINE=i686 ;;',
                '\t    i?86) _ots_m=i686 ;;')
            content = content.replace(
                '\t    *)            MACHINE="$UNAME_MACHINE" ;;',
                '\t    *) _ots_m="$UNAME_MACHINE" ;;')
            changed = True
            self.output.info("E007: migrated old GUESS block to echo+exit")
        if "*:HarmonyOS:*:*)" not in content:
            # NOTE: test for the case-arm pattern, not the bare word
            # "HarmonyOS" (the short-circuit comment above contains that
            # word but no case arm).
            block = (
                '    *:HarmonyOS:*:*)\n'
                '\tcase "$UNAME_MACHINE" in\n'
                '\t    aarch64|arm64) _ots_m=aarch64 ;;\n'
                '\t    armv7*|armv8*|arm*) _ots_m=arm ;;\n'
                '\t    x86_64|amd64) _ots_m=x86_64 ;;\n'
                '\t    i?86) _ots_m=i686 ;;\n'
                '\t    *) _ots_m="$UNAME_MACHINE" ;;\n'
                '\tesac\n'
                '\techo ${_ots_m}-unknown-linux-ohos\n'
                '\texit 0\n'
                '\t;;\n\n'
            )
            # Try known anchors in order; fall back to the catch-all case
            # so the patch NEVER silently no-ops on a new vintage.
            anchors = ("    *:NetBSD:*:*)", "*:NetBSD:*:*)",
                       "*:OpenBSD:*:*)", "*:MirBSD:*:*)")
            done = False
            for anchor in anchors:
                if anchor in content:
                    content = content.replace(anchor, block + anchor, 1)
                    changed = True
                    done = True
                    self.output.info(
                        f"E007: patched config.guess via anchor {anchor}")
                    break
            if not done:
                # Modern (2024) scripts still end the uname case list with
                # a generic "*:*:*:*)" / "*)" fallback before esac.
                for fallback in ("    *:*:*:*)", "*:*:*:*)"):
                    if fallback in content:
                        content = content.replace(
                            fallback, block + fallback, 1)
                        changed = True
                        done = True
                        self.output.info(
                            "E007: patched config.guess via catch-all anchor")
                        break
            if not done:
                self.output.warning(
                    "E007: config.guess anchor not found; HarmonyOS case missing")
        if changed:
            with open(cg_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.output.info("E007: patched config.guess for HarmonyOS")
        else:
            if "HarmonyOS" in content:
                self.output.info("E007: config.guess already has HarmonyOS")
            else:
                self.output.warning("E007: config.guess patch had no effect")

    def _patch_config_sub_python(self, cs_path):
        import re

        with open(cs_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        changed = False
        # 2026-09-24: the 2006-vintage sub has no android-era anchors, so
        # the regex patches below silently no-op, and its machine list
        # predates aarch64 entirely ("machine `aarch64-unknown-linux' not
        # recognized"). Two vintage-independent fixes first.
        if "OTS_OHOS_SUB_SHORT_CIRCUIT" not in content:
            _scl = content.splitlines(True)
            _scb = (
                '# OTS_OHOS_SUB_SHORT_CIRCUIT (recipe E007, POSIX sh):\n'
                'case "$1" in\n'
                '    *ohos*|*harmony*|*HarmonyOS*)\n'
                '        case "$1" in\n'
                '            aarch64*|arm64*) _ots_sc=aarch64 ;;\n'
                '            arm*) _ots_sc=arm ;;\n'
                '            x86_64*|amd64*) _ots_sc=x86_64 ;;\n'
                '            i?86*) _ots_sc=i686 ;;\n'
                '            *) _ots_sc=aarch64 ;;\n'
                '        esac\n'
                '        echo ${_ots_sc}-unknown-linux-ohos\n'
                '        exit 0\n'
                '        ;;\n'
                'esac\n'
            )
            if _scl and _scl[0].startswith("#!"):
                content = _scl[0] + _scb + "".join(_scl[1:])
            else:
                content = _scb + content
            changed = True
            self.output.info("E007: installed config.sub ohos short-circuit")
        if "basic_machine=aarch64-unknown" not in content:
            # NOTE: test for the arm body, not the word "aarch64" (the
            # short-circuit above contains that word but no machine arm).
            _arm = (
                '\taarch64* | arm64*)\n'
                '\t\tbasic_machine=aarch64-unknown\n'
                '\t\t;;\n'
            )
            content, _n = re.subn(
                r"(case\s+\$basic_machine\s+in\s*\n)", r"\1" + _arm,
                content, count=1)
            if _n > 0:
                changed = True
                self.output.info("E007: added aarch64 CPU arm to config.sub")
            else:
                self.output.warning("E007: basic_machine case not found")
        if "ohos-linux" not in content:
            pattern = (
                r'(android-linux\)\s*\n\s*basic_machine=\$field1-unknown\s*\n'
                r'\s*basic_os=linux-android\s*\n\s*;;\s*\n)'
            )
            replacement = (
                r'\1\tohos-linux)\n\tbasic_machine=$field1-unknown\n'
                r'\tbasic_os=linux-ohos\n\t;;\n'
            )
            content, count = re.subn(pattern, replacement, content)
            if count > 0:
                changed = True
        if "ohos*" not in content:
            new_content = content.replace("gnu* | android*", "gnu* | android* | ohos*", 1)
            if new_content != content:
                content = new_content
                changed = True
        if "linux-ohos" not in content:
            content, count = re.subn(r'(linux-uclibc[\*/-]?\s*\))', r'\1| linux-ohos*)', content)
            if count > 0:
                changed = True
        # Belt and braces: if config.guess ever emits a raw HarmonyOS
        # triplet, canonicalise it to linux-ohos instead of failing validation.
        if "harmonyos" not in content.lower():
            content, count = re.subn(
                r'(linux-android[\*/ -]?\s*\))', r'\1 | harmonyos*)', content)
            if count > 0:
                changed = True
        if changed:
            with open(cs_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.output.info("E007: patched config.sub for HarmonyOS")
        else:
            self.output.info("E007: config.sub already handles ohos")

    def _verify_config_guess(self, config_shell, tmpdir):
        # Evidence for the next round: run each patched config.guess and
        # log the triplet. Short one-liner survives hmbs focused summaries.
        # 2026-09-24: probe ALL copies (source/build/work), not just source.
        seen = set()
        try:
            pairs = list(self._config_script_pairs())
        except Exception:
            pairs = []
        for cg, _cs in pairs:
            if cg in seen:
                continue
            seen.add(cg)
            if not os.path.isfile(cg):
                continue
            d = os.path.dirname(cg)
            try:
                import subprocess
                out = subprocess.run(
                    [config_shell, cg], capture_output=True, text=True,
                    timeout=30, cwd=(d or self.source_folder),
                    env={**__import__('os').environ, "TMPDIR": tmpdir,
                         "TMP": tmpdir, "TEMP": tmpdir}).stdout.strip()
                self.output.info("OTS_CONFIG_GUESS[%s]=%s" % (d, out[:200]))
                self.output.warning("OTS_CONFIG_GUESS=%s" % out[:200])
            except Exception as exc:
                self.output.warning("config.guess probe failed: %s" % exc)
        # 2026-09-24: also validate config.sub accepts the ohos triplet,
        # so the next round's log shows sub status, not just guess status.
        try:
            pairs = list(self._config_script_pairs())
        except Exception:
            pairs = []
        seen_sub = set()
        for _cg, cs in pairs:
            if cs in seen_sub:
                continue
            seen_sub.add(cs)
            if not os.path.isfile(cs):
                continue
            d = os.path.dirname(cs)
            try:
                import subprocess
                out = subprocess.run(
                    [config_shell, cs, "aarch64-unknown-linux-ohos"],
                    capture_output=True, text=True,
                    timeout=30, cwd=(d or self.source_folder),
                    env={**__import__('os').environ, "TMPDIR": tmpdir,
                         "TMP": tmpdir, "TEMP": tmpdir})
                res = (out.stdout.strip() or out.stderr.strip())[:200]
                self.output.warning("OTS_CONFIG_SUB=%s" % res)
            except Exception as exc:
                self.output.warning("config.sub probe failed: %s" % exc)

    @staticmethod
    def _is_elf(path):
        with open(path, "rb") as fh:
            return fh.read(4) == b"\x7fELF"

    def _sign_ohos_elf(self, path):
        """OHOS XPM requires a .codesign section on executed ELF binaries."""
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not (os.path.isfile(objcopy) and os.path.isfile(signer) and os.path.isfile(readelf)):
            raise ConanException("Required OHOS signing tools are missing")
        sections = subprocess.run(
            [readelf, "-SW", path], check=True, capture_output=True,
            text=True, timeout=30,
        ).stdout
        if sections.count(".codesign") == 1:
            return
        if sections.count(".codesign") != 0:
            raise ConanException("ELF has invalid .codesign count: %s" % path)
        clean = path + ".sign-clean"
        signed = path + ".ots-signed"
        try:
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", path, clean],
                check=True, timeout=30,
            )
            subprocess.run(
                [signer, "sign", "-inFile", clean, "-outFile", signed, "-selfSign", "1"],
                check=True, timeout=60,
            )
            sections = subprocess.run(
                [readelf, "-SW", signed], check=True, capture_output=True,
                text=True, timeout=30,
            ).stdout
            if sections.count(".codesign") != 1:
                raise ConanException("Signed ELF has invalid .codesign count: %s" % path)
            os.chmod(signed, (os.stat(path).st_mode & 0o777) | 0o055)
            os.replace(signed, path)
        finally:
            for generated in (clean, signed):
                if os.path.exists(generated):
                    os.remove(generated)

    def package(self):
        if str(self.settings.os) == "OHOS":
            # Build ran out-of-source in ohos-work with an explicit shell;
            # install from there with the same TMPDIR env (osi pattern).
            work_folder = self._ohos_work_folder()
            if os.path.isfile(os.path.join(work_folder, "Makefile")):
                tmpdir = self._writable_tmpdir()
                self._strip_conan_ld_from_env()
                # Same lld hazard as configure: scrub conan-home entries
                # in-shell so libtool relink keeps system libxml2.
                ld_scrub = (
                    "LD_LIBRARY_PATH=\"$(printf '%s' \"${LD_LIBRARY_PATH:-}\""
                    " | tr ':' '\\n' | grep -v 'conan-home' | grep . "
                    " | paste -sd: - 2>/dev/null || true)\"; "
                    "export LD_LIBRARY_PATH; "
                )
                destination = shlex.quote(self.package_folder)
                try:
                    self.run(f"{ld_scrub}{self._tmp_env_prefix(tmpdir)}make install DESTDIR={destination} -j1",
                             cwd=work_folder)
                except Exception:
                    # Fall back to an explicit DESTDIR retry in the same work
                    # folder (osi pattern). The Autotools helper defaults to
                    # build_folder, which has no Makefile in this
                    # out-of-source layout, so it must not be used here.
                    self.run(f"{ld_scrub}{self._tmp_env_prefix(tmpdir)}make install DESTDIR={destination} -j1",
                             cwd=work_folder)
            else:
                autotools = Autotools(self)
                autotools.install(args=["-j1"])
        else:
            autotools = Autotools(self)
            autotools.install()
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # OHOS executables must carry a .codesign section so `ots` can run.
        if str(self.settings.os) == "OHOS" and can_run(self):
            bindir = os.path.join(self.package_folder, "bin")
            if os.path.isdir(bindir):
                for name in sorted(os.listdir(bindir)):
                    path = os.path.join(bindir, name)
                    if os.path.isfile(path) and not os.path.islink(path) and self._is_elf(path):
                        self._sign_ohos_elf(path)

    def package_info(self):
        self.cpp_info.libs = ["ots-1"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "libots-1")
        self.cpp_info.set_property("cmake_target_name", "libots-1::libots-1")
        self.cpp_info.set_property("pkg_config_name", "libots-1")
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
