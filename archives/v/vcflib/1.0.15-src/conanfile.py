#!/usr/bin/env python3
"""Conan recipe — vcflib 1.0.15-src (CMake C++17 library + VCF tool suite).

vcflib is a C++ library and command-line tool suite for parsing and
manipulating Variant Call Format (VCF) files. It provides the Variant /
VariantCallFile API, ~85 command-line tools, and optional pybind11 Python
bindings (pyvcflib).

Build system: CMake (min 3.16, C++17). The official release tarball vendors
all submodule dependencies (htslib, WFA2-lib, fastahack, tabixpp, ...), so no
external autotools vendored sub-build is required when system/conan htslib is
provided.

Dependencies
------------
- htslib/1.24-r0 (ohpcd) : vcflib discovers htslib via pkg-config
  (pkg_check_modules htslib). Supplying it avoids the vendored htslib
  ExternalProject autotools bootstrap (which needs autoreconf on device).
- zlib/1.3.1, xz/5.6.2, bzip2/1.0.8 : satisfy vcflib's
  find_package(ZLIB) / find_package(LibLZMA) / find_package(BZip2) and the
  explicit -lz/-llzma/-lbz2 links.
- WFA2-lib is built from the bundled contrib/WFA2-lib via -DWFA_GITMODULE=ON
  (no system wfa2 on OHOS).
- ZIG is disabled (-DZIG=OFF) — the optional vcfcreatemulti zig code path is
  not needed and no zig toolchain exists on OHOS.

Upstream tests
--------------
The upstream ctest suite is Python doctest/pytest based (python3 -m doctest on
test/pytest/*.md + test/tests/realign.py). Two of the registered cases
(realign and pyvcflib) require the pybind11 Python module pyvcflib, which is
not available on OHOS (no pybind11 in the ohpcd registry). source() guards
those blocks behind pybind11_FOUND (in-place CMakeLists.txt edit); the
remaining doctest cases are executed in full via ctest in build().
"""
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get
from conan.tools.gnu import PkgConfigDeps

# Official upstream ctest suite for vcflib 1.0.15-src (官方向口径 ctest_entries).
# The upstream CMakeLists.txt registers TEN vcflib-owned ctest cases under its
# default options (BUILD_STATIC=OFF, ZIG=ON, pybind11 present):
#   realign, pyvcflib, vcflib-api, vcf2tsv, vcfallelicprimitives, vcfwave,
#   vcffilter, vcfcreatemulti, vcfnulldotslashdot, doc/vcfintersect
# (WFA2-lib's own `wfa2lib` ctest is a third-party dependency self-test pulled
# in by WFA_GITMODULE=ON; it is disabled by source() and is not part of vcflib's
# own suite.)
#
# On OHOS, three of those ten are registered but physically cannot run:
#   - realign, pyvcflib: build the optional pyvcflib Python module via the
#     pybind11_add_module() path (CMakeLists.txt ~line 478) and run the
#     realign/pyvcflib doctests (~line 535). No pybind11 is present in the
#     ohpcd registry and there is no python-binding runtime on OHOS, so
#     source() guards both blocks behind `pybind11_FOUND` (undefined here).
#   - vcfcreatemulti: registered only `if (ZIG)` (CMakeLists.txt ~line 544) and
#     triggers a configure-time FATAL_ERROR if ZIG=ON but no `zig` binary is on
#     PATH (~line 106-110). OHOS has no zig compiler, so the recipe forces
#     -DZIG=OFF.
# These three are OHOS platform/toolchain feature gaps, not vcflib failures and
# not installable dependencies (nothing in the registry provides them). Each is
# reported as an `ohos_feature` gap; the ten-entry total is what rule4 uses.
UPSTREAM_TEST_TOTAL = 10
UPSTREAM_GAPS = [
    {
        "count": 2,
        "category": "ohos_feature",
        "detail": ("realign/pyvcflib ctest cases need the pyvcflib Python module "
                   "(pybind11_add_module, CMakeLists.txt ~478/535); pybind11 is "
                   "absent from the ohpcd registry and OHOS has no python-binding "
                   "runtime. source() guards them behind pybind11_FOUND."),
        "evidence": ("CMakeLists.txt:478 if (pybind11_FOUND AND NOT BUILD_STATIC); "
                     "CMakeLists.txt:535 if (pybind11_FOUND AND NOT BUILD_STATIC)"),
    },
    {
        "count": 1,
        "category": "ohos_feature",
        "detail": ("vcfcreatemulti ctest needs the zig toolchain (CMakeLists.txt "
                   "~544 if (ZIG) add_pydoctest(vcfcreatemulti)); with ZIG=ON and "
                   "no `zig` binary CMake FATAL_ERRORs (~106-110). OHOS has no zig, "
                   "so the recipe forces -DZIG=OFF."),
        "evidence": ("CMakeLists.txt:106-110 ZIG_EXE FATAL_ERROR; "
                     "CMakeLists.txt:544-546 if (ZIG) add_pydoctest(vcfcreatemulti)"),
    },
]


