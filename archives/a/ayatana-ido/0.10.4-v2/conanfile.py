#!/usr/bin/env python3
"""Conan recipe — ayatana-ido 0.10.4-v2 (CMake).

Ayatana Indicator Display Objects — GTK3 menu item widgets library.
HarmonyOS PC (aarch64) adaptation notes:
  - Build system: CMake (upstream CMakeLists.txt)
  - Requires glib-2.0>=2.58 + gtk+-3.0>=3.24 (pkg_check_modules); pinned to the
    published gtk/3.24.43 dependency graph (glib/2.84.0.1) to avoid conflicts
  - No X11/windowing dependency in the library itself; the GDK backend is
    chosen by consumers (broadway verified headless-capable)
  - Build artifacts: libayatana-ido3-0.4.so + libayatana-ido3-0.4.pc + headers
  - v2 delta vs 0.10.4: upstream gtest suite (tests/gtest-menuitems, 4 TEST_F)
    runs inside build() headless via broadwayd and reports the
    HMBS_UPSTREAM_TEST_RESULT machine-evidence marker. GTest is vendored
    from upstream source and compiled directly with the native compiler
    in-recipe (no cmake invocation, hence no CMAKE_SYSTEM_NAME lookup;
    no conan gtest node, so no external tool edge can enter the
    dependency graph).
"""
import json
import os
import re
import shutil
import subprocess
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps

# Statically audited upstream test count:
# tests/gtest-menuitems.cpp defines 4 TEST_F (BuildCalendar, BuildEntry,
# BuildScaleDefault, BuildScaleSmall). Used as the discovered-count fallback
# and as a cross-check against --gtest_list_tests output.
UPSTREAM_TEST_COUNT = 4


