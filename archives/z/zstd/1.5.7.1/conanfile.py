#!/usr/bin/env python3
"""Conan recipe - zstd 1.5.7.1 (cmake)

Zstandard (zstd) is a fast real-time compression algorithm by Facebook.
Provides libzstd shared library and command-line tools (zstd, unzstd, zstdcat, etc.).

Build: cmake (build/cmake subdirectory) with OHOS NDK ohos.toolchain.cmake,
self-discovered (no conan_toolchain dependency). R32: os in ("Linux", "OHOS").
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import collect_libs, get
from conan.tools.cmake import CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import apply_conandata_patches


class ZstdConan(ConanFile):
    name = "zstd"
    version = "1.5.7.1"
    description = "Zstandard - fast real-time compression algorithm"
    license = "BSD-3-Clause AND GPL-2.0-or-later"
    homepage = "https://github.com/facebook/zstd"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        # R32: platform detection must use in ("Linux", "OHOS")
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self, src_folder=".")

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def _ohos_toolchain(self):
        # Self-discover OHOS NDK ohos.toolchain.cmake (no profile host user_toolchain
        # dependency). Same approach as glfw/3.4.6, libjpeg-turbo/3.2.0.
        import os
        import glob
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        candidates = list(ut) + ([os.path.join(ndk, "build", "cmake", "ohos.toolchain.cmake")] if ndk else [])
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        globbed = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if globbed:
            return globbed[-1]
        raise ConanInvalidConfiguration(
            "Cannot find ohos.toolchain.cmake: set OHOS_NDK_HOME, or configure "
            "tools.cmake.cmaketoolchain:user_toolchain=[<sdk>/ohos/native/build/cmake/ohos.toolchain.cmake] in profile [conf]")

    def build(self):
        # Use OHOS NDK ohos.toolchain.cmake directly (CMAKE_SYSTEM_NAME=OHOS →
        # cmake recognises the system, produces correct SONAME/version symlinks,
        # GNUInstallDirs works). Avoids conan_toolchain which degenerates to
        # "System is unknown HarmonyOS" (ML-0035).
        import os
        apply_conandata_patches(self)
        self._patch_gnu_qsort_r()
        toolchain = self._ohos_toolchain()
        # Derive llvm-ar path from toolchain directory
        llvm_bin = os.path.dirname(toolchain)  # .../build/cmake -> .../build
        llvm_bin = os.path.join(os.path.dirname(os.path.dirname(llvm_bin)), "llvm", "bin")
        cmake_ar = os.path.join(llvm_bin, "llvm-ar")
        # OHOS SDK doesn't ship llvm-ranlib; create a wrapper that uses llvm-ar s
        ranlib_wrapper = os.path.join(self.build_folder, "llvm-ranlib-shim")
        with open(ranlib_wrapper, "w") as f:
            f.write("#!/data/service/hnp/bin/bash\nexec {ar} s \"$@\"\n".format(ar=cmake_ar))
        os.chmod(ranlib_wrapper, 0o755)
        # zstd CMakeLists.txt is in build/cmake subdirectory
        cml_dir = os.path.join(self.source_folder, "build", "cmake")
        bdir = os.path.join(self.build_folder, "build-ohos")
        defs = " ".join([
            '-DCMAKE_TOOLCHAIN_FILE={}'.format(toolchain),
            '-DCMAKE_AR={}'.format(cmake_ar),
            '-DCMAKE_RANLIB={}'.format(ranlib_wrapper),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",
            "-DZSTD_BUILD_SHARED=ON",
            "-DZSTD_BUILD_STATIC=ON",
            "-DZSTD_BUILD_PROGRAMS=ON",
            "-DZSTD_BUILD_TESTS=OFF",
        ])
        self.run('cmake -G Ninja -B {bdir} -S {cml_dir} {defs}'.format(bdir=bdir, cml_dir=cml_dir, defs=defs))
        self.run('cmake --build {bdir} -- -j$(nproc)'.format(bdir=bdir))

    def _patch_gnu_qsort_r(self):
        # OHOS uses musl, which lacks GNU qsort_r. zstd's cover.c and zstd_deps.h
        # #define _GNU_SOURCE under __linux__ → tries glibc qsort_r → undefined symbol.
        # Add __OHOS__ exception (same as upstream's __ANDROID__ handling:
        # "NDK doesn't ship qsort_r()"), falling back to C90 qsort (global ctx).
        import os
        old = "#if !defined(_GNU_SOURCE) && !defined(__ANDROID__)"
        new = "#if !defined(_GNU_SOURCE) && !defined(__ANDROID__) && !defined(__OHOS__)"
        for rel in ("lib/dictBuilder/cover.c", "lib/common/zstd_deps.h"):
            p = os.path.join(self.source_folder, rel)
            with open(p, encoding="utf-8") as f:
                txt = f.read()
            if old in txt:
                with open(p, "w", encoding="utf-8") as f:
                    f.write(txt.replace(old, new))

    def package(self):
        import os
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        # HarmonyOS PC requires code signing for .so files loaded via dlopen.
        # SDK toolchain-built .so may have invalid self-sign → strip old .codesign
        # and re-sign with binary-sign-tool -selfSign 1 (ML-0043).
        import glob
        import os
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for so in sos:
            if os.path.islink(so):
                continue  # skip symlinks, sign real ELF only
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))

    def package_info(self):
        explicit_libs = ['zstd']
        self.cpp_info.libs = explicit_libs or collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "zstd")
        self.cpp_info.set_property("cmake_target_name", "zstd::libzstd")
        # R38: declare bindirs so CI recognizes CLI tools (zstd/unzstd/zstdcat)
        self.cpp_info.bindirs = ["bin"]
        pkg = self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)

    def _detect_pkg_config_name(self):
        # Detect pkg-config name from installed .pc files.
        import glob
        import os
        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        if not pcs:
            return ""
        return os.path.splitext(os.path.basename(pcs[0]))[0]