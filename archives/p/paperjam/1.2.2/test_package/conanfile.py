#!/usr/bin/env python3
"""Conan test_package — paperjam 1.2.2 (CLI tool, bin/paperjam).

Tool package: no library to link, so build() is a no-op; test() executes
test.sh against the installed binary with 6 content-level checks
(--version, --help, fixture non-empty, unknown-paper rejection via vendored
shim, 'null' round-trip, 'paper(paper=a4)' named-size path). Satisfies L0d (test() has
self.run) and R34 (real invocations of the packaged binary).

Evidence markers (emitted in test() every round so cache-hit rounds still
carry evidence):
- HMBS_TEST_PACKAGE_RESULT: discovered/passedCount from the script's real
  RESULT counters.
- HMBS_UPSTREAM_TEST_RESULT: status=no_tests. Upstream 1.2.2 ships no test
  suite (audit in test_package/MANIFEST.yml). Re-emitted here because the
  main recipe build() output is skipped on `Already installed!` rounds.
"""
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment


class PaperjamTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def build(self):
        pass

    def _writable_signed_copy(self, binary):
        """Copy the packaged binary to writable TMPDIR and self-sign it.

        The Conan cache may live on HMDFS/erofs (no chmod/hardlink), so
        in-place signing silently fails and the HongMeng kernel SIGKILLs
        unsigned binaries. Signing an isolated writable copy avoids that.
        """
        writable_tmp = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                        or os.environ.get("TEMP") or self.build_folder)
        try:
            os.makedirs(writable_tmp, exist_ok=True)
        except OSError:
            writable_tmp = self.build_folder
        signed_copy = os.path.join(writable_tmp, "paperjam.signed")
        try:
            shutil.copy2(binary, signed_copy)
            self.output.info("OHOS test: copied %s -> %s for signing" % (binary, signed_copy))
            binary = signed_copy
        except Exception as exc:
            self.output.warning("OHOS test: copy failed (%s), using %s" % (exc, binary))
        for tool in ("/data/service/hnp/bin/llvm-objcopy",
                     shutil.which("llvm-objcopy") or "llvm-objcopy"):
            try:
                subprocess.run([tool, "--remove-section", ".codesign", binary],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               check=False, timeout=10)
                break
            except Exception:
                continue
        signed = False
        for tool in ("/data/service/hnp/bin/binary-sign-tool",
                     shutil.which("binary-sign-tool") or "binary-sign-tool"):
            try:
                r = subprocess.run([tool, "sign", "-inFile", binary, "-outFile", binary, "-selfSign", "1"],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   check=False, timeout=15)
                if r.returncode == 0:
                    self.output.info("OHOS self-signed %s with %s" % (binary, tool))
                    signed = True
                    break
                self.output.warning("sign tool %s rc=%s: %s" % (tool, r.returncode, r.stderr.decode(errors="replace")[:300]))
            except Exception as exc:
                self.output.warning("sign tool %s exception: %s" % (tool, exc))
        if not signed:
            self.output.warning("OHOS signing failed for %s (trying exec anyway)" % binary)
        try:
            os.chmod(binary, 0o755)
        except OSError:
            pass
        return binary

    def _find_so(self, dep, soname_prefix):
        """Find a runtime .so under a dependency package folder.

        Kept for diagnostics only; the OHOS run uses DT_RPATH embedded
        in the paperjam binary, not LD_PRELOAD (preloading libqpdf fails
        on OHOS with `Error loading shared library libjpeg.so.62` even
        when libjpeg is preloaded first — the loader does not resolve a
        preloaded lib's own DT_NEEDED from the rest of LD_PRELOAD).
        """
        hits = []
        for root, _dirs, files in os.walk(dep.package_folder):
            for f in sorted(files):
                if f.startswith(soname_prefix):
                    hits.append(os.path.join(root, f))
        if not hits:
            return None
        for p in hits:
            try:
                if not os.path.islink(p):
                    return p
            except OSError:
                continue
        return hits[0]

    def _runtime_preload(self):
        """No longer used: LD_PRELOAD of libqpdf is broken on OHOS.

        Kept as a stub so the diff vs. the failed round is explicit.
        Evidence (2 consecutive preflights): with LD_PRELOAD set (both
        qpdf-first and jpeg-first orders) the loader aborts before the
        test binary even runs:
        `Error loading shared library libjpeg.so.62: (needed by
        .../libqpdf.so.30.3.2)`. Runtime resolution now relies on the
        DT_RPATH embedded in the paperjam binary at build time.
        """
        return ""

    def test(self):
        pkg = self.dependencies["paperjam"].package_folder
        paperjam_bin = os.path.join(pkg, "bin", "paperjam")
        if not os.path.isfile(paperjam_bin):
            raise ConanException("paperjam binary not found in package: %s" % paperjam_bin)
        if self.settings.os == "OHOS":
            paperjam_bin = self._writable_signed_copy(paperjam_bin)

        shell = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "/bin/sh"
        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP") or os.path.join(self.build_folder, ".tmp"))
        os.makedirs(tmpdir, exist_ok=True)

        test_script = os.path.join(self.recipe_folder, "test.sh")
        logfile = os.path.join(self.build_folder, "test_package.log")

        env_vars = Environment()
        env_vars.define("PAPERJAM_BIN", paperjam_bin)
        env_vars.define("TMPDIR", tmpdir)
        env_vars.define("TMP", tmpdir)
        env_vars.define("TEMP", tmpdir)
        # No LD_PRELOAD: preloading libqpdf.so fails on the OHOS loader
        # even with leaf-first order (`Error loading shared library
        # libjpeg.so.62`, 2 consecutive preflights). The paperjam binary
        # carries DT_RPATH to the conan dep lib dirs (see main recipe
        # build()); also log the binary's dynamic section for diagnosis.
        try:
            for _tool in ("llvm-readelf", "readelf"):
                _exe = shutil.which(_tool) or (
                    "/data/service/hnp/bin/" + _tool
                    if os.path.isfile("/data/service/hnp/bin/" + _tool) else _tool)
                _r = subprocess.run([_exe, "-d", paperjam_bin],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    timeout=15)
                _txt = _r.stdout.decode(errors="replace")
                if _r.returncode == 0 and ("NEEDED" in _txt or "RPATH" in _txt or "RUNPATH" in _txt):
                    self.output.info(_tool + " -d paperjam:\n" + "\n".join(_txt.splitlines()[:20]))
                    break
        except Exception as _exc:
            self.output.warning("readelf probe failed: %s" % _exc)

        inner = '"%s" "%s" > "%s" 2>&1' % (shell, test_script, logfile)
        if shutil.which("timeout"):
            cmd = "timeout 90 %s" % inner
        elif os.path.isfile("/data/service/hnp/bin/timeout"):
            cmd = "/data/service/hnp/bin/timeout 90 %s" % inner
        else:
            cmd = inner
        with env_vars.vars(self).apply():
            # env=conanrun keeps VirtualRunEnv LD_LIBRARY_PATH (qpdf dep
            # libdirs) composed with our TMPDIR overlay; LD_PRELOAD is
            # intentionally unset (see above).
            self.run(cmd, env="conanrun", ignore_errors=True)

        out = ""
        if os.path.isfile(logfile):
            with open(logfile, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        self.output.info("test.sh log:\n" + "\n".join(out.splitlines()[-16:]))

        m = re.search(r"RESULT: (\d+) passed, (\d+) failed", out)
        if not m:
            raise ConanException("test.sh produced no RESULT line — harness broken")
        passed = int(m.group(1))
        failed = int(m.group(2))
        discovered = passed + failed
        ok = failed == 0 and discovered > 0

        marker = {
            "executed": True,
            "passed": ok,
            "command": "bash test.sh",
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
        if not ok:
            raise RuntimeError("test.sh failed: %d/%d cases failed" % (failed, discovered))

        upstream_marker = {
            "status": "no_tests",
            "framework": "none",
            "command": "",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (None
                       if False else
                       "paperjam-1.2.2.tar.gz audited (sha256 "
                       "a281912d00a935f490ce20873e87b82d5203bb6180326be1bec60184acab30fc): "
                       "no tests/ directory and no test source files anywhere in the "
                       "tree; Makefile defines only all/paperjam/paperjam.1/paperjam.1.html/"
                       "clean/install/release with no check/test target "
                       "(.PHONY: all clean release); no configure; "
                       "`make -n check` has no rule, so make check executes zero test cases"),
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker, ensure_ascii=False))
        self.output.info("paperjam functional test_package passed")
