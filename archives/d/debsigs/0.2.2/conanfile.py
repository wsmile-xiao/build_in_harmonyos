#!/usr/bin/env python3
"""Conan recipe — debsigs 0.2.2 (Perl .deb signature tool)."""

import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import download
from conan.tools.layout import basic_layout


class DebsigsConan(ConanFile):
    name = "debsigs"
    version = "0.2.2"
    package_type = "application"
    description = "debsigs — Debian .deb package signature manager (pure Perl scripts)"
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.com/debsigs/debsigs"
    topics = ("debian", "deb", "signing", "gpg", "perl")
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "debsigs is prepared for Linux/OHOS targets only"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        download(self, self.conan_data["sources"]["url"],
                 "debsigs_0.2.2.orig.tar.xz",
                 sha256=self.conan_data["sources"]["sha256"])
        self.run("tar -xJf debsigs_0.2.2.orig.tar.xz --no-same-owner || true")
        self.run("cp -a debsigs-0.2.2/. . && rm -rf debsigs-0.2.2")

    def _perl(self):
        for cand in ("/data/service/hnp/bin/perl", "/usr/bin/perl"):
            if os.path.isfile(cand):
                return cand
        found = shutil.which("perl")
        return found or "perl"

    def _run_upstream_tests(self):
        """Run upstream perl/test.pl (Test::More, 4 tests) and emit HMBS marker."""
        perl = self._perl()
        test_pl = os.path.join(self.source_folder, "perl", "test.pl")
        perldir = os.path.join(self.source_folder, "perl")
        # Upstream perl/*.pm are stored flat (arf.pm, ...) but loaded as
        # Debian::debsigs::<mod>, so stage them under Debian/debsigs/ and
        # expose via PERL5LIB; otherwise @INC lookup fails (4/4 not ok).
        lib_stage = os.path.join(self.build_folder, "perl-lib")
        staged = os.path.join(lib_stage, "Debian", "debsigs")
        os.makedirs(staged, exist_ok=True)
        for mod in ("arf.pm", "debsigsmain.pm", "forktools.pm", "gpg.pm"):
            src = os.path.join(perldir, mod)
            dst = os.path.join(staged, mod)
            try:
                if os.path.isfile(src):
                    shutil.copy2(src, dst)
            except Exception:
                pass
        run_env = dict(os.environ)
        perl5lib = [lib_stage, perldir]
        if run_env.get("PERL5LIB"):
            perl5lib.append(run_env["PERL5LIB"])
        run_env["PERL5LIB"] = os.pathsep.join(perl5lib)
        discovered = 4
        executed = 0
        passed = 0
        failed = 0
        skipped = 0
        status = "failed"
        output = ""
        try:
            proc = subprocess.run(
                [perl, "test.pl"],
                cwd=perldir,
                env=run_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=120,
            )
            output = proc.stdout.decode(errors="replace")
        except Exception as exc:  # noqa: BLE001 — report as failed marker
            output = "failed to run perl test.pl: %s" % exc
        self.output.info("debsigs upstream perl/test.pl output:\n" + output)
        m = re.search(r"#\s*Failed\s+(\d+)\s*/\s*(\d+)", output)
        if m:
            failed = int(m.group(1))
            total = int(m.group(2))
            discovered = total
            executed = total
            passed = total - failed
        else:
            m2 = re.search(r"Result:\s*(\w+)", output)
            ok_lines = re.findall(r"^ok\s+\d+", output, re.M)
            not_ok = re.findall(r"^not ok\s+\d+", output, re.M)
            if ok_lines or not_ok:
                passed = len(ok_lines)
                failed = len(not_ok)
                discovered = passed + failed
                executed = discovered
            elif m2 and m2.group(1).upper() == "PASS":
                executed = discovered
                passed = discovered
        if failed == 0 and passed == discovered and discovered > 0:
            status = "passed"
        elif failed > 0:
            status = "failed"
        marker = {
            "status": status,
            "framework": "perl-Test-More",
            "command": "perl test.pl",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False)
        print(msg, flush=True)
        self.output.info(msg)
        try:
            with open(os.path.join(self.build_folder, "hmbs_upstream.json"),
                      "w", encoding="utf-8") as f:
                json.dump(marker, f)
        except Exception:
            pass
        if status != "passed":
            raise RuntimeError("upstream perl/test.pl failed: %s" % marker)

    def build(self):
        self._run_upstream_tests()

    def package(self):
        perldir = os.path.join(self.source_folder, "perl")
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        for script in ("debsigs", "debsigs-autosign",
                       "debsigs-installer", "debsigs-signchanges"):
            src = os.path.join(perldir, script)
            if os.path.isfile(src):
                dst = os.path.join(bindir, script)
                shutil.copy2(src, dst)
                os.chmod(dst, 0o755)
        moddir = os.path.join(self.package_folder, "lib", "perl5",
                              "Debian", "debsigs")
        os.makedirs(moddir, exist_ok=True)
        for mod in ("arf.pm", "debsigsmain.pm", "forktools.pm", "gpg.pm"):
            src = os.path.join(perldir, mod)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(moddir, mod))
        for doc in ("COPYING",):
            src = os.path.join(perldir, doc)
            if os.path.isfile(src):
                dst_dir = os.path.join(self.package_folder, "licenses")
                os.makedirs(dst_dir, exist_ok=True)
                shutil.copy2(src, os.path.join(dst_dir, doc))
        try:
            src = os.path.join(self.build_folder, "hmbs_upstream.json")
            if os.path.isfile(src):
                dst_dir = os.path.join(self.package_folder, "res")
                os.makedirs(dst_dir, exist_ok=True)
                shutil.copy2(src, os.path.join(dst_dir, "hmbs_upstream.json"))
        except Exception:
            pass

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
