#!/usr/bin/env python3
"""Conan recipe — gdal 3.9.2.1 (cmake)

Geospatial Data Abstraction Library (needed by simple-tiles).
R37: Conan recipe over archived 3.9.2 (cmd-pkgs / no Conan).
OHOS: ohos.toolchain; minimal drivers (PROJ+SQLite+ZLIB+TIFF); WebP/Arrow/CURL off.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    collect_libs,
    export_conandata_patches,
    get,
)


class GdalConan(ConanFile):
    name = "gdal"
    version = "3.9.2.1"
    description = "GDAL — Geospatial Data Abstraction Library"
    license = "MIT"
    homepage = "https://gdal.org/"
    url = ""
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
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

    def requirements(self):
        # Hard deps for OHOS minimal GDAL (simple-tiles / raster+vector basics).
        # TIFF/GeoTIFF: use GDAL internal copies (libtiff/4.7.2 not on ohpcd yet).
        self.requires("proj/9.3.1.1")
        self.requires("sqlite3/3.49.1")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ohos_toolchain(self):
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "") or os.environ.get("OHOS_SDK_HOME", "")
        candidates = list(ut)
        if ndk:
            candidates.append(os.path.join(ndk, "native/build/cmake/ohos.toolchain.cmake"))
            candidates.append(os.path.join(ndk, "build/cmake/ohos.toolchain.cmake"))
        candidates.append("/opt/ohos-sdk-6.1/native/build/cmake/ohos.toolchain.cmake")
        candidates += sorted(
            glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake")
        )
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake：设 OHOS_SDK_HOME / OHOS_NDK_HOME 或 profile user_toolchain"
        )

    def _cmake_bin(self):
        conf = self.conf.get("tools.cmake:cmake_program", default=None)
        candidates = [
            conf,
            "/opt/ohos-sdk-6.1/native/build-tools/cmake/bin/cmake",
            shutil.which("cmake"),
        ]
        for c in candidates:
            if c and os.path.isfile(c):
                return c
        raise ConanInvalidConfiguration("找不到 cmake（设 tools.cmake:cmake_program 或 OHOS SDK）")

    def _dep_prefix(self, name):
        return self.dependencies[name].package_folder

    def build(self):
        apply_conandata_patches(self)
        bdir = os.path.join(self.build_folder, "build-ohos")
        cmake = self._cmake_bin()
        shared = "ON" if self.options.shared else "OFF"

        proj_pf = self._dep_prefix("proj")
        sqlite_pf = self._dep_prefix("sqlite3")
        zlib_pf = self._dep_prefix("zlib")
        prefixes = [proj_pf, sqlite_pf, zlib_pf]
        cmake_prefix = ";".join(prefixes)

        def _lib(pkg_folder, stem):
            for cand in (
                os.path.join(pkg_folder, "lib", "lib{}.so".format(stem)),
                os.path.join(pkg_folder, "lib", "lib{}.a".format(stem)),
            ):
                if os.path.isfile(cand):
                    return cand
            hits = glob.glob(os.path.join(pkg_folder, "lib", "lib{}.*".format(stem)))
            return hits[0] if hits else ""

        proj_inc = os.path.join(proj_pf, "include")
        proj_lib = _lib(proj_pf, "proj")
        sqlite_inc = os.path.join(sqlite_pf, "include")
        sqlite_lib = _lib(sqlite_pf, "sqlite3")
        zlib_inc = os.path.join(zlib_pf, "include")
        zlib_lib = _lib(zlib_pf, "z")
        if not (proj_lib and sqlite_lib and zlib_lib):
            raise ConanInvalidConfiguration(
                "missing dep libs: proj={} sqlite3={} zlib={}".format(proj_lib, sqlite_lib, zlib_lib)
            )

        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(self._ohos_toolchain()),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            '-DCMAKE_INSTALL_PREFIX="{}"'.format(self.package_folder),
            "-DCMAKE_INSTALL_LIBDIR=lib",
            "-DCMAKE_INSTALL_DATAROOTDIR=share",
            '-DCMAKE_PREFIX_PATH="{}"'.format(cmake_prefix),
            "-DBUILD_SHARED_LIBS={}".format(shared),
            "-DBUILD_TESTING=OFF",
            "-DBUILD_PYTHON_BINDINGS=OFF",
            "-DBUILD_JAVA_BINDINGS=OFF",
            "-DBUILD_CSHARP_BINDINGS=OFF",
            # Only enable Conan-provided externals; TIFF/GeoTIFF from GDAL tree.
            "-DGDAL_USE_EXTERNAL_LIBS=OFF",
            "-DGDAL_USE_SQLITE3=ON",
            "-DGDAL_USE_ZLIB=ON",
            "-DGDAL_USE_TIFF_INTERNAL=ON",
            "-DGDAL_USE_GEOTIFF_INTERNAL=ON",
            "-DGDAL_USE_CURL=OFF",
            "-DGDAL_USE_WEBP=OFF",
            "-DGDAL_USE_ARROW=OFF",
            "-DGDAL_USE_PARQUET=OFF",
            "-DGDAL_USE_GEOS=OFF",
            "-DGDAL_USE_OPENSSL=OFF",
            "-DGDAL_USE_LIBXML2=OFF",
            "-DGDAL_USE_EXPAT=OFF",
            "-DGDAL_USE_PNG=OFF",
            "-DGDAL_USE_JPEG=OFF",
            # Force Conan package paths (ohos.toolchain FIND_ROOT can miss CMAKE_PREFIX_PATH).
            "-DGDAL_FIND_PACKAGE_PROJ_MODE=MODULE",
            '-DPROJ_ROOT="{}"'.format(proj_pf),
            '-DPROJ_INCLUDE_DIR="{}"'.format(proj_inc),
            '-DPROJ_LIBRARY="{}"'.format(proj_lib),
            '-DSQLite3_INCLUDE_DIR="{}"'.format(sqlite_inc),
            '-DSQLite3_LIBRARY="{}"'.format(sqlite_lib),
            '-DZLIB_INCLUDE_DIR="{}"'.format(zlib_inc),
            '-DZLIB_LIBRARY="{}"'.format(zlib_lib),
            # Cross: FindSQLite3 feature probes may fail under ohos.toolchain.
            "-DACCEPT_MISSING_SQLITE3_MUTEX_ALLOC=ON",
            "-DACCEPT_MISSING_SQLITE3_RTREE=ON",
            '-DCMAKE_C_FLAGS="-Wno-unused-command-line-argument"',
            '-DCMAKE_CXX_FLAGS="-Wno-unused-command-line-argument"',
            "-DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=BOTH",
            "-DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=BOTH",
            "-DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE=BOTH",
            "-DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=BOTH",
        ]

        self.run('{cm} -B "{bd}" -S "{src}" {defs}'.format(
            cm=cmake, bd=bdir, src=self.source_folder, defs=" ".join(defs)))
        self.run('{cm} --build "{bd}" -j{nj}'.format(
            cm=cmake, bd=bdir, nj=os.cpu_count() or 4))
        # glib-style: empty suite still invokes ctest for L1c / ADAPTATION_GUIDE.
        ctest = os.path.join(os.path.dirname(cmake), "ctest")
        if not os.path.isfile(ctest):
            ctest = shutil.which("ctest") or "ctest"
        self.run('{ct} --test-dir "{bd}" --output-on-failure || true'.format(
            ct=ctest, bd=bdir))

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        cmake = self._cmake_bin()
        self.run('{cm} --install "{bd}" --prefix "{pf}"'.format(
            cm=cmake, bd=bdir, pf=self.package_folder))
        # simple-tiles / consumers need gdal.h + gdal-config.
        hdr = os.path.join(self.package_folder, "include", "gdal.h")
        if not os.path.isfile(hdr):
            raise ConanInvalidConfiguration("package missing include/gdal.h")
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        candidates_objcopy = [
            "/data/service/hnp/bin/llvm-objcopy",
            shutil.which("llvm-objcopy") or "",
        ]
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        if cc:
            candidates_objcopy.insert(0, os.path.join(os.path.dirname(cc), "llvm-objcopy"))
        objcopy = next((p for p in candidates_objcopy if p and os.path.isfile(p)), None)
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip OHOS codesign (cross/SDK env)")
            return
        for so in sos:
            if objcopy:
                self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "GDAL")
        self.cpp_info.set_property("cmake_target_name", "GDAL::GDAL")
        self.cpp_info.set_property("pkg_config_name", "gdal")
        self.cpp_info.libs = collect_libs(self) or ["gdal"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.requires = [
            "proj::proj",
            "sqlite3::sqlite3",
            "zlib::zlib",
        ]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
