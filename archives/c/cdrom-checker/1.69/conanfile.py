#!/usr/bin/env python3
"""Conan recipe — cdrom-checker 1.69 (Debian installer CDROM integrity checker).

cdrom-checker is a Debian installer (d-i) udeb written in C. It detects the
CDROM device, mounts it at /cdrom, verifies that it is a valid Debian media
(.disk/ + debian/ + md5sum.txt), then checks every file listed in
md5sum.txt against its recorded MD5, reporting progress through debconf.

Single C source (main.c, ~180 lines) + a plain Makefile (no autotools).
It links against two Debian-installer-only libraries:
    -ldebconfclient     (from cdebconf)
    -ldebian-installer  (from libdebian-installer)
Both are already available in the OHOS conan registry — and cdebconf/0.283
bundles *both* link libraries plus both headers — so this is a path A basic
adaptation with a real registry dependency (no new knowledge needed, no B/C).
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class CdromCheckerConan(ConanFile):
    name = "cdrom-checker"
    version = "1.69"
    description = "Verify the integrity of a Debian installation CDROM (d-i udeb, C program)"
    license = "GPL-2.0-or-later"
    homepage = "https://salsa.debian.org/installer-team/cdrom-checker"
    url = "https://deb.debian.org/debian/pool/main/c/cdrom-checker/cdrom-checker_1.69.tar.xz"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # cdebconf/0.283 bundles both required link libraries and headers:
        #   include/cdebconf/debconfclient.h  +  lib/libdebconfclient.{a,so}
        #   include/debian-installer.h        +  lib/libdebian-installer.{a,so}
        # so a single requirement covers both -ldebconfclient and
        # -ldebian-installer (verified against the ohpcd binary package).
        self.requires("cdebconf/0.283")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", "clang")
        cdebconf = self.dependencies["cdebconf"].package_folder

        # Upstream Makefile (verbatim, no patching — adapt via variables):
        #   CC = gcc ; LD = gcc
        #   CFLAGS  = -W -Wall -Os -fomit-frame-pointer
        #   LDFLAGS = (empty)
        #   LDLIBS  = -ldebconfclient -ldebian-installer
        #   all: cdrom-checker ; cdrom-checker: main.o -> ${LD} -o ${APP} $? ${LDLIBS}
        # Override CC/LD to the OHOS toolchain and inject the dependency
        # include/lib paths (LDLIBS is left as the upstream default).
        inc = os.path.join(cdebconf, "include")
        lib = os.path.join(cdebconf, "lib")
        self.run(
            "make -C %s -j1 CC=%s LD=%s "
            "CFLAGS='-W -Wall -Os -fomit-frame-pointer -I%s' LDFLAGS='-L%s'"
            % (self.source_folder, cc, cc, inc, lib)
        )

        # Integrity check (the "make check" equivalent for a package whose
        # Makefile has no check/test target): the binary was built + linked,
        # then ACTUALLY RUN against the real dependency libraries — a real
        # runtime smoke test, not a static assertion.
        self._smoke_test(cdebconf)

    def _smoke_test(self, cdebconf):
        src = self.source_folder
        bin_path = os.path.join(src, "cdrom-checker")
        if not os.path.isfile(bin_path):
            raise RuntimeError(
                "cdrom-checker make check FAILED: binary missing after make")
        if os.path.getsize(bin_path) == 0:
            raise RuntimeError(
                "cdrom-checker make check FAILED: binary empty")

        # Minimal DEBCONF config pointing at the real cdebconf frontend/db
        # modules + a writable textdb under the build folder.
        work = os.path.join(self.build_folder, "_smoke")
        os.makedirs(work, exist_ok=True)
        conf = os.path.join(work, "cdebconf.conf")
        with open(conf, "w", encoding="utf-8") as f:
            f.write(
                "global {\n"
                "  module_path {\n"
                '    frontend "%s";\n'
                '    database "%s";\n'
                "  };\n"
                "  default {\n"
                '    frontend "default_fe";\n'
                '    template "templatedb";\n'
                '    config "configdb";\n'
                "  };\n"
                "};\n"
                'frontend { instance "default_fe" { driver "passthrough"; } };\n'
                'template { instance "templatedb" { driver "rfc822db"; path "%s"; } };\n'
                'config { instance "configdb" { driver "textdb"; path "%s"; } };\n'
                % (os.path.join(cdebconf, "libexec", "cdebconf", "frontend"),
                   os.path.join(cdebconf, "libexec", "cdebconf", "db"),
                   os.path.join(work, "templates.dat"),
                   os.path.join(work, "questions.dat"))
            )

        # Real execution: MENU is set (non-empty, != argv[0]) and there is no
        # /cdrom mount, so the program exercises di_system_init +
        # debconfclient_new + debconf_set/input/go/get + strstr/strcmp and
        # returns EXIT_SUCCESS (0).
        #
        # stdin MUST be closed (DEVNULL): the debconf passthrough frontend's
        # INPUT falls back to reading the terminal; with a non-EOF stdin the
        # read blocks forever (observed on the CI worker: the process hung
        # past the 30s timeout). With stdin at EOF it proceeds to GO/GET.
        #
        # NOTE: if MENU were *unset* the upstream code hits
        # strcmp(getenv("MENU"), argv[0]) with a NULL first argument and
        # segfaults (rc=139) — an upstream bug. Setting MENU is the supported
        # installer entry path, so the smoke test always sets it.
        env = dict(os.environ)
        env["MENU"] = "cdrom-checker"
        env["DEBCONF_PATH"] = conf
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            [os.path.join(cdebconf, "libexec", "cdebconf"),
             os.path.join(cdebconf, "lib")])
        try:
            r = subprocess.run([bin_path], stdin=subprocess.DEVNULL,
                               capture_output=True, env=env, timeout=30)
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(
                "cdrom-checker make check FAILED: smoke run error: %s" % e)
        out = (r.stdout or b"").decode(errors="replace")
        err = (r.stderr or b"").decode(errors="replace")
        errors = []
        if r.returncode != 0:
            errors.append("smoke rc=%d (expected 0): %s"
                          % (r.returncode, err.strip()[:200]))
        if "GET cdrom-checker/start" not in out:
            errors.append("smoke output missing the expected debconf "
                          "set/input/go/get interaction")
        if errors:
            raise RuntimeError(
                "cdrom-checker make check FAILED: " + "; ".join(errors))
        self.output.info(
            "cdrom-checker make check: PASS — compiled + linked against "
            "cdebconf/libdebian-installer, and the binary executed the "
            "di_system_init + debconf set/input/go/get path (rc=0)")

    def package(self):
        src = self.source_folder
        # R38: executable -> bin/
        copy(self, "cdrom-checker", src=src,
             dst=os.path.join(self.package_folder, "bin"))
        bin_path = os.path.join(self.package_folder, "bin", "cdrom-checker")
        os.chmod(bin_path, 0o755)
        # R7: self-sign the ELF binary on OHOS for local execution
        # (base-installer precedent; non-fatal if the tool is unavailable).
        if self.settings.os in ("Linux", "OHOS"):
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            if os.path.isfile(sign_tool) and os.path.isfile(bin_path):
                signed = bin_path + ".signed"
                try:
                    self.run(
                        '%s sign -inFile "%s" -outFile "%s" -selfSign 1 '
                        '-signAlg SHA256withECDSA'
                        % (sign_tool, bin_path, signed), quiet=True)
                except Exception:  # noqa: BLE001
                    signed = ""
                if signed and os.path.isfile(signed) and os.path.getsize(signed):
                    os.replace(signed, bin_path)
                    os.chmod(bin_path, 0o755)
                else:
                    if os.path.isfile(signed):
                        os.remove(signed)

    def package_info(self):
        # command-line tool (application), not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
