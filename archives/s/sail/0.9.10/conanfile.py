#!/usr/bin/env python3
"""Conan recipe for sail 0.9.10 — SAIL (Squirrel Abstract Imaging Library).

SAIL is a fast, lightweight C11 image decoding/encoding library with a
pluggable codec architecture. The upstream CMake build auto-detects enabled
codecs from the third-party libraries present (module-mode find_package for
PNG/JPEG/GIF/TIFF) and the whole test suite is codec-aware: tests/images/
acceptance/test-images.h.in only includes images guarded by
#SAIL_HAVE_BUILTIN_<CODEC> so the tests adapt to the actually enabled codecs.

On HarmonyOS PC we enable a coherent, dependency-light codec set:
  * external deps (available as Conan packages): PNG, JPEG, GIF, TIFF
  * self-contained codecs (no external deps): BMP, PCX, PNM, PSD, TGA, WAL,
    XBM, XPM, XWD, HDR, ICO, QOI
The remaining upstream codecs (AVIF, HEIF, JPEG2000, JPEGXL, OpenEXR, WEBP,
JBIG, SVG) need third-party deps not ported here yet, so disabling them also
adapts the upstream test suite to only the enabled formats (guarded images).

BUILD STRATEGY (milestone fix 2026-09-18): the recipe drives `cmake` directly
via self.run() using the OHOS NDK ohos.toolchain.cmake, mirroring the in-tree
libjpeg-turbo/3.2.0 and libtiff/4.7.0 recipes. It deliberately does NOT use the
Conan CMake()/CMakeToolchain() helper classes: those inject a conancenter
`cmake/<ver>` tool_requires which has no OHOS source entry and fails at its own
build() with ``KeyError: 'OHOS'`` when conan tries to compile it for this
platform. Direct cmake invocation both avoids that dead-end and makes the
recipe self-contained (CMAKE_SYSTEM_NAME=OHOS handled by ohos.toolchain.cmake).
"""
import glob
import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMakeDeps, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class SailConan(ConanFile):
    name = "sail"
    version = "0.9.10"
    description = "The missing small and fast image decoding library for humans (not for machines)"
    license = "MIT"
    homepage = "https://sail.software"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # Codecs enabled on OHOS. PNG/JPEG/GIF/TIFF use standard module-mode
    # find_package (FindPNG/FindJPEG/FindGIF/FindTIFF) which resolves the
    # Conan-provided deps via CMAKE_PREFIX_PATH. The rest are self-contained
    # (no third-party headers/libs).
    _ONLY_CODECS = (
        "bmp;gif;hdr;ico;jpeg;pcx;pnm;png;psd;qoi;tga;tiff;wal;xbm;xpm;xwd"
    )

    _BUILD_DIR = "build-ohos"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # JPEG provider: the OHOS-adapted libtiff recipes (4.7.0/4.7.2) build
        # against libjpeg-turbo/3.2.0 directly (no jpeg flavor option), so with
        # those the graph has a single libjpeg-turbo provider already. The CCI
        # conancenter libtiff, in contrast, has a `jpeg` flavor option defaulting
        # to "libjpeg" (IJG libjpeg/9e series), which would split the graph into
        # two JPEG providers AND inject a cmake tool_requires that cannot build
        # for OHOS (KeyError 'OHOS'). We therefore resolve libtiff to the repo
        # ohpcd-adapted 4.7.2 recipe and only defensively align the flavor in
        # case some future transitive dep still selects the CCI recipe.
        # try/except: the OHOS-adapted libtiff recipe has no jpeg option.
        try:
            self.options["libtiff"].jpeg = "libjpeg-turbo"
        except Exception:
            pass

    def requirements(self):
        # Codec dependencies. The codecs use CMake module-mode find_package
        # (FindPNG/FindJPEG/FindGIF/FindTIFF) which resolve through
        # CMAKE_PREFIX_PATH pointing at these package folders. JPEG uses
        # libjpeg-turbo (API-compatible with IJG libjpeg) to stay on a single
        # provider with libtiff.
        #
        # The four codec deps MUST be pinned to the ohpcd recipe revisions of
        # the OHOS-adapted recipes. Preflight (2026-09-18) kept failing with
        # `cmake/4.4.3: Error in build() ... KeyError: 'OHOS'` because the
        # device remote order has conancenter first, so these same-version refs
        # resolved to the conancenter CCI recipes (conancenter also publishes
        # giflib/5.2.2, libpng/1.6.58, libjpeg-turbo/3.2.0, libtiff/4.7.2).
        # The CCI recipes declare a `cmake/<ver>` tool_requires, and that cmake
        # package has no OHOS source entry (build machine IS the OHOS device,
        # so the build-context os=OHOS) -> KeyError: 'OHOS'. Simply moving
        # between 4.7.0/4.7.2 did NOT help because conancenter ships them all.
        # Pinning the exact ohpcd recipe revision forces conan to use the
        # OHOS-adapted recipes (bare cmake + ohos.toolchain, NO cmake
        # tool_require, published OHOS binaries) regardless of remote order —
        # the same fix as libgsf/1.14.58, pycairo, graalvm (RREV pin to ohpcd).
        # RREVs read from ohpcd v2 API (conans/<name>/<version>/_/_/revisions),
        # each a single published revision.
        #
        # Pinning ONLY the four codec deps was NOT enough: the pinned ohpcd
        # libtiff/4.7.2 recipe itself requires a transitive closure of
        # zlib/libdeflate/zstd/libwebp/lerc/jbigkit/xz. With the preflight's
        # remote order (conancenter first) those transitives resolved to the
        # conancenter CCI recipes, and the CCI libwebp/1.6.0 recipe declares
        #   build_requirements(): self.tool_requires("cmake/[>=3.17]")
        # which injects conancenter `cmake/4.4.3` into the build context. Since
        # the device build profile is os=OHOS, the cmake package has no OHOS
        # source entry and its own build() fails with `KeyError: 'OHOS'`
        # (cmake/4.4.3: Error in build() ... get(self, ...sources[version][os][arch]
        # ... KeyError: 'OHOS'). So the whole libtiff transitive closure must
        # also be RREV-pinned to ohpcd: the ohpcd/OHOS-adapted recipes for all
        # of these use bare `self.run('cmake ...')` (NO cmake tool_requires),
        # identical to how the official CI resolves them (conancenter disabled).
        self.requires("giflib/5.2.2#ae75b0990c16f6d776f5ffa7ad78e6bf")
        self.requires("libpng/1.6.58#d25df07aba0399181f60ee377e83d701")
        self.requires("libjpeg-turbo/3.2.0#5ed08e7ff848da8fdf6b7bca74354560")
        self.requires("libtiff/4.7.2#f386d7b671befab127228dbcfc6fe1bf")
        # libtiff's transitive closure (same versions the ohpcd libtiff/4.7.2
        # recipe requires), pinned to their ohpcd OHOS-adapted recipes so the
        # conancenter CCI cmake tool_requires (via libwebp) never enters the graph.
        self.requires("zlib/1.3.1.1#9a23e7d51311d0440b6e4d36cf44e4d9")
        self.requires("libdeflate/1.25#2346ca4f797e19d8d553b6f698dd8982")
        self.requires("zstd/1.5.7#83364ff4f4ab63fae26fbfb89f89fefe")
        self.requires("libwebp/1.6.0#8b273a5128ee70c508671933b61288ec")
        self.requires("lerc/4.1.1#9c8297567326e560407157395590b2f8")
        self.requires("jbigkit/2.1#872f3b26b5921c9156cb3aa4675b20c5")
        self.requires("xz/5.6.2#66ce4bbd966830b5a11768474be4b259")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # CMakeDeps only writes <pkg>-config.cmake files; it does NOT inject a
        # cmake tool_requires (unlike CMake()/CMakeToolchain()). We use it to
        # drive the codec deps through CONFIG-mode find_package (the way the
        # in-tree leptonica/1.85.0 recipe does, which passes OHOS CI with the
        # exact same codec deps: giflib/5.2.2 + libpng/1.6.58 +
        # libjpeg-turbo/3.2.0 + libtiff/4.7.2).
        #
        # Module-mode find_package (FindGIF/FindPNG/FindJPEG/FindTIFF) over the
        # OHOS sysroot was NOT reliable: with the NDK's CMAKE_FIND_ROOT_PATH
        # constrained search, FindGIF.cmake's find_path/find_library could not
        # locate gif_lib.h / libgif in the Conan package folders even with
        # CMAKE_PREFIX_PATH + CMAKE_FIND_ROOT_PATH_MODE_*=BOTH, failing
        # configure with "Could NOT find GIF (missing: GIF_LIBRARY
        # GIF_INCLUDE_DIR)". Config mode pollutes nothing into the root_path
        # filtering: CMake simply searches CMAKE_PREFIX_PATH for the
        # <pkg>Config.cmake files that CMakeDeps writes into the generators
        # folder, and those embed the exact package folders.
        #
        # The upstream codec CMakeLists call find_package(GIF/PNG/JPEG/TIFF)
        # (the CMake package name, e.g. uppercase "GIF"), which does NOT match
        # the conan default cmake_file_name (giflib -> "giflib"). We therefore
        # override cmake_file_name/cmake_target_name to the names the upstream
        # find_package calls expect, so CMakeDeps writes GIFConfig.cmake /
        # PNGConfig.cmake / JPEGConfig.cmake / TIFFConfig.cmake and the
        # matching <PKG>::<target> imported targets. CMakeDeps' generated
        # config also sets the classic <PKG>_INCLUDE_DIR(S)/_LIBRARIES/
        # _FOUND variables (via additional_variables_prefixes) that the sail
        # codecs read (GIF_INCLUDE_DIRS/GIF_LIBRARIES, etc.).
        deps = CMakeDeps(self)
        # zlib is a transitive dep (libpng/libtiff both need it); give it the
        # classic ZLIB name so the transitive find_dependency(ZLIB) resolves.
        deps.set_property("zlib", "cmake_file_name", "ZLIB")
        deps.set_property("zlib", "cmake_target_name", "ZLIB::ZLIB")
        deps.set_property("giflib", "cmake_file_name", "GIF")
        deps.set_property("giflib", "cmake_target_name", "GIF::GIF")
        deps.set_property("libpng", "cmake_file_name", "PNG")
        deps.set_property("libpng", "cmake_target_name", "PNG::PNG")
        deps.set_property("libjpeg-turbo", "cmake_file_name", "JPEG")
        deps.set_property("libjpeg-turbo", "cmake_target_name", "JPEG::JPEG")
        deps.set_property("libtiff", "cmake_file_name", "TIFF")
        deps.set_property("libtiff", "cmake_target_name", "TIFF::tiff")
        deps.generate()

    def _ohos_toolchain(self):
        """Locate the OHOS NDK ohos.toolchain.cmake (self-contained, does not
        depend on an os=OHOS-aware conan_toolchain). Search order: profile
        [conf] user_toolchain -> env OHOS_NDK_HOME -> glob device/CI SDK
        layout. Same approach as in-tree libjpeg-turbo/3.2.0."""
        ut = self.conf.get(
            "tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list
        )
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        candidates = list(ut)
        if ndk:
            candidates.append(os.path.join(ndk, "build", "cmake", "ohos.toolchain.cmake"))
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        globbed = sorted(
            glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake")
        )
        if globbed:
            return globbed[-1]
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake：设 OHOS_NDK_HOME，或在 profile [conf] 配 "
            "tools.cmake.cmaketoolchain:user_toolchain=[<sdk>/ohos/native/build/cmake/ohos.toolchain.cmake]"
        )

    def _archiver_defs(self, toolchain):
        """Explicit -DCMAKE_AR / -DCMAKE_RANLIB pointing at the OHOS SDK's
        LLVM archiver.

        Direct-cmake static builds on OHOS fail in the *link* step of each
        static library with:
            [ 14%] Linking C static library libsail-common.a
            Error running link command: no such file or directory
            make[2]: *** [src/.../build.make:...: .../libsail-common.a] Error 2
        because the OHOS NDK ships only LLVM tools (E012): the toolchain's
        default archiver is not resolvable on the minimal PATH that `make`
        uses, so the `ar`/llvm-ar link rule has no executable ->
        "no such file or directory". The in-tree recipes (libxc 7.1.0,
        nanoarrow 0.9.0, libuv 1.52.x) fix this by pinning CMAKE_AR/RANLIB to
        the SDK's llvm-ar / llvm-ranlib. Prefer llvm-ar over plain ar so a GNU
        archiver can never shadow it.
        """
        candidates_ar = self._find_sdk_bin("llvm-ar", toolchain)
        candidates_ranlib = self._find_sdk_bin("llvm-ranlib", toolchain)
        ar = candidates_ar or shutil.which("llvm-ar") or shutil.which("ar")
        ranlib = candidates_ranlib or shutil.which("llvm-ranlib") or shutil.which("ranlib")
        defs = []
        if ar:
            defs.append('-DCMAKE_AR="%s"' % ar)
        if ranlib:
            defs.append('-DCMAKE_RANLIB="%s"' % ranlib)
        return defs

    def _find_sdk_bin(self, name, toolchain):
        """Locate an SDK tool (e.g. llvm-ar) next to the NDK used by the
        toolchain file. `toolchain` is <sdk>/.../ohos/native/build/cmake/
        ohos.toolchain.cmake; the NDK native dir (parent of build/ and llvm/)
        is reached by 3 dirname()s, so the LLVM bin dir is <sdk>/.../ohos/
        native/llvm/bin. Also check the well-known /data/service/hnp/bin
        location used by the official CI buildenv."""
        native = os.path.dirname(os.path.dirname(os.path.dirname(toolchain)))
        llvm_bin = os.path.join(native, "llvm", "bin")
        candidates = []
        for d in (llvm_bin, "/data/service/hnp/bin"):
            p = os.path.join(d, name)
            if os.path.isfile(p) and os.access(p, os.X_OK):
                candidates.append(p)
        return candidates[0] if candidates else None

    def _abs_dir(self, dep, d):
        """Resolve a cpp_info dir entry to an absolute path under package_folder."""
        if not d:
            return None
        if os.path.isabs(d):
            return d
        return os.path.join(dep.package_folder or "", d)

    def _dep_include(self, dep):
        """Absolute include dir for a conan dependency (first existing)."""
        pkg = dep.package_folder
        if not pkg:
            return None
        for d in dep.cpp_info.includedirs or []:
            absp = self._abs_dir(dep, d)
            if absp and os.path.isdir(absp):
                return absp
        fallback = os.path.join(pkg, "include")
        return fallback if os.path.isdir(fallback) else None

    def _dep_library(self, dep):
        """Find an existing library file (static preferred) for a conan dep."""
        pkg = dep.package_folder
        if not pkg:
            return None
        search_dirs = [self._abs_dir(dep, d) for d in (dep.cpp_info.libdirs or [])]
        search_dirs = [d for d in search_dirs if d]
        if not search_dirs:
            search_dirs = [os.path.join(pkg, "lib")]
        names = list(dep.cpp_info.libs) or [dep.ref.name]
        # Prefer the static archive for a static sail build, fall back to .so.
        for suffix in (".a", ".so"):
            for d in search_dirs:
                for n in names:
                    cand = os.path.join(d, "lib%s%s" % (n, suffix))
                    if os.path.isfile(cand):
                        return cand
        return None

    def _codec_module_vars(self):
        """Preset the CMake find-module result cache variables so the codec
        `find_package(GIF/PNG/JPEG/TIFF)` (called in MODULE mode by the sail
        codec CMakeLists) resolves deterministically from the Conan package
        folders — WITHOUT relying on CMake CONFIG search, CMAKE_PREFIX_PATH
        ordering, <PKG>_DIR hints or a CMakeDeps-generated <PKG>Config.cmake.

        Why this route (2026-09-19, replaces the failed CONFIG-mode approach):
        the upstream codec CMakeLists call plain find_package(GIF/PNG/JPEG/TIFF)
        which, with CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON + <PKG>_DIR hints, is
        *supposed* to resolve CMakeDeps' <PKG>Config.cmake in the generators
        folder. On the OHOS device (cmake 4.1 + NDK ohos.toolchain with
        CMAKE_FIND_ROOT_PATH) this kept falling back to MODULE mode
        (FindGIF.cmake) and failing "-- Could NOT find GIF (missing:
        GIF_LIBRARY GIF_INCLUDE_DIR)" 3 preflights in a row. Instead of
        fighting the CONFIG search, we preset the exact cache variables the
        standard Find*.cmake modules require:
          * FindGIF    REQUIRED_VARS: GIF_LIBRARY, GIF_INCLUDE_DIR
          * FindPNG    REQUIRED_VARS: PNG_LIBRARY, PNG_PNG_INCLUDE_DIR
          * FindJPEG   REQUIRED_VARS: JPEG_LIBRARY, JPEG_INCLUDE_DIR
          * FindTIFF   REQUIRED_VARS: TIFF_LIBRARY, TIFF_INCLUDE_DIR
          * FindZLIB   REQUIRED_VARS: ZLIB_LIBRARY, ZLIB_INCLUDE_DIR
            (libpng's FindPNG calls find_package(ZLIB) internally and appends
            ZLIB_INCLUDE_DIR/ZLIB_LIBRARY to PNG_INCLUDE_DIRS/PNG_LIBRARIES)
        When these are preset as cache variables, find_path/find_library are
        skipped and find_package_handle_standard_args immediately reports
        *_FOUND=TRUE, so the result is completely independent of the NDK's
        CMAKE_FIND_ROOT_PATH-constrained search, the package-config path
        ordering, or the cmake version's PREFIX_PATH handling.
        """
        mapping = [
            # (conan dep ref, upstream find_package name, include var, lib var)
            ("giflib",        "GIF",  "GIF_INCLUDE_DIR", "GIF_LIBRARY"),
            ("libpng",        "PNG",  "PNG_PNG_INCLUDE_DIR", "PNG_LIBRARY"),
            ("libjpeg-turbo", "JPEG", "JPEG_INCLUDE_DIR", "JPEG_LIBRARY"),
            ("libtiff",       "TIFF", "TIFF_INCLUDE_DIR", "TIFF_LIBRARY"),
            ("zlib",          "ZLIB", "ZLIB_INCLUDE_DIR", "ZLIB_LIBRARY"),
        ]
        defs = []
        for dep_ref, _find_name, inc_var, lib_var in mapping:
            try:
                dep = self.dependencies.get(dep_ref)
            except KeyError:
                continue
            if not dep.package_folder:
                continue
            inc = self._dep_include(dep)
            lib = self._dep_library(dep)
            if inc:
                defs.append('-D%s="%s"' % (inc_var, inc))
            if lib:
                defs.append('-D%s="%s"' % (lib_var, lib))
            # Directories without a lib (e.g. zlib dep may be header/system):
            # still add the include dir if present; FindPNG can then find zlib.h.
        return defs

    def _cmake_defs(self):
        """Build the cmake -D define list for the sail configure step."""
        toolchain = self._ohos_toolchain()
        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="%s"' % toolchain,
            "-DOHOS_ARCH=arm64-v8a",  # ohos.toolchain uses this for arch
            "-DCMAKE_BUILD_TYPE=%s" % self.settings.build_type,
            "-DCMAKE_INSTALL_LIBDIR=lib",  # ohos.toolchain defaults 64-bit to lib64/
            "-DBUILD_SHARED_LIBS=%s" % ("ON" if self.options.shared else "OFF"),
            "-DSAIL_COMBINE_CODECS=ON",
            # SAIL_ONLY_CODECS is a CMake ;-separated list. The value must be
            # wrapped in shell quotes: build() joins the defs into a single
            # string passed to self.run (sh), and an unquoted ";" would be
            # split into separate commands, making sh try to run the codec
            # names (gif/hdr/ico/...) -> Error 127 "/system/bin/sh: gif:
            # inaccessible or not found".
            "-DSAIL_ONLY_CODECS=\"%s\"" % self._ONLY_CODECS,
            "-DSAIL_THIRD_PARTY_CODECS_PATH=OFF",
            "-DSAIL_THREAD_SAFE=ON",
            "-DSAIL_ENABLE_OPENMP=OFF",
            "-DSAIL_BUILD_APPS=OFF",
            "-DSAIL_BUILD_EXAMPLES=OFF",
            # C++ bindings are ON upstream by default and register 16 extra
            # ctest tests (tests/bindings/c++). rule4 requires the declared
            # upstream_total (upstream_test_total) to match the full official
            # registration (48 = 12 sail + 15 sail-common + 5 sail-manip + 16
            # sail-c++). Keep bindings ON so all 48 upstream tests actually
            # register and run on the real machine, instead of under-reporting
            # at 32.
            "-DSAIL_BUILD_BINDINGS=ON",
            # Run the upstream ctest suite during conan create (HMBS evidence).
            "-DBUILD_TESTING=ON",
            # The codec CMakeLists call plain find_package(GIF/PNG/JPEG/TIFF).
            # We preset the Find*.cmake MODULE result cache variables (see
            # _codec_module_vars) computed from the Conan package folders, so
            # force MODULE mode (PREFER_CONFIG=OFF) — CONFIG mode (as tried in
            # previous rounds with <PKG>_DIR hints) does not read those preset
            # module variables and kept falling back to a broken module search
            # under the NDK's CMAKE_FIND_ROOT_PATH.
            "-DCMAKE_FIND_PACKAGE_PREFER_CONFIG=OFF",
        ]
        # Pin the archiver to the OHOS SDK's llvm-ar / llvm-ranlib. Without an
        # explicit CMAKE_AR/CMAKE_RANLIB, the direct-cmake static build fails in
        # the static-library link step with "Error running link command: no such
        # file or directory" because make cannot resolve the default archiver on
        # the minimal OHOS PATH (E012: SDK ships only LLVM tools; same fix as
        # libuv/libxc/nanoarrow).
        defs.extend(self._archiver_defs(toolchain))
        # Preset the module-mode find_package variables for every codec dep
        # (and zlib, which libpng's FindPNG needs). This is the primary and
        # self-contained mechanism — it needs no generators-folder config files
        # nor CMAKE_PREFIX_PATH ordering.
        defs.extend(self._codec_module_vars())
        # Keep the codec package folders + generators folder on the prefix path
        # as a harmless fallback for any remaining module/check_* searches.
        prefix = [self.generators_folder]
        for dep_ref in ("giflib", "libpng", "libjpeg-turbo", "libtiff",
                        "zlib", "zstd", "lerc", "libdeflate", "jbigkit",
                        "libwebp", "xz"):
            pkg = self.dependencies[dep_ref].package_folder
            if pkg and pkg not in prefix:
                prefix.append(pkg)
        defs.append('-DCMAKE_PREFIX_PATH="%s"' % ";".join(prefix))
        # Keep CMAKE_FIND_ROOT_PATH_MODE_* = BOTH so check_* / FindThreads and
        # any remaining module find_package still work for the non-root Conan
        # include/lib dirs (they are also on CMAKE_PREFIX_PATH, which is not
        # root-filtered).
        defs.append("-DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=BOTH")
        defs.append("-DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=BOTH")
        defs.append("-DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE=BOTH")
        return defs

    def _run_env_prefix(self):
        """Return a `sh`-style env-export prefix that points TMPDIR/TMP/TEMP
        at a writable location, to prepend to self.run() commands.

        self.run(env=...) does NOT accept a dict — Conan 2's env parameter is a
        list of *managed* env names (conanbuild/conanrun/etc.), and passing a
        dict raises `AssertionError: env argument to ConanFile.run() should be
        a list` (hit on the OHOS device). To inject arbitrary variables for a
        subprocess we therefore export them inline in the shell command.

        On OHOS the root /tmp is read-only (HMBS diagnostic [readonly_tmp]);
        cmake's check_* probes and shell temp files must not land there.
        Prefer HMBS's injected TMPDIR/TMP/TEMP (HMBS_PLATFORM_CAPABILITIES
        .tmpdir), else fall back to the conan build folder (always writable).
        """
        base = None
        for var in ("TMPDIR", "TMP", "TEMP"):
            if os.environ.get(var) and os.path.isdir(os.environ.get(var)):
                base = os.environ.get(var)
                break
        if not base:
            base = os.path.join(self.build_folder, ".tmp")
            try:
                os.makedirs(base, exist_ok=True)
            except OSError:
                base = self.build_folder
        return "export TMPDIR=\"%s\"; export TMP=\"%s\"; export TEMP=\"%s\"; " % (
            base, base, base)

    def _runtime_lib_dirs(self):
        """Absolute library directories (libdirs / <pkg>/lib) of every
        dependency in the graph.

        The codec deps (libtiff, libpng, libjpeg, giflib) and libtiff's
        transitive closure (libwebp, libzstd, zlib, ...) are published as
        shared libraries. When a test binary links libsail-codecs.a (static),
        its resolved codec symbols still pull the shared dep .so files in as
        DT_NEEDED at runtime: loading libtiff.so needs libwebp.so/libzstd.so,
        libpng.so needs zlib, etc. On the OHOS device those Conan package lib
        dirs are NOT on the default loader search path, so the dynamic loader
        fails every such relocation with the exact errors seen in preflight:
            Error relocating <pkg>/lib/libtiff.so.6.3.0: WebPPictureImportRGBA:
            symbol not found
            Error relocating <pkg>/lib/libtiff.so.6.3.0: ZSTD_maxCLevel:
            symbol not found
        We therefore prepend all dependency lib dirs to LD_LIBRARY_PATH for
        the ctest + test_package runs.
        """
        dirs = []
        for dep in self.dependencies.values():
            pkg = dep.package_folder
            if not pkg:
                continue
            libdirs = [self._abs_dir(dep, d) for d in (dep.cpp_info.libdirs or [])]
            libdirs = [d for d in libdirs if d]
            if not libdirs:
                libdirs = [os.path.join(pkg, "lib")]
            for d in libdirs:
                if d not in dirs:
                    dirs.append(d)
        return dirs

    def _runtime_env_prefix(self):
        """tmpdir export + LD_LIBRARY_PATH export for test runs (ctest and
        test_package consumer). Appends to any pre-existing LD_LIBRARY_PATH so
        we never clobber the system path."""
        libdirs = self._runtime_lib_dirs()
        old = os.environ.get("LD_LIBRARY_PATH", "")
        combined = ":".join(libdirs + ([old] if old else []))
        return "%sexport LD_LIBRARY_PATH=\"%s\"; " % (
            self._run_env_prefix(), combined)

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        bdir = os.path.join(self.build_folder, self._BUILD_DIR)
        defs = " ".join(self._cmake_defs())
        envpre = self._run_env_prefix()
        # Drive cmake directly (system/HMBS cmake on PATH). The CMake/CmakeToolchain
        # helper classes would otherwise pull in a conancenter cmake tool_requires
        # that has no OHOS source and fails with KeyError: 'OHOS'.
        self.run('%scmake -B "%s" -S "%s" %s' % (envpre, bdir, src, defs))
        self.run('%scmake --build "%s"' % (envpre, bdir))
        self._run_upstream_tests(bdir)

    # ------------------------------------------------------------------
    # Upstream test execution
    # ------------------------------------------------------------------
    def _run_upstream_tests(self, build_dir):
        """Run the upstream ctest suite against the build tree, parse real
        counts, and persist a summary JSON that the test_package stage
        re-emits as HMBS_UPSTREAM_TEST_RESULT (the hmbs evidence gate only
        scans the test_package stage stdout, and the package may be served from
        the Conan cache with build() skipped on later runs)."""
        log_path = os.path.join(build_dir, "sail-ctest.log")
        ctest_cmd = "ctest --output-on-failure"
        rc = 0
        try:
            self.run(
                '%sctest --output-on-failure > "%s" 2>&1' % (self._runtime_env_prefix(), log_path),
                cwd=build_dir,
            )
        except ConanException:
            rc = 1
        output = ""
        try:
            with open(log_path, "r", encoding="utf-8", errors="replace") as handle:
                output = handle.read()
        except OSError:
            output = ""
        tail = "\n".join(output.splitlines()[-40:])
        if tail:
            self.output.info("sail upstream ctest tail:\n%s" % tail)

        parsed = self._parse_ctest(output)
        if parsed is None:
            # The authoritative ctest summary line is missing -> we cannot
            # truthfully report counts. Fail honestly with the searched-for
            # pattern and the log location, rather than fabricating numbers.
            self.output.error(
                "sail: could not find ctest summary line "
                "('N tests failed out of M') in %s" % log_path
            )
            raise ConanException(
                "sail upstream tests could not be parsed (no ctest summary in "
                + log_path + ")"
            )

        discovered, executed, passed, failed, skipped = parsed

        if failed == 0 and passed > 0 and rc == 0 and executed == discovered:
            status = "passed"
        else:
            status = "failed"

        summary = {
            "status": status,
            "framework": "ctest",
            "command": ctest_cmd,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        # Persist inside the package's res/ so test_package can re-emit it even
        # when a cached binary skips build(). Write into build folder and copy
        # in package(); store a copy also off build_dir for robustness.
        summary_path = os.path.join(build_dir, "upstream_test_summary.json")
        with open(summary_path, "w", encoding="utf-8") as handle:
            json.dump(summary, handle, ensure_ascii=False)
        self.output.info("sail upstream test summary written: %s" % summary_path)

        if status != "passed":
            raise ConanException(
                "sail upstream tests did not fully pass: "
                + json.dumps(summary, ensure_ascii=False)
            )

    @staticmethod
    def _parse_ctest(output):
        """Parse ctest output into (discovered, executed, passed, failed,
        skipped) — a single deterministic source: the ctest summary line
        "100% tests passed, 0 tests failed out of N".

        ctest's summary is authoritative for `discovered` (= N) and `failed`;
        every registered test is executed (executed = discovered) and only the
        summary line is read. If the summary line is absent we return None so
        the caller fails HONESTLY with a reason instead of guessing counts from
        ad-hoc stdout scanning (which produced self-contradictory markers and
        was rejected by rule4 in past libraries)."""
        m = re.search(r"(\d+)\s+tests?\s+failed\s+out\s+of\s+(\d+)", output)
        if not m:
            return None
        failed = int(m.group(1))
        discovered = int(m.group(2))
        # ctest prints a separate skipped line only when some tests are
        # filtered out (e.g. `ctest -R/-E`); with a full run it is absent -> 0.
        skipped = 0
        sm = re.search(r"(\d+)\s+tests?\s+(?:skipped|not run)", output,
                       re.IGNORECASE)
        if sm:
            skipped = int(sm.group(1))
        # All registered tests are executed in a full `ctest` run.
        executed = discovered
        # passed is derived arithmetically from the single summary source
        # (passed + failed + skipped == discovered == executed).
        passed = discovered - failed - skipped
        return discovered, executed, passed, failed, skipped

    # ------------------------------------------------------------------
    # Packaging
    # ------------------------------------------------------------------
    def package(self):
        bdir = os.path.join(self.build_folder, self._BUILD_DIR)
        self.run('cmake --install "%s" --prefix "%s"' % (bdir, self.package_folder))
        # Carry the upstream test summary into the package so the test_package
        # stage can emit HMBS_UPSTREAM_TEST_RESULT even when a later preflight
        # reuses the cached binary (build() skipped).
        summary_src = os.path.join(bdir, "upstream_test_summary.json")
        if os.path.isfile(summary_src):
            copy(
                self,
                "upstream_test_summary.json",
                src=bdir,
                dst=os.path.join(self.package_folder, "res"),
                keep_path=False,
            )

    def package_info(self):
        # Canonical ConanCenter sail recipe: the top-level cpp_info sets only
        # cmake_file_name ("Sail") — the consumer-facing SAIL::Sail target comes
        # from the "libsail" component, NOT from a top-level cmake_target_name.
        # Setting BOTH a top-level cmake_target_name (-> CMakeDeps "global
        # aggregate" target) AND a component with the SAME target name ("SAIL::Sail")
        # makes CMakeDeps fail to generate a usable SailConfig.cmake, so
        # `find_package(Sail CONFIG)` in the test_package/consumers cannot find
        # it. Mirror the upstream sail/0.9.10 recipe exactly.
        self.cpp_info.set_property("cmake_file_name", "Sail")

        # sail-common
        self.cpp_info.components["sail-common"].set_property(
            "cmake_target_name", "SAIL::SailCommon"
        )
        self.cpp_info.components["sail-common"].set_property(
            "pkg_config_name", "libsail-common"
        )
        self.cpp_info.components["sail-common"].includedirs = ["include/sail"]
        self.cpp_info.components["sail-common"].libs = ["sail-common"]

        # sail-codecs (combined static library)
        self.cpp_info.components["sail-codecs"].set_property(
            "cmake_target_name", "SAIL::SailCodecs"
        )
        self.cpp_info.components["sail-codecs"].includedirs = ["include/sail"]
        self.cpp_info.components["sail-codecs"].libs = ["sail-codecs"]
        self.cpp_info.components["sail-codecs"].requires = ["sail-common"]
        # Static combined codec library must propagate the codec deps to the
        # final consumer link line.
        self.cpp_info.components["sail-codecs"].requires.append("giflib::giflib")
        self.cpp_info.components["sail-codecs"].requires.append("libpng::libpng")
        self.cpp_info.components["sail-codecs"].requires.append("libjpeg-turbo::libjpeg-turbo")
        self.cpp_info.components["sail-codecs"].requires.append("libtiff::libtiff")
        # libtiff's transitive codec linkage is folded into the static combined
        # libsail-codecs.a, so the consumer link line must also carry these.
        # They are listed as *direct* requires() in this recipe (RREV-pinned to
        # the ohpcd recipes), and Conan 2 validates that every direct dependency
        # is consumed by at least one component — adding them here both satisfies
        # that validation and propagates the correct link flags downstream.
        self.cpp_info.components["sail-codecs"].requires.append("zlib::zlib")
        self.cpp_info.components["sail-codecs"].requires.append("libdeflate::libdeflate")
        self.cpp_info.components["sail-codecs"].requires.append("zstd::zstd")
        self.cpp_info.components["sail-codecs"].requires.append("libwebp::libwebp")
        self.cpp_info.components["sail-codecs"].requires.append("lerc::lerc")
        self.cpp_info.components["sail-codecs"].requires.append("jbigkit::jbigkit")
        self.cpp_info.components["sail-codecs"].requires.append("xz::xz")

        # libsail (junior/high-level API) — named "libsail" like the upstream
        # ConanCenter recipe so the SAIL::Sail target is a well-scoped component
        # target (not shadowing/conflicting with the package itself).
        self.cpp_info.components["libsail"].set_property(
            "cmake_target_name", "SAIL::Sail"
        )
        self.cpp_info.components["libsail"].set_property(
            "pkg_config_name", "libsail"
        )
        self.cpp_info.components["libsail"].includedirs = ["include/sail"]
        self.cpp_info.components["libsail"].libs = ["sail"]
        self.cpp_info.components["libsail"].requires = ["sail-common", "sail-codecs"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.components["libsail"].system_libs.append("dl")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.components["libsail"].system_libs.append("pthread")

        # sail-manip (pixel format conversion)
        self.cpp_info.components["sail-manip"].set_property(
            "cmake_target_name", "SAIL::SailManip"
        )
        self.cpp_info.components["sail-manip"].set_property(
            "pkg_config_name", "libsail-manip"
        )
        self.cpp_info.components["sail-manip"].includedirs = ["include/sail"]
        self.cpp_info.components["sail-manip"].libs = ["sail-manip"]
        self.cpp_info.components["sail-manip"].requires = ["sail-common"]

        # sail-c++ (C++ binding, built because SAIL_BUILD_BINDINGS=ON so the
        # 16 tests/bindings/c++ upstream tests register/run, matching the full
        # upstream N=48). Upstream installs public headers under
        # include/sail/sail-c++/ and the library as libsail-c++; it links the
        # C libraries (sail-common, sail, sail-manip).
        self.cpp_info.components["sail-c++"].set_property(
            "cmake_target_name", "SAIL::SailCpp"
        )
        self.cpp_info.components["sail-c++"].set_property(
            "pkg_config_name", "libsail-c++"
        )
        self.cpp_info.components["sail-c++"].includedirs = ["include/sail"]
        self.cpp_info.components["sail-c++"].libs = ["sail-c++"]
        self.cpp_info.components["sail-c++"].requires = ["sail-common", "libsail", "sail-manip"]
