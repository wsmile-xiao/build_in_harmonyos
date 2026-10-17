#!/usr/bin/env python3
"""Conan recipe — libgeotiff 1.7.4 (cmake)

libgeotiff is a library for reading and writing GeoTIFF tags in TIFF files.
It depends on libtiff and PROJ for coordinate reference system handling.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
import os
import glob
import shutil


class LibgeotiffConan(ConanFile):
    name = "libgeotiff"
    version = "1.7.1"
    description = "Library for reading and writing GeoTIFF tags in TIFF files"
    license = "MIT"
    homepage = "https://github.com/OSGeo/libgeotiff"
    url = ""
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        # Check if source already extracted (handles offline/re-run scenarios)
        if os.path.exists(os.path.join(self.source_folder, "CMakeLists.txt")):
            return
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        self.requires("libtiff/4.7.2")
        self.requires("proj/9.3.1.1")
        self.requires("zlib/1.3.1.1")
        self.requires("libjpeg-turbo/3.2.0")

    def layout(self):
        from conan.tools.cmake import cmake_layout
        cmake_layout(self, src_folder=".")

    def _ohos_toolchain(self):
        """Self-discover OHOS NDK ohos.toolchain.cmake."""
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        for _c in list(ut) + ([os.path.join(ndk, "build/cmake/ohos.toolchain.cmake")] if ndk else []):
            if _c and os.path.isfile(_c):
                return _c
        _sdk = os.environ.get("OHOS_SDK_HOME", "")
        if _sdk:
            _tc = os.path.join(_sdk, "ohos/native/build/cmake/ohos.toolchain.cmake")
            if os.path.isfile(_tc):
                return _tc
        # Fallback: discover from HNP_PUBLIC_HOME (CI standard env var)
        _hnp = os.environ.get("HNP_PUBLIC_HOME", "")
        if _hnp:
            _g = sorted(glob.glob(os.path.join(_hnp, "ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake")))
            if _g:
                return _g[-1]
        raise ConanInvalidConfiguration(
            "Cannot find ohos.toolchain.cmake: set OHOS_NDK_HOME or OHOS_SDK_HOME or profile [conf] user_toolchain")

    def build(self):
        apply_conandata_patches(self)
        toolchain = self._ohos_toolchain()
        src = self.source_folder
        bdir = os.path.join(self.build_folder, "build-ohos")
        _ohos_arch = "arm64-v8a" if str(self.settings.arch).startswith("armv8") else str(self.settings.arch)
        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH={}".format(_ohos_arch),
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",
            "-DBUILD_SHARED_LIBS={}".format("ON" if self.options.shared else "OFF"),
            "-DWITH_TIFF=ON",
            "-DWITH_UTILITIES=OFF",
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
            # libproj.a is a C++ static library — linking a C shared lib against it
            # requires the C++ runtime. Use -fuse-ld=bfd (bfd auto-resolves C++ symbols)
            # and add -lc++_shared explicitly.
            '-DCMAKE_C_FLAGS="-fPIC"',
            '-DCMAKE_SHARED_LINKER_FLAGS="-lc++_shared -fuse-ld=bfd"',
            # OHOS SDK 26.0.0.18 llvm/bin/ has llvm-ar but NOT llvm-ranlib.
            # CMake's CMAKE_AR/CMAKE_RANLIB default to the toolchain's bin/,
            # so libxtiff.a creation fails with "llvm-ranlib: No such file or
            # directory". Point CMAKE_RANLIB at the HNP-wide llvm-ranlib
            # (/data/service/hnp/bin/llvm-ranlib -> llvm-ar 15.0.4), which
            # supports the `llvm-ranlib <archive>` invocation.
            '-DCMAKE_RANLIB="/data/service/hnp/bin/llvm-ranlib"',
            '-DCMAKE_AR="/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/llvm-ar"',
        ]

        # Wire up dependencies: libgeotiff uses find_package(PROJ) and find_package(TIFF).
        # The CMakeLists.txt tries config mode first (NO_MODULE), then falls back to module mode.
        # We pre-set the cache variables used by the module-mode FindPROJ.cmake and standard FindTIFF.
        # Config mode is bypassed because CMAKE_FIND_ROOT_PATH is not set to package folders.
        _wire = [
            # (conan dep, INCLUDE_DIR cache var, LIBRARY cache var, [lib file candidates])
            ("proj", "PROJ_INCLUDE_DIR", "PROJ_LIBRARY", ["libproj.a", "libproj.so"]),
            ("libtiff", "TIFF_INCLUDE_DIR", "TIFF_LIBRARY", ["libtiff.so", "libtiff.a"]),
        ]
        _ldirs = []
        for _dep, _incv, _libv, _names in _wire:
            _pkg = self.dependencies[_dep].package_folder
            defs.append('-D{}="{}"'.format(_incv, os.path.join(_pkg, "include")))
            _lp = next((h for n in _names for h in glob.glob(os.path.join(_pkg, "lib", n))),
                       os.path.join(_pkg, "lib", _names[0]))
            defs.append('-D{}="{}"'.format(_libv, _lp))
            _ldirs.append(os.path.join(_pkg, "lib"))

        # Add lib dirs for all transitive deps (zlib, libjpeg-turbo, etc.) for rpath-link
        for _ref, _d in self.dependencies.items():
            _pf = _d.package_folder
            if _pf is None:
                continue
            _lp = os.path.join(_pf, "lib")
            if os.path.isdir(_lp) and _lp not in _ldirs:
                _ldirs.append(_lp)

        # libproj has transitive deps on sqlite3, lzma, etc.
        # CMAKE_C_STANDARD_LIBRARIES is appended to the END of every link command,
        # so transitive deps are processed after libproj (which is linked via target_link_libraries).
        # Only link transitive libs whose files are actually available in _ldirs
        # (e.g., sqlite3/lzma may be skipped if proj is a shared lib from registry).
        def _lib_found(_name):
            for _d in _ldirs:
                if glob.glob(os.path.join(_d, "lib{}.so*".format(_name))) or \
                   glob.glob(os.path.join(_d, "lib{}.a".format(_name))):
                    return True
            return False

        _transitive_libs = []
        _seen = set()
        for _ref_name, _dep in self.dependencies.items():
            if _dep.package_folder is None:
                continue
            try:
                _cpp_info = _dep.cpp_info
                _libs = _cpp_info.libs if _cpp_info else []
                for _lib in _libs:
                    if _lib not in _seen and _lib not in ("geotiff", "tiff", "proj"):
                        if _lib_found(_lib):
                            _seen.add(_lib)
                            _transitive_libs.append("-l{}".format(_lib))
            except Exception:
                pass
        for _extra in ["sqlite3", "lzma", "zstd", "z", "jpeg", "webp"]:
            if _extra not in _seen and _lib_found(_extra):
                _seen.add(_extra)
                _transitive_libs.append("-l{}".format(_extra))

        # Build the standard libraries string with -L paths and transitive libs
        _L_flags = " ".join("-L{}".format(d) for d in _ldirs)
        _rpath_flags = " ".join("-Wl,-rpath-link,{}".format(d) for d in _ldirs)
        _link_str = " ".join(_transitive_libs)
        _std_libs = "{} {} -lc++_shared {}".format(_L_flags, _rpath_flags, _link_str)

        # CMAKE_SHARED_LINKER_FLAGS: just bfd linker
        for i, d in enumerate(defs):
            if "CMAKE_SHARED_LINKER_FLAGS" in d:
                defs[i] = '-DCMAKE_SHARED_LINKER_FLAGS="-fuse-ld=bfd"'
                break

        # CMAKE_C_STANDARD_LIBRARIES: transitive deps appended at end of link command
        defs.append('-DCMAKE_C_STANDARD_LIBRARIES="{}"'.format(_std_libs))

        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, src, " ".join(defs)))
        # CMake 3.5 + 1.7.1 libxtiff STATIC target: ARCHIVE_OUTPUT_DIRECTORY
        # is ${PROJECT_BINARY_DIR}/lib, but CMake doesn't create the parent
        # directory before invoking llvm-ar, so "Error running link command:
        # no such file or directory". Pre-create lib/ to fix.
        _lib_out = os.path.join(bdir, "lib")
        os.makedirs(_lib_out, exist_ok=True)
        self.run('cmake --build "{}"'.format(bdir))
        # L1: Run upstream official tests (ctest) as required by CI gate
        if not cross_building(self):
            self.run('ctest --test-dir "{}"'.format(bdir))

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        """Sign .so files for OHOS code verification."""
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        _tools_dir = os.environ.get("OHOS_TOOLS_DIR", "")
        objcopy = os.path.join(_tools_dir, "llvm-objcopy") if _tools_dir else shutil.which("llvm-objcopy")
        signer = os.path.join(_tools_dir, "binary-sign-tool") if _tools_dir else shutil.which("binary-sign-tool")
        if not signer or not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found, skipping .so signing")
            return
        for so in sos:
            if os.path.islink(so):
                continue
            if objcopy and os.path.isfile(objcopy):
                self.run('{oc} --remove-section .codesign "{f}"'.format(oc=objcopy, f=so), ignore_errors=True)
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))

    def package_info(self):
        self.cpp_info.libs = ["geotiff"]
        self.cpp_info.set_property("cmake_file_name", "GeoTIFF")
        self.cpp_info.set_property("cmake_target_name", "GeoTIFF::geotiff")
        self.cpp_info.set_property("pkg_config_name", "libgeotiff")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
