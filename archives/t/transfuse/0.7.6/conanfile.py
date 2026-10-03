#!/usr/bin/env python3
"""Conan recipe — transfuse 0.7.6 (CMake).

transfuse runs formatted documents (HTML / HTML-fragment / ODT / DOCX / PPTX /
TXT) through transformations or translation.  It extracts nested inline
formatting into manageable spans, optionally pipes the resulting stream through
a transformation handler (``apertium`` or ``visl``), injects the transformed
stream back into the original document and restores the formatting.

Build system: CMake >= 3.12 (upstream ``CMakeLists.txt``).
Products: one executable ``transfuse`` plus the ``tf-extract`` / ``tf-inject`` /
``tf-clean`` aliases that upstream creates as symlinks.

Dependencies, as resolved by the upstream ``CMakeLists.txt``:

  ============  ==========================================  =============
  dependency    upstream lookup                             Conan
  ============  ==========================================  =============
  libxml2       ``pkg_search_module(LIBXML2 REQUIRED ...)`` libxml2
  sqlite3       ``pkg_search_module(SQLITE3 REQUIRED ...)`` sqlite3
  libzip        ``find_path``/``find_library`` on zip.h     libzip
  icu           ``find_package(ICU REQUIRED)``             icu
  xxhash        ``find_path``/``find_library``             xxhash
  ============  ==========================================  =============

* Upstream looks libxml2 and sqlite3 up through ``pkg_search_module()``, which
  puts only the ``-l`` flags in ``<PREFIX>_LIBRARIES`` and reports the search
  path separately as ``<PREFIX>_LIBRARY_DIRS``.  Upstream links the former and
  never adds the latter, so the link line ends up with a bare ``-lxml2`` /
  ``-lsqlite3``; the hook declares the dependency libdirs so the ``-L`` comes
  back.  ICU is resolved by CMake's own ``FindICU`` module through
  ``CMAKE_PREFIX_PATH``, and libzip/xxhash by plain ``find_*`` calls, which
  also honour ``CMAKE_PREFIX_PATH``.

OHOS notes
----------
* Pure C++/CMake, so the CI toolchain matrix covers it (clang/cmake/ninja all
  available).  No Rust/OCaml-style toolchain gap.
* The upstream CMake enables ``-flto`` when the compiler accepts it and then
  hardcodes ``CMAKE_AR=gcc-ar``.  That only affects static archive creation and
  transfuse builds no static archives (``BUNDLED_XXHASH=OFF``), so it is a
  no-op here; the executable links through the clang driver / lld.
* ``test_big_endian()`` resolves through ``CMAKE_<LANG>_BYTE_ORDER`` on
  CMake >= 3.20, so no ``try_run`` is attempted and no
  ``CMAKE_CROSSCOMPILING_EMULATOR`` is needed.
* The OHOS profile pins ``compiler.cppstd=17``, which CMakeToolchain turns
  into an unconditional ``set(CMAKE_CXX_STANDARD 17)``.  CMake appends that
  ``-std=`` flag *after* ``CMAKE_CXX_FLAGS``, so it overrides the
  ``-std=c++20`` that upstream's own ``CHECK_CXX_COMPILER_FLAG`` probe puts
  into ``CMAKE_CXX_FLAGS``, and the C++20-only ``std::map``/``std::set``
  ``::contains`` in ``src/dom.cpp`` does not compile.  The standard is unset
  through a ``CMAKE_PROJECT_INCLUDE`` hook so upstream's probe decides again
  (same approach as arg_router 1.3.0).
* Upstream ``include/xxhash/CMakeLists.txt`` propagates ``XXHASH_INCLUDE_DIRS``
  from itself instead of from the ``XXHASH_INCLUDE_DIR`` that ``find_path``
  just produced, so the header directory never reaches the ``transfuse``
  target and ``#include <xxhash.h>`` cannot resolve.  Patched by
  ``0001-fix-xxhash-include-dir-parent-scope.patch``; this is an upstream typo,
  not a platform workaround.
* R26: static only, so the executable stays self-contained.
* R32: supports both Linux and OHOS.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, export_conandata_patches,
                              get, save)
from conan.tools.gnu import PkgConfigDeps


class TransfuseConan(ConanFile):
    name = "transfuse"
    version = "0.7.6"
    description = "Runs formatted documents through transformations/translation"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/TinoDidriksen/transfuse"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # CMake adaptation hook, written to disk by generate() and pulled in through
    # CMAKE_PROJECT_INCLUDE right after project() has run the Conan toolchain.
    _HOOK_CMAKE = """\
