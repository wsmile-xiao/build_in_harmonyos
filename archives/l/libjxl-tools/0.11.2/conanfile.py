#!/usr/bin/env python3
"""Conan recipe — libjxl-tools 0.11.2 (JPEG XL command-line tools: cjxl / djxl / jxlinfo).

HarmonyOS PC (OHOS / aarch64) adaptation:
  * Native build with the OHOS clang (target aarch64-unknown-linux-ohos); the
    libjxl CMake sees the platform as "Linux" (proven pattern used by the
    published highway/libwebp recipes) so its pkg-config based Find* modules
    behave normally.
  * Tools are linked against static in-tree libjxl (BUILD_SHARED_LIBS=OFF;
    JPEGXL_STATIC stays OFF because it would force `-static` for the whole
    executable, incompatible with the shared brotli package).  The shared
    runtime deps (brotli, libpng16 and its zlib) are copied next to the
    binaries and `$ORIGIN/../lib` is baked as RPATH — makes the package
    self-contained and runnable with a completely empty environment
    (`env -i <pkg>/bin/cjxl --version`), not just under LD_LIBRARY_PATH.
  * libjxl release tarballs do not ship git submodules; the built-in colour
    management library skcms (pinned to the upstream-libjxl commit) is fetched
    into third_party/skcms so JPEGXL_ENABLE_SKCMS can stay ON (avoids the
    lcms2 dependency, which is not published to ohpcd).
  * PNG support is a REQUIRED dependency, not optional: libjxl's extras codec
    always runs find_package(PNG) (JPEGXL_BUNDLE_LIBPNG=OFF) and compiles the
    APNG codec in, so cjxl/djxl link libpng16.so.16.  We therefore declare
    libpng/1.6.58 (which pulls zlib/1.3.1.1) AND pin CMake's FindPNG/FindZLIB
    to the Conan packages — the earlier recipe was silently leaking the host
    /storage/Users/currentUser/usr/local libpng/libz, so the tools only ran
    with the host LD_LIBRARY_PATH.  The remaining optional codecs
    (JPEG/GIF/WebP/OpenEXR) and jpegli stay disabled.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)


class LibjxlToolsConan(ConanFile):
    name = "libjxl-tools"
    version = "0.11.2"
    description = "JPEG XL reference encoder/decoder command-line tools (cjxl, djxl, jxlinfo)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/libjxl/libjxl"
    url = "https://github.com/libjxl/libjxl"
    topics = ("image", "jpeg-xl", "jxl", "jpeg", "tool")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("brotli/1.2.0")
        self.requires("highway/1.3.0.2")
        # libjxl's extras PNG codec is unconditional (see module docstring).
        self.requires("libpng/1.6.58")
        # libpng/1.6.58 already pulls zlib/1.3.1.1 transitively; it is declared
        # here as well (same version -> same graph node) only so generate() can
        # reach its package_folder and pin CMake's FindZLIB at the Conan zlib
        # instead of the host one.  The package folder of a purely transitive
        # dependency is not populated for the consumer recipe in Conan 2.
        self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        src = self.conan_data["sources"][self.version]
        get(self, url=src["url"], sha256=src["sha256"], strip_root=True)
        # libjxl tarballs do not bundle git submodules. skcms is the built-in
        # colour-management engine (JPEGXL_ENABLE_SKCMS=ON), pinned to the
        # revision the upstream 0.11.2 build tree expects.
        get(self, url=src["skcms_url"], sha256=src["skcms_sha256"],
            destination="third_party/skcms", strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)

        # ── Disable everything not needed for the CLI tools ────────────────
        tc.variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        # JPEGXL_STATIC=ON appends -static to EXE_LINKER_FLAGS, which forces ALL
        # transitive libs (incl. shared brotli) static and lld rejects the .so.
        # Keep the in-tree libjxl static (BUILD_SHARED_LIBS=OFF) and let brotli
        # stay dynamic; the $ORIGIN/../lib RPATH handles runtime resolution.
        tc.variables["JPEGXL_STATIC"] = "OFF"
        tc.variables["JPEGXL_BUNDLE_LIBPNG"] = "OFF"
        tc.variables["JPEGXL_ENABLE_BENCHMARK"] = "OFF"
        tc.variables["JPEGXL_ENABLE_DOXYGEN"] = "OFF"
        tc.variables["JPEGXL_ENABLE_EXAMPLES"] = "OFF"
        tc.variables["JPEGXL_ENABLE_FUZZERS"] = "OFF"
        tc.variables["JPEGXL_ENABLE_JNI"] = "OFF"
        tc.variables["JPEGXL_ENABLE_MANPAGES"] = "OFF"
        tc.variables["JPEGXL_ENABLE_OPENEXR"] = "OFF"
        tc.variables["JPEGXL_ENABLE_PLUGINS"] = "OFF"
        tc.variables["JPEGXL_ENABLE_SJPEG"] = "OFF"
        tc.variables["JPEGXL_ENABLE_SKCMS"] = "ON"
        tc.variables["JPEGXL_ENABLE_TCMALLOC"] = "OFF"
        tc.variables["JPEGXL_ENABLE_TOOLS"] = "ON"
        tc.variables["JPEGXL_ENABLE_DEVTOOLS"] = "OFF"
        tc.variables["JPEGXL_ENABLE_VIEWERS"] = "OFF"
        tc.variables["JPEGXL_ENABLE_JPEGLI"] = "OFF"
        tc.variables["JPEGXL_FORCE_SYSTEM_BROTLI"] = "ON"
        tc.variables["JPEGXL_FORCE_SYSTEM_GTEST"] = "ON"
        tc.variables["JPEGXL_FORCE_SYSTEM_HWY"] = "ON"
        tc.variables["JPEGXL_WARNINGS_AS_ERRORS"] = "OFF"
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0077"] = "NEW"

        # ── OHOS / HarmonyOS PC (aarch64) ──────────────────────────────────
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            # Skip the executable link step during CMake feature/try-compile
            # probes (CI worker lld env is sparse); real builds link normally.
            tc.cache_variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"

        # ── RPATH: keep the shipped shared runtime libs loadable from lib/ ──
        tc.variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN/../lib"
        tc.variables["CMAKE_BUILD_RPATH"] = "$ORIGIN/../lib"

        # ── Wire Conan deps into libjxl's pkg-config based Find modules ────
        # libjxl ships cmake/FindBrotli.cmake / FindHWY.cmake which use
        # pkg_check_modules + find_library/find_path.  Feeding the Conan
        # package paths as cache variables makes find_package(Brotli/HWY)
        # succeed regardless of pkg-config .pc availability.
        if "brotli" in self.dependencies:
            bp = self.dependencies["brotli"].package_folder
            tc.cache_variables["BROTLI_INCLUDE_DIR"] = os.path.join(bp, "include").replace("\\", "/")
            tc.cache_variables["BROTLICOMMON_LIBRARY"] = self._lib_path(bp, "brotlicommon")
            tc.cache_variables["BROTLIENC_LIBRARY"] = self._lib_path(bp, "brotlienc")
            tc.cache_variables["BROTLIDEC_LIBRARY"] = self._lib_path(bp, "brotlidec")
        if "highway" in self.dependencies:
            hp = self.dependencies["highway"].package_folder
            tc.cache_variables["HWY_INCLUDE_DIR"] = os.path.join(hp, "include").replace("\\", "/")
            tc.cache_variables["HWY_LIBRARY"] = self._lib_path(hp, "hwy")
        # ── Pin CMake's FindPNG / FindZLIB to the Conan packages ────────────
        # libjxl's extras core codec unconditionally does find_package(PNG) when
        # JPEGXL_BUNDLE_LIBPNG=OFF; the stock CMake module FindPNG first runs
        # find_package(ZLIB) and then reads the cache variables
        # PNG_PNG_INCLUDE_DIR + PNG_LIBRARY (see Modules/FindPNG.cmake).  Without
        # pinning these, both PNG and ZLIB are found in the *host*
        # /storage/Users/currentUser/usr/local prefix, so cjxl/djxl end up with
        # DT_NEEDED libpng16.so.16/libz.so that no Conan package ships and the
        # tools only run with the host LD_LIBRARY_PATH set.  Feed the Conan
        # libpng (+ transitive zlib) package paths instead.
        if "libpng" in self.dependencies:
            pp = self.dependencies["libpng"].package_folder
            tc.cache_variables["PNG_PNG_INCLUDE_DIR"] = os.path.join(pp, "include").replace("\\", "/")
            tc.cache_variables["PNG_LIBRARY"] = self._lib_path(pp, "png16")
        if "zlib" in self.dependencies:
            zp = self.dependencies["zlib"].package_folder
            tc.cache_variables["ZLIB_INCLUDE_DIR"] = os.path.join(zp, "include").replace("\\", "/")
            tc.cache_variables["ZLIB_LIBRARY"] = self._lib_path(zp, "z")

        tc.generate()

    @staticmethod
    def _lib_path(pkg_folder: str, name: str) -> str:
        """Absolute path of lib{name}.so / lib{name}.a inside a Conan package."""
        libdir = os.path.join(pkg_folder, "lib")
        for ext in (".so", ".a"):
            cand = os.path.join(libdir, "lib" + name + ext)
            if os.path.isfile(cand):
                return cand.replace("\\", "/")
        return os.path.join(libdir, "lib" + name).replace("\\", "/")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        # Ship the shared runtime deps next to the tools ($ORIGIN/../lib) so the
        # package is self-contained (runnable with a completely empty env).
        # Files copied out of a Conan package are already code-signed.
        if "brotli" in self.dependencies:
            bp = self.dependencies["brotli"].package_folder
            copy(self, "libbrotli*.so*", os.path.join(bp, "lib"),
                 os.path.join(self.package_folder, "lib"), keep_path=False)
        if "libpng" in self.dependencies:
            pp = self.dependencies["libpng"].package_folder
            copy(self, "libpng16.so*", os.path.join(pp, "lib"),
                 os.path.join(self.package_folder, "lib"), keep_path=False)
        # The ohpcd zlib package is static-only (lib/libz.a) yet the Conan
        # libpng16.so.16 carries DT_NEEDED "libz.so" (upstream libpng linked a
        # non-SONAME host libz), and no loader default path on OHOS provides a
        # plain "libz.so".  Synthesize a shared libz.so (SONAME "libz.so") from
        # that static archive so the tools resolve zlib from the package lib/
        # instead of the host.  libz.a is already built with -fPIC.
        if "zlib" in self.dependencies:
            zp = self.dependencies["zlib"].package_folder
            libz_a = os.path.join(zp, "lib", "libz.a")
            if os.path.isfile(libz_a):
                self._build_shared_libz(libz_a)
        self._sign_binaries()

    def _build_shared_libz(self, libz_a: str) -> None:
        """Build a shared libz.so (SONAME libz.so) from the Conan static libz.a."""
        import shutil
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = (compilers or {}).get("c") or shutil.which("clang") or "clang"
        out = os.path.join(self.package_folder, "lib", "libz.so")
        self.run(f'"{cc}" -shared -fPIC -Wl,-soname,libz.so '
                 f'-o "{out}" -Wl,--whole-archive "{libz_a}" -Wl,--no-whole-archive')

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        """HarmonyOS PC requires a code-signed ELF for execution / loading.

        Uses the same signing flow as the other OHOS CLI recipes in this repo
        (e.g. abbtr / acme / accountsservice): strip any pre-existing
        `.codesign` section, then re-sign with binary-sign-tool.  Both the
        executables under bin/ and the shared runtime libs shipped under lib/
        (libbrotli*, libpng16*, libz.so) are signed.  The signing tools live
        under the OHOS SDK; `shutil.which` is tried first and the SDK path is
        used as a fallback (they are not always on the build PATH).
        """
        if str(self.settings.os) != "OHOS":
            return
        import glob
        import shutil
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, signer):
            if not os.path.isfile(tool):
                raise ConanException(f"Required OHOS signing tool not found: {tool}")

        targets = []
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            # Sign only real files (skip the version-symlink targets like
            # libpng16.so -> libpng16.so.16 to avoid double-signing the same inode).
            for f in sorted(glob.glob(os.path.join(libdir, "*.so*"))):
                if os.path.isfile(f) and not os.path.islink(f) and self._is_elf(f):
                    targets.append(f)
        for f in targets:
            # Remove a stale signature so binary-sign-tool won't refuse with
            # ".codesign section already exists" (E077); ignore if absent.
            self.run(f'"{objcopy}" --remove-section .codesign "{f}" 2>/dev/null || true')
            self.run(f'"{signer}" sign -inFile "{f}" -outFile "{f}" -selfSign 1')

    def package_info(self):
        # Application package: consumers use the tools in bin/.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.set_property("cmake_file_name", "libjxl-tools")
        self.cpp_info.set_property("cmake_target_name", "libjxl-tools::tools")
