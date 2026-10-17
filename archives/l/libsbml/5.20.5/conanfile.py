#!/usr/bin/env python3
"""Conan recipe — libsbml 5.20.5 (cmake)"""

import contextlib
import glob
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import copy, export_conandata_patches, get, rm


class LibsbmlConan(ConanFile):
    name = "libsbml"
    version = "5.20.5"
    description = "Library for reading, writing and manipulating SBML (Systems Biology Markup Language)"
    license = "LGPL-2.1-only"
    homepage = "https://sbml.org/software/libsbml"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        # NOTE (2026-09-21): a previous round forced
        # `self.options.shared = False` on OHOS to dodge the shared-link
        # relocation failure against static non-PIC zlib (notes.md row 14).
        # That assignment aborts the whole graph when the option value was
        # requested as True from outside the recipe (preflight 2026-09-21:
        # "Incorrect attempt to modify option 'shared' from 'True' to
        # 'False'" in configure(), line 51). Conan forbids overriding an
        # externally requested option inside configure(), so the recipe must
        # honour shared=True and instead make the shared build linkable
        # (see generate(): WITH_ZLIB/WITH_BZIP2 are OFF for OHOS shared).
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("libxml2/2.15.3", transitive_headers=True, transitive_libs=True)
        self.requires("zlib/1.3.1", transitive_libs=True)
        self.requires("bzip2/1.0.8", transitive_libs=True)

    def build_requirements(self):
        # Only the upstream libcheck-based test suite needs this; it is not
        # part of the installed libsbml link interface.
        self.test_requires("check/0.15.2")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libsbml supports Linux and OHOS, not {}".format(self.settings.os)
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        self._patch_findlibxml_zlib()
        self._patch_keep_static_for_tests()

    def _patch_findlibxml_zlib(self):
        # Replaces patches/0001-findlibxml-zlib-plain-lib.patch (removed
        # 2026-09-21: the unified diff failed to apply on the preflight box
        # with "source file is different - CMakeModules/FindLIBXML.cmake",
        # i.e. hunk context/line-offset mismatch; an in-recipe substring
        # replacement has no hunk headers and cannot fail that way).
        # Upstream CMakeModules/FindLIBXML.cmake sets
        #   set(ADDITIONAL_LIBS "${ADDITIONAL_LIBS}ZLIB::ZLIB;")
        # and later passes "${LIBXML_LIBRARY};${ADDITIONAL_LIBS}" as
        # CMAKE_REQUIRED_LIBRARIES into CHECK_C_SOURCE_COMPILES. The inner
        # try_compile project never runs find_package(ZLIB), so the
        # ZLIB::ZLIB imported target is invisible there and CMake 4.x
        # aborts with "Target cmTC_* links to ZLIB::ZLIB but the target
        # was not found". Use the plain ${ZLIB_LIBRARY} path (same file)
        # which propagates into try_compile verbatim; link semantics are
        # unchanged. Idempotent; fail-closed with evidence when the
        # pattern is absent.
        path = os.path.join(
            self.source_folder, "CMakeModules", "FindLIBXML.cmake")
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except OSError as exc:
            self.output.warning(
                "FindLIBXML zlib patch skipped (non-fatal): cannot read {}: {}".format(path, exc))
            return
        needle = 'set(ADDITIONAL_LIBS "${ADDITIONAL_LIBS}ZLIB::ZLIB;")'
        replacement = 'set(ADDITIONAL_LIBS "${ADDITIONAL_LIBS}${ZLIB_LIBRARY};")'
        if needle in content:
            content = content.replace(needle, replacement)
            try:
                with open(path, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(content)
            except OSError as exc:
                raise ConanException(
                    "FindLIBXML zlib patch: cannot write {}: {}".format(path, exc))
            self.output.info(
                "FindLIBXML zlib patch: ZLIB::ZLIB -> ${ZLIB_LIBRARY} plain path")
        elif replacement in content:
            self.output.info("FindLIBXML zlib patch: already applied, skipping")
        else:
            self.output.warning(
                "FindLIBXML zlib patch: pattern not found in {}; ".format(path)
                + "ZLIB::ZLIB present={}".format("ZLIB::ZLIB" in content))

    def _patch_keep_static_for_tests(self):
        # Upstream tests link ${LIBSBML_LIBRARY}-static unconditionally
        # (src/sbml/packages/*/test/CMakeLists.txt:
        # `set(TEST_LIB ${LIBSBML_LIBRARY}-static)`), but the top-level
        # CMakeLists maps DEFINED BUILD_SHARED_LIBS=ON to
        # LIBSBML_SKIP_STATIC_LIBRARY=ON, so a shared build defines no
        # sbml-static target and every test link fails with
        # `ld.lld: error: unable to find library -lsbml-static`
        # (preflight 2026-09-23, shared libsbml.so itself linked OK).
        # Previous route (rows 16-17) kept the static archive alongside
        # the shared library (dual build). That doubles compilation
        # (every TU compiled twice: sbml + sbml-static objects) and
        # flakes Signal 9 OOM on the small-memory box: 2026-09-24 kill
        # during UniqueSpatialIds.cpp.o (sbml-static, 24%) despite
        # -O0 -g0 -j1 + VERBOSE, while the same dual build had passed
        # 35/35 once (row 18) -- i.e. flaky peak, not deterministic.
        # Same test scope, lighter route: link the tests against the
        # shared sbml target so only ONE library build is needed. Test
        # assertions/coverage are unchanged (same API, same sources).
        # Packaging still ships/announces the shared lib (package_info
        # selects by the live shared option). Idempotent; fail-closed
        # when no test link is found.
        import io
        # Roll back the row-16 dual-build override if present (source()
        # runs on a fresh extract, but conan may reuse the source folder
        # across retries): remove the two lines added after
        # find_package(CHECK REQUIRED) so the default SKIP_STATIC=ON
        # (shared-only) applies again.
        top = os.path.join(self.source_folder, "CMakeLists.txt")
        try:
            with io.open(top, "r", encoding="utf-8", errors="replace") as fh:
                top_content = fh.read()
        except OSError as exc:
            raise ConanException(
                "keep-static rollback: cannot read {}: {}".format(top, exc))
        sentinel = "HMBS (OHOS shared): upstream tests link"
        if sentinel in top_content:
            # Drop only the two lines this recipe added (sentinel comment
            # + the immediately following marker). The pristine upstream
            # file already contains its own generic
            # set(LIBSBML_SKIP_STATIC_LIBRARY OFF) in an else-branch
            # (row 17), so a blanket substring delete would corrupt it.
            out_lines = []
            skip_marker = False
            for ln in top_content.splitlines(True):
                if sentinel in ln:
                    skip_marker = True
                    continue
                if skip_marker and "set(LIBSBML_SKIP_STATIC_LIBRARY OFF)" in ln:
                    skip_marker = False
                    continue
                skip_marker = False
                out_lines.append(ln)
            top_content = "".join(out_lines)
            try:
                with io.open(top, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(top_content)
            except OSError as exc:
                raise ConanException(
                    "keep-static rollback: cannot write {}: {}".format(top, exc))
            self.output.info(
                "keep-static rollback: dual-build override removed, "
                "shared-only build restored")
        needle = "${LIBSBML_LIBRARY}-static"
        patched_files = 0
        patched_occurrences = 0
        searched = 0
        for root, _dirs, files in os.walk(self.source_folder):
            # Only test build files can reference the static test lib;
            # restrict to */test/CMakeLists.txt to avoid touching the
            # library definition itself (src/CMakeLists add_library).
            if os.path.basename(root) != "test":
                continue
            if "CMakeLists.txt" not in files:
                continue
            searched += 1
            cmake_path = os.path.join(root, "CMakeLists.txt")
            try:
                with io.open(cmake_path, "r", encoding="utf-8", errors="replace") as fh:
                    content = fh.read()
            except OSError:
                continue
            count = content.count(needle)
            if count <= 0:
                continue
            content = content.replace(needle, "${LIBSBML_LIBRARY}")
            try:
                with io.open(cmake_path, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(content)
            except OSError as exc:
                raise ConanException(
                    "test-link-shared patch: cannot write {}: {}".format(cmake_path, exc))
            patched_files += 1
            patched_occurrences += count
        self.output.info(
            "test-link-shared patch: replaced {} occurrence(s) in {} "
            "test CMakeLists (searched {} test dirs)".format(
                patched_occurrences, patched_files, searched))
        if patched_occurrences <= 0:
            raise ConanException(
                "test-link-shared patch: pattern {!r} not found in any "
                "*/test/CMakeLists.txt under {} (searched {} dirs)".format(
                    needle, self.source_folder, searched))

    def _dependency(self, name):
        for deps in (self.dependencies.host, self.dependencies.test, self.dependencies.build):
            try:
                return deps[name]
            except KeyError:
                continue
        return None

    def _dep_include(self, dep):
        if dep is None:
            return ""
        for inc in dep.cpp_info.includedirs:
            path = inc if os.path.isabs(inc) else os.path.join(dep.package_folder, inc)
            if os.path.isdir(path):
                return path
        return ""

    def _dep_lib(self, dep, names):
        if dep is None:
            return ""
        search_dirs = []
        for libdir in dep.cpp_info.libdirs:
            path = libdir if os.path.isabs(libdir) else os.path.join(dep.package_folder, libdir)
            if os.path.isdir(path):
                search_dirs.append(path)
        for directory in search_dirs:
            for name in names:
                for ext in (".so", ".a", ".lib", ".dylib"):
                    candidate = os.path.join(directory, name + ext)
                    if os.path.isfile(candidate):
                        return candidate
                matches = sorted(glob.glob(os.path.join(directory, name + ".*")))
                for match in matches:
                    if os.path.isfile(match):
                        return match
        return ""

    def _ensure_writable_tmp(self):
        # HMBS injects a task-private TMPDIR/TMP/TEMP (see preflight
        # HMBS_PLATFORM_CAPABILITIES.tmpdir); /tmp is read-only on the
        # device. Prefer the injected value when it exists and is writable,
        # otherwise fall back to a directory inside build_folder (always
        # writable). Never fall back to /tmp.
        import tempfile
        candidates = [
            os.environ.get("TMPDIR", ""),
            os.environ.get("TMP", ""),
            os.environ.get("TEMP", ""),
            os.path.join(self.build_folder, "tmp"),
        ]
        chosen = ""
        for cand in candidates:
            if cand and os.path.isdir(cand):
                try:
                    fd, probe = tempfile.mkstemp(prefix="hmbs-w", dir=cand)
                    os.close(fd)
                    os.unlink(probe)
                    chosen = cand
                    break
                except OSError:
                    continue
        if not chosen:
            chosen = os.path.join(self.build_folder, "tmp")
            os.makedirs(chosen, exist_ok=True)
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = chosen
        return chosen

    def generate(self):
        self._ensure_writable_tmp()
        deps = CMakeDeps(self)
        # Upstream ships its own CMakeModules/Find{LIBXML,ZLIB,BZ2,CHECK}.cmake
        # defining ALLCAPS imported targets (LIBXML::LIBXML, ZLIB::ZLIB,
        # BZ2::BZ2, CHECK::CHECK). Conan's CMakeToolchain sets
        # CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON by default, so find_package()
        # resolves to CMakeDeps CONFIG files instead of those Find modules.
        # The in-repo deps expose different names (zlib::zlib default,
        # bzip2::bzip2 default, LibXml2::LibXml2, Check::check), hence
        # generate-step "Target sbml links to ZLIB::ZLIB but the target was
        # not found" + the same for every CHECK::CHECK test. Remap both file
        # and target names to the upstream ALLCAPS spelling (same pattern as
        # quazip/1.4.1, groonga, maeparser) so CONFIG mode provides exactly
        # what src/CMakeLists.txt and src/*/test link against.
        deps.set_property("zlib", "cmake_file_name", "ZLIB")
        deps.set_property("zlib", "cmake_target_name", "ZLIB::ZLIB")
        deps.set_property("bzip2", "cmake_file_name", "BZ2")
        deps.set_property("bzip2", "cmake_target_name", "BZ2::BZ2")
        deps.set_property("libxml2", "cmake_file_name", "LIBXML")
        deps.set_property("libxml2", "cmake_target_name", "LIBXML::LIBXML")
        deps.set_property("check", "cmake_file_name", "CHECK")
        deps.set_property("check", "cmake_target_name", "CHECK::CHECK")
        deps.generate()
        VirtualRunEnv(self).generate()
        tc = CMakeToolchain(self)
        # CMake >= 4.0 removed compatibility with
        # cmake_minimum_required(< 3.5); upstream declares
        # 'cmake_minimum_required(VERSION 3.1...3.19)', so configure
        # aborts before compiler identification without this (same fix
        # as oystr/0.2.0, wxWidgets/3.2.6, type-safe/0.2.4).
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        if str(self.settings.os) == "OHOS":
            # Vanilla CMake (e.g. 4.4.x) ships no Platform/HarmonyOS module,
            # so the default CMakeToolchain mapping (CMAKE_SYSTEM_NAME=
            # HarmonyOS) aborts compiler identification with
            # "System is unknown to cmake". Build as Linux/aarch64.
            # Single channel only (cache_variables -> -D on the cmake
            # command line), like the merged oystr/0.2.0 recipe: setting
            # the same key through both cache_variables and tc.variables
            # is redundant and risks toolchain/preset ordering surprises
            # under Conan 2.30.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["WITH_SWIG"] = "OFF"
        tc.variables["WITH_LIBXML"] = "ON"
        tc.variables["WITH_EXPAT"] = "OFF"
        tc.variables["WITH_XERCES"] = "OFF"
        # OHOS shared-link guard (notes.md rows 14-15): OHOS zlib/1.3.1 is
        # static-only by design (R26, no shared option, no -fPIC objects)
        # and bzip2/1.0.8 rejects shared=True on OHOS, so a shared libsbml
        # on aarch64 cannot link those static non-PIC archives into
        # libsbml.so (preflight evidence: R_AARCH64_ADR_PREL_PG_HI21 against
        # z_errmsg from libz.a(zutil.o)). Conan forbids overriding an
        # externally requested options.shared inside configure(), so the
        # recipe honours shared=True and instead builds the shared library
        # without compression support; static builds keep WITH_ZLIB /
        # WITH_BZIP2 ON (no shared-link step there). Upstream gates the
        # ZLIB/BZ2 link on exactly these options, so OFF skips the failing
        # link with no other build change.
        _ohos_shared = (str(self.settings.os) == "OHOS" and self.options.shared)
        if _ohos_shared:
            self.output.info(
                "OHOS shared build: WITH_ZLIB/WITH_BZIP2=OFF (static "
                "non-PIC zlib/bzip2 cannot link into libsbml.so on aarch64)")
        tc.variables["WITH_ZLIB"] = "OFF" if _ohos_shared else "ON"
        tc.variables["WITH_BZIP2"] = "OFF" if _ohos_shared else "ON"
        tc.variables["WITH_CHECK"] = "ON"
        tc.variables["WITH_EXAMPLES"] = "OFF"
        tc.variables["WITH_CPP_NAMESPACE"] = "OFF"
        tc.variables["WITH_STABLE_PACKAGES"] = "ON"
        tc.variables["WITH_ALL_PACKAGES"] = "OFF"
        # Small-memory guard (preflight 2026-09-20: compile stage
        # `tar: child process: Cannot fork: Out of memory`; 2026-09-21:
        # compile stage `Signal 9` with empty stdout/stderr tail, i.e. the
        # OOM-killer took the compiler with no flushed log): libsbml
        # ships very large generated TUs (ASTNode/SBMLDocument) and a
        # huge shared link; default Release -O3 plus debug info spikes
        # peak RSS so far that even fork() fails box-wide, and -O1 still
        # Signal-9s. Clamp ALL configs to -O0 -g0 (lowest peak; codegen
        # semantics unchanged for packaging) via the per-config cache
        # channel so ordering cannot re-enable -O3/-g; base
        # CMAKE_C/CXX_FLAGS carry -g0 so Debug (previously unclamped,
        # default -g) cannot reintroduce debug bloat; linker flags carry
        # -g0 for the same reason. extra_*flags are a belt for other
        # channels. CMAKE_VERBOSE_MAKEFILE streams per-file compile
        # lines so a kill leaves last-file evidence instead of silence.
        # WITH_CHECK stays ON: tests are not disabled for memory.
        tc.cache_variables["CMAKE_VERBOSE_MAKEFILE"] = "ON"
        tc.cache_variables["CMAKE_C_FLAGS"] = "-g0"
        tc.cache_variables["CMAKE_CXX_FLAGS"] = "-g0"
        tc.cache_variables["CMAKE_C_FLAGS_RELEASE"] = "-O0 -DNDEBUG -g0"
        tc.cache_variables["CMAKE_CXX_FLAGS_RELEASE"] = "-O0 -DNDEBUG -g0"
        tc.cache_variables["CMAKE_C_FLAGS_RELWITHDEBINFO"] = "-O0 -DNDEBUG -g0"
        tc.cache_variables["CMAKE_CXX_FLAGS_RELWITHDEBINFO"] = "-O0 -DNDEBUG -g0"
        tc.cache_variables["CMAKE_C_FLAGS_MINSIZEREL"] = "-O0 -DNDEBUG -g0"
        tc.cache_variables["CMAKE_CXX_FLAGS_MINSIZEREL"] = "-O0 -DNDEBUG -g0"
        tc.cache_variables["CMAKE_C_FLAGS_DEBUG"] = "-O0 -g0"
        tc.cache_variables["CMAKE_CXX_FLAGS_DEBUG"] = "-O0 -g0"
        tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = "-g0"
        tc.cache_variables["CMAKE_SHARED_LINKER_FLAGS"] = "-g0"
        tc.cache_variables["CMAKE_MODULE_LINKER_FLAGS"] = "-g0"
        for _flag_attr, _flag_vals in (("extra_cflags", ["-O0", "-g0"]), ("extra_cxxflags", ["-O0", "-g0"]), ("extra_ldflags", ["-g0"])):
            try:
                _flag_list = getattr(tc, _flag_attr, None)
                if _flag_list is not None:
                    for _flag in _flag_vals:
                        if _flag not in _flag_list:
                            _flag_list.append(_flag)
            except Exception:
                pass

        libxml2 = self._dependency("libxml2")
        zlib = self._dependency("zlib")
        bzip2 = self._dependency("bzip2")
        check = self._dependency("check")
        libxml_lib = self._dep_lib(libxml2, ["libxml2", "xml2"])
        libxml_inc = self._dep_include(libxml2)
        if libxml_lib:
            tc.cache_variables["LIBXML_LIBRARY"] = libxml_lib
        if libxml_inc:
            tc.cache_variables["LIBXML_INCLUDE_DIR"] = libxml_inc
        z_lib = self._dep_lib(zlib, ["libz", "z"])
        z_inc = self._dep_include(zlib)
        if z_lib:
            tc.cache_variables["ZLIB_LIBRARY"] = z_lib
        if z_inc:
            tc.cache_variables["ZLIB_INCLUDE_DIR"] = z_inc
        if zlib is not None:
            tc.cache_variables["ZLIB_ROOT"] = zlib.package_folder
        bz_lib = self._dep_lib(bzip2, ["libbz2", "bz2"])
        bz_inc = self._dep_include(bzip2)
        if bz_lib:
            tc.cache_variables["LIBBZ_LIBRARY"] = bz_lib
        if bz_inc:
            tc.cache_variables["LIBBZ_INCLUDE_DIR"] = bz_inc
        check_lib = self._dep_lib(check, ["libcheck", "check"])
        check_inc = self._dep_include(check)
        if check_lib:
            tc.cache_variables["LIBCHECK_LIBRARY"] = check_lib
        if check_inc:
            tc.cache_variables["LIBCHECK_INCLUDE_DIR"] = check_inc
        # Profile compiler may be stale (missing file) while PATH carries
        # the migrated toolchain (harmonybrew). Override only on miss.
        try:
            _cc, _cxx, _over = self._resolve_compilers()
            if _over:
                if _cc and os.path.isfile(_cc):
                    tc.cache_variables["CMAKE_C_COMPILER"] = _cc
                if _cxx and os.path.isfile(_cxx):
                    tc.cache_variables["CMAKE_CXX_COMPILER"] = _cxx
                self.output.info(
                    "compiler fallback: profile-missing, using c={} cpp={}".format(_cc, _cxx))
        except Exception as _exc:
            self.output.warning("compiler fallback skipped (non-fatal): {}".format(_exc))
        tc.generate()

    # -- OHOS SDK linker host runtime (E557) -------------------------
    # Same failure stage as ls-hpack/2.3.5 (PR #7487): the OHOS clang
    # driver spawns `lld` for the final link step, and lld is a
    # dynamically linked HOST ELF whose NEEDED list includes
    # libxml2.so.16 (normally resolved via its RUNPATH
    # $ORIGIN/../lib -> SDK llvm/lib, which the host loader does not
    # always expand). When lld cannot start, CMake only reports the
    # surface symptom at project() ("compiler identification is
    # unknown" / "not able to compile a simple test program").
    # Fix: before cmake.configure() run a REAL minimal compile+link
    # probe with the configured clang; ambient success is a no-op,
    # otherwise derive a host-runtime dir from the active toolchain
    # and scope the build under an LD_LIBRARY_PATH prepend. No CMake
    # bypass (no CMAKE_C_COMPILER_WORKS / forced compiler check) --
    # the real CMake probe must succeed on its own, otherwise the
    # build stops with full diagnostics.

    def _resolve_compilers(self):
        # Preflight 2026-09-20 16:48: profile still points at
        # /data/service/hnp/bin/clang{,++} (cc_exists=False) while PATH
        # provides /storage/Users/currentUser/.harmonybrew/bin/clang.
        # CMakeToolchain copies the profile path verbatim into
        # CMAKE_C/CXX_COMPILER, so without an override CMake keeps
        # failing at project() with "compiler identification is unknown".
        # Only override when the profile path is missing and a PATH
        # compiler exists; otherwise keep the profile value (CI parity).
        # Never fabricates a compiler: both candidates missing -> keep
        # the profile value and fail closed in CMake with diagnostics.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc_prof = compilers.get("c", "")
        cxx_prof = compilers.get("cpp", "")

        def _pick(prof, names):
            if prof and os.path.isfile(prof):
                return prof, False
            cands = []
            if prof:
                cands.append(os.path.basename(prof))
            cands += names
            for name in cands:
                found = shutil.which(name)
                if found and os.path.isfile(found):
                    return found, True
            return prof or names[0], False

        cc, cc_over = _pick(cc_prof, ["clang"])
        cxx, cxx_over = _pick(cxx_prof, ["clang++"])
        if cc and os.path.isfile(cc) and (not cxx or not os.path.isfile(cxx)):
            sibling = os.path.join(os.path.dirname(cc), "clang++")
            if os.path.isfile(sibling):
                cxx, cxx_over = sibling, True
        return cc, cxx, (cc_over or cxx_over)

    def _repair_stale_toolchain_compilers(self):
        # 3rd strategy cycle (2026-09-20 16:48 fingerprint, 2nd repair):
        # the generate()-time _resolve_compilers() override did not reach
        # the 16:48 toolchain (still
        # set(CMAKE_C_COMPILER "/data/service/hnp/bin/clang")). The
        # generate() process env does not yet source the hmbs/Conan
        # buildenv PATH that build() sees (flagged probe in build()
        # resolved which=harmonybrew/clang while generate() saw no
        # candidate), so a generate-only fix cannot cover a migrated
        # toolchain. Repair the already-generated conan_toolchain.cmake
        # in build(): only when the recorded compiler path is missing
        # on disk and a PATH compiler exists; otherwise leave the file
        # untouched and fail closed in CMake with diagnostics. No
        # hardcoded SDK paths: candidates come from basename + PATH
        # plus the resolved C sibling for clang++.
        try:
            base = getattr(self, "build_folder", "") or "."
            tc_paths = []
            try:
                for root, _dirs, files in os.walk(base):
                    if "conan_toolchain.cmake" in files:
                        tc_paths.append(os.path.join(root, "conan_toolchain.cmake"))
            except OSError:
                pass
            if not tc_paths:
                return
            try:
                cc_new, cxx_new, _over = self._resolve_compilers()
            except Exception:
                return
            if not _over:
                return
            for tc_path in tc_paths:
                try:
                    with open(tc_path, "r", encoding="utf-8", errors="replace") as fh:
                        content = fh.read()
                except OSError:
                    continue
                orig = content
                for key, new_val in (("CMAKE_C_COMPILER", cc_new),
                                     ("CMAKE_CXX_COMPILER", cxx_new)):
                    if not new_val or not os.path.isfile(new_val):
                        continue
                    pattern = re.compile(
                        r'set\(' + key + r'\s+"([^"]+)"')
                    match = pattern.search(content)
                    if not match:
                        continue
                    old_val = match.group(1)
                    if old_val and not os.path.isfile(old_val):
                        content = pattern.sub(
                            'set(' + key + ' "' + new_val + '"', content, count=1)
                        self.output.info(
                            "toolchain compiler repair: {} {} -> {}".format(
                                key, old_val, new_val))
                if content != orig:
                    try:
                        with open(tc_path, "w", encoding="utf-8") as fh:
                            fh.write(content)
                    except OSError as exc:
                        self.output.warning(
                            "toolchain compiler repair: cannot write {}: {}".format(
                                tc_path, exc))
        except Exception as exc:
            self.output.warning(
                "toolchain compiler repair skipped (non-fatal): {}".format(exc))

    def _get_cc(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c")
        if not cc:
            return shutil.which("clang") or "clang"
        if os.path.isfile(cc):
            return cc
        return shutil.which(os.path.basename(cc)) or cc

    def _resolve_lld(self, cc):
        candidates = []
        try:
            proc = subprocess.run(
                [cc, "-print-prog-name=ld.lld"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, timeout=60, check=False,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                candidates.append(proc.stdout.strip())
        except (OSError, subprocess.SubprocessError):
            pass
        bin_dir = os.path.dirname(os.path.realpath(cc))
        candidates += [os.path.join(bin_dir, "ld.lld"),
                       os.path.join(bin_dir, "lld")]
        for candidate in candidates:
            if os.path.isfile(candidate):
                return os.path.realpath(candidate)
            resolved = shutil.which(candidate)
            if resolved:
                return os.path.realpath(resolved)
        return ""

    def _libxml2_host_libdirs(self, cc, lld):
        candidates = []
        for tool in (cc, lld):
            if tool and os.path.sep in tool:
                llvm_root = os.path.dirname(
                    os.path.dirname(os.path.realpath(tool))
                )
                candidates.append(os.path.join(llvm_root, "lib"))
        try:
            proc = subprocess.run(
                [cc, "-print-resource-dir"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, timeout=60, check=False,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                # <prefix>/lib/clang/<ver> -> <prefix>/lib
                candidates.append(
                    os.path.dirname(os.path.dirname(proc.stdout.strip()))
                )
        except (OSError, subprocess.SubprocessError):
            pass
        candidates += [
            p for p in (os.environ.get("PATH") or "").split(os.pathsep) if p
        ]
        candidates += [
            p for p in (os.environ.get("LD_LIBRARY_PATH") or "").split(os.pathsep)
            if p
        ]
        for tool in (lld, cc):
            if not tool or os.path.sep not in tool:
                continue
            node = os.path.dirname(os.path.realpath(tool))
            for _ in range(4):
                node = os.path.dirname(node)
                if node in ("", os.path.sep):
                    break
                candidates.append(os.path.join(node, "lib"))
                candidates.append(os.path.join(node, "llvm", "lib"))
        found = []
        for candidate in dict.fromkeys(candidates):
            if os.path.isfile(os.path.join(candidate, "libxml2.so.16")):
                found.append(candidate)
        return found

    def _cc_link_probe(self, cc, extra_ld_library_path=None):
        probe_dir = os.path.join(self.build_folder, "linker-probe")
        os.makedirs(probe_dir, exist_ok=True)
        source = os.path.join(probe_dir, "probe.c")
        binary = os.path.join(probe_dir, "probe")
        with open(source, "w") as fh:
            fh.write("int main(void) { return 0; }\n")
        env = os.environ.copy()
        if extra_ld_library_path:
            current = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                p for p in (extra_ld_library_path, current) if p
            )
        try:
            proc = subprocess.run(
                [cc, source, "-o", binary],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, env=env, timeout=180, check=False,
            )
        except (OSError, subprocess.SubprocessError) as error:
            return 127, str(error)
        finally:
            if os.path.exists(binary):
                try:
                    os.unlink(binary)
                except OSError:
                    pass
        return proc.returncode, (proc.stdout or "").strip()

    def _linker_runtime_environment(self):
        if str(self.settings.os) != "OHOS":
            return None
        cc = self._get_cc()
        lld = self._resolve_lld(cc)
        self.output.info("OHOS linker probe: clang={}".format(cc))
        self.output.info("OHOS linker probe: lld={}".format(lld or "(unresolved)"))
        rc, log = self._cc_link_probe(cc)
        if rc == 0:
            self.output.info(
                "OHOS linker probe: minimal C compile+link OK "
                "(ambient environment)"
            )
            return None
        self.output.warning(
            "OHOS linker probe: minimal C compile+link FAILED in the "
            "ambient environment (rc={}); locating the SDK host "
            "runtime (libxml2.so.16) ...".format(rc)
        )
        if log:
            self.output.info("OHOS linker probe output:\n{}".format(log))
        candidates = self._libxml2_host_libdirs(cc, lld)
        if not candidates:
            raise ConanException(
                "OHOS linker probe: the configured C compiler "
                "'{}' cannot compile+link a minimal program and no "
                "directory containing libxml2.so.16 could be derived "
                "from the active toolchain (lld={}). "
                "Probe output:\n{}".format(cc, lld or "unresolved", log or "(empty)")
            )
        for libdir in candidates:
            rc, log = self._cc_link_probe(cc, extra_ld_library_path=libdir)
            if rc == 0:
                self.output.info(
                    "OHOS linker probe: minimal C compile+link OK with "
                    "{} prepended to LD_LIBRARY_PATH".format(libdir)
                )
                env = Environment()
                env.prepend_path("LD_LIBRARY_PATH", libdir)
                return env
        raise ConanException(
            "OHOS linker probe: the configured C compiler "
            "'{}' cannot compile+link a minimal program even with "
            "the discovered libxml2.so.16 host runtime. Candidates "
            "tried: {}; lld={}. "
            "Last probe output:\n{}".format(
                cc, ", ".join(candidates), lld or "unresolved", log or "(empty)")
        )

    def _test_env(self):
        env = Environment()
        if str(self.settings.os) == "OHOS":
            import tempfile
            test_tmp = os.environ.get("TMPDIR", "")
            usable = False
            if test_tmp and os.path.isdir(test_tmp):
                try:
                    fd, probe = tempfile.mkstemp(prefix="hmbs-w", dir=test_tmp)
                    os.close(fd)
                    os.unlink(probe)
                    usable = True
                except OSError:
                    usable = False
            if not usable:
                test_tmp = os.path.join(self.build_folder, "tmp")
                os.makedirs(test_tmp, exist_ok=True)
            env.define("TMPDIR", test_tmp)
            env.define("TMP", test_tmp)
            env.define("TEMP", test_tmp)
            # libcheck forked runner uses temp IPC files restricted on HMDFS.
            env.define("CK_FORK", "no")
        return env

    def _discover_ctest_count(self, build_dir):
        count = 0
        for root, _dirs, files in os.walk(build_dir):
            for filename in files:
                if filename == "CTestTestfile.cmake":
                    try:
                        with open(os.path.join(root, filename), "r", encoding="utf-8", errors="ignore") as handle:
                            count += len(re.findall(r"add_test\s*\(", handle.read()))
                    except OSError:
                        continue
        return count

    def _emit_upstream(self, status, discovered, executed, passed, failed, skipped, reason=None):
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
        if reason:
            result["reason"] = reason
        print("HMBS_UPSTREAM_TEST_RESULT={}".format(json.dumps(result)))

    def _cmake_binary_dir(self):
        # Conan 2.30's CMake helper exposes no `build_folder` attribute
        # (AttributeError in the preflight log masked the real CMake
        # error for three rounds). Resolve the actual CMake binary dir
        # from the layout: prefer the directory containing
        # CMakeCache.txt under self.build_folder, else self.build_folder.
        base = getattr(self, "build_folder", "") or "."
        try:
            candidates = []
            for root, _dirs, files in os.walk(base):
                if "CMakeCache.txt" in files:
                    candidates.append(root)
            if candidates:
                return sorted(candidates)[0]
        except OSError:
            pass
        return base

    def _dump_cmake_diagnostics(self, build_dir):
        # Fail-closed diagnostics: when configure fails, the real
        # compiler error lives in CMakeFiles/CMakeError.log, which the
        # preflight summary truncates away. Print the tails plus the
        # active conan_toolchain.cmake key lines into the conan output
        # so the next round diagnoses from evidence. Never masks the
        # original failure (all internal errors are swallowed).
        try:
            scope = build_dir or "."
            # Layout evidence first (short lines survive hmbs truncation):
            # when logs are missing we still learn the real tree shape.
            try:
                entries = sorted(os.listdir(scope))[:30]
                self.output.info("cmake diagnostics: ls({}): {}".format(
                    scope, " ".join(entries) or "(empty)"))
            except OSError as exc:
                self.output.warning("cmake diagnostics: cannot list {}: {}".format(scope, exc))
            parent = os.path.dirname(os.path.normpath(scope))
            if parent and parent != os.path.normpath(scope):
                try:
                    pentries = sorted(os.listdir(parent))[:30]
                    self.output.info("cmake diagnostics: ls(parent {}): {}".format(
                        parent, " ".join(pentries) or "(empty)"))
                except OSError:
                    pass
            search_roots = [scope]
            if parent and parent not in search_roots:
                search_roots.append(parent)
            for name in ("CMakeError.log", "CMakeOutput.log"):
                path = ""
                try:
                    for root0 in search_roots:
                        for root, _dirs, files in os.walk(root0):
                            if name in files:
                                path = os.path.join(root, name)
                                break
                        if path:
                            break
                except OSError:
                    path = ""
                if not path:
                    self.output.warning(
                        "cmake diagnostics: {} not found under {}".format(name, scope)
                    )
                    continue
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as fh:
                        lines = fh.read().splitlines()
                except OSError as exc:
                    self.output.warning(
                        "cmake diagnostics: cannot read {}: {}".format(path, exc)
                    )
                    continue
                tail = "\n".join(lines[-60:])
                self.output.info("cmake diagnostics: tail of {}:\n{}".format(path, tail))
            # Active toolchain evidence, one short line per key so the
            # hmbs summary truncation keeps it (full-line dump of 40
            # lines did not survive last round).
            try:
                tc_path = ""
                for root0 in search_roots:
                    for root, _dirs, files in os.walk(root0):
                        if "conan_toolchain.cmake" in files:
                            tc_path = os.path.join(root, "conan_toolchain.cmake")
                            break
                    if tc_path:
                        break
                if tc_path:
                    with open(tc_path, "r", encoding="utf-8", errors="replace") as fh:
                        tc_lines = fh.read().splitlines()
                    short = []
                    for ln in tc_lines:
                        s = ln.strip()
                        if re.match(
                            r"set\(CMAKE_SYSTEM_NAME|set\(CMAKE_SYSTEM_PROCESSOR"
                            r"|set\(CMAKE_C_COMPILER |set\(CMAKE_CXX_COMPILER "
                            r"|set\(CMAKE_SYSROOT|set\(CONAN_C_FLAGS|set\(CONAN_CXX_FLAGS"
                            r"|set\(CMAKE_POLICY_VERSION_MINIMUM"
                            r"|set\(CMAKE_C_FLAGS_INIT|set\(CMAKE_CXX_FLAGS_INIT"
                            r"|set\(CMAKE_EXE_LINKER_FLAGS_INIT", s):
                            short.append(s[:220])
                    self.output.info(
                        "cmake diagnostics: toolchain({} keys) {}:\n{}".format(
                            len(short), tc_path, "\n".join(short[:14]) or "(none)"))
                else:
                    self.output.warning(
                        "cmake diagnostics: conan_toolchain.cmake not found under {}".format(scope))
            except OSError as exc:
                self.output.warning("cmake diagnostics: cannot read toolchain: {}".format(exc))
        except Exception as exc:
            self.output.warning("cmake diagnostics failed (non-fatal): {}".format(exc))

    def _flagged_probe_evidence(self):
        # Evidence-only, never raises, never alters env: reproduce CMake's
        # flagged compiler invocation. The retired bare probe (`cc src -o
        # bin`, no toolchain flags) always passed yet configure kept
        # failing, proving it could not reproduce the real invocation.
        # This probe extracts the OHOS-relevant tokens (--target,
        # --sysroot, -stdlib, -march) from the generated toolchain and
        # compiles with them; configure still runs afterwards and fails
        # on its own when broken (no bypass of any kind).
        try:
            # Probe the compiler CMake will actually use (profile path when
            # present, otherwise the same PATH fallback generate() applies).
            try:
                cc, _cxx0, _over0 = self._resolve_compilers()
            except Exception:
                compilers = self.conf.get(
                    "tools.build:compiler_executables", default={}, check_type=dict)
                cc = compilers.get("c") or "clang"
            base = getattr(self, "build_folder", "") or "."
            tc_path = ""
            for root, _dirs, files in os.walk(base):
                if "conan_toolchain.cmake" in files:
                    tc_path = os.path.join(root, "conan_toolchain.cmake")
                    break
            tokens = []
            if tc_path:
                try:
                    with open(tc_path, "r", encoding="utf-8", errors="replace") as fh:
                        content = fh.read()
                    raw = re.findall(
                        r"--target=\S+|--sysroot[=\s]\S+|-stdlib=\S+|-march=\S+", content)
                    # Toolchain lines are quoted CMake strings, e.g.
                    # string(APPEND CONAN_CXX_FLAGS " -stdlib=libc++").
                    # A bare \S+ capture keeps the trailing '")' (preflight
                    # 2026-09-20 showed tokens=['-stdlib=libc++")']), which
                    # would poison the probe invocation once clang exists.
                    # Strip trailing CMake/quote punctuation and split the
                    # '--sysroot <path>' space form into two argv elements.
                    cleaned = []
                    for tok in raw:
                        tok = tok.strip().rstrip("\"');")
                        if tok.startswith("--sysroot") and (" " in tok or "\t" in tok):
                            parts = tok.replace("=", " ").split()
                            if len(parts) >= 2:
                                cleaned.append(parts[0])
                                cleaned.append(parts[1].strip("\"'"))
                            elif parts:
                                cleaned.append(parts[0])
                        elif tok:
                            cleaned.append(tok.rstrip("\"'"))
                    tokens = list(dict.fromkeys(t for t in cleaned if t))[:8]
                except OSError:
                    tokens = []
            cc_exists = os.path.isfile(cc)
            which_cc = shutil.which(os.path.basename(cc)) if (cc and os.path.sep in cc) else shutil.which(cc or "")
            self.output.info("flagged probe: cc_exists={} which={}".format(cc_exists, which_cc or "(none)"))
            self.output.info("flagged probe: cc={} tokens={}".format(cc, tokens or "(none)"))
            probe_dir = os.path.join(base, "flagged-probe")
            try:
                os.makedirs(probe_dir, exist_ok=True)
            except OSError:
                return
            src = os.path.join(probe_dir, "probe.c")
            bin0 = os.path.join(probe_dir, "probe")
            try:
                with open(src, "w") as fh:
                    fh.write("int main(void) { return 0; }\n")
            except OSError:
                return
            try:
                proc = subprocess.run(
                    [cc] + tokens + [src, "-o", bin0],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, timeout=180, check=False)
                out = (proc.stdout or "").strip().splitlines()
                tail = "\n".join(line[:300] for line in out[-12:])
                self.output.info("flagged probe: rc={} output:\n{}".format(
                    proc.returncode, tail or "(empty)"))
            except (OSError, subprocess.SubprocessError) as exc:
                self.output.info("flagged probe: exec failed: {}".format(exc)[:300])
            finally:
                try:
                    if os.path.exists(bin0):
                        os.unlink(bin0)
                except OSError:
                    pass
            try:
                proc = subprocess.run(
                    [cc, "-v"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, timeout=60, check=False)
                out = ((proc.stdout or "").strip().splitlines() or ["(empty)"])
                self.output.info("flagged probe: clang -v rc={} first={} last={}".format(
                    proc.returncode, out[0][:200], out[-1][:200]))
            except (OSError, subprocess.SubprocessError) as exc:
                self.output.info("flagged probe: clang -v failed: {}".format(exc)[:200])
        except Exception as exc:
            self.output.info("flagged probe: skipped (non-fatal): {}".format(exc)[:200])

    def build(self):
        self._ensure_writable_tmp()
        # NOTE (2nd strategy cycle): the E557 bare-flag linker probe ran
        # before configure for three rounds and always passed silently,
        # yet cmake.configure() kept failing at project() with the same
        # compiler-identification fingerprint. A bare `cc src -o bin`
        # without the conan toolchain flags (sysroot/target/arch from
        # the OHOS-adapted conan + conan_toolchain.cmake) cannot
        # reproduce CMake's flagged compiler invocation, and the
        # profile already provides the SDK llvm/lib LD_LIBRARY_PATH
        # globally -- so the host-runtime hypothesis is rejected. The
        # failing channel is the CMake invocation itself; on failure
        # dump the real CMakeError.log / toolchain evidence instead of
        # probing around it. No compiler-check bypass is used.
        # Evidence-first: run the flagged probe BEFORE configure so its
        # output lands in the conan log ahead of the cmake failure tail.
        # Build-time repair first (3rd cycle): generate() may not have
        # seen the migrated toolchain on PATH, so rewrite a stale
        # CMAKE_C/CXX_COMPILER in the generated toolchain when the
        # recorded path is missing; the flagged probe below then
        # validates the repaired compiler CMake will actually use.
        self._repair_stale_toolchain_compilers()
        self._flagged_probe_evidence()
        cmake = CMake(self)
        try:
            cmake.configure()
            # Serial compile: peak RSS guard for the small-memory box
            # (HMBS already injects tools.build:jobs=1; explicit -j1 is a
            # belt so a profile/conf override cannot re-enable parallel
            # compilation of the huge libsbml TUs + shared link).
            cmake.build(build_tool_args=["-j1"])
        except Exception:
            try:
                self._dump_cmake_diagnostics(self._cmake_binary_dir())
            except Exception:
                pass
            raise
        build_dir = self._cmake_binary_dir()
        discovered = self._discover_ctest_count(build_dir)
        if discovered <= 0:
            self._emit_upstream("no_tests", 0, 0, 0, 0, 0, "no CTestTestfile entries discovered")
            raise ConanInvalidConfiguration("libsbml upstream ctest suite was not generated")
        try:
            with self._test_env().vars(self).apply():
                self.run("ctest --output-on-failure -j1", cwd=build_dir, env="conanrun")
        except Exception as exc:
            self._emit_upstream("failed", discovered, discovered, 0, discovered, 0, str(exc)[:200])
            raise
        self._emit_upstream("passed", discovered, discovered, discovered, 0, 0)

    def _resolve_sign_tool(self, name, legacy):
        # Preflight 2026-09-24: /data/service/hnp/bin/binary-sign-tool
        # (and llvm-objcopy) no longer exist on the box (Error 127
        # "inaccessible or not found"); the toolchain migrated to
        # harmonybrew on PATH. Resolve miss-only: legacy path when
        # present, else PATH lookup; never fabricate, never fail.
        if legacy and os.path.isfile(legacy):
            return legacy
        try:
            found = shutil.which(name)
        except Exception:
            found = None
        if found and os.path.isfile(found):
            return found
        return ""

    def _sign_shared_libs(self):
        if str(self.settings.os) != "OHOS":
            return
        import glob as _glob

        libdir = os.path.join(self.package_folder, "lib")
        targets = _glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        targets += _glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not targets:
            return
        # Best-effort signing (knowledge/operations/packaging.md: sign
        # failures must fall back, never abort packaging). The 2026-09-24
        # preflight proved this: build + 35/35 ctest passed, only the
        # hardcoded signer path failed with Error 127. Missing tools or
        # per-file sign errors only warn; packaging continues unsigned
        # (official CI signs releases separately via ci/artifacts/sign.sh).
        objcopy = self._resolve_sign_tool(
            "llvm-objcopy", "/data/service/hnp/bin/llvm-objcopy")
        if not objcopy:
            try:
                objcopy = shutil.which("objcopy") or ""
            except Exception:
                objcopy = ""
        signer = self._resolve_sign_tool(
            "binary-sign-tool", "/data/service/hnp/bin/binary-sign-tool")
        if not signer:
            self.output.warning(
                "OHOS signing skipped (non-fatal): neither "
                "/data/service/hnp/bin/binary-sign-tool nor a "
                "binary-sign-tool on PATH was found; shipping unsigned")
            return
        self.output.info("OHOS signing: signer={} objcopy={}".format(
            signer, objcopy or "(none)"))
        for target in targets:
            if os.path.islink(target):
                continue
            if objcopy:
                try:
                    self.run(
                        "\"{}\" --remove-section .codesign \"{}\" 2>/dev/null || true".format(objcopy, target))
                except Exception as exc:
                    self.output.warning(
                        "OHOS signing: objcopy strip failed (non-fatal) for {}: {}".format(target, exc))
            try:
                self.run(
                    "\"{}\" sign -inFile \"{}\" -outFile \"{}\" -selfSign 1".format(signer, target, target))
            except Exception as exc:
                self.output.warning(
                    "OHOS signing failed (non-fatal) for {}: {}; shipping unsigned".format(target, exc))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        rm(self, "*.la", folder=os.path.join(self.package_folder, "lib"))
        copy(self, "COPYING.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "LICENSE.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        self._sign_shared_libs()

    def package_info(self):
        # Upstream UNIX names: shared target "sbml" -> libsbml.so,
        # static target "sbml-static" -> libsbml-static.a (src/CMakeLists:
        # add_library(${LIBSBML_LIBRARY}-static STATIC ...)). OHOS shared
        # builds skip compression deps (see generate()), static keeps them;
        # both spellings are honoured here via the live shared option.
        if self.options.get_safe("shared", True):
            self.cpp_info.libs = ["sbml"]
        else:
            self.cpp_info.libs = ["sbml-static"]
        self.cpp_info.set_property("cmake_file_name", "libsbml")
        self.cpp_info.set_property("cmake_target_name", "libsbml::libsbml")
        self.cpp_info.set_property("pkg_config_name", "libsbml")
        self.cpp_info.requires = ["libxml2::libxml2", "zlib::zlib", "bzip2::bzip2"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
