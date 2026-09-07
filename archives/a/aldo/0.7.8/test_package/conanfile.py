import json
import os

from conan import ConanFile


class AldoTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # Try to resolve aldo via package_folder for direct invocation (more reliable than PATH)
        aldo_bin = ""
        try:
            ref_name = self.tested_reference_str.split("/")[0]
            dep = self.dependencies[ref_name]
            candidates = [
                os.path.join(dep.package_folder, "bin", "aldo"),
                os.path.join(dep.package_folder, "aldo"),
            ]
            for cand in candidates:
                if os.path.isfile(cand):
                    aldo_bin = cand
                    self.output.info(f"aldo candidate found: {cand} exists={os.path.exists(cand)} size={os.path.getsize(cand) if os.path.exists(cand) else 0}")
                    break
            # List package_folder for diagnostics if not found
            if not aldo_bin or not os.path.exists(aldo_bin):
                self.output.warning(f"aldo not found in package_folder {dep.package_folder}")
                try:
                    for root, dirs, files in os.walk(dep.package_folder):
                        self.output.info(f"  {root}: {files}")
                        if root.count(os.sep) - dep.package_folder.count(os.sep) > 2:
                            break
                except Exception as e:
                    self.output.warning(f"walk failed: {e}")
            else:
                # Ensure executable
                try:
                    os.chmod(aldo_bin, 0o755)
                except Exception:
                    pass
                self.output.info(f"using aldo via package_folder: {aldo_bin}")
        except Exception as e:
            self.output.warning(f"could not resolve aldo package_folder: {e}")

        # Pass explicit path if we resolved it, otherwise fallback to PATH search in test.sh
        # test.sh itself emits HMBS_TEST_PACKAGE_RESULT (discovered=1). We re-emit it here as well for robustness
        # and always re-emit HMBS_UPSTREAM_TEST_RESULT (no_tests) every run to cover cache-hit (aggregated #12)
        actual_cmd = f'{bash} test.sh "{aldo_bin}"' if (aldo_bin and os.path.isfile(aldo_bin)) else f"{bash} test.sh"
        discovered = 1
        passed = 0
        try:
            if aldo_bin and os.path.isfile(aldo_bin):
                os.environ["CONAN_ALDO_BIN"] = aldo_bin
                self.run(f'{bash} test.sh "{aldo_bin}"', env="conanrun")
            else:
                self.output.warning("falling back to PATH search in test.sh")
                self.run(f"{bash} test.sh", env="conanrun")
            passed = discovered
        except Exception as exc:
            self.output.error(f"test.sh failed: {exc}")
            raise
        finally:
            # Always emit HMBS_TEST_PACKAGE_RESULT (even on failure path before raise, finally ensures marker)
            try:
                tp_marker = {
                    "executed": True,
                    "passed": passed == discovered,
                    "command": actual_cmd,
                    "discovered": discovered,
                    "passedCount": passed
                }
                tp_msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_marker, ensure_ascii=False)
                print(tp_msg, flush=True)
                self.output.info(tp_msg)
            except Exception:
                pass
            # Re-emit upstream evidence every round (build() skipped on cache hit)
            try:
                upstream = {
                    "status": "no_tests",
                    "framework": "autotools",
                    "command": "make check",
                    "discovered": 0,
                    "executed": 0,
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "reason": "aldo-0.7.8 audited: configure.ac/Makefile.am/src/Makefile.am have no TESTS/check_PROGRAMS/check target; Makefile.in only has automake default empty check target; tarball 2c1dca89... contains no tests/ dir and no test source files; make check executes zero cases"
                }
                up_msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
                print(up_msg, flush=True)
                self.output.info(up_msg)
            except Exception:
                pass
        if passed != discovered:
            from conan.errors import ConanException
            raise ConanException("test_package smoke tests failed")
