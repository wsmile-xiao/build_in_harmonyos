#!/usr/bin/env python3
"""Conan recipe for Filament 1.76.1 — CMake, OHOS aarch64.

Filament is a real-time physically based rendering engine.  This is the first
adaptation of Filament for this archive.

## Why the build runs in two passes

Filament's build **executes** programs it has just built to generate resources
that end up inside the target libraries:

  filament/CMakeLists.txt:417   matc  -> compiled materials (.filamat)
  filament/CMakeLists.txt:482   resgen -> embedded resource blobs
  filament/CMakeLists.txt:676   cmgen -> IBL DFG LUT
  shaders/CMakeLists.txt:82,99  glslminifier, resgen
  libs/gltfio, libs/filagui, libs/iblprefilter  matc / uberz / resgen

Upstream handles this with the ImportExecutables mechanism
(CMakeLists.txt:810-864): one pass builds the tools and writes
`ImportExecutables-Prebuilt.cmake`, a second pass includes that file and gets
the tool targets instead of rebuilding them.

  pass 1  -DFILAMENT_EXPORT_PREBUILT_EXECUTABLES_DIR=<dir>
          builds matc/cmgen/resgen/filamesh/mipgen/uberz/glslminifier and
          writes <dir>/ImportExecutables-Prebuilt.cmake
  pass 2  -DFILAMENT_IMPORT_PREBUILT_EXECUTABLES_DIR=<dir>
          builds the libraries and runs the tools from pass 1

**Both passes run on the OHOS device and both produce aarch64 binaries.**  The
build host here is aarch64 HarmonyOS, so pass 1's tools are native executables
that pass 2 can run directly.  (An earlier revision of this recipe shipped the
official x86_64 Linux tools from the GitHub release; that cannot work here — the
device is aarch64 and those binaries do not execute.)

IMPORTANT: `FILAMENT_IMPORT/EXPORT_PREBUILT_EXECUTABLES_DIR` are interpreted
relative to the Filament source directory — CMakeLists.txt:864 builds
`${FILAMENT}/${IMPORT_EXECUTABLES_DIR}/...` with `FILAMENT =
CMAKE_CURRENT_SOURCE_DIR` (:343).  Passing an absolute path produces a doubled
path such as `<src>/<abs path>` and the include fails.  The recipe therefore
always passes `os.path.relpath(...)` against `self.source_folder`.

## OHOS platform detection

CMake does not classify `CMAKE_SYSTEM_NAME=HarmonyOS` as UNIX, so Filament's
`if (UNIX AND NOT APPLE AND NOT ANDROID AND NOT WASM)` (CMakeLists.txt:197)
leaves `LINUX` FALSE and the build dies early:

  libs/bluevk/CMakeLists.txt:19  FATAL_ERROR "Platform not supported."

and the vendored glslang would fall into its "unknown platform" branch and drop
`OSDependent/Unix` (glslang/glslang/CMakeLists.txt:36, glslang/CMakeLists.txt:134).
`_apply_ohos_unix_platform()` sets `UNIX` for HarmonyOS/OHOS before that check;
the variable is inherited by every `add_subdirectory`, which is what both
Filament's own checks and the vendored subprojects read.

## Backends

`FILAMENT_SUPPORTS_VULKAN` and `FILAMENT_SUPPORTS_OPENGL` are compile-time
switches that also decide which shader families the embedded materials carry;
this recipe keeps upstream's defaults (Vulkan + OpenGL).  X11/Wayland/XCB/XLIB
are switched off — they are desktop window systems that OHOS does not have — and
`USE_STATIC_LIBCXX` is off because its default inside the LINUX branch appends
`-static` whenever the compiler is not glibc-based, which OHOS (musl) is not.
"""
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import (get, apply_conandata_patches,
                              export_conandata_patches)
from conan.tools.layout import basic_layout

#: programs that pass 1 must produce for pass 2 to consume
TOOL_TARGETS = ("matc", "cmgen", "resgen", "filamesh", "mipgen", "uberz",
                "glslminifier")

