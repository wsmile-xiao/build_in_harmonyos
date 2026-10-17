#!/usr/bin/env python3
"""Conan recipe — libarchive 3.7.7 (CMake build system).

libarchive is a multi-format archive and compression library (tar, cpio, zip,
ISO, 7-zip, ...), providing libarchive + bsdtar/bsdcpio/bsdcat/bsdunzip tools.

Upstream CMakeLists.txt declares cmake_minimum_required(VERSION 2.8.0) which
CMake 4.x rejects; pass CMAKE_POLICY_VERSION_MINIMUM=3.5 (same as libtiff).

Build: cmake + OHOS NDK ohos.toolchain.cmake (self-discovered, ML-0035:
conan_toolchain maps os=OHOS to a CMAKE_SYSTEM_NAME cmake does not recognise).
Dependencies are wired by pre-setting the find_* cache variables of upstream's
Find modules (zlib/bzip2/lzma/zstd) — FIND_ROOT_PATH_MODE=ONLY hides conan
package dirs, so the cache variables bypass the search entirely (libtiff
4.7.2 approach). Optional deps unavailable on OHOS are disabled:
nettle/mbedtls/cng/libb2/lzo/pcre/pcre2/libgcc/expat/libxml2/lz4.
libxml2 is intentionally disabled (xar format only; keeps the dependency graph
lean — expat is an either/or alternative for xar, both OFF).
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class LibarchiveConan(ConanFile):
    name = "libarchive"
    version = "3.7.7"
    description = "Multi-format archive and compression library (tar, cpio, zip, ...)"
    license = "BSD-2-Clause"
    homepage = "https://www.libarchive.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"  # recipe contribution repo

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # zlib must be the -fPIC static rebuild (zlib/1.3.1.1): the upstream
        # zlib/1.3.1 libz.a objects are not position-independent and linking
        # them into the shared libarchive.so fails on aarch64 with
        # R_AARCH64_ADR_PREL_PG_HI21 relocation errors (3.8.7 notes, CI #18317).
        self.requires("zlib/1.3.1.1")
        self.requires("bzip2/1.0.8")
        self.requires("xz/5.6.2")      # liblzma
        self.requires("zstd/1.5.7")

    def layout(self):
        # basic_layout: cmake is driven manually with self.run() (ohos toolchain
        # approach), no conan cmake generators needed.
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ohos_toolchain(self):
        # Self-discover OHOS NDK ohos.toolchain.cmake (glfw/libjpeg-turbo/
        # zstd/libtiff approach): 1) profile [conf] user_toolchain
        # 2) OHOS_NDK_HOME env 3) glob the device/CI SDK layout.
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        for cand in list(ut) + ([os.path.join(ndk, "build", "cmake", "ohos.toolchain.cmake")] if ndk else []):
            if cand and os.path.isfile(cand):
                return cand
        found = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if found:
            return found[-1]
        raise ConanInvalidConfiguration(
            "Cannot find ohos.toolchain.cmake: set OHOS_NDK_HOME or profile conf user_toolchain")

    def build(self):
        apply_conandata_patches(self)
        toolchain = self._ohos_toolchain()
        llvm_bin = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(toolchain))), "llvm", "bin")
        cmake_ar = os.path.join(llvm_bin, "llvm-ar")
        # OHOS SDK does not ship llvm-ranlib; wrap "llvm-ar s" (zstd recipe).
        ranlib_shim = os.path.join(self.build_folder, "llvm-ranlib-shim")
        with open(ranlib_shim, "w") as f:
            f.write("#!/data/service/hnp/bin/bash\nexec {} s \"$@\"\n".format(cmake_ar))
        os.chmod(ranlib_shim, 0o755)

        src = self.source_folder
        bdir = os.path.join(self.build_folder, "build-ohos")
        defs = [
            '-DCMAKE_TOOLCHAIN_FILE={}'.format(toolchain),
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",   # cmake 4.x vs cmake_minimum_required(2.8.0)
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_AR={}".format(cmake_ar),
            "-DCMAKE_RANLIB={}".format(ranlib_shim),
            "-DBUILD_SHARED_LIBS={}".format("ON" if self.options.shared else "OFF"),
            # optional deps not available / not wanted on OHOS
            "-DENABLE_NETTLE=OFF",
            "-DENABLE_MBEDTLS=OFF",
            "-DENABLE_CNG=OFF",
            "-DENABLE_LIBB2=OFF",
            "-DENABLE_LZO=OFF",
            "-DENABLE_PCREPOSIX=OFF",
            "-DENABLE_PCRE2POSIX=OFF",
            "-DENABLE_LIBGCC=OFF",
            "-DENABLE_EXPAT=OFF",     # xar XML: expat/libxml2 are either/or, both disabled
            "-DENABLE_LIBXML2=OFF",   # xar format only; keeps graph lean (see notes.md)
            "-DENABLE_LZ4=OFF",       # not in registry
            # tests: upstream suite is run separately in the workflow (L1);
            # building the test binaries here would double the compile time.
            "-DENABLE_TEST=OFF",
        ]
        # Wire conan deps into upstream Find modules via cache variables.
        # (conan dep, INCLUDE var, [LIB vars...], [lib file candidates])
        wire = [
            ("zlib",  "ZLIB_INCLUDE_DIR",    ["ZLIB_LIBRARY"],                               ["libz.a"]),
            ("bzip2", "BZIP2_INCLUDE_DIR",   ["BZIP2_LIBRARIES"],                            ["libbz2.a"]),
            ("xz",    "LIBLZMA_INCLUDE_DIR", ["LIBLZMA_LIBRARY", "LIBLZMA_LIBRARIES"],       ["liblzma.a"]),
            ("zstd",  "ZSTD_INCLUDE_DIR",    ["ZSTD_LIBRARY"],                               ["libzstd.so", "libzstd.a"]),
        ]
        libdirs = []
        for dep_name, inc_var, lib_vars, names in wire:
            pkg = self.dependencies[dep_name].package_folder
            defs.append('-D{}="{}"'.format(inc_var, os.path.join(pkg, "include")))
            lib_path = next(
                (hit for name in names for hit in glob.glob(os.path.join(pkg, "lib", name))),
                os.path.join(pkg, "lib", names[0]))
            for lv in lib_vars:
                defs.append('-D{}="{}"'.format(lv, lib_path))
            libdirs.append(os.path.join(pkg, "lib"))
        # Linking libarchive.so pulls in the deps' .so (zstd) — give the linker
        # -L + -rpath-link for the transitive NEEDED entries (libtiff approach).
        ldflags = " ".join("-L{} -Wl,-rpath-link,{}".format(d, d) for d in libdirs)
        os.environ["LDFLAGS"] = ldflags + " " + os.environ.get("LDFLAGS", "")

        self.run('cmake -G Ninja -B "{bdir}" -S "{src}" {defs}'.format(
            bdir=bdir, src=src, defs=" ".join(defs)))
        self.run('cmake --build "{bdir}" -- -j$(nproc)'.format(bdir=bdir))
        self._bdir = bdir

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        # HarmonyOS PC: dlopen-ed .so must carry a valid code signature.
        # Strip any stale .codesign section and re-sign (ML-0043, zstd recipe).
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for so in sos:
            if os.path.islink(so):
                continue  # sign real ELF only, skip versioned symlinks
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))

    def package_info(self):
        self.cpp_info.libs = ["archive"]
        # Standard CMake consumer: find_package(libarchive) → libarchive::archive
        self.cpp_info.set_property("cmake_file_name", "libarchive")
        self.cpp_info.set_property("cmake_target_name", "libarchive::archive")
        self.cpp_info.set_property("pkg_config_name", "libarchive")
        # R38: CLI tools shipped (bsdtar/bsdcpio/bsdcat/bsdunzip) → declare bindirs
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
