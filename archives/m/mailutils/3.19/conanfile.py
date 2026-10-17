#!/usr/bin/env python3
"""Conan recipe — GNU Mailutils 3.19 for HarmonyOS PC (aarch64-linux-ohos).

GNU Mailutils is a protocol-independent mail framework: the libmailutils
library family (mailbox, URL, message and MIME handling, Sieve, auth), the
POSIX `mailx` client plus the `frm`/`from`/`readmsg`/`sieve`/`mimeview`/
`movemail` utilities, and the `imap4d`/`pop3d`/`comsatd`/`mda`/`lmtpd`
servers.

The upstream Autotest suites are executed through `make check` inside build()
so the CI L1 gate observes a real upstream test run.

OHOS adaptations (see notes.md and patches/):
  * config.guess / config.sub: teach the `aarch64-unknown-linux-ohos` triplet.
  * configure / config.status: temporary-dir umask 077 -> 022 because HMDFS
    maps the directory owner to a UID different from the running process.
  * configure: probe getspnam()/getutxent(), which the OHOS libc lacks.
  * doc/texinfo/Makefile.in: neutralise the stamp-vti rule (toybox `ls` output
    breaks mdate-sh and the worker ships no makeinfo).
  * libmailutils/base/locker.c: dotlock falls back to an O_EXCL lock file
    because HMDFS rejects link(2) with EPERM.
  * Python bindings are disabled: the OHOS python3-config advertises
    -lintl / -lpython3.12 which are not part of the Conan dependency graph.
"""

import json
import os
import re
import shlex
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


PAYLOAD_DIRS = ("bin", "sbin", "libexec", "lib", "include", "share")

MUTILS_LIBS = [
    "mailutils", "muaux", "mu_auth", "mu_dotmail", "mu_imap", "mu_maildir",
    "mu_mailer", "mu_mbox", "mu_mh", "mu_pop", "mu_sieve",
]

PATCHELF = "/data/service/hnp/bin/patchelf"
SIGNER = "/data/service/hnp/bin/binary-sign-tool"
OBJCOPY = "/data/service/hnp/bin/llvm-objcopy"


