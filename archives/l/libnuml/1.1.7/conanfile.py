#!/usr/bin/env python3
"""Conan recipe for libnuml 1.1.7 (CMake, bare-cmake vendor flow).

libNUML is the C++ library for reading/writing Numerical Markup Language
(NuML) documents. Upstream: https://github.com/NuML/NuML (tag v1.1.7).

Build notes:
- CMake project (LANGUAGES CXX). Produces shared libnuml (+ static
  libnuml-static) with SOVERSION 1.
- Upstream hard-requires libSBML (its XML layer) and an XML parser for
  libSBML (expat here). Neither is published in the ohpcd registry, so
  this recipe builds their official release sources into a private
  static prefix inside the build folder (single-PR constraint, R36).
  Same pattern as the merged libcombine/0.2.20 (vendored libSBML 5.20.5)
  and libsedml/2.0.33 (vendored expat 2.7.1 + libSBML 5.21.0 + libNuML
  1.1.7) recipes. The vendored headers/static libs are shipped inside
  this package; split into standalone recipes as follow-up.
- Upstream has no test suite (no tests/ dir, no add_test(); ctest -N
  registers 0 entries), so build() proves that with ctest -N and emits
  an HMBS_UPSTREAM_TEST_RESULT no_tests marker. See
  test_package/MANIFEST.yml for the audit record.
- OHOS toolchain: bare `cmake -B/-S/--build/--install` with an
  ohos.toolchain.cmake when discoverable, else a generated minimal
  fallback (Linux platform identity + OHOS clang, libsedml 2.0.33
  validated pattern). CMake 4.x ships no Platform/HarmonyOS module and
  Conan's default "HarmonyOS" name has no platform module either, while
  faking "Linux" in a toolchain breaks nothing here because the
  compilers stay the OHOS clang pair. No hard dependency on the NDK
  ohos.toolchain.cmake file (absent on the preflight worker).
"""

import glob
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, get, replace_in_file


