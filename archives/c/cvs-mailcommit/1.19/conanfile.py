#!/usr/bin/env python3
"""Conan recipe — cvs-mailcommit 1.19 (pure Perl commit-mail tool).

Debian cvs-mailcommit: Perl script that mails CVS commit notifications
(log message + diff) to a configured address. No C compilation, pure
script packaging for HarmonyOS PC (OHOS aarch64).
"""
import json
import os
import shutil

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CvsMailcommitConan(ConanFile):
    name = "cvs-mailcommit"
    version = "1.19"
    description = "Send CVS commit messages via email (Perl script)"
    license = "GPL-2.0-or-later"
    homepage = "https://tracker.debian.org/pkg/cvs-mailcommit"
    url = ""
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _find_perl(self):
        # Prefer toolchain perl / $PERL over PATH perl: preflight showed
        # PATH perl (.harmonybrew/bin/perl) forking as OOM, while the
        # toolchain perl is the supported interpreter.
        cand = os.environ.get("PERL")
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
        for p in ("/data/service/hnp/bin/perl",
                  "/usr/bin/perl", "/bin/perl", "/usr/local/bin/perl"):
            if os.path.isfile(p) and os.access(p, os.X_OK):
                return p
        for name in ("perl", "perl5"):
            p = shutil.which(name)
            if p:
                return p
        return "perl"

    def build(self):
        apply_conandata_patches(self)
        # Pure Perl script: no compilation. Upstream ships no test suite
        # (single script + Debian packaging); run perl -c syntax check as
        # a best-effort self-check and emit the HMBS evidence marker.
        # True-machine notes:
        #  - Do NOT use `self.run('cd ... && perl -c ...')`: /bin/sh on the
        #    rig needs writable /tmp for temp files (readonly_tmp) and the
        #    extra shell fork can surface as `[Errno 12] Out of memory`.
        #    Run perl directly via subprocess with cwd=source_folder.
        #  - Prefer the toolchain perl (/data/service/hnp/bin/perl, $PERL)
        #    over PATH perl (harmonybrew perl OOMed in preflight).
        #  - The check is advisory only: a missing/broken perl must not
        #    fail packaging of a pure script. Warn and continue.
        import subprocess
        perl = self._find_perl()
        script = self._find_script()
        if script is not None:
            try:
                proc = subprocess.run(
                    [perl, "-c", script],
                    cwd=self.source_folder,
                    capture_output=True, text=True, timeout=120)
                combined = (proc.stdout or "") + (proc.stderr or "")
                if proc.returncode == 0 and "syntax OK" in combined:
                    self.output.info("perl -c OK: %s" % combined.strip().splitlines()[-1] if combined.strip() else "syntax OK")
                else:
                    self.output.warning("perl -c advisory check failed (%s, rc=%s), continuing packaging: %s"
                                        % (perl, proc.returncode, combined.strip()[-2000:]))
            except OSError as exc:
                self.output.warning("perl -c advisory check could not run (%s: %s), continuing packaging" % (perl, exc))
            except subprocess.SubprocessError as exc:
                self.output.warning("perl -c advisory check error (%s), continuing packaging" % exc)
        result = {
            "status": "no_tests",
            "framework": "none",
            "command": "",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "cvs-mailcommit 1.19 upstream ships no test suite: orig.tar.gz is a single Perl script with no tests/ dir, no Makefile/ctest/pytest entry (audit in test_package/MANIFEST.yml); perl -c above is a recipe self-check, not an upstream suite",
        }
        self.output.info('HMBS_UPSTREAM_TEST_RESULT=%s' % json.dumps(result))

    def _find_script(self):
        for cand in ("cvs-mailcommit", "cvs-mailcommit.pl", "mailcommit", "mailcommit.pl"):
            p = os.path.join(self.source_folder, cand)
            if os.path.isfile(p):
                return p
        # Fallback: first executable-looking Perl file at top level.
        for name in sorted(os.listdir(self.source_folder)):
            if name.endswith(".pl") or name.startswith("cvs-"):
                p = os.path.join(self.source_folder, name)
                if os.path.isfile(p):
                    return p
        return None

    def package(self):
        src = self.source_folder
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        script = self._find_script()
        if script is not None:
            copy(self, os.path.basename(script), src=src, dst=bin_dir)
            installed = os.path.join(bin_dir, os.path.basename(script))
            # Normalize installed name to cvs-mailcommit.
            target = os.path.join(bin_dir, "cvs-mailcommit")
            if installed != target:
                if os.path.exists(target):
                    os.remove(target)
                os.rename(installed, target)
            try:
                os.chmod(target, 0o755)
            except OSError:
                pass
        # Man page / docs when present (Debian tarball may carry them).
        for pattern in ("*.1", "*.8"):
            copy(self, pattern, src=src, dst=os.path.join(self.package_folder, "share", "man", "man1"))
        for doc in ("README", "README.md", "ChangeLog", "CHANGELOG", "COPYING", "LICENSE"):
            dst = os.path.join(self.package_folder, "licenses" if doc in ("COPYING", "LICENSE") else "share", "doc", "cvs-mailcommit")
            if os.path.isfile(os.path.join(src, doc)):
                copy(self, doc, src=src, dst=dst, keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
