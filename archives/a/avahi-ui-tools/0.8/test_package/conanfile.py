#!/usr/bin/env python3
"""Consumer test for avahi-ui-tools 0.8 (application package).

Exercises the packaged bssh binary (plus its bvnc/bshell aliases) through
its offline CLI contract.  bssh is a GTK3 dialog utility: real browsing
needs a live avahi-daemon and an interactive session, so the harness
verifies binary presence, alias derivation, and the failure path that
runs before gtk_init (unknown option → usage on stderr, non-zero
exit).  The harness script counts real assertions and writes
discovered/passed counters; this conanfile emits one
HMBS_TEST_PACKAGE_RESULT marker from those counters.
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment


class AvahiUiToolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # The GTK stack's shared objects (e.g. libharfbuzz.so) are C++
        # binaries that require libc++_shared.so from the platform SDK;
        # the conan-run library path does not include the system dir by
        # default on OHOS, so expose it explicitly at test time.
        run_env = Environment()
        run_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        run_env.vars(self).save_script("system_run_env")

    def test(self):
        package_folder = self.dependencies["avahi-ui-tools"].package_folder
        bin_dir = os.path.join(package_folder, "bin")
        if not os.path.isdir(bin_dir):
            raise ConanException(f"package lacks bin directory: {bin_dir}")
        for program in ("bssh", "bvnc", "bshell"):
            binary = os.path.join(bin_dir, program)
            if not os.path.islink(binary) and not os.path.isfile(binary):
                raise ConanException(f"packaged program missing: {binary}")

        shell = (os.environ.get("CONFIG_SHELL")
                 or os.environ.get("SHELL") or "/bin/sh")
        script = os.path.join(self.recipe_folder, "test_avahi_ui_tools.sh")
        base_dir = getattr(self, "build_folder", None) or os.getcwd()
        result_file = os.path.join(base_dir, "avahi-ui-tools-test-result.txt")

        run_ok = True
        try:
            self.run(
                f'"{shell}" "{script}" "{bin_dir}" "{result_file}"',
                env=["conanrun", "system_run_env"],
            )
        except Exception:
            # Harness failure must not skip the marker emission below.
            run_ok = False

        discovered = 0
        passed = 0
        if os.path.isfile(result_file):
            with open(result_file, "r", encoding="utf-8") as handle:
                for line in handle:
                    parts = line.split()
                    if len(parts) == 2 and parts[0] == "discovered":
                        discovered = int(parts[1])
                    elif len(parts) == 2 and parts[0] == "passed":
                        passed = int(parts[1])
        result = {
            "executed": True,
            "passed": bool(run_ok and discovered > 0 and passed == discovered),
            "command": f"sh test_avahi_ui_tools.sh <pkg>/bin {result_file}",
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False))
        if not result["passed"]:
            raise ConanException(
                f"avahi-ui-tools consumer test failed: {passed}/{discovered} "
                "assertions passed (see harness output above)")