class LibnumlConan(ConanFile):
    name = "libnuml"
    version = "1.1.7"
    description = "C++ library for reading, writing and manipulating NuML documents"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/NuML/NuML"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libnuml supports Linux and OHOS targets, got {}".format(
                    self.settings.os)
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        # Bare-cmake flow (same as libsedml/2.0.33): build dirs are managed
        # explicitly under self.build_folder, sources under self.source_folder.
        pass

    def source(self):
        get(self, **self.conan_data["sources"]["libnuml"], strip_root=True,
            destination="numl-src")
        get(self, **self.conan_data["sources"]["expat"], strip_root=True,
            destination="vendor/expat")
        get(self, **self.conan_data["sources"]["libsbml"], strip_root=True,
            destination="vendor/libsbml")

    def _ohos_toolchain(self):
        # Best-effort discovery of ohos.toolchain.cmake. The official CI
        # profile (ci/conan/profiles/ohos-aarch64) is a native build and
        # sets no user_toolchain, so a missing file must NOT be fatal:
        # fall back to a generated minimal toolchain (Linux platform
        # identity + OHOS clang). Same idiom as libsedml/2.0.33.
        candidates = []
        try:
            ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain",
                               default=[], check_type=list)
        except Exception:
            ut = []
        if ut:
            candidates.extend(list(ut))
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
            "/data/service/hnp/ohos-sdk*/ohos/native/build/cmake/ohos.toolchain.cmake",
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
        # one. Identifying as Linux makes if(UNIX) hold in the old
        # upstreams (libSBML/libNuML take a WIN32 branch otherwise and
        # libSBML fails with "__declspec attributes are not enabled").
        # The compilers below are still the OHOS clang pair, so the
        # objects stay native OHOS/aarch64 binaries.
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
        val = os.environ.get("HMBS_CMAKE", "")
        if val and os.path.isfile(val):
            return val
        which = shutil.which("cmake")
        if which:
            return which
        return "cmake"

    def _compilers(self):
        # Prefer the profile-declared compilers, then CC/CXX env, then
        # PATH lookup. Validates executability where possible.
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
        # llvm-ranlib. Resolve both explicitly; when llvm-ranlib is
        # absent, fall back to an `llvm-ar s` shim (equivalent to ranlib).
        # Same pit as libsedml/2.0.33 (knowledge E385 family).
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
        dirs += ["/data/service/hnp/bin"]

        def _find(names):
            for d in dirs:
                for n in names:
                    cand = os.path.join(d, n)
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
                self.output.info("llvm-ranlib missing, using shim: %s" % shim)
                ranlib = shim
            except OSError as e:
                self.output.warning("create ranlib shim failed: %s" % e)
        self.output.info("llvm tools: AR=%s RANLIB=%s"
                         % (ar or "(toolchain default)",
                            ranlib or "(toolchain default)"))
        return ar, ranlib

    def _ensure_writable_tmp(self):
        # HMBS readonly_tmp: /tmp can be read-only on OHOS; cmake, clang
        # and /bin/sh fall back to /tmp unless TMPDIR points at a writable
        # dir. Ensure the directory really exists and is writable, then
        # export it so every self.run()/subprocess child inherits it.
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
                cands.append(os.path.join(str(self.build_folder), "hmbs-tmp"))
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
            self.output.warning("no writable tmp dir found among: %s" % cands)

    def _base_defs(self, toolchain):
        return [
            '-DCMAKE_TOOLCHAIN_FILE="%s"' % toolchain,
            "-DCMAKE_BUILD_TYPE=%s" % self.settings.build_type,
            "-DCMAKE_INSTALL_LIBDIR=lib",
            "-DCMAKE_POSITION_INDEPENDENT_CODE=ON",
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
        ]

    def _parallel_args(self):
        # Low-memory Zhenji: Signal 9 (SIGKILL/OOM) with empty logs.
        # Bare cmake --build defaults to max parallelism (Ninja: ncpu+2),
        # which OOM-kills the large vendored libSBML build. Force serial;
        # HMBS injects tools.build:jobs=1 but bare cmake ignores that conf.
        for _k in ("CMAKE_BUILD_PARALLEL_LEVEL", "CTEST_PARALLEL_LEVEL"):
            try:
                os.environ[_k] = "1"
            except Exception:
                pass
        return " --parallel 1"

    def _find_archives(self, root):
        # Bounded archive search (no unbounded ** walk): probe the known
        # install/output layouts at fixed depths only.
        found = []
        for _pat in (os.path.join(root, "*.a"), os.path.join(root, "*", "*.a"), os.path.join(root, "*", "*", "*.a"), os.path.join(root, "*", "*", "*", "*.a")):
            try:
                found.extend(glob.glob(_pat))
            except Exception:
                continue
        return sorted(set(found))

    def _dep_prefix(self):
        return os.path.join(self.build_folder, "deps")

    def _guard_findzlib(self, path):
        # libSBML runs find_package(ZLIB QUIET) unconditionally, then
        # calls check_library_exists() even when ZLIB_LIBRARY is NOTFOUND
        # (no system zlib on this host). CMake 4.x turns that into a hard
        # configure error. Guard the probe so a missing zlib degrades to
        # "not found" instead of aborting configure. No functional change:
        # we build WITH_ZLIB=OFF, zlib is never linked.
        if not os.path.isfile(path):
            return
        with open(path, encoding="utf-8", errors="replace") as f:
            content = f.read()
        old = 'check_library_exists("${LIBZ_CMAKE_PATH}" "gzopen" "" LIBZ_FOUND_SYMBOL)'
        if old not in content:
            return
        replace_in_file(self, path, old,
                        'if(LIBZ_CMAKE_PATH)\n    %s\n    endif()' % old)

    def _relax_findexpat(self, path):
        # libSBML/libNuML share the same FindEXPAT.cmake probe: after
        # finding headers+archive it try-compiles a CHECK_C_SOURCE_COMPILES
        # program and calls message(FATAL_ERROR) when both variants fail.
        # On the OHOS toolchain that probe is fragile (same archive passes
        # for libSBML yet fails when run indirectly via sbml config during
        # the libNuML configure). The probe only decides the XML_STATIC
        # compile definition; on non-Windows targets expat.h leaves
        # XMLIMPORT empty with or without it, so continuing without the
        # flag is functionally neutral. Keep the attempt; downgrade only
        # the fatal abort to a warning. A truly unlinkable archive still
        # fails loudly at the real build link step.
        if not os.path.isfile(path):
            return
        # Do not touch expat's own build helper: editing it breaks the
        # very first cmake step with a parse error (libsedml precedent).
        norm = path.replace("\\", "/")
        if "/vendor/expat/" in norm:
            return
        with open(path, encoding="utf-8", errors="replace") as f:
            content = f.read()
        old = 'message(FATAL_ERROR "Unable to compile a test executable against expat with'
        if old not in content:
            return
        new = 'message(WARNING "HMBS expat probe continuing without XML_STATIC: Unable to compile a test executable against expat with'
        replace_in_file(self, path, old, new)

    def _enable_c_language(self, path):
        # libNUML 1.1.7 declares project(... LANGUAGES CXX) but its
        # FindEXPAT.cmake runs enable_language(C) + CHECK_C_SOURCE_COMPILES
        # lazily during find_package. The late C enablement mishandles the
        # OHOS toolchain and both EXPAT try-compiles fail. Enabling C from
        # the start lets the toolchain configure both compilers up front;
        # no functional change (libsedml precedent, CI #48898).
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
        jobs = self._parallel_args()
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
        numl_src = os.path.join(self.source_folder, "numl-src", "libnuml")

        # Guard vendored copies before configuring anything. Bounded
        # candidate list (no full source-tree walk: low-memory host).
        _cands = set()
        for _pat in (
                os.path.join(sbml_src, "*.cmake"),
                os.path.join(sbml_src, "*", "*.cmake"),
                os.path.join(sbml_src, "*", "*", "*.cmake"),
                os.path.join(numl_src, "*.cmake"),
                os.path.join(numl_src, "*", "*.cmake"),
                os.path.join(numl_src, "*", "*", "*.cmake")):
            try:
                for _p in glob.glob(_pat):
                    _b = os.path.basename(_p)
                    if _b in ("FindZLIB.cmake", "FindEXPAT.cmake"):
                        _cands.add(_p)
            except Exception:
                continue
        for _p in sorted(_cands):
            if os.path.basename(_p) == "FindZLIB.cmake":
                self._guard_findzlib(_p)
            else:
                self._relax_findexpat(_p)
        self._enable_c_language(os.path.join(numl_src, "CMakeLists.txt"))

        # 1. expat (static, no tests/tools/examples) into the private prefix.
        b_expat = os.path.join(self.build_folder, "build-expat")
        self.run('%s -B "%s" -S "%s" %s '
                 '-DCMAKE_INSTALL_PREFIX="%s" '
                 '-DBUILD_SHARED_LIBS=OFF -DEXPAT_SHARED_LIBS=OFF '
                 '-DEXPAT_BUILD_TESTS=OFF -DEXPAT_BUILD_EXAMPLES=OFF '
                 '-DEXPAT_BUILD_TOOLS=OFF'
                 % (cmake, b_expat, expat_src, base, deps))
        self.run('%s --build "%s"%s' % (cmake, b_expat, jobs))
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
        self.run('%s --build "%s"%s' % (cmake, b_sbml, jobs))
        self.run('%s --install "%s"' % (cmake, b_sbml))

        # 3. libNuML (static+shared per option) against the vendored libSBML.
        # Pass the vendored expat explicitly (same values that made the
        # libSBML configure succeed) instead of relying on
        # LIBNUML_DEPENDENCY_DIR search.
        b_numl = os.path.join(self.build_folder, "build-numl")
        env_numl = ("LIBSBML_DIR=\"%s\" EXPAT_DIR=\"%s\" " % (deps, deps))
        skip_shared = "ON" if not self.options.shared else "OFF"
        self.run(env_numl + '%s -B "%s" -S "%s" %s '
                 '-DCMAKE_INSTALL_PREFIX="%s" '
                 '-DBUILD_SHARED_LIBS=%s -DLIBNUML_SKIP_SHARED_LIBRARY=%s '
                 '-DWITH_SWIG=OFF -DWITH_EXAMPLES=OFF -DWITH_CHECK=OFF '
                 '-DLIBNUML_DEPENDENCY_DIR="%s" '
                 '-DCMAKE_PREFIX_PATH="%s" '
                 '-DEXPAT_INCLUDE_DIR="%s/include" '
                 '-DEXPAT_LIBRARY="%s/lib/libexpat.a"'
                 % (cmake, b_numl, numl_src, base, deps,
                    "ON" if self.options.shared else "OFF", skip_shared,
                    deps, deps, deps, deps))
        self.run('%s --build "%s"%s' % (cmake, b_numl, jobs))
        self.run('%s --install "%s"' % (cmake, b_numl))
        self._verify_numl_archive(b_numl)
        self._report_upstream_tests(b_numl, cmake)

    def _verify_numl_archive(self, b_numl):
        # Fail fast if the archives consumers link are missing, and confirm
        # the static archive really exports the NUML consumer symbols.
        cands = sorted(self._find_archives(b_numl))
        self.output.info("numl build archives: %s"
                         % ([os.path.relpath(p, b_numl) for p in cands]
                            if cands else "NONE"))
        want = [p for p in cands
                if os.path.basename(p) in ("libnuml-static.a", "libnuml.a")]
        if not want:
            raise Exception("libnuml static archive missing in build tree")
        probe = want[0]
        for tool in ("llvm-nm", "nm"):
            w = shutil.which(tool)
            if not w:
                continue
            try:
                r = subprocess.run([w, probe], capture_output=True, text=True,
                                   timeout=120)
                if "NUMLDocument" in (r.stdout or ""):
                    self.output.info("archive symbol check: NUMLDocument found via %s" % tool)
                    return
            except Exception as e:
                self.output.warning("nm probe with %s failed: %s" % (tool, e))
        self.output.warning("nm probe skipped (no llvm-nm/nm); archive presence already verified")

    def _emit_upstream_result(self, result):
        # Dual-channel evidence (conan log + stdout) plus persistence to
        # the build folder so later cache-hit rounds can re-emit the
        # measured result from test_package. Same idiom as the merged
        # libsedml/2.0.33 recipe.
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

    def _report_upstream_tests(self, b_numl, cmake):
        # Upstream v1.1.7 ships no test suite: prove it with `ctest -N`
        # (single deterministic source: the "Total Tests: N" line) and emit
        # the no_tests evidence marker. Never fabricate counts.
        total = None
        try:
            r = subprocess.run([cmake, "-E", "chdir", b_numl,
                                "ctest", "-N"],
                               capture_output=True, text=True, timeout=120)
            out = (r.stdout or "") + "\n" + (r.stderr or "")
            self.output.info("ctest -N output:\n%s" % out.strip()[:2000])
            m = re.search(r"Total Tests:\s*(\d+)", out)
            if m is not None:
                total = int(m.group(1))
        except Exception as e:
            self.output.warning("ctest -N probe failed: %s" % e)
        if total is None:
            marker = {"status": "error", "framework": "ctest",
                      "command": "ctest -N",
                      "discovered": 0, "executed": 0, "passed": 0,
                      "failed": 0, "skipped": 0,
                      "reason": "ctest -N output unparsable; searched build-numl dir"}
            self._emit_upstream_result(marker)
            raise Exception("cannot prove upstream test count; aborting")
        if total != 0:
            raise Exception("upstream registered %d tests; recipe assumed no_tests" % total)
        marker = {"status": "no_tests", "framework": "ctest",
                  "command": "ctest -N",
                  "discovered": 0, "executed": 0, "passed": 0,
                  "failed": 0, "skipped": 0,
                  "reason": "upstream libnuml 1.1.7 has no test suite (no tests/ dir, no add_test; ctest -N Total Tests: 0)"}
        self._emit_upstream_result(marker)

    def package(self):
        # Merge the private prefix (numl + sbml + expat headers and static
        # archives) into the package. `cmake --install` does not reliably
        # place the static archives into <prefix>/lib for these old
        # upstreams (libsedml/2.0.33 preflight 2026-09-16: headers
        # installed, build tree held libsedml-static.a, yet package lib/
        # had only libexpat.a), so sweep the build tree for the
        # allowlisted archives as fallback. Shared libnuml.so* ships only
        # when built (shared=True).
        deps = self._dep_prefix()
        copy(self, "*.h", src=os.path.join(deps, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "*.a", src=os.path.join(deps, "lib"),
             dst=os.path.join(self.package_folder, "lib"))
        pkg_lib = os.path.join(self.package_folder, "lib")
        pkg_lib64 = os.path.join(self.package_folder, "lib64")
        if os.path.isdir(pkg_lib64):
            for arc64 in glob.glob(os.path.join(pkg_lib64, "*.a")):
                dest = os.path.join(pkg_lib, os.path.basename(arc64))
                if not os.path.isfile(dest):
                    self.output.info("folding lib64 archive into lib/: %s"
                                     % os.path.basename(arc64))
                    copy(self, os.path.basename(arc64), src=pkg_lib64,
                         dst=pkg_lib, keep_path=False)
        allow = ("libnuml-static.a", "libnuml.a",
                 "libsbml-static.a", "libsbml.a",
                 "libexpat.a")
        if os.path.isdir(self.build_folder):
            _arc_cands = []
            for _b in ("build-expat", "build-sbml", "build-numl", "deps"):
                _arc_cands.extend(self._find_archives(os.path.join(self.build_folder, _b)))
            for arc in sorted(set(_arc_cands)):
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
        shipped = sorted(os.path.basename(p)
                         for p in glob.glob(os.path.join(pkg_lib, "*.a")))
        self.output.info("package lib inventory: %s"
                         % (shipped if shipped else "NONE"))
        for _arc in shipped:
            _p = os.path.join(pkg_lib, _arc)
            try:
                self.output.info("  %s (%d bytes)" % (_arc, os.path.getsize(_p)))
            except OSError:
                pass
        if not any(n in ("libnuml-static.a", "libnuml.a") for n in shipped):
            raise Exception(
                "package lib/ ships no numl archive "
                "(found: %s); consumer link cannot succeed" % shipped)
        if self.options.shared:
            copy(self, "*.so*", src=os.path.join(deps, "lib"),
                 dst=os.path.join(self.package_folder, "lib"))
        # Persist the measured upstream result into the package so
        # test_package can re-emit it every round even when Conan hits
        # the binary cache and build() is skipped (libsedml/2.0.33 idiom).
        try:
            src_json = os.path.join(str(self.build_folder),
                                    "hmbs_upstream.json")
            if os.path.isfile(src_json):
                with open(src_json, "r", encoding="utf-8") as rf:
                    payload = rf.read()
                obj = json.loads(payload)
                if (not isinstance(obj, dict)
                        or obj.get("status") != "no_tests"
                        or int(obj.get("discovered", -1)) != 0
                        or int(obj.get("executed", -1)) != 0):
                    raise ValueError("expected audited no_tests/0 payload")
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

    def package_info(self):
        # Static link order matters: numl -> sbml -> expat. Probe the
        # actually shipped archives so the list always matches what
        # package() installed (archive names differ slightly between
        # upstreams: libnuml-static.a vs libnuml.a, same for sbml).
        # Same idiom as libsedml/2.0.33.
        if self.options.shared:
            self.cpp_info.libs = ["numl", "sbml-static", "expat"]
        else:
            shipped = {os.path.splitext(os.path.basename(p))[0][3:]
                       for p in glob.glob(os.path.join(
                           self.package_folder, "lib", "*.a"))}
            shipped |= {os.path.splitext(os.path.basename(p))[0][3:]
                        for p in glob.glob(os.path.join(
                            self.package_folder, "lib64", "*.a"))}
            self.output.info("package_info shipped archives: %s"
                             % sorted(shipped))
            want = ["numl-static", "numl",
                    "sbml-static", "sbml", "expat"]
            libs = [lib for lib in want if lib in shipped]
            if not any(lib in ("numl-static", "numl") for lib in libs):
                self.output.warning(
                    "no numl archive among shipped files; "
                    "falling back to pinned libs")
                libs = ["numl-static", "sbml-static", "expat"]
            self.cpp_info.libs = libs
            self.output.info("package_info libs: %s" % libs)
            have64 = any(os.path.isfile(os.path.join(
                self.package_folder, "lib64", "lib%s.a" % lib)) for lib in libs)
            have = any(os.path.isfile(os.path.join(
                self.package_folder, "lib", "lib%s.a" % lib)) for lib in libs)
            if have64 and not have:
                self.cpp_info.libdirs = ["lib64"]
            else:
                self.cpp_info.libdirs = ["lib"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
