#!/usr/bin/env python3
"""Conan test_package — castget 2.0.1 (RSS/podcast downloader, executable).

test.sh drives the packaged `castget` binary through real behaviour:
version banner, a local file:// RSS feed parsed via the full stack
(libxml2 parse + curl fetch + channel listing), a --catchup run, and the
error path for a missing configuration file. It prints the
HMBS_TEST_PACKAGE_RESULT machine-evidence marker.

HMBS_UPSTREAM_TEST_RESULT: the upstream GLib testsuite (tests/, 3 programs
/ 9 cases) runs for real inside recipe build() (`make check`); the summary
is persisted as res/upstream_test_result.json in the package and
re-emitted here for every preflight log.
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class CastgetTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["castget"].package_folder
        bin_path = os.path.join(package_folder, "bin", "castget")
        assert os.path.isfile(bin_path), "castget binary not found: %s" % bin_path

        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test.sh")
            shell = os.environ.get("SHELL", "/bin/sh")
            cwd = os.environ.get("TMPDIR") or os.environ.get("TMP") or self.recipe_folder
            # castget dynamically links glib/libxml2/curl: run the script in
            # the conanrun environment so the loader finds the dependency .so
            # files (VirtualRunEnv generates them).
            self.run('"%s" "%s" "%s" "%s"' % (
                shell, test_script, bin_path, package_folder), cwd=cwd,
                env="conanrun")
            # HMBS_TEST_PACKAGE_RESULT is printed by test.sh itself.
        else:
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)
            assert magic == b"\x7fELF", "castget is not an ELF binary: %r" % magic
            self.output.info("castget binary exists and has ELF magic: %s" % bin_path)

        result_file = os.path.join(package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(result_file):
            raise ConanException(
                "upstream_test_result.json missing in package: %s — "
                "build() must have failed to persist the upstream test result"
                % result_file)
        with open(result_file, "r", encoding="utf-8") as f:
            upstream = json.load(f)
        print("HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(upstream, ensure_ascii=False), flush=True)