class VcflibConan(ConanFile):
    name = "vcflib"
    version = "1.0.15-src"
    description = ("C++ library and command-line tools for parsing and "
                   "manipulating VCF files")
    license = "MIT"
    homepage = "https://github.com/vcflib/vcflib"
    url = "https://github.com/vcflib/vcflib"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def requirements(self):
        # htslib provides the htslib.pc that vcflib discovers via pkg-config
        self.requires("htslib/1.24-r0")
        # satisfy find_package(ZLIB/LibLZMA/BZip2) + -lz/-llzma/-lbz2 links
        self.requires("zlib/1.3.1")
        self.requires("xz/5.6.2")
        self.requires("bzip2/1.0.8")
        # htslib 1.24 is built --with-libdeflate, so htslib.pc's Libs.private
        # pulls `-ldeflate` (libdeflate) into every vcflib tool link. libdeflate
        # is built as a SHARED lib (its recipe ships only libdeflate.so), so
        # each tool ends up with a runtime DT_NEEDED on libdeflate.so. Making it
        # an explicit (not merely transitive) dep lets us pin its package folder
        # on the linker -L path and in the binary RPATH so the tool always
        # resolves the conan libdeflate.so we were built against, instead of
        # whatever stale/system libdeflate.so the loader happens to find first
        # (`libdeflate_*: symbol not found` relocation failures on the CI
        # worker while the fresh-conan .so resolves fine on the preflight
        # device).
        self.requires("libdeflate/1.25")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # OHOS has no pybind11 in the registry. The upstream CMakeLists.txt
        # builds the pyvcflib Python module and registers the realign/pyvcflib
        # ctest cases when BUILD_STATIC is OFF, which would fail without
        # pybind11. We guard those blocks behind pybind11_FOUND (false/undefined
        # here) by editing the file in place with exact string replacement.
        # Done in Python (not external .patch files / GNU patch) so it neither
        # depends on a writable temp dir (the真机 /tmp is read-only) nor on
        # Conan's strict patch-file validation.
        # musl/OHOS portability: contrib/fastahack/LargeFileSupport.h uses the
        # glibc-internal type `__off64_t` in its generic #else branch, which does
        # not exist on musl (OHOS builds fail with "unknown type name
        # '__off64_t'"). With _FILE_OFFSET_BITS 64 (set at the top of the file)
        # off_t is 64-bit on both glibc and musl, so switching to `off_t` is
        # portable. The file already uses `typedef off_t off_type;` for Apple/
        # FreeBSD, confirming this is the upstream-intended approach.
        cmake = os.path.join(self.source_folder, "CMakeLists.txt")
        lfs = os.path.join(
            self.source_folder, "contrib", "fastahack", "LargeFileSupport.h")
        with open(lfs, "r", encoding="utf-8") as fh:
            lfs_content = fh.read()
        lfs_old = (
            "#else\n"
            "#define ftell64(a)     ftello(a)\n"
            "#define fseek64(a,b,c) fseeko(a,b,c)\n"
            "typedef __off64_t off_type;\n"
            "#endif\n"
        )
        lfs_new = (
            "#else\n"
            "#define ftell64(a)     ftello(a)\n"
            "#define fseek64(a,b,c) fseeko(a,b,c)\n"
            "typedef off_t off_type;\n"
            "#endif\n"
        )
        if lfs_content.count(lfs_old) != 1:
            raise ConanException(
                "could not locate unique LargeFileSupport.h __off64_t typedef")
        lfs_content = lfs_content.replace(lfs_old, lfs_new)
        with open(lfs, "w", encoding="utf-8") as fh:
            fh.write(lfs_content)

        with open(cmake, "r", encoding="utf-8") as fh:
            content = fh.read()
        replacements = [
            # Force a NON-shared build. Upstream defaults BUILD_STATIC=OFF, and
            # its else() branch unconditionally does `set(BUILD_SHARED_LIBS ON)`,
            # so every tool dynamically links libvcflib.so/libwfa2.so and at test
            # runtime the loader aborts with "symbol not found" (wavefront_*,
            # VariantAllele::*) because the fresh .so can't be located reliably.
            # Flipping it OFF (rather than BUILD_STATIC=ON, which also forces the
            # risky full "-static" libc flag) makes vcflib a static libvcflib.a and
            # the tools link libvcflib.a + wfa2_static.a with no shared-lib
            # runtime dependency at all (line ~51, inside if(BUILD_STATIC) else).
            (
                "  set(BUILD_SHARED_LIBS ON)",
                "  set(BUILD_SHARED_LIBS OFF)",
            ),
            # guard the pyvcflib Python module behind pybind11_FOUND (line ~478)
            (
                "if (NOT BUILD_STATIC) # only when not building static",
                "if (pybind11_FOUND AND NOT BUILD_STATIC) # only when not building static",
            ),
            # guard the realign/pyvcflib ctest cases behind pybind11_FOUND (line ~535)
            (
                "if (NOT BUILD_STATIC)\n  add_pytest(realign)",
                "if (pybind11_FOUND AND NOT BUILD_STATIC)\n  add_pytest(realign)",
            ),
            # Link the bundled WFA2-lib STATICALLY (wfa2_static -> libwfa2.a)
            # instead of the SHARED wfa2 target (libwfa2.so). The tools
            # (vcfwave/vcfallelicprimitives) dynamically link libwfa2.so for the
            # WFA C API (wavefront_*, e.g. wavefront_aligner_new), but at runtime
            # the loader does not find the freshly built libwfa2.so (or hits a
            # symbol-incompatible lib) and aborts every WFA-based tool with
            # "symbol not found". Note the conan `shared=False` option is NOT
            # wired to upstream CMake, so without a forced configure() variable
            # upstream defaults to BUILD_SHARED_LIBS=ON (see build()). build()
            # now forces BUILD_SHARED_LIBS=OFF; this WFALIB change makes WFA
            # static too so all wavefront_* symbols are resolved at link time
            # and there is no libwfa2.so runtime dependency at all (line ~374,
            # inside if(WFA_GITMODULE)).
            (
                "  set(WFALIB wfa2) # pick up the wfa2 lib target from the included CMakeLists.txt",
                "  set(WFALIB wfa2_static) # static wfa2 (libwfa2.a): link WFA C API symbols at link time, not via libwfa2.so at runtime",
            ),
            # WFALIB is now the static wfa2 target; install it as an ARCHIVE
            # (static lib) instead of RUNTIME (only valid for executables /
            # shared libs). Otherwise `cmake.install()` fails on a non-executable
            # target in the package() stage (line ~603, inside if(WFA_GITMODULE)).
            (
                "  install(TARGETS ${WFALIB} RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})",
                "  install(TARGETS ${WFALIB} ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR})",
            ),
        ]
        for old, new in replacements:
            if old not in content:
                raise ConanException(
                    f"could not locate CMakeLists.txt guard target:\n{old!r}")
            if content.count(old) != 1:
                raise ConanException(
                    f"CMakeLists.txt guard target is not unique:\n{old!r}")
            content = content.replace(old, new)
        with open(cmake, "w", encoding="utf-8") as fh:
            fh.write(content)

        # OHOS has no `bash` on PATH (toybox shell is /bin/sh). The upstream
        # Python doctest harness `test/pytest/rtest.py` hardcodes `bash -c` in
        # its `sh()` helper, which raises FileNotFoundError('bash') for every
        # `sh(...)` doctest example (vcffilter / vcfallelicprimitives /
        # vcfwave). `os.system()` in the same harness already runs via /bin/sh
        # (present and functional on OHOS), so switching the explicit shell to
        # `/bin/sh` keeps the exact same POSIX semantics (pipes, redirection)
        # while removing the OHOS-missing bash dependency. Done in-place to
        # avoid GNU patch/temporary files.
        #
        # Separate issue (observed on the device AFTER the static/OpenMP-off
        # fixes): `head()`/`cat()` doctest examples do bare
        # `Popen([tool, ...])` whose exec does NOT locate the freshly built
        # tools on PATH, spilling `FileNotFoundError: 'vcfwave'` for every
        # `head("... -h", N)` example, while `sh()` and `os.system()`
        # (which go through `/bin/sh`) DO find them. Route head() through the
        # same proven working `/bin/sh -c` mechanism (identical output capture,
        # so expected doctest output is unchanged).
        rtest = os.path.join(self.source_folder, "test", "pytest", "rtest.py")
        with open(rtest, "r", encoding="utf-8") as fh:
            rtest_content = fh.read()
        rtest_old = "    cmds = ['bash','-c']+[cmd]"
        rtest_new = "    cmds = ['/bin/sh','-c']+[cmd]"
        if rtest_content.count(rtest_old) != 1:
            raise ConanException("could not locate unique rtest.py sh() shell line")
        rtest_content = rtest_content.replace(rtest_old, rtest_new)
        # head()/cat() (bare Popen over an explicit argv): route through /bin/sh
        # so the exec uses the shell PATH lookup like the working sh()/os.system.
        head_old = (
            "    cmd2 = cmd.split(\" \")\n"
            "    cmd1 = cmd2[0]\n"
            "    cmds = [cmd1]+cmd2[1:]\n"
        )
        head_new = (
            "    cmds = ['/bin/sh','-c',cmd]\n"
        )
        if rtest_content.count(head_old) != 1:
            raise ConanException(
                "could not locate unique rtest.py head() argv-splitting block")
        rtest_content = rtest_content.replace(head_old, head_new)
        with open(rtest, "w", encoding="utf-8") as fh:
            fh.write(rtest_content)

        # The bundled third-party WFA2-lib subproject (pulled in via
        # WFA_GITMODULE) registers an incidental `wfa2lib` ctest case whose
        # harness (tests/wfa.utest.sh) is a GNU-bash / GNU-time / process
        # substitution heavy script. It is not portable to OHOS (no bash, toybox
        # coreutils, hmdfs restricts '#!' script exec), and it exercises the
        # third-party WFA2 dependency, not the vcflib library/tools. It is not
        # part of the vcflib upstream test suite, so disable its registration.
        wfa_cmake = os.path.join(
            self.source_folder, "contrib", "WFA2-lib", "CMakeLists.txt")
        with open(wfa_cmake, "r", encoding="utf-8") as fh:
            wfa_content = fh.read()
        wfa_old = "add_wfa_test()"
        wfa_new = ("# disabled: WFA2-lib's own unit-test harness "
                   "(tests/wfa.utest.sh) needs GNU bash/time and is not "
                   "OHOS-portable; it tests the third-party WFA2 dep, not "
                   "vcflib.\n# add_wfa_test()")
        if wfa_content.count(wfa_old) != 1:
            raise ConanException(
                "could not locate unique WFA2-lib add_wfa_test() call")
        wfa_content = wfa_content.replace(wfa_old, wfa_new)
        with open(wfa_cmake, "w", encoding="utf-8") as fh:
            fh.write(wfa_content)

        # Runtime shared-library search path for the doctests (defensive only).
        # The build is now forced static (see the BUILD_SHARED_LIBS OFF patch
        # above), so the tools no longer depend on libvcflib.so/libwfa2.so at
        # runtime. We keep prepending ${CMAKE_BINARY_DIR} to the doctest
        # LD_LIBRARY_PATH anyway so that IF a residual shared dep ever appears it
        # resolves to the freshly built binary dir rather than a stale/mismatched
        # lib from the shared conan cache (which previously produced dynamic
        # loader "symbol not found" failures, e.g. `vcfwave:
        # wavefront_aligner_attr_default: symbol not found`).
        ctest_env_old = ("LD_LIBRARY_PATH=$ENV{LIBRARY_PATH}:$ENV{GUIX_PROFILE}/lib"
                         ";PATH=${CMAKE_BINARY_DIR}:$ENV{PATH}")
        ctest_env_new = ("LD_LIBRARY_PATH=${CMAKE_BINARY_DIR}:$ENV{LIBRARY_PATH}"
                         ":$ENV{GUIX_PROFILE}/lib;PATH=${CMAKE_BINARY_DIR}:$ENV{PATH}")
        if content.count(ctest_env_old) != 1:
            raise ConanException(
                "could not locate unique add_pydoctest LD_LIBRARY_PATH line")
        content = content.replace(ctest_env_old, ctest_env_new)
        with open(cmake, "w", encoding="utf-8") as fh:
            fh.write(content)

    def generate(self):
        # Generate pkg-config .pc files (htslib.pc, zlib.pc, liblzma.pc, bzip2.pc)
        # into the generators folder so vcflib's pkg_check_modules(htslib)
        # resolves the conan-provided htslib.
        PkgConfigDeps(self).generate()
        CMakeDeps(self).generate()

        # Inject the generators folder (containing the .pc files) into
        # PKG_CONFIG_PATH for the CMake configure step (pkg_check_modules runs
        # the pkg-config tool which reads PKG_CONFIG_PATH).
        self.buildenv_info.append_path("PKG_CONFIG_PATH", self.generators_folder)

        # vcflib tools carry a DT_NEEDED on the SHARED libdeflate.so (htslib is
        # built --with-libdeflate), and the upstream ctest harness sets each
        # test's runtime LD_LIBRARY_PATH from the *build-time* LIBRARY_PATH env
        # var (CMakeLists.txt add_pydoctest:
        #   LD_LIBRARY_PATH=$ENV{LIBRARY_PATH}:$ENV{GUIX_PROFILE}/lib).
        # Prepend every conan dep lib dir (incl. libdeflate) to LIBRARY_PATH so
        # it lands FIRST in the test LD_LIBRARY_PATH and the loader resolves the
        # freshly built conan libdeflate.so rather than a stale/system one that
        # lacks the `libdeflate_*` symbols (CI-worker "Error relocating ...:
        # symbol not found"). This complements the CMAKE_BUILD_RPATH for
        # runtimes that honor DT_RUNPATH-after-LD_LIBRARY_PATH.
        for name in ("htslib", "zlib", "xz", "bzip2", "libdeflate"):
            try:
                folder = self._dep_folder(name)
            except Exception:
                continue
            self.buildenv_info.append_path("LIBRARY_PATH", os.path.join(folder, "lib"))

        tc = CMakeToolchain(self)
        tc.variables["ZIG"] = "OFF"          # no zig toolchain on OHOS
        tc.variables["WFA_GITMODULE"] = "ON"  # build bundled WFA2-lib via add_subdirectory
        tc.generate()

    def _dep_folder(self, name):
        dep = self.dependencies[name]
        folder = getattr(dep, "package_folder", None)
        if not folder:
            raise ConanException(f"dependency {name} package_folder unavailable")
        return folder

    def build(self):
        # Wire conan dependency paths into CMake Module find_* calls.
        # vcflib uses find_package(ZLIB)/find_package(BZip2)/find_package(LibLZMA)
        # (Module mode). Pre-set the Find* cache variables from the conan package
        # folders so the modules resolve deterministically (same technique as
        # assimp), instead of relying on system search paths/headers that may be
        # absent on the OHOS sysroot.
        zlib_folder = self._dep_folder("zlib")
        xz_folder = self._dep_folder("xz")
        bzip2_folder = self._dep_folder("bzip2")
        htslib_folder = self._dep_folder("htslib")
        libdeflate_folder = self._dep_folder("libdeflate")

        # Upstream links every tool against the bare `-lhts -llzma -lbz2 -lz`
        # flags (CMakeLists.txt `vcflib_LIBS`), relying on the linker search
        # path (-L) -- NOT on full library paths. CMAKE_PREFIX_PATH only helps
        # find_*()/pkg-config resolution; it does not place these folders on the
        # linker's -L search path. Without them the static conan libs
        # (libhts.a, liblzma.a, libbz2.a) are unresolved at link time
        # ("unable to find library -lhts/-llzma/-lbz2", ld.lld). Add explicit
        # -L flags for every dependency lib dir. libdeflate is a SHARED lib, so
        # its -L is added here too so `-ldeflate` (from htslib.pc Libs.private)
        # resolves to the conan libdeflate.so rather than a stale/system one.
        dep_libdirs = [
            os.path.join(f, "lib")
            for f in (htslib_folder, xz_folder, bzip2_folder, zlib_folder,
                      libdeflate_folder)
        ]
        link_search = " ".join(["-L" + d for d in dep_libdirs])
        linker_flags = link_search

        cmake = CMake(self)
        cmake.configure(variables={
            # The build is forced static IN source(): we patch the upstream
            # CMakeLists so its else() branch no longer does
            # `set(BUILD_SHARED_LIBS ON)` (upstream defaults BUILD_STATIC=OFF and
            # would otherwise build every tool as a dynamic binary that links
            # libvcflib.so/libwfa2.so — at test runtime the loader then aborts
            # with "symbol not found"). With BUILD_SHARED_LIBS off the tools link
            # libvcflib.a + wfa2_static.a and have NO shared-lib runtime
            # resolution, eliminating that failure class entirely.
            # Disable OpenMP. Upstream defaults OPENMP=ON and line 444 does
            # `target_link_libraries(vcflib OpenMP::OpenMP_CXX)`, which puts
            # `-fopenmp` on every tool's link. `-fopenmp` adds a runtime
            # dependency on the LLVM OpenMP shared lib (libomp.so: __kmpc_*,
            # omp_* symbols). The OHOS device has no libomp.so, so after the
            # static-vcflib fix every tool died at startup with
            # "omp_get_thread_num: symbol not found" / "__kmpc_fork_call: symbol
            # not found". vcflib never actually needs OMP here: every `#pragma
            # omp` is guarded behind HAS_OPENMP (never defined) and vcfwave
            # guards its omp calls behind WFA_PARALLEL (off), so OPENMP=OFF is
            # purely runtime-dependency removal with no functional change (the
            # tools were effectively serial already).
            "OPENMP": "OFF",
            "CMAKE_PREFIX_PATH": ";".join([
                zlib_folder, xz_folder, bzip2_folder, htslib_folder,
                libdeflate_folder,
            ]),
            "CMAKE_EXE_LINKER_FLAGS": linker_flags,
            "CMAKE_SHARED_LINKER_FLAGS": linker_flags,
            # Embed every conan dependency lib dir in the built binaries' RPATH
            # (CMAKE_BUILD_RPATH), not just the build folder. vcflib tools each
            # carry a DT_NEEDED on the SHARED libdeflate.so (from htslib's
            # --with-libdeflate -> htslib.pc Libs.private `-ldeflate`). Without
            # an explicit RPATH the runtime loader relies on LD_LIBRARY_PATH /
            # the system search path, which differs between hosts.
            #
            # PRECEDING-ROUND LESSON (RPATH-to-absolute-conan-cache FAILED on
            # the CI worker while passing on the preflight device): pointing the
            # RPATH at the machine-specific absolute conan-cache libdeflate
            # path was NOT honored on the CI worker, so the tool still resolved
            # a stale/system libdeflate.so lacking `libdeflate_*` symbols
            # ("Error relocating vcffilter: libdeflate_deflate_compress:\n
            # symbol not found") and every real VCF tool (vcf2tsv /
            # vcfallelicprimitives / vcfwave / vcffilter) aborted at startup.
            #
            # NEW deterministic route (this round): make the runtime resolve OUR
            # exact libdeflate.so with NO dependence on any host-specific
            # absolute path:
            #   1) $ORIGIN entry in the build RPATH — the loader looks for
            #      libdeflate.so in the SAME directory as each tool binary
            #      (build/Release/ for ctest, and the installed bin/ dir).
            #   2) build() copies the exact conan libdeflate.so we linked
            #      against into self.build_folder (== CMAKE_BINARY_DIR), which
            #      is ALSO first in the ctest harness LD_LIBRARY_PATH
            #      (${CMAKE_BINARY_DIR}:...) — the highest-precedence search
            #      list on both glibc and MUSL.
            #   3) keep the conan libdir and build_folder as further fallbacks.
            # Together these resolve deterministically on ANY host, so preflight
            # and CI behave identically.
            "CMAKE_BUILD_RPATH": ";".join(
                ["$ORIGIN", self.build_folder] + dep_libdirs),
            "CMAKE_INSTALL_RPATH_USE_LINK_PATH": "TRUE",
            "ZLIB_INCLUDE_DIR": os.path.join(zlib_folder, "include"),
            "ZLIB_LIBRARY": os.path.join(zlib_folder, "lib", "libz.a"),
            "ZLIB_LIBRARY_RELEASE": os.path.join(zlib_folder, "lib", "libz.a"),
            "LIBLZMA_INCLUDE_DIR": os.path.join(xz_folder, "include"),
            "LIBLZMA_LIBRARY": os.path.join(xz_folder, "lib", "liblzma.a"),
            "BZIP2_INCLUDE_DIR": os.path.join(bzip2_folder, "include"),
            "BZIP2_LIBRARY": os.path.join(bzip2_folder, "lib", "libbz2.a"),
            "BZIP2_LIBRARY_RELEASE": os.path.join(bzip2_folder, "lib", "libbz2.a"),
        })
        cmake.build()

        # Deterministic libdeflate runtime resolution (see the CMAKE_BUILD_RPATH
        # comment above for the full reasoning). The vcflib tools carry a
        # DT_NEEDED on the SHARED libdeflate.so and the ctest doctest harness
        # prepends ${CMAKE_BINARY_DIR} (= self.build_folder) to each test's
        # LD_LIBRARY_PATH.
        # Deploy EVERY libdeflate.so* name from the
        # package into the ctest working dir so the loader never falls through
        # to a stale system libdeflate.so.<N>. PRIOR-ROUND FIX (why the
        # first-entry copy alone still failed on CI): the previous code copied
        # only a single file — so_candidates[0] (the un-versioned libdeflate.so
        # after sorting) — as build_folder/libdeflate.so. But the tools' DT_NEEDED
        # on libdeflate records the library SONAME, which is the VERSIONED name
        # (libdeflate.so.1). The loader inside the ctest LD_LIBRARY_PATH looked
        # for build_folder/libdeflate.so.1, did NOT find it (only libdeflate.so
        # had been placed), and fell through to the system/stale libdeflate.so.1,
        # which lacks the newer libdeflate_* symbols -> "Error relocating
        # .../vcffilter: libdeflate_deflate_compress: symbol not found" on the CI
        # worker (preflight passed there because that device's libdeflate package
        # is the static-only variant, giving the tools no .so dependency at all).
        # We copy every libdeflate.so* name (un-versioned symlink name AND all
        # versioned files), dereferencing symlinks into real files, so whichever
        # SONAME name the DT_NEEDED references the loader finds OUR copy first.
        def _deploy_libdeflate(destdir):
            libdeflate_libdir = os.path.join(libdeflate_folder, "lib")
            if not os.path.isdir(libdeflate_libdir):
                return 0
            names = sorted(f for f in os.listdir(libdeflate_libdir)
                           if f.startswith("libdeflate.so"))
            if not names:
                # Static-only variant: tools have no runtime .so dependency.
                return 0
            os.makedirs(destdir, exist_ok=True)
            for n in names:
                src = os.path.join(libdeflate_libdir, n)
                dst = os.path.join(destdir, n)
                if os.path.islink(src):
                    # Dereference the symlink into a real file with the SAME
                    # (SONAME) basename so that DT_NEEDED name resolves here too.
                    src = os.path.realpath(src)
                shutil.copy2(src, dst)
            return len(names)

        copied = _deploy_libdeflate(self.build_folder)
        if copied:
            self.output.info(
                "copied %d libdeflate.so* file(s) -> %s "
                "(ctest LD_LIBRARY_PATH first entry)" %
                (copied, self.build_folder))
        else:
            # libdeflate resolved statically (no shared lib shipped): the tools
            # have no runtime libdeflate.so dependency, so no copy is needed.
            self.output.info(
                "libdeflate package has no shared libdeflate.so under %s; "
                "tools linked libdeflate statically (no runtime .so dep)" %
                libdeflate_folder)

        # Run the upstream ctest suite (Python doctests over the built tools).
        self._run_upstream_ctest(cmake)

    def _run_upstream_ctest(self, cmake):
        ctest_log = os.path.join(self.build_folder, "ctest_output.log")
        # ctest returns non-zero when a case fails; capture stdout to parse
        # the per-test summary instead of relying on the exit code alone.
        try:
            self.run(
                f'cd "{self.build_folder}" && ctest --output-on-failure > "{ctest_log}" 2>&1',
                env="conanbuild")
        except ConanException:
            self.output.warning("ctest exited non-zero — see ctest_output.log")
        with open(ctest_log, "r", encoding="utf-8", errors="replace") as fh:
            out = fh.read()
        self.output.info("ctest output tail:\n" + out[-4000:])
        # ctest summary: "100% tests passed, 0 tests failed out of 7"
        mt = re.search(r"(\d+)% tests passed, (\d+) tests failed out of (\d+)", out)
        if not mt:
            raise ConanException(
                "could not parse ctest summary; full output tail:\n" + out[-2000:])
        pct, failed, total = int(mt.group(1)), int(mt.group(2)), int(mt.group(3))
        if failed or pct != 100:
            failed_lines = [
                l for l in out.splitlines()
                if re.search(r"\*\*\*Failed|\*\*\*Timeout|Failed ", l)]
            raise ConanException(
                f"upstream test suite failed: {failed}/{total} cases failed\n"
                + "\n".join(failed_lines[:40]))
        marker = {
            "status": "passed",
            "framework": "ctest",
            "command": "ctest --output-on-failure (vcflib python doctests)",
            "discovered": total,
            "executed": total,
            "passed": total - failed,
            "failed": failed,
            "skipped": 0,
            # The ten-case official ctest suite (UPSTREAM_TEST_TOTAL=10) is the
            # declared upstream_test_total; OHOS runs the seven that register when
            # pybind11/zig are absent. These gaps reconcile declared-total - passed
            # (10 - 7 = 3).
            "gaps": UPSTREAM_GAPS,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False),
              flush=True)
        # Persist the marker (as structured JSON) so test_package can re-emit it
        # on EVERY `conan create` run. Conan skips build()/package() on cache
        # hits, so the build()-time marker would otherwise disappear from the
        # preflight log (the pagodacf/gmime R26 regression: discovered=0
        # executed=0). package() copies this file into the package's res/ dir.
        with open(os.path.join(self.build_folder, "upstream_test_result.json"),
                  "w", encoding="utf-8") as fh:
            json.dump(marker, fh, ensure_ascii=False)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Ship the persisted upstream-test marker so test_package can re-emit
        # HMBS_UPSTREAM_TEST_RESULT on cache-hit rounds (build() skipped).
        res_dir = os.path.join(self.package_folder, "res")
        os.makedirs(res_dir, exist_ok=True)
        marker_src = os.path.join(self.build_folder, "upstream_test_result.json")
        if os.path.isfile(marker_src):
            copy(self, "upstream_test_result.json",
                 self.build_folder, res_dir)
        # Deterministic libdeflate runtime resolution for INSTALLED tools too:
        # the vcflib tools carry a DT_NEEDED on the SHARED libdeflate.so, and the
        # build RPATH starts with $ORIGIN (see CMAKE_BUILD_RPATH above). Place
        # every libdeflate.so* we deployed into the build folder (all SONAME
        # variants, see build()) next to the installed tool binaries so an
        # installed consumer also resolves our library deterministically instead
        # of a stale/system libdeflate.so (the CI-worker "symbol not found" class).
        bin_dir = os.path.join(self.package_folder, "bin")
        deployed = []
        if os.path.isdir(self.build_folder):
            deployed = sorted(
                f for f in os.listdir(self.build_folder)
                if f.startswith("libdeflate.so"))
        if deployed:
            os.makedirs(bin_dir, exist_ok=True)
            for n in deployed:
                shutil.copy2(os.path.join(self.build_folder, n),
                             os.path.join(bin_dir, n))

    def package_info(self):
        self.cpp_info.libs = ["vcflib"]
        self.cpp_info.includedirs = ["include/vcflib"]
        # libvcflib.a statically references htslib/zlib/lzma/bz2 symbols
        # (linked via PkgConfig::htslib at build time). Propagate them so
        # consumers (incl. test_package) link success.
        # NOTE: the reference syntax here is `pkg::component`. Each of these
        # deps (htslib, zlib, xz, bzip2 conan recipes) declares NO explicit
        # components — they expose only the implicit top-level "global"
        # component, which CMakeDeps names after the PACKAGE NAME. So the valid
        # reference is `pkg::pkg` (e.g. `bzip2::bzip2`), NOT the library file
        # name (e.g. `bzip2::bz2` — the ``bz2`` lib is just self.cpp_info.libs
        # content). Using ``bzip2::bz2`` makes CMakeDeps fail at test_package
        # generate() with:
        #   Component 'bzip2::bz2' not found in 'bzip2' package requirement
        # The actual CMake target name is unaffected: it comes from each dep's
        # set_property("cmake_target_name", ...) (ZLIB::ZLIB, BZip2::BZip2,
        # LibLZMA::LibLZMA, htslib::htslib) independently of this reference.
        self.cpp_info.requires = [
            "htslib::htslib", "zlib::zlib", "xz::xz", "bzip2::bzip2",
            "libdeflate::libdeflate",
        ]
        self.cpp_info.set_property("cmake_file_name", "vcflib")
        self.cpp_info.set_property("cmake_target_name", "vcflib::vcflib")
        self.cpp_info.set_property("pkg_config_name", "vcflib")
        self.cpp_info.bindirs = ["bin"]
