#!/usr/bin/env python3
"""Conan test_package for libbpp-seq 2.4.1 — exercises the real public API.

Builds test_bpp_seq.cpp (DNA/RNA/proteic alphabets, BasicSequence,
SequenceTools motif search, VectorSequenceContainer) with CMake and runs it
via ctest. Emits the HMBS_TEST_PACKAGE_RESULT marker with the real assertion
count from the test source (8 checks), and re-emits the upstream ctest result
persisted by the main recipe (res/upstream_test_result.json) so the evidence
survives package cache hits (libcanard pattern).
"""
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class LibbppSeqTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # New route (differs from the previous CMAKE_PREFIX_PATH scan):
        # inject the tested package folder as an absolute CMake cache var so
        # test_package links libbpp-seq.a/libbpp-core.a by absolute path
        # without relying on find_package targets (whose shared objects carry
        # a slash-containing DT_NEEDED unresolvable on OHOS/musl).
        tc = CMakeToolchain(self)
        pkg_folder = None
        try:
            for dep in self.dependencies.values():
                try:
                    name = dep.ref.name if getattr(dep, "ref", None) else ""
                except Exception:
                    name = ""
                if name == "libbpp-seq" and getattr(dep, "package_folder", None):
                    pkg_folder = dep.package_folder
                    break
            if pkg_folder is None:
                # Fallback: match by tested reference string prefix.
                ref = str(getattr(self, "tested_reference_str", ""))
                want = ref.split("/")[0] if "/" in ref else ref
                for dep in self.dependencies.values():
                    try:
                        n = dep.ref.name if getattr(dep, "ref", None) else ""
                    except Exception:
                        n = ""
                    if n == want and getattr(dep, "package_folder", None):
                        pkg_folder = dep.package_folder
                        break
        except Exception:
            pkg_folder = None
        if pkg_folder:
            tc.cache_variables["LIBBPP_SEQ_PACKAGE_FOLDER"] = pkg_folder.replace("\\", "/")
            self.output.info("test_package package folder: %s" % pkg_folder)
        else:
            self.output.warning("test_package package folder unknown; CMake falls back to targets")
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _tested_package_folder(self):
        """Locate the tested libbpp-seq package folder."""
        try:
            for dep in self.dependencies.values():
                try:
                    name = dep.ref.name if getattr(dep, "ref", None) else ""
                except Exception:
                    name = ""
                if name == "libbpp-seq" and getattr(dep, "package_folder", None):
                    return dep.package_folder
            ref = str(getattr(self, "tested_reference_str", ""))
            want = ref.split("/")[0] if "/" in ref else ref
            for dep in self.dependencies.values():
                try:
                    n = dep.ref.name if getattr(dep, "ref", None) else ""
                except Exception:
                    n = ""
                if n == want and getattr(dep, "package_folder", None):
                    return dep.package_folder
        except Exception:
            pass
        return None

    def _ctest_bin(self):
        """Resolve ctest to an absolute binary (CI worker base PATH has none).

        Same failure class as PR #10479 build #48961's missing cmake: raw
        subprocess.run() does not inherit Conan's aggregated buildenv, so a
        bare "ctest" fails with FileNotFoundError on CI. Order: HMBS conf,
        HMBS env, cmake sibling dir, PATH, absolute HNP fallbacks.
        """
        try:
            conf_path = self.conf.get("user.hmbs:cmake_path", default=None, check_type=str)
        except Exception:
            conf_path = None
        if conf_path:
            sibling = os.path.join(os.path.dirname(conf_path), "ctest")
            if os.path.isfile(sibling):
                return sibling
        for env_var in ("HMBS_CMAKE", "CMAKE"):
            base = os.environ.get(env_var)
            if base:
                sibling = os.path.join(os.path.dirname(base), "ctest")
                if os.path.isfile(sibling):
                    return sibling
        found = shutil.which("ctest")
        if found:
            return found
        for cand in (
            "/data/service/hnp/bin/ctest",
            "/storage/Users/currentUser/usr/local/bin/ctest",
            "/usr/local/bin/ctest",
            "/usr/bin/ctest",
        ):
            if os.path.isfile(cand):
                return cand
        self.output.warning("ctest not found via conf/env/PATH/HNP fallbacks; trying bare 'ctest'")
        return "ctest"

    def _emit_upstream_evidence(self):
        """Re-emit the upstream ctest result persisted by the main recipe."""
        pkg_folder = self._tested_package_folder()
        if not pkg_folder:
            raise RuntimeError("tested package folder unknown; cannot re-emit upstream result")
        res_json = os.path.join(pkg_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(res_json):
            raise RuntimeError("upstream_test_result.json missing from package res/")
        with open(res_json, "r", encoding="utf-8") as fh:
            upstream = json.load(fh)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
        if (upstream.get("status") != "passed"
                or int(upstream.get("discovered", 0)) <= 0
                or int(upstream.get("executed", 0)) != int(upstream.get("discovered", 0))
                or int(upstream.get("passed", 0)) != int(upstream.get("discovered", 0))):
            raise RuntimeError("upstream result invalid: %s" % (upstream,))
        return upstream

    def test(self):
        # 8 explicit checks in test_bpp_seq.cpp (see REQUIRE list below).
        discovered = 8
        if not can_run(self):
            self.output.info("cross-building: consumer linked but cannot run")
            marker = {
                "executed": False,
                "passed": False,
                "command": "ctest --output-on-failure -R test_bpp_seq",
                "discovered": discovered,
                "passedCount": 0,
            }
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
            try:
                self._emit_upstream_evidence()
            except Exception as exc:
                self.output.warning("cannot re-emit upstream evidence: %s" % exc)
            return
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries directly,
        # so wrap the test command with the bash from the build environment.
        # Consumer binary links bpp-seq-shared; ensure the musl loader finds
        # the tested package's lib dir via absolute LD_LIBRARY_PATH.
        lib_dirs = []
        try:
            for dep in self.dependencies.values():
                pkg = getattr(dep, "package_folder", None)
                if not pkg:
                    continue
                for sub in ("lib", "lib64"):
                    d = os.path.join(pkg, sub)
                    if os.path.isdir(d) and d not in lib_dirs:
                        lib_dirs.append(d)
        except Exception:
            pass
        env = dict(os.environ)
        if lib_dirs:
            old_ld = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = ":".join(lib_dirs) + (":" + old_ld if old_ld else "")
            self.output.info("test_package lib dirs: %s" % ":".join(lib_dirs))
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        ctest_bin = self._ctest_bin()
        self.output.info("test_package ctest binary: %s" % ctest_bin)
        if os.path.isfile(bash):
            argv = [bash, "-c", ctest_bin + " -V --output-on-failure -R test_bpp_seq"]
        else:
            # No bash on this host: no shell features are used, run directly.
            argv = [ctest_bin, "-V", "--output-on-failure", "-R", "test_bpp_seq"]
        proc = subprocess.run(
            argv,
            cwd=self.build_folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=600,
            env=env,
        )
        output = proc.stdout or ""
        self.output.info(output[-3000:])
        # The test binary prints one "CHECK OK <n>/8" line per passing check;
        # counting them proves the binary really executed (exit-0-alone is
        # not proof — see toybox tar B-flag lesson).
        passed_count = len(re.findall(r"CHECK OK \d+/8", output))
        passed = proc.returncode == 0 and passed_count == discovered
        marker = {
            "executed": True,
            "passed": bool(passed),
            "command": "ctest -V --output-on-failure -R test_bpp_seq",
            "discovered": discovered,
            "passedCount": passed_count,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
        # L0d quality gate requires a literal self.run() execution in
        # test_package; re-run the consumer ctest through Conan's runner as
        # second real proof (static-linked binary, bash wrapper for OHOS mksh).
        if lib_dirs:
            _old = os.environ.get("LD_LIBRARY_PATH", "")
            _want = ":".join(lib_dirs) + (":" + _old if _old else "")
            if _old != _want:
                os.environ["LD_LIBRARY_PATH"] = _want
        self.run(f'{bash} -c "{ctest_bin} --output-on-failure -R test_bpp_seq"', cwd=self.build_folder, env="conanrun")
        # Re-emit the upstream suite result persisted by the main recipe so
        # the evidence survives package cache hits (build() skipped).
        self._emit_upstream_evidence()
        if not passed:
            raise RuntimeError(
                "test_package failed: exit=%d passedCount=%d/%d" % (proc.returncode, passed_count, discovered)
            )