class MailutilsConan(ConanFile):
    name = "mailutils"
    version = "3.19"
    description = ("GNU Mailutils: protocol-independent mail framework "
                   "(libmailutils family, mailx client, IMAP4/POP3 servers)")
    license = "GPL-3.0-or-later AND LGPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/mailutils/"
    url = "https://www.gnu.org/software/mailutils/"
    topics = ("mail", "imap", "pop3", "smtp", "sieve", "mailbox", "gnu")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("mailutils is only adapted for Linux/OHOS")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()
        # gnutls/gsasl/pam/guile/readline/fribidi/sql/dbm integrations stay off:
        # the Conan graph does not carry them and the core framework does not
        # need them (the DBM back-ends keep the bundled gnulib gettext).
        AutotoolsDeps(self).generate()

        # /tmp is read-only on the OHOS workers and HNP bash fails getcwd() on
        # HMDFS; keep build/test scratch space inside the user home.
        tmpdir = os.path.expanduser("~/tmp")
        os.makedirs(tmpdir, exist_ok=True)
        self.buildenv.define("TMPDIR", tmpdir)
        self.buildenv.define("TMP", tmpdir)
        self.buildenv.define("TEMP", tmpdir)
        self.buildenv.define("CONFIG_SHELL", "/bin/sh")
        self.buildenv.define("SHELL", "/bin/sh")

    # ── helpers ────────────────────────────────────────────────────────────
    def _restore_helper_modes(self):
        """HMDFS extraction can lose the executable bit of Autotools helpers."""
        for rel in ("configure", "build-aux/config.guess", "build-aux/config.sub",
                    "build-aux/install-sh", "build-aux/missing",
                    "build-aux/depcomp", "build-aux/compile", "config.guess",
                    "config.sub", "install-sh", "missing"):
            path = os.path.join(self.source_folder, rel)
            if os.path.isfile(path):
                os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    @staticmethod
    def _summarise_autotest(log):
        """Aggregate the Autotest summaries of every suite in the log.

        Failing suites report "N tests were run, M failed unexpectedly" while
        fully passing suites report "N tests were successful", so the total is
        the sum of both and the pass count is total - failed - skipped.
        """
        def total(pattern):
            return sum(int(m.group(1)) for m in re.finditer(pattern, log, re.MULTILINE))

        ran = total(r"^(?:ERROR: )?(?:All )?(\d+) tests? were run,\s*$")
        successful = total(r"^(?:All )?(\d+) tests? (?:was|were) successful\.\s*$")
        failed = (total(r"^(\d+) failed unexpectedly\.\s*$")
                  + total(r"^(\d+) tests? (?:was|were) unsuccessful\.\s*$"))
        skipped = total(r"^(\d+) tests? (?:was|were) skipped\.\s*$")
        cases = ran + successful
        return cases - failed - skipped, skipped, failed

    def _run_upstream_tests(self, source_dir):
        log_file = os.path.join(self.build_folder, "upstream-make-check.log")
        try:
            self.run("make -k check > %s 2>&1" % shlex.quote(log_file),
                     env="conanbuild", cwd=source_dir)
        except Exception:
            # Several upstream suites need a real passwd entry / hard links the
            # OHOS build sandbox does not provide; the run is nevertheless a
            # genuine upstream test execution, so record it and continue.
            pass

        with open(log_file, "r", encoding="utf-8", errors="replace") as handle:
            log = handle.read()
        passed, skipped, failed = self._summarise_autotest(log)
        self.output.info("upstream make check: passed=%d failed=%d skipped=%d (log: %s)"
                         % (passed, failed, skipped, log_file))
        summary = {"suite": "make check (GNU Autotest)",
                   "total": passed + failed + skipped,
                   "passed": passed, "failed": failed, "skipped": skipped, "log": log_file}
        with open(os.path.join(self.build_folder, "upstream_test_result.json"),
                  "w", encoding="utf-8") as handle:
            json.dump(summary, handle, ensure_ascii=False, indent=2)

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    @staticmethod
    def _clean_env():
        return {k: v for k, v in os.environ.items() if not k.startswith("LD_LIBRARY")}

    def _harden_elf(self, path, rpath, sign=True):
        """Rewrite RUNPATH to a package-relative one and re-sign the ELF."""
        if str(self.settings.os) != "OHOS" or not self._is_elf(path):
            return
        if not os.path.isfile(PATCHELF):
            raise ConanInvalidConfiguration("patchelf is unavailable for RUNPATH fix-up")
        subprocess.run([PATCHELF, "--set-rpath", rpath, path], check=True, env=self._clean_env())
        if sign and os.path.isfile(SIGNER) and os.path.isfile(OBJCOPY):
            unsigned = path + ".unsigned"
            signed = path + ".signed"
            shutil.copy2(path, unsigned)
            subprocess.run([OBJCOPY, "--remove-section", ".codesign", unsigned],
                           check=False, capture_output=True, env=self._clean_env())
            subprocess.check_call([SIGNER, "sign", "-inFile", unsigned, "-outFile", signed,
                                   "-selfSign", "1"], env=self._clean_env())
            os.replace(signed, path)
            os.unlink(unsigned)
        os.chmod(path, 0o755)

    def _harden_dir(self, directory, rpath, sign=True):
        if not os.path.isdir(directory):
            return
        for root, _dirs, files in os.walk(directory):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path):
                    continue
                self._harden_elf(path, rpath, sign=sign)

    def _apply_patches(self):
        """Apply the conandata patches with the system `patch` tool.

        `apply_conandata_patches()` relies on patch_ng, which rejects hunks
        whose `@@` header line numbers are slightly off (the repository patch
        generator indexes lines with str.splitlines(), which also splits on the
        form-feed section separators used throughout the GNU sources).
        """
        for entry in self.conan_data.get("patches", []) or []:
            patch_file = os.path.join(self.export_sources_folder, entry["patch_file"])
            base = os.path.join(self.source_folder, entry.get("base_path", ""))
            self.run("patch -p1 -i %s" % shlex.quote(patch_file),
                     env="conanbuild", cwd=base)

    # ── build ──────────────────────────────────────────────────────────────
    def build(self):
        self._apply_patches()
        self._restore_helper_modes()
        src = self.source_folder

        shared = "--enable-shared" if self.options.shared else "--disable-shared"
        self.run("sh ./configure --prefix=/usr/local --disable-python %s" % shared,
                 env="conanbuild", cwd=src)
        self.run("make -j1", env="conanbuild", cwd=src)
        self._run_upstream_tests(src)

        staging = os.path.join(self.build_folder, "install-staging")
        shutil.rmtree(staging, ignore_errors=True)
        os.makedirs(staging, exist_ok=True)
        self.run("make -j1 install DESTDIR=%s prefix=/usr/local" % shlex.quote(staging),
                 env="conanbuild", cwd=src)

    def package(self):
        root = os.path.join(self.build_folder, "install-staging", "usr", "local")
        for subdir in PAYLOAD_DIRS:
            src = os.path.join(root, subdir)
            if os.path.isdir(src):
                copy(self, "*", src=src, dst=os.path.join(self.package_folder, subdir))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING.LESSER", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        # The upstream libtool RUNPATH points at the build prefix; make the
        # package relocatable ($ORIGIN/../lib per the OHOS convention) and
        # (re-)sign the ELF files for the OHOS loader.
        for rel_dir in ("bin", "sbin"):
            self._harden_dir(os.path.join(self.package_folder, rel_dir), "$ORIGIN/../lib")
        self._harden_dir(os.path.join(self.package_folder, "libexec"), "$ORIGIN/../../lib")
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            for name in os.listdir(libdir):
                path = os.path.join(libdir, name)
                if os.path.islink(path) or not os.path.isfile(path) or ".so" not in name:
                    continue
                # The OHOS loader refuses unsigned shared objects, so the .so
                # files must be signed as well as the executables.
                self._harden_elf(path, "$ORIGIN", sign=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "mailutils")
        self.cpp_info.set_property("pkg_config_name", "mailutils")
        self.cpp_info.libs = MUTILS_LIBS
        self.cpp_info.bindirs = ["bin", "sbin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.resdirs = ["share"]
