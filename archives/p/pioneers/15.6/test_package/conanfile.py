#!/usr/bin/env python3
"""Consumer test for pioneers 15.6 (application package).

Every packaged executable is actually executed (R34 / 积分赛补全测试):
- Contract smoke (6/6): the headless programs (pioneers-server-console,
  pioneers-metaserver, pioneersai) must answer `--version` with exit 0 and a
  "15.6" banner; the GTK3 programs (pioneers, pioneers-editor,
  pioneers-server-gtk) parse `--help` through GOption before gtk_init, so on
  a display-less OHOS host `--help` still exits 0 and prints usage.
- Integration (2/2, 上游 .game fixture 驱动): pioneers-server-console loads
  the upstream `small.game` definition and reaches the "Preparing game"
  state (real game-initialisation code path, not just a banner);
  pioneers-metaserver starts and stays alive as the game directory service.

Upstream pioneers 15.6 ships no automated tests (N=0, see MANIFEST.yml);
the assertions above are the adapted-side tests补全 carried by this package.
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException


class PioneersTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["pioneers"].package_folder
        bin_dir = os.path.join(package_folder, "bin")
        if not os.path.isdir(bin_dir):
            raise ConanException(f"package lacks bin directory: {bin_dir}")
        for program in ("pioneers", "pioneersai", "pioneers-editor",
                        "pioneers-server-console", "pioneers-server-gtk",
                        "pioneers-metaserver"):
            binary = os.path.join(bin_dir, program)
            if not os.path.isfile(binary):
                raise ConanException(f"packaged program missing: {binary}")

        shell = (os.environ.get("CONFIG_SHELL")
                 or os.environ.get("SHELL") or "/bin/sh")
        script = os.path.join(self.recipe_folder, "test_pioneers.sh")
        fixture_dir = os.path.join(self.recipe_folder, "fixtures")
        # Write the harness result outside the recipe tree: in-place conan
        # create would otherwise leave a build artifact inside the archive
        # (junk-check/JC blocks it).
        result_file = os.path.join(
            os.environ.get("TMPDIR", os.path.expanduser("~/tmp")),
            "pioneers-15.6-test-result.txt")

        run_ok = True
        try:
            self.run(
                f'"{shell}" "{script}" "{bin_dir}" "{result_file}" '
                f'"{fixture_dir}"',
                env=["conanrun"],
            )
        except Exception:
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
            "command": f"sh test_pioneers.sh <pkg>/bin {result_file}",
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False))
        if not result["passed"]:
            raise ConanException(
                f"pioneers consumer test failed: {passed}/{discovered} "
                "assertions passed (see harness output above)")
