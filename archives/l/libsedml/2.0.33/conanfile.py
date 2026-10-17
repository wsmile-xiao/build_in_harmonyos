#!/usr/bin/env python3
"""Conan recipe for libsedml 2.0.33 (CMake, bare-cmake flow).

libSEDML is a C++ library for reading/writing SED-ML documents. It is built
on top of libSBML's XML layer and libNuML. Neither libSBML nor libNuML has
been published to the ohpcd registry yet, so this recipe builds the exact
upstream dependency sources (same family, same maintainer) from their
official release archives into a private prefix inside the build folder and
links them statically. No conan `requires` are declared, so every input is
pinned by URL + sha256 in conandata.yml.

Vendored (official sources, static, private to this build):
  - expat 2.7.1       (XML parser for libSBML)
  - libSBML 5.21.0    (core only, no L3 packages, no bindings, no zlib)
  - libNuML 1.1.7     (built against the vendored libSBML)

Upstream tests (tests/TestIssues.cpp, Catch, 33 cases) are built with
BUILD_TESTS=ON and executed via ctest in build(); the result is reported
with an HMBS_UPSTREAM_TEST_RESULT marker parsed from real test output.
"""

import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, export_conandata_patches, replace_in_file


class LibsedmlConan(ConanFile):
    name = "libsedml"
    version = "2.0.33"
    description = "Library for reading, writing and manipulating SED-ML files"
    license = "BSD-2-Clause"
    homepage = "https://github.com/fbergmann/libSEDML"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # Bare-cmake flow (same as libxml2/2.15.3): build dirs are managed
        # explicitly under self.build_folder, sources under self.source_folder.
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True,
            destination="libsedml-src")
        get(self, **self.conan_data["sources_expat"], strip_root=True,
            destination="vendor/expat")
        get(self, **self.conan_data["sources_libsbml"], strip_root=True,
            destination="vendor/libsbml")
        get(self, **self.conan_data["sources_libnuml"], strip_root=True,
            destination="vendor/libnuml")

    def _ohos_toolchain(self):
        # Best-effort discovery of ohos.toolchain.cmake. The official CI
        # profile (ci/conan/profiles/ohos-aarch64) is a native build and
        # sets no user_toolchain, so a missing file must NOT be fatal:
        # fall back to a generated minimal toolchain (Linux platform
        # identity + OHOS clang, see _fallback_toolchain).
        import glob
        try:
            ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain",
                               default=[], check_type=list)
        except Exception:
            ut = []
        candidates = list(ut) if ut else []
        for env_key in ("OHOS_NDK_HOME", "OHOS_SDK_HOME", "OHOS_SDK_NATIVE",
                        "OHOS_SDK_ROOT", "HMBS_OHOS_SDK", "HMBS_NDK_HOME"):
            root = os.environ.get(env_key, "")
            if not root:
                continue
            candidates.append(os.path.join(
                root, "build/cmake/ohos.toolchain.cmake"))
            candidates.append(os.path.join(
                root, "ohos/native/build/cmake/ohos.toolchain.cmake"))
            candidates.append(os.path.join(
                root, "native/build/cmake/ohos.toolchain.cmake"))
        for cand in candidates:
            if cand and os.path.isfile(cand):
                self.output.info("using ohos toolchain: %s" % cand)
                return cand
        patterns = [
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/build/cmake/ohos.toolchain.cmake",
            "/data/service/hnp/ohos-sdk*/ohos/native/build/cmake/ohos.toolchain.cmake",
            "/data/service/hnp/ohos-sdk*/native/build/cmake/ohos.toolchain.cmake",
            "/data/service/hnp/sdk/*/ohos/native/build/cmake/ohos.toolchain.cmake",
            "/opt/ohos-sdk/ohos/native/build/cmake/ohos.toolchain.cmake",
        ]
        for pat in patterns:
            try:
                globbed = sorted(glob.glob(pat))
            except Exception:
                continue
            if globbed:
                self.output.info("using ohos toolchain: %s" % globbed[-1])
                return globbed[-1]
        self.output.info("ohos.toolchain.cmake not found, generating fallback")
        return self._fallback_toolchain()

    def _fallback_toolchain(self):
        # No system ohos.toolchain.cmake on this host: generate a minimal
        # one. cmake 4.x ships no Platform/HarmonyOS module, so an
        # identity-less native configure leaves UNIX unset and old
        # upstreams take their WIN32 branch (libSBML then fails with
        # "__declspec attributes are not enabled"). Identifying as Linux
        # makes if(UNIX) hold; the compilers below are still the OHOS
        # clang pair, so the objects stay native OHOS/aarch64 binaries.
        cc, cxx = self._compilers()
        path = os.path.join(self.build_folder, "hmbs-fallback-toolchain.cmake")
        with open(path, "w", encoding="utf-8") as f:
            f.write('set(CMAKE_SYSTEM_NAME Linux)\n'
                    'set(CMAKE_SYSTEM_PROCESSOR aarch64)\n'
                    'set(CMAKE_C_COMPILER "%s")\n'
                    'set(CMAKE_CXX_COMPILER "%s")\n' % (cc, cxx))
        self.output.info("using fallback toolchain: %s" % path)
        return path

    def _cmake(self):
        # hmbs injects an absolute HMBS_CMAKE; fall back to PATH lookup.
        for key in ("HMBS_CMAKE",):
            val = os.environ.get(key, "")
            if val and os.path.isfile(val):
                return val
        which = shutil.which("cmake")
        if which:
            return which
        return "cmake"

    def _compilers(self):
        # Prefer the profile-declared compilers (official ohos-aarch64
        # profile pins /data/service/hnp/bin/clang), then CC/CXX env,
        # then HMBS-injected PATH lookup. Validates executability.
        def _pick(conf_key, env_key, fallback):
            try:
                val = self.conf.get(conf_key, default="", check_type=str)
            except Exception:
                val = ""
            if val and os.path.isfile(val) and os.access(val, os.X_OK):
                return val
            env_val = os.environ.get(env_key, "")
            if env_val:
                if os.path.isfile(env_val) and os.access(env_val, os.X_OK):
                    return env_val
                found = shutil.which(env_val)
                if found:
                    return found
                return env_val
            found = shutil.which(fallback)
            if found:
                return found
            return fallback
        cc = _pick("tools.build:compiler_executables:c", "CC", "clang")
        cxx = _pick("tools.build:compiler_executables:cpp", "CXX", "clang++")
        return cc, cxx

    def _llvm_tools(self, toolchain):
        # OHOS SDK llvm/bin ships llvm-ar but no llvm-ranlib, while
        # ohos.toolchain.cmake points CMAKE_RANLIB at the missing
        # llvm-ranlib. CMake static-archive creation is
        # `<AR> qc ... && <RANLIB> <lib>`, so every .o compiles and the
        # .a step fails with the content-free message:
        #   Error running link command: no such file or directory
        # (knowledge E385; brotli/OpenCV/SuiteSparse/wildmidi/assimp same
        # pit). Resolve both tools explicitly and pass them as
        # -DCMAKE_AR/-DCMAKE_RANLIB. When no llvm-ranlib exists anywhere,
        # fall back to a `llvm-ar s` shim (equivalent to ranlib).
        ar = ""
        ranlib = ""
        dirs = []
        try:
            sdk_bin = os.path.normpath(os.path.join(
                os.path.dirname(toolchain), "..", "..", "llvm", "bin"))
            dirs.append(sdk_bin)
        except Exception:
            pass
        try:
            cc, _ = self._compilers()
            if cc and os.path.dirname(cc):
                dirs.append(os.path.dirname(cc))
        except Exception:
            pass
        dirs += ["/data/service/hnp/bin",
                 "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18"
                 "/ohos/native/llvm/bin"]

        def _find(names):
            for d in dirs:
                for n in names:
                    try:
                        cand = os.path.join(d, n)
                    except Exception:
                        continue
                    if cand and os.path.isfile(cand):
                        return cand
            for n in names:
                w = shutil.which(n)
                if w:
                    return w
            return ""

        ar = _find(["llvm-ar"])
        ranlib = _find(["llvm-ranlib"])
        if not ranlib and ar:
            shim = os.path.join(self.build_folder, "llvm-ranlib-shim")
            try:
                with open(shim, "w", encoding="utf-8", newline="\n") as f:
                    f.write('#!/bin/sh\nexec "%s" s "$@"\n' % ar)
                try:
                    os.chmod(shim, 0o755)
                except Exception:
                    pass
                self.output.info("llvm-ranlib missing, using shim: %s -> %s"
                                 % (shim, ar))
                ranlib = shim
            except OSError as e:
                self.output.warning("create ranlib shim failed: %s" % e)
        self.output.info("llvm tools: AR=%s RANLIB=%s"
                         % (ar or "(toolchain default)",
                            ranlib or "(toolchain default)"))
        return ar, ranlib

    def _ensure_writable_tmp(self):
        # HMBS readonly_tmp (E002): /tmp is erofs read-only on OHOS; cmake,
        # clang and /bin/sh fall back to /tmp for temp files unless TMPDIR
        # points at a writable dir. HMBS injects TMPDIR/TMP/TEMP, but make
        # sure the directory really exists and is writable, then export it
        # to this process so every self.run()/subprocess child inherits it.
        # Only the temp root is relocated; no test is skipped or removed.
        cands = []
        for _k in ("TMPDIR", "TMP", "TEMP"):
            try:
                _v = os.environ.get(_k, "")
            except Exception:
                _v = ""
            if _v:
                cands.append(_v)
        try:
            _home = os.environ.get("HOME", "")
        except Exception:
            _home = ""
        if _home:
            cands.append(os.path.join(_home, "tmp"))
        try:
            if self.build_folder:
                cands.append(os.path.join(str(self.build_folder),
                                          "hmbs-tmp"))
        except Exception:
            pass
        chosen = ""
        for _c in cands:
            try:
                os.makedirs(_c, exist_ok=True)
                _probe = os.path.join(_c, ".hmbs_write_probe")
                with open(_probe, "w", encoding="utf-8") as _f:
                    _f.write("ok")
                try:
                    os.remove(_probe)
                except Exception:
                    pass
                chosen = _c
                break
            except Exception:
                continue
        if chosen:
            for _k in ("TMPDIR", "TMP", "TEMP", "GOTMPDIR"):
                try:
                    os.environ[_k] = chosen
                except Exception:
                    pass
            self.output.info("writable tmp: %s" % chosen)
        else:
            self.output.warning("no writable tmp dir found among: %s"
                                % cands)
        return chosen

    def _base_defs(self, toolchain):
        return [
            '-DCMAKE_TOOLCHAIN_FILE="%s"' % toolchain,
            "-DCMAKE_BUILD_TYPE=%s" % self.settings.build_type,
            "-DCMAKE_INSTALL_LIBDIR=lib",
            "-DCMAKE_POSITION_INDEPENDENT_CODE=ON",
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
        ]

    def _dep_prefix(self):
        return os.path.join(self.build_folder, "deps")

    def _guard_findzlib(self, path):
        # libSBML 5.21.0 runs find_package(ZLIB QUIET) unconditionally,
        # then calls check_library_exists() even when ZLIB_LIBRARY is
        # NOTFOUND (no system zlib on this host). CMake 4.x turns that
        # into a hard configure error. Guard the probe so a missing zlib
        # degrades to "not found" instead of aborting configure.
        # No functional change: we build WITH_ZLIB=OFF, zlib is never
        # linked; the probe result is unused in that case.
        if not os.path.isfile(path):
            return
        with open(path, encoding="utf-8", errors="replace") as f:
            content = f.read()
        old = 'check_library_exists("${LIBZ_CMAKE_PATH}" "gzopen" "" LIBZ_FOUND_SYMBOL)'
        if old not in content:
            return
        replace_in_file(
            self, path, old,
            'if(LIBZ_CMAKE_PATH)\n    %s\n    endif()' % old)

    def _relax_findexpat(self, path):
        # libSBML/libNuML/libSEDML share the same FindEXPAT.cmake probe:
        # after finding headers+archive it try-compiles a trivial
        # CHECK_C_SOURCE_COMPILES program and calls message(FATAL_ERROR)
        # when both variants fail. On the OHOS toolchain that probe is
        # fragile (identical probe passed for libSBML minutes earlier in
        # the same CI worker with the same archive, yet fails when run
        # indirectly via sbml-static-config's find_dependency during the
        # libNuML/libSEDML configures: CI #48914, "EXPAT_EXPAT_TEST /
        # TEST2 - Failed"). The probe only decides whether the
        # XML_STATIC compile definition is needed; on non-Windows
        # targets expat.h leaves XMLIMPORT empty with or without it, so
        # continuing without the flag is functionally neutral. Keep the
        # attempt (a genuine pass still sets XML_STATIC); downgrade only
        # the fatal abort to a warning so a probe false-negative cannot
        # kill configure. A truly unlinkable archive still fails loudly
        # at the real build link step.
        if not os.path.isfile(path):
            return
        # Do not touch expat's own build helper: this walk runs before the
        # vendored expat configure, and any edit there breaks the very
        # first cmake step (preflight 2026-09-16: Parse error at
        # CMakeModules/FindEXPAT.cmake:189, unterminated string).
        norm = path.replace("\\", "/")
        if "/vendor/expat/" in norm:
            return
        with open(path, encoding="utf-8", errors="replace") as f:
            content = f.read()
        old = 'message(FATAL_ERROR "Unable to compile a test executable against expat with'
        if old not in content:
            return
        # Quote-balanced downgrade: exactly one opening quote, same as the
        # original prefix, so the untouched suffix (closing \'")\') still
        # parses. Extra injected quotes previously produced the
        # "Function missing ending ... unterminated string" parse error.
        new = 'message(WARNING "HMBS expat probe continuing without XML_STATIC: Unable to compile a test executable against expat with'
        replace_in_file(self, path, old, new)

    def _enable_c_language(self, path):
        # libNuML 1.1.7 and libSEDML 2.0.33 declare
        # project(... LANGUAGES CXX) but their FindEXPAT.cmake runs
        # enable_language(C) + CHECK_C_SOURCE_COMPILES lazily during
        # find_package. The late C enablement mishandles the OHOS
        # toolchain and both EXPAT try-compiles fail with the fatal
        # "Unable to compile a test executable against expat"
        # (CI #48898; libSBML itself declares C and passed the same
        # test). Enabling C from the start lets the toolchain configure
        # both compilers up front; no functional change.
        if not os.path.isfile(path):
            return
        with open(path, encoding="utf-8", errors="replace") as f:
            content = f.read()
        old = "LANGUAGES CXX)"
        if old not in content:
            return
        replace_in_file(self, path, old, "LANGUAGES C CXX)")

    def build(self):
        self._ensure_writable_tmp()
        cmake = self._cmake()
        toolchain = self._ohos_toolchain()
        deps = self._dep_prefix()
        _ar, _ranlib = self._llvm_tools(toolchain)
        _extra = []
        if _ar:
            _extra.append('-DCMAKE_AR="%s"' % _ar)
        if _ranlib:
            _extra.append('-DCMAKE_RANLIB="%s"' % _ranlib)
        base = " ".join(self._base_defs(toolchain) + _extra)

        expat_src = os.path.join(self.source_folder, "vendor", "expat")
        sbml_src = os.path.join(self.source_folder, "vendor", "libsbml")
        numl_src = os.path.join(self.source_folder, "vendor", "libnuml",
                                "libnuml")
        sedml_src = os.path.join(self.source_folder, "libsedml-src")

        # libSBML's FindZLIB.cmake aborts configure on CMake 4.x when no
        # system zlib exists (WITH_ZLIB=OFF still runs the QUIET probe).
        # Guard every vendored copy before configuring anything.
        for _root, _dirs, _files in os.walk(self.source_folder):
            if "FindZLIB.cmake" in _files:
                self._guard_findzlib(os.path.join(_root, "FindZLIB.cmake"))
            if "FindEXPAT.cmake" in _files:
                self._relax_findexpat(os.path.join(_root, "FindEXPAT.cmake"))
        # NuML/SEDML are CXX-only projects whose FindEXPAT enables C
        # lazily; enable C up front for the OHOS toolchain (see helper).
        self._enable_c_language(os.path.join(numl_src, "CMakeLists.txt"))
        self._enable_c_language(os.path.join(sedml_src, "CMakeLists.txt"))

        # 1. expat (static, no tests/tools/examples)
        b_expat = os.path.join(self.build_folder, "build-expat")
        self.run('%s -B "%s" -S "%s" %s '
                 '-DCMAKE_INSTALL_PREFIX="%s" '
                 '-DBUILD_SHARED_LIBS=OFF -DEXPAT_SHARED_LIBS=OFF '
                 '-DEXPAT_BUILD_TESTS=OFF -DEXPAT_BUILD_EXAMPLES=OFF '
                 '-DEXPAT_BUILD_TOOLS=OFF'
                 % (cmake, b_expat, expat_src, base, deps))
        self.run('%s --build "%s"' % (cmake, b_expat))
        self.run('%s --install "%s"' % (cmake, b_expat))

        # 2. libSBML core only (static, expat parser, no compression,
        #    no bindings, no examples, no own test suite).
        b_sbml = os.path.join(self.build_folder, "build-sbml")
        self.run('%s -B "%s" -S "%s" %s '
                 '-DCMAKE_INSTALL_PREFIX="%s" '
                 '-DBUILD_SHARED_LIBS=OFF '
                 '-DWITH_EXPAT=ON -DWITH_LIBXML=OFF -DWITH_XERCES=OFF '
                 '-DWITH_ZLIB=OFF -DWITH_BZIP2=OFF '
                 '-DWITH_SWIG=OFF -DWITH_STABLE_PACKAGES=OFF '
                 '-DWITH_ALL_PACKAGES=OFF -DWITH_EXAMPLES=OFF -DWITH_CHECK=OFF '
                 '-DEXPAT_INCLUDE_DIR="%s/include" '
                 '-DEXPAT_LIBRARY="%s/lib/libexpat.a"'
                 % (cmake, b_sbml, sbml_src, base, deps, deps, deps))
        self.run('%s --build "%s"' % (cmake, b_sbml))
        self.run('%s --install "%s"' % (cmake, b_sbml))

        # 3. libNuML (static) against the vendored libSBML.
        # Pass the vendored expat explicitly (same values that made the
        # libSBML configure succeed) instead of relying on
        # LIBNUML_DEPENDENCY_DIR search: the SBML config pulls
        # find_package(EXPAT) and its try-compile must link the exact
        # static archive under the OHOS toolchain.
        b_numl = os.path.join(self.build_folder, "build-numl")
        env_numl = ("LIBSBML_DIR=\"%s\" EXPAT_DIR=\"%s\" " % (deps, deps))
        self.run(env_numl + '%s -B "%s" -S "%s" %s '
                 '-DCMAKE_INSTALL_PREFIX="%s" '
                 '-DBUILD_SHARED_LIBS=OFF -DLIBNUML_SHARED=OFF '
                 '-DWITH_SWIG=OFF -DWITH_EXAMPLES=OFF -DWITH_CHECK=OFF '
                 '-DLIBNUML_DEPENDENCY_DIR="%s" '
                 '-DCMAKE_PREFIX_PATH="%s" '
                 '-DEXPAT_INCLUDE_DIR="%s/include" '
                 '-DEXPAT_LIBRARY="%s/lib/libexpat.a"'
                 % (cmake, b_numl, numl_src, base, deps, deps, deps,
                    deps, deps))
        self.run('%s --build "%s"' % (cmake, b_numl))
        self.run('%s --install "%s"' % (cmake, b_numl))

        # 4. libSEDML itself, with upstream tests enabled.
        # One-line source tweak (same idiom as the merged ldns recipe):
        # the upstream floor 2.8.12 is rejected by current CMake, lift it
        # to 3.5 (no functional change; -DCMAKE_POLICY_VERSION_MINIMUM=3.5
        # below covers the vendored projects).
        replace_in_file(
            self, os.path.join(sedml_src, "CMakeLists.txt"),
            "cmake_minimum_required(VERSION 2.8.12...3.19.0)",
            "cmake_minimum_required(VERSION 3.5...3.19.0)")
        b_sedml = os.path.join(self.build_folder, "build-sedml")
        skip_shared = "ON" if not self.options.shared else "OFF"
        env_sedml = ("LIBSBML_DIR=\"%s\" LIBNUML_DIR=\"%s\" "
                     "EXPAT_DIR=\"%s\" " % (deps, deps, deps))
        self.run(env_sedml + '%s -B "%s" -S "%s" %s '
                 '-DCMAKE_INSTALL_PREFIX="/" '
                 '-DBUILD_SHARED_LIBS=%s -DLIBSEDML_SKIP_SHARED_LIBRARY=%s '
                 '-DBUILD_TESTS=ON '
                 '-DWITH_SWIG=OFF -DWITH_EXAMPLES=OFF '
                 '-DWITH_ZLIB=OFF '
                 '-DLIBSEDML_DEPENDENCY_DIR="%s" '
                 '-DCMAKE_PREFIX_PATH="%s" '
                 '-DEXPAT_INCLUDE_DIR="%s/include" '
                 '-DEXPAT_LIBRARY="%s/lib/libexpat.a" '
                 '-DEXTRA_LIBS="%s/lib/libexpat.a" '
                 '-DEXTRA_INCLUDE_DIRS="%s/include"'
                 % (cmake, b_sedml, sedml_src, base,
                    "ON" if self.options.shared else "OFF", skip_shared,
                    deps, deps, deps, deps, deps, deps))
        self.run('%s --build "%s"' % (cmake, b_sedml))
        self._verify_sedml_archive(b_sedml)

        # Upstream test suite: ctest drives tests/test_sedml (Catch, 33 cases).
        # Streamed via self.run for the log, then re-run the binary directly
        # to capture real counts for the evidence marker.
        ctest_ok = True
        try:
            self.run('ctest --output-on-failure -C %s --test-dir "%s"'
                     % (self.settings.build_type, b_sedml))
        except Exception:
            ctest_ok = False
        self._report_upstream_tests(b_sedml, sedml_src, ctest_ok)
        if not ctest_ok:
            raise Exception("libSEDML upstream ctest suite failed")

    def _verify_sedml_archive(self, b_sedml):
        # Fail fast if the static archive that consumers link is missing,
        # and confirm it really exports the Sed* consumer symbols.
        # (Preflight evidence 2026-09-16: test_package failed with
        # `undefined symbol: SedDocument::...` for every Sed class, i.e.
        # the consumer link saw no sedml archive at all.)
        import glob as _glob
        cands = sorted(_glob.glob(os.path.join(b_sedml, "**", "*.a"),
                                  recursive=True))
        self.output.info("sedml build archives: %s"
                         % ([os.path.relpath(p, b_sedml) for p in cands]
                            if cands else "NONE"))
        want = [p for p in cands
                if os.path.basename(p) in ("libsedml-static.a",
                                           "libsedml.a")]
        if not want:
            raise Exception(
                "libsedml static archive missing in build tree "
                "(expected libsedml-static.a; found: %s)" % cands)
        arc = want[0]
        self.output.info("sedml archive: %s (%d bytes)"
                         % (arc, os.path.getsize(arc)))
        nm = (shutil.which("llvm-nm") or shutil.which("nm"))
        if nm is None:
            self.output.warning("no nm/llvm-nm available; "
                                "skipping symbol check for %s" % arc)
            return
        try:
            proc = subprocess.run([nm, "-g", arc],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, timeout=300)
            out = proc.stdout.decode("utf-8", "replace")
        except Exception as e:
            self.output.warning("symbol check failed to run: %s" % e)
            return
        if "SedDocument" not in out:
            raise Exception(
                "archive %s exports no SedDocument symbols "
                "(consumer link would fail)" % arc)
        self.output.info("archive symbol check: SedDocument present in %s"
                         % os.path.basename(arc))

    def _report_upstream_tests(self, b_sedml, sedml_src, ctest_ok):
        discovered = executed = passed = failed = skipped = 0
        status = "failed"
        try:
            test_bin = os.path.join(b_sedml, "tests", "test_sedml")
            env = dict(os.environ)
            env["srcdir"] = os.path.join(sedml_src, "tests")
            proc = subprocess.run([test_bin], stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, env=env,
                                  timeout=600)
            out = proc.stdout.decode("utf-8", "replace")
            for line in out.splitlines():
                self.output.info("test_sedml: %s" % line)
            m = re.search(r"All tests passed \((\d+) assertions in (\d+) test cases\)", out)
            if m and proc.returncode == 0:
                executed = passed = int(m.group(2))
                discovered = executed
                status = "passed"
            else:
                m2 = re.search(r"(\d+) assertions in (\d+) test cases", out)
                mf = re.search(r"(\d+) failed", out)
                if m2:
                    discovered = executed = int(m2.group(2))
                    failed = int(mf.group(1)) if mf else 1
                    passed = executed - failed
                    status = "passed" if proc.returncode == 0 and failed == 0 else "failed"
        except Exception as e:
            self.output.warning("catch re-run for evidence failed: %s" % e)
        if discovered == 0:
            # Fall back to ctest-level evidence (1 registered test).
            discovered = executed = 1
            passed = 1 if ctest_ok else 0
            failed = 0 if ctest_ok else 1
            status = "passed" if ctest_ok else "failed"
        marker = {"status": status, "framework": "ctest",
                  "command": "ctest --output-on-failure",
                  "discovered": discovered, "executed": executed,
                  "passed": passed, "failed": failed, "skipped": skipped}
        self._emit_upstream_result(marker)

    def _emit_upstream_result(self, result):
        # Dual-channel evidence: self.output.info plus a stdout-direct
        # print of the same line, then persist to the build folder so a
        # later Conan cache hit (build() skipped) can still re-emit the
        # measured result from test_package. No BOM.
        line = ("HMBS_UPSTREAM_TEST_RESULT="
                + json.dumps(result, separators=(",", ":")))
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass
        try:
            path = os.path.join(str(self.build_folder), "hmbs_upstream.json")
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(result, separators=(",", ":")))
        except OSError as e:
            self.output.warning("persist upstream evidence failed: %s" % e)

    def package(self):
        self._ensure_writable_tmp()
        cmake = self._cmake()
        b_sedml = os.path.join(self.build_folder, "build-sedml")
        self.run('%s --install "%s" --prefix "%s"'
                 % (cmake, b_sedml, self.package_folder))
        # Ship the vendored static archives alongside so consumers of the
        # static libsedml resolve sbml/numl/expat symbols. Only files that
        # were actually produced are copied (archive names differ slightly
        # between upstreams, so probe instead of assuming).
        deps_lib = os.path.join(self._dep_prefix(), "lib")
        for lib in ("libnuml-static.a", "libnuml.a",
                    "libsbml-static.a", "libsbml.a",
                    "libexpat.a"):
            if os.path.isfile(os.path.join(deps_lib, lib)):
                copy(self, lib, src=deps_lib,
                     dst=os.path.join(self.package_folder, "lib"),
                     keep_path=False)
            else:
                self.output.info("vendored lib not produced, skipping: %s" % lib)
        # Headers of vendored deps live next to sedml headers already
        # (all installed under <prefix>/include by their own install).
        for inc in ("sbml", "numl"):
            copy(self, "*.h",
                 src=os.path.join(self._dep_prefix(), "include", inc),
                 dst=os.path.join(self.package_folder, "include", inc),
                 keep_path=True)
        copy(self, "expat*.h", src=os.path.join(self._dep_prefix(), "include"),
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        # Some toolchains/GNUInstallDirs variants install to lib64 even when
        # lib is requested: fold any such archives back into lib/ so the
        # consumer link (-L lib -lsedml-static ...) always resolves.
        import glob as _pkg_glob
        pkg_lib = os.path.join(self.package_folder, "lib")
        pkg_lib64 = os.path.join(self.package_folder, "lib64")
        if os.path.isdir(pkg_lib64):
            for arc64 in _pkg_glob.glob(os.path.join(pkg_lib64, "*.a")):
                dest = os.path.join(pkg_lib, os.path.basename(arc64))
                if not os.path.isfile(dest):
                    self.output.info("folding lib64 archive into lib/: %s"
                                     % os.path.basename(arc64))
                    copy(self, os.path.basename(arc64), src=pkg_lib64,
                         dst=pkg_lib, keep_path=False)
        shipped = sorted(os.path.basename(p) for p in _pkg_glob.glob(
            os.path.join(pkg_lib, "*.a")))
        # Fallback: upstream `cmake --install` does not reliably place the
        # static archives into <package>/lib (preflight 2026-09-16: headers
        # installed, build tree held build-sedml/src/sedml/libsedml-static.a
        # 4.3MB with SedDocument symbols, yet package lib/ had only
        # libexpat.a). Copy any missing allowlisted archives straight from
        # the build tree so the consumer link always resolves. sha-pinned
        # sources are unchanged; this only changes where built files land.
        # Always sweep: top up any allowlisted archive missing from lib/
        # (sedml itself or vendored numl/sbml/expat) straight from the build
        # tree. Copies are skipped when the file already exists, so this is
        # a no-op when `cmake --install` behaved.
        import glob as _fb_glob
        allow = ("libsedml-static.a", "libsedml.a",
                 "libnuml-static.a", "libnuml.a",
                 "libsbml-static.a", "libsbml.a",
                 "libexpat.a")
        _fb_root = self.build_folder
        if _fb_root and os.path.isdir(_fb_root):
            # Skip the package folder itself if nested; only ship build
            # outputs (build-*/** and deps/**).
            for arc in _fb_glob.glob(os.path.join(_fb_root, "**", "*.a"),
                                     recursive=True):
                if arc.startswith(self.package_folder):
                    continue
                base = os.path.basename(arc)
                if base not in allow:
                    continue
                dest = os.path.join(pkg_lib, base)
                if os.path.isfile(dest):
                    continue
                self.output.info("fallback copy archive -> lib/: %s" % arc)
                copy(self, base, src=os.path.dirname(arc),
                     dst=pkg_lib, keep_path=False)
        shipped = sorted(os.path.basename(p) for p in _pkg_glob.glob(
            os.path.join(pkg_lib, "*.a")))
        self.output.info("package lib inventory: %s"
                         % (shipped if shipped else "NONE"))
        for _arc in shipped:
            _p = os.path.join(pkg_lib, _arc)
            self.output.info("  %s (%d bytes)" % (_arc, os.path.getsize(_p)))
        if not any(n in ("libsedml-static.a", "libsedml.a") for n in shipped):
            raise Exception(
                "package lib/ ships no sedml archive "
                "(found: %s); consumer link cannot succeed" % shipped)
        # Persist the measured upstream result into the package so
        # test_package can re-emit it every round even when Conan hits
        # the binary cache and build() is skipped.
        try:
            src_json = os.path.join(str(self.build_folder),
                                    "hmbs_upstream.json")
            if os.path.isfile(src_json):
                with open(src_json, "r", encoding="utf-8") as rf:
                    payload = rf.read()
                obj = json.loads(payload)
                if (not isinstance(obj, dict)
                        or int(obj.get("discovered", 0)) <= 0
                        or int(obj.get("executed", 0)) <= 0):
                    raise ValueError("discovered/executed must be > 0")
                res_dir = os.path.join(str(self.package_folder), "res")
                os.makedirs(res_dir, exist_ok=True)
                with open(os.path.join(res_dir, "hmbs_upstream.json"),
                          "w", encoding="utf-8", newline="\n") as wf:
                    wf.write(json.dumps(obj, separators=(",", ":")))
                self.output.info("package: persisted hmbs_upstream.json")
            else:
                self.output.warning(
                    "package: hmbs_upstream.json not found in build "
                    "folder; test_package cannot re-emit upstream evidence")
        except (OSError, ValueError) as e:
            self.output.warning(
                "package: persist upstream evidence failed: %s" % e)
        if self.options.shared:
            self._sign_shared_libs()

    def _sign_shared_libs(self):
        # Same treatment as libxml2/2.15.3: SDK-produced .so files need
        # re-signing with binary-sign-tool to be loadable on OHOS.
        import glob
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for so in sos:
            if os.path.islink(so):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))

    def package_info(self):
        if self.options.shared:
            self.cpp_info.libs = ["sedml"]
        else:
            # Static: sedml itself plus the vendored archives it was linked
            # against. Probe the shipped files so the list always matches
            # what package() actually installed; keep dependency order
            # (sedml -> numl -> sbml -> expat) for left-to-right resolution.
            # Probe lib/ and lib64/ (install dir varies by toolchain); log
            # both so the next preflight shows exactly what consumers see.
            import glob as _glob
            found = []
            for _d in ("lib", "lib64"):
                found += _glob.glob(os.path.join(
                    self.package_folder, _d, "*.a"))
            shipped = {os.path.splitext(os.path.basename(p))[0][3:]
                       for p in found}
            self.output.info("package_info shipped archives: %s"
                             % sorted(shipped))
            want = ["sedml-static", "sedml", "numl-static", "numl",
                    "sbml-static", "sbml", "expat"]
            libs = [l for l in want if l in shipped]
            if not any(l in ("sedml-static", "sedml") for l in libs):
                # Never hand consumers an empty/misleading list silently:
                # fall back to the pinned expectation so a broken package
                # fails with a clear "unable to find library" instead of
                # a wall of `undefined symbol: SedDocument::...`.
                self.output.warning(
                    "no sedml archive among shipped files; "
                    "falling back to pinned libs")
                libs = ["sedml-static", "numl-static", "sbml-static",
                        "expat"]
            self.cpp_info.libs = libs
            self.output.info("package_info libs: %s" % libs)
            have64 = any(os.path.isfile(os.path.join(
                self.package_folder, "lib64", "lib%s.a" % l)) for l in libs)
            have = any(os.path.isfile(os.path.join(
                self.package_folder, "lib", "lib%s.a" % l)) for l in libs)
            if have64 and not have:
                self.cpp_info.libdirs = ["lib64"]
            else:
                self.cpp_info.libdirs = ["lib"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