# transfuse 0.7.6 — adaptation hook (written by conanfile.py generate(), do not edit)
#
# The OHOS profile pins compiler.cppstd=17, and conan_toolchain.cmake turns that
# into an unconditional `set(CMAKE_CXX_STANDARD 17)`. CMake appends the -std=
# flag derived from that variable *after* CMAKE_CXX_FLAGS and after
# CMAKE_CXX_FLAGS_RELEASE, so it overrides the -std=c++20 that upstream's own
# CHECK_CXX_COMPILER_FLAG probe has already placed in CMAKE_CXX_FLAGS, and the
# C++20-only std::map/std::set::contains in src/dom.cpp does not compile.
#
# The value cannot be corrected from the command line or the cache: the
# toolchain uses a normal set(), which shadows both. This hook runs in the
# top-level directory scope right after project() returns, so a plain set()
# here wins. It has to be a real value rather than unset() because an empty
# CMAKE_CXX_STANDARD makes CMake fall back to CMAKE_CXX_STANDARD_DEFAULT, which
# is 14 for clang 15 — that appends a trailing -std=c++14 and lands in exactly
# the same place as the value it replaced.
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
"""

    @staticmethod
    def _dependency_libdirs(conanfile):
        # Absolute libdirs of every host requirement, taken from the dependency
        # graph so nothing is hard-coded (R49).
        libdirs = []
        for dep in conanfile.dependencies.host.values():
            if not dep.cpp_info:
                continue
            for libdir in dep.cpp_info.libdirs:
                path = os.path.join(dep.package_folder, libdir)
                if path not in libdirs:
                    libdirs.append(path)
        return libdirs

    @staticmethod
    def _icu_data_library(conanfile):
        # FindICU only searches the icu data library when "data" is listed in
        # ICU_FIND_COMPONENTS, and upstream calls find_package(ICU REQUIRED)
        # without components.  This ICU is a static build, so libicuuc.a keeps
        # an undefined reference to icudt<ver>_dat that only libicudata.a
        # satisfies and the link fails with "undefined symbol: icudt76_dat".
        # Locate that archive from the dependency graph rather than guessing a
        # path (R49).
        for dep in conanfile.dependencies.host.values():
            if dep.ref.name != "icu" or not dep.cpp_info:
                continue
            for libdir in dep.cpp_info.libdirs:
                for lib in dep.cpp_info.libs:
                    if "icudata" not in lib:
                        continue
                    found = sorted(glob.glob(
                        os.path.join(dep.package_folder, libdir, "lib{}*".format(lib))))
                    if found:
                        return found[0]
        return ""

    def _hook_cmake(self):
        extra = []
        # pkg_search_module() puts only the -l flags in <PREFIX>_LIBRARIES
        # (FindPkgConfig.cmake queries --libs-only-l for it) and reports the
        # search path separately as <PREFIX>_LIBRARY_DIRS.  Upstream links
        # ${LIBXML2_LIBRARIES}/${SQLITE3_LIBRARIES} and never adds the
        # matching LIBRARY_DIRS, so the final link line carries a bare -lxml2
        # / -lsqlite3 with no -L and ld.lld reports "unable to find library".
        # Declaring the directories once for the whole project supplies the
        # missing -L for both.
        extra.append("link_directories(\n{}\n)".format(
            "\n".join('    "{}"'.format(d) for d in self._dependency_libdirs(self))))

        icu_data = self._icu_data_library(self)
        if icu_data:
            # link_libraries() entries are emitted before the target's own
            # libraries, so the data archive would reach the linker ahead of
            # the archives that reference it.  Repeating the static libraries
            # makes the final link order-independent.
            extra.append('link_libraries("{}")'.format(icu_data))
            extra.append("set(CMAKE_LINK_INTERFACE_MULTIPLICITY 3)")
        return self._HOOK_CMAKE + "\n".join(extra) + "\n"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("icu/76.1")
        self.requires("libxml2/2.15.3.1")
        self.requires("libzip/1.11.4")
        self.requires("sqlite3/3.53.4")
        self.requires("xxhash/0.8.4")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()

        tc = CMakeToolchain(self)
        # Hand the C++ standard decision back to upstream and restore the -L
        # search paths pkg_search_module() leaves out (see _hook_cmake).
        hook = os.path.join(self.build_folder, "transfuse_adapt_hook.cmake")
        save(self, hook, self._hook_cmake())
        tc.cache_variables["CMAKE_PROJECT_INCLUDE"] = hook
        # R26: static only, keep the installed executable self-contained.
        tc.cache_variables["BUILD_SHARED_LIBS"] = False
        # Use the Conan-provided xxhash instead of the in-tree copy.
        tc.cache_variables["BUNDLED_XXHASH"] = False
        tc.cache_variables["BUILD_DOCS"] = False
        tc.cache_variables["BUILD_MAN"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream registers 14 cases in tests/CMakeLists.txt (12 extract-*
        # across 6 formats x 2 handlers, plus 2 clean-*).  They drive the
        # freshly built executable and diff against checked-in .expect files.
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # HarmonyOS PC XPM requires a code signature on every executable that is
        # exec'd.  The signer only exists inside the HNP image on the build
        # worker (/data/service/hnp/bin), never in a cross-compile workspace, so
        # this step is best-effort: sign when the tool is present, otherwise
        # leave the freshly linked ELF untouched.
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(signer):
            return

        bindir = os.path.join(self.package_folder, "bin")
        if not os.path.isdir(bindir):
            return

        for name in sorted(os.listdir(bindir)):
            path = os.path.join(bindir, name)
            if os.path.islink(path) or not self._is_elf(path):
                continue
            self.run('{} --remove-section .codesign "{}"'.format(objcopy, path),
                     ignore_errors=True)
            self.run('{} sign -inFile "{}" -outFile "{}" -selfSign 1'.format(signer, path, path))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]