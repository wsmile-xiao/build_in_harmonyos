#!/usr/bin/env python3
"""Conan recipe — enigma 1.3 (pure Perl Enigma machine module).

Upstream distribution is Crypt-Enigma 1.3 (module Crypt::Enigma) by Alistair
Francis: a pure-Perl implementation of the WWII Enigma machine with zero
dependencies. This recipe follows the task slug "enigma" for the package
name; the upstream identity mapping is documented in notes.md.

Build system is ExtUtils::MakeMaker (perl Makefile.PL + make). The module
contains no C/XS code, so no compiler flags, no static/shared choice and no
platform patches are needed. `make test` runs the upstream suite (t/01.t)
inside build(); test_package/ exercises the real Crypt::Enigma API.
"""
import glob
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class EnigmaConan(ConanFile):
    name = "enigma"
    version = "1.3"
    description = "Pure-Perl implementation of the WWII Enigma machine (Crypt::Enigma)"
    license = "Artistic-1.0"
    homepage = "https://metacpan.org/dist/Crypt-Enigma"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: OHOS platform compatibility
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # E002 + HMBS readonly_tmp: /tmp is erofs read-only on HarmonyOS
        # workers. Prefer the task-independent TMPDIR/TMP/TEMP injected by
        # hmbs (known writable); fall back to build_folder. Define all three
        # together so ExtUtils::MakeMaker / File::Temp / sh pick the writable
        # path regardless of which variable they honour.
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or self.build_folder
        )
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except Exception:
            tmpdir = self.build_folder
        env = Environment()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        env.vars(self).save_script("enigma_build_env")

    def _save_upstream_result(self, log):
        """Parse `make test` output into res/upstream_test_result.json.

        Raises when the harness did not report success, so a silent or
        skipped upstream suite can never be mistaken for a pass.
        """
        log = log or ""
        match = re.search(r"Tests=(\d+)", log)
        if match:
            discovered = int(match.group(1))
        else:
            # Fallback count sources: verbose TAP plan or harness Files=N.
            # Only used for counting; success still requires an explicit
            # PASS marker (or a full ok-line set, see below).
            plan = re.search(r"^1\.\.(\d+)\s*$", log, re.MULTILINE)
            if plan:
                discovered = int(plan.group(1))
            else:
                files = re.search(r"Files=(\d+)", log)
                discovered = int(files.group(1)) if files else 0
        ok = ("Result: PASS" in log) or ("All tests successful" in log)
        if not ok and discovered > 0:
            # Verbose TAP fallback: every planned test has an ok line and
            # no failure marker. Still strict: any "not ok"/FAIL keeps ok=False.
            oks = len(re.findall(r"^ok\b", log, re.MULTILINE))
            if oks >= discovered and "not ok" not in log and "FAIL" not in log:
                ok = True
        if not ok or discovered <= 0:
            excerpt = log[-2000:] if len(log) > 2000 else log
            raise ConanException(
                "upstream `make test` evidence missing "
                f"(success={ok}, discovered={discovered}); refusing to continue. "
                f"captured tail:\n{excerpt}"
            )
        result = {
            "status": "passed",
            "framework": "perl-Test-Harness",
            "command": "make test TEST_VERBOSE=1",
            "discovered": discovered,
            "executed": discovered,
            "passed": discovered,
            "failed": 0,
            "skipped": 0,
        }
        path = os.path.join(self.build_folder, "upstream_test_result.json")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

    def build(self):
        apply_conandata_patches(self)
        # E002/readonly_tmp: make sure every child process (perl/make/sh/
        # File::Temp) inherits a writable temp dir even if the buildenv
        # script sourcing misses it; prefer the hmbs-injected value.
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or self.build_folder
        )
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except Exception:
            tmpdir = self.build_folder
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        # Pure Perl module: ExtUtils::MakeMaker, no compiler interaction.
        self.run("perl Makefile.PL", cwd=self.source_folder)
        self.run("make -j1", cwd=self.source_folder)
        # Upstream official test suite (t/01.t via Test::Harness). Capture
        # combined stdout+stderr to a writable file inside build_folder
        # (never /tmp) so evidence parsing does not depend on Conan's stdout
        # return value, which came back empty on the read-only-/tmp worker
        # even though the harness itself reported PASS.
        log_path = os.path.join(self.build_folder, "make_test.log")
        rc_out = None
        try:
            rc_out = self.run(
                'make test TEST_VERBOSE=1 > "{0}" 2>&1'.format(log_path),
                cwd=self.source_folder,
                stdout=True,
            )
        except ConanException:
            # make test exited non-zero; the captured log below still holds
            # the evidence _save_upstream_result needs. Fall through to parse.
            pass
        out = ""
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        except OSError:
            out = ""
        out = out or (rc_out or "")
        self.output.info("upstream `make test` output:\n" + out)
        self._save_upstream_result(out)

    def package(self):
        # Install to a temporary DESTDIR, then pick up the module file.
        # Quote DESTDIR (paths may contain spaces) and keep it inside
        # build_folder (writable; never /tmp per E002/readonly_tmp).
        dest_dir = os.path.join(self.build_folder, "destdir")
        self.run('make install "DESTDIR={}"'.format(dest_dir), cwd=self.source_folder)

        # Locate Crypt/Enigma.pm robustly: the MakeMaker PREFIX on the
        # worker is a deep harmonybrew path
        # (destdir/storage/.../Cellar/perl/5.44.0_1/.../Crypt/Enigma.pm),
        # so walk the tree instead of relying on a single glob pattern.
        pm_files = []
        if os.path.isdir(dest_dir):
            for root, _dirs, files in os.walk(dest_dir):
                if "Enigma.pm" in files:
                    full = os.path.join(root, "Enigma.pm")
                    if full.replace(os.sep, "/").endswith("Crypt/Enigma.pm"):
                        pm_files.append(full)
                        break
        if not pm_files and os.path.isdir(dest_dir):
            # Fallback: any Enigma.pm (diagnosed via tree excerpt on failure).
            for root, _dirs, files in os.walk(dest_dir):
                if "Enigma.pm" in files:
                    pm_files.append(os.path.join(root, "Enigma.pm"))
                    break
        if not pm_files:
            tree = []
            if os.path.isdir(dest_dir):
                for root, dirs, files in os.walk(dest_dir):
                    level = root.replace(dest_dir, "").count(os.sep)
                    if level > 4:
                        dirs[:] = []
                        continue
                    tree.append(root.replace(dest_dir, "") or "/")
                    for name in (dirs + files)[:20]:
                        tree.append("  " + name)
                    if len(tree) > 60:
                        break
            raise ConanException(
                "Crypt/Enigma.pm not found under DESTDIR after make install. "
                "DESTDIR tree excerpt:\n" + "\n".join(tree[:60])
            )
        target_dir = os.path.join(self.package_folder, "lib", "perl5", "Crypt")
        os.makedirs(target_dir, exist_ok=True)
        # copyfile (not copy2): worker FS reports chmod/hardlink unsupported
        # (HMBS hardlink=0 chmod=0), so avoid metadata-preserving copies.
        shutil.copyfile(pm_files[0], os.path.join(target_dir, "Enigma.pm"))

        # Persist the parsed upstream evidence for test_package to re-emit.
        evidence = os.path.join(self.build_folder, "upstream_test_result.json")
        if not os.path.isfile(evidence):
            raise ConanException(
                "upstream_test_result.json missing; build() must run make test first"
            )
        res_dir = os.path.join(self.package_folder, "res")
        os.makedirs(res_dir, exist_ok=True)
        shutil.copyfile(evidence, os.path.join(res_dir, "upstream_test_result.json"))

    def package_info(self):
        # Pure Perl module — no compiled libraries.
        self.cpp_info.libs = []
        # Consumers find Crypt/Enigma.pm through PERL5LIB.
        perl_lib = os.path.join(self.package_folder, "lib", "perl5")
        self.runenv_info.append_path("PERL5LIB", perl_lib)
        self.buildenv_info.append_path("PERL5LIB", perl_lib)
