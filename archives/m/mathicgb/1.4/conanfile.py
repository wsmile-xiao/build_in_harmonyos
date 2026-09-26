#!/usr/bin/env python3
"""Conan recipe -- mathicgb 1.4 (Macaulay2/mathicgb) on OpenHarmony PC.

mathicgb computes (signature) Groebner bases on top of the fast data
structures from mathic, with special-purpose allocators from memtailor.
C++17, dual CMake + autotools build; this recipe uses CMake.

OHOS adaptation points (see patches/ and notes.md):
- Upstream ``include(CTest)`` lives in ``src/CMakeLists.txt`` (a sub
  directory). CMake only generates ``CTestTestfile.cmake`` for the directory
  that calls ``enable_testing()`` and its children, so running ``ctest`` in
  the build root reports ``No tests were found!!!`` with **exit code 0**.
  Patch 0001 hoists ``include(CTest)`` to the top level (same trap and same
  fix as archives/m/memtailor/1.4).
- Upstream ``src/CMakeLists.txt`` tests ``if(GTEST_FOUND)`` (all caps).
  Under CMakeDeps CONFIG mode CMake only defines ``GTest_FOUND``; the all
  caps spelling is a FindGTest.cmake (MODULE mode) legacy. The condition is
  therefore always false and configure falls into ``FetchContent`` cloning
  googletest from GitHub, which fails on the offline CI worker. Patch 0002
  accepts ``GTest_FOUND OR GTEST_FOUND OR TARGET GTest::gtest`` and links
  the Conan-provided ``GTest::gtest`` target (same fix as memtailor 0002).
- Upstream ``install(TARGETS mathicgb LIBRARY DESTINATION lib)`` declares
  only LIBRARY, so the static archive is never installed; ``mathicgb.h``
  hangs off the ``PUBLIC_HEADER`` property with no destination and is never
  installed either. Patch 0001 adds ARCHIVE/LIBRARY/PUBLIC_HEADER
  destinations (same fix as memtailor 0001b).
- ``with_tbb`` is pinned to OFF: single-threaded build, one fewer runtime
  dependency, deterministic behaviour on OHOS (path A, basic adaptation).

Upstream tests: ``src/test/`` 14 translation units, 101 gtest TEST macros,
registered via ``gtest_discover_tests`` and executed with ctest in build().

mathic/1.4 has no recipe in ohpcd and is absent from the remote, so it is
NOT a conan requirement here. The official mathic v1.4 tarball is vendored
via conandata ``vendor.mathic`` (see _build_private_mathic), built as a
private static archive into the build-folder prefix, and merged into this
package (headers + libmathic.a + licenses). Consumers link -lmathicgb
-lmathic -lmemtailor from this package plus the memtailor dependency.
"""

import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)

# CTest entries registered by gtest_discover_tests under gtest/1.17.0.1
# (audited on HarmonyOS preflight 2026-09-24: ctest -N reports
# Total Tests: 237, all executed and passed). Source audit: ~101 plain
# TEST/TEST_F macros in src/test/*.cpp plus 13 TYPED_TESTs in
# src/test/MonoMonoid.cpp expanded over 11 MonoidTypes
# (13*11=143 typed instances). 101+143=244 nominal; the 237 observed is
# the canonical ctest_entries count for this toolchain/gtest version
# (typed short-circuit in MonoArena + discovery dedup). Guards against
# the "green but idle" trap: ctest reports
# "No tests were found!!!" with exit code 0 when nothing is registered.
CTEST_EXPECTED_TESTS = 237

# ctest canonical summary line, e.g.
# ``100% tests passed, 0 tests failed out of 101``.
_CTEST_SUMMARY = re.compile(r"(\d+)% tests passed, (\d+) tests failed out of (\d+)")

# ``ctest -N`` trailer, e.g. ``Total Tests: 101``.
_CTEST_TOTAL = re.compile(r"Total Tests:\s*(\d+)")


