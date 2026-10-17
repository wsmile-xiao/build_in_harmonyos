#!/usr/bin/env python3
"""Conan recipe for GNU Anubis 4.3 on HarmonyOS PC.

GNU Anubis is an SMTP daemon/CLI application.  The first adaptation keeps
optional integrations disabled because the OHOS Conan graph does not provide
the corresponding host-side services; the core daemon and anubisadm are
still built and exercised by the upstream Autotest suite.
"""

import json
import os
import re
import shlex
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


UPSTREAM_STATIC_TESTS = 27


class AnubisConan(ConanFile):
    name = "anubis"
    version = "4.3"
    description = "GNU SMTP message submission daemon"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/anubis/"
    url = "https://www.gnu.org/software/anubis/"
    topics = ("smtp", "mail", "daemon", "gnu")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("anubis supports Linux/OHOS only")

    def requirements(self):
        # The core build is intentionally independent of optional GnuTLS,
        # GPGME, Guile, GSASL, SQL, PCRE, PAM, and TCP-wrapper libraries.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @staticmethod
    def _configure_args():
        # The release tarball's config.sub does not recognize linux-ohos.
        # Keep the build/host tuple in the accepted GNU family while the
        # Conan OHOS compiler/profile supplies the actual target ABI.
        return [
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
            "--prefix=/usr/local",
            "--disable-nls",
            "--without-gsasl",
            "--without-gnutls",
            "--without-gpgme",
            "--without-guile",
            "--without-mysql",
            "--without-postgres",
            "--without-pcre",
            "--without-pam",
            "--without-socks-proxy",
            "--without-tcp-wrappers",
            "--with-unprivileged-user=nobody",
        ]

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()
        AutotoolsDeps(self).generate()

        # HNP bash can fail getcwd() on HMDFS and /tmp is not a reliable
        # writable location.  Keep these overrides local to the Conan build.
        tmpdir = os.path.expanduser("~/tmp")
        os.makedirs(tmpdir, exist_ok=True)
        self.buildenv.define("TMPDIR", tmpdir)
        self.buildenv.define("TMP", tmpdir)
        self.buildenv.define("TEMP", tmpdir)
        self.buildenv.define("CONFIG_SHELL", "/bin/sh")
        self.buildenv.define("SHELL", "/bin/sh")

    def _run_make_check(self, source_dir):
        log_file = os.path.join(self.build_folder, "upstream-check.log")
        # The release ships the generated anubis.info file, but Automake
        # still attempts to refresh it because version.texi gets regenerated.
        # The OHOS worker has no makeinfo; avoid regenerating shipped docs
        # while still executing the complete upstream test target.
        command = "make -j1 MAKEINFO=/bin/true check > %s 2>&1" % shlex.quote(log_file)
        try:
            self.run(command, env="conanbuild", cwd=source_dir)
        except ConanException:
            if os.path.isfile(log_file):
                with open(log_file, "r", encoding="utf-8", errors="replace") as handle:
                    tail = [line for line in handle.read().splitlines() if line.strip()]
                for line in tail[-40:]:
                    self.output.info("upstream-check| " + line)
            raise

        with open(log_file, "r", encoding="utf-8", errors="replace") as handle:
            log = handle.read()

        values = {}
        for key in ("TOTAL", "PASS", "SKIP", "XFAIL", "FAIL", "XPASS", "ERROR"):
            match = re.search(r"^# %s:\s+(\d+)\s*$" % key, log, re.MULTILINE)
            if match:
                values[key.lower()] = int(match.group(1))
        if "total" not in values:
            # GNU Autotest versions shipped with Anubis use the human-readable
            # summary rather than the newer `# TOTAL:` block.
            for key, pattern in (
                ("pass", r"^(\d+) tests? were successful\.\s*$"),
                ("skip", r"^(\d+) tests? were skipped\.\s*$"),
                ("fail", r"^(\d+) tests? were unsuccessful\.\s*$"),
            ):
                match = re.search(pattern, log, re.MULTILINE)
                if match:
                    values[key] = int(match.group(1))
            if "pass" in values or "skip" in values or "fail" in values:
                values.setdefault("pass", 0)
                values.setdefault("skip", 0)
                values.setdefault("fail", 0)
                values["total"] = values["pass"] + values["skip"] + values["fail"]
        if "total" not in values:
            raise ConanException("make check log has no Autotest summary")

        result = {
            "suite": "make check (GNU Autotest)",
            "static_declared": UPSTREAM_STATIC_TESTS,
            "registered": values["total"],
            "executed": values["total"] - values.get("skip", 0),
            "passed": values.get("pass", 0),
            "failed": values.get("fail", 0) + values.get("error", 0),
            "skipped": values.get("skip", 0),
            "xfail": values.get("xfail", 0),
            "xpass": values.get("xpass", 0),
            "consumer_tests": 1,
            "log": log_file,
        }
        if result["registered"] != UPSTREAM_STATIC_TESTS:
            raise ConanException(
                "Autotest registered %d cases, expected %d"
                % (result["registered"], UPSTREAM_STATIC_TESTS)
            )
        if result["failed"] or result["xpass"]:
            raise ConanException(
                "Autotest failed=%d xpass=%d" % (result["failed"], result["xpass"])
            )

        result_file = os.path.join(self.build_folder, "upstream_test_result.json")
        with open(result_file, "w", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=2)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(result, ensure_ascii=False))

    def _restore_helper_modes(self):
        # E490: source extraction on HMDFS can lose executable bits for
        # Autotools helper programs.  Restore only the known helper files.
        for relative in (
            "configure",
            "build/config.guess",
            "build/config.sub",
            "build/install-sh",
            "build/missing",
            "install-sh",
            "missing",
        ):
            path = os.path.join(self.source_folder, relative)
            if os.path.isfile(path):
                os.chmod(
                    path,
                    os.stat(path).st_mode
                    | stat.S_IXUSR
                    | stat.S_IXGRP
                    | stat.S_IXOTH,
                )

    def build(self):
        apply_conandata_patches(self)
        source_dir = self.source_folder
        self._restore_helper_modes()
        args = " ".join(shlex.quote(arg) for arg in self._configure_args())

        # Run through /bin/sh explicitly: the profile's HNP bash may fail
        # getcwd() on HMDFS even though the source directory is usable.
        self.run(
            "CONFIG_SHELL=/bin/sh SHELL=/bin/sh sh ./configure %s" % args,
            env="conanbuild",
            cwd=source_dir,
        )
        self.run("make -j1 MAKEINFO=/bin/true", env="conanbuild", cwd=source_dir)
        self._run_make_check(source_dir)

        staging = os.path.join(self.build_folder, "install-staging")
        shutil.rmtree(staging, ignore_errors=True)
        os.makedirs(staging, exist_ok=True)
        self.run(
            "make -j1 MAKEINFO=/bin/true install DESTDIR=%s prefix=/usr/local"
            % shlex.quote(staging),
            env="conanbuild",
            cwd=source_dir,
        )

    @staticmethod
    def _signer_env():
        return {
            key: value
            for key, value in os.environ.items()
            if not key.startswith("LD_LIBRARY")
        }

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_elf(self, path):
        if str(self.settings.os) != "OHOS" or not self._is_elf(path):
            return
        env = self._signer_env()
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(signer) or not os.path.isfile(objcopy):
            raise ConanInvalidConfiguration("OHOS ELF signing tools are unavailable")
        unsigned = path + ".unsigned"
        signed = path + ".signed"
        shutil.copy2(path, unsigned)
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", unsigned],
            check=False,
            capture_output=True,
            env=env,
        )
        subprocess.check_call(
            [signer, "sign", "-inFile", unsigned, "-outFile", signed, "-selfSign", "1"],
            env=env,
        )
        os.replace(signed, path)
        os.unlink(unsigned)
        os.chmod(path, 0o755)

    def package(self):
        staging_root = os.path.join(self.build_folder, "install-staging", "usr", "local")
        # Conan application packages expose executables through bin/.  The
        # upstream Autotools install target uses sbin/ for anubis, so fold
        # that directory into bin/ to keep the consumer test and R34
        # destructive check tied to the packaged artifact.
        upstream_sbin = os.path.join(staging_root, "sbin")
        if os.path.isdir(upstream_sbin):
            copy(self, "*", src=upstream_sbin, dst=os.path.join(self.package_folder, "bin"))
        for subdir in ("bin", "lib", "share"):
            source = os.path.join(staging_root, subdir)
            if os.path.isdir(source):
                copy(self, "*", src=source, dst=os.path.join(self.package_folder, subdir))
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

        for subdir in ("bin",):
            installed = os.path.join(self.package_folder, subdir)
            if not os.path.isdir(installed):
                continue
            for name in os.listdir(installed):
                self._sign_elf(os.path.join(installed, name))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
