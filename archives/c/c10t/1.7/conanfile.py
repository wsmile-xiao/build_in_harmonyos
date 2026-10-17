#!/usr/bin/env python3
"""Conan recipe for c10t 1.7 — Minecraft cartography tool.

c10t (BSD-3-Clause, C++, CMake) renders Minecraft worlds to PNG images.
This is an application package (R38): only the `c10t` executable is
published; the bundled `libs/unc` helper library is built in-tree
(`BUILD_DEV_LIBS=ON`, same as the Homebrew formula) and never packaged.

OHOS/aarch64 adaptation notes (see notes.md):
- Upstream `cmake_minimum_required(VERSION 2.6)` is bumped to 3.5 by patch
  (device CMake 4.x removed <3.5 compatibility); the Homebrew formula
  passes the equivalent `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`.
- Upstream probes the version with `git rev-list`; conan source trees have
  no .git, so the patch falls back to the fixed "1.7" revision.
- `find_package(Boost ... COMPONENTS thread filesystem system)` drops the
  `system` component: Boost.System is header-only since Boost 1.85 and the
  component no longer exists (Homebrew DATA-patch precedent).
- `filesystem::basename()/extension()/is_regular()` were removed from
  Boost.Filesystem; the patch migrates to
  `path::stem()/.extension()/is_regular_file()` (Homebrew precedent), and
  the `file_filter(path().filename())` call gains an explicit `.string()`
  (the filter matches on the extension, so stem() would corrupt it).
- Upstream ships no `install()` target, so `package()` copies the
  `<build>/c10t` binary (CMAKE_RUNTIME_OUTPUT_DIRECTORY = CMAKE_BINARY_DIR)
  into the package `bin/` directory (Homebrew `bin.install` equivalent).
- Conan CMakeDeps uses CONFIG mode: legacy `Boost_INCLUDE_DIR` stays empty,
  so the patch propagates imported-target include dirs globally for the
  intermediate static libs.
- Host `boost/1.91.0.1` is a subset build (`BOOST_INCLUDE_LIBRARIES`) whose
  package omits header-only dirs such as `boost/ptr_container` (included by
  `src/nbt/nbt.hpp`). The published header-only `boost/1.84.0` package keeps
  the complete header set, so it is used as a build-context header fallback
  (`tool_requires`, autodock-vina 1.2.7 precedent; host and build contexts
  may carry different versions of one package without a graph conflict).
  `generate()` passes both include dirs via `C10T_BOOST_INCLUDE_DIRS`
  (host first, fallback second) plus the component defines.
- Boost.Filesystem ABI split: 1.91 declares
  `directory_iterator_construct(..., directory_options, ...)` while 1.84
  declares `(..., unsigned int, ...)`; mixing 1.91 libboost_filesystem.so
  with 1.84 fallback declarations (quoted-include fallthrough from a
  partial host filesystem subtree) leaves that symbol undefined.
  `generate()` therefore shadows the complete 1.84 `boost/filesystem/**`
  subtree first in `C10T_BOOST_INCLUDE_DIRS` and links the device-verified
  1.84 `libboost_filesystem.a` (`C10T_BOOST_FS184_LIB`, via c10t-mc PUBLIC)
  while thread stays on the 1.91 shared lib.
- `src/image/format/png.hpp` uses `Z_DEFAULT_STRATEGY` without including
  `<zlib.h>` (transitive via `<png.h>` on some libpng builds, undeclared
  with Conan's libpng/zlib split); the patch adds the missing include
  (upstream commit 800977bb, also applied by Homebrew).
- OHOS musl lacks the POSIX thread-cancellation API
  (`pthread_setcancelstate/setcanceltype`, E127/E085), which Boost's
  `sp_thread_sleep.hpp` calls around `nanosleep()`. `generate()` writes a
  musl-detected shim into the build folder and force-includes it via
  `-include` for all C/C++ units (a recipe-side header alone never reaches
  the device cache because `export_sources()` only exports conandata.yml).
- Upstream configures `font.ttf` via an unconditional
  `copy_if_different`; the 1.7 release tarball layout may lack that file
  at the source root, so `build()` ensures a placeholder exists and the
  destination directory is present before `cmake.configure()`.
- Upstream ships no registered test suite: `test/` only defines the
  `EXCLUDE_FROM_ALL` `c10t-test` helper (needs `boost_unit_test_framework`,
  not required here) and the top tree never calls `enable_testing()` /
  `add_test()`. There is therefore no `ctest`/`make check` entry to run;
  the no_tests audit lives in `test_package/MANIFEST.yml`.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class C10tConan(ConanFile):
    name = "c10t"
    version = "1.7"
    description = "Minecraft cartography tool (map renderer)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/udoprog/c10t"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("boost/1.91.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("libpng/1.6.58", transitive_headers=True, transitive_libs=True)
        self.requires("freetype/2.14.3", transitive_headers=True, transitive_libs=True)
        # zlib arrives via libpng, but c10t links ${ZLIB_LIBRARIES}
        # directly, so it is an explicit direct requirement (R36: pinned to
        # zlib/1.3.1.1 to match the published libpng/1.6.58 closure; pinning
        # zlib/1.3.1 conflicts with libpng's zlib/1.3.1.1 in one graph).
        self.requires("zlib/1.3.1.1", transitive_headers=True, transitive_libs=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"c10t supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build_requirements(self):
        # Header-only fallback for Boost dirs missing from the host subset
        # package (e.g. boost/ptr_container/ptr_vector.hpp). Only `-I`
        # fallback: linking stays on the host 1.91.0.1 libraries.
        self.tool_requires("boost/1.84.0")

    def _boost_include_dirs(self):
        host_inc = os.path.join(
            self.dependencies["boost"].package_folder, "include"
        )
        fallback_inc = os.path.join(
            self.dependencies.build["boost"].package_folder, "include"
        )
        if not os.path.isdir(host_inc):
            raise ConanException(
                "host boost include dir missing: %s" % host_inc
            )
        ptr_header = os.path.join("boost", "ptr_container", "ptr_vector.hpp")
        host_has = os.path.isfile(os.path.join(host_inc, ptr_header))
        fallback_has = os.path.isfile(os.path.join(fallback_inc, ptr_header))
        if not (host_has or fallback_has):
            raise ConanException(
                "neither host boost (%s) nor fallback boost (%s) provides %s"
                % (host_inc, fallback_inc, ptr_header)
            )
        dirs = [host_inc]
        if os.path.isdir(fallback_inc) and fallback_inc not in dirs:
            # Host first so its headers win; the fallback only fills gaps.
            dirs.append(fallback_inc)
        return dirs

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # Component defines from the Boost packages (header-only consumers
        # such as c10t-mc get no target-propagated defines, so set them
        # toolchain-wide, matching the published component metadata).
        tc.preprocessor_definitions["BOOST_ALL_NO_LIB"] = "1"
        try:
            shared = self.dependencies["boost"].options.get_safe("shared", True)
        except Exception:
            shared = True
        if shared:
            tc.preprocessor_definitions["BOOST_ALL_DYN_LINK"] = "1"
        # Boost header inventory (proves which side provides the
        # directory-iteration declarations consumed below): Boost 1.91
        # declares directory_iterator_construct(..., directory_options, ...)
        # while 1.84 declares (..., unsigned int, ...). A mixed include
        # path (quoted-include fallthrough from a partial 1.91 filesystem
        # subtree into the 1.84 fallback) links against a
        # libboost_filesystem.so whose symbols never match.
        _boost_inc_dirs = self._boost_include_dirs()
        _host_inc, _fallback_inc = _boost_inc_dirs[0], _boost_inc_dirs[-1]
        for _label, _inc in (("host", _host_inc), ("fallback", _fallback_inc)):
            _ver = "unknown"
            try:
                with open(
                    os.path.join(_inc, "boost", "version.hpp"),
                    "r", encoding="utf-8", errors="replace",
                ) as _vf:
                    for _line in _vf:
                        _s = _line.strip()
                        if _s.startswith("#") and "BOOST_VERSION " in _s:
                            _ver = _s
                            break
            except OSError as _exc:
                _ver = "unreadable (%s)" % _exc
            _dir_hpp = os.path.join(
                _inc, "boost", "filesystem", "directory.hpp"
            )
            self.output.info(
                "c10t: %s boost headers %s: %s; filesystem/directory.hpp %s"
                % (
                    _label,
                    _inc,
                    _ver,
                    "present"
                    if os.path.isfile(_dir_hpp)
                    else "MISSING",
                )
            )
        # Version-consistent Boost.Filesystem headers: shadow ONLY the
        # boost/filesystem/** subtree (plus boost/filesystem.hpp) from the
        # complete 1.84 fallback package into the build folder and put the
        # shadow first, so every filesystem declaration comes from 1.84
        # while thread/other headers still resolve from the 1.91 host.
        # (Copies, not symlinks: HMDFS-safe. Contents logged for audit.)
        _shadow = os.path.join(self.build_folder, "c10t_boost_fs184")
        _shadow_count = 0
        try:
            os.makedirs(self.build_folder, exist_ok=True)
            _fs_src = os.path.join(_fallback_inc, "boost", "filesystem")
            _fs_dst = os.path.join(_shadow, "boost", "filesystem")
            if os.path.isdir(_fs_src):
                shutil.copytree(_fs_src, _fs_dst, dirs_exist_ok=True)
                for _root, _ds, _fs in os.walk(_fs_dst):
                    _shadow_count += len(_fs)
            _top_src = os.path.join(_fallback_inc, "boost", "filesystem.hpp")
            if os.path.isfile(_top_src):
                os.makedirs(os.path.join(_shadow, "boost"), exist_ok=True)
                shutil.copy2(
                    _top_src, os.path.join(_shadow, "boost", "filesystem.hpp")
                )
                _shadow_count += 1
            self.output.info(
                "c10t: filesystem shadow %s holds %d files"
                % (_shadow, _shadow_count)
            )
        except Exception as _exc:
            self.output.warning("c10t: filesystem shadow failed (%s)" % _exc)
            _shadow = None
        _ordered_incs = list(_boost_inc_dirs)
        if _shadow and os.path.isdir(_shadow):
            _ordered_incs.insert(0, _shadow)
        tc.cache_variables["C10T_BOOST_INCLUDE_DIRS"] = ";".join(
            _ordered_incs
        )
        # C++11: required by modern Boost headers (Homebrew passes
        # -DCMAKE_CXX_STANDARD=11 for the same reason).
        tc.cache_variables["CMAKE_CXX_STANDARD"] = "11"
        # Device CMake is 4.x: allow the patched 3.5 minimum explicitly.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # The recipe links the shared Conan dependency closure; the
        # upstream default (Boost_USE_STATIC_LIBS=TRUE) would make
        # FindBoost pick .a files that do not match the Conan packages.
        tc.cache_variables["Boost_USE_STATIC_LIBS"] = False
        # Prefer Conan CMakeDeps CONFIG packages over CMake-bundled
        # Find-modules: in MODULE mode the legacy *_LIBRARIES variables
        # point at system paths and the imported targets miss the OHOS
        # binaries (undefined boost_filesystem / FT_* symbols at link).
        tc.cache_variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = True
        # Absolute-path Boost THREAD lib (recipe-side ground truth): link
        # libboost_thread by absolute path so the link never depends on
        # imported-target name matching. Filesystem is handled separately
        # below (version-consistent 1.84 static lib); the lib listing is
        # logged so the preflight log shows exactly what the resolved
        # host boost package ships.
        _boost_libdir = os.path.join(
            self.dependencies["boost"].package_folder, "lib"
        )
        try:
            _libfiles = sorted(os.listdir(_boost_libdir))
        except OSError as _exc:
            _libfiles = []
            self.output.warning(
                "c10t: cannot list host boost lib dir %s (%s)"
                % (_boost_libdir, _exc)
            )
        self.output.info(
            "c10t: host boost lib dir %s contains: %s"
            % (_boost_libdir, ", ".join(_libfiles[:60]))
        )
        _boost_link_libs = []
        for _comp in ("thread",):
            _found = None
            for _pat in (
                "libboost_%s.so" % _comp,
                "libboost_%s.a" % _comp,
                "boost_%s.lib" % _comp,
            ):
                _cand = os.path.join(_boost_libdir, _pat)
                if os.path.isfile(_cand):
                    _found = _cand
                    break
            if _found:
                _boost_link_libs.append(_found)
            else:
                self.output.warning(
                    "c10t: host boost package provides no %s library"
                    % _comp
                )
        if _boost_link_libs:
            tc.cache_variables["C10T_BOOST_LINK_LIBS"] = ";".join(
                _boost_link_libs
            )
        # Version-consistent Boost.Filesystem LIBRARY: the 1.91
        # libboost_filesystem.so exports the directory_options ABI while
        # the shadowed headers declare the 1.84 unsigned-int ABI, so link
        # the device-verified 1.84 static lib (its upstream filesystem
        # tests pass on OHOS) by absolute path from the build context.
        # It is consumed via c10t-mc PUBLIC (see patch) so the archive
        # lands after the static convenience libs on the link line.
        _fb_libdir = os.path.join(
            self.dependencies.build["boost"].package_folder, "lib"
        )
        try:
            _fb_libs = sorted(os.listdir(_fb_libdir))
        except OSError as _exc:
            _fb_libs = []
            self.output.warning(
                "c10t: cannot list fallback boost lib dir %s (%s)"
                % (_fb_libdir, _exc)
            )
        self.output.info(
            "c10t: fallback boost lib dir %s contains: %s"
            % (_fb_libdir, ", ".join(_fb_libs[:60]))
        )
        _fs184 = os.path.join(_fb_libdir, "libboost_filesystem.a")
        if os.path.isfile(_fs184):
            tc.cache_variables["C10T_BOOST_FS184_LIB"] = _fs184
            self.output.info("c10t: Boost.Filesystem lib -> %s" % _fs184)
        else:
            self.output.warning(
                "c10t: fallback boost package provides no libboost_filesystem.a"
            )
        # Temporary link diagnostics: print the full link command so the
        # preflight tail proves which boost binaries reach the linker.
        tc.cache_variables["CMAKE_VERBOSE_MAKEFILE"] = True
        # Build the bundled libs/unc in-tree (Homebrew default path).
        tc.cache_variables["BUILD_DEV_LIBS"] = True
        # OHOS musl lacks pthread_setcancelstate/setcanceltype (E127/E085),
        # called by Boost sp_thread_sleep.hpp around nanosleep(). The shim
        # is written into the build folder here (not read from the recipe
        # folder: `export_sources()` only exports conandata.yml, so a
        # recipe-side header never reaches the device cache) and
        # force-included before every translation unit. On glibc the guard
        # is false and the header is a no-op.
        _shim_lines = [
            "#pragma once",
            "#include <pthread.h>",
            "#if defined(__linux__) && !defined(__GLIBC__)",
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
            "static inline int c10t_pthread_setcancelstate_noop(int s, int *o)",
            "{ if (o) { *o = s; } return 0; }",
            "static inline int c10t_pthread_setcanceltype_noop(int t, int *o)",
            "{ if (o) { *o = t; } return 0; }",
            "#ifdef pthread_setcancelstate",
            "#undef pthread_setcancelstate",
            "#endif",
            "#ifdef pthread_setcanceltype",
            "#undef pthread_setcanceltype",
            "#endif",
            "#define pthread_setcancelstate c10t_pthread_setcancelstate_noop",
            "#define pthread_setcanceltype c10t_pthread_setcanceltype_noop",
            "#endif",
            "",
        ]
        try:
            os.makedirs(self.build_folder, exist_ok=True)
            _stub = os.path.join(
                self.build_folder, "c10t_ohos_pthread_stub.h"
            )
            with open(_stub, "w", encoding="utf-8", newline="\n") as _f:
                _f.write("\n".join(_shim_lines))
            self.output.info("c10t: OHOS pthread shim -> %s" % _stub)
            # Conan 2 CMakeToolchain exposes extra_cflags/extra_cxxflags
            # (no plain cflags/cxxflags attributes).
            _inc = "-include %s" % _stub
            _done = False
            for _c_attr in ("extra_cflags", "cflags"):
                if hasattr(tc, _c_attr):
                    getattr(tc, _c_attr).append(_inc)
                    _done = True
                    break
            for _cxx_attr in ("extra_cxxflags", "cxxflags"):
                if hasattr(tc, _cxx_attr):
                    getattr(tc, _cxx_attr).append(_inc)
                    _done = True
                    break
            if not _done:
                raise ConanException(
                    "CMakeToolchain has neither extra_cflags nor cflags"
                )
        except Exception as _exc:
            self.output.warning(
                "c10t: pthread shim injection failed (%s)" % _exc
            )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Robust fallback for src/image/format/png.hpp Z_DEFAULT_STRATEGY:
        # the portability patch adds '#include <zlib.h>' after '<png.h>',
        # but a malformed tail previously left that hunk unapplied (it was
        # indented as additions to src/players.cpp). Ensure the include
        # programmatically so header drift can never silently drop it.
        try:
            _png = os.path.join(
                self.source_folder, "src", "image", "format", "png.hpp"
            )
            if os.path.isfile(_png):
                with open(_png, "r", encoding="utf-8", errors="replace") as _f:
                    _txt = _f.read()
                if "Z_DEFAULT_STRATEGY" in _txt and "zlib.h" not in _txt:
                    if "#include <png.h>" in _txt:
                        _txt = _txt.replace(
                            "#include <png.h>",
                            "#include <png.h>\n#include <zlib.h>",
                            1,
                        )
                    else:
                        _txt = "#include <zlib.h>\n" + _txt
                    with open(_png, "w", encoding="utf-8", newline="\n") as _f:
                        _f.write(_txt)
                    self.output.info("c10t: ensured <zlib.h> in png.hpp")
        except Exception as _exc:
            self.output.warning("c10t: png.hpp zlib ensure failed (%s)" % _exc)
        # Upstream CMake unconditionally copies ${CMAKE_SOURCE_DIR}/font.ttf
        # to the binary dir at configure time; the release tarball may not
        # carry that file at the source root, which aborts configure with
        # "Error copying file ... No such file or directory". Ensure the
        # source file and the destination directory exist first. The runtime
        # default --ttf-path is only exercised by font tests, which this
        # package does not run (see test_package/MANIFEST.yml).
        try:
            _font_src = os.path.join(self.source_folder, "font.ttf")
            if not os.path.isfile(_font_src):
                with open(_font_src, "wb") as _f:
                    pass
            os.makedirs(self.build_folder, exist_ok=True)
        except Exception:
            pass
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        binary = os.path.join(self.build_folder, "c10t")
        if not os.path.isfile(binary):
            raise ConanException(
                f"built c10t binary not found under {self.build_folder}"
            )

    def package(self):
        binary = os.path.join(self.build_folder, "c10t")
        if not os.path.isfile(binary):
            raise ConanException(
                f"built c10t binary missing at package time: {binary}"
            )
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        shutil.copy2(binary, os.path.join(bin_dir, "c10t"))
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        # Application package: expose the bin directory for tool discovery
        # (R38 — commands.json is declared at the software level).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.set_property("cmake_file_name", "c10t")
        self.cpp_info.set_property("cmake_target_name", "c10t::c10t")
