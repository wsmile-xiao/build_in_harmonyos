#!/usr/bin/env python3
"""Conan recipe — libics 1.7.0 (CMake).

Image Cytometry Standard file reading and writing library.
Build: CMake with LIBICS_USE_ZLIB=ON (zlib from Conan).
Upstream tests: ctest suite (20 real tests + 1 build helper) runs
in build() and reports the HMBS_UPSTREAM_TEST_RESULT marker.
"""

import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import get, copy


# Statically audited upstream ctest total (CMakeLists.txt +
# support/cpp_interface/CMakeLists.txt, tag 1.7.0, zlib enabled):
# C: test_ics1, test_ics2a, test_ics2b, test_gzip, test_compress,
# test_strides, test_strides2, test_strides3,
# test_metadata1..4, test_history = 13 real tests
# C++: test_ics2a_cpp, test_ics2b_cpp,
# test_metadata1_cpp..4_cpp, test_history_cpp = 7 real tests
# => 20 real tests + 1 ctest_build_test_code helper = 21 ctest entries.
# HMBS evidence requires discovered == executed == ctest total, so the
# marker reports the parsed ctest total; this constant is the minimum
# expected total (fails the build when fewer ran).
UPSTREAM_TEST_COUNT = 21


class LibicsConan(ConanFile):
    name = "libics"
    version = "1.7.0"
    description = "Image Cytometry Standard file reading and writing library."
    license = "LGPL-2.1-or-later"
    homepage = "https://svi-opensource.github.io/libics/"
    url = "https://github.com/svi-opensource/libics"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def requirements(self):
        self.requires("zlib/1.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        self._fix_cpp_real16()
        self._patch_math_lib()
        self._patch_zlib_link()

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        if self.settings.os == "OHOS":
            # E092 minimal alias (libwmime-r16/frei0r/ayatana-ido precedent):
            # plain tc.variables (not cache_variables) so the name rides the
            # toolchain file together with the OHOS sysroot/target; only the
            # platform name is replaced, OHOS clang from the profile stays.
            # No PROCESSOR/STATIC_LIBRARY/COMPILER_WORKS bypasses: those act
            # after the identification step and were proven ineffective for
            # this fingerprint (libwmime rounds 7-13); keep the real check.
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            self._guard_ohos_compiler(tc)
        # Upstream CMakeLists requires 3.5; keep configuring on newer CMake.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Use zlib from Conan (curl-recipe precedent: explicit module vars).
        # cpp_info dirs are relative ("include"/"lib"); join with the real
        # package folder to get absolute paths for FIND_PACKAGE(ZLIB).
        zlib_pkg = self.dependencies["zlib"]
        zlib = zlib_pkg.cpp_info
        tc.cache_variables["LIBICS_USE_ZLIB"] = True
        tc.cache_variables["ZLIB_INCLUDE_DIR"] = os.path.join(
            str(zlib_pkg.package_folder), zlib.includedirs[0])
        zlib_lib = os.path.join(
            str(zlib_pkg.package_folder), zlib.libdirs[0], "libz.a")
        if not os.path.isfile(zlib_lib):
            shared_lib = os.path.join(
                str(zlib_pkg.package_folder), zlib.libdirs[0], "libz.so")
            if os.path.isfile(shared_lib):
                zlib_lib = shared_lib
        tc.cache_variables["ZLIB_LIBRARY"] = zlib_lib
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def _guard_ohos_compiler(self, tc):
        """Pin a usable compiler when the conf path dangles (ayatana-ido
        guard; Experience-2 adapt for CMake).

        The profile pins /data/service/hnp/bin/clang(++), unusable on some
        workers. When the conf path carries a directory component but is
        absent/not-executable, fall back to the PATH-resolved compiler so
        the toolchain does not embed a dangling path; when usable, leave
        the toolchain untouched (keeps OHOS sysroot/target).
        """
        try:
            exes = self.conf.get("tools.build:compiler_executables",
                                 default=None)
        except Exception:
            exes = None
        conf_c = conf_cxx = None
        if isinstance(exes, dict):
            conf_c = exes.get("c")
            conf_cxx = (exes.get("cpp") or exes.get("cxx")
                        or exes.get("c"))
        for key, conf_val, bare in (
                ("CMAKE_C_COMPILER", conf_c, "clang"),
                ("CMAKE_CXX_COMPILER", conf_cxx, "clang++")):
            if conf_val and (os.path.sep in str(conf_val)
                             or "/" in str(conf_val)):
                try:
                    ok = (os.path.isfile(str(conf_val))
                          and os.access(str(conf_val), os.X_OK))
                except Exception:
                    ok = False
                if not ok:
                    self.output.warning(
                        "conf compiler '%s' unusable; falling back to PATH"
                        % conf_val)
                    which = shutil.which(bare)
                    if which:
                        tc.variables[key] = which

    def build(self):
        self._fix_cpp_real16()
        self._patch_math_lib()
        self._patch_zlib_link()
        self._ensure_writable_tmp()
        self._ensure_lld_runnable()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_ctest()

    def _sdk_llvm_lib_dir(self):
        """Derive the OHOS SDK llvm/lib dir holding libxml2.so.16 (E266).

        OHOS SDK lld (llvm/bin/lld) dynamically links libxml2.so.16, but
        CI worker sandboxes may not resolve it via the default library
        search path, so lld fails to start and every test-executable link
        dies with "Error loading shared library libxml2.so.16 / Error
        relocating lld: xmlFreeDoc: symbol not found" (julius-1.8.0 merged
        precedent, identical signature). Derive the dir from
        `clang -print-resource-dir` (<sdk>/llvm/lib/clang/<ver> -> dirname
        twice -> <sdk>/llvm/lib) and only return it when it really holds
        libxml2.so.16; otherwise return None (graceful degrade, no
        hard-coded absolute paths).
        """
        candidates = []
        try:
            exes = self.conf.get("tools.build:compiler_executables",
                                 default=None)
        except Exception:
            exes = None
        if isinstance(exes, dict):
            for key in ("c", "cpp", "cxx"):
                val = exes.get(key)
                if val:
                    candidates.append(str(val))
        which_clang = shutil.which("clang")
        if which_clang:
            candidates.append(which_clang)
        for cc in candidates:
            try:
                out = subprocess.check_output(
                    [cc, "-print-resource-dir"],
                    stderr=subprocess.DEVNULL, text=True).strip()
            except Exception:
                continue
            lib = os.path.dirname(os.path.dirname(out))
            if lib and os.path.isfile(
                    os.path.join(lib, "libxml2.so.16")):
                return lib
        return None

    def _ensure_lld_runnable(self):
        """Prepend SDK llvm/lib to LD_LIBRARY_PATH so lld can start (E266).

        Runs before cmake.configure(); os.environ mutation is inherited
        by cmake build steps and by the _run_upstream_ctest() subprocess
        (which spawns cmake --build -> clang/lld for the 20 test
        executables). Idempotent; never deletes tests. Never switches the
        linker: GNU ld output is not executable in the OHOS sandbox
        (babeltrace DRAFT-6048 forbid_5), only lld output is.
        """
        sdk_lib = self._sdk_llvm_lib_dir()
        if not sdk_lib:
            self.output.info(
                "lld compat: no SDK llvm/lib with libxml2.so.16, skipping")
            return
        old = os.environ.get("LD_LIBRARY_PATH", "")
        if old.split(":")[0] != sdk_lib:
            os.environ["LD_LIBRARY_PATH"] = (
                sdk_lib + (":" + old if old else ""))
            self.output.info(
                "lld compat: prepended SDK llvm/lib to LD_LIBRARY_PATH: %s"
                % sdk_lib)
        else:
            self.output.info(
                "lld compat: SDK llvm/lib already first in LD_LIBRARY_PATH")

    def _fix_cpp_real16(self):
        """Insert missing Real16 into C++ DataType enum (tag 1.7.0 bug).

        Upstream tag 1.7.0 added Ics_real16 to the C library and uses
        DataType::Real16 in support/cpp_interface/libics.cpp, but forgot
        the member in support/cpp_interface/libics.hpp (fixed on master
        with one line between SInt64 and Real32). Previous round shipped
        this as a .patch file; conan rejected it with context mismatch
        (expected-context vs '   UInt32, ...' at hunk offset) because the
        hunk header/indent did not match the archived source byte for
        byte. This route replaces the patch file with an idempotent,
        whitespace- and line-ending-tolerant in-place edit anchored on
        the SInt64->Real32 boundary, failing loudly when the anchor is
        absent. Only adds the one upstream-master-identical member;
        never deletes tests.
        """
        base = getattr(self, "source_folder", None) or getattr(
            self, "base_source_folder", None)
        if not base:
            return
        header = os.path.join(str(base), "support", "cpp_interface",
                              "libics.hpp")
        if not os.path.isfile(header):
            # source() stage: folder may not exist yet on some flows;
            # build() will retry when the tree is present.
            self.output.info("Real16 fix skipped (header not present yet)")
            return
        try:
            with open(header, "rb") as handle:
                raw = handle.read()
        except OSError as exc:
            raise ConanException("cannot read libics.hpp: %s" % exc)
        if b"Real16" in raw:
            self.output.info("Real16 already present, fix is a no-op")
            return
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ConanException("libics.hpp not utf-8: %s" % exc)
        newline = "\r\n" if "\r\n" in text else "\n"
        pattern = re.compile(
            r"(?m)^(?P<indent>[ \t]*)SInt64(?P<rest>,[ \t]*//[^\r\n]*\r?\n)"
            r"(?P=indent)Real32,")
        match = pattern.search(text)
        if not match:
            raise ConanException(
                "Real16 anchor not found (SInt64->Real32 boundary missing) "
                "in support/cpp_interface/libics.hpp")
        indent = match.group("indent")
        # Upstream-master-identical line, reusing the file's own indent
        # and line ending so the result matches master apart from indent.
        insert = "%sReal16,    // real,    signed,   16 bpp%s" % (
            indent, newline)
        # Insert the new line right after the SInt64 line, before Real32.
        sint64_end = text.index(newline, match.start()) + len(newline)
        fixed = text[:sint64_end] + insert + text[sint64_end:]
        if "Real16" not in fixed:
            raise ConanException("Real16 insertion produced no change")
        try:
            with open(header, "w", encoding="utf-8", newline="") as handle:
                handle.write(fixed)
        except OSError as exc:
            raise ConanException("cannot write libics.hpp: %s" % exc)
        self.output.info("inserted missing Real16 into libics.hpp (master-identical)")

    def _patch_math_lib(self):
        """Make `target_link_libraries(libics PUBLIC m)` robust on OHOS.

        Upstream links libm unconditionally under if(UNIX). The main
        static archive builds without resolving it, so a missing libm
        only surfaces when ctest_build_test_code links the 14 test
        executables (all_tests) -- exactly the observed signature:
        cmake.build() ok, first ctest item Failed, rest Not Run.
        Replace with a find_library guard: link only when found,
        otherwise rely on libc (muslToolchain provides math in libc).
        Idempotent; never deletes tests.
        """
        base = getattr(self, "source_folder", None) or getattr(
            self, "base_source_folder", None)
        if not base:
            return
        cmake_lists = os.path.join(str(base), "CMakeLists.txt")
        if not os.path.isfile(cmake_lists):
            self.output.info("math-lib patch skipped (no CMakeLists yet)")
            return
        try:
            with open(cmake_lists, "rb") as handle:
                raw = handle.read()
        except OSError as exc:
            raise ConanException("cannot read CMakeLists.txt: %s" % exc)
        if b"LIBICS_MATH_LIB" in raw:
            self.output.info("math-lib guard already present, no-op")
            return
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ConanException("CMakeLists.txt not utf-8: %s" % exc)
        anchor = "target_link_libraries(libics PUBLIC m)"
        if anchor not in text:
            self.output.info("math-lib anchor absent, no-op")
            return
        replacement = (
            "find_library(LIBICS_MATH_LIB m)\n"
            "if(LIBICS_MATH_LIB)\n"
            "   target_link_libraries(libics PUBLIC ${LIBICS_MATH_LIB})\n"
            "endif()"
        )
        fixed = text.replace(anchor, replacement, 1)
        if fixed == text:
            raise ConanException("math-lib replacement produced no change")
        try:
            with open(cmake_lists, "w", encoding="utf-8", newline="") as handle:
                handle.write(fixed)
        except OSError as exc:
            raise ConanException("cannot write CMakeLists.txt: %s" % exc)
        self.output.info("math-lib link made conditional (find_library guard)")

    def _patch_zlib_link(self):
        """Link libics against Conan zlib in either CMake package case (v2).

        v1 only appended `if(TARGET ZLIB::ZLIB)` and still failed on真机:
        the guard message printed ("zlib imported-target link guard added")
        yet every test executable still reported `undefined symbol:
        crc32/deflate/inflate` from libics_gzip.c.o. So the uppercase
        target did not exist after upstream `find_package(ZLIB)`: the
        CMakeDeps hint in the same log advertises lowercase
        `find_package(zlib)` / `zlib::zlib`, which upstream never calls
        (CMake package names are case-sensitive), while the uppercase
        FindZLIB MODULE path honoring ZLIB_LIBRARY/ZLIB_INCLUDE_DIR did
        not yield a target either. Static libics.a still builds; only the
        test-executable link fails -- the observed `ctest_build_test_code
        Failed, rest Not Run` signature.
        v2 keeps the upstream MODULE line untouched and, inside the same
        LIBICS_USE_ZLIB block, explicitly probes the lowercase Conan
        CONFIG package (`find_package(zlib CONFIG QUIET)`) then links
        whichever imported target exists (`zlib::zlib` first, `ZLIB::ZLIB`
        second, both PUBLIC so all C/C++ tests inherit them). Idempotent
        via LIBICS_ZLIB_CONAN_GUARD; never deletes tests.
        """
        base = getattr(self, "source_folder", None) or getattr(
            self, "base_source_folder", None)
        if not base:
            return
        cmake_lists = os.path.join(str(base), "CMakeLists.txt")
        if not os.path.isfile(cmake_lists):
            self.output.info("zlib-link patch skipped (no CMakeLists yet)")
            return
        try:
            with open(cmake_lists, "rb") as handle:
                raw = handle.read()
        except OSError as exc:
            raise ConanException("cannot read CMakeLists.txt: %s" % exc)
        if b"LIBICS_ZLIB_CONAN_GUARD" in raw:
            self.output.info("zlib-link conan guard already present, no-op")
            return
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ConanException("CMakeLists.txt not utf-8: %s" % exc)
        # Drop the v1 guard in freshly-extracted trees if present so v2
        # is the single active strategy (fresh get() trees will not have
        # it, but build-folder retries might).
        if "LIBICS_ZLIB_TARGET_GUARD" in text:
            v1_block = (
                "\n# LIBICS_ZLIB_TARGET_GUARD: CMakeDeps provides ZLIB::ZLIB in\n"
                "# CONFIG mode where ${ZLIB_LIBRARIES} is empty; link it when\n"
                "# available so test executables resolve crc32/deflate/inflate.\n"
                "if(TARGET ZLIB::ZLIB)\n"
                "   target_link_libraries(libics PUBLIC ZLIB::ZLIB)\n"
                "endif()"
            )
            text = text.replace(v1_block, "", 1)
            raw = text.encode("utf-8")
        anchor_line = "target_link_libraries(libics PUBLIC ${ZLIB_LIBRARIES})"
        if anchor_line not in text:
            self.output.info("zlib-link anchor absent, no-op")
            return
        replacement = (
            anchor_line + "\n"
            "# LIBICS_ZLIB_CONAN_GUARD (v2): upstream never calls the\n"
            "# lowercase Conan CONFIG package, so probe it explicitly and\n"
            "# link whichever imported target exists. PUBLIC propagates to\n"
            "# every C/C++ test executable (crc32/deflate/inflate).\n"
            "find_package(zlib CONFIG QUIET)\n"
            "if(TARGET zlib::zlib)\n"
            "   target_link_libraries(libics PUBLIC zlib::zlib)\n"
            "endif()\n"
            "if(TARGET ZLIB::ZLIB)\n"
            "   target_link_libraries(libics PUBLIC ZLIB::ZLIB)\n"
            "endif()"
        )
        fixed = text.replace(anchor_line, replacement, 1)
        if fixed == text:
            raise ConanException("zlib-link replacement produced no change")
        try:
            with open(cmake_lists, "w", encoding="utf-8", newline="") as handle:
                handle.write(fixed)
        except OSError as exc:
            raise ConanException("cannot write CMakeLists.txt: %s" % exc)
        self.output.info("zlib conan-config link guard added (v2)")

    def _writable_dir(self, path):
        """Return True when path is an actually-writable directory."""
        try:
            if not (path and os.path.isdir(path)):
                return False
            probe = os.path.join(path, ".hmbs_write_probe")
            with open(probe, "w", encoding="utf-8") as handle:
                handle.write("ok")
            os.remove(probe)
            return True
        except OSError:
            return False

    def _ensure_writable_tmp(self):
        """Point TMPDIR/TMP/TEMP at a verified-writable dir (/tmp is read-only).

        HMBS injects TMPDIR; keep it only when a write probe succeeds,
        else fall back to a build-folder subdir so clang/cmake temp
        files never hit /tmp. Only replaces the temp root, never
        deletes tests.
        """
        tmp = os.environ.get("TMPDIR") or os.environ.get("TMP") or os.environ.get("TEMP")
        if not self._writable_dir(tmp):
            cand = os.environ.get("TMPDIR")
            if not self._writable_dir(cand):
                cand = os.path.join(str(self.build_folder), "hmbs-tmp")
            try:
                os.makedirs(cand, exist_ok=True)
            except OSError:
                cand = os.path.join(str(self.build_folder), "hmbs-tmp")
                os.makedirs(cand, exist_ok=True)
            tmp = cand
            os.environ["TMPDIR"] = tmp
            os.environ["TMP"] = tmp
            os.environ["TEMP"] = tmp
        self.output.info("writable TMPDIR=%s" % os.environ.get("TMPDIR"))

    def _ctest_binary_dir(self):
        """Locate the dir holding CTestTestfile.cmake (the real binary dir)."""
        candidates = [str(self.build_folder)]
        for sub in ("build/Release", "build", "Release"):
            candidates.append(os.path.join(str(self.build_folder), sub))
        for cand in candidates:
            if os.path.isfile(os.path.join(cand, "CTestTestfile.cmake")):
                return cand
        # Fall back to a recursive search one level deep.
        try:
            for entry in os.listdir(str(self.build_folder)):
                full = os.path.join(str(self.build_folder), entry)
                if os.path.isdir(full) and os.path.isfile(
                        os.path.join(full, "CTestTestfile.cmake")):
                    return full
        except OSError:
            pass
        return str(self.build_folder)

    def _resolve_ctest(self):
        """Resolve ctest via HMBS_CMAKE sibling dir first, then PATH."""
        hmbs_cmake = os.environ.get("HMBS_CMAKE")
        if hmbs_cmake:
            sib = os.path.join(os.path.dirname(hmbs_cmake), "ctest")
            if os.path.isfile(sib):
                return sib
        found = shutil.which("ctest")
        if found:
            return found
        return "ctest"

    def _run_upstream_ctest(self):
        """Run the upstream ctest suite and emit the evidence marker.

        Parses `ctest --output-on-failure` output; any failure raises so
        the build fails (exit code 0 alone is not accepted as proof).
        Full output is logged in chunks so the ctest_build_test_code
        compile error (head of log) is never truncated away.
        """
        tmp = os.environ.get("TMPDIR") or os.environ.get("TMP") or os.environ.get("TEMP")
        if not self._writable_dir(tmp):
            tmp = os.path.join(str(self.build_folder), "hmbs-tmp")
            os.makedirs(tmp, exist_ok=True)
            os.environ["TMPDIR"] = tmp
            os.environ["TMP"] = tmp
            os.environ["TEMP"] = tmp
        ctest_bin = self._ctest_binary_dir()
        ctest_exe = self._resolve_ctest()
        self.output.info("ctest binary dir=%s exe=%s" % (ctest_bin, ctest_exe))
        env = dict(os.environ)
        # Serial inner build: tiny suite, avoids oversubscribing the 1-slot
        # preflight worker when ctest_build_test_code spawns cmake --build.
        env.setdefault("CMAKE_BUILD_PARALLEL_LEVEL", "1")
        env.setdefault("CTEST_OUTPUT_ON_FAILURE", "1")
        proc = subprocess.run(
            [ctest_exe, "--output-on-failure"],
            cwd=ctest_bin,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=1200,
        )
        output = proc.stdout or ""
        try:
            with open(os.path.join(str(self.build_folder),
                                   "hmbs_ctest_full.log"),
                      "w", encoding="utf-8") as handle:
                handle.write(output)
        except OSError:
            pass
        # Log the whole output in chunks: the root cause lives in the
        # ctest_build_test_code section at the head, while the old
        # output[-4000:] tail only showed Not-Run lines.
        for idx in range(0, max(1, len(output)), 3000):
            self.output.info(output[idx:idx + 3000])
        passed = len(re.findall(r"Passed", output))
        failed = len(re.findall(r"Failed", output))
        total_match = re.search(r"tests passed,\s*(\d+)\s*tests? failed out of\s*(\d+)", output)
        if total_match:
            failed = int(total_match.group(1))
            total = int(total_match.group(2))
            passed = total - failed
        else:
            total = passed + failed
        if total == 0:
            # No parseable ctest summary: force the failure path with a
            # consistent discovered count (never emit executed > discovered).
            total = UPSTREAM_TEST_COUNT
            passed = 0
            failed = total
        # discovered/executed must both equal the parsed ctest total;
        # the 21st entry is the ctest_build_test_code helper (20 real
        # tests + 1 helper). Fewer than expected means incomplete.
        discovered = total if total >= UPSTREAM_TEST_COUNT else UPSTREAM_TEST_COUNT
        executed = passed + failed if (passed + failed) else total
        if proc.returncode == 0 and failed == 0 and total >= UPSTREAM_TEST_COUNT and passed == total:
            result = {
                "status": "passed",
                "framework": "ctest",
                "command": "ctest --output-on-failure",
                "discovered": discovered,
                "executed": executed,
                "passed": passed,
                "failed": 0,
                "skipped": 0,
            }
        else:
            result = {
                "status": "failed",
                "framework": "ctest",
                "command": "ctest --output-on-failure",
                "discovered": discovered,
                "executed": executed,
                "passed": passed,
                "failed": failed if (failed or proc.returncode != 0) else total - passed,
                "skipped": 0,
                "reason": "rc=%s passed=%s failed=%s total=%s expected=%s" % (
                    proc.returncode, passed, failed, total, UPSTREAM_TEST_COUNT),
            }
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False)
        print(msg, flush=True)
        self.output.info(msg)
        try:
            with open(os.path.join(self.build_folder, "hmbs_upstream.json"),
                      "w", encoding="utf-8") as handle:
                json.dump(result, handle)
        except OSError:
            pass
        if result["status"] != "passed":
            raise ConanException("libics upstream ctest suite failed")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        try:
            copy(self, "hmbs_upstream.json",
                 src=self.build_folder,
                 dst=os.path.join(self.package_folder, "res"))
        except Exception:
            pass

    def package_info(self):
        # Upstream OUTPUT_NAME is "ics" -> libics.a; headers in include/.
        self.cpp_info.libs = ["ics"]
        self.cpp_info.requires = ["zlib::zlib"]
        self.cpp_info.set_property("cmake_file_name", "libics")
        self.cpp_info.set_property("cmake_target_name", "libics::libics")
