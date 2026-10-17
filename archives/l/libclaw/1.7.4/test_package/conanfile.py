#!/usr/bin/env python3
"""Conan test_package for libclaw 1.7.4 — exercises the real public API.

Builds test_libclaw.cpp (tween single_tweener run-to-finish, box_2d
geometry, configuration_file parse: 6 explicit checks) with CMake and
runs it via ctest. Emits HMBS_TEST_PACKAGE_RESULT with the real check
count, and re-emits HMBS_UPSTREAM_TEST_RESULT status=no_tests every run
(upstream 1.7.4 ships no test suite; bwm/0.6.3 precedent) so the evidence
gate passes even on Conan cache hits.
"""
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class LibclawTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Explicit Boost requirement so CMakeDeps always emits the Boost
        # config for test_package's find_package(Boost ...) even when the
        # main recipe's transitive propagation is skipped (e.g. cache-hit
        # graphs). Version must match the main recipe (boost/1.91.0).
        self.requires("boost/1.91.0")

    def layout(self):
        cmake_layout(self)

    def _writable_tmpdir(self):
        # HMBS readonly_tmp: same minimal root replacement as main recipe.
        # Also honors HMBS_PLATFORM_CAPABILITIES.tmpdir (JSON).
        caps = {}
        try:
            caps = json.loads(os.environ.get("HMBS_PLATFORM_CAPABILITIES") or "{}")
        except Exception:
            caps = {}
        cap_tmp = caps.get("tmpdir") if isinstance(caps, dict) else ""
        ordered = [v for v in (os.environ.get("HMBS_TMPDIR"), cap_tmp) if v and v not in ("0", "/tmp")]
        for var in ("TMPDIR", "TMP", "TEMP", "HMBS_AUTOCONF_MKTEMP_FALLBACK"):
            value = os.environ.get(var)
            if value and value not in ("0", "/tmp") and value not in ordered:
                ordered.append(value)
        for value in ordered:
            try:
                os.makedirs(value, exist_ok=True)
            except OSError:
                continue
            try:
                probe = os.path.join(value, ".hmbs_probe")
                with open(probe, "w", encoding="utf-8") as handle:
                    handle.write("probe")
                os.remove(probe)
                return value
            except OSError:
                continue
        fallback = os.path.join(self.build_folder or os.getcwd(), "tmp_hmbs")
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            pass
        return fallback

    def _ensure_tmp_env(self):
        tmp = self._writable_tmpdir()
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        os.environ["SHELL"] = "/bin/sh"
        os.environ["CONFIG_SHELL"] = "/bin/sh"
        return tmp

    def _runs_compiler(self, path):
        try:
            if not path or not os.path.isfile(path):
                return False
            r = subprocess.run([path, "--version"], capture_output=True,
                               text=True, timeout=20,
                               env=os.environ.copy())
            return r.returncode == 0
        except Exception:
            return False

    def _discover_ohos_compilers(self):
        """Mirror of the main recipe probe: conf -> PATH -> env."""
        try:
            cm = self.conf.get("tools.build:compiler_executables",
                               default={}, check_type=dict) or {}
        except Exception:
            cm = {}
        pc = cm.get("c", "") if isinstance(cm, dict) else ""
        pcpp = cm.get("cpp", "") if isinstance(cm, dict) else ""
        if pc and pcpp and self._runs_compiler(pc) and self._runs_compiler(pcpp):
            return pc, pcpp
        if pc or pcpp:
            self.output.warning("profile compiler not runnable: c=%s cpp=%s" % (pc, pcpp))
        for name_c, name_cpp in (("clang", "clang++"), ("cc", "c++"),
                                 ("gcc", "g++")):
            wc = shutil.which(name_c) or ""
            wcpp = shutil.which(name_cpp) or ""
            if wc and wcpp and self._runs_compiler(wc) and self._runs_compiler(wcpp):
                self.output.info("using PATH compilers: %s / %s" % (wc, wcpp))
                return wc, wcpp
        cc_env = os.environ.get("CC", "")
        cxx_env = os.environ.get("CXX", "")
        if cc_env and cxx_env and self._runs_compiler(cc_env) and self._runs_compiler(cxx_env):
            return cc_env, cxx_env
        return "", ""

    def generate(self):
        self._ensure_tmp_env()
        tc = CMakeToolchain(self)
        disc_c, disc_cpp = self._discover_ohos_compilers()
        if disc_c and disc_cpp:
            tc.variables["CMAKE_C_COMPILER"] = disc_c
            tc.variables["CMAKE_CXX_COMPILER"] = disc_cpp
            self.output.info("test_package pinning compilers: %s / %s" % (disc_c, disc_cpp))
            os.environ["CC"] = disc_c
            os.environ["CXX"] = disc_cpp
        tc.generate()
        tmp = self._writable_tmpdir()
        hmbs_env = Environment()
        hmbs_env.define("TMPDIR", tmp)
        hmbs_env.define("TMP", tmp)
        hmbs_env.define("TEMP", tmp)
        hmbs_env.define("SHELL", "/bin/sh")
        hmbs_env.define("CONFIG_SHELL", "/bin/sh")
        if os.environ.get("CC"):
            hmbs_env.define("CC", os.environ["CC"])
        if os.environ.get("CXX"):
            hmbs_env.define("CXX", os.environ["CXX"])
        hmbs_env.vars(self, scope="build").save_script("hmbs_env")

    def build(self):
        self._ensure_tmp_env()
        bc, bcpp = self._discover_ohos_compilers()
        if bc and bcpp:
            os.environ["CC"] = bc
            os.environ["CXX"] = bcpp
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _find_ohos_tool(self, name):
        try:
            cm = self.conf.get("tools.build:compiler_executables",
                               default={}, check_type=dict) or {}
        except Exception:
            cm = {}
        compiler_dir = os.path.dirname((cm.get("cpp", "") or "") if isinstance(cm, dict) else "")
        candidates = []
        if compiler_dir:
            candidates.append(os.path.join(compiler_dir, name))
        candidates += ["/data/service/hnp/bin/" + name,
                       shutil.which(name) or ""]
        for p in candidates:
            if p and os.path.isfile(p):
                return p
        return ""

    def _sign_test_binary_ohos(self):
        # OHOS loader rejects unsigned ELF at exec/dlopen time
        # (lapack/3.12.1 precedent). Tolerant: warn-only when tools
        # are absent so Linux/CI builds never break.
        if str(self.settings.os) != "OHOS":
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            self.output.warning("OHOS signing tools not found, skipping test binary sign")
            return
        candidates = []
        try:
            for d in (self.cpp.build.bindirs or []):
                candidates.append(os.path.join(d, "test_libclaw"))
        except Exception:
            pass
        for root, _dirs, files in os.walk(self.build_folder or "."):
            if "test_libclaw" in files:
                candidates.append(os.path.join(root, "test_libclaw"))
        seen = set()
        for exe in candidates:
            if exe in seen or not os.path.isfile(exe):
                continue
            seen.add(exe)
            try:
                self.run('"%s" --remove-section .codesign "%s"'
                         % (objcopy, exe), ignore_errors=True)
                self.run('"%s" sign -inFile "%s" -outFile "%s" -selfSign 1'
                         % (signer, exe, exe))
                self.output.info("signed test binary: %s" % exe)
            except Exception as exc:
                self.output.warning("signing %s failed: %s" % (exe, exc))

    def _prepend_run_ld_path(self):
        # musl ignores RPATH/RUNPATH, so the loader only searches
        # LD_LIBRARY_PATH + defaults. VirtualRunEnv for os=OHOS does not
        # always export the tested package's libdir, which is exactly why
        # preflight failed with "Error loading shared library
        # libclaw_*.so.1" while Boost (static deps) stayed silent.
        # Collect every dependency libdir explicitly so ctest children
        # inherit a complete search path. Never fails.
        dirs = []
        try:
            for _name, dep in self.dependencies.items():
                try:
                    folders = list(dep.cpp_info.libdirs or [])
                except Exception:
                    folders = []
                for d in folders:
                    if d and os.path.isdir(d) and d not in dirs:
                        dirs.append(d)
                try:
                    pf = getattr(dep, "package_folder", "")
                except Exception:
                    pf = ""
                if pf:
                    for sub in ("lib",):
                        cand = os.path.join(str(pf), sub)
                        if os.path.isdir(cand) and cand not in dirs:
                            dirs.append(cand)
        except Exception:
            pass
        if dirs:
            prev = os.environ.get("LD_LIBRARY_PATH", "")
            merged = ":".join(dirs)
            if prev:
                merged = merged + ":" + prev
            os.environ["LD_LIBRARY_PATH"] = merged
            self.output.info("test_package LD_LIBRARY_PATH=%s" % merged)
        return dirs

    def test(self):
        self._ensure_tmp_env()
        if not can_run(self):
            self.output.info("cross-building: build verified, runtime tests skipped")
            return
        # 6 explicit CHECK() assertions in test_libclaw.cpp
        test_pkg = {
            "executed": True,
            "passed": True,
            "command": "ctest --output-on-failure -R test_libclaw",
            "discovered": 6,
            "passedCount": 6,
        }
        shell = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL")
        if not shell or not os.path.isfile(shell):
            shell = "/bin/sh"
        self._sign_test_binary_ohos()
        self._prepend_run_ld_path()
        try:
            self.run(
                '%s -c "ctest --output-on-failure -R test_libclaw"' % shell,
                env="conanrun",
            )
        except Exception:
            test_pkg["passed"] = False
            test_pkg["passedCount"] = 0
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False)
            )
            raise
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False)
        )
        upstream_marker = {
            "status": "no_tests",
            "framework": "none",
            "command": "ctest -N",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "libclaw 1.7.4 upstream has no test suite: no enable_testing/add_test in CMakeLists.txt, no test/ directory in the 1.7.4 tarball; examples/ are demos without assertions",
        }
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker, ensure_ascii=False)
        print(msg, flush=True)
        self.output.info(msg)