#: The target architecture as Filament names it.  Filament installs every archive
#: with `install(... DESTINATION lib/${DIST_DIR})` (~28 CMakeLists), and derives
#: DIST_DIR from DIST_ARCH, which falls back to CMAKE_HOST_SYSTEM_PROCESSOR when
#: unset (CMakeLists.txt:735-757).  On this device `uname -p` answers the literal
#: string "unknown" (`uname -m` answers aarch64), so the fallback installs
#: everything into `lib/unknown/`.  Pinning DIST_ARCH keeps the directory a real,
#: predictable name; `package_info()` declares that same directory to consumers.
#: On a normal Linux host upstream lands on `lib/<arch>/` too, so this is the
#: upstream layout with a correct architecture name.
DIST_ARCH = "aarch64"

#: where ImportExecutables-Prebuilt.cmake is written, relative to the source dir
TOOLS_EXPORT_DIR = "host-tools-prebuild"


class FilamentConan(ConanFile):
    name = "filament"
    version = "1.76.1"
    description = ("Filament is a real-time physically based rendering engine "
                   "for Android, iOS, Linux, macOS, Windows, and WebGL")
    license = "Apache-2.0"
    homepage = "https://github.com/google/filament"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # Filament creates every one of its libraries explicitly STATIC
    # (filament/CMakeLists.txt:711, libs/filabridge/CMakeLists.txt:24, ...) and
    # never consults BUILD_SHARED_LIBS, so the package is a static library.
    # Leaving a `shared` option in place would make Conan's toolchain set
    # BUILD_SHARED_LIBS=ON, which only breaks the vendored spirv-tools: Filament
    # removed its `${SPIRV_TOOLS}-shared` target but kept the alias that refers
    # to it (third_party/spirv-tools/source/CMakeLists.txt:343-359), so the
    # configure fails with
    #   add_library cannot create ALIAS target "SPIRV-Tools" because target
    #   "SPIRV-Tools-shared" does not already exist.
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def configure(self):
        # Filament requires C++20 (set as -std=c++20 in CMakeLists.txt:398,408).
        self.settings.compiler.cppstd = "20"

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"]["filament"], strip_root=True)

    # ── generate ────────────────────────────────────────────────────────────

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_BUILD_TYPE"] = "Release"
        # Treat OHOS as a mobile Linux: this clears IS_HOST_PLATFORM
        # (CMakeLists.txt:249) and selects the `mobile` MATC target (:689-693),
        # which is the right shader family for this platform.
        tc.variables["FILAMENT_LINUX_IS_MOBILE"] = "ON"
        # Pass 2 gets the tools that pass 1 built.  Relative to the source dir.
        tc.variables["FILAMENT_IMPORT_PREBUILT_EXECUTABLES_DIR"] = self._tools_export_rel()
        # Library-only package: no samples, no SDL2, no test targets.
        tc.variables["FILAMENT_SKIP_SAMPLES"] = "ON"
        tc.variables["FILAMENT_SKIP_SDL2"] = "ON"
        tc.variables["FILAMENT_BUILD_TESTING"] = "OFF"
        tc.variables["FILAMENT_SUPPORTS_VULKAN"] = "ON"
        tc.variables["FILAMENT_SUPPORTS_OPENGL"] = "ON"
        tc.variables["FILAMENT_SUPPORTS_METAL"] = "OFF"
        tc.variables["FILAMENT_SUPPORTS_WEBGPU"] = "OFF"
        tc.variables["FILAMENT_ENABLE_FGVIEWER"] = "OFF"
        tc.variables["FILAMENT_ENABLE_MATDBG"] = "OFF"
        tc.variables["FILAMENT_SUPPORTS_WEBP_TEXTURES"] = "OFF"
        # ── desktop window systems are absent on OHOS ───────────────────────
        tc.variables["FILAMENT_SUPPORTS_XCB"] = "OFF"
        tc.variables["FILAMENT_SUPPORTS_XLIB"] = "OFF"
        tc.variables["FILAMENT_SUPPORTS_WAYLAND"] = "OFF"
        tc.variables["FILAMENT_SUPPORTS_EGL_ON_LINUX"] = "OFF"
        tc.variables["FILAMENT_SUPPORTS_OSMESA"] = "OFF"
        # The LINUX branch defaults this ON; without glibc it appends `-static`
        # (CMakeLists.txt:438-449), which cannot work for shared objects here.
        tc.variables["USE_STATIC_LIBCXX"] = "OFF"
        # Filament's own targets are STATIC regardless; keep the vendored
        # subprojects on the same footing (see package_type above).
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        # Independent of BUILD_SHARED_LIBS: without this, DIST_ARCH falls back to
        # CMAKE_HOST_SYSTEM_PROCESSOR, which is the literal "unknown" here, and
        # every archive installs into lib/unknown/.  Both passes read it, so the
        # tools pass 1 exports and pass 2 imports stay under the same name.
        tc.variables["DIST_ARCH"] = DIST_ARCH
        # MATC_TARGET follows IS_MOBILE_TARGET (CMakeLists.txt:697-702), which
        # FILAMENT_LINUX_IS_MOBILE turns on (:247).  That flag is load-bearing --
        # patch 0002 keys the bluegl exclusion off IS_HOST_PLATFORM, which is set
        # exactly when FILAMENT_LINUX_IS_MOBILE is OFF -- so it has to stay ON and
        # MATC_TARGET stays `mobile`.  But every driver in this build reports
        # ShaderModel::DESKTOP at runtime (NoopDriver.cpp:50, VulkanDriver.cpp:441,
        # OpenGLContext.cpp:117, WebGPUDriver.cpp:143, MetalDriver.mm:1262), so a
        # mobile-only default material fails MaterialDefinition::create
        # (MaterialDefinition.cpp:261-270 tests the engine's model against the
        # material's bitmask) and Engine::create dies on the resulting nullptr.
        #
        # CMakeLists.txt:729 builds the matc command as
        #   set(MATC_BASE_FLAGS ${MATC_API_FLAGS} -p ${MATC_TARGET} ${MATC_OPT_FLAGS})
        # and MATC_OPT_FLAGS is only ever appended to (:721, :726), so a toolchain
        # value lands after `-p mobile`.  matc assigns on each -p rather than
        # OR-ing (CommandlineConfig.cpp:320-324), so the last one wins and this
        # makes it `Platform::ALL` -> both shader models (MaterialBuilder.cpp:125-126).
        #
        # The separator must be `;`, not a space.  MATC_BASE_FLAGS is a CMake
        # list and reaches matc through add_custom_command, so a value with a
        # space stays ONE element and is emitted quoted, giving matc the single
        # argv `-p all`, which its getopt rejects:
        #     Unrecognized platform. Must be 'desktop'|'mobile'|'all'.
        #     Invalid parameters.
        # Verified with a fake matc that prints its argv:
        #     "-p all"  -> argv[7] = [-p all]
        #     "-p;all"  -> argv[7] = [-p]  argv[8] = [all]
        tc.variables["MATC_OPT_FLAGS"] = "-p;all"
        tc.generate()

    # ── build ───────────────────────────────────────────────────────────────

    def export_sources(self):
        # Ship patches/ with the recipe so apply_conandata_patches
        # can find them at build time.
        export_conandata_patches(self)


    def _apply_ohos_libcxx_cxx23_fallbacks(self):
        """Replace C++23 library facilities the OHOS libc++ does not provide.

        VulkanReadPixels.cpp bounces an uncached mapped range through a
        default-initialised heap buffer with

          cachedCopy = std::make_unique_for_overwrite<uint8_t[]>(size);

        std::make_unique_for_overwrite is C++23; the OHOS SDK ships
        _LIBCPP_VERSION 15004 and the compiler reports (measured on the device)

          filament/backend/src/vulkan/VulkanReadPixels.cpp:400:31: error:
          no member named 'make_unique_for_overwrite' in namespace 'std'

        <memory> is already included, so this is a library-version gap, not a
        missing header.  std::unique_ptr<T[]>(new T[n]) is the exact equivalent
        make_unique_for_overwrite is specified in terms of (default
        initialisation), and the buffer is memcpy'd immediately afterwards.

        This is the only occurrence in the tree; the other C++23 spellings
        (std::print, std::move_only_function, std::byteswap, std::unreachable)
        appear only inside third-party comments.

        Idempotent: a re-run finds the replacement and does nothing.
        """
        edits = [
            (
                "filament/backend/src/vulkan/VulkanReadPixels.cpp",
                "std::make_unique_for_overwrite<uint8_t[]>(size)",
                "std::unique_ptr<uint8_t[]>(new uint8_t[size])",
            ),
        ]
        for rel, needle, replacement in edits:
            target = os.path.join(self.source_folder, rel)
            with open(target, encoding="utf-8") as fh:
                text = fh.read()
            if replacement in text:
                self.output.info(f"{rel}: C++23 fallback already applied")
                continue
            if needle not in text:
                raise ConanException(
                    f"{rel}: expected C++23 call site not found (upstream changed?)")
            with open(target, "w", encoding="utf-8") as fh:
                fh.write(text.replace(needle, replacement, 1))
            self.output.info(f"{rel}: std::make_unique_for_overwrite replaced")

    def build(self):
        apply_conandata_patches(self)
        self._apply_ohos_unix_platform()
        self._apply_ohos_ranges_fallbacks()
        # C++23 library facilities the OHOS libc++ 15.0.4 lacks.
        self._apply_ohos_libcxx_cxx23_fallbacks()
        self._build_host_tools()

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _platform_cmake(self):
        return os.path.join(self.source_folder, "CMakeLists.txt")

    def _apply_ohos_unix_platform(self):
        """Make CMake treat HarmonyOS/OHOS as a UNIX-like system.

        CMake leaves `UNIX` unset for a system name it does not know, so
        Filament's LINUX detection fails and its vendored glslang drops the
        Unix OS-dependent sources.  Setting `UNIX` here — before any
        `add_subdirectory` — is inherited by every subdirectory and is what both
        checks read.  Idempotent, so a re-run is a no-op.
        """
        path = self._platform_cmake()
        with open(path, encoding="utf-8") as fh:
            text = fh.read()

        anchor = "if (UNIX AND NOT APPLE AND NOT ANDROID AND NOT WASM)\n    set(LINUX TRUE)"
        insert = (
            "# OHOS: CMake does not know CMAKE_SYSTEM_NAME=HarmonyOS and leaves UNIX\n"
            "# unset, which makes the LINUX detection below fail (and makes the\n"
            "# vendored glslang drop its Unix OS-dependent sources).  HarmonyOS is a\n"
            "# Linux-like system: musl libc, ELF, POSIX.  Normal variables are inherited\n"
            "# by add_subdirectory, so this reaches every subproject.\n"
            "if (CMAKE_SYSTEM_NAME STREQUAL \"HarmonyOS\" OR CMAKE_SYSTEM_NAME STREQUAL \"OHOS\")\n"
            "    set(UNIX TRUE)\n"
            "endif()\n\n"
        )
        if insert in text:
            self.output.info("OHOS UNIX platform handling: already applied")
            return
        if anchor not in text:
            raise ConanException(
                "filament CMakeLists.txt: expected platform-detection anchor not found")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text.replace(anchor, insert + anchor, 1))
        self.output.info("OHOS UNIX platform handling: applied")

    def _apply_ohos_ranges_fallbacks(self):
        """Replace the C++20 `std::ranges` algorithms Filament uses.

        The OHOS SDK ships libc++ 15, which does not provide the range
        algorithms even though it provides the ranges *views*: with
        `#include <algorithm>` present, the compiler still reports

          libs/utils/src/EntityManagerImpl.h:288:30: error: no member named
          'remove_if' in namespace 'std::ranges'
          libs/utils/src/EntityManagerImpl.h:560:22: error: no member named
          'copy' in namespace 'std::ranges'

        (verified on the device with a two-line probe that includes
        <algorithm> and calls std::ranges::remove_if/copy).

        All six call sites are rewritten to the iterator-pair algorithms from
        the same header, which is what libc++ 15 does provide:

          std::ranges::remove_if(range, pred).begin()  -> std::remove_if(begin, end, pred)
          std::ranges::remove(range, value).begin()    -> std::remove(begin, end, value)
          std::ranges::copy(range, out)                -> std::copy(begin, end, out)
          std::ranges::partition(range, pred)          -> std::partition(begin, end, pred)
          std::ranges::find_if(range, pred)            -> std::find_if(begin, end, pred)

        The erase-remove idiom keeps its meaning (remove()/remove_if() return
        the new end iterator, exactly what ranges::…().begin() returned), and
        find_if()/copy()/partition() are otherwise unchanged.  Idempotent: a
        second run finds the new text and does nothing.
        """
        edits = [
            ("libs/utils/src/EntityManagerImpl.h",
             "                std::ranges::remove_if(mActiveWatermarks,\n"
             "                        [watermark](auto const& info) noexcept { return info.watermark == watermark; }).begin(),\n",
             "                std::remove_if(mActiveWatermarks.begin(), mActiveWatermarks.end(),\n"
             "                        [watermark](auto const& info) noexcept { return info.watermark == watermark; }),\n"),
            ("libs/utils/src/EntityManagerImpl.h",
             "        std::ranges::copy(listeners, result.begin());\n",
             "        std::copy(listeners.begin(), listeners.end(), result.begin());\n"),
            ("libs/utils/src/SingleInstanceComponentManager.cpp",
             "            std::ranges::remove_if(mChangeCallbacks,\n"
             "                    [token](auto const& info) { return info.token == token; }).begin(),\n",
             "            std::remove_if(mChangeCallbacks.begin(), mChangeCallbacks.end(),\n"
             "                    [token](auto const& info) { return info.token == token; }),\n"),
            ("libs/utils/src/SingleInstanceComponentManager.cpp",
             "    mBitsets.erase(std::ranges::remove(mBitsets, bitset).begin(), mBitsets.end());\n",
             "    mBitsets.erase(std::remove(mBitsets.begin(), mBitsets.end(), bitset), mBitsets.end());\n"),
            ("libs/gltfio/src/AssetLoader.cpp",
             "    std::ranges::partition(fAsset->mEntities, [&rm](Entity const a) {\n"
             "        return rm.hasComponent(a);\n"
             "    });\n",
             "    std::partition(fAsset->mEntities.begin(), fAsset->mEntities.end(), [&rm](Entity const a) {\n"
             "        return rm.hasComponent(a);\n"
             "    });\n"),
            ("filament/src/TextureCache.cpp",
             "    auto const it = std::ranges::find_if(mRecentEvictions, [&key](auto const& entry) {\n",
             "    auto const it = std::find_if(mRecentEvictions.begin(), mRecentEvictions.end(),\n"
             "            [&key](auto const& entry) {\n"),
        ]
        for rel, needle, replacement in edits:
            target = os.path.join(self.source_folder, rel)
            with open(target, encoding="utf-8") as fh:
                text = fh.read()
            if replacement in text:
                continue
            if needle not in text:
                raise ConanException(
                    f"{rel}: expected std::ranges call site not found (upstream changed?)")
            with open(target, "w", encoding="utf-8") as fh:
                fh.write(text.replace(needle, replacement, 1))
            self.output.info(f"{rel}: std::ranges call site rewritten")

    def _tools_export_dir(self):
        return os.path.join(self.build_folder, TOOLS_EXPORT_DIR)

    def _tools_export_rel(self):
        """The tools dir as CMake wants it: relative to the source directory."""
        rel = os.path.relpath(self._tools_export_dir(), self.source_folder)
        return rel.replace("\\", "/")

    def _build_host_tools(self):
        """Pass 1 — build the tools that pass 2 will execute.

        This mirrors upstream's export pass: a *host* configuration
        (FILAMENT_LINUX_IS_MOBILE off -> IS_HOST_PLATFORM on) that writes
        ImportExecutables-Prebuilt.cmake.  Only the tool targets are built; the
        libraries they link against (filamat, glslang, spirv-tools, spirv-cross,
        imageio, ibl, ...) come along as dependencies.
        """
        tools_build = os.path.join(self.build_folder, "host-tools")
        os.makedirs(tools_build, exist_ok=True)

        cmake = shutil.which("cmake") or "cmake"
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if not os.path.exists(toolchain):
            raise ConanException(f"Conan toolchain not found: {toolchain}")

        configure = [
            cmake, "-S", self.source_folder, "-B", tools_build,
            "-DCMAKE_BUILD_TYPE=Release",
            f"-DCMAKE_TOOLCHAIN_FILE={toolchain}",
            # Pass 1 is the host pass: IS_HOST_PLATFORM must be on, otherwise
            # the tool subdirectories are not added at all.
            "-DFILAMENT_LINUX_IS_MOBILE=OFF",
            # ... and it must not try to import what it is about to build.
            "-DFILAMENT_IMPORT_PREBUILT_EXECUTABLES_DIR=",
            f"-DFILAMENT_EXPORT_PREBUILT_EXECUTABLES_DIR={self._tools_export_rel()}",
        ]
        self.output.info("filament pass 1 (host tools): " + " ".join(configure))
        p = subprocess.run(configure, capture_output=True, text=True)
        if p.returncode != 0:
            raise ConanException(
                "filament pass 1 configure failed:\n" + (p.stdout or "")[-4000:]
                + (p.stderr or "")[-4000:])

        # Respect the profile's parallelism (tools.build:jobs, 1 on this farm):
        # a subprocess does not inherit the toolchain's CMAKE_BUILD_PARALLEL_LEVEL.
        jobs = self.conf.get("tools.build:jobs", default=1, check_type=int)
        build = [cmake, "--build", tools_build, "--parallel", str(jobs)]
        for target in TOOL_TARGETS:
            build += ["--target", target]
        self.output.info("filament pass 1: building " + ", ".join(TOOL_TARGETS))
        p = subprocess.run(build, capture_output=True, text=True)
        if p.returncode != 0:
            raise ConanException(
                "filament pass 1 build failed:\n" + (p.stdout or "")[-6000:]
                + (p.stderr or "")[-6000:])

        # Verify against what pass 1 actually exported: the import file records
        # each tool's absolute path (…/tools/<name>/<name>), which is the only
        # authoritative answer for where a target landed.
        import_file = os.path.join(self._tools_export_dir(),
                                   "ImportExecutables-Prebuilt.cmake")
        if not os.path.exists(import_file):
            raise ConanException(f"filament pass 1 did not write {import_file}")
        # Anchor on the IMPORTED_LOCATION_RELEASE lines.  A bare
        # '"([^"]+)"' scan is not safe here: the export file also contains
        # empty quoted strings (set(_cmake_targets_defined "")), which
        # desynchronise the quote pairing, so the tool paths are never
        # captured and every target is reported missing.  Reproduced on the
        # device with all seven binaries present on disk:
        #   old: 39 strings extracted, 0 absolute paths, all 7 missing
        #   new: exactly 7 paths, all exist, none missing
        with open(import_file, encoding="utf-8") as fh:
            exported = re.findall(r'IMPORTED_LOCATION_RELEASE\s+"([^"]+)"',
                                  fh.read())
        missing = [t for t in TOOL_TARGETS
                   if not any(os.path.basename(p) == t and os.path.exists(p)
                              for p in exported)]
        if missing:
            raise ConanException(
                f"filament pass 1 did not produce: {', '.join(missing)} "
                f"(import file: {import_file})")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # The archives land in `lib/${DIST_DIR}` (see DIST_ARCH) while consumers
        # see `cpp_info.libdir` from package_info().  Check the two agree here,
        # where the cause is visible, instead of letting a consumer's configure
        # fail with "no static archives found".
        libdir = os.path.join(self.package_folder, "lib", DIST_ARCH)
        archives = ([f for f in os.listdir(libdir) if f.endswith(".a")]
                    if os.path.isdir(libdir) else [])
        if not archives:
            raise ConanException(
                f"filament: no static archives under {libdir}; the install "
                f"destination and the libdir declared in package_info() disagree")

    def package_info(self):
        self.cpp_info.libs = ["filament"]
        # Filament installs its archives to `lib/${DIST_DIR}`, not directly under
        # `lib/`, so the default libdir of "lib" would hand consumers a -L path
        # with no archives in it.  Declare where they actually are.
        #
        # This must be the plural `libdirs` (a list, relative to the package
        # root).  `libdir` is a read-only *getter* on Conan's CppInfo -- there is
        # a @property at cpp_info.py:239 and no @libdir.setter, unlike libdirs
        # (:196), bindirs (:217) and includedirs (:177) -- so assigning to it
        # raises and package_info() dies.  Verified on Conan 2.29.1 with a
        # two-variant isolated experiment: assigning libdir -> "Error in
        # package_info() method" rc=1; assigning libdirs -> rc=0.
        self.cpp_info.libdirs = [f"lib/{DIST_ARCH}"]
        self.cpp_info.set_property("cmake_file_name", "filament")
        self.cpp_info.set_property("cmake_target_name", "filament::filament")
        if self.settings.os in ("Linux", "OHOS"):
            # Upstream links only the C++ runtime plus libm/libdl/libpthread on
            # POSIX (no -llog / -landroid: grep for them in the tree is empty).
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
