#!/usr/bin/env python3
"""Conan test_package — consumer-level verification for libcangjie.

Builds test_cangjie.c against the installed libcangjie package and runs it
with CANGJIE_DB pointing at the packaged share/libcangjie/cangjie.db.
The binary performs 6 real API checks (version/char/list/new/query), each
printing one "CHECK-OK:" line; the conanfile counts those lines for the
HMBS_TEST_PACKAGE_RESULT machine-evidence marker (exit-0-alone is not proof).
"""

import json
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, cmake_layout

CONSUMER_CHECK_COUNT = 6


class LibcangjieTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _ensure_writable_tmp(self):
        for key in ("TMPDIR", "TMP", "TEMP"):
            candidate = os.environ.get(key)
            if candidate and os.path.isdir(candidate):
                tmp = candidate
                break
        else:
            tmp = None
        if not tmp:
            tmp = os.path.join(self.build_folder, "hmbs-tmp")
            os.makedirs(tmp, exist_ok=True)
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        return tmp

    def build(self):
        self._ensure_writable_tmp()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _cangjie_db(self):
        try:
            pkg = str(
                self.dependencies[self.tested_reference_str].package_folder
            )
        except Exception:
            try:
                pkg = str(self.dependencies["libcangjie"].package_folder)
            except Exception:
                return ""
        for cand in (
            os.path.join(pkg, "share", "libcangjie", "cangjie.db"),
            os.path.join(pkg, "res", "share", "libcangjie", "cangjie.db"),
        ):
            if os.path.isfile(cand):
                return cand
        # Fallback: search the package folder.
        for root, _dirs, files in os.walk(pkg):
            if "cangjie.db" in files:
                return os.path.join(root, "cangjie.db")
        return ""

    def _run_env_with_dep_libs(self, db_path):
        env = dict(os.environ)
        libdirs = []
        try:
            deps = list(self.dependencies.values())
        except Exception:
            deps = []
        for dep in deps:
            try:
                pkg = str(dep.package_folder)
            except Exception:
                pkg = ""
            candidates = []
            try:
                for rel in (dep.cpp_info.libdirs or []):
                    candidates.append(
                        rel if os.path.isabs(rel)
                        else os.path.join(pkg, rel)
                    )
            except Exception:
                pass
            if pkg and not candidates:
                candidates.append(os.path.join(pkg, "lib"))
            for cand in candidates:
                try:
                    if cand and os.path.isdir(cand) and cand not in libdirs:
                        libdirs.append(cand)
                except Exception:
                    pass
        if libdirs:
            old = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                libdirs + ([old] if old else [])
            )
        if db_path:
            env["CANGJIE_DB"] = db_path
        return env

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile/link test completed")
            return
        tmp = self._ensure_writable_tmp()
        # ctest spawns test_libcangjie as a child process: it only inherits
        # what is present in os.environ at launch time. The consumer binary
        # requires CANGJIE_DB to open cangjie.db (else CANGJIE_DBOPEN) and a
        # writable TMPDIR (true-machine /tmp is read-only), so both must be
        # exported BEFORE cmake.test(), not only inside _run_consumer_binary().
        db_path = self._cangjie_db()
        if db_path:
            os.environ["CANGJIE_DB"] = db_path
            self.output.info("using CANGJIE_DB=%s for ctest" % db_path)
        else:
            self.output.warning(
                "cangjie.db not found in package; ctest runs without CANGJIE_DB"
            )
        self.output.info("using TMPDIR=%s for ctest" % os.environ.get("TMPDIR", ""))
        cmake = CMake(self)
        try:
            try:
                cmake.test(env="conanrun")
            except TypeError:
                ctest_dir = self.build_folder
                try:
                    for root, _dirs, files in os.walk(self.build_folder):
                        if "CTestTestfile.cmake" in files:
                            ctest_dir = root
                            break
                except Exception:
                    pass
                self.run(
                    "ctest --output-on-failure --no-tests=error",
                    cwd=ctest_dir,
                    env="conanrun",
                )
        except Exception as exc:
            self.output.warning("ctest failed: %s" % exc)
            self._run_consumer_binary(raise_on_failure=False)
            raise
        self._run_consumer_binary(raise_on_failure=True)
        self._reemit_upstream_result()
        self.output.info("libcangjie consumer test_package passed")

    def _reemit_upstream_result(self):
        # Re-emit the real in-build upstream result on EVERY run. Conan
        # skips build() when the package binary is cached, so the marker
        # printed there disappears; test_package runs every preflight, so
        # re-printing the persisted JSON keeps upstream evidence present.
        # Counts are the real meson-test numbers from the device run that
        # produced the package; nothing is redefined here.
        upstream = None
        try:
            dep = None
            try:
                dep = self.dependencies[self.tested_reference_str]
            except Exception:
                try:
                    dep = self.dependencies["libcangjie"]
                except Exception:
                    dep = None
            pkg = str(getattr(dep, "package_folder", "") or "") if dep else ""
            if pkg:
                for cand in (
                    os.path.join(pkg, "res", "hmbs_upstream.json"),
                    os.path.join(pkg, "res", "upstream_test_result.json"),
                ):
                    if os.path.isfile(cand):
                        with open(cand, "r", encoding="utf-8") as handle:
                            upstream = json.load(handle)
                        break
        except Exception as exc:
            self.output.warning("read persisted upstream result failed: %s" % exc)
            upstream = None
        if isinstance(upstream, dict) and upstream.get("discovered"):
            msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
                upstream, ensure_ascii=False
            )
            print(msg, flush=True)
            self.output.info(msg)
        else:
            raise ConanException(
                "hmbs_upstream.json missing in package; upstream tests did "
                "not run during build(); refusing to pass silently"
            )

    def _run_consumer_binary(self, raise_on_failure):
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_libcangjie")
        if not os.path.isfile(bin_path):
            raise ConanException("test binary missing: %s" % bin_path)
        db_path = self._cangjie_db()
        if not db_path:
            self.output.warning("cangjie.db not found in package; running without CANGJIE_DB")
        else:
            self.output.info("using CANGJIE_DB=%s" % db_path)
        proc = subprocess.run(
            [bin_path],
            env=self._run_env_with_dep_libs(db_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
        )
        output = proc.stdout or ""
        self.output.info(output[-3000:])
        ok_count = output.count("CHECK-OK:")
        marker = {
            "executed": True,
            "passed": proc.returncode == 0 and ok_count == CONSUMER_CHECK_COUNT,
            "command": bin_path,
            "discovered": CONSUMER_CHECK_COUNT,
            "passedCount": ok_count,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
        if not marker["passed"] and raise_on_failure:
            raise ConanException(
                "consumer test failed: rc=%s ok=%s/%s"
                % (proc.returncode, ok_count, CONSUMER_CHECK_COUNT)
            )
