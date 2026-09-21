#!/usr/bin/env python3
"""Conan recipe for xelb 0.20 (Emacs Lisp X protocol binding)."""

import glob
import json
import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class XelbConan(ConanFile):
    name = "xelb"
    version = "0.20"
    description = "X protocol Emacs Lisp Binding (pure Elisp X11 implementation)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/emacs-exwm/xelb"
    url = "https://github.com/emacs-exwm/xelb"
    package_type = "unknown"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"xelb supports Linux and OHOS, got {self.settings.os}"
            )

    def package_id(self):
        self.info.clear()

    def requirements(self):
        # xelb.el 0.20 declares Package-Requires: emacs 27.1 + compat 29.1
        # (bumped to compat 30 at release time). Emacs 29.1 and compat
        # 31.0.0.2 are backwards compatible supersets.
        self.requires("emacs/29.1")
        self.requires("compat/31.0.0.2")
        # CCI-competition guard (preflight 2026-09-20: the create graph pulls
        # CCI ninja/1.13.2 from source and its CMakeToolchain configure fails
        # with "System is unknown to cmake" plus a broken CMAKE_CXX_COMPILER
        # sanity check). Parent chain: emacs requires bare ncurses/6.5, which
        # exists on BOTH remotes (CCI ncurses config.yml carries 6.5/6.4/6.3),
        # and the CCI ncurses recipe declares
        # build_requirements->tool_requires("pkgconf/2.0.3"), whose CCI recipe
        # builds via meson, which in turn requires ninja/[>=1.10.2 <2]
        # (resolves to ninja/1.13.2). Preflight checks conancenter first (CI
        # disables it), so the CCI recipe wins and drags the ninja-from-source
        # cmake failure into this pure-Elisp closure, which itself declares
        # zero cmake/ninja/tool_requires edges (same fingerprint as the
        # ayatana-ido/0.10.4-v2 and naga/1.0 preflight notes in this repo).
        # Pin the ohpcd-published recipe revision with override=True so the
        # whole closure uses the hardened in-repo ncurses (zero
        # tool_requires). RREV evidence: archives/e/emacs/29.1/notes.md
        # records the 2026-08-09 isolated run downloading
        # ncurses/6.5#69914b9d115a9d31e4b32372c44e49bf from ohpcd, after the
        # current ncurses/6.5 recipe commit, so it matches the in-repo recipe.
        # Version-preserving: emacs publish identity is untouched, so the
        # published emacs OHOS binary stays a valid hit instead of forcing a
        # source rebuild.
        self.requires(
            "ncurses/6.5#69914b9d115a9d31e4b32372c44e49bf",
            override=True,
        )

    def source(self):
        sources = (self.conan_data or {}).get("sources")
        if not sources:
            raise ConanException(
                "conandata.yml 'sources' is missing; "
                "ensure conandata.yml is exported with the recipe"
            )
        get(self, **sources, strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def _emacs(self):
        dependency = self.dependencies["emacs"]
        emacs = os.path.join(dependency.package_folder, "bin", "emacs")
        if not os.path.isfile(emacs):
            raise ConanInvalidConfiguration(f"Emacs executable is missing: {emacs}")
        return shlex.quote(emacs)

    def _compat_lispdir(self):
        dependency = self.dependencies["compat"]
        lispdir = os.path.join(
            dependency.package_folder,
            "share",
            "emacs",
            "site-lisp",
            "compat-31.0.0.2",
        )
        if not os.path.isdir(lispdir):
            raise ConanInvalidConfiguration(
                f"compat lisp directory is missing: {lispdir}"
            )
        return lispdir

    def _library_sources(self):
        # All shipped .el files except the upstream ERT test module.
        # The Makefile regeneration target (xelb-gen + xcb-proto XML) is
        # deliberately not used: it would delete the shipped pre-generated
        # bindings and need xcb-proto sources. ELPA installs byte-compile
        # the shipped files directly, and so do we.
        candidates = sorted(
            glob.glob(os.path.join(self.source_folder, "*.el"))
        )
        sources = [
            path
            for path in candidates
            if os.path.basename(path) != "xelb-test.el"
        ]
        if len(sources) != 46:
            raise ConanException(
                f"expected 46 xelb library sources, found {len(sources)}"
            )
        return sources

    def _emit_upstream_marker(self, log_path, command):
        discovered = executed = passed = failed = skipped = 0
        status = "failed"
        reason = ""
        try:
            with open(log_path, encoding="utf-8", errors="replace") as handle:
                log_text = handle.read()
        except OSError as exc:
            reason = f"cannot read ERT log {log_path}: {exc}"
            log_text = ""
        match = None
        if log_text:
            match = re.search(
                r"Ran (\d+) tests?, (\d+) results? as expected"
                r"(?:, (\d+) unexpected)?",
                log_text,
            )
        if match:
            discovered = executed = int(match.group(1))
            passed = int(match.group(2))
            unexpected = match.group(3)
            failed = int(unexpected) if unexpected is not None else discovered - passed
            skipped = 0
            if passed + failed == executed and executed <= discovered:
                status = "passed" if failed == 0 else "failed"
            else:
                status = "failed"
                reason = "ERT summary counts violate passed+failed==executed"
        elif not reason:
            reason = "no 'Ran N tests' ERT summary found in log"
        marker = {
            "status": status,
            "framework": "ert",
            "command": command,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        if reason:
            marker["reason"] = reason
        self.output.info(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(marker)}")
        return status

    def build(self):
        emacs = self._emacs()
        compat_dir = self._compat_lispdir()
        load_path = (
            f"-L {shlex.quote(compat_dir)} "
            f"-L {shlex.quote(self.source_folder)}"
        )
        sources = self._library_sources()
        quoted = " ".join(shlex.quote(path) for path in sources)
        self.run(
            f"{emacs} -Q --batch {load_path} -f batch-byte-compile {quoted}",
            cwd=self.source_folder,
            env="conanbuild",
        )
        for source in sources:
            compiled = os.path.splitext(source)[0] + ".elc"
            if not os.path.isfile(compiled) or os.path.getsize(compiled) == 0:
                raise ConanException(
                    f"byte-compilation did not produce {compiled}"
                )
        # Upstream test suite: xelb-test.el holds 2 ERT tests
        # (xelb-test-binary32, xelb-test-binary64) exercising the
        # binary32/binary64 conversion primitives of xcb-types.el.
        # Loading xcb and xelb here also proves the entry points resolve.
        ert_log = os.path.join(self.build_folder, "xelb-ert.log")
        ert_command = (
            f"{emacs} -Q --batch {load_path} "
            f"-l {shlex.quote(os.path.join(self.source_folder, 'xcb.el'))} "
            f"-l {shlex.quote(os.path.join(self.source_folder, 'xelb.el'))} "
            f"-l {shlex.quote(os.path.join(self.source_folder, 'xelb-test.el'))} "
            "-f ert-run-tests-batch-and-exit"
        )
        try:
            self.run(
                f"{ert_command} > {shlex.quote(ert_log)} 2>&1",
                cwd=self.source_folder,
                env="conanbuild",
            )
        except Exception:
            self._emit_upstream_marker(ert_log, ert_command)
            raise
        if self._emit_upstream_marker(ert_log, ert_command) != "passed":
            raise ConanException("upstream xelb ERT suite reported failures")

    def _lisp_dir(self):
        return os.path.join(
            self.package_folder,
            "share",
            "emacs",
            "site-lisp",
            f"xelb-{self.version}",
        )

    def package(self):
        lisp_dir = self._lisp_dir()
        for pattern in ("xcb*.el", "xcb*.elc", "xelb.el", "xelb.elc"):
            copy(self, pattern, self.source_folder, lisp_dir, keep_path=False)
        copy(
            self,
            "README.md",
            self.source_folder,
            os.path.join(self.package_folder, "share", "xelb"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        lisp_dir = self._lisp_dir()
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = []
        self.buildenv_info.define_path("XELB_LISPDIR", lisp_dir)
        self.runenv_info.define_path("XELB_LISPDIR", lisp_dir)
        self.buildenv_info.prepend_path("EMACSLOADPATH", lisp_dir)
        self.runenv_info.prepend_path("EMACSLOADPATH", lisp_dir)
