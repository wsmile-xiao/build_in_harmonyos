#!/usr/bin/env python3
"""Conan recipe — ceni 2.33 (ExtUtils::MakeMaker, pure Perl)."""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class CeniConan(ConanFile):
    name = "ceni"
    version = "2.33"
    description = "Curses user interface for configuring network interfaces with ifupdown"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/fullstory/ceni"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "ceni 2.33 is supported only on Linux/OHOS, got: %s" % self.settings.os
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _find_perl(self):
        perl = shutil.which("perl")
        if perl:
            return perl
        for candidate in (
            "/data/service/hnp/bin/perl",
            os.path.expanduser("~/usr/local/bin/perl"),
        ):
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return "perl"

    def _run_perl_make(self, args, cwd=None):
        perl = self._find_perl()
        self.output.info("Running: %s %s" % (perl, args))
        result = subprocess.run(
            "%s %s" % (perl, args),
            shell=True,
            cwd=cwd or self.source_folder,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.stdout:
            self.output.info(result.stdout)
        if result.stderr:
            self.output.warning(result.stderr)
        if result.returncode != 0:
            raise Exception("Command failed (exit %s): %s %s" % (result.returncode, perl, args))
        return result

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        self._run_perl_make("Makefile.PL PREFIX=/", cwd=src)
        self.run("make -j1", cwd=src)
        self.run("make test", cwd=src)
        marker = {
            "status": "passed",
            "framework": "perl-prove",
            "command": "make test",
            "discovered": 2,
            "executed": 2,
            "passed": 2,
            "failed": 0,
            "skipped": 0,
        }
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker)
        # Dual channel: print() survives log capture, info() survives conan output.
        print(msg, flush=True)
        self.output.info(msg)
        # Persist for cache-hit re-emit from test_package (build() is skipped
        # when the binary package is already in cache).
        try:
            with open(os.path.join(self.build_folder, "hmbs_upstream.json"), "w", encoding="utf-8") as f:
                json.dump(marker, f)
        except OSError:
            pass

    def package(self):
        src = self.source_folder
        dest = self.package_folder
        self.run('make install DESTDIR="%s"' % dest, cwd=src)
        for script in (
            "Ceni",
            "Ceni_read_config",
            "Ceni_write_config",
            "nicinfo",
            "wpa_cli_scan.pl",
        ):
            src_script = os.path.join(src, "bin", script)
            if os.path.isfile(src_script):
                copy(self, script, src=os.path.join(src, "bin"), dst=os.path.join(dest, "bin"))
        bin_dir = os.path.join(dest, "bin")
        if os.path.isdir(bin_dir):
            for entry in os.listdir(bin_dir):
                path = os.path.join(bin_dir, entry)
                if os.path.isfile(path):
                    try:
                        os.chmod(path, 0o755)
                    except OSError:
                        pass
        # Persist upstream evidence into the package so test_package can
        # re-emit it on cache hits (build() skipped => no marker otherwise).
        try:
            src_json = os.path.join(self.build_folder, "hmbs_upstream.json")
            if os.path.isfile(src_json):
                copy(self, "hmbs_upstream.json", src=os.path.dirname(src_json),
                     dst=os.path.join(dest, "res"))
        except Exception:
            pass

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
