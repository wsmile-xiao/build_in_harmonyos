#!/usr/bin/env python3
"""Conan test_package — blogc 0.20.1 (blog compiler, executable tools).

test.sh drives the packaged `blogc` binary end to end: it renders a real
template + source post and asserts the rendered output, then prints the
HMBS_TEST_PACKAGE_RESULT machine-evidence marker consumed by hmbs/preflight.

HMBS_UPSTREAM_TEST_RESULT: the upstream testsuite (cmocka unit programs +
end-to-end shell suites) runs on the real device inside recipe build()
(`make check` in a signed executable workspace). The summary is persisted
as res/upstream_test_result.json in the package and re-emitted here, so the
marker also appears in preflight logs that reuse the cached package without
re-running build().
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class BlogcTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["blogc"].package_folder
        bin_path = os.path.join(package_folder, "bin", "blogc")
        assert os.path.isfile(bin_path), "blogc binary not found: %s" % bin_path

        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test.sh")
            shell = os.environ.get("SHELL", "/bin/sh")
            cwd = os.environ.get("TMPDIR") or os.environ.get("TMP") or self.recipe_folder
            self.run('"%s" "%s" "%s" "%s"' % (
                shell, test_script, bin_path, package_folder), cwd=cwd)
            # HMBS_TEST_PACKAGE_RESULT is printed by test.sh itself.
        else:
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)
            assert magic == b"\x7fELF", "blogc is not an ELF binary: %r" % magic
            self.output.info("blogc binary exists and has ELF magic: %s" % bin_path)

        # Re-emit the upstream testsuite result recorded by build() on the
        # real device; the marker must appear in every preflight log.
        result_file = os.path.join(package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(result_file):
            raise ConanException(
                "upstream_test_result.json missing in package: %s — "
                "build() must have failed to persist the upstream test result"
                % result_file)
        with open(result_file, "r", encoding="utf-8") as f:
            upstream = json.load(f)
        print("HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(upstream, ensure_ascii=False), flush=True)
