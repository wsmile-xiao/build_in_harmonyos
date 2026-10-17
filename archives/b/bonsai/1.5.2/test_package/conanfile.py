import json
import os
import pathlib
from conan import ConanFile
from conan.tools.build import can_run


class BonsaiTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # Re-emit upstream result if carried via package res (build may be cached)
            try:
                for base in [self.dependencies[self.tested_reference_str].package_folder] if self.tested_reference_str in self.dependencies else []:
                    summary_path = os.path.join(base, "res", "upstream_test_summary.json")
                    if os.path.isfile(summary_path):
                        with open(summary_path, "r", encoding="utf-8") as f:
                            upstream = json.load(f)
                        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
                        break
            except Exception as e:
                self.output.warning(f"re-emit upstream summary failed: {e}")

            python = os.environ.get("HMBS_PYTHON3") or "python3"
            # HMBS readonly /tmp: ensure writable tmp for any test that might use tempfile
            for key in ("TMPDIR", "TMP", "TEMP"):
                v = os.environ.get(key)
                if v and pathlib.Path(v).is_dir():
                    break
            else:
                fallback = os.environ.get("TMPDIR") or "/tmp"
                try:
                    pathlib.Path(fallback).mkdir(parents=True, exist_ok=True)
                except Exception:
                    pass

            # Run consumer tests; count assertions from test scripts (6 checks in test_bonsai.py + 1 in test_ldif.py)
            test_cmds = [
                f"{python} test_bonsai.py",
                f"{python} test_ldif.py",
            ]
            passed = 0
            failed = 0
            for cmd in test_cmds:
                try:
                    self.run(cmd, env="conanrun")
                    passed += 1
                except Exception as e:
                    self.output.error(f"test command failed {cmd}: {e}")
                    failed += 1

            # Emit HMBS test_package marker with real counts
            discovered = len(test_cmds)
            # Each test script internally runs multiple assertions; we report script-level as discovered
            # For HMBS, passedCount/discovered must reflect real test count executed
            test_pkg = {
                "executed": True,
                "passed": failed == 0,
                "command": " && ".join(test_cmds),
                "discovered": discovered,
                "passedCount": passed,
            }
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
            if failed:
                raise RuntimeError(f"test_package failed: {failed} of {discovered} scripts failed")
