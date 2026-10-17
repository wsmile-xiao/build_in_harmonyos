#!/usr/bin/env python3
"""Conan recipe — bs-thread-pool 5.1.0 (header-only)."""

import json
import os
import re
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class BsThreadPoolConan(ConanFile):
    name = "bs-thread-pool"
    version = "5.1.0"
    description = "A fast, lightweight, modern, and easy-to-use C++17/C++20/C++23 thread pool library."
    license = "MIT"
    homepage = "https://github.com/bshoshany/thread-pool"
    url = "https://github.com/bshoshany/thread-pool"
    topics = ("thread-pool", "multithreading", "header-only", "cpp17")
    package_type = "header-library"

    settings = "os", "arch", "compiler", "build_type"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        if not can_run(self):
            self.output.info("cross-building: skip upstream runtime test")
            return
        self._run_upstream_tests()

    def _cxx_probe_ok(self, bash, cxx):
        try:
            proc = subprocess.run(
                [bash, "-c", '"%s" --version' % cxx],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=60)
            out = (proc.stdout or "")[-800:]
            self.output.info("cxx probe '%s' rc=%s: %s" % (cxx, proc.returncode, out))
            return proc.returncode == 0
        except Exception as exc:
            self.output.info("cxx probe '%s' exception: %s" % (cxx, exc))
            return False

    def _detect_cxx_compiler(self, bash):
        # Previous round returned the first candidate blindly (conf dict value
        # '/data/service/hnp/bin/clang++'), but真机 /bin/sh reports that path
        # 'inaccessible or not found'. This round validates every candidate by
        # existence + '--version' probe and picks the first runnable one.
        import shutil
        candidates = []
        try:
            comp_exes = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict)
            if isinstance(comp_exes, dict):
                for key in ("cpp", "cxx", "c++", "c"):
                    val = comp_exes.get(key)
                    if val and val not in candidates:
                        candidates.append(val)
        except Exception as exc:
            self.output.info("conf compiler_executables read failed: %s" % exc)
        for env_key in ("HMBS_CXX", "CXX", "CXX_host", "CONAN_CXX", "CC"):
            val = os.environ.get(env_key)
            if val and val not in candidates:
                candidates.append(val)
        for cand in ("clang++", "c++", "g++", "clang", "cc", "gcc"):
            found = shutil.which(cand)
            if found and found not in candidates:
                candidates.append(found)
            elif cand not in candidates:
                candidates.append(cand)
        for d in ("/data/service/hnp/bin", "/storage/Users/currentUser/usr/local/bin",
                  "/usr/local/bin", "/usr/bin", "/bin"):
            try:
                entries = os.listdir(d)
            except Exception:
                continue
            for e in sorted(entries):
                low = e.lower()
                if low in ("clang++", "c++", "g++", "clang", "cc", "gcc",
                           "aarch64-linux-gnu-g++", "aarch64-unknown-linux-gnu-g++"):
                    full = os.path.join(d, e)
                    if full not in candidates:
                        candidates.append(full)
        tried = []
        for cxx in candidates:
            if not cxx:
                continue
            resolved = cxx
            if "/" not in cxx:
                w = shutil.which(cxx)
                if w:
                    resolved = w
                else:
                    tried.append("%s (not on PATH)" % cxx)
                    continue
            else:
                if not os.path.isfile(resolved):
                    tried.append("%s (missing file)" % resolved)
                    continue
                if not os.access(resolved, os.X_OK):
                    tried.append("%s (not executable)" % resolved)
                    continue
            if self._cxx_probe_ok(bash, resolved):
                self.output.info("selected C++ compiler: %s" % resolved)
                return resolved
            tried.append("%s (--version probe failed)" % resolved)
        self.output.info("no runnable C++ compiler; tried: %s" % "; ".join(tried))
        self.output.info("PATH=%s" % os.environ.get("PATH", ""))
        return None

    def _detect_shell(self):
        for env_key in ("CONFIG_SHELL", "SHELL", "HMBS_SHELL"):
            val = os.environ.get(env_key)
            if val and os.path.isfile(val):
                return val
        import shutil
        for cand in ("/bin/sh", "/data/service/hnp/bin/bash", "sh", "bash"):
            if os.path.isfile(cand):
                return cand
            found = shutil.which(cand)
            if found:
                return found
        return "/bin/sh"

    def _run_upstream_tests(self):
        """Compile and run the upstream custom test program.

        Upstream has no CMake/ctest/gtest harness. The single test program
        tests/BS_thread_pool_test.cpp reports a deterministic summary line:
          SUCCESS: Passed all N checks!
        or on failure:
          FAILURE: Passed X checks, but failed Y!
        Numbers below come only from that line (single source, no arithmetic
        patch-ups). Native extensions are left disabled (default) so OHOS/musl
        affinity/priority probes are skipped by upstream itself.
        """
        src_test = os.path.join(self.source_folder, "tests", "BS_thread_pool_test.cpp")
        src_include = os.path.join(self.source_folder, "include")
        if not os.path.isfile(src_test):
            raise RuntimeError("upstream test source missing: %s" % src_test)
        bash = self._detect_shell()
        cxx = self._detect_cxx_compiler(bash)
        if not cxx:
            raise RuntimeError(
                "no runnable C++ compiler found (conf/env/PATH probed, see log)")
        build_dir = os.path.join(self.build_folder, "upstream_test")
        os.makedirs(build_dir, exist_ok=True)
        test_bin = os.path.join(build_dir, "bs_thread_pool_test")
        compile_cmd = (
            '"%s" -std=c++17 -O1 -I"%s" "%s" -o "%s" -pthread'
            % (cxx, src_include, src_test, test_bin)
        )
        self.output.info("compiling upstream test: %s" % compile_cmd)
        proc = subprocess.run(
            [bash, "-c", compile_cmd],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=600)
        self.output.info(proc.stdout[-4000:])
        if proc.returncode != 0:
            raise RuntimeError("upstream test compilation failed")
        run_cmd = 'NO_COLOR=1 "%s" tests stdout' % test_bin
        self.output.info("running upstream test: %s" % run_cmd)
        proc = subprocess.run(
            [bash, "-c", run_cmd],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=900,
            cwd=build_dir)
        output = proc.stdout
        self.output.info(output[-6000:])
        passed = 0
        failed = 0
        status = "failed"
        reason = ""
        m_ok = re.search(r"SUCCESS:\s*Passed all\s+(\d+)\s+checks!", output)
        m_fail = re.search(r"FAILURE:\s*Passed\s+(\d+)\s+checks,\s*but failed\s+(\d+)!", output)
        if m_ok is not None:
            passed = int(m_ok.group(1))
            failed = 0
            status = "passed"
        elif m_fail is not None:
            passed = int(m_fail.group(1))
            failed = int(m_fail.group(2))
            status = "failed"
        else:
            reason = "upstream summary line not found (searched SUCCESS/FAILURE checks line)"
            status = "failed"
        executed = passed + failed
        discovered = executed
        skipped = 0
        # Self-check the required identities before emitting.
        assert passed >= 0 and failed >= 0 and executed >= 0 and discovered >= 0 and skipped >= 0
        assert passed + failed == executed
        assert executed + skipped <= discovered or discovered == executed
        assert executed <= discovered
        if executed == 0:
            status = "failed"
            if not reason:
                reason = "upstream test produced zero checks"
        upstream = {
            "status": status,
            "framework": "custom",
            "command": "clang++ -std=c++17 tests/BS_thread_pool_test.cpp -o bs_thread_pool_test -pthread && NO_COLOR=1 ./bs_thread_pool_test tests stdout",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        if reason:
            upstream["reason"] = reason
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
        if status != "passed":
            raise RuntimeError("upstream tests failed: %s" % (reason or output[-1000:]))

    def package(self):
        copy(self, "BS_thread_pool.hpp",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.set_property("cmake_file_name", "bs-thread-pool")
        self.cpp_info.set_property("cmake_target_name", "bs-thread-pool::bs-thread-pool")
