from conan import ConanFile
import json
import os

class K2tfTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh", env="conanrun")
        # Re-emit upstream marker for cache-hit case where build() was skipped.
        # The build() stage writes hmbs_upstream.json into the package's res dir.
        # test_package must print HMBS_UPSTREAM_TEST_RESULT every run, otherwise
        # HMBS evidence gate sees discovered=0 on cache hit.
        upstream = None
        candidates = []
        try:
            pkg_name = self.tested_reference_str.split("/")[0] if "/" in self.tested_reference_str else "k2tf"
            for dep_name in [pkg_name, "k2tf"]:
                try:
                    dep = self.dependencies[dep_name]
                    pf = getattr(dep, "package_folder", None)
                    if pf:
                        candidates.append(os.path.join(pf, "res", "hmbs_upstream.json"))
                        candidates.append(os.path.join(pf, "hmbs_upstream.json"))
                except Exception:
                    continue
        except Exception:
            pass
        for env_key in ["CONAN_PACKAGE_FOLDER", "CONAN_K2TF_PACKAGE_FOLDER"]:
            v = os.environ.get(env_key)
            if v:
                candidates.append(os.path.join(v, "res", "hmbs_upstream.json"))
        seen = set()
        for cand in list(candidates):
            if cand and cand not in seen:
                seen.add(cand)
                try:
                    if os.path.isfile(cand):
                        with open(cand, "r", encoding="utf-8") as _fh:
                            upstream = json.load(_fh)
                        break
                except Exception:
                    continue
        if upstream is not None:
            msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
            print(msg, flush=True)
            self.output.info(msg)
        else:
            # Persisted build()-time result is genuinely unavailable (e.g. stale cache from
            # an old package built before the res/hmbs_upstream.json copy logic existed).
            # The real go test always runs inside build(); the package carried the real
            # result forward. Do NOT invent counts here: per HMBS rule "宁缺毋假", emit an
            # honest non-passing marker with the searched paths so the evidence gate flags
            # this instead of a fabricated pass.
            not_found = {
                "status": "failed",
                "framework": "go test",
                "command": "go test -v -count=1 ./...",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "persisted upstream result unavailable: searched " + ", ".join(sorted(seen)) + " ; the real go test ran during build() but its res/hmbs_upstream.json is missing (stale cache) - require a fresh build, do not fabricate counts"
            }
            msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(not_found, ensure_ascii=False)
            print(msg, flush=True)
            self.output.info(msg)
