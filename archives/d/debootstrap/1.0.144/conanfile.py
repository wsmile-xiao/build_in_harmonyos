#!/usr/bin/env python3
"""Conan recipe for debootstrap 1.0.144 — pure POSIX shell script tool.

debootstrap is a collection of POSIX shell scripts (main script + functions +
one script per Debian suite) that download and set up a base Debian system.
There is nothing to compile: the upstream Makefile only substitutes the
@VERSION@ placeholder via sed when installing, so we replicate that here.

Platform adaptations for OHOS:
  1. No compiler needed — pure shell code, no autotools/autoconf.
  2. @VERSION@ is replaced with the real version at packaging time, matching
     the upstream `sed 's/@VERSION@/$(VERSION)/g'`.
  3. The packaged layout follows the Debian install paths relativized under
     the Conan prefix: bin/debootstrap, share/debootstrap/functions,
     share/debootstrap/scripts/ and share/man/man8/debootstrap.8.
  4. DEBOOTSTRAP_DIR is exported via runenv so the script finds its
     functions/scripts without needing /usr/share/debootstrap.
  5. usage() prints its help text with printf instead of a here-document
     (patches/0001): the OHOS /bin/sh is mksh, and mksh writes here-doc
     bodies to a temp file under /tmp before feeding them to `cat`. OHOS
     /tmp is read-only, and debootstrap itself does `unset TMP TEMP
     TMPDIR` at startup, so the shell default applies and `--help` died
     with "can't create temporary file ...: Read-only file system"
     (silently, under set -e). printf is a builtin: no temp file, and the
     help output stays byte-identical to upstream.

R28: test_package/ exists.
R34: test_package runs `debootstrap --version` (real command invocation).
R38: commands.json declared at software level (tool-type package).

The upstream autopkgtest suite in debian/tests/ is executed for real from
build() via test_package/run_upstream_tests.sh. That runner parses
debian/tests/control to discover the cases and their Restrictions, probes each
case's preconditions on the actual build machine, and only reports a case as
blocked when a probe genuinely fails -- otherwise it runs the upstream script
and its real exit code is the verdict.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.layout import basic_layout


class DebootstrapConan(ConanFile):
    name = "debootstrap"
    version = "1.0.144"
    description = "Bootstrap a basic Debian system"
    license = "MIT"
    homepage = "https://salsa.debian.org/installer-team/debootstrap"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    # OHOS profile requires four settings (L0p gate)
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # The upstream autopkgtest runner lives next to the other test assets in
        # test_package/, but test_package/ is NOT part of the recipe export, so
        # build() would not find it in the cache. Ship it as an exported source.
        copy(self, "run_upstream_tests.sh",
             src=os.path.join(self.recipe_folder, "test_package"),
             dst=self.export_sources_folder)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # Pure shell tool: substitute @VERSION@ like the upstream Makefile.
        src = os.path.join(self.source_folder, "debootstrap")
        # Read/write binary. Text mode translates "\n" -> "\r\n" on a Windows
        # packager, which ships a shell script whose shebang becomes "/bin/sh\r".
        # Verified on Linux: running such a file fails with
        #   /bin/sh^M: bad interpreter: No such file or directory   (rc=126)
        with open(src, "rb") as handle:
            content = handle.read().decode("utf-8")
        content = content.replace("@VERSION@", self.version, 1)
        dst = os.path.join(self.build_folder, "debootstrap")
        with open(dst, "wb") as handle:
            handle.write(content.encode("utf-8"))
        # Keep upstream's mode and force the executable bits. Writing a fresh
        # file yields 0644, which would ship a CLI entry point that consumers
        # cannot run:
        #   /usr/bin/sh: 1: .../bin/debootstrap: Permission denied   (rc=126)
        src_mode = os.stat(src).st_mode
        os.chmod(dst, (src_mode & 0o7777) | 0o111)
        # Fail loudly rather than ship a script that cannot exec.
        with open(dst, "rb") as handle:
            if b"\r" in handle.read():
                raise ConanException(
                    "built debootstrap contains CR; a CRLF shell script cannot be "
                    "executed (bad interpreter /bin/sh^M). Refusing to package it."
                )
        # Smoke-run the freshly built script. It sources
        # "$DEBOOTSTRAP_DIR/functions" at line 21, before argument parsing, so a
        # valid data dir must be exported or even --version dies. The export is
        # done inside the shell (not via run(env=...)) so it is applied the same
        # way on a Linux worker and under git-bash on Windows.
        self.run('{} -c \'DEBOOTSTRAP_DIR="{}" "{}" --version\''.format(
            self._shell(), self._posix(self.source_folder), self._posix(dst)))
        self._run_upstream_tests(dst)

    def _posix(self, path):
        """Path in a form a POSIX shell can actually use.

        When a POSIX shell (git-bash/MSYS, as used for local verification) drives
        a Windows path, C:\\... is meaningless to `.`/`source`; convert it.
        No-op on the Linux CI worker.
        """
        if os.name != "nt" or not shutil.which("cygpath"):
            return path
        return subprocess.check_output(["cygpath", "-u", path]).decode().strip()

    def _shell(self):
        """A POSIX shell to drive the shell-based tests with.

        CONFIG_SHELL is what the CI worker provides (e.g.
        /data/service/hnp/bin/bash); fall back to whatever `sh` is on PATH.
        """
        cand = os.environ.get("CONFIG_SHELL") or shutil.which("sh") or shutil.which("bash")
        if not cand:
            raise ConanException(
                "no POSIX shell found (set CONFIG_SHELL); cannot run the shell tests")
        return '"{}"'.format(cand)

    def _run_upstream_tests(self, built_script):
        """Execute the genuine upstream autopkgtest suite against what we built.

        See test_package/run_upstream_tests.sh for the honesty contract. A
        runnable upstream test that fails fails the build on purpose; a test
        whose precondition probe fails on this machine is reported BLOCKED with
        the probe output, never silently passed.
        """
        runner = os.path.join(self.source_folder, "run_upstream_tests.sh")
        tests_dir = os.path.join(self.source_folder, "debian", "tests")
        if not os.path.isfile(runner) or not os.path.isdir(tests_dir):
            self.output.warning(
                "upstream test runner or debian/tests/ not available "
                "(runner={}, tests={}); skipping suite".format(
                    os.path.isfile(runner), os.path.isdir(tests_dir)))
            return
        report = os.path.join(self.build_folder, "upstream_test_report.md")
        # Never exec the runner through its own shebang; drive it with a shell.
        # Paths handed to the runner are POSIX-ised for the same reason as above.
        self.run('{} "{}" "{}" "{}" "{}"'.format(
            self._shell(), self._posix(runner), self._posix(self.source_folder),
            self._posix(built_script), self._posix(report)))

    def package(self):
        src = self.source_folder
        # Main script with version substituted (same relative path as upstream
        # /usr/sbin/debootstrap, but under our bin/).
        copy(self, "debootstrap", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        # functions + one script per suite -> share/debootstrap/*
        copy(self, "functions", src=src,
             dst=os.path.join(self.package_folder, "share", "debootstrap"),
             keep_path=False)
        copy(self, "*", src=os.path.join(src, "scripts"),
             dst=os.path.join(self.package_folder, "share", "debootstrap", "scripts"))
        # Man page
        copy(self, "debootstrap.8", src=src,
             dst=os.path.join(self.package_folder, "share", "man", "man8"),
             keep_path=False)
        # License (Expat / MIT)
        copy(self, "debian/copyright", src=src,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        bin_dir = os.path.join(self.package_folder, "bin")
        share_dir = os.path.join(self.package_folder, "share", "debootstrap")
        if os.path.isdir(bin_dir):
            self.runenv_info.append_path("PATH", bin_dir)
            self.buildenv_info.append_path("PATH", bin_dir)
        if os.path.isdir(share_dir):
            self.runenv_info.define("DEBOOTSTRAP_DIR", share_dir)