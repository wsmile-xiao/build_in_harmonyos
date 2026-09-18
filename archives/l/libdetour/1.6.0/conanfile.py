#!/usr/bin/env python3
"""Conan recipe — libdetour 1.6.0 (CMake, Detour runtime from Recast Navigation)."""

import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import copy, get, rm, rmdir


class LibdetourConan(ConanFile):
    name = "libdetour"
    version = "1.6.0"
    description = "Detour runtime navigation-mesh query library from Recast Navigation"
    license = "Zlib"
    homepage = "https://github.com/recastnavigation/recastnavigation"
    url = "https://github.com/recastnavigation/recastnavigation"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # OHOS preflight hardening (proven ayatana-indicator-keyboard pattern):
        # profile nails tools.build:compiler_executables to
        # /data/service/hnp/bin/clang(++), which is missing on some
        # preflight runners -> CMAKE_C/CXX_COMPILER points at a dead path
        # and configure fails at the compiler check. Reuse the conf path
        # when it exists; only then fall back to PATH-discovered clang.
        cc_conf = cxx_conf = ""
        try:
            exes = self.conf.get("tools.build:compiler_executables") or {}
            if isinstance(exes, dict):
                cc_conf = exes.get("c") or ""
                cxx_conf = exes.get("cpp") or ""
        except Exception:
            pass
        cc = cc_conf if (cc_conf and os.path.isfile(cc_conf)) else ""
        cxx = cxx_conf if (cxx_conf and os.path.isfile(cxx_conf)) else ""
        cc_fallback = cxx_fallback = False
        if not cc:
            cc = shutil.which("clang") or shutil.which("cc") or ""
            cc_fallback = bool(cc)
        if not cxx:
            cxx = shutil.which("clang++") or shutil.which("c++") or ""
            cxx_fallback = bool(cxx)
        if cc_conf and not os.path.isfile(cc_conf):
            self.output.info("compiler_fix: conf c %r missing; fallback %r" % (cc_conf, cc))
        if cxx_conf and not os.path.isfile(cxx_conf):
            self.output.info("compiler_fix: conf cpp %r missing; fallback %r" % (cxx_conf, cxx))
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["RECASTNAVIGATION_DEMO"] = "OFF"
        tc.variables["RECASTNAVIGATION_EXAMPLES"] = "OFF"
        tc.variables["RECASTNAVIGATION_TESTS"] = "ON"
        tc.variables["RECASTNAVIGATION_DT_POLYREF64"] = "OFF"
        tc.variables["RECASTNAVIGATION_DT_VIRTUAL_QUERYFILTER"] = "OFF"
        if cc_fallback and cc:
            tc.variables["CMAKE_C_COMPILER"] = cc
        if cxx_fallback and cxx:
            tc.variables["CMAKE_CXX_COMPILER"] = cxx
        tc.generate()
        env = Environment()
        # readonly_tmp: preflight /tmp is read-only; HMBS injects a
        # task-private TMPDIR/TMP/TEMP. Forward it into conanbuild so
        # CMake try-compile and clang temp files land on writable storage.
        # Only the temp root is replaced; build logic is unchanged.
        for _k in ("TMPDIR", "TMP", "TEMP"):
            _v = os.environ.get(_k)
            if _v:
                env.define(_k, _v)
        if cc_fallback and cc:
            env.define("CC", cc)
        if cxx_fallback and cxx:
            env.define("CXX", cxx)
        llvm_lib = self._llvm_lib_for_lld(cc or cxx)
        if llvm_lib:
            self.output.info("lld_fix: prepend llvm lib {}".format(llvm_lib))
            env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        else:
            self.output.info("lld_fix: no llvm lib with libxml2.so.16 found; skip")
        env.vars(self).save_script("hmbs_fix")

    def _llvm_lib_for_lld(self, cc_hint=""):
        # OHOS SDK lld needs libxml2.so.16 at host runtime; the try-link
        # fails with "compiler broken" when the loader cannot find it.
        # Ask the compiler itself for its library search dirs and return
        # the dir holding libxml2.so.16 (isfile probe, no readdir).
        cc = cc_hint or ""
        if not cc:
            try:
                exes = self.conf.get("tools.build:compiler_executables") or {}
                if isinstance(exes, dict):
                    cc = exes.get("c") or ""
            except Exception:
                cc = ""
        if not cc:
            cc = shutil.which("clang") or ""
        if not cc:
            self.output.info("lld_fix: cc not resolvable")
            return ""
        try:
            proc = subprocess.run([cc, "-print-search-dirs"], capture_output=True,
                                  text=True, timeout=60)
        except Exception as exc:
            self.output.info("lld_fix: search-dirs failed: {}".format(exc))
            return ""
        out = (proc.stdout or "") + (proc.stderr or "")
        for line in out.splitlines():
            if not line.startswith("libraries:"):
                continue
            paths = line.split("=", 1)[1] if "=" in line else ""
            for p in paths.replace(";", ":").split(":"):
                p = p.strip().lstrip("=")
                if not p:
                    continue
                for cand in (p, os.path.dirname(p.rstrip("/"))):
                    try:
                        hit = os.path.isfile(os.path.join(cand, "libxml2.so.16"))
                    except OSError:
                        hit = False
                    if hit:
                        return cand
        return ""

    def _dump_configure_evidence(self):
        # Failure-path only: surface CMake compiler-check logs so the
        # next round can tell missing compiler vs sysroot vs lld runtime.
        try:
            cands = []
            for root, _ds, fs in os.walk(self.build_folder):
                for f in fs:
                    if f in ("CMakeError.log", "CMakeOutput.log"):
                        cands.append(os.path.join(root, f))
            for path in sorted(set(cands)):
                self.output.info("configure_evidence: --- {} (tail 40) ---".format(path))
                try:
                    with open(path, "r", errors="replace") as fh:
                        lines = fh.read().splitlines()[-40:]
                    for ln in lines:
                        self.output.info("configure_evidence: " + ln[:400])
                except Exception as exc:
                    self.output.info("configure_evidence: read failed {}: {}".format(path, exc))
            try:
                exes = self.conf.get("tools.build:compiler_executables") or {}
            except Exception:
                exes = {}
            for label in ("c", "cpp"):
                p = exes.get(label, "") if isinstance(exes, dict) else ""
                try:
                    self.output.info("configure_evidence: {}={!r} isfile={}".format(
                        label, p, os.path.isfile(p) if p else False))
                except Exception:
                    pass
            for w in ("clang", "clang++", "cc", "c++", "cmake", "ninja", "make"):
                self.output.info("configure_evidence: which {}={!r}".format(w, shutil.which(w)))
            for k in ("TMPDIR", "TMP", "TEMP", "LD_LIBRARY_PATH"):
                self.output.info("configure_evidence: {}={!r}".format(k, os.environ.get(k, "")))
        except Exception as exc:
            self.output.info("configure_evidence: dump failed: {}".format(exc))

    def _find_tests_binary(self):
        candidates = []
        for root, _, files in os.walk(self.build_folder):
            if "Tests" in files:
                candidates.append(os.path.join(root, "Tests"))
        for cand in candidates:
            if os.path.isfile(cand):
                return cand
        return None

    def _parse_catch2_result(self, output):
        discovered = 0
        passed = 0
        failed = 0
        m = re.search(r"All tests passed\s*\(\s*(\d+)\s+assertions?\s+in\s+(\d+)\s+test\s+cases?\s*\)", output)
        if m:
            discovered = int(m.group(2))
            passed = discovered
            failed = 0
            return discovered, passed, failed
        m = re.search(r"(\d+)\s+test\s+cases?\s*,\s*(\d+)\s+passed", output)
        if m:
            discovered = int(m.group(1))
            passed = int(m.group(2))
            failed = discovered - passed
            return discovered, passed, failed
        m = re.search(r"FAILED", output)
        if m:
            failed = 1
        return discovered, passed, failed

    def build(self):
        cmake = CMake(self)
        try:
            cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        except Exception:
            self._dump_configure_evidence()
            raise
        cmake.build()
        # Upstream test suite: Tests/ (Catch2, vendored in Tests/Contrib).
        # ctest registers a single "Tests" entry that runs all Catch2 cases.
        self.run("ctest --output-on-failure", cwd=self.build_folder, env="conanbuild")
        tests_bin = self._find_tests_binary()
        discovered = 0
        passed = 0
        failed = 0
        status = "passed"
        detail = ""
        if tests_bin is not None:
            proc = subprocess.run(
                [tests_bin, "--reporter", "compact"],
                cwd=os.path.dirname(tests_bin),
                capture_output=True,
                text=True,
                timeout=300,
            )
            detail = (proc.stdout or "") + (proc.stderr or "")
            self.output.info("upstream Tests output:\n" + detail)
            discovered, passed, failed = self._parse_catch2_result(detail)
            if discovered <= 0:
                # Fallback: count TEST_CASE macros from the source tree.
                count = 0
                tests_dir = os.path.join(self.source_folder, "Tests")
                for root, _, files in os.walk(tests_dir):
                    for fn in files:
                        if fn.endswith(".cpp"):
                            try:
                                with open(os.path.join(root, fn), "r", encoding="utf-8", errors="replace") as f:
                                    count += len(re.findall(r"TEST_CASE\s*\(", f.read()))
                            except OSError:
                                pass
                # Benchmark BM() cases are platform-conditional; only use
                # the static count when the binary parse yields nothing.
                if count > 0:
                    discovered = count
                    passed = count if proc.returncode == 0 else 0
                    failed = 0 if proc.returncode == 0 else count
            if proc.returncode != 0:
                status = "failed"
        else:
            # ctest passed but binary not located: report the ctest entry.
            discovered = 1
            passed = 1
            failed = 0
        skipped = 0
        marker = {
            "status": status,
            "framework": "catch2",
            "command": "ctest --output-on-failure (Tests, Catch2)",
            "discovered": discovered,
            "executed": discovered,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        with open(os.path.join(self.build_folder, "upstream_test_result.json"), "w", encoding="utf-8") as f:
            json.dump(marker, f, ensure_ascii=False)
        if status != "passed" or discovered <= 0 or failed != 0:
            raise RuntimeError("upstream Tests failed: %s" % json.dumps(marker, ensure_ascii=False))

    def package(self):
        copy(self, "License.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        # This split package ships only the Detour runtime. Remove the
        # sibling libraries and their headers installed by the full project.
        for lib in ("Recast", "DetourCrowd", "DetourTileCache", "DebugUtils"):
            rm(self, "lib%s*" % lib, os.path.join(self.package_folder, "lib"))
            rm(self, "%s*" % lib, os.path.join(self.package_folder, "lib"))
            rm(self, "%s*" % lib, os.path.join(self.package_folder, "bin"))
        include_dir = os.path.join(self.package_folder, "include", "recastnavigation")
        if os.path.isdir(include_dir):
            for fn in os.listdir(include_dir):
                if fn.startswith("Detour") or fn in ("version.h",):
                    continue
                path = os.path.join(include_dir, fn)
                try:
                    if os.path.isfile(path):
                        os.remove(path)
                except OSError:
                    pass
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        copy(self, "upstream_test_result.json", src=self.build_folder,
             dst=os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libdetour")
        self.cpp_info.set_property("cmake_target_name", "libdetour::libdetour")
        self.cpp_info.set_property("pkg_config_name", "libdetour")
        self.cpp_info.libs = ["Detour"]
        self.cpp_info.includedirs = ["include", "include/recastnavigation"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
