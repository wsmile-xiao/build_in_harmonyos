import json
import os
import shutil

from conan import ConanFile


class DeltarpmTestConan(ConanFile):
    """test_package for deltarpm tools.

    Runs two behavioral smoke cases (each a shell script invoking the real
    binaries and asserting on their diagnostic output), then emits the HMBS
    machine-evidence markers with truthful per-case counts.
    """

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _bindir(self):
        ref_name = self.tested_reference_str.split("/")[0]
        dep = self.dependencies[ref_name]
        return os.path.join(dep.package_folder, "bin")

    def test(self):
        # 与主配方同等校验回退: conf/环境硬编码shell缺失时回退PATH查找,
        # 保证编译与运行相位一致 (naga经验).
        bash = None
        for cand in (os.environ.get("CONFIG_SHELL"), os.environ.get("SHELL")):
            if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
                bash = cand
                break
        if bash is None:
            bash = shutil.which("bash") or shutil.which("sh") or "/bin/sh"
        bindir = self._bindir()
        cases = [
            "test_iso_tools.sh",
            "test_rpm_tools.sh",
        ]
        discovered = len(cases)
        passed = 0
        try:
            for script in cases:
                self.run('%s %s "%s"' % (bash, script, bindir), env="conanrun")
                passed += 1
        except Exception as exc:
            self.output.error("test_package case failed: %s" % exc)
            raise
        finally:
            try:
                tp = {
                    "executed": True,
                    "passed": passed == discovered,
                    "command": "bash test_iso_tools.sh + bash test_rpm_tools.sh",
                    "discovered": discovered,
                    "passedCount": passed,
                }
                msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp, ensure_ascii=False)
                print(msg, flush=True)
                self.output.info(msg)
            except Exception:
                pass
            # Re-emit upstream evidence every round (build() is skipped on cache hit).
            try:
                upstream = {
                    "status": "no_tests",
                    "framework": "make",
                    "command": "make (upstream has no check/test target)",
                    "discovered": 0,
                    "executed": 0,
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "reason": "deltarpm-3.6.5 audited: top Makefile has no check/test target; "
                    "tarball has no tests/ dir and no TEST/TEST_F/def test_ cases "
                    "(only bundled-zlib contrib samples); make check would be a no-op",
                }
                msg2 = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
                print(msg2, flush=True)
                self.output.info(msg2)
            except Exception:
                pass
        if passed != discovered:
            from conan.errors import ConanException

            raise ConanException("test_package smoke cases failed")
