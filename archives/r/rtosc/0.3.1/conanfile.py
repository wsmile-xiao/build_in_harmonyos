#!/usr/bin/env python3
"""Conan recipe — rtosc 0.3.1 (CMake).

Realtime safe OSC packet serialization and dispatch (MIT, fundamental/rtosc).
Core libraries rtosc (C99) + rtosc-cpp (C++11) have no mandatory third-party
dependencies; the optional liblo/JACK/FLTK/Ruby/Doxygen probes stay OFF on
OHOS (nothing to find), so only the core libraries and the default 28 ctest
entries are built and executed.

Build notes:
  - os=OHOS maps to CMAKE_SYSTEM_NAME=HarmonyOS, which stock CMake does not
    know and which upstream gates GNUInstallDirs/install() behind
    CMAKE_SYSTEM_NAME MATCHES "Linux". Pin CMAKE_SYSTEM_NAME=Linux, same
    doctrine as rttr/zstr in this repo.
  - upstream cmake_minimum_required is 2.8, rejected by CMake >= 4; pass
    CMAKE_POLICY_VERSION_MINIMUM=3.5 instead of patching the source.
  - upstream option RTOSC_BUILD_SHARED_LIBS mirrors BUILD_SHARED_LIBS;
    both are set from the Conan shared option. Examples and PERF_TEST stay
    OFF (examples need JACK/GUI, perf/serializer are opt-in).
  - upstream tests run in build() via ctest (see _run_upstream_ctest):
    deterministic parsing of `ctest -N` (discovered) and the
    `ctest --output-on-failure` per-test lines (executed/passed/failed),
    single regex pass, no string-count arithmetic, identity self-check,
    drift assertion against the audited total of 28.
"""
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import copy, export_conandata_patches, get


# Audited from the v0.3.1 tag tarball (CMakeLists.txt maketest/maketestcpp):
# C (15): version, util, osc-spec, arg-val-cmp, arg-val-math, pretty-format,
#   simple-messages, null-messages, bundles, patterns, nested-bundles,
#   fat-message, empty-strings, message-alignment, test-arg-iter.
# C++ (13): test-midi-mapper, metadata, apropos, default-value, headerlib,
#   test-walker, walk-ports, path-search, undo-test, sugar,
#   typed-template-test, path-collapse, test-automation.
# liblo/JACK/Ruby/PERF_TEST optionals are OFF on OHOS, so none of the
# conditional entries (liblo, performance, serializer, port-checker) exist.
UPSTREAM_TEST_TOTAL = 28


