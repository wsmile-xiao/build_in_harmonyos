#!/usr/bin/env python3
"""Conan test_package — cyrus-sasl-gs2 2.1.28 consumer test.

Builds test_gs2.c against the packaged libsasl2 (CMakeDeps +
CMakeToolchain), runs it on the native OHOS target and counts the
per-check "CHECK-OK:" lines for the HMBS_TEST_PACKAGE_RESULT
machine-evidence marker (exit-0-alone is not proof: 6 CHECK-OK lines
are required for a pass). GS2 ships as a shared plugin module
(plugins/libgs2.so); the plugin dir is baked into the binary via
SASL_PLUGIN_DIR (pinned with sasl_set_path) and also exported through
SASL_PATH for every direct binary run, so discovery never depends on
the library's relocated baked-in default path.

Upstream evidence: cyrus-sasl 2.1.28 ships no automated test harness
(BLFS: "This package does not come with a test suite"; audit in
MANIFEST.yml), so this re-emits HMBS_UPSTREAM_TEST_RESULT with
status=no_tests on every run (cache-hit rounds skip the main build,
the gate still needs the marker).
"""

import json
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake
from conan.tools.cmake import cmake_layout

# test_gs2.c performs exactly 6 checks, each printing one
# "CHECK-OK: <name>" line on success.
CONSUMER_CHECK_COUNT = 6


class Cyrussaslgs2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _ensure_writable_tmp(self):
        # HMBS injects a task-private writable TMPDIR on the real
        # machine (/tmp is read-only: [readonly_tmp]). Prefer it in
        # every phase; fall back to a dir under build_folder so neither
        # CMake/ctest nor the test binary ever touches /tmp.
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
        # Keep CMake temp files off a possibly read-only /tmp.
        self._ensure_writable_tmp()
        cmake = CMake(self)
        plugin_dir = self._plugin_dir_for_ohos()
        variables = {}
        if plugin_dir:
            variables["SASL_PLUGIN_DIR"] = plugin_dir
        cmake.configure(variables=variables)
        cmake.build()

    def _tested_package_folder(self):
        try:
            return str(
                self.dependencies[self.tested_reference_str].package_folder)
        except Exception:
            pass
        try:
            return str(self.dependencies["cyrus-sasl-gs2"].package_folder)
        except Exception:
            return ""

    def _plugin_dir_for_ohos(self):
        pkg = self._tested_package_folder()
        if not pkg:
            return ""
        plugdir = os.path.join(pkg, "lib", "sasl2")
        if os.path.isdir(plugdir):
            return plugdir
        return ""

    def _emit_upstream_marker(self):
        upstream_marker = {
            "status": "no_tests",
            "framework": "autotools-make-check",
            "command": "make check (upstream provides no automated suite)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "cyrus-sasl 2.1.28 ships no automated test harness: "
                "no TEST/TEST_F, no ctest/meson/pytest wiring, no automake "
                "TESTS/check_PROGRAMS and no make check target "
                "(utils/testsuite and sample/ are manual interactive "
                "programs, BLFS confirms no test suite); "
                "see test_package/MANIFEST.yml upstream_test_audit"
            ),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(upstream_marker, ensure_ascii=False)
        )

    def _dump_last_test_log(self):
        # ctest writes per-test output to Testing/Temporary/LastTest.log
        # under the build dir; surface it so the next preflight round can
        # see the real test_gs2 failure without guessing.
        try:
            candidates = []
            build_folder = getattr(self, "build_folder", "") or ""
            if build_folder and os.path.isdir(build_folder):
                for root, dirs, files in os.walk(build_folder):
                    if "LastTest.log" in files:
                        candidates.append(os.path.join(root, "LastTest.log"))
                    # Keep the walk shallow: build trees are deep.
                    if root.count(os.sep) - build_folder.count(os.sep) > 6:
                        dirs[:] = []
            for log_path in sorted(candidates)[:2]:
                try:
                    with open(log_path, "r", encoding="utf-8",
                              errors="replace") as handle:
                        content = handle.read()
                except OSError:
                    continue
                self.output.info("LastTest.log (%s) tail:" % log_path)
                self.output.info(content[-4000:])
        except Exception:
            pass

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile/link test completed")
            return
        tmp = self._ensure_writable_tmp()
        self._log_package_libs_for_ohos()
        cmake = CMake(self)
        try:
            # test_gs2 links krb5 shared libs (libgssapi_krb5 et al. need
            # libgssrpc/kadm5/kdb5/krad/krb5support/verto at runtime).
            # ctest must run under the conanrun env, otherwise the OHOS
            # loader reports "Error loading shared library ..." plus
            # "symbol not found" for every gss_* reloc.
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
            # Do not lose the evidence: dump the real ctest output and
            # still emit both machine markers (passed:false) so HMBS can
            # judge instead of marking the round incomplete.
            self.output.warning("ctest failed: %s" % exc)
            self._dump_last_test_log()
            self._run_consumer_binary(raise_on_failure=False)
            self._emit_upstream_marker()
            raise
        self._run_consumer_binary(raise_on_failure=True)
        # L0d quality gate: prove the binary also executes under the
        # conanrun environment (uses the same writable TMPDIR).
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_gs2")
        self.run(bin_path, env="conanrun")
        self._emit_upstream_marker()
        self.output.info("cyrus-sasl-gs2 consumer test_package passed")

    def _log_package_libs_for_ohos(self):
        # Diagnose static-vs-shared mixups and missing plugin modules:
        # the package must ship libsasl2 plus lib/sasl2/libgs2.so (the
        # GS2 mechanism). Log both so the next preflight shows whether
        # a missing plugin caused a GS2 check failure.
        try:
            pkg = self.dependencies[self.tested_reference_str].package_folder
        except Exception:
            try:
                pkg = self.dependencies["cyrus-sasl-gs2"].package_folder
            except Exception:
                return
        libdir = os.path.join(str(pkg), "lib")
        try:
            names = sorted(os.listdir(libdir))
        except OSError as exc:
            self.output.info("package libdir missing %s: %s" % (libdir, exc))
            return
        self.output.info("package libdir %s: %s" % (libdir, ", ".join(names)))
        plugdir = os.path.join(str(pkg), "lib", "sasl2")
        try:
            plugnames = sorted(os.listdir(plugdir))
        except OSError as exc:
            self.output.info(
                "package plugindir missing %s: %s" % (plugdir, exc))
            return
        self.output.info(
            "package plugindir %s: %s" % (plugdir, ", ".join(plugnames)))

    def _run_env_with_dep_libs(self):
        # Subprocess run for CHECK-OK counting must see the same runtime
        # search path as `self.run(..., env="conanrun")`: prepend every
        # direct/transitive dependency libdir to LD_LIBRARY_PATH so the
        # krb5 closure resolves without relying on the shell hook, and
        # export SASL_PATH so the shared GS2 plugin module is found even
        # outside the conanrun environment.
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
                    if cand and os.path.isdir(cand) \
                            and cand not in libdirs:
                        libdirs.append(cand)
                except Exception:
                    pass
        if libdirs:
            old = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                libdirs + ([old] if old else []))
        plugin_dir = self._plugin_dir_for_ohos()
        if plugin_dir and not env.get("SASL_PATH"):
            env["SASL_PATH"] = plugin_dir
        return env

    def _run_consumer_binary(self, raise_on_failure):
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_gs2")
        if not os.path.isfile(bin_path):
            raise ConanException("test binary missing: %s" % bin_path)
        proc = subprocess.run(
            [bin_path],
            env=self._run_env_with_dep_libs(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
        )
        output = proc.stdout or ""
        self.output.info(output[-2000:])
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
