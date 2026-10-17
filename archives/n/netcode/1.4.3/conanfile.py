#!/usr/bin/env python3
"""Conan recipe -- netcode 1.4.3 (CMake).

netcode is a secure client/server protocol for multiplayer games built on
top of UDP. It uses the vendored libsodium subset (NETCODE_SYSTEM_SODIUM=OFF),
so there are no external Conan dependencies.

Upstream test suite: a single ctest entry (netcode_test) that runs 46
RUN_TEST cases inside netcode.c netcode_test() (crypto vectors, packet
codecs, encryption manager, replay protection, client/server connect and
error paths over real UDP sockets).
"""
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class NetcodeConan(ConanFile):
    name = "netcode"
    version = "1.4.3"
    description = "Secure client/server protocol for multiplayer games on top of UDP"
    license = "BSD-3-Clause"
    homepage = "https://github.com/mas-bandwidth/netcode"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("networking", "udp", "game", "netcode")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        self._ensure_writable_tmp()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        # Build the upstream test runner and examples so build() can run ctest.
        tc.variables["NETCODE_BUILD_TESTS"] = True
        # Use the vendored libsodium subset: no external dependency to publish.
        tc.variables["NETCODE_SYSTEM_SODIUM"] = False
        # Profile hardcodes /data/service/hnp/bin/clang; that path is missing
        # on some preflight workers -> cmake configure "compiler not found".
        # Only the conf value is honoured when the file exists and is
        # executable, otherwise fall back to PATH clang (HMBS prepends tool
        # dirs to buildenv PATH). Harmless on healthy workers/CI.
        tc.variables["CMAKE_C_COMPILER"] = self._resolve_compiler("c", ("clang", "cc"))
        tc.variables["CMAKE_CXX_COMPILER"] = self._resolve_compiler("cpp", ("clang++", "c++"))
        tc.generate()

    def _resolve_compiler(self, key, fallbacks):
        """Return a working compiler for CMakeToolchain.

        Prefers tools.build:compiler_executables when it points at an
        existing executable; otherwise falls back to shutil.which() over
        HMBS-prepended PATH. Never raises: returns the raw conf value (or
        the first fallback name) so CMake can still report the real error.
        """
        try:
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict) or {}
        except Exception:
            executables = {}
        cand = executables.get(key)
        if cand:
            if os.path.isabs(cand):
                try:
                    if os.path.isfile(cand) and os.access(cand, os.X_OK):
                        return cand
                except OSError:
                    pass
            else:
                found = shutil.which(cand)
                if found:
                    return found
                return cand
        for name in fallbacks:
            found = shutil.which(name)
            if found:
                return found
        return cand or fallbacks[0]

    def _ensure_writable_tmp(self):
        """Point TMPDIR/TMP/TEMP at a writable dir (OHOS /tmp is read-only).

        Prefers the HMBS-injected TMPDIR/TMP/TEMP; falls back to a per-build
        tmp dir under build_folder. Only replaces the temp root, never
        skips tests. Clang/CMake/ctest temp files then avoid EROFS.
        """
        candidate = (
            os.environ.get("HMBS_TMPDIR")
            or os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
        )

        def _writable(path):
            try:
                os.makedirs(path, exist_ok=True)
                probe = os.path.join(path, ".hmbs_write_probe")
                with open(probe, "w", encoding="utf-8") as f:
                    f.write("ok")
                try:
                    os.remove(probe)
                except OSError:
                    pass
                return True
            except OSError:
                return False

        if candidate and _writable(candidate):
            tmp = candidate
        else:
            try:
                base = self.build_folder
            except Exception:
                base = os.path.expanduser("~")
            tmp = os.path.join(base, "tmp")
            os.makedirs(tmp, exist_ok=True)
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = tmp
        return tmp

    def _dump_cmake_diagnostics(self, context):
        """Best-effort dump to surface the real compiler-check failure.

        The preflight summary truncates CMake's compiler output
        (\"...\" omissions), so on failure we print the toolchain file,
        clang version, and CMakeError/CMakeOutput logs into the full log
        for the next round. Never raises.
        """
        try:
            self.output.info("HMBS_DIAG context=%s TMPDIR=%s TEMP=%s TMP=%s" % (
                context, os.environ.get("TMPDIR", "<unset>"),
                os.environ.get("TEMP", "<unset>"),
                os.environ.get("TMP", "<unset>")))
            self.output.info("HMBS_DIAG PATH=%s" % os.environ.get("PATH", "<unset>")[:2000])
            for key in ("CC", "CXX", "HMBS_CMAKE", "HMBS_MAKE", "HMBS_NINJA"):
                self.output.info("HMBS_DIAG %s=%s" % (key, os.environ.get(key, "<unset>")))
        except Exception:
            pass
        # Toolchain file generated by CMakeToolchain.
        try:
            cands = []
            try:
                gen_folder = self.generators_folder
            except Exception:
                gen_folder = None
            if gen_folder:
                cands.append(os.path.join(gen_folder, "conan_toolchain.cmake"))
            gen_dir = os.path.join(self.build_folder, "build", "Release", "generators")
            cands.extend([os.path.join(gen_dir, "conan_toolchain.cmake"),
                          os.path.join(self.build_folder, "conan_toolchain.cmake"),
                          os.path.join(self.build_folder, "generators",
                                       "conan_toolchain.cmake")])
            for tc_path in cands:
                if os.path.isfile(tc_path):
                    with open(tc_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    self.output.info("HMBS_DIAG conan_toolchain.cmake (%s, %d bytes):\n%s" % (
                        tc_path, len(content), content[:6000]))
                    break
            else:
                self.output.info("HMBS_DIAG no conan_toolchain.cmake found under %s" % self.build_folder)
        except Exception as exc:
            self.output.info("HMBS_DIAG toolchain dump failed: %s" % exc)
        # Direct compiler sanity: clang --version + hello.c compile with -v.
        try:
            comp = (self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}).get("c") \
                or shutil.which("clang") or "/data/service/hnp/bin/clang"
            self.output.info("HMBS_DIAG compiler=%s" % comp)
            proc = subprocess.run([comp, "--version"],
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, timeout=60, env=dict(os.environ))
            self.output.info("HMBS_DIAG clang --version rc=%d:\n%s" % (
                proc.returncode, (proc.stdout or "")[:3000]))
            hello = os.path.join(self.build_folder, "hmbs_hello.c")
            hello_obj = os.path.join(self.build_folder, "hmbs_hello.o")
            with open(hello, "w", encoding="utf-8") as f:
                f.write("int main(void){return 0;}\n")
            proc2 = subprocess.run([comp, "-v", hello, "-c", "-o", hello_obj],
                                   cwd=self.build_folder,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, timeout=120, env=dict(os.environ))
            self.output.info("HMBS_DIAG hello.c compile rc=%d:\n%s" % (
                proc2.returncode, (proc2.stdout or "")[:5000]))
        except Exception as exc:
            self.output.info("HMBS_DIAG compiler probe failed: %s" % exc)
        # CMake try-compile logs (only exist after a failed configure).
        try:
            import glob as _glob
            for pattern in ("CMakeFiles/CMakeError.log", "CMakeFiles/CMakeOutput.log",
                            "**/CMakeFiles/CMakeError.log", "**/CMakeFiles/CMakeOutput.log"):
                for log_path in _glob.glob(os.path.join(self.build_folder, pattern), recursive=True):
                    try:
                        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                            txt = f.read()
                        self.output.info("HMBS_DIAG %s (%d bytes, head):\n%s" % (
                            log_path, len(txt), txt[:8000]))
                    except OSError as exc:
                        self.output.info("HMBS_DIAG read %s failed: %s" % (log_path, exc))
                    break
        except Exception as exc:
            self.output.info("HMBS_DIAG log dump failed: %s" % exc)

    def _resolve_ctest(self):
        """Resolve ctest preferring the HMBS-probed cmake dir (PATH already
        has HMBS tools prepended; this is only an explicit fallback)."""
        hmbs_cmake = os.environ.get("HMBS_CMAKE") or os.environ.get(
            "user.hmbs:cmake_path")
        if hmbs_cmake:
            cand = os.path.join(os.path.dirname(hmbs_cmake), "ctest")
            if os.path.isfile(cand):
                return cand
        found = shutil.which("ctest")
        return found or "ctest"

    def _upstream_run_test_names(self):
        """Audit helper: RUN_TEST() case names declared in upstream netcode.c."""
        path = os.path.join(self.source_folder, "netcode.c")
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            src = f.read()
        names = re.findall(r"^[ \t]*RUN_TEST\s*\(\s*(test_\w+)\s*\)", src, re.MULTILINE)
        return sorted(set(names))

    def _run_upstream_suite(self):
        """Run the upstream suite once via ctest and emit HMBS evidence.

        ctest is invoked with -V so the per-case output (one line per
        RUN_TEST plus the final ALL TESTS PASSED banner) stays in the log
        for L1c trace checks and for honest executed/passed counting.
        """
        expected = self._upstream_run_test_names()
        discovered = len(expected)
        if discovered == 0:
            raise ConanException("upstream audit failed: no RUN_TEST found in netcode.c")

        candidates = [
            os.path.join(self.build_folder, "bin", "test"),
            os.path.join(self.build_folder, "bin", "test.exe"),
        ]
        runner = next((p for p in candidates if os.path.isfile(p)), None)
        if runner is None:
            marker = {
                "status": "failed",
                "framework": "ctest",
                "command": "ctest -V --output-on-failure",
                "discovered": discovered,
                "executed": 0,
                "passed": 0,
                "failed": discovered,
                "skipped": 0,
                "reason": "upstream test runner (bin/test) was not built",
            }
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
            raise ConanException("upstream test runner was not built: %s" % candidates)
        # Falsification guard: a stub/empty binary must never count as a pass.
        if os.path.getsize(runner) < 1024:
            raise ConanException("upstream test runner too small, refusing: %s" % runner)

        self.output.info("Running upstream suite: ctest -V --output-on-failure")
        ctest_bin = self._resolve_ctest()
        self.output.info("using ctest: %s (TMPDIR=%s)" % (
            ctest_bin, os.environ.get("TMPDIR", "<unset>")))
        try:
            proc = subprocess.run(
                [ctest_bin, "-V", "--output-on-failure"],
                cwd=self.build_folder,
                env=dict(os.environ),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=900,
            )
            out = proc.stdout or ""
        except subprocess.TimeoutExpired as exc:
            marker = {
                "status": "failed",
                "framework": "ctest",
                "command": "ctest -V --output-on-failure",
                "discovered": discovered,
                "executed": 0,
                "passed": 0,
                "failed": discovered,
                "skipped": 0,
                "reason": "timeout after 900s: %s" % str(exc)[:300],
            }
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
            raise ConanException("upstream ctest timed out after 900s")

        self.output.info("upstream ctest output:\n" + out)
        if not out.strip():
            raise ConanException("upstream ctest produced no output, refusing to pass")

        seen = set(re.findall(r"^\s*(?:\d+:\s*)?(test_[A-Za-z0-9_]+)\s*$", out, re.MULTILINE))
        executed = len(set(expected) & {n.strip() for n in seen})
        banner = "*** ALL TESTS PASSED ***" in out
        ok = proc.returncode == 0 and banner and executed == discovered
        marker = {
            "status": "passed" if ok else "failed",
            "framework": "ctest",
            "command": "ctest -V --output-on-failure",
            "discovered": discovered,
            "executed": executed,
            "passed": executed if ok else 0,
            "failed": 0 if ok else discovered,
            "skipped": 0,
        }
        if not ok:
            marker["reason"] = "rc=%d banner=%s executed=%d/%d" % (
                proc.returncode, banner, executed, discovered)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
        if not ok:
            raise ConanException("upstream netcode tests failed: %s" % json.dumps(marker))

    def build(self):
        self._ensure_writable_tmp()
        apply_conandata_patches(self)
        # Pre-configure probe: proves whether the compiler itself works with
        # the current TMPDIR before CMake's compiler check runs. Output lands
        # in the full preflight log for the next round's diagnosis.
        self._dump_cmake_diagnostics("pre-configure")
        cmake = CMake(self)
        try:
            cmake.configure()
        except ConanException:
            # Surface the real compiler error (summary truncates it).
            self._dump_cmake_diagnostics("configure-failed")
            raise
        # OOM mitigation (真机 /bin/sh: Out of memory): upstream builds 5
        # examples + netcode_test when NETCODE_BUILD_TESTS=ON. Only the
        # library and the upstream runner are needed, so build just those
        # two targets sequentially with a single job to keep peak RSS low.
        # ctest evidence below still runs the full 46-case suite.
        os.environ["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"
        cmake.build(target="netcode")
        cmake.build(target="netcode_test")
        # Layer 1: run the full upstream suite inside the build tree.
        self._run_upstream_suite()

    def package(self):
        copy(self, "LICENCE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        # Upstream installs only the netcode library; the vendored sodium
        # STATIC archive (add_library(sodium STATIC sodium/sodium.c)) is
        # linked PUBLIC into netcode but never installed. Without it the
        # consumer link fails with undefined sodium_* symbols (see preflight
        # test_package ld.lld errors). Persist it under lib/ so
        # package_info can expose -lsodium to downstream.
        import glob as _glob
        lib_dst = os.path.join(self.package_folder, "lib")
        _found = []
        for _pattern in ("**/libsodium.a", "**/libsodium*.lib",
                         "**/sodium.lib", "**/sodium.a"):
            for _cand in _glob.glob(
                    os.path.join(self.build_folder, _pattern), recursive=True):
                try:
                    if os.path.isfile(_cand):
                        _found.append(_cand)
                except OSError:
                    pass
        # De-duplicate by basename, prefer the largest (real archive).
        _best = {}
        for _cand in _found:
            try:
                _best.setdefault(os.path.basename(_cand), _cand)
                if os.path.getsize(_cand) > os.path.getsize(_best[os.path.basename(_cand)]):
                    _best[os.path.basename(_cand)] = _cand
            except OSError:
                pass
        for _name, _src in _best.items():
            try:
                copy(self, _name, src=os.path.dirname(_src), dst=lib_dst)
                self.output.info("packaged vendored sodium archive: %s" % _src)
            except Exception as exc:
                raise ConanException(
                    "failed to package vendored sodium archive %s: %s" % (_src, exc))
        if not _best:
            raise ConanException(
                "vendored sodium archive not found under %s (patterns: libsodium.a/sodium.lib)" % self.build_folder)
        # Persist the upstream test runner so test_package can rerun the
        # suite on every conan create (build() is skipped on cache hits,
        # so evidence must not depend on build() alone).
        test_dst = os.path.join(self.package_folder, "res", "upstream-test")
        for _name in ("test", "test.exe"):
            _src = os.path.join(self.build_folder, "bin", _name)
            if os.path.isfile(_src):
                copy(self, _name, src=os.path.join(self.build_folder, "bin"), dst=test_dst)

    def package_info(self):
        # Static consumers need the vendored sodium archive explicitly:
        # upstream install(TARGETS netcode) drops the PUBLIC-linked sodium
        # STATIC lib, so -lnetcode alone leaves sodium_* undefined.
        # Shared libnetcode already folds sodium objects in, no extra lib.
        try:
            shared = bool(self.options.shared)
        except Exception:
            shared = False
        if shared:
            self.cpp_info.libs = ["netcode"]
        else:
            self.cpp_info.libs = ["netcode", "sodium"]
        if self.settings.os == "Windows":
            self.cpp_info.system_libs = ["ws2_32", "iphlpapi"]
        self.cpp_info.set_property("cmake_file_name", "netcode")
        self.cpp_info.set_property("cmake_target_name", "netcode::netcode")
