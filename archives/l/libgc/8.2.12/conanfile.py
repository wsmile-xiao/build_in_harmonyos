#!/usr/bin/env python3
"""Conan recipe for libgc 8.2.12 — Autotools build system.

libgc (Boehm-Demers-Weiser conservative garbage collector) provides
GC_MALLOC/GC_FREE as drop-in replacements for malloc/free with automatic
collection of unreachable memory. On HarmonyOS, pthread_setcancelstate and
pthread_cancel are not available in musl libc, so CANCEL_SAFE and
GC_HAVE_PTHREAD_EXIT are disabled via source patches.
"""
import json
import os
import re
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy, save, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibgcConan(ConanFile):
    name = "libgc"
    version = "8.2.12"
    description = "Boehm-Demers-Weiser conservative garbage collector for C/C++"
    license = "MIT"
    homepage = "https://github.com/bdwgc/bdwgc"
    url = "https://github.com/bdwgc/bdwgc"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libgc is built for Linux/OHOS only")

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        else:
            tc.configure_args.append("--enable-shared")
        if self.settings.os == "OHOS":
            # config.sub is patched above to accept these triplets;
            # AutotoolsToolchain injects OHOS sysroot/target flags so
            # bare `CC=clang ./configure` ("C compiler cannot create
            # executables") is avoided.
            tc.configure_args.extend([
                "--build=aarch64-linux-ohos",
                "--host=aarch64-linux-ohos",
            ])
        # E002/readonly_tmp: /tmp is erofs read-only on OHOS workers;
        # export the writable HMBS tmpdir so configure/conftest/clang
        # temp files avoid /tmp (libseqlib/backuppc-rsync precedent).
        # tc.environment() lands in conanautotoolstoolchain.sh; build()
        # additionally sets os.environ plus an inline prefix because the
        # profile conanbuildenv aggregation may not carry TMPDIR.
        tmpdir = self._writable_tmpdir()
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        env = tc.environment()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        tc.generate(env=env)
        self.output.info("libgc: writable tmpdir propagated via buildenv: %s" % tmpdir)

    def _writable_tmpdir(self):
        """E002/readonly_tmp: OHOS /tmp is erofs read-only.

        Reuse the HMBS-injected writable task tmpdir (TMPDIR/TMP/TEMP/
        HMBS_TMPDIR plus HMBS_AUTOCONF_MKTEMP_FALLBACK when it carries a
        path); probe writability and fall back to $HOME/tmp/libgc-8.2.12.
        Only replaces the temp-file root; never deletes tests.
        """
        candidates = []
        fallback_var = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK", "")
        if fallback_var and fallback_var not in ("0", "1"):
            candidates.append(fallback_var)
        for var in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR"):
            val = os.environ.get(var, "")
            if val and val != "/tmp" and val not in candidates:
                candidates.append(val)
        for cand in candidates:
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs_probe")
                with open(probe, "w") as handle:
                    handle.write("probe")
                try:
                    os.remove(probe)
                except OSError:
                    pass
                return cand
            except OSError:
                continue
        fallback = os.path.join(os.path.expanduser("~"), "tmp", "libgc-8.2.12")
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            fallback = self.build_folder or os.getcwd()
        return fallback

    def _resolve_cc(self):
        """Return a verified C compiler path (libseqlib-round10 pattern).

        The aggregated conanbuild.sh CC may point at a profile-hardcoded
        clang that behaves differently on this worker; autoconf hides the
        real error inside config.log. Probe conf value first (if it is a
        file), then PATH (hmbs prepends tool dirs), then known OHOS
        locations. Last resort is the conf value / bare clang.
        """
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            compilers = {}
        conf_val = compilers.get("c") or ""
        if conf_val and os.path.isfile(conf_val):
            return conf_val
        found = shutil.which("clang")
        if found:
            return found
        for cand in ("/data/service/hnp/bin/clang",
                     "/system/bin/clang"):
            if cand and os.path.isfile(cand):
                return cand
        return conf_val or "clang"

    def _smoke_test_cc(self, cc):
        """Compile+link a minimal C probe before configure (round-10)."""
        self.output.info("libgc: CC smoke test with '%s'" % cc)
        try:
            self.run('"%s" --version' % cc, env="conanbuild")
        except Exception as exc:
            self.output.warning("libgc: CC --version failed: %s" % exc)
        probe_src = os.path.join(self.build_folder, "_hmbs_cc_probe.c")
        probe_bin = os.path.join(self.build_folder, "_hmbs_cc_probe")
        try:
            with open(probe_src, "w", encoding="utf-8") as f:
                f.write("int main(void){return 0;}\n")
        except OSError as exc:
            self.output.warning("libgc: cannot write CC probe: %s" % exc)
            return
        try:
            self.run('"%s" "%s" -o "%s"' % (cc, probe_src, probe_bin),
                     env="conanbuild")
            self.output.info("libgc: CC smoke test link OK")
        except Exception as exc:
            self.output.warning("libgc: CC smoke test FAILED: %s" % exc)
            raise
        finally:
            for p in (probe_src, probe_bin):
                try:
                    if os.path.isfile(p):
                        os.remove(p)
                except OSError:
                    pass

    def _dump_config_log(self):
        """Print config.log tail so the hidden compiler error is visible."""
        for folder in (self.build_folder, self.source_folder):
            if not folder:
                continue
            log_path = os.path.join(folder, "config.log")
            if os.path.isfile(log_path):
                try:
                    with open(log_path, "r", encoding="utf-8",
                              errors="replace") as f:
                        lines = f.read().splitlines()
                    tail = lines[-80:] if len(lines) > 80 else lines
                    self.output.info(
                        "libgc: config.log tail (%s):\n%s"
                        % (log_path, "\n".join(tail)))
                except OSError as exc:
                    self.output.warning(
                        "libgc: cannot read config.log: %s" % exc)
                return

    def _working_shell(self):
        """Pick a shell that exists on this worker.

        The shared profile sets CONFIG_SHELL/SHELL to
        /data/service/hnp/bin/bash, which is absent on some true-machine
        workers (configure re-exec fails with
        "inaccessible or not found" at configure[139]). HMBS guarantees
        /bin/sh on those workers; OHOS devices provide /system/bin/sh.
        Probe the filesystem instead of trusting the profile value.
        """
        for cand in ("/bin/sh", "/system/bin/sh"):
            if cand and os.path.isfile(cand):
                return cand
        for cand in (os.environ.get("CONFIG_SHELL"), os.environ.get("SHELL")):
            if cand and os.path.isfile(cand):
                return cand
        found = shutil.which("sh") or shutil.which("bash")
        if found:
            return found
        return "/bin/sh"

    def _parse_make_check_log(self, log_path):
        """Parse automake test-suite.log for TOTAL/PASS/FAIL/SKIP counts."""
        total = passed = failed = skipped = 0
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            m = re.search(r"#\s*TOTAL:\s*(\d+)", content)
            if m:
                total = int(m.group(1))
            m = re.search(r"#\s*PASS:\s*(\d+)", content)
            if m:
                passed = int(m.group(1))
            m = re.search(r"#\s*FAIL:\s*(\d+)", content)
            if m:
                failed = int(m.group(1))
            m = re.search(r"#\s*SKIP:\s*(\d+)", content)
            if m:
                skipped = int(m.group(1))
            m = re.search(r"#\s*XFAIL:\s*(\d+)", content)
            if m:
                passed += int(m.group(1))
                total += int(m.group(1))
            if total == 0:
                passes = len(re.findall(r"^(PASS|XPASS):", content, re.MULTILINE))
                fails = len(re.findall(r"^(FAIL|XFAIL):", content, re.MULTILINE))
                skips = len(re.findall(r"^SKIP:", content, re.MULTILINE))
                total = passes + fails + skips
                passed = passes
                failed = fails
                skipped = skips
        except OSError:
            pass
        return total, passed, failed, skipped

    def _emit_upstream_marker(self, total, passed, failed, skipped):
        executed = passed + failed
        status = "passed" if (total > 0 and failed == 0 and executed == total) else "failed"
        if total == 0:
            status = "failed"
        marker = {
            "status": status,
            "framework": "autotools-make-check",
            "command": "make check",
            "discovered": total,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        return marker

    def _fix_file(self, relpath, replacements):
        """Apply exact-substring replacements; fail loudly on anchor drift."""
        from conan.errors import ConanException
        path = os.path.join(self.source_folder, relpath)
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        for old, new in replacements:
            if old not in content:
                raise ConanException(
                    "libgc: anchor not found in %s: %r" % (relpath, old[:60]))
            content = content.replace(old, new)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        self.output.info("libgc: fixed %s (%d replacements)"
                         % (relpath, len(replacements)))

    def _apply_ohos_source_fixes(self):
        # All anchors verified against gc-8.2.12.tar.gz. Exact-string edits
        # replace the former patch files, so autoconf hunk drift can no
        # longer break the build; any upstream change fails loudly above.
        guess_entry = (
            "    *:HarmonyOS:*:*)\n"
            '\tcase "$UNAME_MACHINE" in\n'
            "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
            "\t    armv7*|armv8*) MACHINE=arm ;;\n"
            "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
            "\t    i?86)         MACHINE=i686 ;;\n"
            '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
            "\tesac\n"
            '\techo "${MACHINE}-unknown-linux-ohos"\n'
            "\texit\n"
            "\t;;\n"
        )
        self._fix_file("config.guess", [
            ("case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in\n"
             "    *:NetBSD:*:*)",
             "case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in\n"
             + guess_entry + "    *:NetBSD:*:*)"),
        ])
        self._fix_file("config.sub", [
            ("\t\t\tandroid-linux)\n"
             "\t\t\t\tbasic_machine=$field1-unknown\n"
             "\t\t\t\tbasic_os=linux-android\n",
             "\t\t\tandroid-linux)\n"
             "\t\t\t\tbasic_machine=$field1-unknown\n"
             "\t\t\t\tbasic_os=linux-android\n"
             "\t\t\t;;\n"
             "\t\t\tohos-linux)\n"
             "\t\t\t\tbasic_machine=$field1-unknown\n"
             "\t\t\t\tbasic_os=linux-ohos\n"),
            ("\tgnu* | android* | bsd* | mach*",
             "\tgnu* | android* | ohos* | bsd* | mach*"),
            ("\t\t   | linux-musl* | linux-relibc* | linux-uclibc* )",
             "\t\t   | linux-musl* | linux-relibc* | linux-uclibc* | linux-ohos* )"),
        ])
        # E011: HMDFS creates dirs with 0700 under umask 077 causing
        # config.status 'Permission denied creating subs1.awk'.
        self._fix_file("configure", [
            ("umask 077", "umask 022"),
        ])
        # OHOS musl lacks pthread_cancel: no GC_HAVE_PTHREAD_EXIT.
        self._fix_file(os.path.join("include", "gc_config_macros.h"), [
            ("# if !defined(GC_HAVE_PTHREAD_EXIT) \\\n"
             "     && !defined(HOST_ANDROID) && !defined(__ANDROID__) \\",
             "# if !defined(GC_HAVE_PTHREAD_EXIT) \\\n"
             "     && !defined(HOST_ANDROID) && !defined(__ANDROID__) && !defined(__OHOS__) \\"),
        ])
        # OHOS musl lacks pthread_setcancelstate: no CANCEL_SAFE.
        self._fix_file(os.path.join("include", "private", "gcconfig.h"), [
            ("#if defined(UNIX_LIKE) && defined(THREADS) && !defined(NO_CANCEL_SAFE) \\\n"
             "    && !defined(HOST_ANDROID)",
             "#if defined(UNIX_LIKE) && defined(THREADS) && !defined(NO_CANCEL_SAFE) \\\n"
             "    && !defined(HOST_ANDROID) && !defined(__OHOS__)"),
        ])

    def build(self):
        # E002/readonly_tmp: process-level writable TMPDIR so autoconf
        # conftest, mktemp and clang temp files never fall back to
        # read-only /tmp (libseqlib/unixodbc precedent). Only replaces
        # the temp-file root; tests are untouched.
        _tmpdir = self._writable_tmpdir()
        try:
            os.makedirs(_tmpdir, exist_ok=True)
        except OSError:
            pass
        for _key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[_key] = _tmpdir
        self.output.info("libgc: writable tmpdir for build(): %s" % _tmpdir)
        apply_conandata_patches(self)
        self._apply_ohos_source_fixes()
        # Toolchain env (CC/CFLAGS/LDFLAGS with OHOS sysroot) comes from
        # AutotoolsToolchain via generate(). The shared profile exports
        # CONFIG_SHELL/SHELL=/data/service/hnp/bin/bash, which does not
        # exist on some true-machine workers; autoconf re-execs via
        # $CONFIG_SHELL and dies at configure[139] with "inaccessible or
        # not found". Invoke configure explicitly with a probed shell and
        # override both vars on the command line (prefix wins over the
        # sourced conanbuild.sh). Do not bypass with bare CC=clang.
        autotools = Autotools(self)
        shell = self._working_shell()
        # Round-10 strategy (different from TMPDIR-only): pin and
        # smoke-test the exact compiler before configure so the raw
        # toolchain stderr reaches the log instead of hiding in
        # config.log; explicit CC= prefix stops configure from picking
        # another compiler out of the aggregated conanbuild.sh env.
        cc = self._resolve_cc()
        self.output.info("libgc: resolved CC='%s' TMPDIR='%s'" % (cc, _tmpdir))
        self._smoke_test_cc(cc)
        configure_script = os.path.join(self.source_folder, "configure")
        configure_args = getattr(autotools, "_configure_args", "") or ""
        cmd = (f"CC=\"{cc}\" CONFIG_SHELL={shell} SHELL={shell} TMPDIR=\"$TMPDIR\" TMP=\"$TMP\" TEMP=\"$TEMP\" "
               + shlex.join([shell, configure_script]))
        if configure_args:
            cmd = f"{cmd} {configure_args}"
        self.output.info(f"libgc: configure with shell {shell} tmpdir {_tmpdir}")
        # env="conanbuild" aggregates AutotoolsToolchain flags (OHOS
        # sysroot/target) plus the TMPDIR defined in generate(); the
        # inline prefix wins over profile ordering (libseqlib precedent).
        try:
            self.run(cmd, cwd=self.build_folder, env="conanbuild")
        except Exception:
            self._dump_config_log()
            raise
        # E011 fix: HMDFS umask 077 creates dirs with 0700 perms; use 022
        for folder in (self.source_folder, self.build_folder):
            config_status = os.path.join(folder, "config.status")
            if os.path.isfile(config_status):
                with open(config_status, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                if "umask 077" in content:
                    content = content.replace("umask 077", "umask 022")
                    with open(config_status, "w", encoding="utf-8") as f:
                        f.write(content)
        autotools.make()
        # L1: Run upstream official test suite (make check)
        autotools.make(args=["check"])
        total, passed, failed, skipped = 0, 0, 0, 0
        for candidate in (
            os.path.join(self.source_folder, "test-suite.log"),
            os.path.join(self.build_folder, "test-suite.log"),
        ):
            if os.path.isfile(candidate):
                total, passed, failed, skipped = self._parse_make_check_log(candidate)
                if total > 0:
                    break
        marker = self._emit_upstream_marker(total, passed, failed, skipped)
        # Persist summary for test_package re-emit (build() skipped on cache hit)
        try:
            res_dir = os.path.join(self.build_folder, "upstream_summary")
            os.makedirs(res_dir, exist_ok=True)
            save(self, os.path.join(res_dir, "upstream_test_summary.json"),
                 json.dumps(marker, ensure_ascii=False, indent=2))
        except Exception as exc:
            self.output.warning(f"libgc: could not stage upstream summary: {exc}")
        if total == 0:
            raise ConanInvalidConfiguration("libgc: make check produced no test-suite.log counts")
        if failed != 0:
            raise ConanInvalidConfiguration(f"libgc: make check failed {failed}/{total}")

    def _write_install_shim(self):
        # E182/E188 (lzop/xeyes/adms precedent): the HMBS install shim
        # only accepts single-file two-arg calls and may depend on a
        # writable temp area; libtool's `install -c .libs/libgc.a dest`
        # followed by `chmod 644 dest` dies with "No such file" when the
        # copy never lands. Write a cp/mkdir shim (executable via open
        # mode, HMBS_CAP_CHMOD=0) that always mkdir -p's the destination
        # parent and tolerates chmod failures. Returns shim path.
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
                    "  mkdir -p \"$(dirname \"$dest\")\"\n"
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
            except OSError:
                pass
            raise
        try:
            os.chmod(install, 0o755)
        except OSError:
            pass  # HMBS_CAP_CHMOD=0
        return install

    def _redirect_install_to_shim(self, root, shim_install):
        # configure bakes the probed install path into every generated
        # Makefile's INSTALL variable; redirect it to our shim so
        # `make install` never depends on the HMBS shim's arg limits or
        # temp area (INSTALL_DATA/INSTALL_PROGRAM reference ${INSTALL}).
        # Returns the original install program path (first token) so the
        # caller can also patch the generated libtool script, which
        # captured the same probe result and ignores Makefile INSTALL.
        orig_prog = None
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
                    if orig_prog is None:
                        _val = _stripped[len("INSTALL = "):].strip()
                        _prog = _val.split()[0] if _val.split() else None
                        if _prog and "/install" in _prog:
                            orig_prog = _prog
                    _indent = _line[:len(_line) - len(_stripped)]
                    _lines.append(f"{_indent}INSTALL = {shim_install}\n")
                    _changed = True
                else:
                    _lines.append(_line)
            if _changed:
                with open(_mp, "w", encoding="utf-8") as _f:
                    _f.write("".join(_lines))
        return orig_prog

    def _redirect_libtool_install_to_shim(self, root, orig_prog, shim_install):
        # Best-effort: the generated libtool script captured configure's
        # install probe (absolute HMBS shim path) and uses it for
        # `libtool --mode=install` regardless of Makefile INSTALL.
        # Replace that exact path with our shim; skip silently when the
        # anchor is absent (e.g. other workers resolved plain `install`).
        if not orig_prog:
            return 0
        patched = 0
        for _root, _, _files in os.walk(root):
            if "libtool" not in _files:
                continue
            _lp = os.path.join(_root, "libtool")
            try:
                with open(_lp, "r", encoding="utf-8", errors="ignore") as _f:
                    _content = _f.read()
            except OSError:
                continue
            if orig_prog not in _content:
                continue
            _content = _content.replace(orig_prog, shim_install)
            try:
                with open(_lp, "w", encoding="utf-8") as _f:
                    _f.write(_content)
                patched += 1
            except OSError:
                continue
        return patched

    def package(self):
        # package() runs without the build() os.environ overrides on a
        # fresh worker step: re-establish the writable TMPDIR so the
        # install shim/libtool temp files avoid read-only /tmp.
        _tmpdir = self._writable_tmpdir()
        try:
            os.makedirs(_tmpdir, exist_ok=True)
        except OSError:
            pass
        for _key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[_key] = _tmpdir
        if self.settings.os == "OHOS":
            shim = self._write_install_shim()
            orig_prog = None
            for _root in {self.source_folder, self.build_folder}:
                if _root and os.path.isdir(_root):
                    _prog = self._redirect_install_to_shim(_root, shim)
                    orig_prog = orig_prog or _prog
            patched = 0
            for _root in {self.source_folder, self.build_folder}:
                if _root and os.path.isdir(_root):
                    patched += self._redirect_libtool_install_to_shim(
                        _root, orig_prog, shim)
            self.output.info(
                "libgc: INSTALL redirected to shim for package() "
                "(orig=%s, libtool patched=%d)" % (orig_prog, patched))
        autotools = Autotools(self)
        autotools.install()
        # Ship upstream summary for test_package stage evidence
        staged = os.path.join(self.build_folder, "upstream_summary", "upstream_test_summary.json")
        if os.path.isfile(staged):
            res_dir = os.path.join(self.package_folder, "res")
            os.makedirs(res_dir, exist_ok=True)
            copy(self, "upstream_test_summary.json",
                 src=os.path.join(self.build_folder, "upstream_summary"),
                 dst=res_dir)
        # R26: libgc is not a system同名 library on OHOS (/lib has no libgc); keep shared objects.
        # Remove libtool archives (.la); they are never shipped. Previous
        # code called copy() with identical src/dst which Conan 2 rejects
        # ("src and dst must have different values"); rm() is the correct API.
        try:
            rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        except Exception:
            # Fallback when lib dir is absent or rm() is unavailable.
            try:
                for root, _, files in os.walk(os.path.join(self.package_folder, "lib")):
                    for fn in files:
                        if fn.endswith(".la"):
                            os.remove(os.path.join(root, fn))
            except OSError:
                pass

    def package_info(self):
        self.cpp_info.libs = ["gc"]
        self.cpp_info.system_libs = ["pthread", "dl"]
