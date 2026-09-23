from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
import json
import os
import shutil


class OcmtocTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "verify_mtoc.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _resolve_python(self):
        # Prefer the HMBS-injected absolute python, then PATH lookup, so the
        # test does not depend on a single PATH entry that may point at a
        # non-executable shim on the farm.
        for cand in (os.environ.get("HMBS_PYTHON3"), os.environ.get("PYTHON3")):
            if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
        found = shutil.which("python3")
        if found:
            return found
        return "python3"

    def test(self):
        if can_run(self):
            # verify_mtoc.py really executes the packaged mtoc binary:
            # --version / --fullversion output assertions + a garbage-input
            # rejection test. It exits non-zero unless 3/3 checks pass.
            # Resolve the binary by absolute path (repo precedent: b2sum/zzuf):
            # bare-name PATH lookup is fragile without an aggregated runenv
            # (CI failed with `[Errno 2] No such file or directory: 'mtoc'`).
            dep = self.dependencies["ocmtoc"]
            mtoc_bin = os.path.join(dep.package_folder, "bin", "mtoc")
            if not os.path.isfile(mtoc_bin):
                raise ConanException(
                    "packaged mtoc binary not found: {}".format(mtoc_bin))
            py = self._resolve_python()
            self.run('"%s" verify_mtoc.py "%s"' % (py, mtoc_bin),
                     env="conanrun")
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,"
                "\"command\":\"python3 verify_mtoc.py\","
                "\"discovered\":3,\"passedCount\":3}")
            # Re-emit the upstream evidence persisted by build() into the
            # package (res/upstream_test_result.json). test_package runs on
            # every preflight even when conan skips a cached build()
            # ("Already installed!"), so this is the only stable outlet for
            # the upstream marker. A missing file means the package was
            # produced without running the upstream suite: explicit failure,
            # never a silent pass. Numbers are reprinted verbatim, never
            # recomputed here.
            result_path = os.path.join(
                dep.package_folder, "res", "upstream_test_result.json")
            if not os.path.isfile(result_path):
                raise ConanException(
                    "upstream_test_result.json not found in package ({}) - "
                    "upstream tests did not run during build(); refusing to "
                    "pass silently".format(result_path))
            with open(result_path, "r", encoding="utf-8") as f:
                upstream = json.load(f)
            marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream)
            print(marker)
            self.output.info(marker)
