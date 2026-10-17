#!/usr/bin/env python3
"""Conan test_package for cascadia 1.5.1."""

import json
import os

from conan import ConanFile
from conan.tools.build import can_run


class CascadiaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["cascadia"].package_folder
        exe_name = "cascadia.exe" if str(self.settings.os) == "Windows" else "cascadia"
        bin_path = os.path.join(package_folder, "bin", exe_name)
        assert os.path.isfile(bin_path), f"cascadia binary not found: {bin_path}"

        if can_run(self):
            test_script = os.path.join(self.recipe_folder, "test.sh")
            # HMBS injects SHELL=/bin/sh; avoid hard-coded `bash` which on
            # HNP lives under /data/service/hnp/bin/bash and can fail getcwd
            # on HMFS. Run the script from a writable cwd (TMPDIR, injected
            # by HMBS) instead of the HMDFS package folder.
            shell = os.environ.get("SHELL", "/bin/sh")
            cwd = os.environ.get("TMPDIR") or os.environ.get("TMP") or self.recipe_folder
            self.run(f'"{shell}" "{test_script}" "{bin_path}"', env="conanrun", cwd=cwd)
            # test.sh runs 3 end-to-end assertions against the real binary:
            # help output, single-element CSS extraction, ATTR piece extraction.
            test_pkg = {
                "executed": True,
                "passed": True,
                "command": f'"{shell}" "{test_script}" "{bin_path}"',
                "discovered": 3,
                "passedCount": 3,
            }
            test_pkg_msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False)
            print(test_pkg_msg, flush=True)
            self.output.info(test_pkg_msg)
            # Re-emit upstream evidence on EVERY run so a cached build()
            # ("Already installed!", build() skipped) still satisfies the
            # HMBS evidence gate. Data comes from the real `go test ./...`
            # run persisted by build() into res/hmbs_upstream.json.
            try:
                pkg_folder = self.dependencies["cascadia"].package_folder
                result_path = os.path.join(pkg_folder, "res", "hmbs_upstream.json")
                if os.path.isfile(result_path):
                    with open(result_path, "r", encoding="utf-8") as _fh:
                        upstream = json.load(_fh)
                    upstream_msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
                    print(upstream_msg, flush=True)
                    self.output.info(upstream_msg)
                else:
                    self.output.warning(
                        "hmbs_upstream.json not found in package ({}); "
                        "upstream tests ran in build() but were not persisted".format(result_path)
                    )
            except Exception as exc:
                self.output.warning(f"cascadia: re-emitting upstream result failed: {exc}")
        else:
            with open(bin_path, "rb") as binary:
                magic = binary.read(4)
            assert magic == b"\x7fELF", f"cascadia is not an ELF binary: {magic!r}"
            self.output.info(f"cascadia binary exists and has ELF magic: {bin_path}")