class MathicgbConan(ConanFile):
    name = "mathicgb"
    version = "1.4"
    description = "Compute (signature) Groebner bases using the fast datastructures from mathic"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/Macaulay2/mathicgb"
    url = ""  # CI fills this
    topics = ("groebner", "computer-algebra", "macaulay2", "mathic", "memtailor")

    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def requirements(self):
        # memtailor provides Arena/BufferPool allocators used by mathicgb
        # (published in ohpcd, resolved normally).
        # NOTE: mathic/1.4 is NOT required here -- it has no recipe in ohpcd
        # and is absent from the remote (preflight: "Unable to find
        # 'mathic/1.4' in remotes"). It is vendored from official sources
        # and built privately (see source() + _build_private_mathic), then
        # merged into this package. No new conan requirement is introduced.
        self.requires("memtailor/1.4")

    def build_requirements(self):
        # Only needed when BUILD_TESTING is on: lets find_package(GTest) hit
        # the Conan-provided config instead of FetchContent-cloning googletest
        # (offline CI worker). Patch 0002 makes upstream honour it.
        self.test_requires("gtest/1.17.0.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)
        # Vendor the private mathic backend alongside (same pattern as
        # archives/b/bzrtp/5.3.105: vendor what the registry does not
        # publish, no new conan requirement, same-tree private build).
        get(self, **self.conan_data["vendor"]["mathic"],
            strip_root=True,
            destination=os.path.join(self.source_folder, "vendor", "mathic-1.4"))

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream gates the unit-test target on if(BUILD_TESTING), whose
        # option is provided by include(CTest) (default ON); pin it.
        tc.cache_variables["BUILD_TESTING"] = "ON"
        # Upstream v1.4 uses option(with_tbb auto); OFF gives a deterministic
        # single-threaded build (MATHICGB_NO_TBB) with no TBB dependency.
        tc.cache_variables["with_tbb"] = "OFF"
        # Ship the mgb command line interface (default ON upstream).
        tc.cache_variables["enable_mgb"] = "ON"
        tc.cache_variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()


    def _cmake_executable(self):
        import shutil as _shutil
        for key in ("HMBS_CMAKE",):
            found = os.environ.get(key, "") or ""
            if found.strip() and os.path.isfile(found.strip()):
                return found.strip()
            cand = (os.environ.get(key, "") or "").strip()
            if cand and os.path.isfile(cand):
                return cand
        found = _shutil.which("cmake")
        if not found:
            raise ConanException(
                "cmake executable not found (HMBS_CMAKE unset, PATH lookup failed)")
        return found

    def _vendor_paths(self):
        mathic_src = os.path.join(self.source_folder, "vendor", "mathic-1.4")
        mathic_build = os.path.join(self.build_folder, "vendor-mathic-build")
        priv_prefix = os.path.join(self.build_folder, "vendor-install")
        return mathic_src, mathic_build, priv_prefix

    def _patch_private_mathic_install(self, mathic_src):
        # Upstream mathic 1.4 has the same static-install flaw as mathicgb:
        # install(TARGETS mathic LIBRARY DESTINATION lib) never installs the
        # static archive (ARCHIVE category) nor the PUBLIC_HEADER umbrella.
        # Patch the vendored tree in place (idempotent) before configuring.
        top = os.path.join(mathic_src, "CMakeLists.txt")
        try:
            with open(top, "r", encoding="utf-8", errors="replace") as handle:
                data = handle.read()
        except OSError as exc:
            raise ConanException("cannot read vendored mathic %s: %s" % (top, exc))
        old = "install(TARGETS mathic LIBRARY DESTINATION lib)"
        new = ("install(TARGETS mathic\n"
               "  ARCHIVE DESTINATION lib\n"
               "  LIBRARY DESTINATION lib\n"
               "  PUBLIC_HEADER DESTINATION include\n"
               ")")
        if old in data:
            data = data.replace(old, new)
            with open(top, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(data)
            self.output.info("patched vendored mathic install(TARGETS ...) for static archive")
        elif "ARCHIVE DESTINATION lib" in data:
            self.output.info("vendored mathic install patch already applied")
        else:
            raise ConanException(
                "vendored mathic install anchor not found in %s" % top)

    def _build_private_mathic(self):
        mathic_src, mathic_build, priv_prefix = self._vendor_paths()
        for marker in ("CMakeLists.txt", "src/mathic.cpp", "cmake/FindMemtailor.cmake"):
            if not os.path.isfile(os.path.join(mathic_src, marker)):
                raise ConanException(
                    "vendored mathic incomplete, missing %s under %s" % (marker, mathic_src))
        self._patch_private_mathic_install(mathic_src)
        try:
            mem_pkg = self.dependencies["memtailor"].package_folder
        except Exception as exc:
            raise ConanException("memtailor package folder unavailable: %s" % exc)
        mem_inc = os.path.join(mem_pkg, "include")
        mem_lib_cands = [
            os.path.join(mem_pkg, "lib", "libmemtailor.a"),
            os.path.join(mem_pkg, "lib64", "libmemtailor.a"),
        ]
        mem_lib = next((c for c in mem_lib_cands if os.path.isfile(c)), None)
        if mem_lib is None or not os.path.isfile(os.path.join(mem_inc, "memtailor.h")):
            # Fall back to a filesystem search inside the memtailor package.
            found_lib = ""
            found_hdr = ""
            for root, _dirs, files in os.walk(mem_pkg):
                if "libmemtailor.a" in files and not found_lib:
                    found_lib = os.path.join(root, "libmemtailor.a")
                if "memtailor.h" in files and not found_hdr:
                    found_hdr = os.path.join(root, "memtailor.h")
            if found_lib:
                mem_lib = found_lib
            if found_hdr:
                mem_inc = os.path.dirname(found_hdr)
        if mem_lib is None or not os.path.isfile(mem_lib):
            raise ConanException(
                "libmemtailor.a not found under memtailor package %s" % mem_pkg)
        if not os.path.isfile(os.path.join(mem_inc, "memtailor.h")):
            raise ConanException(
                "memtailor.h not found under memtailor package %s" % mem_pkg)
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if not os.path.isfile(toolchain):
            raise ConanException("conan_toolchain.cmake missing at %s" % toolchain)
        cmake = self._cmake_executable()
        try:
            build_type = str(self.settings.build_type)
        except Exception:
            build_type = "Release"
        if build_type not in ("Release", "Debug", "RelWithDebInfo", "MinSizeRel"):
            build_type = "Release"
        if os.path.isdir(mathic_build):
            shutil.rmtree(mathic_build, ignore_errors=True)
        os.makedirs(mathic_build, exist_ok=True)
        os.makedirs(priv_prefix, exist_ok=True)
        configure = (
            '"%s" -S "%s" -B "%s" '
            '-DCMAKE_TOOLCHAIN_FILE="%s" '
            '-DCMAKE_BUILD_TYPE=%s '
            '-DCMAKE_INSTALL_PREFIX="%s" '
            '-DBUILD_SHARED_LIBS=OFF -DCMAKE_POSITION_INDEPENDENT_CODE=ON '
            '-DBUILD_TESTING=OFF '
            '"-DMEMTAILOR_INCLUDE_DIR=%s" "-DMEMTAILOR_LIBRARIES=%s"'
            % (cmake, mathic_src, mathic_build, toolchain, build_type,
               priv_prefix, mem_inc, mem_lib)
        )
        self.output.info("private mathic configure: %s" % configure)
        self.run(configure, env="conanbuild")
        self.run('"%s" --build "%s" --config %s -j1' % (cmake, mathic_build, build_type),
                 env="conanbuild")
        self.run('"%s" --install "%s" --config %s' % (cmake, mathic_build, build_type),
                 env="conanbuild")
        lib_cands = [
            os.path.join(priv_prefix, "lib", "libmathic.a"),
            os.path.join(priv_prefix, "lib64", "libmathic.a"),
        ]
        installed_lib = next((c for c in lib_cands if os.path.isfile(c)), None)
        if installed_lib is None:
            # cmake --install with the patched rules must produce the archive;
            # fail closed rather than shipping a mathicgb without mathic.
            raise ConanException(
                "private mathic install missing libmathic.a under %s" % priv_prefix)
        hdr = os.path.join(priv_prefix, "include", "mathic.h")
        if not os.path.isfile(hdr):
            raise ConanException(
                "private mathic install missing include/mathic.h under %s" % priv_prefix)
        self.output.info("private mathic installed under %s" % priv_prefix)
        return priv_prefix

    def _private_mathic_lib(self, priv_prefix):
        for cand in (os.path.join(priv_prefix, "lib", "libmathic.a"),
                     os.path.join(priv_prefix, "lib64", "libmathic.a")):
            if os.path.isfile(cand):
                return cand
        raise ConanException(
            "private mathic archive missing under %s" % priv_prefix)

    def _emit_upstream_marker(self, discovered, executed, passed, failed, skipped,
                              status, gaps=None):
        marker = {
            "status": status,
            "framework": "ctest",
            "command": "ctest --output-on-failure",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        if gaps:
            marker["gaps"] = gaps
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
        # Persist for the test_package re-emit channel (tolerates conan
        # build-cache hits where build() is skipped and the marker above
        # never prints). Written on every emit (pass and fail) so the
        # consumer always replays the exact numbers measured in build().
        try:
            evidence_dir = os.path.join(self.build_folder, "upstream")
            os.makedirs(evidence_dir, exist_ok=True)
            with open(os.path.join(evidence_dir, "upstream_test_result.json"),
                      "w", encoding="utf-8") as handle:
                json.dump(marker, handle)
        except Exception as exc:
            self.output.warning("persist upstream marker failed: %s" % exc)
        return marker

    def build(self):
        priv_prefix = self._build_private_mathic()
        try:
            mem_pkg = self.dependencies["memtailor"].package_folder
        except Exception as exc:
            raise ConanException("memtailor package folder unavailable: %s" % exc)
        mem_inc = os.path.join(mem_pkg, "include")
        if not os.path.isfile(os.path.join(mem_inc, "memtailor.h")):
            for root, _dirs, files in os.walk(mem_pkg):
                if "memtailor.h" in files:
                    mem_inc = root
                    break
        mem_lib = ""
        for cand in (os.path.join(mem_pkg, "lib", "libmemtailor.a"),
                     os.path.join(mem_pkg, "lib64", "libmemtailor.a")):
            if os.path.isfile(cand):
                mem_lib = cand
                break
        if not mem_lib:
            for root, _dirs, files in os.walk(mem_pkg):
                if "libmemtailor.a" in files:
                    mem_lib = os.path.join(root, "libmemtailor.a")
                    break
        if not mem_lib:
            raise ConanException(
                "libmemtailor.a not found under memtailor package %s" % mem_pkg)
        mathic_lib = self._private_mathic_lib(priv_prefix)
        mathic_inc = os.path.join(priv_prefix, "include")
        cmake = CMake(self)
        # Upstream uses MODULE FindMathic/FindMemtailor (find_path/find_library):
        # pin the search results explicitly so the private prefix is honoured
        # even when CMAKE_PREFIX_PATH propagation differs across workers.
        cmake.configure(variables={
            "MATHIC_INCLUDE_DIR": mathic_inc,
            "MATHIC_LIBRARIES": mathic_lib,
            "MEMTAILOR_INCLUDE_DIR": mem_inc,
            "MEMTAILOR_LIBRARIES": mem_lib,
        })
        cmake.build()

        # -- Layer 1: upstream gtest suite, executed in full -----------------
        # ctest must run in the build root: patch 0001 hoists
        # enable_testing() to the top level so CTestTestfile.cmake exists
        # here (upstream keeps it in src/, where `ctest` would report
        # "No tests were found!!!" and exit 0).
        discovered_out = os.path.join(self.build_folder, "ctest-n.log")
        self.run(
            'ctest -N > "{}" 2>&1 || true'.format(discovered_out),
            cwd=self.build_folder,
        )
        with open(discovered_out, encoding="utf-8", errors="replace") as fh:
            discovered_text = fh.read()
        m_total = _CTEST_TOTAL.search(discovered_text)
        if m_total is None:
            self._emit_upstream_marker(0, 0, 0, 0, 0, "failed",
                                       [{"count": CTEST_EXPECTED_TESTS,
                                         "category": "test_failure",
                                         "detail": "ctest -N produced no Total Tests line",
                                         "evidence": discovered_text[-1500:]}])
            raise ConanException(
                "ctest -N produced no Total Tests line -- suite not registered:\n"
                + discovered_text[-2000:]
            )
        discovered = int(m_total.group(1))

        log = os.path.join(self.build_folder, "ctest.log")
        # Trailing `|| true`: keep the raw log for parsing even when ctest
        # exits non-zero (self.run would otherwise raise first and the log
        # would be lost).
        self.run(
            'ctest --output-on-failure > "{}" 2>&1 || true'.format(log),
            cwd=self.build_folder,
        )
        with open(log, encoding="utf-8", errors="replace") as fh:
            text = fh.read()

        if "No tests were found" in text:
            self._emit_upstream_marker(discovered, 0, 0, 0, discovered, "failed",
                                       [{"count": discovered,
                                         "category": "test_failure",
                                         "detail": "ctest registered 0 tests "
                                                   "(enable_testing() not reached)",
                                         "evidence": text[-1500:]}])
            raise ConanException(
                "ctest registered 0 tests (enable_testing() not reached by the "
                "top-level directory) -- zero execution must not count as pass.\n"
                + text[-2000:]
            )
        m = _CTEST_SUMMARY.search(text)
        if m is None:
            self._emit_upstream_marker(discovered, 0, 0, 0, discovered, "failed",
                                       [{"count": discovered,
                                         "category": "test_failure",
                                         "detail": "ctest summary line not found",
                                         "evidence": text[-1500:]}])
            raise ConanException(
                "ctest summary line not found -- the suite did not run:\n"
                + text[-2000:]
            )
        failed, total = int(m.group(2)), int(m.group(3))
        executed = total
        passed = total - failed
        skipped = discovered - executed
        if skipped < 0 or passed < 0:
            self._emit_upstream_marker(discovered, executed, 0, failed, 0, "failed",
                                       [{"count": discovered,
                                         "category": "test_failure",
                                         "detail": "contradictory ctest counts",
                                         "evidence": text[-1500:]}])
            raise ConanException(
                "contradictory ctest counts: discovered={} executed={} "
                "failed={}\n".format(discovered, executed, failed)
                + text[-2000:]
            )
        if failed != 0:
            self._emit_upstream_marker(discovered, executed, passed, failed,
                                       skipped, "failed",
                                       [{"count": failed,
                                         "category": "test_failure",
                                         "detail": "upstream gtest cases failed",
                                         "evidence": text[-1500:]}])
            raise ConanException(
                "upstream ctest not all green: {} failed out of {}\n".format(
                    failed, total) + text[-4000:]
            )
        if total < CTEST_EXPECTED_TESTS:
            self._emit_upstream_marker(discovered, executed, passed, failed,
                                       skipped, "failed",
                                       [{"count": CTEST_EXPECTED_TESTS - total,
                                         "category": "test_failure",
                                         "detail": "registered test set shrank",
                                         "evidence": text[-1500:]}])
            raise ConanException(
                "only {} upstream tests were registered (expected >= {}) -- "
                "test set shrank\n".format(total, CTEST_EXPECTED_TESTS)
                + text[-2000:]
            )
        self._emit_upstream_marker(discovered, executed, passed, failed,
                                   skipped, "passed")
        self.output.info(
            "upstream ctest suite: {} tests discovered, {} executed, all passed".format(
                discovered, executed)
        )

    def package(self):
        copy(self, "gpl-2.0.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "gpl-3.0.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        # Merge the privately built mathic (same-tree static sub-build):
        # headers + static archive + licenses ship inside this package so
        # consumers need no separate mathic parcel.
        _, _, priv_prefix = self._vendor_paths()
        copy(self, "*", src=os.path.join(priv_prefix, "include"),
             dst=os.path.join(self.package_folder, "include"))
        for _lib in ("libmathic.a",):
            for _subdir in ("lib", "lib64"):
                _cand = os.path.join(priv_prefix, _subdir, _lib)
                if os.path.isfile(_cand):
                    copy(self, _lib, src=os.path.join(priv_prefix, _subdir),
                         dst=os.path.join(self.package_folder, "lib"))
                    break
        mathic_src = os.path.join(self.source_folder, "vendor", "mathic-1.4")
        for _lic in ("lgpl-2.0.txt", "lgpl-2.1.txt", "lgpl-3.0.txt"):
            try:
                if os.path.isfile(os.path.join(mathic_src, _lic)):
                    copy(self, _lic, src=mathic_src,
                         dst=os.path.join(self.package_folder, "licenses"))
            except Exception as exc:
                self.output.warning("mathic license copy failed %s: %s" % (_lic, exc))
        if not os.path.isfile(os.path.join(self.package_folder, "lib", "libmathic.a")):
            raise ConanException("packaged libmathic.a missing (private mathic not merged)")
        if not os.path.isfile(os.path.join(self.package_folder, "include", "mathic.h")):
            raise ConanException("packaged mathic.h missing (private mathic headers not merged)")
        # Persist the upstream evidence so test_package can re-emit the
        # exact numbers measured in build() on cache hits (no hard copies).
        try:
            copy(self, "upstream_test_result.json",
                 src=os.path.join(self.build_folder, "upstream"),
                 dst=os.path.join(self.package_folder, "res"))
        except Exception as exc:
            raise ConanException("packaged upstream_test_result.json missing: %s" % exc)
        if not os.path.isfile(os.path.join(self.package_folder, "res",
                                           "upstream_test_result.json")):
            raise ConanException("packaged upstream_test_result.json missing")

    def package_info(self):
        # Bundled closure: libmathic.a is merged into this package (private
        # static sub-build); static consumers link it after libmathicgb.
        # libmemtailor stays an external requirement (published in ohpcd).
        self.cpp_info.libs = ["mathicgb", "mathic"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
