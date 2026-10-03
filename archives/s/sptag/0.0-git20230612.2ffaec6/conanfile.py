#!/usr/bin/env python3
"""Conan recipe — sptag 0.0-git20230612.2ffaec6 (OHOS aarch64 adaptation).

SPTAG (Space Partition Tree And Graph) is Microsoft Research's large-scale
vector approximate nearest neighbor search library (ANN indexes: KDT/BKT
trees + relative neighborhood graph, plus ANNServing/Tools executables).

Upstream build: CMake. Key OHOS adaptations (see patches/):
  - Top-level CMake only accepts GCC/MSVC and overwrites Conan toolchain
    flags -> accept Clang like GNU, append instead of overwrite, and take
    Boost from the recipe via SPTAG_BOOST_* (0001).
  - x86 SIMD (-mavx2... flags, SSE/AVX/AVX512 intrinsics, cpuid,
    _mm_malloc, _mm_prefetch) has no aarch64 equivalent -> portable
    scalar fallbacks with identical numerics (0002-0006). The runtime
    selectors already fall back to the scalar kernels when no x86
    instruction set is detected, so the wrappers only guarantee that
    every declared symbol still links on ARM.
  - Boost comes from the OHOS-adapted component packages
    (boost1.84/1.84.0: full header tree + filesystem/regex,
    boost1.84-thread, boost1.84-serialization, boost1.84-wserialization),
    injected as absolute static-library paths (static link order:
    wserialization, serialization, thread, filesystem, regex, pthread).
  - Boost.Test is header-only on OHOS (unit_test_framework is not built
    there): the test CMake drops the component and main.cpp uses the
    single-header runner (0007). The 154 upstream cases are self-contained
    (synthetic data generated at runtime, no network/datasets).
    Upstream registers no ctest target, so build() runs SPTAGTest directly
    and counts "Leaving test case" lines for the HMBS evidence marker.
  - OHOS musl lacks pthread_setaffinity_np (glibc extension): the thread
    affinity helper uses sched_setaffinity(0, ...) on musl/OHOS while the
    glibc path is unchanged (build()-time replace, not patches/: conan's
    patcher applies hunks without offset search). All callers pin the
    calling thread itself, so the replacement is semantically identical.
  - HarmonyOS/HongMeng may reject O_DIRECT and lack kernel AIO: AsyncFileIO
    keeps O_DIRECT + AIO first and falls back to plain open + sync pread
    only on failure (build()-time replace, same pattern).
  - ThirdParty/zstd is a git submodule (empty in the source tarball), so
    source() vendors the period-correct zstd 1.5.5 release tarball.
  - Python/Java/C#/CUDA/MPI autodetection is disabled via
    CMAKE_DISABLE_FIND_PACKAGE_* (library + CLI tools + C++ tests only);
    GPU=OFF (no CUDA on OHOS).
"""
import glob
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file


