#!/usr/bin/env python3
"""Consumer test for avahi-tools 0.9_rc5.

Executes the packaged command-line utilities and checks their offline CLI
contract (--help/--version exit codes and output content, argument
validation failure paths). The harness script counts real assertions,
writes discovered/passed counters to a result file, and this conanfile
emits exactly one HMBS_TEST_PACKAGE_RESULT marker from those counters.
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException


class AvahiToolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["avahi-tools"].package_folder
        bin_dir = os.path.join(package_folder, "bin")
        if not os.path.isdir(bin_dir):
            raise ConanException(f"package lacks bin directory: {bin_dir}")
        for program in ("avahi-browse", "avahi-resolve", "avahi-publish",
                        "avahi-set-host-name"):
            binary = os.path.join(bin_dir, program)
            if not os.path.isfile(binary):
                raise ConanException(f"packaged program missing: {binary}")

        shell = (os.environ.get("CONFIG_SHELL")
                 or os.environ.get("SHELL") or "/bin/sh")
        script = os.path.join(self.recipe_folder, "test_avahi_tools.sh")
        base_dir = getattr(self, "build_folder", None) or os.getcwd()
        result_file = os.path.join(base_dir, "avahi-tools-test-result.txt")

        # OHOS: wrap the harness in the platform-provided shell instead of
        # relying on shebang execution, and run it with the conanrun env so
        # the packaged binaries resolve correctly.
        run_ok = True
        try:
            self.run(
                f'"{shell}" "{script}" "{bin_dir}" "{result_file}"',
                env="conanrun",
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
            "command": f"sh test_avahi_tools.sh <pkg>/bin {result_file}",
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False))
        if not result["passed"]:
            raise ConanException(
                f"avahi-tools consumer test failed: {passed}/{discovered} "
                "assertions passed (see harness output above)")
