#!/usr/bin/env python3
"""Conan test_package for ytt 0.55.1 - consumer smoke tests plus HMBS evidence re-emit."""
import json
import os

from conan import ConanFile


class YttTestConan(ConanFile):
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
        upstream = None
        candidates = []
        try:
            pkg_name = self.tested_reference_str.split("/")[0] if "/" in self.tested_reference_str else "ytt"
            for dep_name in [pkg_name, "ytt"]:
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
        for env_key in ["CONAN_PACKAGE_FOLDER", "CONAN_YTT_PACKAGE_FOLDER"]:
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