class SptagConan(ConanFile):
    name = "sptag"
    version = "0.0-git20230612.2ffaec6"
    description = ("SPTAG: Microsoft Space Partition Tree And Graph library "
                   "for large-scale vector approximate nearest neighbor search")
    license = "MIT"
    homepage = "https://github.com/microsoft/SPTAG"
    url = ""  # CI fills this
    topics = ("ann", "vector-search", "nearest-neighbor", "graph-index")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # R32: accept both Linux (dev builds) and OHOS.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "sptag supports Linux and OHOS, not %s" % self.settings.os)

    def requirements(self):
        # Full Boost 1.84 header tree + filesystem/regex static libs.
        self.requires("boost1.84/1.84.0",
                      transitive_headers=True, transitive_libs=True)
        # Remaining compiled Boost libs SPTAG links (AnnService tools and
        # the SPTAGTest binary link ${Boost_LIBRARIES}).
        # NOTE: boost1.84-serialization is intentionally NOT required:
        # boost1.84-wserialization already compiles AND packages both
        # libboost_serialization.a and libboost_wserialization.a (see its
        # build()/package(): core+std_wstreambuf sets + WSOURCES, glob
        # libboost_*.a), so a separate serialization package only adds a
        # fourth colliding BoostConfig.cmake with duplicate Boost::headers
        # / Boost::serialization targets. Three Boost packages suffice.
        self.requires("boost1.84-thread/1.84.0",
                      transitive_headers=True, transitive_libs=True)
        self.requires("boost1.84-wserialization/1.84.0",
                      transitive_headers=True, transitive_libs=True)
        # zlib override: boost1.84 requests conancenter zlib/1.3.1 whose
        # CMake build does not know CMAKE_SYSTEM_NAME=HarmonyOS and fails
        # before compiling (see preflight: "System is unknown to cmake" in
        # zlib/1.3.1 configure). The in-repo zlib/1.3.1.2 vendors the same
        # 1.3.1 source but builds via ./configure --static + make, bypassing
        # the CMake platform check entirely. Override here so the whole graph
        # (boost1.84 -> zlib) resolves to the OHOS-proven recipe. This cannot
        # be fixed from sptag's generate()/toolchain patching: each dependency
        # runs its own generate()/build() with the shared profile compiler.
        self.requires("zlib/1.3.1.2", override=True)
        # OpenMP: provided by the OHOS SDK clang toolchain itself
        # (-fopenmp auto-links the SDK libomp, cf. combblas/aaphoto/faiss
        # which need no conan OpenMP package). The conancenter libomp/15.0.4
        # recipe cannot configure on OHOS (CMAKE_SYSTEM_NAME=HarmonyOS is
        # unknown to its CMake + compiler test fails), so no conan dep here.

    def layout(self):
        cmake_layout(self)

    @staticmethod
    def _abs_dirs(dep, dirs):
        """cpp_info dirs may be package-relative; make them absolute."""
        return [d if os.path.isabs(d) else os.path.join(dep.package_folder, d)
                for d in dirs]

    def _find_boost_lib(self, stem):
        """Absolute path of a Boost static archive across component pkgs."""
        for ref in ("boost1.84-wserialization",
                    "boost1.84-thread", "boost1.84"):
            dep = self.dependencies[ref]
            for d in self._abs_dirs(dep, dep.cpp_info.libdirs):
                for cand in glob.glob(os.path.join(d, stem + ".a")):
                    return cand
        raise ConanException(
            "%s.a not found in Boost component packages" % stem)

    def _boost_libraries(self):
        """Absolute static Boost libs in correct (dependents-first) order."""
        libs = [self._find_boost_lib(s) for s in (
            "libboost_wserialization",
            "libboost_serialization",
            "libboost_thread",
            "libboost_filesystem",
            "libboost_regex",
        )]
        # boost1.84-thread declares system_libs pthread; its OHOS test
        # links -lpthread successfully, so propagate it here as well.
        libs.append("pthread")
        return libs

    def _resolve_compiler(self, configured, names):
        # True device migrated clang from /data/service/hnp/bin to
        # ~/usr/local/bin but the shared profile still points at the old
        # path: prefer the configured absolute path only when it exists,
        # otherwise resolve via PATH or the ~/usr/local/bin fallback
        # (traildb/0.6 + zydis/4.1.1 precedent, same device issue).
        if configured and os.path.isabs(configured) \
                and os.path.isfile(configured):
            return configured
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        home_bin = os.path.join(os.path.expanduser("~"), "usr", "local",
                                "bin")
        for name in names:
            cand = os.path.join(home_bin, name)
            if os.path.isfile(cand):
                return cand
        return configured or names[0]

    def _query_compiler_libdirs(self, cc_path):
        # Ask the live compiler where its libraries live (clang
        # -print-search-dirs / -print-resource-dir). This is layout-free:
        # harmonybrew, migrated ~/usr/local/bin, and /data/service/hnp/bin
        # all answer correctly without hardcoding their prefixes. Only dirs
        # actually containing libomp.so are returned.
        found = []
        if not cc_path:
            return found
        try:
            for args in (["-print-search-dirs"], ["-print-resource-dir"]):
                try:
                    p = subprocess.run(
                        [cc_path] + args, capture_output=True, text=True,
                        timeout=20)
                except Exception:
                    continue
                out = (p.stdout or "") + "\n" + (p.stderr or "")
                # -print-search-dirs: "libraries: =/a:/b:...".
                for token in out.replace(";", ":").split(":"):
                    token = token.strip().strip(" =\t\r\n\"'")
                    if not token or not token.startswith("/"):
                        continue
                    token = os.path.normpath(token)
                    if len(token) > 400:
                        continue
                    try:
                        if os.path.isfile(os.path.join(token, "libomp.so")) \
                                and token not in found:
                            found.append(token)
                        # Resource dir itself is .../lib/clang/15; the
                        # runtime often sits one level up or in
                        # lib/linux/<triple>.
                        for extra in (os.path.dirname(token),
                                      os.path.join(token, "linux",
                                                   "aarch64-linux-ohos"),
                                      os.path.join(token, "lib", "linux",
                                                   "aarch64-linux-ohos")):
                            if os.path.isfile(
                                    os.path.join(extra, "libomp.so")) \
                                    and extra not in found:
                                found.append(extra)
                    except Exception:
                        continue
        except Exception:
            pass
        return found

    def _prefix_omp_candidates(self, cc_path):
        # Toolchain-prefix candidates derived from the live compiler path:
        # prefix = grandparent of <prefix>/bin/clang. Covers harmonybrew
        # (~/.harmonybrew, /storage/.../.harmonybrew), ~/usr/local, and the
        # legacy /data/service/hnp/bin layouts without naming any of them.
        # Plus the repo-profile authoritative SDK dir (exact version first,
        # then version-drift wildcard) and current LD_LIBRARY_PATH entries.
        cands = []
        try:
            seeds = []
            if cc_path:
                seeds.append(cc_path)
                try:
                    seeds.append(os.path.realpath(cc_path))
                except Exception:
                    pass
            for seed in seeds:
                try:
                    bdir = os.path.dirname(seed)
                except Exception:
                    continue
                if not bdir:
                    continue
                prefix = os.path.normpath(os.path.join(bdir, ".."))
                for d in (os.path.join(bdir, "..", "lib",
                                       "aarch64-linux-ohos"),
                          os.path.join(bdir, "..", "lib"),
                          os.path.join(bdir, "..", "lib64"),
                          os.path.join(prefix, "lib",
                                       "aarch64-linux-ohos"),
                          os.path.join(prefix, "lib"),
                          os.path.join(prefix, "lib64"),
                          os.path.join(prefix, "llvm", "lib"),
                          os.path.join(prefix, "lib", "llvm", "lib")):
                    nd = os.path.normpath(d)
                    if nd not in cands:
                        cands.append(nd)
            # Repo-profile authoritative SDK dir (ci/conan/profiles/ohos-aarch64
            # [buildenv]): exact pinned version first, wildcard for drift.
            cands.append("/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
                         "ohos/native/llvm/lib")
            try:
                for d in sorted(glob.glob(
                        "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/"
                        "ohos/native/llvm/lib")):
                    if d not in cands:
                        cands.append(d)
            except Exception:
                pass
            # Whatever the current process already searches.
            try:
                for d in os.environ.get("LD_LIBRARY_PATH", "").split(
                        os.pathsep):
                    if d and d not in cands:
                        cands.append(d)
            except Exception:
                pass
            try:
                hb = os.path.join(os.path.expanduser("~"), "usr", "local",
                                  "lib")
                if hb not in cands:
                    cands.append(hb)
            except Exception:
                pass
        except Exception:
            pass
        return cands

    def _sdk_omp_libdirs(self, cc_path):
        # OHOS SDK libomp lives next to the toolchain, not on the default
        # loader path (faiss/1.15.0 precedent). Without it any -fopenmp
        # binary (SPTAGTest, test_sptag) dies at startup with
        # "Error loading shared library libomp.so" + undefined
        # __kmpc_*/omp_* relocations -> shell reports Error 127 even though
        # the binary itself exists and is executable. Only dirs actually
        # containing libomp.so are returned; empty list = no-op (e.g. Linux
        # dev builds with system libomp).
        # Round 4 hardening: the old bindir-relative guess alone returned
        # NONE on the harmonybrew layout (clang at
        # ~/.harmonybrew/bin/clang), so this now unions three sources:
        # prefix/profile candidates, direct compiler query, and the legacy
        # bindir-relative derivation. Static -static-openmp linking (see
        # build()) is the primary fix; these dirs remain the fallback.
        found = []
        try:
            for d in self._prefix_omp_candidates(cc_path):
                try:
                    if d and d not in found and os.path.isfile(
                            os.path.join(d, "libomp.so")):
                        found.append(d)
                except Exception:
                    continue
            for d in self._query_compiler_libdirs(cc_path):
                if d not in found:
                    found.append(d)
            seeds = []
            if cc_path:
                seeds.append(cc_path)
                try:
                    seeds.append(os.path.realpath(cc_path))
                except Exception:
                    pass
                if not os.path.dirname(cc_path):
                    try:
                        _w = shutil.which(cc_path)
                        if _w:
                            seeds.append(_w)
                            seeds.append(os.path.realpath(_w))
                    except Exception:
                        pass
            cands = []
            for seed in seeds:
                try:
                    bdir = os.path.dirname(seed)
                except Exception:
                    continue
                if not bdir:
                    continue
                cands.append(os.path.normpath(
                    os.path.join(bdir, "..", "lib", "aarch64-linux-ohos")))
                cands.append(os.path.normpath(
                    os.path.join(bdir, "..", "lib")))
                cands.append(os.path.normpath(
                    os.path.join(bdir, "..", "lib64")))
            for d in cands:
                try:
                    if d and d not in found and os.path.isfile(
                            os.path.join(d, "libomp.so")):
                        found.append(d)
                except Exception:
                    continue
        except Exception:
            pass
        return found

    def _fix_generated_toolchain_compiler(self, configured_map, c, cxx):
        # The cache_variables pin alone did not override the stale profile
        # compiler on the true device in past tasks, so correct the
        # generated conan_toolchain.cmake single file as well -- only when
        # the configured path is missing and a live one was resolved.
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
            else:
                self.output.warning(
                    "HMBS diag toolchain file not found: %s" % path)
        except Exception as e:
            self.output.warning("HMBS diag toolchain fix failed: %s" % e)

    def _hmbs_append_lowmem_block(self):
        # Constrained-device additive low-opt (libgridxc precedent): append
        # -O1 -g0 so the tail wins over upstream -O3/-g without dropping any
        # other flag. Idempotent via the HMBS_LOWMEM marker. The extra_cflags
        # above flow through the toolchain INIT variables, but upstream
        # overwrites CMAKE_CXX_FLAGS via set() and the vendored zstd
        # sub-build re-reads base + per-config variables, so this tail block
        # covers base + each config + directory compile options.
        try:
            gf = getattr(self, "generators_folder", None)
            path = os.path.join(gf, "conan_toolchain.cmake") if gf else None
            if not path or not os.path.isfile(path):
                self.output.warning(
                    "HMBS diag lowmem block skipped, no toolchain: %s" % path)
                return
            with open(path, "r", encoding="utf-8",
                      errors="replace") as f:
                text = f.read()
            if "HMBS_LOWMEM" in text:
                return
            block = (
                "\n# HMBS_LOWMEM sptag: constrained-device additive low-opt\n"
                "# (preflight SSH dropped at ~27% compiling zstd compress TUs\n"
                "# with jobs=1; tail -O1 -g0 wins over -O3/-g, nothing removed).\n"
                "string(APPEND CMAKE_C_FLAGS \" -O1 -g0\")\n"
                "string(APPEND CMAKE_CXX_FLAGS \" -O1 -g0\")\n"
                "foreach(_hmbs_cfg IN ITEMS RELEASE RELWITHDEBINFO "
                "MINSIZEREL DEBUG)\n"
                "  string(APPEND CMAKE_C_FLAGS_${_hmbs_cfg} \" -O1 -g0\")\n"
                "  string(APPEND CMAKE_CXX_FLAGS_${_hmbs_cfg} \" -O1 -g0\")\n"
                "endforeach()\n"
                "add_compile_options(-O1 -g0)\n"
            )
            with open(path, "a", encoding="utf-8") as f:
                f.write(block)
            self.output.info(
                "HMBS diag appended lowmem block to %s" % path)
        except Exception as e:
            self.output.warning("HMBS diag lowmem block failed: %s" % e)

    @staticmethod
    def _pthread_compat_lines():
        # Byte-identical content for generate() (build-folder shim,
        # fallback) and build() (source-tree header, primary): one shared
        # include guard so both -include flags can coexist. Active on OHOS
        # or any non-glibc (musl) libc; strict no-op on glibc. C and C++
        # safe (the vendored zstd C files also see it via directory scope).
        return [
            "#ifndef SPTAG_OHOS_PTHREAD_COMPAT_H",
            "#define SPTAG_OHOS_PTHREAD_COMPAT_H",
            "#pragma once",
            "#include <pthread.h>",
            "#if defined(__OHOS__) || !defined(__GLIBC__)",
            "#ifndef PTHREAD_CANCEL_DISABLE",
            "#define PTHREAD_CANCEL_DISABLE 0",
            "#endif",
            "#ifndef PTHREAD_CANCEL_ENABLE",
            "#define PTHREAD_CANCEL_ENABLE 1",
            "#endif",
            "#ifndef PTHREAD_CANCEL_DEFERRED",
            "#define PTHREAD_CANCEL_DEFERRED 0",
            "#endif",
            "#ifndef PTHREAD_CANCEL_ASYNCHRONOUS",
            "#define PTHREAD_CANCEL_ASYNCHRONOUS 1",
            "#endif",
            "static inline int sptag_pthread_setcancelstate_noop(int s, int *o)",
            "{ if (o) { *o = s; } return 0; }",
            "static inline int sptag_pthread_setcanceltype_noop(int t, int *o)",
            "{ if (o) { *o = t; } return 0; }",
            "#ifdef pthread_setcancelstate",
            "#undef pthread_setcancelstate",
            "#endif",
            "#ifdef pthread_setcanceltype",
            "#undef pthread_setcanceltype",
            "#endif",
            "#define pthread_setcancelstate sptag_pthread_setcancelstate_noop",
            "#define pthread_setcanceltype sptag_pthread_setcanceltype_noop",
            "#endif",
            "#endif",
            "",
        ]

    def generate(self):
        tc = CMakeToolchain(self)
        # R26 does not apply (sptag is not a system-name library); keep
        # the flag for the bundled zstd sub-build.
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # aarch64/OHOS: upstream always builds BOTH SPTAGLib (SHARED) and
        # SPTAGLibStatic from non-PIC static archives (DistanceUtils etc).
        # ld.lld on aarch64 rejects non-PIC objects in a shared link
        # (R_AARCH64_ADR_PREL_PG_HI21 / LDST8_ABS_LO12_NC against
        # SPTAG::COMMON::InstructionSet::CPU_Rep, "recompile with -fPIC").
        # x86_64 tolerates text relocations so this never surfaced there.
        # Use the CMake-level switch (not a raw -fPIC flag): upstream
        # overwrites CMAKE_CXX_FLAGS via set(), which can swallow toolchain
        # extra flags, while POSITION_INDEPENDENT_CODE is a per-target
        # property that survives and also propagates to the vendored zstd
        # sub-build via add_subdirectory.
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        # CMake 4.x compat: the vendored zstd 1.5.5 sub-build declares
        # cmake_minimum_required(VERSION 2.8.12), which CMake >= 4 refuses
        # ("Compatibility with CMake < 3.5 has been removed"). The worker
        # cmake is 4.4.3 (HMBS_BUILD_TOOLS). Belt and suspenders: toolchain
        # CACHE hint here (combblas notes it alone does not take effect at
        # the minimum-version check) + command-line -D in build().
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # No CUDA on OHOS; keep the full build (tools + SPTAGTest).
        tc.variables["GPU"] = False
        # Wrappers (Python/Java/C#) and optional MPI/CUDA probing need
        # toolchains absent on OHOS; disable deterministically instead of
        # depending on worker whims (missing swig/JDK would break configure).
        for pkg in ("Python3", "Python2", "JNI", "MPI", "CUDA"):
            tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_" + pkg] = True
        # Boost (patch 0001): full 1.84 header tree + absolute static libs.
        boost = self.dependencies["boost1.84"]
        boost_inc = self._abs_dirs(boost, boost.cpp_info.includedirs)[0]
        tc.variables["SPTAG_BOOST_INCLUDE_DIR"] = boost_inc
        tc.variables["SPTAG_BOOST_LIBRARIES"] = ";".join(self._boost_libraries())
        # OpenMP comes from the OHOS SDK toolchain (clang -fopenmp, already
        # in SPTAG's own CMAKE_CXX_FLAGS via patch 0001); find_package(OpenMP)
        # resolves the SDK omp.h/libomp without any conan -I/-L injection
        # (combblas precedent).
        # OHOS musl lacks the POSIX thread-cancellation API
        # (pthread_setcancelstate/setcanceltype), which Boost 1.84
        # core/detail/sp_thread_sleep.hpp calls around nanosleep()
        # (pulled in via smart_ptr/detail/yield_k.hpp -> SearchService.cpp).
        # The previous -DBOOST_SP_NO_PTHREAD_SETCANCELSTATE had no effect:
        # the 1.84 header never checks that macro (only !defined(__ANDROID__),
        # the __OHOS__ guard exists solely upstream on develop). The prior
        # generate()-only -include shim re-failed with the same fingerprint
        # (build error line shifted +57 but identical undeclared-identifier
        # errors), so the primary channel is now CMake-level (see build():
        # source-tree header + add_compile_options, immune to toolchain
        # INIT-flag handling and with a broadened guard). This
        # build-folder shim stays as a fallback; both headers share the
        # SPTAG_OHOS_PTHREAD_COMPAT_H guard and byte-identical content, so
        # a double -include is a harmless no-op. No-op on glibc.
        # CXX-only: the vendored zstd huf_decompress_amd64.S TU is forced to
        # LANGUAGE C by its CMake (near-empty on aarch64 via
        # ZSTD_ENABLE_ASM_X86_64_BMI2); injecting this C header into it via
        # extra_cflags breaks the assembler (true-device: alltypes.h /
        # pthread.h / compat-header "unexpected token" cascade). Only Boost
        # C++ TUs need the shim, so extra_cxxflags alone suffices.
        _shim_lines = self._pthread_compat_lines()
        try:
            os.makedirs(self.build_folder, exist_ok=True)
            _stub = os.path.join(
                self.build_folder, "sptag_ohos_pthread_stub.h"
            )
            with open(_stub, "w", encoding="utf-8", newline="\n") as _f:
                _f.write("\n".join(_shim_lines))
            self.output.info("sptag: OHOS pthread shim -> %s" % _stub)
            _inc = "-include %s" % _stub
            if _inc not in tc.extra_cxxflags:
                tc.extra_cxxflags.append(_inc)
        except Exception as _exc:
            self.output.warning(
                "sptag: pthread shim injection failed (%s)" % _exc
            )
        # HMBS lowmem: preflight SSH dropped mid-compile at ~27% inside the
        # vendored zstd 1.5.5 compress TUs (huf_compress/zstd_compress*) with
        # jobs=1 already enforced. Those Release -O3 TUs are the heaviest in
        # this build. Additive only (-O1 -g0 appended, tail wins over -O3/-g;
        # all other flags kept, all assertions kept). Propagates to the zstd
        # sub-build via add_subdirectory + the toolchain tail block below.
        for _lm in ("-O1", "-g0"):
            if _lm not in tc.extra_cflags:
                tc.extra_cflags.append(_lm)
            if _lm not in tc.extra_cxxflags:
                tc.extra_cxxflags.append(_lm)
        # Pin live compilers: the shared profile may still point at the
        # migrated /data/service/hnp/bin/clang path while the true device
        # keeps clang under ~/usr/local/bin or PATH (traildb precedent).
        try:
            _compilers = self.conf.get("tools.build:compiler_executables",
                                       default=None)
        except Exception:
            _compilers = None
        if not isinstance(_compilers, dict):
            _compilers = {}
        _c = self._resolve_compiler(_compilers.get("c"), ("clang", "cc"))
        _cxx = self._resolve_compiler(_compilers.get("cpp"),
                                      ("clang++", "c++"))
        if _c:
            tc.cache_variables["CMAKE_C_COMPILER"] = _c
        if _cxx:
            tc.cache_variables["CMAKE_CXX_COMPILER"] = _cxx
        self.output.info("HMBS diag compilers c=%s cxx=%s" % (_c, _cxx))
        tc.generate()
        self._fix_generated_toolchain_compiler(_compilers, _c, _cxx)
        self._hmbs_append_lowmem_block()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # ThirdParty/zstd is a git submodule: empty in the source tarball.
        # Vendor the period-correct zstd release so the bundled sub-build
        # works exactly as upstream designed it.
        zstd = self.conan_data["third_party"]["zstd"]
        get(self, url=zstd["url"], sha256=zstd["sha256"], strip_root=True,
            destination=os.path.join(self.source_folder, "ThirdParty", "zstd"))

    def _hmbs_emit_upstream(self, payload):
        line = "HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(
            payload, separators=(",", ":"))
        # Dual-channel: conan output + raw stdout so preflight catches it.
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass
        try:
            bf = getattr(self, "build_folder", None)
            if bf:
                with open(os.path.join(bf, "hmbs_upstream.json"),
                          "w", encoding="utf-8") as f:
                    json.dump(payload, f)
        except Exception as e:
            self.output.warning("HMBS diag persist upstream failed: %s" % e)
        return line

    def build(self):
        apply_conandata_patches(self)
        # Constrained-device source-level low-opt (differs from the prior
        # toolchain-tail attempt): the toolchain file is included BEFORE
        # project(), while top CMakeLists does
        # set(CMAKE_CXX_FLAGS_RELEASE "${...} -DNDEBUG -O3 -march=native")
        # AFTERWARDS, so any -O1 appended to the toolchain lands BEFORE
        # -O3 on the command line and loses (last -O wins; preflight kept
        # dying mid-compile in BKTIndex/IQuantizer/KDTree template TUs with
        # jobs=1 despite the tail block). Edit the source flag itself so the
        # downgrade is effective; also drop -march=native (x86-centric, bloats
        # ARM codegen/memory) and force -g0. Numerics unchanged (scalar
        # fallbacks already bit-identical; DistanceTest validates).
        replace_in_file(
            self,
            os.path.join(self.source_folder, "CMakeLists.txt"),
            'set (CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -DNDEBUG -O3 -march=native")',
            'set (CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} -DNDEBUG -O1 -g0")  # HMBS lowmem: -O3->-O1, drop -march=native on ARM\n'
            'if(CMAKE_CXX_COMPILER_ID MATCHES "Clang")\n'
            '    # HMBS static OpenMP: test_package died with Error 127\n'
            '    # (libomp.so not on the loader path, omp_dirs=NONE on the\n'
            '    # harmonybrew layout after 3 rounds of RPATH/LD fixes).\n'
            '    # -static-openmp embeds the runtime so neither SPTAGTest nor\n'
            '    # consumers need LD_LIBRARY_PATH/RPATH. Clang-only: GCC dev\n'
            '    # builds keep shared -fopenmp (GCC uses -static-libgomp).\n'
            '    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -static-openmp")\n'
            '    set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -static-openmp")\n'
            '    set(CMAKE_SHARED_LINKER_FLAGS "${CMAKE_SHARED_LINKER_FLAGS} -static-openmp")\n'
            'endif()')
        # OHOS/musl pthread-cancel compat, CMake channel (primary, see
        # generate() comment): write the compat header into the source tree
        # and force-include it for the C++ parts below (AnnService + Test),
        # which pull Boost 1.84 sp_thread_sleep. The injection point is
        # AFTER add_subdirectory(ThirdParty/zstd/...): directory-scope
        # add_compile_options only covers subdirectories added after the
        # call, so the vendored zstd build never sees the -include. That
        # matters because zstd forces huf_decompress_amd64.S to LANGUAGE C
        # (near-empty on aarch64 via ZSTD_ENABLE_ASM_X86_64_BMI2) and a
        # COMPILE_LANGUAGE:C guard still matches it -- the previous round's
        # genex scoping failed for exactly this reason (identical .S errors
        # re-ran at build()+11 lines). zstd is pure C and needs no shim;
        # only Boost C++ TUs do. Line-number free replace_in_file (same
        # pattern as the VectorIndex/pthread affinity fixes above).
        _compat_path = os.path.join(self.source_folder,
                                    "ohos_pthread_compat.h")
        try:
            with open(_compat_path, "w", encoding="utf-8",
                       newline="\n") as _cf:
                _cf.write("\n".join(self._pthread_compat_lines()))
            self.output.info("sptag: pthread compat header -> %s"
                             % _compat_path)
        except Exception as _exc:
            raise ConanException(
                "sptag: cannot write pthread compat header: %s" % _exc)
        replace_in_file(
            self,
            os.path.join(self.source_folder, "CMakeLists.txt"),
            'add_subdirectory (ThirdParty/zstd/build/cmake)',
            'add_subdirectory (ThirdParty/zstd/build/cmake)\n'
            '# OHOS/musl: force-include the pthread-cancel compat header\n'
            '# for the C++ targets below (Boost 1.84 sp_thread_sleep needs\n'
            '# pthread_setcancelstate, absent on musl; no-op on glibc).\n'
            '# Placed AFTER the zstd subdirectory: directory scope only\n'
            '# covers subdirs added later, so the vendored zstd ASM-as-C TU\n'
            '# (huf_decompress_amd64.S, LANGUAGE C) never sees this header.\n'
            'if(NOT MSVC)\n'
            '    add_compile_options("$<$<COMPILE_LANGUAGE:C>:-include' + _compat_path + '>" "$<$<COMPILE_LANGUAGE:CXX>:-include' + _compat_path + '>")\n'
            'endif()')
        # Clang -Wnon-pod-varargs is a hard error on the OHOS clang:
        # AnnService/src/Core/VectorIndex.cpp passes a std::string through
        # the C-variadic Logger::Logging(..., const char*, ...) (UB, aborts
        # at runtime per the diagnostic). Every sibling %s call site in the
        # tree already passes .c_str() (IQuantizer.cpp x2,
        # Quantizer/main.cpp); this one was missed upstream. Fixed here
        # instead of patches/ because this file uses CRLF line endings while
        # the patch pipeline (gen_patches.py) requires LF-only sources; the
        # single-line anchor contains no newline so it matches either way.
        # replace_in_file raises if the pattern is absent: fail loudly.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "AnnService", "src", "Core",
                         "VectorIndex.cpp"),
            "Helper::Convert::ConvertToString<VectorValueType>"
            "(m_pQuantizer->GetReconstructType()));",
            "Helper::Convert::ConvertToString<VectorValueType>"
            "(m_pQuantizer->GetReconstructType()).c_str());")
        # OHOS musl provides no pthread_setaffinity_np (glibc extension,
        # knowledge E211): SetThreadAffinity in AnnService/src/Helper/
        # AsyncFileReader.cpp uses sched_setaffinity(0, ...) on musl/OHOS
        # while the glibc path is unchanged. Every caller pins the calling
        # thread itself (ListionIOCP, IndexSearcher, SSDIndex), so pid 0 is
        # semantically identical. Fixed here instead of patches/: conan's
        # patcher applies hunks without offset search, so a context-correct
        # patch still failed on device over a hunk header line number;
        # replace_in_file anchors are line-number free and raise loudly
        # when absent (same pattern as the VectorIndex fix above).
        # <sched.h> provides sched_setaffinity/cpu_set_t on musl.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "AnnService", "inc", "Helper",
                         "AsyncFileReader.h"),
            "#include <linux/aio_abi.h>",
            "#include <linux/aio_abi.h>\n"
            "#include <sched.h>  // sched_setaffinity: musl/OHOS has no "
            "pthread_setaffinity_np (E211)")
        # The two call sites share the same statement but differ in the
        # preceding CPU_SET line (i vs threadID), so the two-line anchors
        # below hit exactly one site each (NUMA branch, then the
        # non-NUMA branch).
        replace_in_file(
            self,
            os.path.join(self.source_folder, "AnnService", "src", "Helper",
                         "AsyncFileReader.cpp"),
            "                            CPU_SET(i, &cpuset);\n"
            "                            int rc = pthread_setaffinity_np"
            "(thread.native_handle(), sizeof(cpu_set_t), &cpuset);",
            "                            CPU_SET(i, &cpuset);\n"
            "#if defined(__OHOS__) || !defined(__GLIBC__)\n"
            "                            // OHOS musl has no pthread_setaffinity_np "
            "(glibc extension, E211).\n"
            "                            // Every caller pins the calling thread itself, "
            "so sched_setaffinity(0, ...) is identical.\n"
            "                            (void)thread;\n"
            "                            int rc = sched_setaffinity(0, "
            "sizeof(cpu_set_t), &cpuset);\n"
            "#else\n"
            "                            int rc = pthread_setaffinity_np"
            "(thread.native_handle(), sizeof(cpu_set_t), &cpuset);\n"
            "#endif")
        replace_in_file(
            self,
            os.path.join(self.source_folder, "AnnService", "src", "Helper",
                         "AsyncFileReader.cpp"),
            "            CPU_SET(threadID, &cpuset);\n"
            "            int rc = pthread_setaffinity_np"
            "(thread.native_handle(), sizeof(cpu_set_t), &cpuset);",
            "            CPU_SET(threadID, &cpuset);\n"
            "#if defined(__OHOS__) || !defined(__GLIBC__)\n"
            "            // OHOS musl has no pthread_setaffinity_np "
            "(glibc extension, E211).\n"
            "            // Every caller pins the calling thread itself, "
            "so sched_setaffinity(0, ...) is identical.\n"
            "            (void)thread;\n"
            "            int rc = sched_setaffinity(0, "
            "sizeof(cpu_set_t), &cpuset);\n"
            "#else\n"
            "            int rc = pthread_setaffinity_np"
            "(thread.native_handle(), sizeof(cpu_set_t), &cpuset);\n"
            "#endif")
        # HarmonyOS/HongMeng portability: the SSD index reader
        # (AnnService/inc/Helper/AsyncFileReader.h, Linux branch) opens
        # the just-built "zbtest/*.ssd_index" with O_RDONLY|O_DIRECT and
        # requires kernel AIO (io_setup/io_submit/io_getevents). The
        # true-device preflight filesystem rejects O_DIRECT
        # ("Failed to create file handle: zbtest/...", then
        # "Cannot Load SSDIndex!" even though the SimpleFileIO writer
        # succeeded and BuildIndex returned true), and HongMeng may lack
        # AIO entirely. Keep the fast path first and fall back only on
        # failure (kanzi-cpp precedent): plain open when O_DIRECT fails,
        # synchronous pread when io_setup is unavailable. Upstream test
        # logic is untouched.
        # Single-line anchors (line-number free, same pattern as the
        # pthread fix above); replace_in_file raises loudly when absent.
        _aio_header = os.path.join(self.source_folder, "AnnService", "inc",
                                   "Helper", "AsyncFileReader.h")
        replace_in_file(
            self, _aio_header,
            "#include <fcntl.h>",
            "#include <fcntl.h>\n"
            "#include <unistd.h> // pread: sync fallback when AIO is unavailable")
        replace_in_file(
            self, _aio_header,
            "                m_fileHandle = open(filePath, O_RDONLY | O_DIRECT);",
            "                bool _hmbsDirect = true; // O_DIRECT usable until proven otherwise\n"
            "                m_fileHandle = open(filePath, O_RDONLY | O_DIRECT);\n"
            "                if (m_fileHandle <= 0) {\n"
            "                    // OHOS/HongMeng: filesystem rejects O_DIRECT; retry plain.\n"
            "                    m_fileHandle = open(filePath, O_RDONLY);\n"
            "                    _hmbsDirect = false;\n"
            "                }\n"
            "                if (!_hmbsDirect && m_fileHandle > 0) {\n"
            "                    // Plain fd cannot use kernel AIO (IOCB_CMD_PREAD via\n"
            "                    // io_submit requires O_DIRECT): skip io_setup entirely\n"
            "                    // and serve reads via sync pread (HasAio()==false).\n"
            "                    // Without this, BatchReadFileAsync spins forever in\n"
            "                    // io_submit/io_getevents (submitted never advances) and\n"
            "                    // the preflight SSH session goes idle until the remote\n"
            "                    // closes it (\"Connection closed by remote host\").\n"
            "                    SPTAGLIB_LOG(LogLevel::LL_Info, \"O_DIRECT unavailable for %s, using sync pread fallback\\n\", filePath);\n"
            "                    m_iocps.clear();\n"
            "                    return true;\n"
            "                }")
        replace_in_file(
            self, _aio_header,
            "                        SPTAGLIB_LOG(LogLevel::LL_Error, \"Cannot setup aio: %s\\n\", strerror(errno));\n"
            "                        return false;",
            "                        SPTAGLIB_LOG(LogLevel::LL_Info, \"AIO unavailable (%s), using sync pread fallback for %s\\n\", strerror(errno), filePath);\n"
            "                        for (int j = 0; j < i; j++) syscall(__NR_io_destroy, m_iocps[j]);\n"
            "                        m_iocps.clear();\n"
            "                        break;")
        replace_in_file(
            self, _aio_header,
            "                m_shutdown = false;",
            "                m_shutdown = false;\n"
            "                if (m_iocps.empty()) return true; // no kernel AIO: sync pread mode, no IOCP threads")
        replace_in_file(
            self, _aio_header,
            "                struct iocb myiocb = { 0 };",
            "                if (m_iocps.empty()) {\n"
            "                    // Sync fallback: kernel AIO unavailable.\n"
            "                    ssize_t _n = pread(m_fileHandle, readRequest.m_buffer, readRequest.m_readSize, (off_t)readRequest.m_offset);\n"
            "                    bool _ok = (_n == (ssize_t)readRequest.m_readSize);\n"
            "                    readRequest.m_callback(_ok);\n"
            "                    return _ok;\n"
            "                }\n"
            "                struct iocb myiocb = { 0 };")
        replace_in_file(
            self, _aio_header,
            "                for (int i = 0; i < m_iocps.size(); i++) syscall(__NR_io_destroy, m_iocps[i]);",
            "                for (int i = 0; i < m_iocps.size(); i++) syscall(__NR_io_destroy, m_iocps[i]);\n"
            "                m_iocps.clear();")
        replace_in_file(
            self, _aio_header,
            "                close(m_fileHandle);",
            "                if (m_fileHandle > 0) close(m_fileHandle);\n"
            "                m_fileHandle = -1;")
        replace_in_file(
            self, _aio_header,
            "            int GetFileHandler() { return m_fileHandle; }",
            "            int GetFileHandler() { return m_fileHandle; }\n"
            "\n"
            "            // True when kernel AIO contexts exist; false after the sync fallback.\n"
            "            bool HasAio() const { return !m_iocps.empty(); }")
        replace_in_file(
            self, _aio_header,
            "            int m_fileHandle;\n"
            "\n"
            "            std::vector<aio_context_t> m_iocps;",
            "            int m_fileHandle = -1;\n"
            "\n"
            "            std::vector<aio_context_t> m_iocps;")
        _aio_cpp = os.path.join(self.source_folder, "AnnService", "src",
                                "Helper", "AsyncFileReader.cpp")
        replace_in_file(
            self, _aio_cpp,
            "            std::vector<struct iocb> myiocbs(num);",
            "            // Sync fallback when kernel AIO is unavailable (see AsyncFileReader.h).\n"
            "            {\n"
            "                bool _hasAio = false;\n"
            "                for (size_t _hi = 0; _hi < handlers.size(); _hi++) {\n"
            "                    if (((AsyncFileIO*)(handlers[_hi].get()))->HasAio()) { _hasAio = true; break; }\n"
            "                }\n"
            "                if (!_hasAio) {\n"
            "                    for (int _i = 0; _i < num; _i++) {\n"
            "                        AsyncReadRequest* _req = &(readRequests[_i]);\n"
            "                        int _fid = (_req->m_status >> 16);\n"
            "                        AsyncFileIO* _h = (AsyncFileIO*)(handlers[_fid].get());\n"
            "                        ssize_t _got = pread(_h->GetFileHandler(), _req->m_buffer, _req->m_readSize, (off_t)_req->m_offset);\n"
            "                        bool _ok = (_got == (ssize_t)_req->m_readSize);\n"
            "                        if (!_ok) {\n"
            "                            SPTAGLIB_LOG(Helper::LogLevel::LL_Error, \"Sync fallback read failed: want %llu got %zd\\n\", (unsigned long long)_req->m_readSize, _got);\n"
            "                        }\n"
            "                        _req->m_callback(_ok);\n"
            "                    }\n"
            "                    return;\n"
            "                }\n"
            "            }\n"
            "            std::vector<struct iocb> myiocbs(num);")
        # Re-resolve live compilers at build time as well: the dependency
        # graph may have been computed before the toolchain moved, and the
        # generated conan_toolchain.cmake may still carry the stale
        # /data/service/hnp/bin/clang path (zydis/traildb precedent).
        try:
            _compilers = self.conf.get("tools.build:compiler_executables",
                                       default=None)
        except Exception:
            _compilers = None
        if not isinstance(_compilers, dict):
            _compilers = {}
        _c = self._resolve_compiler(_compilers.get("c"), ("clang", "cc"))
        _cxx = self._resolve_compiler(_compilers.get("cpp"),
                                      ("clang++", "c++"))
        self.output.info("HMBS diag build compilers c=%s cxx=%s"
                         % (_c, _cxx))
        self._fix_generated_toolchain_compiler(_compilers, _c, _cxx)
        cmake = CMake(self)
        # CMake 4.x requires the policy-floor exemption on the command line
        # (toolchain CACHE alone is not honored at the minimum-version check;
        # combblas/clfft precedent for cmake_minimum_required(<3.5) upstreams).
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()
        if can_run(self):
            # R51: run the upstream Boost.Test suite (12 suites / 154 cases:
            # 33 plain BOOST_AUTO_TEST_CASE + 121 macro-generated SSDServing
            # cases; GVQ 8 + TestHead 16 + BuildHead 32 + BuildSSD 32 +
            # SearchSSD 32 + RUN_FROM_MAP 1; self-contained, generates its
            # own data at runtime). Upstream registers no ctest target, so
            # run the binary directly (sciplot precedent); --log_level makes
            # failures attributable. Deterministic count source
            # (coordgen/osrm-backend precedent): one "Leaving test case"
            # line per executed case in the log file.
            sptag_test = os.path.join(
                self.source_folder, str(self.settings.build_type), "SPTAGTest")
            log_path = os.path.join(self.build_folder, "sptagtest.log")
            # SSDServing tests write relative paths "sddtest/..." (created by
            # the GVQ cases via boost::filesystem::create_directory) and
            # "zbtest/<ssd_index>" (IndexDirectory, never created upstream).
            # Without zbtest every BuildSSD/SearchSSD case fails with
            # "Failed to create file handle: zbtest/...". Pre-create both
            # directories in the test working directory (build_folder, the
            # explicit cwd of self.run below) AND next to the test binary,
            # so an upstream cwd change cannot turn into a
            # missing-directory artifact.
            _test_cwd = self.build_folder
            self.output.info("HMBS diag test cwd=%s binary=%s"
                             % (_test_cwd, sptag_test))
            # OpenMP runtime for the build-time SPTAGTest runs: this recipe's
            # own runenv_info is not visible to its own build() self.run
            # calls (only to consumers via conanrun), so export the SDK
            # libomp dir into the process environment now. Otherwise the
            # loader fails with "libomp.so not found" + __kmpc_*/omp_*
            # relocations -> Error 127 despite a valid executable
            # (test_package failure fingerprint this round).
            # Sources: authoritative SDK dir pinned by the repo profile
            # (ci/conan/profiles/ohos-aarch64 [buildenv]) + E120/E132,
            # then the live-compiler-relative fallback.
            try:
                _omp_all = []
                for _d in sorted(glob.glob(
                        "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/"
                        "ohos/native/llvm/lib")):
                    try:
                        if os.path.isfile(os.path.join(_d, "libomp.so")) \
                                and _d not in _omp_all:
                            _omp_all.append(_d)
                    except Exception:
                        continue
                for _d in self._sdk_omp_libdirs(_c):
                    if _d not in _omp_all:
                        _omp_all.append(_d)
                for _omp_d in _omp_all:
                    _prev = os.environ.get("LD_LIBRARY_PATH", "")
                    if _omp_d not in _prev.split(os.pathsep):
                        os.environ["LD_LIBRARY_PATH"] = (
                            _omp_d + (os.pathsep + _prev if _prev else ""))
                    self.output.info(
                        "HMBS diag exported LD_LIBRARY_PATH+=%s" % _omp_d)
                if not _omp_all:
                    self.output.warning(
                        "HMBS diag no SDK omp dir found in build()")
            except Exception as _e:
                self.output.warning("HMBS diag omp env export failed: %s" % _e)
            for _base in (self.build_folder, os.path.dirname(sptag_test)):
                for _d in ("zbtest", "sddtest"):
                    try:
                        os.makedirs(os.path.join(_base, _d), exist_ok=True)
                    except Exception as _e:
                        self.output.warning("HMBS diag mkdir %s in %s failed: %s"
                                            % (_d, _base, _e))
            # R51 per-suite execution: the full 154-case binary mixes light
            # suites with heavy ones (SSDServing 121 cases building
            # 1000x100 indices, PerfTest 2000x128 brute-force truth +
            # Sleep(10000)x2). A single silent `self.run(... > log 2>&1)`
            # holds the preflight SSH session idle for many minutes; the
            # remote then closes it ("Connection closed by remote host")
            # with zero test evidence. Running each Boost suite as its own
            # self.run keeps the session alive (progress info between runs)
            # and attributes the next hang to one suite. Upstream logic is
            # untouched; counts below are aggregated deterministically from
            # the per-suite logs (same Entering/Leaving segmentation).
            # NOTE: the file is Base64HelperTest.cpp but the Boost suite inside
            # is BOOST_AUTO_TEST_SUITE(Base64Test); filtering by the file name
            # matches zero cases and Boost exits 200 with a 2-line log, which
            # undercounted discovered by 1 and left executed>discovered.
            _suites = (
                "Base64Test",
                "IniReaderTest",
                "StringConvertTest",
                "CommonHelperTest",
                "FilterTest",
                "DistanceTest",
                "SIMDTest",
                "AlgoTest",
                "ConcurrentTest",
                "ReconstructIndexSimilarityTest",
                "PerfTest",
                "SSDServingTest",
            )
            _rc = 0
            _log_lines = []
            _suite_rows = []
            _ansi_re = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
            _suite_discovered = 0
            for _suite in _suites:
                _slog = os.path.join(self.build_folder,
                                     "sptagtest_" + _suite + ".log")
                self.output.info("HMBS diag upstream suite start %s" % _suite)
                try:
                    self.run(sptag_test + " --run_test=" + _suite
                             + " --log_level=test_suite"
                             + " > \"" + _slog + "\" 2>&1",
                             cwd=_test_cwd, env="conanrun")
                    self.output.info("HMBS diag upstream suite done %s rc=0"
                                     % _suite)
                except Exception as e:
                    _rc = 1
                    self.output.warning(
                        "HMBS diag upstream suite %s exited non-zero: %s"
                        % (_suite, e))
                try:
                    with open(_slog, "r", encoding="utf-8",
                              errors="replace") as _sf:
                        _stext = _sf.read()
                except Exception as e:
                    self.output.warning(
                        "HMBS diag read %s failed: %s" % (_slog, e))
                    _stext = ""
                _slines = _stext.splitlines()
                _log_lines.append("===== SUITE %s (%d lines) =====" % (
                    _suite, len(_slines)))
                _log_lines.extend(_slines)
                _s_disc = 0
                for _sl in (_ansi_re.sub("", _l) for _l in _slines):
                    # Boost prints singular "Running 1 test case..." for
                    # 1-case suites (IniReader/Filter/SIMD); "cases?" covers
                    # both singular and plural from this single source.
                    _m = re.search(r"Running\s+(\d+)\s+test cases?", _sl)
                    if _m:
                        try:
                            _s_disc = int(_m.group(1))
                        except Exception:
                            pass
                        break
                _suite_rows.append((_suite, _s_disc, len(_slines)))
                _suite_discovered += _s_disc
            try:
                with open(log_path, "w", encoding="utf-8") as _cf:
                    _cf.write("\n".join(_log_lines))
            except Exception as e:
                self.output.warning("HMBS diag write combined log failed: %s" % e)
            _log_text = "\n".join(_log_lines)
            # Boost.Test emits ANSI color escapes (e.g. ESC[1;34;49m) around
            # the "Entering test case" lines even when redirected to a file
            # (true-device log shows "[1;34;49mEntering test module"). The
            # previous startswith() parser therefore matched zero of 8884
            # lines. Strip ANSI first and match by substring. discovered comes
            # from the authoritative "Running N test cases..." header line in
            # the same log (154 on this commit); the audited source total
            # (154) is only a consistency check, never a substitute.
            _stripped = [_ansi_re.sub("", _l) for _l in _log_lines]
            # Per-suite aggregation: each suite log carries its own
            # "Running N test cases..." header; the total discovered is the
            # SUM over all suites (must equal the audited 154). A single
            # first-match breaks here (it would return one suite's N).
            discovered = 0
            for _sl in _stripped:
                # Same singular/plural source as the per-suite header above.
                _m = re.search(r"Running\s+(\d+)\s+test cases?", _sl)
                if _m:
                    try:
                        discovered += int(_m.group(1))
                    except Exception:
                        pass
            self.output.info("HMBS diag suites=%s discovered_sum=%d" % (
                ",".join("%s:%d/%d" % _r for _r in _suite_rows),
                discovered))
            if discovered <= 0:
                # Fall back to the audited total only for the marker shape;
                # the suite-row diagnostic above keeps the failure honest.
                discovered = 154
                self.output.warning(
                    "HMBS diag no Running-header found; fallback discovered=154")
            if not _log_lines:
                # Binary produced no output at all (failed to start?);
                # report honestly with a reason, inventing no counts.
                self._hmbs_emit_upstream({
                    "status": "failed",
                    "framework": "boost_test",
                    "command": "./Release/SPTAGTest --run_test=<suite> --log_level=test_suite (per-suite x12, aggregated)",
                    "discovered": discovered,
                    "executed": 0,
                    "passed": 0,
                    "failed": 0,
                    "skipped": discovered,
                    "reason": "SPTAGTest rc=%d with empty/missing log %s; "
                              "binary may have failed to start" % (_rc, log_path),
                })
                raise ConanException(
                    "SPTAGTest produced no log output (rc=%d, log: %s)"
                    % (_rc, log_path))
            # Segment the log into per-case runs (single source for every
            # counter). Boost.Test log_level=test_suite emits one
            # "Entering test case" line per started case, one "Leaving test
            # case" line per completed case, and "error in ..." lines inside
            # failing cases. A started-but-never-completed case means the
            # runner crashed/aborted mid-case and counts as failed.
            _seg_failed = []
            _seg_errline = []
            _seg_names = []
            _open = None
            _open_failed = False
            _open_errline = ""
            for _ln in _stripped:
                _s = _ln.strip()
                if "Entering test case" in _s:
                    _nm = _s.split("Entering test case", 1)[1].strip().strip("\"'")
                    if _open is not None:
                        _seg_names.append(_open)
                        _seg_failed.append(True)
                        _seg_errline.append(
                            _open_errline or "aborted before 'Leaving test case'")
                    _open = _nm
                    _open_failed = False
                    _open_errline = ""
                elif "Leaving test case" in _s:
                    if _open is not None:
                        _seg_names.append(_open)
                        _seg_failed.append(_open_failed)
                        _seg_errline.append(_open_errline)
                        _open = None
                elif _open is not None and "error in " in _s:
                    _open_failed = True
                    if not _open_errline:
                        _open_errline = _s[:300]
            if _open is not None:
                _seg_names.append(_open)
                _seg_failed.append(True)
                _seg_errline.append(
                    _open_errline or "aborted before 'Leaving test case'")
            executed = len(_seg_names)
            if executed == 0:
                # Parser did not recognize the log format: dump head/tail
                # and fail loudly instead of emitting zero counts.
                for _t in (_log_lines[:30] + ["..."] + _log_lines[-30:]):
                    self.output.warning("SPTAGLOG | " + _t[:500])
                raise ConanException(
                    "SPTAGTest log has %d lines but no 'Entering test case' "
                    "entries (log: %s); refusing to emit marker"
                    % (len(_log_lines), log_path))
            failed = sum(1 for _f in _seg_failed if _f)
            passed = executed - failed
            skipped = discovered - executed
            if executed > discovered or passed < 0 or skipped < 0:
                raise ConanException(
                    "SPTAGTest count check failed: executed=%d failed=%d "
                    "passed=%d discovered=%d; refusing to fudge numbers"
                    % (executed, failed, passed, discovered))
            # Identity check: passed + failed == executed,
            # executed + skipped <= discovered (both hold by construction).
            if _rc != 0 or failed:
                self.output.warning(
                    "SPTAGTest log tail (%s, %d lines total):"
                    % (log_path, len(_log_lines)))
                for _t in _log_lines[-80:]:
                    self.output.warning("SPTAGLOG | " + _t[:500])
            _gaps = []
            for _nm, _fl, _el in zip(_seg_names, _seg_failed, _seg_errline):
                if _fl:
                    _gaps.append({
                        "count": 1,
                        "category": "test_failure",
                        "detail": "case '%s': %s"
                                  % (_nm, _el or "failed without error line"),
                        "evidence": "sptagtest.log dumped to build output above",
                    })
            if skipped > 0:
                _gaps.append({
                    "count": skipped,
                    "category": "test_failure",
                    "detail": "cases never started: runner aborted with rc=%d" % _rc,
                    "evidence": "sptagtest.log dumped to build output above",
                })
            if failed == 0 and skipped == 0:
                _status = "passed"
            elif _rc == 0:
                _status = "partial"
            else:
                _status = "failed"
            _payload = {
                "status": _status,
                "framework": "boost_test",
                "command": "./Release/SPTAGTest --run_test=<suite> --log_level=test_suite (per-suite x12, aggregated)",
                "discovered": discovered,
                "executed": executed,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
            }
            if _gaps:
                _payload["gaps"] = _gaps
            self._hmbs_emit_upstream(_payload)
            if _rc != 0:
                _bad = [_nm for _nm, _fl in zip(_seg_names, _seg_failed) if _fl]
                raise ConanException(
                    "SPTAGTest failed: %d/%d cases failed (%s); see "
                    "SPTAGLOG tail above" % (failed, executed, ", ".join(_bad)))

    def package(self):
        # Public headers keep the upstream "inc/..." layout (as in
        # SPTAG.nuspec): consumers include "inc/Core/VectorIndex.h" with
        # the package include dir on the path.
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "AnnService", "inc"),
             dst=os.path.join(self.package_folder, "include", "inc"))
        copy(self, "*.hxx",
             src=os.path.join(self.source_folder, "AnnService", "inc"),
             dst=os.path.join(self.package_folder, "include", "inc"))
        cmake = CMake(self)
        cmake.install()
        # DistanceUtils is a STATIC helper archive that SPTAGLibStatic links
        # but upstream never installs (no install() rule for it; static-link
        # does not merge objects). Without it consumers of the static lib
        # get undefined refs to SPTAG::COMMON::SIMDUtils/DistanceUtils.
        # The shared SPTAGLib embeds these objects at .so link time, so this
        # only matters for the static configuration. Upstream sets
        # LIBRARY_OUTPUT_PATH to <source>/Release, so search both the source
        # and build trees for the built archive and copy it into the package.
        _dist_copied = False
        for _root in (self.source_folder, self.build_folder):
            if not _root:
                continue
            for _cand in glob.glob(os.path.join(str(_root), "**",
                                                "libDistanceUtils.a"),
                                   recursive=True):
                try:
                    _dst = os.path.join(self.package_folder, "lib",
                                        "libDistanceUtils.a")
                    os.makedirs(os.path.dirname(_dst), exist_ok=True)
                    shutil.copyfile(_cand, _dst)
                    self.output.info("HMBS diag packaged DistanceUtils: %s"
                                     % _cand)
                    _dist_copied = True
                    break
                except Exception as e:
                    self.output.warning("HMBS diag copy %s failed: %s"
                                        % (_cand, e))
            if _dist_copied:
                break
        if not _dist_copied:
            self.output.warning(
                "HMBS diag libDistanceUtils.a not found under source/build; "
                "static consumers may miss SIMD symbols")
        if not self.options.shared:
            # Upstream always builds both variants; drop the shared objects
            # when the static configuration was requested.
            for so in glob.glob(os.path.join(self.package_folder, "lib", "*.so*")):
                os.remove(so)
        # Carry the real upstream result into the package so cache-hit
        # test_package runs can re-emit without re-running the build.
        try:
            src = os.path.join(self.build_folder, "hmbs_upstream.json")
            if os.path.isfile(src):
                dst_dir = os.path.join(self.package_folder, "res")
                os.makedirs(dst_dir, exist_ok=True)
                shutil.copyfile(src, os.path.join(dst_dir,
                                                  "hmbs_upstream.json"))
            else:
                self.output.warning(
                    "HMBS diag hmbs_upstream.json missing in package()")
        except Exception as e:
            self.output.warning("HMBS diag package upstream copy failed: %s"
                                % e)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "sptag")
        self.cpp_info.set_property("cmake_target_name", "sptag::sptag")
        # Explicit component requires (no implicit aggregate): the default
        # aggregate (e.g. boost1.84::boost1.84) has no matching CMake target
        # because every boost1.84-* package sets cmake_file_name="Boost" and
        # only defines Boost::* component targets. Listing the real
        # components keeps sptag_DEPS_TARGET referencing targets that exist
        # in the (renamed, see test_package) Boost configs. wserialization's
        # boost_wserialization internally requires its sibling
        # boost_serialization + headers, so no separate serialization entry.
        self.cpp_info.requires = [
            "boost1.84::boost_headers",
            "boost1.84::boost_filesystem",
            "boost1.84::boost_regex",
            "boost1.84-thread::boost_thread",
            "boost1.84-wserialization::boost_wserialization",
        ]
        # SPTAGLibStatic is self-contained except bundled zstd (static
        # archives do not merge); the shared variant additionally needs
        # nothing beyond what is linked into it at build time.
        # NOTE: the zstd CMake targets are libzstd_static/libzstd_shared but
        # their OUTPUT_NAME is plain "zstd" on non-MSVC (libzstd.a/libzstd.so),
        # so the conan lib stems must be "zstd", not the target names.
        if self.options.shared:
            self.cpp_info.libs = ["SPTAGLib", "zstd"]
        else:
            # Dependents-first order: SPTAGLibStatic needs DistanceUtils
            # objects (SIMD/distance kernels) plus bundled zstd.
            self.cpp_info.libs = ["SPTAGLibStatic", "DistanceUtils", "zstd"]
        # OpenMP runtime from the OHOS SDK (clang -fopenmp); consumers of
        # the static lib need -lomp at final link (faiss precedent).
        self.cpp_info.system_libs = ["omp"]
        # OpenMP runtime loader path (faiss/1.15.0 precedent): libomp.so
        # lives under the SDK toolchain (<bindir>/../lib/aarch64-linux-ohos)
        # and is NOT on the default loader path, so test_package's
        # test_sptag dies with "Error loading shared library libomp.so" +
        # undefined __kmpc_*/omp_* -> ConanException Error 127. Expose it
        # via runenv so conanrun finds it at test time. Best-effort only.
        try:
            _ce = self.conf.get("tools.build:compiler_executables",
                                default=None)
        except Exception:
            _ce = None
        try:
            _seeds = []
            if isinstance(_ce, dict) and _ce.get("c"):
                _seeds.append(_ce.get("c"))
            # Live-toolchain fallback: the shared profile may still point at
            # the migrated /data/service/hnp/bin/clang path while the true
            # device keeps clang under PATH or ~/usr/local/bin (traildb /
            # zydis precedent). Cover both so a stale conf path alone
            # cannot leave LD_LIBRARY_PATH empty.
            for _nm in ("clang", "cc"):
                try:
                    _w = shutil.which(_nm)
                    if _w and _w not in _seeds:
                        _seeds.append(_w)
                except Exception:
                    pass
            try:
                _hb = os.path.join(os.path.expanduser("~"), "usr", "local",
                                   "bin", "clang")
                if os.path.isfile(_hb) and _hb not in _seeds:
                    _seeds.append(_hb)
            except Exception:
                pass
            _seen = set()
            # L1 first: authoritative SDK dir (repo profile + E120/E132).
            try:
                for _d in sorted(glob.glob(
                        "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/"
                        "ohos/native/llvm/lib")):
                    try:
                        if os.path.isfile(os.path.join(_d, "libomp.so")) \
                                and _d not in _seen:
                            _seen.add(_d)
                            self.runenv_info.append_path("LD_LIBRARY_PATH",
                                                         _d)
                    except Exception:
                        continue
            except Exception:
                pass
            for _sd in _seeds:
                for _omp_d in self._sdk_omp_libdirs(_sd):
                    if _omp_d not in _seen:
                        _seen.add(_omp_d)
                        self.runenv_info.append_path("LD_LIBRARY_PATH",
                                                     _omp_d)
        except Exception:
            pass
