#!/usr/bin/env python3
"""Conan recipe — lib3mf 1.8.1 (cmake)

3MF (3D Manufacturing Format) reference implementation library.
OHOS adaptation:
  - external deps via conan (libzip/1.11.4, ossp-uuid/1.6.2, zlib/1.3.1.1),
    bundled Sources/Libraries/{libzip,zlib} disabled (USE_INCLUDED_*=OFF)
  - patches: CMake modernization + external dep linking, ossp-uuid API bridge,
    system include paths
  - ohos.toolchain.cmake + bare cmake (same pattern as libzip/1.11.4)
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches


class Lib3MfConan(ConanFile):
    name = "lib3mf"
    version = "1.8.1"
    description = "Lib3MF is a C++ implementation of the 3D Manufacturing Format (3MF) file standard"
    license = "BSD-2-Clause"
    homepage = "https://3mf.io"
    url = "https://github.com/3MFConsortium/lib3mf"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        from conan.tools.files import export_conandata_patches
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libzip/1.11.4")
        self.requires("zlib/1.3.1.1")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        from conan.tools.files import get
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        toolchain = self._ohos_toolchain()
        src = self.source_folder
        bdir = os.path.join(self.build_folder, "build-ohos")
        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",           # ohos.toolchain 64-bit defaults to lib64/, restore lib
            '-DCMAKE_INSTALL_PREFIX="{}"'.format(self.package_folder),
            "-DBUILD_SHARED_LIBS={}".format("ON" if self.options.shared else "OFF"),
            # external deps instead of bundled third_party copies
            "-DUSE_INCLUDED_ZLIB=OFF",
            "-DUSE_INCLUDED_LIBZIP=OFF",
            # tests need googletest submodule which release tarballs do not carry
            "-DLIB3MF_TESTS=OFF",
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
        ]
        _rl = self._llvm_ranlib(toolchain)
        if _rl:
            defs.append('-DCMAKE_RANLIB="{}"'.format(_rl))

        # dependency wiring for find_package/find_library under cross toolchain
        # (FIND_ROOT_PATH=ONLY blocks host discovery; pre-seed cache variables)
        libzip = self.dependencies["libzip"]
        zlib = self.dependencies["zlib"]
        dep_dirs = [d.package_folder for _r, d in self.dependencies.items() if d.package_folder]
        find_root = ";".join(dep_dirs)
        defs.append('-DCMAKE_FIND_ROOT_PATH="{}"'.format(find_root))
        defs.append('-Dlibzip_DIR="{}"'.format(
            os.path.join(libzip.package_folder, "lib", "cmake", "libzip")))
        defs.append('-DLIBUUID_PATH="{}"'.format(
            os.path.join(zlib.package_folder, "lib", "libz.a")))
        inc_flags = " ".join(
            "-I{}".format(os.path.join(d, "include")) for d in dep_dirs)
        defs.append('-DCMAKE_CXX_FLAGS="{}"'.format(inc_flags))
        defs.append('-DCMAKE_C_FLAGS="{}"'.format(inc_flags))

        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, src, " ".join(defs)))
        self.run('cmake --build "{}" -j4'.format(bdir))

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        self._sign_binaries()

    def _ohos_toolchain(self):
        # Self-discover OHOS NDK ohos.toolchain.cmake (① profile [conf] user_toolchain
        # ② env OHOS_NDK_HOME ③ glob device/CI SDK layout).
        import glob
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        for _c in list(ut) + ([os.path.join(ndk, "build/cmake/ohos.toolchain.cmake")] if ndk else []):
            if _c and os.path.isfile(_c):
                return _c
        _g = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if _g:
            return _g[-1]
        raise ConanInvalidConfiguration(
            "ohos.toolchain.cmake not found: set OHOS_NDK_HOME or profile [conf] user_toolchain")

    def _llvm_ranlib(self, toolchain):
        # OHOS SDK llvm/bin has llvm-ar but NOT llvm-ranlib, while ohos.toolchain.cmake
        # still points CMAKE_RANLIB there. Same issue as libzip/1.11.4 (OpenCV/SuiteSparse).
        import shutil
        sdk_bin = os.path.join(toolchain, "..", "..", "..", "llvm", "bin")
        cand = os.path.normpath(os.path.join(sdk_bin, "llvm-ranlib"))
        if os.path.isfile(cand):
            return ""                            # SDK has it, no override needed
        return shutil.which("llvm-ranlib") or ""

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # HarmonyOS PC XPM requires code signatures on dlopen'ed .so files.
        import glob
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):   # only sign real ELF, skip versioned .so symlinks
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.libs = ["3MF"]
        self.cpp_info.set_property("cmake_file_name", "lib3MF")
        self.cpp_info.set_property("cmake_target_name", "lib3MF::lib3MF")
        pkg = self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)

    def _detect_pkg_config_name(self):
        import glob
        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        if not pcs:
            return ""
        return os.path.splitext(os.path.basename(pcs[0]))[0]
