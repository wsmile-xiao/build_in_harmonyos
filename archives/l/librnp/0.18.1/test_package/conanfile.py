#!/usr/bin/env python3
"""Conan test_package for librnp — Conan L1 official test.

Links the packaged librnp and exercises its real C API (version, backend,
feature query, ffi create/destroy). Parses the binary output for assertion
counts and emits HMBS evidence markers; re-emits the upstream ctest evidence
persisted by the main recipe.
"""
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class LibrnpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        # E346: test_package re-runs CMake compiler checks in its own
        # context; use Ninja on OHOS so they don't go through /bin/sh.
        if self.settings.os == "OHOS":
            tc = CMakeToolchain(self, generator="Ninja")
        else:
            tc = CMakeToolchain(self)
        ninja_bin = None
        try:
            ninja_bin = self.conf.get("user.hmbs:ninja_path", check_type=str)
        except Exception:
            ninja_bin = None
        ninja_bin = ninja_bin or os.environ.get("HMBS_NINJA")
        if ninja_bin:
            tc.cache_variables["CMAKE_MAKE_PROGRAM"] = ninja_bin
        # Same cycle-5 probe-environment hardening as the main recipe:
        # this context runs its own project() compiler check, so it needs
        # the verified-writable tmp chain and the E266 lld runtime in its
        # conanbuild environment too. The reachable compiler is patched
        # into the generated toolchain AFTER tc.generate() (cycle-4 proved
        # -D overrides are stomped by the toolchain file). No cflags
        # clearing (cycle-3 hypothesis disproven; keep Conan's target flags).
        good_c = ""
        good_cxx = ""
        if self.settings.os == "OHOS":
            tmp_base = self._ensure_writable_tmpdir()
            test_env = Environment()
            for _var in ("TMPDIR", "TMP", "TEMP"):
                test_env.define(_var, tmp_base)
            llvm_lib = self._ohos_sdk_llvm_lib()
            if llvm_lib:
                test_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            good_c = self._reachable_compiler("c", "clang")
            good_cxx = self._reachable_compiler("cpp", "clang++")
            if good_c:
                test_env.define("CC", good_c)
            if good_cxx:
                test_env.define("CXX", good_cxx)
            test_env.vars(self, scope="build").save_script("librnp_test_ohos_env")
        # Same OHOS cross fix as the main recipe (json-c 0.18 pattern):
        # force a known CMake system so this test project passes its own
        # compiler check on device.
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            tc.cache_variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()
        if self.settings.os == "OHOS":
            self._patch_ohos_toolchain_compilers(good_c, good_cxx)

    # -- OHOS probe-environment helpers (mirror of the main recipe) ----
    def _writable_tmpdir(self):
        import tempfile
        candidates = [
            os.environ.get("TMPDIR"),
            os.environ.get("TMP"),
            os.environ.get("TEMP"),
            os.path.join(self.build_folder, "tmp"),
        ]
        try:
            candidates.append(os.path.join(os.path.expanduser("~"), "tmp"))
        except Exception:
            pass
        for cand in candidates:
            if not cand:
                continue
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs_write_probe")
                with open(probe, "w", encoding="utf-8") as probe_file:
                    probe_file.write("ok")
                try:
                    os.remove(probe)
                except OSError:
                    pass
                try:
                    tempfile.tempdir = cand
                except Exception:
                    pass
                return cand
            except OSError:
                continue
        fallback = os.path.join(self.build_folder, "tmp")
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            pass
        return fallback

    def _ensure_writable_tmpdir(self):
        tmp_base = self._writable_tmpdir()
        for var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[var] = tmp_base
        return tmp_base

    def _reachable_compiler(self, kind, bare):
        import shutil
        cands = []
        try:
            comp_exes = self.conf.get(
                "tools.build:compiler_executables", default=None)
            if isinstance(comp_exes, dict) and comp_exes.get(kind):
                cands.append(comp_exes.get(kind))
        except Exception:
            pass
        try:
            which = shutil.which(bare)
            if which:
                cands.append(which)
                try:
                    cands.append(os.path.realpath(which))
                except Exception:
                    pass
        except Exception:
            pass
        for cand in dict.fromkeys(c for c in cands if c):
            try:
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    if cands and cand != cands[0]:
                        self.output.warning(
                            "OHOS compiler: conf {}={!r} unreachable, "
                            "using {!r}".format(kind, cands[0], cand))
                    return cand
            except OSError:
                continue
        self.output.warning(
            "OHOS compiler: no reachable compiler for {} (tried {})".format(
                kind, cands))
        return ""

    def _patch_ohos_toolchain_compilers(self, good_c, good_cxx):
        if str(self.settings.os) != "OHOS":
            return
        gen_dir = self.generators_folder or ""
        if not gen_dir or not os.path.isdir(gen_dir):
            gen_dir = os.path.join(
                self.build_folder, "build", "Release", "generators")
        tc_path = os.path.join(gen_dir, "conan_toolchain.cmake")
        try:
            with open(tc_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError as e:
            self.output.warning(
                "ohos-toolchain-patch: cannot read {}: {}".format(tc_path, e))
            return
        total = 0
        for bad, good in (("/data/service/hnp/bin/clang++", good_cxx),
                          ("/data/service/hnp/bin/clang", good_c)):
            if not good or good == bad or bad not in text:
                continue
            try:
                bad_ok = os.path.isfile(bad) and os.access(bad, os.X_OK)
            except OSError:
                bad_ok = False
            if bad_ok:
                continue
            total += text.count(bad)
            self.output.warning(
                "ohos-toolchain-patch: replacing {}x {!r} -> {!r}".format(
                    text.count(bad), bad, good))
            text = text.replace(bad, good)
        if total:
            try:
                with open(tc_path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(text)
            except OSError as e:
                self.output.warning(
                    "ohos-toolchain-patch: cannot write {}: {}".format(
                        tc_path, e))
                return
            self.output.warning(
                "ohos-toolchain-patch: patched {} occurrence(s) in {}".format(
                    total, tc_path))
        else:
            self.output.info("ohos-toolchain-patch: nothing to patch")

    @staticmethod
    def _ohos_sdk_llvm_lib():
        import glob
        candidates = []
        try:
            import shutil
            for tool in (shutil.which("clang") or "",
                         "/data/service/hnp/bin/clang"):
                if tool and os.path.isfile(tool):
                    real = os.path.realpath(tool)
                    llvm_root = os.path.dirname(os.path.dirname(real))
                    candidates.append(os.path.join(llvm_root, "lib"))
                    node = os.path.dirname(real)
                    for _ in range(4):
                        node = os.path.dirname(node)
                        if node in ("", os.path.sep):
                            break
                        candidates.append(os.path.join(node, "llvm", "lib"))
                        candidates.append(os.path.join(
                            node, "ohos", "native", "llvm", "lib"))
        except Exception:
            pass
        candidates += [
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib",
        ]
        sdk_base = os.environ.get(
            "OHOS_SDK_HOME", "/data/service/hnp/ohos-sdk.org")
        try:
            candidates += sorted(glob.glob(
                os.path.join(sdk_base, "*", "ohos", "native", "llvm", "lib")))
        except Exception:
            pass
        for candidate in dict.fromkeys(candidates):
            if candidate and os.path.isdir(candidate):
                return candidate
        return ""

    def build(self):
        # Same writable-tmp + lld handling as the main recipe;
        # test_package is an independent Conan context.
        if self.settings.os == "OHOS":
            self._ensure_writable_tmpdir()
            llvm_lib = self._ohos_sdk_llvm_lib()
            if llvm_lib:
                current = os.environ.get("LD_LIBRARY_PATH", "")
                entries = ([p for p in current.split(os.pathsep) if p]
                           if current else [])
                if llvm_lib not in entries:
                    os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
                        [llvm_lib] + entries)
        else:
            tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                      or os.environ.get("TEMP"))
            if not tmpdir or tmpdir == "/tmp" or not os.path.isdir(tmpdir):
                tmpdir = os.path.join(self.build_folder, "tmp")
            os.makedirs(tmpdir, exist_ok=True)
            for _var in ("TMPDIR", "TMP", "TEMP"):
                os.environ[_var] = tmpdir
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmd = os.path.join(self.cpp.build.bindirs[0], "test_librnp")
        log_path = os.path.join(self.build_folder, "test_librnp.log")
        rc_out = None
        try:
            rc_out = self.run('"{0}" > "{1}" 2>&1'.format(cmd, log_path),
                              env="conanrun", stdout=True)
        except ConanException:
            pass
        out = ""
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                out = f.read()
        except OSError:
            out = ""
        out = out or (rc_out or "")
        self.output.info("test_librnp output:\n" + out)

        m = re.search(r"LIBRNP_TEST_RESULT\s+passed=(\d+)\s+total=(\d+)", out)
        if not m:
            raise ConanException("test_librnp produced no LIBRNP_TEST_RESULT line")
        passed_count = int(m.group(1))
        discovered = int(m.group(2))
        ok = discovered > 0 and passed_count == discovered and "FAIL" not in out

        marker = {
            "executed": True,
            "passed": ok,
            "command": "./test_librnp",
            "discovered": discovered,
            "passedCount": passed_count,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
        if not ok:
            raise ConanException(
                "test_package failed: {}/{} assertions passed".format(passed_count, discovered))

        dep = self.dependencies["librnp"]
        for path in (os.path.join(dep.package_folder, "res", "upstream_test_result.json"),
                     os.path.join(dep.package_folder, "upstream_test_result.json")):
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as f:
                    result = json.load(f)
                self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))
                return
        raise ConanException("upstream_test_result.json not found in package")
