#!/usr/bin/env python3
"""Conan recipe for jpcre2 10.32.01 (Autotools, header-only C++ wrapper for PCRE2).

Upstream: https://github.com/jpcre2/jpcre2 (tag 10.32.01).
Header-only: src/jpcre2.hpp is installed to include/; consumers link the
PCRE2 C library (8/16/32-bit widths) re-exported from pcre2/10.48.

Upstream tests: 11 automake TESTS (src/Makefile.am TESTS lines, thread tests
excluded upstream via commented TESTS +=): test_match, test_replace,
test_shorts, test16, test32, test0, test_issue_29, test, testio, testme,
testmd. Enabled with --enable-test and executed via `make check` in build().
"""

import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


_UPSTREAM_TESTS_TOTAL = 11  # TESTS entries in src/Makefile.am (see notes.md audit)


class Jpcre2Conan(ConanFile):
    name = "jpcre2"
    version = "10.32.01"
    description = "C++ wrapper for PCRE2 library (header-only)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/jpcre2/jpcre2"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Full-width PCRE2 (8/16/32-bit) so test16/test32 link and pass.
        self.requires("pcre2/10.48")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--enable-test")
        tc.generate()
        deps = AutotoolsDeps(self)
        deps.generate()
        # HMBS shell_getcwd: HNP bash (/data/service/hnp/bin/bash) cannot
        # getcwd on the HMDFS build dir ("working directory cannot be
        # determined"), while /bin/sh can. Honor the HMBS-injected
        # SHELL/CONFIG_SHELL (both /bin/sh) and never fall back to HNP bash.
        env = Environment()
        for var in ("CONFIG_SHELL", "SHELL"):
            val = os.environ.get(var)
            if val and os.path.isfile(val):
                env.define(var, val)
            else:
                env.define(var, "/bin/sh")
        env.vars(self).save_script("hmbs_shell")

    def build(self):
        apply_conandata_patches(self)
        self._fix_conanbuild_shell()
        autotools = Autotools(self)
        autotools.configure()
        # HMDFS install compat: configure bakes a system `install`
        # (chmod/hardlink) that silently drops files on the device
        # (HMBS_CAP_CHMOD=0/HARDLINK=0). Redirect before make so the
        # build tree and the later `make install` use cp/mkdir semantics.
        self._redirect_install_to_shim(self._write_install_shim())
        autotools.make(args=["-j1"])
        self._run_upstream_tests()

    def _hmbs_shell(self):
        # Prefer HMBS-injected CONFIG_SHELL/SHELL (both /bin/sh on the
        # preflight device); never default to HNP bash which fails getcwd
        # on HMDFS. Fall back to /bin/sh when unset or missing.
        for var in ("CONFIG_SHELL", "SHELL"):
            val = os.environ.get(var)
            if val and os.path.isfile(val):
                return val
        for cand in ("/bin/sh", shutil.which("sh") or ""):
            if cand and os.path.isfile(cand):
                return cand
        return "/bin/sh"

    def _fix_conanbuild_shell(self):
        # Host profile may reference /data/service/hnp/bin/bash which hits
        # "shell-init: error retrieving current directory" on HMDFS.
        # Rewrite generated env scripts to the working /bin/sh.
        shell = self._hmbs_shell()
        bad = "/data/service/hnp/bin/bash"
        if os.path.isdir(self.generators_folder):
            for fname in os.listdir(self.generators_folder):
                if not fname.endswith(".sh"):
                    continue
                fpath = os.path.join(self.generators_folder, fname)
                with open(fpath, "r", encoding="utf-8",
                          errors="replace") as f:
                    content = f.read()
                if bad in content:
                    content = content.replace(bad, shell)
                    with open(fpath, "w", encoding="utf-8") as f:
                        f.write(content)

    def _write_install_shim(self):
        # OHOS HMDFS rejects chmod from toybox install and drops the
        # single-header install while `make install` still exits 0
        # (test_package then fails with 'jpcre2.hpp file not found').
        # Use cp/mkdir semantics with chmod as best effort.
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        os.makedirs(shim_dir, exist_ok=True)
        install = os.path.join(shim_dir, "install")
        content_lines = [
            "#!/bin/sh",
            "set -eu",
            "mode=",
            "while [ $# -gt 0 ]; do",
            "  case \"$1\" in",
            "    -p|-c) shift ;;",
            "    -m) [ $# -ge 2 ] || exit 2; mode=$2; shift 2 ;;",
            "    -d) shift; [ $# -gt 0 ] || exit 2; mkdir -p \"$@\"; exit 0 ;;",
            "    --) shift; break ;;",
            "    -*) shift ;;",
            "    *) break ;;",
            "  esac",
            "done",
            "[ $# -ge 2 ] || exit 2",
            "dest=",
            "for arg in \"$@\"; do dest=$arg; done",
            "count=$(($# - 1))",
            "mkdir -p \"$(dirname \"$dest\")\"",
            "i=1",
            "for src in \"$@\"; do",
            "  [ $i -gt $count ] && break",
            "  cp -f \"$src\" \"$dest\"",
            "  if [ -n \"$mode\" ]; then",
            "    if [ -d \"$dest\" ]; then",
            "      chmod \"$mode\" \"$dest/${src##*/}\" 2>/dev/null || true",
            "    else",
            "      chmod \"$mode\" \"$dest\" 2>/dev/null || true",
            "    fi",
            "  fi",
            "  i=$((i + 1))",
            "done",
        ]
        script = "\n".join(content_lines) + "\n"
        fd = os.open(
            install, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(script)
        return install

    def _redirect_install_to_shim(self, shim_install):
        # Rewrite generated Makefiles so make/make install use the shim
        # for INSTALL/install_sh/mkdir helpers. Idempotent; safe to call
        # in both build() and package() (same build_folder).
        replacements = {
            "INSTALL = ": "INSTALL = {}".format(shim_install),
            "install_sh = ": "install_sh = {}".format(shim_install),
            "mkdir_p = ": "mkdir_p = {} -d".format(shim_install),
            "MKDIR_P = ": "MKDIR_P = {} -d".format(shim_install),
        }
        bf = self.build_folder or ""
        if not bf or not os.path.isdir(bf):
            return
        for root, _, files in os.walk(bf):
            for name in files:
                if name not in ("Makefile", "GNUmakefile"):
                    continue
                makefile = os.path.join(root, name)
                try:
                    with open(makefile, "r", encoding="utf-8",
                              errors="ignore") as stream:
                        file_lines = stream.readlines()
                except Exception:
                    continue
                changed = False
                output = []
                for line in file_lines:
                    stripped = line.lstrip()
                    replacement = next((
                        value for prefix, value in replacements.items()
                        if stripped.startswith(prefix)), None)
                    if replacement is None:
                        output.append(line)
                        continue
                    if line.endswith("\r\n"):
                        ending = "\r\n"
                    elif line.endswith("\n"):
                        ending = "\n"
                    else:
                        ending = ""
                    indent = line[:len(line) - len(stripped)]
                    output.append(indent + replacement + ending)
                    changed = True
                if changed:
                    with open(makefile, "w", encoding="utf-8") as stream:
                        stream.writelines(output)

    def _writable_tmpdir(self):
        # HMBS readonly_tmp (E002): /tmp is erofs read-only on the device.
        # Honor the HMBS-injected TMPDIR/TMP/TEMP (writable runtime tmp);
        # fall back to the build folder when unset or missing. Only the
        # temporary-file root is redirected; the test suite itself is kept.
        for var in ("TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(var)
            if val and os.path.isdir(val):
                return val
        fallback = self.build_folder or os.getcwd()
        try:
            os.makedirs(fallback, exist_ok=True)
        except Exception:
            pass
        return fallback

    def _dump_upstream_failure_logs(self, output):
        # On failure, surface which TEST failed and why. `make check` only
        # prints "FAIL: <name>"; the root cause (assert/abort message) lives
        # in src/test-suite.log and the per-test src/<name>.log. Emit them
        # (bounded) so the next preflight round can diagnose precisely.
        # Test口径 is unchanged: this is observability only.
        try:
            candidates = []
            bf = self.build_folder or ""
            for rel in ("src/test-suite.log", "test-suite.log"):
                p = os.path.join(bf, rel) if bf else rel
                if os.path.isfile(p):
                    candidates.append(p)
            # Per-test logs for the tests automake reported as FAIL.
            for name in re.findall(r"^FAIL:\s+(\S+)", output, re.M):
                base = name.strip()
                for rel in (os.path.join("src", base + ".log"),
                            base + ".log"):
                    p = os.path.join(bf, rel) if bf else rel
                    if os.path.isfile(p) and p not in candidates:
                        candidates.append(p)
            for p in candidates[:6]:
                try:
                    with open(p, "r", encoding="utf-8",
                              errors="replace") as f:
                        content = f.read()
                    if len(content) > 12000:
                        content = content[:12000] + "\n...[truncated]..."
                    self.output.info(
                        "=== upstream log %s ===\n%s" % (p, content))
                except Exception as e:
                    self.output.info(
                        "=== upstream log %s unreadable: %s ===" % (p, e))
        except Exception as e:
            self.output.info("=== upstream log dump failed: %s ===" % (e,))

    def _run_upstream_tests(self):
        """Run `make check` and emit the HMBS upstream-test marker.

        Parses automake PASS/FAIL/SKIP lines plus the `# TOTAL/# PASS`
        summary. Any failure raises so conan create goes red.
        """
        shell = self._hmbs_shell()
        # E002: run the suite with a writable temp root; inherit the rest
        # of the HMBS/conan environment.
        tmpdir = self._writable_tmpdir()
        env = dict(os.environ)
        for var in ("TMPDIR", "TMP", "TEMP"):
            env[var] = tmpdir
        proc = subprocess.run(
            [shell, "-c", "make check"],
            cwd=self.build_folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=3600,
            env=env,
        )
        output = proc.stdout or ""
        # Leave the raw automake trace in the log for L1c auditing.
        tail = output[-4000:] if len(output) > 4000 else output
        self.output.info("=== upstream make check tail ===\n" + tail)
        # Always list per-test outcomes on one line each for attribution.
        for line in output.splitlines():
            s = line.strip()
            if re.match(r"^(PASS|FAIL|SKIP|XFAIL|ERROR):\s+\S+", s):
                self.output.info("=== upstream test: %s ===" % s)

        passed = len(re.findall(r"^PASS:\s+\S+", output, re.M))
        failed = len(re.findall(r"^FAIL:\s+\S+", output, re.M))
        skipped = len(re.findall(r"^(SKIP|XFAIL):\s+\S+", output, re.M))
        m_total = re.search(r"#\s*TOTAL:\s*(\d+)", output)
        m_pass = re.search(r"#\s*PASS:\s*(\d+)", output)
        m_fail = re.search(r"#\s*FAIL:\s*(\d+)", output)
        if m_total is not None:
            discovered = int(m_total.group(1))
        else:
            discovered = _UPSTREAM_TESTS_TOTAL
        executed = passed + failed
        if m_pass is not None and m_fail is not None:
            passed = int(m_pass.group(1))
            failed = int(m_fail.group(1))
            executed = passed + failed + skipped

        status = "passed" if (
            proc.returncode == 0
            and failed == 0
            and skipped == 0
            and executed == discovered
            and discovered == _UPSTREAM_TESTS_TOTAL
        ) else "failed"
        marker = {
            "status": status,
            "framework": "automake",
            "command": "make check",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
        if status != "passed":
            self._dump_upstream_failure_logs(output)
            raise RuntimeError(
                "upstream tests failed: returncode=%d passed=%d failed=%d "
                "skipped=%d discovered=%d" % (
                    proc.returncode, passed, failed, skipped, discovered
                )
            )

    def package(self):
        # Re-assert the shim at package() time (same build_folder) so
        # `make install` never invokes the HMDFS-incompatible install.
        try:
            self._redirect_install_to_shim(self._write_install_shim())
        except Exception as e:
            self.output.info("=== install shim redirect skipped: %s ===" % (e,))
        autotools = Autotools(self)
        autotools.install()
        copy(self, "LICENCE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # Deterministic fallback: upstream installs exactly one header via
        # src/Makefile.am include_HEADERS. Plain-Python copy is immune to
        # install-program/filesystem quirks and guarantees the consumer
        # test can find <jpcre2.hpp>. Test scope unchanged.
        copy(self, "jpcre2.hpp", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        header = os.path.join(self.package_folder, "include", "jpcre2.hpp")
        try:
            ok = os.path.isfile(header) and os.path.getsize(header) > 0
        except Exception:
            ok = False
        self.output.info("=== packaged header %s exists=%s ===" % (header, ok))
        if not ok:
            try:
                inc = os.path.join(self.package_folder, "include")
                listing = sorted(os.listdir(inc)) if os.path.isdir(inc) else []
            except Exception:
                listing = []
            self.output.info("=== include listing: %s ===" % (listing,))
            raise RuntimeError("jpcre2.hpp missing from package include/")

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "jpcre2")
        self.cpp_info.set_property("cmake_target_name", "jpcre2::jpcre2")
        self.cpp_info.set_property("pkg_config_name", "jpcre2")
        # Consumers include <jpcre2.hpp> which includes <pcre2.h>.
        self.cpp_info.requires = [
            "pcre2::pcre2-8",
            "pcre2::pcre2-16",
            "pcre2::pcre2-32",
        ]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
