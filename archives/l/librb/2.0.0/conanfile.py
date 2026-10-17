#!/usr/bin/env python3
"""Conan recipe — librb 2.0.0 (autotools).

librb is a ring buffer (circular FIFO queue) C library with a POSIX-like
read/write API by Michal Lyszczek: blocking/non-blocking multithreaded
access, growable buffers, dynamic frames and a claim/commit zero-copy API.
The whole library is a single translation unit (rb.c plus generated rb.h).

OHOS notes:
  - The upstream GitHub archive carries no generated `configure`, so build()
    bootstraps it with autoreconf (tool_requires: autoconf/automake/libtool).
  - Threads stay at the upstream default (--enable-threads=yes); OHOS libc
    provides pthread, semaphore.h and C11 atomics. Two musl portability
    patches apply (see conandata.yml): sem_close()->sem_destroy() for unnamed
    semaphores, and rb_sem_post() made unconditional (the sem_getvalue()
    cap gate is racy on any POSIX and musl reports blocked waiters as a
    negative count; a missed post hangs `make check` under high
    producer/consumer contention).
  - Top-level SUBDIRS is `www examples`; www/ regenerates man pages with
    sphinx-build, which is absent on the builder/CI image (flex 2.6.4.2
    texinfo precedent). Build and test therefore target the top-level
    artifacts explicitly (`make librb.la tests`, then `make check-am` which
    runs the local TESTS without recursing into SUBDIRS), so only the
    top-level librb.la + `tests` binary are built, tested and installed;
    man pages are docs, not link inputs. `check-am` (instead of `check`
    with SUBDIRS=.) also avoids the automake self-recursion into `.` which
    relinked `tests` twice back-to-back in the preflight log.
  - `make check` runs the upstream mtest TAP suite (the `tests` binary);
    build() parses the TAP points from tests.log and emits the
    HMBS_UPSTREAM_TEST_RESULT machine evidence marker.
"""
import json
import os
import re
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibrbConan(ConanFile):
    name = "librb"
    version = "2.0.0"
    description = "Ring buffer FIFO queue C library with POSIX-like read/write API"
    license = "BSD-2-Clause"
    homepage = "https://librb.bofc.pl"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("ring-buffer", "fifo", "queue", "multithreading", "ipc")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # librb depends on libc only (pthread/semaphore/C11 atomics) —
        # no third-party dependencies.
        pass

    def validate(self):
        # R32: OHOS must be matched alongside Linux, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "librb supports Linux/OHOS only, got %s" % self.settings.os
            )

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build_requirements(self):
        # The GitHub archive is a bare git tree snapshot without the
        # generated `configure`; bootstrap it on the worker (zzuf 0.15
        # precedent: versions already published in the registry).
        self.tool_requires("automake/1.18")
        self.tool_requires("autoconf/2.72")
        self.tool_requires("libtool/2.5.4")

    def _resolve_hmbs_tmp(self):
        # HMBS readonly_tmp: /tmp is read-only (erofs) on the true machine;
        # probe HMBS-injected candidates for real writability, never /tmp.
        def _valid(p):
            try:
                if not p or p in ("0", "1") or p == "/tmp":
                    return False
                os.makedirs(p, exist_ok=True)
                fd, probe = tempfile.mkstemp(dir=p)
                os.close(fd)
                os.unlink(probe)
                return True
            except Exception:
                return False
        for cand in (
            os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK"),
            os.environ.get("TMPDIR"),
            os.environ.get("TMP"),
            os.environ.get("TEMP"),
            os.environ.get("HMBS_TMPDIR"),
        ):
            if cand and _valid(cand):
                return cand
        fb = os.path.join(self.build_folder, "cfg-tmp")
        try:
            os.makedirs(fb, exist_ok=True)
        except OSError:
            pass
        return fb

    def _patch_configure(self, cfg):
        # Variable-form only (never bake absolute paths): source-time TMPDIR
        # may differ from build-time runtime tmp.
        try:
            with open(cfg, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
            orig = content
            if "umask 077" in content:
                content = content.replace("umask 077", "umask 022")
            if "ac_pwd=`pwd`" in content:
                content = content.replace(
                    "ac_pwd=`pwd`",
                    'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"')
                content = content.replace(
                    'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD" 2>/dev/null || ac_pwd="$PWD"',
                    'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"')
            content = content.replace(
                'mktemp -d -q "./confstatXXXXXX"',
                'mktemp -d -q "${TMPDIR:-.}/confstatXXXXXX"')
            content = content.replace(
                'mktemp -d "./confXXXXXX"',
                'mktemp -d "${TMPDIR:-.}/confXXXXXX"')
            content = content.replace(
                "mktemp -d './confXXXXXX'",
                "mktemp -d '${TMPDIR:-.}/confXXXXXX'")
            content = content.replace("tmp=./conf$-$RANDOM", "tmp=${TMPDIR:-.}/conf$-$RANDOM")
            if "tmp=./conf$" in content:
                content = content.replace("tmp=./conf", "tmp=${TMPDIR:-.}/conf")
            content = re.sub(r":\s*\$\{TMPDIR=/tmp\}", ": ${TMPDIR=\\.}", content)
            content = content.replace("${TMPDIR=/tmp}", "${TMPDIR=\\.}")
            if content != orig:
                with open(cfg, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(content)
                self.output.info("librb: HMDFS tmp patch applied: %s" % cfg)
            elif "umask 022" in content:
                self.output.info("librb: patched generated configure umask 077 -> 022")
        except OSError:
            pass

    def generate(self):
        # Puts the tool_requires bootstrap binaries on the build PATH.
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
            if self.options.get_safe("fPIC"):
                tc.configure_args.append("--with-pic")
        # automake 1.18 config.guess (2024-07-27) cannot recognize
        # UNAME_SYSTEM=HarmonyOS, so configure dies with "cannot guess build
        # type". Bypass guessing with explicit triplets (zzuf 0.15 precedent
        # on the same true machine).
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
        ])
        tc.generate()
        # HMBS readonly_tmp: export writable TMPDIR/TMP/TEMP + SHELL into the
        # build env so autoconf/config.status/libtool/mktemp/tap-driver never
        # fall back to read-only /tmp (cassbeam/c-client precedent).
        tmp = self._resolve_hmbs_tmp()
        try:
            os.makedirs(tmp, exist_ok=True)
        except OSError:
            pass
        shell = os.environ.get("SHELL", "/bin/sh") or "/bin/sh"
        env = Environment()
        env.define("TMPDIR", tmp)
        env.define("TMP", tmp)
        env.define("TEMP", tmp)
        env.define("SHELL", shell)
        env.define("CONFIG_SHELL", shell)
        for _k in ("HMBS_AUTOCONF_MKTEMP_FALLBACK", "HMBS_CAP_LOCAL_MKTEMP",
                   "HMBS_TMPDIR", "HMBS_CAP_HARDLINK", "HMBS_CAP_CHMOD",
                   "HMBS_CAP_SYMLINK"):
            _v = os.environ.get(_k)
            if _v:
                env.define(_k, _v)
        env.vars(self, scope="build").save_script("hmbs_tmp_env")

    def _bootstrap_autotools(self):
        # Conan tool perl 5.42.2 XS (Cwd.so) cannot load on HMDFS/OHOS
        # (Perl_my_cxt_init symbol mismatch when mixed with system perl,
        # aclocal dies with exit 255). Reproduce `autoreconf -fi`
        # step-by-step forcing system perl (zzuf 0.15 / avimetaedit 1.0.2 /
        # burp2 2.1.0 precedent): libtoolize (AC_PROG_LIBTOOL) -> aclocal
        # -I m4 (AC_CONFIG_MACRO_DIR) -> autoheader (AC_CONFIG_HEADERS) ->
        # automake (AM_INIT_AUTOMAKE foreign) -> autoconf.
        src = self.source_folder.replace("\\", "/")
        # HMBS injects SHELL=/bin/sh; keep it (fallback /bin/sh), not bare bash.
        shell = os.environ.get("SHELL", "/bin/sh") or "/bin/sh"
        tmpdir = self._resolve_hmbs_tmp()
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        self.run(
            f"{shell} -c \"set -e"
            f" && export TMPDIR='{tmpdir}' TMP='{tmpdir}' TEMP='{tmpdir}'"
            f" && export PERL=/data/service/hnp/bin/perl"
            f" && cd '{src}'"
            f" && LIBTOOLIZE=$(command -v libtoolize 2>/dev/null || exit 1)"
            f" && unset PERL5LIB"
            f" && sh $LIBTOOLIZE --copy --force"
            f" && ACLOCAL=$(command -v aclocal-1.18 2>/dev/null || command -v aclocal 2>/dev/null || exit 1)"
            f" && unset PERL5LIB"
            f" && export PERL5LIB=$(dirname $(dirname $ACLOCAL))/share/automake-1.18"
            f" && sh $ACLOCAL -I m4"
            f" && AUTOHEADER=$(command -v autoheader 2>/dev/null || exit 1)"
            f" && export PERL5LIB=$(dirname $(dirname $AUTOHEADER))/share/autoconf"
            f" && sh $AUTOHEADER"
            f" && AUTOMAKE=$(command -v automake-1.18 2>/dev/null || command -v automake 2>/dev/null || exit 1)"
            f" && export PERL5LIB=$(dirname $(dirname $AUTOMAKE))/share/automake-1.18"
            f" && sh $AUTOMAKE --foreign --add-missing --copy"
            f" && AUTOCONF=$(command -v autoconf 2>/dev/null || exit 1)"
            f" && export PERL5LIB=$(dirname $(dirname $AUTOCONF))/share/autoconf"
            f" && sh $AUTOCONF\"",
            env="conanbuild",
        )

    def build(self):
        apply_conandata_patches(self)
        # Writable tmp for configure/make/check: never let autoconf/mktemp
        # fall back to read-only /tmp (HMBS readonly_tmp gate).
        tmpdir = self._resolve_hmbs_tmp()
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        for _var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[_var] = tmpdir
        _shell = os.environ.get("SHELL", "/bin/sh") or "/bin/sh"
        os.environ["SHELL"] = _shell
        os.environ["CONFIG_SHELL"] = _shell
        try:
            os.makedirs(os.path.join(os.path.expanduser("~"), "tmp"), exist_ok=True)
        except OSError:
            pass
        self.output.info("librb: HMBS tmp root (probed writable): %s" % tmpdir)
        autotools = Autotools(self)
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.output.info("librb: no configure in source tree, manual bootstrap with system perl")
            self._bootstrap_autotools()
        # HMDFS ignores chmod: autoconf temp dirs created with umask 077 lack
        # group write bits and config.status fails writing subs1.awk, so run
        # the generated script with umask 022 (platform adaptation of the
        # generated file, not a source patch). Plus variable-form TMPDIR
        # patches so mktemp never defaults to read-only /tmp.
        cfg = os.path.join(self.source_folder, "configure")
        if os.path.isfile(cfg):
            self._patch_configure(cfg)
        autotools.configure()
        # Top-level SUBDIRS is `www examples`; www/ rebuilds man pages via
        # sphinx-build, which is not installed on the builder (make dies in
        # www/ with `sphinx-build: command not found`). The library and the
        # `tests` binary both live at top level, so build those explicit
        # targets (explicit targets never recurse into SUBDIRS) and run the
        # local suite via `check-am` (runs top-level TESTS once without the
        # `check-recursive` self-recursion into `.` that relinked `tests`
        # twice back-to-back in the preflight log); man pages are docs, not
        # link inputs.
        autotools.make(args=["-j1", "librb.la", "tests"])
        self._run_upstream_tests(autotools)

    def _run_upstream_tests(self, autotools):
        # Streams the full `make check-am` log to the conan output
        # (evidence); self.run raises on non-zero exit, so failures can
        # never pass silent. `check-am` runs the top-level TESTS once and
        # never recurses into www/examples, while the only automake TESTS
        # entry lives at top level.
        autotools.make(target="check-am", args=["-j1"])
        discovered, passed, failed, skipped = self._parse_tap_results()
        status = "passed" if (failed == 0 and discovered > 0) else "failed"
        marker = {
            "status": status,
            "framework": "mtest-tap",
            "command": "make check-am",
            "discovered": discovered,
            "executed": discovered,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker)
        self.output.info(msg)
        print(msg, flush=True)
        with open(os.path.join(self.build_folder, "upstream_test_result.json"),
                  "w", encoding="utf-8", newline="\n") as fh:
            json.dump(marker, fh)
        if status != "passed":
            raise RuntimeError("librb upstream tests failed: %s" % marker)

    def _parse_tap_results(self):
        # Upstream TESTS is a single `tests` binary driven by the mtest TAP
        # framework: main() fans out over buffer-size/producer/consumer
        # matrices, so one automake entry hides tens of thousands of TAP
        # points. Count the real `ok`/`not ok` lines in tests.log instead of
        # reporting the single automake entry.
        tap_ok = 0
        tap_fail = 0
        for root in (self.build_folder, self.source_folder):
            for dirpath, _, filenames in os.walk(root):
                if "tests.log" not in filenames:
                    continue
                with open(os.path.join(dirpath, "tests.log"),
                          encoding="utf-8", errors="replace") as fh:
                    for line in fh:
                        if re.match(r"^ok\b", line):
                            tap_ok += 1
                        elif re.match(r"^not ok\b", line):
                            tap_fail += 1
        if tap_ok + tap_fail > 0:
            self.output.info("librb: parsed tests.log TAP points ok=%d fail=%d"
                             % (tap_ok, tap_fail))
            return tap_ok + tap_fail, tap_ok, tap_fail, 0
        # Fallback: automake test-suite.log summary (single TESTS entry).
        total = passed = failed = skipped = 0
        for root in (self.build_folder, self.source_folder):
            for dirpath, _, filenames in os.walk(root):
                if "test-suite.log" not in filenames:
                    continue
                with open(os.path.join(dirpath, "test-suite.log"),
                          encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
                for key, attr in (("# TOTAL:", "total"), ("# PASS:", "passed"),
                                  ("# FAIL:", "failed"), ("# SKIP:", "skipped"),
                                  ("# XFAIL:", None), ("# XPASS:", None),
                                  ("# ERROR:", None)):
                    match = re.search(r"%s\s*(\d+)" % re.escape(key), text)
                    if match and attr:
                        if attr == "total":
                            total = int(match.group(1))
                        elif attr == "passed":
                            passed = int(match.group(1))
                        elif attr == "failed":
                            failed = int(match.group(1))
                        elif attr == "skipped":
                            skipped = int(match.group(1))
                    elif match and key in ("# XPASS:", "# ERROR:"):
                        failed += int(match.group(1))
        if total > 0:
            self.output.info("librb: parsed test-suite.log TOTAL=%d PASS=%d FAIL=%d SKIP=%d"
                             % (total, passed, failed, skipped))
            return total, passed, failed, skipped
        raise RuntimeError("librb: no TAP points in tests.log and no test-suite.log "
                           "summary — refusing empty pass")

    def _setup_chmod_shim(self):
        # HMBS_CAP_CHMOD=0: libtool runs `chmod 644 <dest>` after install;
        # a failing chmod must never break install (cryptopant precedent).
        try:
            shim_bin = os.path.join(self.build_folder, "_hmbs_bin")
            os.makedirs(shim_bin, exist_ok=True)
            shim = os.path.join(shim_bin, "chmod")
            if not os.path.isfile(shim):
                fd = os.open(shim, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
                try:
                    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                        f.write("#!/bin/sh\n")
                        f.write("/bin/chmod \"$@\" 2>/dev/null || /usr/bin/chmod \"$@\" 2>/dev/null || true\n")
                        f.write("exit 0\n")
                except Exception:
                    try:
                        os.close(fd)
                    except Exception:
                        pass
                    raise
                try:
                    os.chmod(shim, 0o755)
                except Exception:
                    pass
            cur = os.environ.get("PATH", "")
            if shim_bin not in cur.split(os.pathsep):
                os.environ["PATH"] = shim_bin + os.pathsep + cur
            self.output.info("librb: chmod shim at %s" % shim)
        except Exception as e:
            self.output.warning("librb: chmod shim skipped: %s" % e)

    def _write_install_shim(self):
        # HMBS runtime install shim proved fragile for libtool's
        # `install -c .libs/librb.a <dest>` (dest missing -> chmod ENOENT);
        # own cp/mkdir shim with mkdir -p + tolerant chmod (avahi/cryptopant).
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        os.makedirs(shim_dir, exist_ok=True)
        install = os.path.join(shim_dir, "install")
        fd = os.open(install, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(
                    "#!/bin/sh\n"
                    "set -eu\n"
                    "mode=\n"
                    "while [ $# -gt 0 ]; do\n"
                    "  case \"$1\" in\n"
                    "    -p|-c) shift ;;\n"
                    "    -m) [ $# -ge 2 ] || exit 2; mode=$2; shift 2 ;;\n"
                    "    -d) shift; [ $# -gt 0 ] || exit 2; mkdir -p \"$@\"; exit 0 ;;\n"
                    "    --) shift; break ;;\n"
                    "    -*) shift ;;\n"
                    "    *) break ;;\n"
                    "  esac\n"
                    "done\n"
                    "[ $# -ge 2 ] || exit 2\n"
                    "dest=\n"
                    "for arg in \"$@\"; do dest=$arg; done\n"
                    "count=$(($# - 1))\n"
                    "if [ \"$count\" -gt 1 ]; then\n"
                    "  mkdir -p \"$dest\"\n"
                    "else\n"
                    "  destdir=$(dirname \"$dest\")\n"
                    "  mkdir -p \"$destdir\"\n"
                    "fi\n"
                    "i=1\n"
                    "for src in \"$@\"; do\n"
                    "  [ $i -gt $count ] && break\n"
                    "  cp -f \"$src\" \"$dest\"\n"
                    "  if [ -n \"$mode\" ]; then\n"
                    "    if [ -d \"$dest\" ]; then\n"
                    "      chmod \"$mode\" \"$dest/${src##*/}\" 2>/dev/null || true\n"
                    "    else\n"
                    "      chmod \"$mode\" \"$dest\" 2>/dev/null || true\n"
                    "    fi\n"
                    "  fi\n"
                    "  i=$((i + 1))\n"
                    "done\n"
                )
        except Exception:
            try:
                os.close(fd)
            except Exception:
                pass
            raise
        try:
            os.chmod(install, 0o755)
        except Exception:
            pass
        return install

    def _redirect_install_to_shim(self, root, shim_install):
        for _root, _, _files in os.walk(root):
            if "Makefile" not in _files:
                continue
            _mp = os.path.join(_root, "Makefile")
            try:
                with open(_mp, "r", encoding="utf-8", errors="ignore") as _f:
                    _content = _f.read()
            except OSError:
                continue
            if "INSTALL =" not in _content:
                continue
            _lines = []
            _changed = False
            for _line in _content.splitlines(True):
                _stripped = _line.lstrip()
                if _stripped.startswith("INSTALL = ") and "/install" in _stripped:
                    _indent = _line[:len(_line) - len(_stripped)]
                    _lines.append("%sINSTALL = %s\n" % (_indent, shim_install))
                    _changed = True
                else:
                    _lines.append(_line)
            if _changed:
                with open(_mp, "w", encoding="utf-8") as _f:
                    _f.write("".join(_lines))
                self.output.info("librb: redirected INSTALL to shim in %s" % _mp)

    def _fallback_manual_install(self):
        # Last resort if `make install` still leaves no lib (HMDFS quirks):
        # copy built .libs artifacts + rb.h directly; never silently empty.
        import glob as _glob
        import shutil as _shutil
        libdir = os.path.join(self.package_folder, "lib")
        incdir = os.path.join(self.package_folder, "include")
        try:
            os.makedirs(libdir, exist_ok=True)
            os.makedirs(incdir, exist_ok=True)
        except OSError:
            pass
        cands = []
        for root in (self.build_folder, self.source_folder):
            cands += _glob.glob(os.path.join(root, "**", ".libs", "librb.*"), recursive=True)
            cands += _glob.glob(os.path.join(root, "**", "librb.a"), recursive=True)
            cands += _glob.glob(os.path.join(root, "**", "librb.so*"), recursive=True)
        copied = 0
        for src in dict.fromkeys(cands):
            if os.path.isdir(src):
                continue
            base = os.path.basename(src)
            if not (base.startswith("librb.")):
                continue
            # skip libtool .la companion here (removed later anyway)
            if base.endswith(".la"):
                continue
            try:
                _shutil.copy2(src, os.path.join(libdir, base))
                self.output.info("librb: manual fallback copied %s" % src)
                copied += 1
            except OSError as e:
                self.output.warning("librb: manual copy failed %s: %s" % (src, e))
        for hdr in ("rb.h",):
            for root in (self.build_folder, self.source_folder):
                for cand in _glob.glob(os.path.join(root, "**", hdr), recursive=True):
                    # prefer top-level generated header, skip test fixtures
                    try:
                        _shutil.copy2(cand, os.path.join(incdir, hdr))
                        self.output.info("librb: manual fallback header %s" % cand)
                        break
                    except OSError:
                        continue
                if os.path.isfile(os.path.join(incdir, hdr)):
                    break
        return copied

    def package(self):
        self._setup_chmod_shim()
        try:
            _shim = self._write_install_shim()
            self._redirect_install_to_shim(self.build_folder, _shim)
            self._redirect_install_to_shim(self.source_folder, _shim)
        except Exception as e:
            self.output.warning("librb: install shim skipped: %s" % e)
        autotools = Autotools(self)
        # SUBDIRS=. again: installing www/ would reinstall (and rebuild via
        # sphinx) the man pages; only the top-level lib + generated rb.h ship.
        autotools.install(args=["-j1", "SUBDIRS=."])
        # HMDFS guard: if libtool install left no archive (preflight:
        # `install -c .libs/librb.a <pkg>/lib/librb.a` then chmod ENOENT),
        # fall back to direct copy so package is never silently empty.
        _have_lib = (self._glob(os.path.join(self.package_folder, "lib", "librb.a"))
                     + self._glob(os.path.join(self.package_folder, "lib", "librb.so*")))
        if not _have_lib:
            self.output.warning("librb: make install left no lib, manual fallback")
            self._fallback_manual_install()
            _have_lib = (self._glob(os.path.join(self.package_folder, "lib", "librb.a"))
                         + self._glob(os.path.join(self.package_folder, "lib", "librb.so*")))
            if not _have_lib:
                raise RuntimeError("librb: package lib missing after install + fallback")
        # libtool .la files bake absolute libdir paths; link info already
        # flows through cpp_info, so drop them (gd 2.3.3.1 precedent).
        for stale in (self._glob(os.path.join(self.package_folder, "lib", "*.la"))
                      + self._glob(os.path.join(self.package_folder, "lib", "*.dylib"))):
            try:
                os.remove(stale)
            except OSError:
                pass
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "upstream_test_result.json", self.build_folder,
             os.path.join(self.package_folder, "res"))
        self._sign_binaries()

    def _glob(self, pattern):
        import glob
        return glob.glob(pattern)

    def _is_elf(self, path):
        try:
            with open(path, "rb") as fh:
                return fh.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # HarmonyOS XPM requires signed shared objects; sign the installed
        # .so files in place (gd 2.3.3.1 precedent).
        if self.settings.os != "OHOS":
            return
        targets = []
        targets += self._glob(os.path.join(self.package_folder, "lib", "**", "*.so"))
        targets += self._glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"))
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for target in targets:
            if os.path.islink(target) or not self._is_elf(target):
                continue
            self.run('env -u LD_LIBRARY_PATH "%s" --remove-section .codesign "%s" 2>/dev/null || true'
                     % (objcopy, target))
            self.run('env -u LD_LIBRARY_PATH "%s" sign -inFile "%s" -outFile "%s" -selfSign 1'
                     % (signer, target, target))

    def package_info(self):
        # Built artifact is librb.so / librb.a, so the link lib is "rb".
        self.cpp_info.libs = ["rb"]
        self.cpp_info.set_property("cmake_file_name", "librb")
        self.cpp_info.set_property("cmake_target_name", "librb::librb")
