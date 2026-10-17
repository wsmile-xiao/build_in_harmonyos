#!/usr/bin/env python3
"""Conan recipe — blupimania 1.6.3 (cmake, application).

Blupimania is a logic puzzle game (pure C + SDL2). Upstream builds a single
executable via CMake (dynamic branch): SDL2 + SDL2_image + SDL2_mixer +
WebP::webpdemux. No library target and no upstream automated tests in v1.6.3
(no enable_testing/add_test — see notes.md for the R51 inventory).

OHOS adaptation notes (verified locally 2026-09-07):
  - CMakeLists.txt declares cmake_minimum_required(VERSION 3.2); CMake 4.x
    removed <3.5 compatibility -> CMAKE_POLICY_VERSION_MINIMUM=3.5
    (same as ballerburg/1.2.3-git20250916, cdogs-sdl/1.0.0).
  - E092: CMake does not know HarmonyOS; CMAKE_SYSTEM_NAME=Linux +
    CMAKE_SYSTEM_PROCESSOR=aarch64 (same as sdl2-image/2.8.12).
  - Upstream links WebP::webpdemux, but the libwebp recipe only exposes
    WebP::webp (libwebpdemux.so ships in the same package). Inject the
    missing imported target as a CMake build module
    (same approach as sdl2-image/2.8.12).
  - CMakeDeps names configs after the conan package name; upstream does
    find_package(SDL2_mixer REQUIRED) + links SDL2_mixer::SDL2_mixer.
    Override cmake_file_name to SDL2_mixer (case-sensitive config lookup).
  - sdl2_mixer/2.8.2 and sdl2-image/2.8.12 pin sdl2/2.30.10 -> the same
    version is required here (Conan version conflict otherwise).
  - The packaged ELF must be signed before it can execute on OHOS
    (binary-sign-tool), so package() signs bin/blupimania; the consumer
    test_package then runs `blupimania --version` (argtable3 parses and
    exits before SDL_Init, exit code 0) and asserts the version banner.
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class BlupimaniaConan(ConanFile):
    name = "blupimania"
    version = "1.6.3"
    description = "Blupimania - A mind boggling (brain twisting) game of logic"
    license = "GPL-3.0"
    homepage = "https://github.com/blupi-games/blupimania"
    url = "https://github.com/blupi-games/blupimania"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("sdl2/2.30.10")
        self.requires("sdl2-image/2.8.12")
        self.requires("sdl2_mixer/2.8.2")
        self.requires("libwebp/1.6.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)

        # libwebp package only exposes WebP::webp, but upstream CMakeLists
        # links WebP::webpdemux (libwebpdemux.so ships in the same package).
        # Inject the missing imported target (sdl2-image/2.8.12 approach).
        webp = self.dependencies["libwebp"]
        if webp.package_folder:
            module = os.path.join(self.generators_folder, "WebP-webpdemux.cmake")
            with open(module, "w", encoding="utf-8") as fh:
                fh.write("if(NOT TARGET WebP::webpdemux)\n")
                fh.write("  add_library(WebP::webpdemux UNKNOWN IMPORTED)\n")
                fh.write("  set_target_properties(WebP::webpdemux PROPERTIES\n")
                fh.write("      IMPORTED_LOCATION \"%s\")\n" % os.path.join(
                    webp.package_folder, "lib", "libwebpdemux.so"))
                fh.write("endif()\n")
            deps.set_property("libwebp", "cmake_build_modules", [module])

        # Upstream: find_package(SDL2 REQUIRED) + links SDL2::SDL2. The sdl2
        # recipe sets no cmake properties, so CMakeDeps names the target
        # sdl2::sdl2 (config mode still finds the lowercase sdl2-config.cmake,
        # but the upstream target name is case-sensitive). Align it.
        deps.set_property("sdl2", "cmake_target_name", "SDL2::SDL2")

        # Upstream: find_package(SDL2_mixer REQUIRED) + SDL2_mixer::SDL2_mixer.
        # CMakeDeps config lookup is case-sensitive; the conan package name is
        # sdl2_mixer, so align the generated config/target names with upstream.
        deps.set_property("sdl2_mixer", "cmake_file_name", "SDL2_mixer")
        deps.set_property("sdl2_mixer", "cmake_target_name", "SDL2_mixer::SDL2_mixer")

        deps.generate()

        tc = CMakeToolchain(self)
        # E092: CMake does not know HarmonyOS (sdl2-image/2.8.12 approach)
        tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # find_library(MATH_LIBRARY m) fails on OHOS (musl has all math in
        # libc, no separate libm to find); pre-seed the cache so the upstream
        # search is skipped and nothing extra is linked
        # (ballerburg/1.2.3-git20250916 precedent).
        tc.cache_variables["MATH_LIBRARY"] = ""

        # Shared deps (libwebp.so/libtiff.so/...): -L + -rpath-link resolve
        # transitive NEEDED entries at link time (sdl2-image/2.8.12 approach).
        libdirs = []
        for dep in self.dependencies.values():
            if dep.package_folder:
                for ld in dep.cpp_info.libdirs:
                    if ld and os.path.isdir(ld) and ld not in libdirs:
                        libdirs.append(ld)
        if libdirs:
            flags = " ".join("-L{0} -Wl,-rpath-link,{0}".format(d) for d in libdirs)
            tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = flags

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # R9: single-job build on OHOS (sdl2_mixer/2.8.2 approach)
        cmake.build(cli_args=["--parallel", "1"])
        # CI L1c trace: upstream has no test targets in v1.6.3; ctest exits 1
        # with "No tests found" and the || true keeps the build green
        # (sdl2_mixer/2.8.2 approach).
        self.run("ctest --output-on-failure || true", cwd=self.build_folder)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._sign_binaries()

    def _sign_binaries(self):
        # Unsigned ELF binaries cannot execute on OHOS; re-sign bin/ contents
        # (libwebp/1.6.0 _sign_shared_libs approach, applied to executables).
        # binary-sign-tool links the OHOS system libc++ (St3__h inline
        # namespace); the /usr/local/bin/conan wrapper injects an SDK
        # LD_LIBRARY_PATH whose conflicting libc++ breaks its relocation
        # ("Error relocating ... _ZSt7nothrow: symbol not found"). Clear
        # LD_LIBRARY_PATH for the signer so it always resolves system libs.
        bindir = os.path.join(self.package_folder, "bin")
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for path in sorted(glob.glob(os.path.join(bindir, "*"))):
            if not os.path.isfile(path):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                oc=objcopy, f=path), ignore_errors=True)
            tmp = path + ".signed"
            self.run('env -u LD_LIBRARY_PATH {sg} sign -inFile "{f}" -outFile "{t}" -selfSign 1'.format(
                sg=signer, f=path, t=tmp))
            if os.path.exists(tmp):
                os.replace(tmp, path)
            os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