class RtoscConan(ConanFile):
    name = "rtosc"
    version = "0.3.1"
    description = "Realtime safe OSC packet serialization and dispatch"
    license = "MIT"
    homepage = "https://github.com/fundamental/rtosc"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("osc", "audio", "realtime", "messaging")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "rtosc is adapted for Linux and OHOS, not %s" % self.settings.os)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ensure_writable_tmp(self):
        candidates = []
        for key in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR",
                    "HMBS_AUTOCONF_MKTEMP_FALLBACK"):
            val = os.getenv(key)
            if val and val not in candidates:
                candidates.append(val)
        cap = os.getenv("HMBS_PLATFORM_CAPABILITIES")
        if cap:
            try:
                import json as _json
                tmpdir = _json.loads(cap).get("tmpdir")
                if tmpdir and tmpdir not in candidates:
                    candidates.insert(0, tmpdir)
            except Exception:
                pass
        home = os.path.expanduser("~")
        if home and home != "~":
            home_tmp = os.path.join(home, "tmp")
            if home_tmp not in candidates:
                candidates.append(home_tmp)
        try:
            bf = getattr(self, "build_folder", None)
            if bf:
                local_tmp = os.path.join(bf, "hmbs-tmp")
                if local_tmp not in candidates:
                    candidates.append(local_tmp)
        except Exception:
            pass
        for cand in candidates:
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs_write_probe")
                with open(probe, "w") as f:
                    f.write("ok")
                os.remove(probe)
                os.environ["TMPDIR"] = cand
                os.environ["TMP"] = cand
                os.environ["TEMP"] = cand
                os.environ["GOTMPDIR"] = cand
                return cand
            except Exception:
                continue
        return None

    def _resolve_compiler(self, configured, names):
        if configured and os.path.exists(configured):
            return configured
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        home_bin = os.path.join(os.path.expanduser("~"), "usr", "local", "bin")
        for name in names:
            cand = os.path.join(home_bin, name)
            if os.path.exists(cand):
                return cand
        return configured or names[0]

    def generate(self):
        tmpdir = self._ensure_writable_tmp()
        if tmpdir:
            env = Environment()
            env.define("TMPDIR", tmpdir)
            env.define("TMP", tmpdir)
            env.define("TEMP", tmpdir)
            env.define("GOTMPDIR", tmpdir)
            env.vars(self, scope="build").save_sh("hmbs_tmpdir")
        tc = CMakeToolchain(self)
        try:
            _compilers = self.conf.get("tools.build:compiler_executables",
                                       default=None)
        except Exception:
            _compilers = None
        if not isinstance(_compilers, dict):
            _compilers = {}
        _c = self._resolve_compiler(_compilers.get("c"), ("clang", "cc"))
        _cxx = self._resolve_compiler(_compilers.get("cpp"), ("clang++", "c++"))
        if _c:
            tc.cache_variables["CMAKE_C_COMPILER"] = _c
        if _cxx:
            tc.cache_variables["CMAKE_CXX_COMPILER"] = _cxx
        self.output.info("HMBS diag compilers c=%s cxx=%s" % (_c, _cxx))
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["RTOSC_BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_RTOSC_EXAMPLES"] = "OFF"
        tc.variables["PERF_TEST"] = "OFF"
        tc.generate()
        self._fix_generated_toolchain_compiler(_compilers, _c, _cxx)

    def _fix_generated_toolchain_compiler(self, configured_map, c, cxx):
        if not isinstance(configured_map, dict):
            configured_map = {}
        c_old = configured_map.get("c")
        cxx_old = configured_map.get("cpp")
        pairs = []
        if c_old and c and c_old != c \
                and not os.path.exists(c_old) and os.path.exists(c):
            pairs.append((c_old, c))
        if cxx_old and cxx and cxx_old != cxx \
                and not os.path.exists(cxx_old) and os.path.exists(cxx):
            pairs.append((cxx_old, cxx))
        if not pairs:
            return
        try:
            gf = getattr(self, "generators_folder", None)
            path = os.path.join(gf, "conan_toolchain.cmake") if gf else None
            if path and os.path.isfile(path):
                with open(path, "r", encoding="utf-8",
                          errors="replace") as f:
                    text = f.read()
                orig = text
                for old_p, new_p in pairs:
                    text = text.replace(old_p, new_p)
                if text != orig:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(text)
                    self.output.info(
                        "HMBS diag fixed generated toolchain %s" % path)
        except Exception as e:
            self.output.warning("HMBS diag toolchain fix failed: %s" % e)
        try:
            comp_env = Environment()
            if c_old and c and (c_old, c) in pairs:
                comp_env.define("CC", c)
            if cxx_old and cxx and (cxx_old, cxx) in pairs:
                comp_env.define("CXX", cxx)
            comp_env.vars(self, scope="build").save_sh("hmbs_compiler")
        except Exception as e:
            self.output.warning("HMBS diag compiler env failed: %s" % e)

    def _ctest_executable(self):
        for key in ("HMBS_CMAKE",):
            cmake_bin = os.environ.get(key)
            if cmake_bin and os.path.isfile(cmake_bin):
                sibling = os.path.join(os.path.dirname(cmake_bin), "ctest")
                if os.path.isfile(sibling):
                    return sibling
        found = shutil.which("ctest")
        if found:
            return found
        raise ConanException(
            "ctest executable not found (HMBS_CMAKE sibling unset, PATH lookup failed)")

    def _run_upstream_ctest(self):
        ctest = self._ctest_executable()
        bf = self.build_folder
        n_log = os.path.join(bf, "hmbs-ctest-n.log")
        run_log = os.path.join(bf, "hmbs-ctest.log")
        self.run('"%s" -N > "%s" 2>&1' % (ctest, n_log),
                 cwd=bf, env="conanbuild", ignore_errors=False)
        try:
            with open(n_log, "r", encoding="utf-8", errors="replace") as f:
                n_text = f.read()
        except OSError as exc:
            raise ConanException("cannot read %s: %s" % (n_log, exc))
        self.output.info("ctest -N output:\n" + n_text)
        m = re.search(r"Total\s+Tests:\s*(\d+)", n_text)
        if not m:
            raise ConanException(
                "ctest -N produced no 'Total Tests:' line; refusing to guess "
                "(searched: %s)" % n_log)
        discovered = int(m.group(1))
        if discovered != UPSTREAM_TEST_TOTAL:
            raise ConanException(
                "upstream harness drift: ctest -N reports %d tests, audited %d "
                "(CMakeLists.txt maketest/maketestcpp)" % (discovered, UPSTREAM_TEST_TOTAL))
        rc = 0
        try:
            self.run('"%s" --output-on-failure > "%s" 2>&1' % (ctest, run_log),
                     cwd=bf, env="conanbuild", ignore_errors=False)
        except ConanException as exc:
            rc = 1
            self.output.warning("ctest run returned non-zero: %s" % exc)
        try:
            with open(run_log, "r", encoding="utf-8", errors="replace") as f:
                run_text = f.read()
        except OSError as exc:
            raise ConanException("cannot read %s: %s" % (run_log, exc))
        if not run_text.strip() or "Test #" not in run_text:
            raise ConanException(
                "ctest log empty or without per-test lines; refusing to claim "
                "a pass (log: %s, rc=%d)" % (run_log, rc))
        self.output.info("ctest output:\n" + run_text)
        passed = 0
        failed = 0
        skipped = 0
        seen = set()
        test_line = re.compile(r"Test\s*#\s*(\d+)\s*:\s*(\S+)")
        for line in run_text.splitlines():
            mt = test_line.search(line)
            if not mt:
                continue
            idx = int(mt.group(1))
            name = mt.group(2).strip()
            if idx in seen:
                continue
            seen.add(idx)
            upper = line.upper()
            if "PASSED" in upper and "FAILED" not in upper:
                passed += 1
            elif "FAILED" in upper or "TIMEOUT" in upper or "***FAILED" in upper:
                failed += 1
            elif "SKIPPED" in upper or "NOT RUN" in upper:
                skipped += 1
            else:
                failed += 1
                self.output.warning("HMBS diag unclassified ctest line: %s" % line)
        executed = passed + failed
        for field in (discovered, executed, passed, failed, skipped):
            if not isinstance(field, int) or field < 0:
                raise ConanException("ctest counts must be non-negative ints")
        if not (passed + failed == executed):
            raise ConanException("ctest identity failed: passed+failed != executed")
        if not (executed + skipped <= discovered):
            raise ConanException("ctest identity failed: executed+skipped > discovered")
        if not (executed <= discovered):
            raise ConanException("ctest identity failed: executed > discovered")
        if len(seen) != discovered and executed + skipped != discovered:
            self.output.warning(
                "HMBS diag ctest line coverage %d/%d (executed=%d skipped=%d)" % (
                    len(seen), discovered, executed, skipped))
        status = "passed" if (rc == 0 and failed == 0 and passed == discovered) else "failed"
        result = {
            "status": status,
            "framework": "ctest",
            "command": "ctest --output-on-failure",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, separators=(",", ":"))
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass
        try:
            with open(os.path.join(bf, "hmbs_upstream.json"), "w", encoding="utf-8") as f:
                json.dump(result, f)
        except OSError as exc:
            raise ConanException("cannot persist hmbs_upstream.json: %s" % exc)
        if status != "passed":
            raise ConanException(
                "upstream ctest failed: %d/%d passed, %d failed, %d skipped "
                "(log: %s)" % (passed, discovered, failed, skipped, run_log))
        return result

    def build(self):
        self._ensure_writable_tmp()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_ctest()

    def package(self):
        self._ensure_writable_tmp()
        copy(self, "LICENSE", src=self.source_folder, dst="licenses")
        cmake = CMake(self)
        cmake.install()
        try:
            src = os.path.join(self.build_folder, "hmbs_upstream.json")
            if os.path.isfile(src):
                dst_dir = os.path.join(self.package_folder, "res")
                os.makedirs(dst_dir, exist_ok=True)
                shutil.copyfile(src, os.path.join(dst_dir, "hmbs_upstream.json"))
            else:
                self.output.warning("HMBS diag hmbs_upstream.json missing in package()")
        except Exception as e:
            self.output.warning("HMBS diag package upstream copy failed: %s" % e)

    def package_info(self):
        self.cpp_info.libs = ["rtosc-cpp", "rtosc"]
        self.cpp_info.set_property("cmake_file_name", "rtosc")
        self.cpp_info.set_property("cmake_target_name", "rtosc::rtosc")
        self.cpp_info.set_property("pkg_config_name", "librtosc")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = []
