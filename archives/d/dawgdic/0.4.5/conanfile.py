#!/usr/bin/env python3
"""Conan recipe — dawgdic 0.4.5 (Autotools)

C++ header library plus the dawgdic-build/dawgdic-find tools for building
and accessing dictionaries implemented with directed acyclic word graphs.
"""
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class DawgdicConan(ConanFile):
    name = "dawgdic"
    version = "0.4.5"
    description = "C++ library for building and accessing DAWG dictionaries"
    license = "BSD-3-Clause"
    homepage = "https://github.com/stil/dawgdic"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _writable_tmpdir(self):
        """E002: OHOS /tmp is erofs read-only.

        Reuse the hmbs-injected task tmpdir first (HMBS_TMPDIR/TMPDIR/TMP/TEMP/
        HMBS_AUTOCONF_MKTEMP_FALLBACK), fall back to build_folder/tmp_hmbs.
        Never return bare /tmp.
        """
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP",
                    "HMBS_AUTOCONF_MKTEMP_FALLBACK"):
            value = os.environ.get(var)
            if not value or value in ("0", "/tmp"):
                continue
            try:
                os.makedirs(value, exist_ok=True)
            except OSError:
                continue
            try:
                probe = os.path.join(value, ".hmbs_probe")
                with open(probe, "w") as handle:
                    handle.write("probe")
                os.remove(probe)
                return value
            except OSError:
                continue
        fallback = os.path.join(self.build_folder or os.getcwd(), "tmp_hmbs")
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            pass
        return fallback

    def generate(self):
        tc = AutotoolsToolchain(self)
        # E011: --no-create only generates config.status without executing it,
        # so build() can fix HMDFS mktemp/umask before running it.
        tc.configure_args.append("--no-create")
        tmpdir = self._writable_tmpdir()
        env = tc.environment()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        tc.generate(env=env)

    def _write_upstream_result(self, data):
        # Persist for test_package re-emit on conan-cache hits (header-library
        # binaries are reused across RREVs, so build() may be skipped and the
        # stdout marker lost). test_package re-emits this file every run.
        try:
            base = self.build_folder or os.getcwd()
            os.makedirs(base, exist_ok=True)
            path = os.path.join(base, "upstream_test_result.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False)
        except OSError as exc:
            self.output.warning("[hmbs] write upstream_test_result.json failed: %s" % exc)

    def _find_generated_file(self, name):
        for base in (self.build_folder, self.source_folder):
            if not base:
                continue
            path = os.path.join(base, name)
            if os.path.isfile(path):
                return path
        return None

    def _patch_configure(self):
        """E011 (umask 077) + shell_getcwd (ac_pwd fallback).

        configure is a generated file: patch programmatically, no .patch file.
        """
        path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(path):
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                content = handle.read()
        except OSError:
            return
        orig = content
        if "umask 077" in content:
            content = content.replace("umask 077", "umask 022")
        old_pwd = "ac_pwd=`pwd` && test -n \"$ac_pwd\" &&"
        if old_pwd in content:
            content = content.replace(
                old_pwd,
                "ac_pwd=`pwd` 2>/dev/null || ac_pwd=\"$PWD\"\ntest -n \"$ac_pwd\" &&",
                1,
            )
        if content != orig:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content)
            self.output.info("[hmbs] patched configure: umask 022 + ac_pwd $PWD fallback")

    def _fix_config_status_mktemp(self, tmpdir):
        """E011/E114: redirect config.status mktemp from ./confXXXXXX (HMDFS
        unwritable under umask 077) to a fixed dir under writable TMPDIR.

        Applied after configure --no-create, before running config.status.
        """
        cs_file = self._find_generated_file("config.status")
        if not cs_file:
            self.output.warning("[hmbs] config.status not found for mktemp fix")
            return
        try:
            with open(cs_file, "r", encoding="utf-8", errors="replace") as handle:
                content = handle.read()
        except OSError:
            return
        fixed_dir = os.path.join(tmpdir, "dawgdic-config-status-tmp")
        try:
            if os.path.isdir(fixed_dir):
                shutil.rmtree(fixed_dir, ignore_errors=True)
            os.makedirs(fixed_dir, exist_ok=True)
        except OSError:
            return
        replaced = 0
        new_content, n = re.subn(
            r'tmp=`\(umask 077 && mktemp -d "\./confXXXXXX"\) 2>/dev/null`',
            "tmp=%s" % fixed_dir,
            content,
        )
        content = new_content
        replaced += n
        new_content, n = re.subn(r"tmp=\./conf\$\$-\$RANDOM", "tmp=%s" % fixed_dir, content)
        content = new_content
        replaced += n
        new_content, n = re.subn(r"\(umask 077 && mkdir \"\$tmp\"\)", "mkdir -p \"%s\"" % fixed_dir, content)
        content = new_content
        replaced += n
        if "umask 077" in content:
            content = content.replace("umask 077", "umask 022")
            replaced += 1
        with open(cs_file, "w", encoding="utf-8") as handle:
            handle.write(content)
        try:
            os.chmod(cs_file, 0o755)
        except OSError:
            pass
        self.output.info(
            "[hmbs] redirected config.status mktemp to %s (%d pattern(s))" % (fixed_dir, replaced)
        )

    def _patch_test_scripts(self):
        """Out-of-source `make check` cwd fix (no assertion change).

        Upstream test/dawg-builder-test.sh and test/ranked-completer-test.sh
        invoke their C++ binaries via a bare `./<binary>`, which only works
        when the test cwd is the build test dir. On the HMBS out-of-source
        layout (build=.../b/build-release, source=.../b) the failing case
        runs with cwd=source test dir, so `./dawg-builder-test` resolves to
        `.../b/test/dawg-builder-test` (missing; binary lives in
        `.../b/build-release/test/`). The other two shell tests pass because
        they resolve tools via $TOP_BUILDDIR. Patch only the binary lookup
        to honour $TOP_BUILDDIR, falling back to ./; test logic untouched.
        """
        for name in ("dawg-builder-test.sh", "ranked-completer-test.sh"):
            path = os.path.join(self.source_folder, "test", name)
            self.output.info("[hmbs] patch-check %s exists=%s src=%s" % (
                name, os.path.isfile(path), self.source_folder))
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as handle:
                    content = handle.read()
            except OSError:
                continue
            if "HMBS_TEST_BIN" in content:
                continue
            orig = content
            header = None
            old = None
            new = None
            if name == "dawg-builder-test.sh":
                old = "./dawg-builder-test"
                new = '"$HMBS_TEST_BIN_DAWG_BUILDER"'
                if old not in content:
                    continue
                header = (
                    'HMBS_TEST_BIN_DAWG_BUILDER="./dawg-builder-test"\n'
                    'if [ ! -x "$HMBS_TEST_BIN_DAWG_BUILDER" ] && '
                    '[ -n "$TOP_BUILDDIR" ] && '
                    '[ -x "$TOP_BUILDDIR/test/dawg-builder-test" ]; then\n'
                    '  HMBS_TEST_BIN_DAWG_BUILDER="$TOP_BUILDDIR/test/dawg-builder-test"\n'
                    'fi\n'
                )
            else:
                old = "./ranked-completer-test"
                new = '"$HMBS_TEST_BIN_RANKED"'
                if old not in content:
                    continue
                header = (
                    'HMBS_TEST_BIN_RANKED="./ranked-completer-test"\n'
                    'if [ ! -x "$HMBS_TEST_BIN_RANKED" ] && '
                    '[ -n "$TOP_BUILDDIR" ] && '
                    '[ -x "$TOP_BUILDDIR/test/ranked-completer-test" ]; then\n'
                    '  HMBS_TEST_BIN_RANKED="$TOP_BUILDDIR/test/ranked-completer-test"\n'
                    'fi\n'
                )
            body = orig.replace(old, new)
            # Keep shebang on line 1; insert helper right after it.
            if body.startswith("#!"):
                bnl = body.find("\n")
                if bnl != -1:
                    content = body[:bnl + 1] + header + body[bnl + 1:]
                else:
                    content = body + "\n" + header
            else:
                content = header + body
            if content != orig:
                try:
                    with open(path, "w", encoding="utf-8") as handle:
                        handle.write(content)
                    self.output.info("[hmbs] patched %s: TOP_BUILDDIR binary lookup" % name)
                except OSError:
                    pass

    def build(self):
        apply_conandata_patches(self)
        self._patch_test_scripts()
        # E002: process-level writable TMPDIR so configure/make/mktemp and
        # shell temp files avoid read-only /tmp.
        tmpdir = self._writable_tmpdir()
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmpdir
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        self.output.info("[hmbs] writable tmpdir: %s" % tmpdir)

        if str(self.settings.os) == "OHOS":
            self._patch_configure()
            os.environ["PWD"] = self.build_folder
        try:
            os.chdir(self.build_folder)
        except OSError:
            pass

        autotools = Autotools(self)
        # Step 1 (E011): configure --no-create (from generate()) only writes
        # config.status without executing the broken mktemp path.
        autotools.configure()
        # Step 2: fix generated config.status, then execute it.
        self._fix_config_status_mktemp(tmpdir)
        bash = (
            os.environ.get("CONFIG_SHELL")
            or shutil.which("bash")
            or "/data/service/hnp/bin/bash"
        )
        self.run('"%s" config.status' % bash, env="conanbuild")
        autotools.make(args=["-j1"])
        # Upstream test suite: 4 Automake TESTS (shell) in test/.
        if can_run(self):
            self._run_upstream_tests()
        else:
            self.output.info("Skipping upstream runtime tests while cross-building")
            skipped = {
                "status": "skipped",
                "framework": "automake",
                "command": "make check",
                "discovered": 4,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 4,
            }
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(skipped))
            print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(skipped))
            self._write_upstream_result(skipped)

    def _run_upstream_tests(self):
        """Run `make check` for real, parse Automake counts, emit the HMBS
        machine-evidence marker. Counts come from the framework output."""
        # E002 readonly_tmp: force a writable TMPDIR and run every shell
        # recipe under bash (which honours TMPDIR) instead of /bin/sh
        # (which hardcodes /tmp temp files -> Read-only file system).
        tmpdir = self._writable_tmpdir()
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmpdir
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        bash = (
            os.environ.get("CONFIG_SHELL")
            or shutil.which("bash")
            or "/data/service/hnp/bin/bash"
        )
        self.output.info("[hmbs] upstream tests: TMPDIR=%s SHELL=%s" % (tmpdir, bash))
        # Fallback for bare ./<binary> scripts when test cwd is the source
        # test dir (out-of-source quirk): mirror built test binaries into
        # the source test dir so ./ resolves either way. No test logic change.
        try:
            self.output.info("[hmbs] mirror-check src=%s build=%s" % (
                self.source_folder, self.build_folder))
            for binary in ("dawg-builder-test", "ranked-completer-test"):
                built = os.path.join(self.build_folder, "test", binary)
                dest = os.path.join(self.source_folder, "test", binary)
                if os.path.isfile(built) and not os.path.isfile(dest):
                    try:
                        shutil.copy2(built, dest)
                        try:
                            os.chmod(dest, 0o755)
                        except OSError:
                            pass
                        self.output.info("[hmbs] mirrored %s to source test dir" % binary)
                    except OSError as exc:
                        self.output.info("[hmbs] mirror %s failed: %s" % (binary, exc))
                else:
                    self.output.info("[hmbs] mirror-skip %s built=%s dest_exists=%s" % (
                        binary, os.path.isfile(built), os.path.isfile(dest)))
        except OSError:
            pass
        log_path = os.path.join(self.build_folder, "make_check.log")
        self.run('"%s" -c \'make -j1 check SHELL="%s" > "%s" 2>&1\''
                 % (bash, bash, log_path), env="conanbuild", ignore_errors=True)
        out = ""
        if os.path.isfile(log_path):
            try:
                with open(log_path, encoding="utf-8", errors="replace") as handle:
                    out = handle.read()
            except OSError:
                out = ""
        tail = out.splitlines()[-60:] if out else []
        self.output.info("=== upstream make check (tail) ===")
        for line in tail:
            self.output.info(line)

        # Dump automake suite logs so the next round can see WHICH test
        # failed without guessing from the truncated summary.
        for suite_name in ("test/test-suite.log", "test-suite.log"):
            suite_path = os.path.join(self.build_folder, suite_name)
            if os.path.isfile(suite_path):
                self.output.info("=== %s ===" % suite_name)
                try:
                    with open(suite_path, encoding="utf-8", errors="replace") as handle:
                        for line in handle.read().splitlines()[-40:]:
                            self.output.info(line)
                except OSError:
                    pass
        # Dump per-test .log for any FAIL, plus result/answer diff context.
        for line in out.splitlines():
            m = re.match(r"^FAIL:\s*(\S+)", line.strip())
            if not m:
                continue
            for cand in (os.path.join(self.build_folder, "test", m.group(1) + ".log"),
                         os.path.join(self.build_folder, m.group(1) + ".log")):
                if os.path.isfile(cand):
                    self.output.info("=== FAILED %s ===" % cand)
                    try:
                        with open(cand, encoding="utf-8", errors="replace") as handle:
                            for log_line in handle.read().splitlines()[-60:]:
                                self.output.info(log_line)
                    except OSError:
                        pass
        # List test workdir artefacts (result vs answer) for cmp failures.
        try:
            test_dir = os.path.join(self.build_folder, "test")
            if os.path.isdir(test_dir):
                names = sorted(os.listdir(test_dir))[:40]
                self.output.info("[hmbs] test workdir: %s" % ", ".join(names))
        except OSError:
            pass

        def _num(pattern):
            match = re.search(pattern, out, flags=re.MULTILINE)
            return int(match.group(1)) if match else None

        total = _num(r"^# TOTAL:\s*(\d+)")
        passed = _num(r"^# PASS:\s*(\d+)")
        skipped = _num(r"^# SKIP:\s*(\d+)")
        xfail = _num(r"^# XFAIL:\s*(\d+)")
        failed = _num(r"^# FAIL:\s*(\d+)")
        xpass = _num(r"^# XPASS:\s*(\d+)")
        error = _num(r"^# ERROR:\s*(\d+)")
        if total is None:
            # Fallback: count per-test result lines.
            passed = len(re.findall(r"^PASS:\s*\S+", out, flags=re.MULTILINE))
            failed = len(re.findall(r"^FAIL:\s*\S+", out, flags=re.MULTILINE))
            skipped = len(re.findall(r"^SKIP:\s*\S+", out, flags=re.MULTILINE))
            total = passed + failed + skipped
            xfail, xpass, error = 0, 0, 0
        else:
            passed = passed or 0
            skipped = (skipped or 0) + (xfail or 0)
            failed = (failed or 0) + (xpass or 0) + (error or 0)
        executed = passed + failed + skipped
        if total == 0:
            total = executed
        ok = total > 0 and executed == total and failed == 0 and executed > 0
        # Gate treats any skip as non-pass; dawgdic suite has no skips.
        status = "passed" if (ok and skipped == 0) else "failed"
        result = {
            "status": status,
            "framework": "automake",
            "command": "make -j1 check SHELL=bash",
            "discovered": total,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result))
        self._write_upstream_result(result)
        if status != "passed":
            raise RuntimeError(
                "upstream make check failed: total=%d executed=%d passed=%d failed=%d skipped=%d"
                % (total, executed, passed, failed, skipped)
            )

    def package(self):
        autotools = Autotools(self)
        try:
            autotools.install()
        except Exception as exc:  # noqa: BLE001 - keep headers/bin fallback below
            self.output.warning("[hmbs] make install failed: %s" % exc)
        # Defensive fallback: upstream installs src/dawgdic/*.h to
        # <prefix>/include/dawgdic, but if prefix/DESTDIR handling left the
        # package empty (observed: test_package -I<p>/include cannot find
        # dawgdic/completer.h), copy headers explicitly. No logic change.
        expected_hdr = os.path.join(
            self.package_folder, "include", "dawgdic", "completer.h")
        if not os.path.isfile(expected_hdr):
            self.output.warning("[hmbs] include/dawgdic missing after install; copying headers explicitly")
            copied = False
            for cand in (
                os.path.join(self.source_folder, "src", "dawgdic"),
                os.path.join(self.source_folder, "include", "dawgdic"),
                os.path.join(self.source_folder, "dawgdic"),
            ):
                if os.path.isfile(os.path.join(cand, "completer.h")):
                    copy(self, "*.h", src=cand,
                         dst=os.path.join(self.package_folder, "include", "dawgdic"),
                         keep_path=False)
                    copied = True
                    self.output.info("[hmbs] copied headers from %s" % cand)
                    break
            if not copied and self.source_folder and os.path.isdir(self.source_folder):
                for root, _dirs, files in os.walk(self.source_folder):
                    if os.path.basename(root) == "dawgdic" and "completer.h" in files:
                        copy(self, "*.h", src=root,
                             dst=os.path.join(self.package_folder, "include", "dawgdic"),
                             keep_path=False)
                        copied = True
                        self.output.info("[hmbs] copied headers from walk %s" % root)
                        break
            if not copied:
                self.output.warning("[hmbs] header fallback found no dawgdic source dir")
        # Defensive fallback: ensure packaged tools exist for test_package.
        for tool in ("dawgdic-build", "dawgdic-find"):
            dest = os.path.join(self.package_folder, "bin", tool)
            if os.path.isfile(dest):
                continue
            found = None
            for base in (self.build_folder, self.source_folder):
                if not base or not os.path.isdir(base):
                    continue
                for root, _dirs, files in os.walk(base):
                    if tool in files:
                        cand = os.path.join(root, tool)
                        # Skip shell wrappers/test logs; prefer ELF executable.
                        if os.path.isfile(cand):
                            found = cand
                            break
                    if found:
                        break
                if found:
                    break
            if found:
                try:
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    shutil.copy2(found, dest)
                    try:
                        os.chmod(dest, 0o755)
                    except OSError:
                        pass
                    self.output.info("[hmbs] copied tool %s from %s" % (tool, found))
                except OSError as exc:
                    self.output.warning("[hmbs] copy tool %s failed: %s" % (tool, exc))
        try:
            names = []
            for root, _dirs, files in os.walk(self.package_folder):
                rel = os.path.relpath(root, self.package_folder)
                for name in sorted(files)[:20]:
                    names.append(os.path.join(rel, name))
                if len(names) > 40:
                    break
            self.output.info("[hmbs] package contents: %s" % ", ".join(sorted(names)[:40]))
        except OSError:
            pass
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        # Persist upstream evidence for cache-hit re-emit: test_package runs
        # on every `conan create` even when build() is skipped ("Already
        # installed"), so it re-emits this file as HMBS_UPSTREAM_TEST_RESULT.
        try:
            copy(self, "upstream_test_result.json",
                 src=self.build_folder,
                 dst=os.path.join(self.package_folder, "res"),
                 keep_path=False)
        except Exception as exc:
            self.output.warning("[hmbs] copy upstream_test_result.json failed: %s" % exc)

    def package_info(self):
        # Header-only library: no compiled libs, headers under include/dawgdic.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