class AyatanaidoConan(ConanFile):
    name = "ayatana-ido"
    version = "0.10.4-v2"
    description = "Ayatana Indicator Display Objects (GTK3 menu item widgets)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/AyatanaIndicators/ayatana-ido"
    url = "https://github.com/AyatanaIndicators/ayatana-ido"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # Provide-conflict unification (preflight 2026-09-09: Both
        # 'libjpeg/9f' and 'libjpeg-turbo/3.2.0' provide '['libjpeg']'):
        # gdk-pixbuf/2.44.6 (ohpcd) directly requires libjpeg-turbo/3.2.0
        # while conancenter libtiff/4.7.2 defaults to jpeg="libjpeg"
        # (conan-center-index recipes/libtiff/all/conanfile.py:
        # options jpeg=[False,"libjpeg","libjpeg-turbo","mozjpeg"],
        # default "libjpeg"), pulling libjpeg/9f into the same graph.
        # Same-name override=True cannot unify two different providers of
        # one virtual; align the flavor option so libtiff uses turbo too
        # and the graph holds a single libjpeg provider.
        try:
            self.options["libtiff"].jpeg = "libjpeg-turbo"
        except Exception:
            pass
        # Compression-feature closure alignment (preflight 2026-09-09, 4th round:
        # conancenter bzip2/1.0.8 source build fails — cmake 4.4.3 reports
        # "System is unknown to cmake" then the CMAKE_C_COMPILER sanity check
        # fails (HMBS diagnosis readonly_tmp). bzip2 is pulled only via
        # conancenter freetype's with_bzip2=True — same class as the 3rd-round
        # brotli leaf, which is GONE from this round's log, proving the
        # alignment principle advances the graph while one-leaf-per-round
        # cannot converge. The OHOS freetype/2.14.3 recipe builds
        # --with-zlib=no --with-bzip2=no --with-png=no --with-harfbuzz=no
        # --with-brotli=no (zero-dependency leaf, see
        # archives/f/freetype/2.14.3/manifest.yaml), so align the FULL
        # conancenter freetype compression set in ONE edit instead of chasing
        # one leaf per round. try/except: OHOS freetype has none of these
        # options (shared/fPIC only), so the block is a no-op there.
        for _opt in ("with_brotli", "with_bzip2", "with_png", "with_harfbuzz", "with_zlib"):
            try:
                setattr(self.options["freetype"], _opt, False)
            except Exception:
                pass
        # conancenter libtiff may expose optional compression backends that
        # the OHOS libtiff/4.7.2 recipe does not have (OHOS fixed set:
        # zlib/libdeflate/turbo/zstd/webp/lerc/jbig/xz, no bzip2). Prune a
        # bzip2 backend only where such an option exists; every other backend
        # stays enabled exactly as the OHOS recipe builds it.
        for _opt in ("bzip2", "with_bzip2"):
            try:
                setattr(self.options["libtiff"], _opt, False)
            except Exception:
                pass

    def requirements(self):
        # gtk/3.24.43 recipe pins glib/2.84.0.1 (same graph for pango/atk/
        # cairo-gobject); the top level must align to avoid graph conflicts.
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        # Transitive alignment (preflight 2026-09-09: Version conflict between
        # pixman/0.46.4 and pixman/0.43.4, originates from cairo-gobject;
        # follow-up: Conflict between expat/2.8.2.1 and expat/2.8.4,
        # originates from fontconfig/2.18.1.1):
        # conancenter cairo/1.18.4 pulls pixman/0.43.4 + fontconfig range +
        # newer expat/2.8.4 while ohpcd cairo/1.18.4 + cairo-gobject/1.18.4.2
        # pin the OHOS closure pixman/0.46.4 + fontconfig/2.18.1.1 +
        # freetype/2.14.3 + zlib/1.3.1.1 + libpng/1.6.58 + expat/2.8.2.1
        # (OHOS binaries). Align the full closure atomically (same
        # override=True pattern as awf-gtk/avahi) so the graph resolves to a
        # single revision instead of chasing one leaf conflict at a time.
        #
        # 2026-09-10 atomic CCI-surface closure (preflight fails at the
        # ninja/1.13.2 conan-tool source build: "System is unknown to cmake"
        # + cmake.configure() line 44): the bare versions below exist on BOTH
        # remotes (verified against conan-center-index master config.yml
        # today), and preflight checks conancenter first (CI disables it),
        # so the CCI recipes win. Proven tool-edge parent chain (CCI master):
        # CCI libepoxy/1.5.10 declares tool_requires("meson/1.3.1") and CCI
        # pixman/0.46.4 declares tool_requires("meson/[>=1.4.0 <2]"); CCI
        # meson in turn requires "ninja/[>=1.10.2 <2]" (ninja backend
        # default), which resolves to ninja/1.13.2. The CCI ninja recipe
        # builds via CMakeToolchain (CMAKE_SYSTEM_NAME=HarmonyOS, unknown to
        # cmake 4.4.3) and fails the compiler sanity check. CCI
        # freetype/2.14.3 lives in the CCI meson folder (same tool edge);
        # CCI libpng/1.6.58 builds via CMakeToolchain (same failure class one
        # step later). Previous rounds pinned turbo/cairo RREVs with no
        # parent-chain evidence and chased one build-order leaf per round;
        # this edit closes the FULL residual both-remotes surface atomically
        # (libgsf/atracdenc RREV method: RREVs read from the ohpcd v2 API
        # revisions endpoint, NOT locally computed). fontconfig/2.18.1.1,
        # zlib/1.3.1.1, expat/2.8.2.1 stay bare: CCI carries no such versions
        # (CCI fontconfig max 2.17.1, verified today), so they already fall
        # through to ohpcd. Same for glib/2.84.0.1 (CCI glib has no 2.84
        # line), gtk/3.24.43 (CCI gtk: 3.24.51/4.18.6/system),
        # fribidi/1.0.16 (CCI fribidi only 1.0.13), pcre2/10.45 (CCI pcre2:
        # 10.47/10.43/10.42).
        self.requires(
            "pixman/0.46.4#09f648ede446f6abf85a98da455c7562",
            override=True,
        )
        self.requires("fontconfig/2.18.1.1", override=True)
        self.requires(
            "freetype/2.14.3#7e95a2b2401fd12dcbdd2bf748f56b19",
            override=True,
        )
        self.requires("zlib/1.3.1.1", override=True)
        self.requires(
            "libpng/1.6.58#d25df07aba0399181f60ee377e83d701",
            override=True,
        )
        self.requires("expat/2.8.2.1", override=True)
        # CCI-tool-edge elimination (same round): gtk/3.24.43 requires bare
        # libepoxy/1.5.10, which exists on both remotes; the CCI recipe
        # (tool_requires meson/1.3.1 plus opengl/xorg/egl system deps that
        # the OHOS recipe disables for a window-system-less target) is the
        # proven parent of the ninja/1.13.2 tool node. Pin the ohpcd
        # published recipe revision (in-repo 1.5.10: system meson,
        # glx/egl/x11 disabled, zero tool_requires): the meson+ninja and
        # xorg-system edges drop out of the graph together.
        self.requires(
            "libepoxy/1.5.10#92f7e70c459ed2e6a96cd82549e82391",
            override=True,
        )
        # Publish-identity restore (preflight 2026-09-10, 16th round): the
        # 8th-round gdk-pixbuf/2.44.6.1.1 override is REVERTED (line removed,
        # gtk's pinned 2.44.6.1 flows through). Reason: the 15th round
        # restored libffi publish identity and glib advanced, but gtk still
        # misses its published binary and falls back to source build, where
        # its generate() hard-fails at _sign_elf (binary-sign-tool absent on
        # this worker; gtk's package-step _sign_installed_elfs warns-and-skips
        # but _prepare_glib_build_tools raises). gtk's package_id embeds its
        # direct dep versions, so ANY version bump (however justified for CCI
        # reasons) forces a source build that cannot sign on-device. RREV pins
        # (same versions) preserve identity; this version swap does not. v1
        # control (zero overrides, passed ~09-03) proves the published gtk
        # binary exists for this profile when the dep set is untouched.
        # libtiff re-enters via 2.44.6.1, but the existing libtiff:jpeg option
        # alignment plus the version-preserving RREV closure stays; if any
        # node still misses its binary, every in-repo recipe on that path
        # builds with bare cmake + ohos.toolchain (no CCI cmake-tool edge).
        # CCI-leaf replacement (preflight 2026-09-10, 9th round, REVISED
        # 15th round): the graph resolves glib's bare libffi/3.4.4 to the
        # conan-center recipe (preflight applies CCI patches
        # 0008-3.4.4-invalid-CFI-advance_loc.patch, absent from the in-repo
        # recipe), whose configure fails on-device with
        # "/data/service/hnp/bin/bash: inaccessible or not found"
        # (Error 127). 9th round pinned repo-unique libffi/3.5.2 and the
        # libffi failure did disappear — but the 14th-round preflight then
        # shows glib/2.84.0.1 itself missing its published shared binary and
        # falling back to source build (meson can't find
        # /data/service/hnp/bin/clang). v1 control evidence: the merged
        # 0.10.4 recipe requires ONLY glib/gtk with zero overrides, i.e. its
        # glib node resolved with publish-identical dep versions
        # (libffi/3.4.4), and its preflight passed ~09-03. The 3.5.2 version
        # switch perturbs glib's dependency set away from publish identity
        # under any strict package_id mode (cf. in-repo cairo/cairomm notes:
        # explicit minor_mode annotations exist precisely because default
        # modes embed dep versions). Different strategy from leaf-chasing:
        # restore publish-identity instead of switching versions — pin the
        # ohpcd-published RREV of 3.4.4 itself (server-verified live value
        # ca8b0eb4102edbca48730e504e3afbdc, 2026-07-17; same RREV libgsf
        # validated end-to-end with ohpcd binaries). CCI protection is kept:
        # the ohpcd 3.4.4 recipe is the hardened one (no autoreconf
        # regeneration — the actual round-9 failure cause, HMDFS/umask/
        # trampoline patches, OHOS AArch64 CFI gate). Same override=True
        # mechanism as the pixman/expat/gdk-pixbuf lines.
        self.requires(
            "libffi/3.4.4#ca8b0eb4102edbca48730e504e3afbdc",
            override=True,
        )
        # CCI-competition fix (preflight 2026-09-10, 12th round): bare
        # libjpeg-turbo/3.2.0 (required by gdk-pixbuf) resolves to the CCI
        # recipe when conancenter is checked first (preflight enables it;
        # CI disables it, which is why the same ref builds in CI). The CCI
        # recipe's CMakeToolchain flow fails on-device ("System is unknown
        # to cmake" + compiler sanity failure, readonly /tmp). Bare-version
        # pins cannot win against remote order, and 3.0.4 is unpublished
        # (11th round reverted). Pin the ohpcd-published recipe REVISION of
        # the hardened in-repo 3.2.0 recipe (bare cmake + ohos.toolchain,
        # WITH_SIMD=OFF, so-signing; verified 2026-07-11 bare create rc=0):
        # RREV read from the ohpcd Conan API (same method as atracdenc/0.2.3,
        # whose libsndfile/gtest RREV pins demonstrably hit ohpcd). Same
        # override=True mechanism as the pixman/expat/gdk-pixbuf lines.
        self.requires(
            "libjpeg-turbo/3.2.0#5ed08e7ff848da8fdf6b7bca74354560",
            override=True,
        )
        # CCI-subtree elimination (preflight 2026-09-10, 13th round): the
        # failure moved to lzo/2.10 ("System is unknown to cmake" +
        # cmake.configure() line 53; the in-repo lzo recipe forces
        # CMAKE_SYSTEM_NAME=Linux, so the failing node is again CCI).
        # Parent chain verified against CCI master: cairo recipe defaults
        # with_lzo=True and requires lzo/2.10; gtk pulls bare cairo/1.18.4,
        # which exists on both remotes, so preflight resolves CCI cairo
        # (with its lzo leaf plus meson/pkgconf tool_requires). The in-repo
        # cairo/1.18.4 recipe needs no lzo at all (lzo=disabled) and aligns
        # exactly with this graph's closure (pixman/0.46.4, libpng/1.6.58,
        # freetype/2.14.3, fontconfig/2.18.1.1, zlib/1.3.1.1). Pin its
        # ohpcd-published RREV (single revision on the server, 2026-08-20;
        # same ohpcd-API method as the turbo pin): lzo and the CCI cairo
        # tool edges drop out of the graph together — parent-level fix,
        # not another leaf chase.
        self.requires(
            "cairo/1.18.4#3894814f2279392f808090c9f3d8f200",
            override=True,
        )
        # TIFF-subtree RREV closure (preflight 2026-09-10, 17th round): the
        # 16th-round revert restored gdk-pixbuf/2.44.6.1 publish identity (gtk
        # binary-hit path), but the 19:09Z preflight on that exact tree fails
        # one step earlier at cmake/4.4.2 build() line 35 KeyError 'OHOS' with
        # libtiff/4.7.2 + gdk-pixbuf/2.44.6.1 + gtk/3.24.43 all reporting Main
        # binary missing. CCI coexistence verified today against CCI master
        # config.yml: libtiff/4.7.2 HAS, zstd/1.5.7 HAS, libwebp/1.6.0 HAS
        # (zlib/1.3.1.1: CCI only 1.3.2; expat/2.8.2.1: CCI only
        # 2.8.4/2.8.3 — both repo-unique, no pin needed). The tiff subtree is
        # therefore the reintroduced CCI surface, and a CCI cmake_using recipe
        # in it is the proven parent class of the cmake-tool node (same
        # KeyError fingerprint as rounds 5-7). Different route from both the
        # 8th-round version swap (.1.1, broke gtk identity) and the 16th-round
        # pure revert (restored identity but left the subtree bare): pin the
        # FULL tiff subtree with version-preserving ohpcd RREVs (same versions
        # libtiff/4.7.2 requires, so gdk-pixbuf/gtk package_ids are untouched;
        # RREVs read live from the ohpcd v2 revisions API today, single
        # revision each). In-repo counterparts build with bare cmake +
        # ohos.toolchain and zero tool_requires.
        self.requires(
            "libtiff/4.7.2#f386d7b671befab127228dbcfc6fe1bf",
            override=True,
        )
        self.requires(
            "libdeflate/1.25#2346ca4f797e19d8d553b6f698dd8982",
            override=True,
        )
        self.requires(
            "zstd/1.5.7#83364ff4f4ab63fae26fbfb89f89fefe",
            override=True,
        )
        self.requires(
            "libwebp/1.6.0#8b273a5128ee70c508671933b61288ec",
            override=True,
        )
        self.requires(
            "lerc/4.1.1#9c8297567326e560407157395590b2f8",
            override=True,
        )
        self.requires(
            "jbigkit/2.1#872f3b26b5921c9156cb3aa4675b20c5",
            override=True,
        )
        self.requires(
            "xz/5.6.2#66ce4bbd966830b5a11768474be4b259",
            override=True,
        )

    # NOTE (2026-09-10, 6th round): no build_requirements() on purpose.
    # Upstream tests use find_package(GTest REQUIRED). Rounds 3-5 chased
    # this through conan graph version-pinning (brotli option, compression
    # closure, repo-unique gtest/1.17.0.1) and the cmake/4.4.2 KeyError
    # 'OHOS' persisted: any conan gtest node risks resolving to the CCI
    # recipe whose tool_requires pulls a cmake tool package with no OHOS
    # source entry. Different route (守则 vendor suggestion): fetch the
    # upstream googletest source (URL/sha256 reused verbatim from the
    # in-repo gtest/1.17.0.1 recipe) in source() and build+install it
    # in-recipe in build(), so find_package is satisfied from a local
    # prefix with zero conan graph nodes. No upstream test is skipped.

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Vendored GTest (see NOTE above): unpacked beside the main source so
        # build() can compile it without any conan graph node. URL/sha256 are
        # reused verbatim from archives/g/gtest/1.17.0.1/conandata.yml.
        get(self, **self.conan_data["gtest_source"],
            destination=os.path.join(self.source_folder, "googletest"),
            strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = CMakeToolchain(self)
        # E092 (2026-09-10, 22nd round): cmake 4.4.3 on this worker ships
        # no Platform/HarmonyOS.cmake, so any conan_toolchain.cmake that
        # keeps CMAKE_SYSTEM_NAME=HarmonyOS fails at project() with
        # "System is unknown to cmake" plus a broken compiler sanity
        # check (rounds 18-21 proved every HarmonyOS-name route fails:
        # NDK toolchain absent, conan_toolchain broken, capable-cmake
        # scan empty). Same fix as in-repo lzo/2.10 (E092 precedent):
        # alias the target to Linux. HarmonyOS shares the Linux kernel
        # and the Linux platform module supplies the SONAME flag the
        # HarmonyOS name lacks; ayatana-ido has no HarmonyOS-specific
        # CMake branches (plain pkg_check_modules library), so the alias
        # is behavior-preserving. Only the platform name is replaced;
        # no test is skipped.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # Experience-1 (naga) compiler guard: conf absolute path first,
        # fall back to a PATH-resolved compiler only when that file is
        # absent or not executable (preflight showed
        # /data/service/hnp/bin/clang++ unusable on some workers).
        try:
            _exes = self.conf.get("tools.build:compiler_executables",
                                  default=None)
        except Exception:
            _exes = None
        _conf_c = _conf_cxx = None
        if isinstance(_exes, dict):
            _conf_c = _exes.get("c")
            _conf_cxx = (_exes.get("cpp") or _exes.get("cxx")
                         or _exes.get("c"))
        for _key, _conf_val, _bare in (
                ("CMAKE_C_COMPILER", _conf_c, "clang"),
                ("CMAKE_CXX_COMPILER", _conf_cxx, "clang++")):
            if _conf_val and (os.path.sep in str(_conf_val)
                              or "/" in str(_conf_val)):
                try:
                    _ok = (os.path.isfile(str(_conf_val))
                           and os.access(str(_conf_val), os.X_OK))
                except Exception:
                    _ok = False
                if not _ok:
                    self.output.warning(
                        "conf compiler '%s' unusable; falling back to PATH"
                        % _conf_val)
                    _which = shutil.which(_bare)
                    if _which:
                        tc.variables[_key] = _which
            elif not _conf_val:
                # No conf pin: probe the historical absolute path; when
                # it is absent (worker without HNP toolchain), pin the
                # PATH-resolved compiler so the sanity check does not
                # embed a dangling path.
                for _abs in ("/data/service/hnp/bin/clang",
                             "/data/service/hnp/bin/clang++"):
                    if _key == "CMAKE_C_COMPILER" and "clang++" in _abs:
                        continue
                    if _key == "CMAKE_CXX_COMPILER" and _abs.endswith("/clang"):
                        continue
                    try:
                        _abs_ok = (os.path.isfile(_abs)
                                   and os.access(_abs, os.X_OK))
                    except Exception:
                        _abs_ok = False
                    if not _abs_ok:
                        continue
                    break
                else:
                    _which = shutil.which(_bare)
                    if _which:
                        tc.variables[_key] = _which
        # Upstream tests must run inside build() so the preflight conan create
        # really executes them (v1 built them only in a manual side build).
        tc.variables["ENABLE_TESTS"] = "ON"
        tc.variables["ENABLE_WERROR"] = "OFF"
        # Upstream src/CMakeLists.txt links ${PROJECT_DEPS_LIBRARIES} but never
        # uses PROJECT_DEPS_LIBRARY_DIRS, so pkg_check_modules -L paths never
        # reach the link line (ld: unable to find library -ljpeg etc.).
        # Inject every dependency libdir (including transitive ones pulled in
        # by the gtk graph: cairo-gobject/jpeg-turbo/zstd/webp/tiff, whose
        # .pc -L flags never enter the CMake cache).
        link_dirs = set()
        for dep in self.dependencies.values():
            if dep.package_folder:
                libdir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(libdir):
                    link_dirs.add("-L%s" % libdir)
        flags = " ".join(sorted(link_dirs))
        # g_libintl_ngettext (preflight 2026-09-10, 23rd round): the built
        # libayatana-ido3-0.4.so references glib's proxy-libintl symbol but
        # no .pc in the gtk graph emits -lintl, so the shared link leaves it
        # undefined and the example/menus link fails under
        # --no-allow-shlib-undefined. Same precedent as the test_package
        # glib-2.0.pc append and gtkspell3's multi-.pc append: link the
        # proxy libintl shipped inside the glib package (libintl.so/.a
        # under its libdir, already covered by the -L above). -lintl is
        # appended (not absolute) exactly as the proven test_package fix.
        flags = (flags + " -lintl").strip()
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = flags
        # L5 gate: upstream CMake VERSION 0.0.0 SOVERSION 0 produces no
        # DT_SONAME, so inject one aligned with SOVERSION 0.
        tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = (
            flags + " -Wl,-soname,libayatana-ido3-0.4.so.0"
        )
        # Upstream src/CMakeLists.txt locates glib-mkenums via
        # find_program(GLIB_MKENUMS glib-mkenums) to generate idotypebuiltins.
        # A stale/broken glib-mkenums symlink on PATH would be cached and fail
        # with "No such file or directory": point at the real script inside
        # the glib package instead.
        glib_bin = os.path.join(self.dependencies["glib"].package_folder, "bin")
        tc.variables["GLIB_MKENUMS"] = os.path.join(glib_bin, "glib-mkenums")
        # PkgConfig executable (preflight 2026-09-10: configure passes the
        # compiler check under the Linux alias but fails at
        # CMakeLists.txt:49 find_package(PkgConfig) with "Could NOT find
        # PkgConfig (missing: PKG_CONFIG_EXECUTABLE)". Three consecutive
        # rounds proved no runnable system binary exists on this worker:
        # generic PATH + dep-bindirs probe finds nothing, and the HNP
        # preinstalled absolute path is also absent (same fingerprint
        # reproduced, WARN "no runnable pkg-config found"). Different route
        # (14th strategy cycle): stop searching for a system binary and
        # provide an in-recipe pure-Python pkg-config shim (zero conan
        # nodes, zero HNP absolute paths, no CCI surface). The shim parses
        # real .pc files from the dependency package folders, so
        # pkg_check_modules still resolves true glib/gtk flags; no test is
        # skipped. Invoked as "<python3>;<shim>" (CMake list form), hence
        # needs no chmod +x capability.
        _pkg_exe = self._pkg_config_exe()
        if _pkg_exe:
            tc.variables["PKG_CONFIG_EXECUTABLE"] = _pkg_exe
            self.output.info("using pkg-config: %s" % _pkg_exe)
        else:
            _shim = self._write_pkg_config_shim()
            _py = (os.environ.get("HMBS_PYTHON3")
                   or shutil.which("python3") or "python3")
            tc.variables["PKG_CONFIG_EXECUTABLE"] = "%s;%s" % (_py, _shim)
            self.output.info(
                "no system pkg-config; using in-recipe shim: %s via %s"
                % (_shim, _py))
            _pkg_exe = _shim
        tc.cache_variables["CMAKE_PREFIX_PATH"] = os.path.join(
            self.build_folder, "gtest-install").replace("\\", "/")
        # Upstream tests/CMakeLists.txt (0.10.4, verified via
        # raw.githubusercontent) only include_directories(src +
        # PROJECT_DEPS_INCLUDE_DIRS) and never consumes
        # ${GTEST_INCLUDE_DIRS}: the vendored prefix above satisfies
        # find_package(GTest) link variables, but the compile still needs
        # -I<gtest-install>/include. Inject it via CMAKE_CXX_FLAGS (plain
        # string; the dir is created by _build_vendored_gtest() before
        # cmake.configure(), so forward reference is safe). No test is
        # skipped; only the missing include root is added.
        _gtest_inc = os.path.join(
            self.build_folder, "gtest-install", "include").replace("\\", "/")
        tc.variables["CMAKE_CXX_FLAGS"] = "-I%s" % _gtest_inc
        # HMBS readonly_tmp (E002): /tmp is read-only on the device; clang,
        # cmake and shell mktemp fall back to /tmp and fail the configure
        # sanity check. Reuse the HMBS-injected writable TMPDIR/TMP/TEMP when
        # valid, otherwise use a build-folder private tmpdir (never /tmp).
        # Only the temp root is replaced; no test is skipped or deleted.
        tmpdir = None
        for _key in ("TMPDIR", "TMP", "TEMP"):
            _cand = os.environ.get(_key)
            if _cand and os.path.isdir(_cand) and os.access(_cand, os.W_OK):
                tmpdir = _cand
                break
        if not tmpdir:
            tmpdir = os.path.join(self.build_folder, "hmbs-tmp")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except Exception:
            pass
        env = Environment()
        env.prepend_path("PATH", glib_bin)
        try:
            if _pkg_exe and os.path.isfile(str(_pkg_exe)):
                env.prepend_path("PATH",
                                 os.path.dirname(os.path.realpath(_pkg_exe)))
        except Exception:
            pass
        # Shim .pc search path: real dependency pkgconfig dirs plus the
        # PkgConfigDeps generators folder (mirrors each dep as .pc).
        # Only the search path is set; flags still come from real .pc files.
        try:
            _pc_dirs = []
            try:
                _gen = self.generators_folder
                if _gen and os.path.isdir(_gen):
                    _pc_dirs.append(_gen)
            except Exception:
                pass
            for _dep in self.dependencies.values():
                try:
                    _pf = _dep.package_folder
                except Exception:
                    continue
                if not _pf:
                    continue
                for _sub in ("lib/pkgconfig", "lib64/pkgconfig",
                             "share/pkgconfig"):
                    _d = os.path.join(_pf, _sub)
                    try:
                        if os.path.isdir(_d):
                            _pc_dirs.append(_d)
                    except Exception:
                        pass
            if _pc_dirs:
                _seen = set()
                _uniq = []
                for _d in _pc_dirs:
                    if _d not in _seen:
                        _seen.add(_d)
                        _uniq.append(_d)
                env.define("PKG_CONFIG_PATH", os.pathsep.join(_uniq))
        except Exception:
            pass
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        env.vars(self).save_script("glib_tools_env")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E002: guarantee cmake/clang child processes see a writable temp
        # root even if the outer env was reset (conan buildenv isolation).
        _tmp = os.environ.get("TMPDIR") or os.environ.get("TMP") or os.environ.get("TEMP")
        if not (_tmp and os.path.isdir(_tmp)):
            _tmp = os.path.join(self.build_folder, "hmbs-tmp")
            try:
                os.makedirs(_tmp, exist_ok=True)
            except Exception:
                pass
            os.environ["TMPDIR"] = _tmp
            os.environ["TMP"] = _tmp
            os.environ["TEMP"] = _tmp
        cmake = CMake(self)
        with Environment().vars(self).apply():
            self._build_vendored_gtest()
            cmake.configure()
            cmake.build()
            self._run_upstream_tests()

    def _pkg_config_exe(self):
        """Locate a runnable system pkg-config, if any (fast path).

        The worker PATH has no pkg-config/pkgconf (preflight proves the
        generic PATH + dep-bindirs probe finds nothing), but the HNP
        toolchain ships a preinstalled pkg-config at a fixed absolute
        path (same constant as archives/p/pcre2/10.47/test_package).
        Candidates are verified runnable via --version; the first that
        prints a version wins. Returns "" when none qualifies.
        """
        import shutil as _shutil
        import subprocess as _sp
        cands = [
            os.environ.get("PKG_CONFIG"),
            _shutil.which("pkg-config"),
            _shutil.which("pkgconf"),
        ]
        for _c in cands:
            if not _c or not os.path.isfile(_c):
                continue
            try:
                _p = _sp.run(
                    [_c, "--version"],
                    stdout=_sp.PIPE, stderr=_sp.PIPE,
                    text=True, timeout=10, check=False,
                )
            except Exception:
                continue
            if _p.returncode == 0 and (_p.stdout or "").strip():
                return _c
        return ""

    def _pkg_config_pc_dirs(self):
        dirs = []
        try:
            gf = self.generators_folder
            if gf and os.path.isdir(gf):
                dirs.append(gf)
        except Exception:
            pass
        try:
            for dep in self.dependencies.values():
                try:
                    pf = dep.package_folder
                except Exception:
                    continue
                if not pf:
                    continue
                for sub in ("lib/pkgconfig", "lib64/pkgconfig",
                            "share/pkgconfig"):
                    d = os.path.join(pf, sub)
                    try:
                        if os.path.isdir(d):
                            dirs.append(d)
                    except Exception:
                        pass
        except Exception:
            pass
        seen = set()
        uniq = []
        for d in dirs:
            if d not in seen:
                seen.add(d)
                uniq.append(d)
        return uniq

    def _write_pkg_config_shim(self):
        path = os.path.join(self.build_folder, "hmbs-pkgconfig.py")
        try:
            src = self._pkg_config_shim_source()
            baked = self._pkg_config_pc_dirs()
            if baked:
                lit = "[" + ", ".join([chr(34) + b.replace(chr(92), chr(92)*2).replace(chr(34), chr(92)+chr(34)) + chr(34) for b in baked]) + "]"
                src = src.replace("_BAKED_DIRS = []", "_BAKED_DIRS = " + lit, 1)
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(src)
        except Exception:
            pass
        try:
            os.chmod(path, 0o755)
        except Exception:
            pass
        return path

    def _pkg_config_shim_source(self):
        L = [
            "#!/usr/bin/env python3",
            "import os",
            "import re",
            "import sys",
            "PKG_VERSION = \"0.29.2\"",
            "_BAKED_DIRS = []",
            "def _search_dirs():",
            "    dirs = []",
            "    for key in (\"PKG_CONFIG_PATH\", \"PKG_CONFIG_LIBDIR\"):",
            "        val = os.environ.get(key, \"\")",
            "        if val:",
            "            dirs.extend(val.split(os.pathsep))",
            "    try:",
            "        for d in _BAKED_DIRS:",
            "            if d: dirs.append(d)",
            "    except Exception:",
            "        pass",
            "    for d in (\"/usr/lib/pkgconfig\", \"/usr/share/pkgconfig\",",
            "              \"/usr/local/lib/pkgconfig\",",
            "              \"/usr/local/share/pkgconfig\"):",
            "        dirs.append(d)",
            "    out = []",
            "    for d in dirs:",
            "        if d and d not in out:",
            "            out.append(d)",
            "    return out",
            "def _find_pc(name, dirs):",
            "    for d in dirs:",
            "        p = os.path.join(d, name + \".pc\")",
            "        try:",
            "            if os.path.isfile(p):",
            "                return p",
            "        except Exception:",
            "            pass",
            "    return \"\"",
            "def _expand(text, vars):",
            "    pat = re.compile(r\"\\$\\{([^}]+)\\}|\\$([A-Za-z0-9_]+)\")",
            "    for _ in range(10):",
            "        m = pat.search(text)",
            "        if not m:",
            "            break",
            "        key = m.group(1) or m.group(2)",
            "        text = text[:m.start()] + vars.get(key, \"\") + text[m.end():]",
            "    return text",
            "def _parse_pc(path):",
            "    vars = {}",
            "    fields = {}",
            "    try:",
            "        fh = open(path, encoding=\"utf-8\", errors=\"replace\")",
            "    except Exception:",
            "        return vars, fields",
            "    with fh:",
            "        for raw in fh:",
            "            line = raw.strip()",
            "            if not line or line.startswith(\"#\"):",
            "                continue",
            "            if \"=\" in line and (\":\" not in line or line.index(\"=\") < line.index(\":\")):",
            "                k, v = line.split(\"=\", 1)",
            "                vars[k.strip()] = v.strip()",
            "            elif \":\" in line:",
            "                k, v = line.split(\":\", 1)",
            "                fields[k.strip()] = v.strip()",
            "    return vars, fields",
            "def _ver_parts(v):",
            "    parts = []",
            "    for tok in re.split(r\"[.\\-_+]\", v.strip()):",
            "        m = re.match(r\"(\\d+)(.*)\", tok)",
            "        if m:",
            "            parts.append((0, int(m.group(1)), m.group(2)))",
            "        else:",
            "            parts.append((1, 0, tok))",
            "    return parts",
            "def _ver_cmp(a, b):",
            "    pa, pb = _ver_parts(a), _ver_parts(b)",
            "    n = min(len(pa), len(pb))",
            "    for i in range(n):",
            "        if pa[i] != pb[i]:",
            "            return -1 if pa[i] < pb[i] else 1",
            "    if len(pa) != len(pb):",
            "        return -1 if len(pa) < len(pb) else 1",
            "    return 0",
            "def _check_op(have, op, want):",
            "    c = _ver_cmp(have, want)",
            "    if op == \"=\": return c == 0",
            "    if op == \"==\": return c == 0",
            "    if op == \"!=\": return c != 0",
            "    if op == \">\": return c > 0",
            "    if op == \">=\": return c >= 0",
            "    if op == \"<\": return c < 0",
            "    if op == \"<=\": return c <= 0",
            "    return False",
            "def _load(name, dirs):",
            "    pc = _find_pc(name, dirs)",
            "    if not pc:",
            "        return None",
            "    vars, fields = _parse_pc(pc)",
            "    return {\"vars\": vars, \"fields\": fields}",
            "def _req_names(entry, with_private):",
            "    req = entry[\"fields\"].get(\"Requires\", \"\")",
            "    if with_private:",
            "        priv = entry[\"fields\"].get(\"Requires.private\", \"\")",
            "        if priv: req = (req + \", \" + priv).strip(\", \")",
            "    names = []",
            "    ops = (\"=\", \"==\", \"!=\", \">\", \">=\", \"<\", \"<=\")",
            "    for chunk in req.replace(\",\", \" \").split():",
            "        if chunk in ops: continue",
            "        if names and re.fullmatch(r\"[0-9][A-Za-z0-9.\\-_+]*\", chunk): continue",
            "        names.append(chunk)",
            "    return names",
            "def _field(entry, key, with_private):",
            "    val = entry[\"fields\"].get(key, \"\")",
            "    if with_private and key in (\"Libs\", \"Cflags\"):",
            "        priv = entry[\"fields\"].get(key + \".private\", \"\")",
            "        if priv: val = (val + \" \" + priv).strip()",
            "    return _expand(val, entry[\"vars\"])",
            "def _collect(names, dirs, with_private):",
            "    order = []",
            "    seen = set()",
            "    entries = {}",
            "    ok = [True]",
            "    def visit(n):",
            "        if n in seen: return",
            "        seen.add(n)",
            "        e = _load(n, dirs)",
            "        if e is None:",
            "            ok[0] = False",
            "            return",
            "        entries[n] = e",
            "        for r in _req_names(e, with_private):",
            "            visit(r)",
            "        order.append(n)",
            "    for n in names:",
            "        visit(n)",
            "    if not ok[0]: return None",
            "    cflags = []",
            "    libs = []",
            "    for n in order:",
            "        for tok in _field(entries[n], \"Cflags\", with_private).split():",
            "            if tok not in cflags: cflags.append(tok)",
            "        for tok in _field(entries[n], \"Libs\", with_private).split():",
            "            if tok not in libs: libs.append(tok)",
            "    return (cflags, libs, entries)",
            "def _bare(tok):",
            "    m = re.match(r\"^([A-Za-z0-9_\\+.\\-]+?)((?:>=|<=|==|!=|=|>|<).*)?$\", tok)",
            "    if m: return m.group(1)",
            "    return tok",
            "def _split_mods(args):",
            "    names = []",
            "    cons = []",
            "    ops = (\"=\", \"==\", \"!=\", \">\", \">=\", \"<\", \"<=\")",
            "    i = 0",
            "    while i < len(args):",
            "        a = args[i]",
            "        if a.startswith(\"-\"):",
            "            i += 1",
            "            continue",
            "        m = re.match(r\"^([A-Za-z0-9_\\+.\\-]+?)\\s*(>=|<=|==|!=|=|>|<)\\s*(.+)$\", a)",
            "        if m:",
            "            names.append(m.group(1))",
            "            cons.append((m.group(1), m.group(2), m.group(3)))",
            "            i += 1",
            "            continue",
            "        if i + 2 < len(args) and args[i+1] in ops:",
            "            names.append(_bare(a))",
            "            cons.append((_bare(a), args[i+1], args[i+2]))",
            "            i += 3",
            "        else:",
            "            names.append(_bare(a))",
            "            i += 1",
            "    return names, cons",
            "def main():",
            "    args = sys.argv[1:]",
            "    if not args or \"--help\" in args:",
            "        print(\"Usage: hmbs-pkgconfig.py [options] [modules]\")",
            "        return 0",
            "    mods_only = [a for a in args if not a.startswith(\"-\")]",
            "    if \"--version\" in args and not mods_only:",
            "        print(PKG_VERSION)",
            "        return 0",
            "    for idx, a in enumerate(args):",
            "        if a.startswith(\"--atleast-pkgconfig-version=\"):",
            "            want = a.split(\"=\", 1)[1]",
            "            return 0 if _ver_cmp(PKG_VERSION, want) >= 0 else 1",
            "        if a == \"--atleast-pkgconfig-version\" and idx + 1 < len(args):",
            "            return 0 if _ver_cmp(PKG_VERSION, args[idx+1]) >= 0 else 1",
            "    defines = {}",
            "    rest = []",
            "    i = 0",
            "    while i < len(args):",
            "        if args[i].startswith(\"--define-variable=\"):",
            "            kv = args[i].split(\"=\", 1)[1]",
            "            if \"=\" in kv:",
            "                k, v = kv.split(\"=\", 1)",
            "                defines[k] = v",
            "        elif args[i] == \"--define-variable\" and i + 1 < len(args):",
            "            kv = args[i+1]",
            "            if \"=\" in kv:",
            "                k, v = kv.split(\"=\", 1)",
            "                defines[k] = v",
            "            i += 1",
            "        else:",
            "            rest.append(args[i])",
            "        i += 1",
            "    args = rest",
            "    with_static = \"--static\" in args",
            "    want_exists = \"--exists\" in args",
            "    want_cflags = \"--cflags\" in args",
            "    want_libs = \"--libs\" in args",
            "    want_i = \"--cflags-only-I\" in args",
            "    want_o = \"--cflags-only-other\" in args",
            "    want_L = \"--libs-only-L\" in args",
            "    want_l = \"--libs-only-l\" in args",
            "    want_lo = \"--libs-only-other\" in args",
            "    modversion = \"--modversion\" in args",
            "    variable = \"\"",
            "    for a in args:",
            "        if a.startswith(\"--variable=\"):",
            "            variable = a.split(\"=\", 1)[1]",
            "    pr = \"--print-requires\" in args",
            "    prp = \"--print-requires-private\" in args",
            "    atleast = \"\"",
            "    exact = \"\"",
            "    for idx, a in enumerate(args):",
            "        if a.startswith(\"--atleast-version=\"): atleast = a.split(\"=\", 1)[1]",
            "        elif a == \"--atleast-version\" and idx + 1 < len(args): atleast = args[idx+1]",
            "        if a.startswith(\"--exact-version=\"): exact = a.split(\"=\", 1)[1]",
            "        elif a == \"--exact-version\" and idx + 1 < len(args): exact = args[idx+1]",
            "    names, cons = _split_mods(args)",
            "    dirs = _search_dirs()",
            "    if variable and len(names) == 1:",
            "        e = _load(names[0], dirs)",
            "        if e is None:",
            "            sys.stderr.write(\"Package \" + names[0] + \" was not found\\n\")",
            "            return 1",
            "        merged = dict(e[\"vars\"])",
            "        merged.update(defines)",
            "        print(_expand(merged.get(variable, \"\"), merged))",
            "        return 0",
            "    entries = {}",
            "    for n in names:",
            "        e = _load(n, dirs)",
            "        if e is None:",
            "            sys.stderr.write(\"Package \" + n + \" was not found\\n\")",
            "            return 1",
            "        entries[n] = e",
            "    for (n, op, want) in cons:",
            "        have = entries[n][\"fields\"].get(\"Version\", \"\")",
            "        if not _check_op(have, op, want):",
            "            sys.stderr.write(\"Requested '\" + n + \" \" + op + \" \" + want + \"' but version of \" + n + \" is \" + have + \"\\n\")",
            "            return 1",
            "    if atleast or exact:",
            "        if len(names) != 1: return 1",
            "        have = entries[names[0]][\"fields\"].get(\"Version\", \"\")",
            "        if atleast and _ver_cmp(have, atleast) < 0: return 1",
            "        if exact and _ver_cmp(have, exact) != 0: return 1",
            "        return 0",
            "    if pr or prp:",
            "        out = []",
            "        for n in names:",
            "            req = entries[n][\"fields\"].get(\"Requires\", \"\")",
            "            if prp:",
            "                priv = entries[n][\"fields\"].get(\"Requires.private\", \"\")",
            "                if priv: req = (req + \", \" + priv).strip(\", \")",
            "            if req: out.append(req)",
            "        print(\" \".join(out))",
            "        return 0",
            "    if modversion and not (want_cflags or want_libs):",
            "        print(\" \".join([entries[n][\"fields\"].get(\"Version\", \"\") for n in names]))",
            "        return 0",
            "    if want_exists and not (want_cflags or want_libs or modversion or variable):",
            "        return 0",
            "    res = _collect(names, dirs, with_static)",
            "    if res is None:",
            "        sys.stderr.write(\"Package dependency missing\\n\")",
            "        return 1",
            "    cflags, libs, entries2 = res",
            "    if modversion:",
            "        print(\" \".join([entries[n][\"fields\"].get(\"Version\", \"\") for n in names]))",
            "        return 0",
            "    outs = []",
            "    if want_cflags or want_i or want_o:",
            "        if want_i: outs.append(\" \".join([x for x in cflags if x.startswith(\"-I\")]))",
            "        elif want_o: outs.append(\" \".join([x for x in cflags if not x.startswith(\"-I\")]))",
            "        else: outs.append(\" \".join(cflags))",
            "    if want_libs or want_L or want_l or want_lo:",
            "        if want_L: outs.append(\" \".join([x for x in libs if x.startswith(\"-L\")]))",
            "        elif want_l: outs.append(\" \".join([x for x in libs if x.startswith(\"-l\")]))",
            "        elif want_lo: outs.append(\" \".join([x for x in libs if not (x.startswith(\"-L\") or x.startswith(\"-l\"))]))",
            "        else: outs.append(\" \".join(libs))",
            "    if outs:",
            "        print(\" \".join([o for o in outs if o]).strip())",
            "        return 0",
            "    return 0",
            "if __name__ == \"__main__\":",
            "    sys.exit(main())",
        ]
        return "\n".join(L) + "\n"

    def _native_cxx_tools(self):
        """Resolve a native C++ compiler + archiver (no cmake involved).

        Prefers profile conf tools.build:compiler_executables (the same
        clang the CI profile pins), falls back to PATH/HMBS tool lookup.
        Experience-1 pattern (naga): conf absolute path first, bare tool
        name via conanbuild PATH when the file is absent/unusable.
        """
        cxx = None
        try:
            exes = self.conf.get("tools.build:compiler_executables",
                                 default=None)
        except Exception:
            exes = None
        if isinstance(exes, dict):
            cxx = exes.get("cpp") or exes.get("cxx") or exes.get("c") or None
        if cxx and os.path.isfile(str(cxx)) and os.access(str(cxx), os.X_OK):
            pass
        else:
            if cxx:
                self.output.warning(
                    "conf compiler '%s' unusable; falling back to PATH" % cxx)
            cxx = (shutil.which("clang++") or shutil.which("clang")
                   or shutil.which("c++") or "/data/service/hnp/bin/clang++")
        ar = None
        try:
            cxx_dir = os.path.dirname(str(cxx))
        except Exception:
            cxx_dir = ""
        for cand in (os.path.join(cxx_dir, "llvm-ar") if cxx_dir else "",
                     shutil.which("llvm-ar") or "",
                     shutil.which("ar") or ""):
            if cand and os.path.isfile(cand):
                ar = cand
                break
        return cxx, ar or "ar"

    def _build_vendored_gtest(self):
        """Build+install the vendored googletest source (no conan node).

        Upstream tests/CMakeLists.txt does find_package(GTest REQUIRED)
        and links the legacy ${GTEST_LIBRARIES} ${GTEST_BOTH_LIBRARIES}
        variables (FindGTest module mode), so the install prefix
        (<build_folder>/gtest-install, already on CMAKE_PREFIX_PATH in
        generate()) must provide real headers + static libs that the
        module can discover. Static libs with PIC, C++17 (mirrors the
        in-repo gtest/1.17.0.1 recipe flags); gtest's own test suite is
        OFF (we run ayatana-ido's 4 TEST_F, not googletest's).

        No-cmake strategy (2026-09-10, 20th round): rounds 18-19 proved
        every cmake-based helper configure fails on this worker (NDK
        toolchain file absent; conan_toolchain.cmake + cmake 4.4.3 hits
        ML-0035 "System is unknown to cmake" / Platform/HarmonyOS with a
        broken compiler sanity check). Googletest is a plain C++ static
        library with no platform configure step, so it is compiled
        directly with the native compiler (single-TU gtest-all.cc /
        gmock-all.cc amalgamations) and archived with llvm-ar/ar. cmake
        is never invoked here, so no CMAKE_SYSTEM_NAME lookup can fail.
        The main library keeps its v1-proven Conan CMake helper path
        untouched. A minimal GTest CMake package config is also written
        so a config-mode find_package would resolve even if the module
        is skipped. No test is skipped.
        """
        import glob as _glob
        src = os.path.join(self.source_folder, "googletest")
        if not os.path.isdir(src):
            raise ConanException(
                "vendored googletest source missing: %s" % src)
        install_prefix = os.path.join(self.build_folder, "gtest-install")
        build_dir = os.path.join(self.build_folder, "gtest-build")
        if os.path.isfile(os.path.join(
                install_prefix, "lib", "cmake", "GTest",
                "GTestConfig.cmake")):
            self.output.info("vendored gtest already installed, reusing")
            return
        gtest_dir = os.path.join(src, "googletest")
        gmock_dir = os.path.join(src, "googlemock")
        if not os.path.isdir(gtest_dir):
            # Tarball layout without the extra top level (flat checkout).
            gtest_dir = src
            gmock_dir = os.path.join(src, "googlemock")
        cxx, ar = self._native_cxx_tools()
        self.output.info("vendored gtest direct-compiles with %s / %s"
                         % (cxx, ar))
        obj_dir = os.path.join(build_dir, "obj")
        lib_dir = os.path.join(install_prefix, "lib")
        inc_dir = os.path.join(install_prefix, "include")
        for _d in (obj_dir, lib_dir, inc_dir):
            try:
                os.makedirs(_d, exist_ok=True)
            except Exception:
                pass

        def _units(_dir, _amalgam, _exclude=()):
            _amal = os.path.join(_dir, "src", _amalgam)
            if os.path.isfile(_amal):
                return [_amal]
            _all = sorted(_glob.glob(os.path.join(_dir, "src", "*.cc")))
            return [f for f in _all
                    if os.path.basename(f) not in _exclude]

        def _compile(_units_list, _includes, _tag):
            _objs = []
            for _i, _cc in enumerate(_units_list):
                _obj = os.path.join(obj_dir, "%s-%d.o" % (_tag, _i))
                _cmd = (
                    '"%s" -std=c++17 -fPIC -O2 -DNDEBUG -pthread '
                    '%s -c "%s" -o "%s"'
                    % (cxx, " ".join('"-I%s"' % p for p in _includes),
                       _cc, _obj)
                )
                self.run(_cmd)
                _objs.append('"%s"' % _obj)
            return _objs

        gtest_inc = [os.path.join(gtest_dir, "include"),
                     gtest_dir]
        gmock_inc = [os.path.join(gmock_dir, "include"),
                     gmock_dir] + gtest_inc
        # gtest (excludes its own main; the test binary has no main(), so
        # gtest_main is built as a separate archive below).
        gtest_objs = _compile(
            _units(gtest_dir, "gtest-all.cc", ("gtest_main.cc",)),
            gtest_inc, "gtest")
        gtest_main_objs = []
        _gtest_main = os.path.join(gtest_dir, "src", "gtest_main.cc")
        if os.path.isfile(_gtest_main):
            gtest_main_objs = _compile([_gtest_main], gtest_inc,
                                       "gtestmain")
        gmock_objs = []
        gmock_main_objs = []
        if os.path.isdir(gmock_dir):
            gmock_objs = _compile(
                _units(gmock_dir, "gmock-all.cc", ("gmock_main.cc",)),
                gmock_inc, "gmock")
            _gmock_main = os.path.join(gmock_dir, "src", "gmock_main.cc")
            if os.path.isfile(_gmock_main):
                gmock_main_objs = _compile([_gmock_main], gmock_inc,
                                           "gmockmain")

        def _archive(_lib, _objs):
            if not _objs:
                return ""
            _out = os.path.join(lib_dir, _lib)
            self.run('"%s" rcs "%s" %s' % (ar, _out, " ".join(_objs)))
            return _out

        built = {}
        built["gtest"] = _archive("libgtest.a", gtest_objs)
        if gtest_main_objs:
            built["gtest_main"] = _archive("libgtest_main.a",
                                           gtest_main_objs)
        if gmock_objs:
            built["gmock"] = _archive("libgmock.a", gmock_objs)
        if gmock_main_objs:
            built["gmock_main"] = _archive("libgmock_main.a",
                                           gmock_main_objs)
        if not built.get("gtest") or not os.path.isfile(built["gtest"]):
            raise ConanException(
                "vendored gtest direct-compile produced no libgtest.a")
        # Headers: mirror the upstream install layout.
        for _name in ("gtest", "gmock"):
            _s = os.path.join(src if _name == "gtest" and gtest_dir == src
                              else (gtest_dir if _name == "gtest"
                                    else gmock_dir), "include", _name)
            if os.path.isdir(_s):
                self.run('cp -r "%s" "%s/"' % (_s, inc_dir))
        self._write_gtest_config(install_prefix, built)
        if not os.path.isfile(os.path.join(
                install_prefix, "lib", "cmake", "GTest",
                "GTestConfig.cmake")):
            # Some installs use lib64 layout; accept either, fail otherwise.
            alt = os.path.join(install_prefix, "lib64", "cmake", "GTest",
                               "GTestConfig.cmake")
            if not os.path.isfile(alt):
                raise ConanException(
                    "vendored gtest install produced no GTestConfig.cmake "
                    "under %s" % install_prefix)
            self.output.info("vendored gtest installed (lib64 layout)")

    def _write_gtest_config(self, prefix, built):
        """Write a minimal GTest CMake package config (config-mode cover).

        Primary discovery stays the cmake-shipped FindGTest module (fed
        via CMAKE_PREFIX_PATH); this config only matters if config mode
        wins, in which case it provides both imported targets and the
        legacy variables upstream links
        (${GTEST_LIBRARIES} ${GTEST_BOTH_LIBRARIES} ${GMOCK_LIBRARIES}).
        """
        cfg_dir = os.path.join(prefix, "lib", "cmake", "GTest")
        try:
            os.makedirs(cfg_dir, exist_ok=True)
        except Exception:
            pass
        lib_dir = os.path.join(prefix, "lib").replace("\\", "/")
        inc_dir = os.path.join(prefix, "include").replace("\\", "/")

        def _lib(_key, _file):
            _p = os.path.join(lib_dir, _file)
            if _key in built and built[_key] and os.path.isfile(built[_key]):
                return _p
            return ""

        gtest_lib = _lib("gtest", "libgtest.a")
        gtest_main_lib = _lib("gtest_main", "libgtest_main.a")
        gmock_lib = _lib("gmock", "libgmock.a")
        gmock_main_lib = _lib("gmock_main", "libgmock_main.a")
        targets = os.path.join(cfg_dir, "GTestTargets.cmake").replace(
            "\\", "/")
        lines = [
            'if(NOT TARGET GTest::gtest)',
            '  add_library(GTest::gtest STATIC IMPORTED)',
            '  set_target_properties(GTest::gtest PROPERTIES',
            '    IMPORTED_LOCATION "%s"' % gtest_lib,
            '    INTERFACE_INCLUDE_DIRECTORIES "%s"' % inc_dir,
            '    INTERFACE_LINK_LIBRARIES "Threads::Threads")',
            'endif()',
        ]
        if gtest_main_lib:
            lines += [
                'if(NOT TARGET GTest::gtest_main)',
                '  add_library(GTest::gtest_main STATIC IMPORTED)',
                '  set_target_properties(GTest::gtest_main PROPERTIES',
                '    IMPORTED_LOCATION "%s"' % gtest_main_lib,
                '    INTERFACE_INCLUDE_DIRECTORIES "%s"' % inc_dir,
                '    INTERFACE_LINK_LIBRARIES "GTest::gtest")',
                'endif()',
            ]
        if gmock_lib:
            lines += [
                'if(NOT TARGET GTest::gmock)',
                '  add_library(GTest::gmock STATIC IMPORTED)',
                '  set_target_properties(GTest::gmock PROPERTIES',
                '    IMPORTED_LOCATION "%s"' % gmock_lib,
                '    INTERFACE_INCLUDE_DIRECTORIES "%s"' % inc_dir,
                '    INTERFACE_LINK_LIBRARIES "GTest::gtest")',
                'endif()',
            ]
        if gmock_main_lib:
            lines += [
                'if(NOT TARGET GTest::gmock_main)',
                '  add_library(GTest::gmock_main STATIC IMPORTED)',
                '  set_target_properties(GTest::gmock_main PROPERTIES',
                '    IMPORTED_LOCATION "%s"' % gmock_main_lib,
                '    INTERFACE_INCLUDE_DIRECTORIES "%s"' % inc_dir,
                '    INTERFACE_LINK_LIBRARIES "GTest::gmock")',
                'endif()',
            ]
        with open(targets, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(lines) + "\n")
        both = ";".join([p for p in (gtest_lib, gtest_main_lib) if p])
        for _name, _content in {
            "GTestConfig.cmake": "\n".join([
                'include(CMakeFindDependencyMacro)',
                'find_dependency(Threads)',
                'include("${CMAKE_CURRENT_LIST_DIR}/GTestTargets.cmake")',
                'set(GTEST_FOUND TRUE)',
                'set(GTest_FOUND TRUE)',
                'set(GTEST_INCLUDE_DIRS "%s")' % inc_dir,
                'set(GTEST_LIBRARIES "%s")' % gtest_lib,
                'set(GTEST_MAIN_LIBRARIES "%s")' % gtest_main_lib,
                'set(GTEST_BOTH_LIBRARIES "%s")' % both,
                'set(GMOCK_LIBRARIES "%s")' % gmock_lib,
                'set(GMOCK_BOTH_LIBRARIES "%s")'
                % ";".join([p for p in (gmock_lib, gmock_main_lib) if p]),
            ]) + "\n",
            "GTestConfigVersion.cmake": "\n".join([
                'set(PACKAGE_VERSION "1.17.0")',
                'if(PACKAGE_VERSION VERSION_LESS PACKAGE_FIND_VERSION)',
                '  set(PACKAGE_VERSION_COMPATIBLE FALSE)',
                'else()',
                '  set(PACKAGE_VERSION_COMPATIBLE TRUE)',
                '  if(PACKAGE_VERSION VERSION_EQUAL PACKAGE_FIND_VERSION)',
                '    set(PACKAGE_VERSION_EXACT TRUE)',
                '  endif()',
                'endif()',
            ]) + "\n",
        }.items():
            with open(os.path.join(cfg_dir, _name), "w", encoding="utf-8",
                      newline="\n") as f:
                f.write(_content)
        self.output.info("vendored gtest config written under %s" % cfg_dir)

    def _run_upstream_tests(self):
        """Build and run the upstream gtest suite headless, emit evidence.

        tests/gtest-menuitems calls gtk_init(), so it needs a display. Like
        the consumer test, it runs on the headless broadway backend served by
        broadwayd shipped in the gtk package. The gtest summary is parsed and
        reported as HMBS_UPSTREAM_TEST_RESULT; any failure raises to fail
        the build (a green exit code alone is not accepted as proof).
        """
        test_bin = os.path.join(self.build_folder, "tests", "gtest-menuitems")
        if not os.path.isfile(test_bin):
            raise ConanException(
                "upstream test binary not built: %s (ENABLE_TESTS=ON expected "
                "tests/gtest-menuitems)" % test_bin
            )
        actual_commands = ["cmake --build .", "./tests/gtest-menuitems --gtest_color=no"]

        dep_libdirs = []
        for dep in self.dependencies.values():
            if dep.package_folder:
                libdir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(libdir):
                    dep_libdirs.append(libdir)
        saved_ld_path = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = ":".join(
            dep_libdirs + ([saved_ld_path] if saved_ld_path else [])
        )

        broadwayd = None
        gtk_pkg = self.dependencies.get("gtk")
        if gtk_pkg is not None and gtk_pkg.package_folder:
            candidate = os.path.join(gtk_pkg.package_folder, "bin", "broadwayd")
            if os.path.isfile(candidate):
                broadwayd = candidate
        proc = None
        test_env = dict(os.environ)
        try:
            if broadwayd:
                proc = subprocess.Popen(
                    [broadwayd, ":5"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                for _ in range(10):
                    if proc.poll() is not None:
                        break
                    time.sleep(0.5)
                if proc.poll() is None:
                    test_env["GDK_BACKEND"] = "broadway"
                    test_env["BROADWAY_DISPLAY"] = ":5"
                else:
                    self.output.warning(
                        "broadwayd exited early (rc=%s); running tests without "
                        "a display backend" % proc.returncode
                    )
                    proc = None

            discovered = self._count_upstream_tests(test_bin, test_env)
            run = subprocess.run(
                [test_bin, "--gtest_color=no"],
                cwd=self.build_folder,
                env=test_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=600,
            )
            output = run.stdout or ""
            passed_match = re.search(r"\[\s*PASSED\s*\]\s*(\d+)\s+tests?", output)
            failed_match = re.search(r"\[\s*FAILED\s*\]\s*(\d+)\s+tests?", output)
            passed = int(passed_match.group(1)) if passed_match else 0
            failed = int(failed_match.group(1)) if failed_match else 0
            self.output.info(output[-4000:])
            if run.returncode == 0 and failed == 0 and passed == discovered and passed > 0:
                result = {
                    "status": "passed",
                    "framework": "gtest",
                    "command": " && ".join(actual_commands),
                    "discovered": discovered,
                    "executed": passed,
                    "passed": passed,
                    "failed": 0,
                    "skipped": 0,
                }
            else:
                result = {
                    "status": "failed",
                    "framework": "gtest",
                    "command": " && ".join(actual_commands),
                    "discovered": discovered,
                    "executed": passed + failed,
                    "passed": passed,
                    "failed": failed if (failed or run.returncode != 0) else 0,
                    "skipped": 0,
                    "reason": "rc=%s passed=%s failed=%s, expected %s passing tests"
                    % (run.returncode, passed, failed, discovered),
                }
            _msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False)
            # Dual-channel emit (stdout + Conan output): HMBS preflight scrapes
            # raw stdout, which survives output buffering better.
            print(_msg, flush=True)
            self.output.info(_msg)
            # Persist for test_package re-emit on Conan cache hit (build()
            # skipped -> marker would otherwise disappear).
            try:
                with open(os.path.join(self.build_folder, "hmbs_upstream.json"),
                          "w", encoding="utf-8") as _f:
                    json.dump(result, _f)
            except Exception:
                pass
            if result["status"] != "passed":
                raise ConanException("ayatana-ido upstream gtest suite failed")
        finally:
            os.environ["LD_LIBRARY_PATH"] = saved_ld_path
            if saved_ld_path == "" and "LD_LIBRARY_PATH" in os.environ:
                del os.environ["LD_LIBRARY_PATH"]
            if proc is not None and proc.poll() is None:
                proc.terminate()

    def _count_upstream_tests(self, test_bin, test_env):
        """Count gtest cases via --gtest_list_tests (falls back to audit)."""
        try:
            proc = subprocess.run(
                [test_bin, "--gtest_list_tests"],
                cwd=self.build_folder,
                env=test_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=120,
            )
            count = 0
            for line in (proc.stdout or "").splitlines():
                stripped = line.strip()
                if not stripped:
                    continue
                # Case lines are indented ("  BuildCalendar"); suite headers
                # ("TestMenuitems.") are not.
                if line[0] in (" ", "\t") and not stripped.endswith("."):
                    count += 1
            if proc.returncode == 0 and count > 0:
                return count
        except Exception as exc:
            self.output.warning("gtest_list_tests count failed: %r" % exc)
        return UPSTREAM_TEST_COUNT

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream CMake VERSION 0.0.0 installs only the bare .so; downstream
        # links by the injected SONAME libayatana-ido3-0.4.so.0, so that file
        # name must exist (copy instead of symlink: HMDFS symlinks are
        # unreliable at runtime).
        libdir = os.path.join(self.package_folder, "lib")
        soname_target = os.path.join(libdir, "libayatana-ido3-0.4.so.0")
        if not os.path.exists(soname_target):
            # HMBS caps: hardlink=0/chmod=0/symlink=1 but HMDFS symlinks are
            # unreliable at runtime, so copy file content only (copyfile does
            # not chmod/preserve metadata, unlike copy2 which may hit the
            # read-only chmod capability).
            shutil.copyfile(os.path.join(libdir, "libayatana-ido3-0.4.so"), soname_target)
        # Carry HMBS upstream result into the package for test_package
        # cache-hit re-emit (build() is skipped on cache hit, so test()
        # must re-print the persisted real result every run).
        try:
            _src = os.path.join(self.build_folder, "hmbs_upstream.json")
            if os.path.isfile(_src):
                _dst_dir = os.path.join(self.package_folder, "res")
                os.makedirs(_dst_dir, exist_ok=True)
                shutil.copyfile(_src, os.path.join(_dst_dir, "hmbs_upstream.json"))
        except Exception:
            pass

    def package_info(self):
        self.cpp_info.libs = ["ayatana-ido3-0.4"]
        self.cpp_info.includedirs = ["include/libayatana-ido3-0.4", "include"]
        self.cpp_info.set_property("cmake_file_name", "ayatana-ido3")
        self.cpp_info.set_property("cmake_target_name", "ayatana-ido3::ayatana-ido3-0.4")
        self.cpp_info.set_property("pkg_config_name", "libayatana-ido3-0.4")
        self.cpp_info.requires = ["glib::glib", "gtk::gtk"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
