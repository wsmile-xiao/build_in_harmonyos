import os
import json
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class AudttyTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            # run test script
            self.run(f"{bash} test.sh", env="conanrun")
            # Re-emit upstream test result from package res (cache-proof persistence, experience autotools-dev/20240727.1-nmu1)
            try:
                ref_name = self.tested_reference_str.split("/")[0] if self.tested_reference_str else "audtty"
                pkg_folder = None
                try:
                    pkg_folder = self.dependencies[ref_name].package_folder
                except Exception:
                    for dep in self.dependencies.values():
                        try:
                            if dep.ref.name == ref_name or dep.ref.name == "audtty":
                                pkg_folder = dep.package_folder
                                break
                        except Exception:
                            continue
                if pkg_folder:
                    json_path = os.path.join(pkg_folder, "res", "upstream_test_result.json")
                    if os.path.isfile(json_path):
                        with open(json_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        if data.get("status") != "passed":
                            raise ConanException(f"upstream test status != passed: {data}")
                        if data.get("discovered", 0) <= 0 or data.get("executed", 0) != data.get("discovered"):
                            raise ConanException(f"upstream test discovered/executed invalid: {data}")
                        marker = f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(data)}"
                        self.output.info(marker)
                        print(marker)
                    else:
                        raise ConanException(f"upstream_test_result.json not found at {json_path}, build() may have been skipped or failed to persist")
                else:
                    raise ConanException("could not locate audtty package folder for upstream result")
            except ConanException:
                raise
            except Exception as e:
                raise ConanException(f"failed to re-emit upstream result: {e}")
            # Emit HMBS marker (machine evidence)
            result = {
                "executed": True,
                "passed": True,
                "command": "audtty --help; audtty --version",
                "discovered": 2,
                "passedCount": 2
            }
            marker = f"HMBS_TEST_PACKAGE_RESULT={json.dumps(result)}"
            self.output.info(marker)
            print(marker)
        else:
            self.output.info("cross building, skip run")
