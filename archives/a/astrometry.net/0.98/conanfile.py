#!/usr/bin/env python3
"""Conan recipe — astrometry.net 0.98 (custom Makefile + configure).
"""
import os
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AstrometrynetConan(ConanFile):
    name = "astrometry.net"
    version = "0.98"
    description = "astrometry.net 0.98 — automatic astrometric calibration of astronomical images"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/dstndstn/astrometry.net"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("cfitsio/4.6.4")
        self.requires("gsl/2.8")
        self.requires("bzip2/1.0.8")
        self.requires("zlib/1.3.1.1")
        self.requires("openssl/3.5.6.1")
        self.requires("cairo/1.18.4")
        self.requires("libpng/1.6.58")
        # libjpeg optional (astrometry.net uses pkg-config check; if not found, JPEG features disabled)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R04: Apply gsl-an build fix directly (conan-verify restores conandata.yml, wiping patch registration)
        # config.guess 2016-04-02 cannot detect HarmonyOS/HongMeng Kernel → add --build flag
        gsl_makefile = os.path.join(self.source_folder, "gsl-an", "Makefile")
        if os.path.isfile(gsl_makefile):
            with open(gsl_makefile) as f:
                content = f.read()
            if "--build=" not in content:
                content = content.replace(
                    "./configure --enable-shared=no --prefix=`pwd`/stage",
                    "./configure --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu --enable-shared=no --prefix=`pwd`/stage"
                )
                with open(gsl_makefile, "w") as f:
                    f.write(content)
                self.output.info("gsl-an Makefile: added --build flag (HarmonyOS config.guess fix)")
        # astrometry.net uses a custom bash configure + Makefile
        # configure is a stub, main build is via Makefile
        # R04: Also fix gsl-an sys/infnan.c — need HAVE_DECL_FINITE and HAVE_DECL_ISNAN on OHOS (clang has finite/isnan)
        gsl_infnan = os.path.join(self.source_folder, "gsl-an", "sys", "infnan.c")
        if os.path.isfile(gsl_infnan):
            with open(gsl_infnan) as f:
                content = f.read()
            if "#define HAVE_DECL_FINITE 1" not in content:
                content = '#define HAVE_DECL_FINITE 1\n#define HAVE_DECL_ISNAN 1\n' + content
                with open(gsl_infnan, "w") as f:
                    f.write(content)
                self.output.info("gsl-an sys/infnan.c: added HAVE_DECL_FINITE+HAVE_DECL_ISNAN for OHOS/clang")
        # R04: Use conan gsl/2.8 as system GSL (skips broken vendored gsl-an entirely)
        gsl_dep = self.dependencies.get("gsl")
        if gsl_dep and gsl_dep.package_folder:
            # gsl.pc has prefix=/ (broken) — use package_folder directly for correct paths
            gsl_include = os.path.join(gsl_dep.package_folder, "include")
            gsl_lib = os.path.join(gsl_dep.package_folder, "lib")
            # Set PKG_CONFIG_PATH so pkg-config --atleast-version succeeds (SYSTEM_GSL=yes)
            pc_dir = os.path.join(gsl_dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(pc_dir):
                os.environ["PKG_CONFIG_PATH"] = pc_dir
            # Pass correct include/lib paths directly (bypass broken gsl.pc prefix=/)
            self.output.info(f"GSL include: {gsl_include}")
            self.output.info(f"GSL lib: {gsl_lib}")
            os.environ["CPPFLAGS"] = f"-I{gsl_include} " + os.environ.get("CPPFLAGS", "")
            os.environ["LDFLAGS"] = f"-L{gsl_lib} " + os.environ.get("LDFLAGS", "")
        # R07: Add bzip2/1.0.8 include/lib path directly (same pattern as GSL)
        bzip2_dep = self.dependencies.get("bzip2")
        if bzip2_dep and bzip2_dep.package_folder:
            bzip2_include = os.path.join(bzip2_dep.package_folder, "include")
            bzip2_lib = os.path.join(bzip2_dep.package_folder, "lib")
            self.output.info(f"bzip2 include: {bzip2_include}")
            os.environ["CPPFLAGS"] = f"-I{bzip2_include} " + os.environ.get("CPPFLAGS", "")
            os.environ["LDFLAGS"] = f"-L{bzip2_lib} " + os.environ.get("LDFLAGS", "")
        # R08: Add cfitsio/4.6.4 include/lib path directly (same pattern)
        cfitsio_dep = self.dependencies.get("cfitsio")
        if cfitsio_dep and cfitsio_dep.package_folder:
            cfitsio_include = os.path.join(cfitsio_dep.package_folder, "include")
            cfitsio_lib = os.path.join(cfitsio_dep.package_folder, "lib")
            self.output.info(f"cfitsio include: {cfitsio_include}")
            os.environ["CPPFLAGS"] = f"-I{cfitsio_include} " + os.environ.get("CPPFLAGS", "")
            os.environ["LDFLAGS"] = f"-L{cfitsio_lib} -lcfitsio " + os.environ.get("LDFLAGS", "")
            self.output.info(f"cfitsio LDFLAGS: -L{cfitsio_lib} -lcfitsio")
        # R08: Add zlib include/lib path (cfitsio zcompress needs deflate)
        zlib_dep = self.dependencies.get("zlib")
        if zlib_dep and zlib_dep.package_folder:
            zlib_include = os.path.join(zlib_dep.package_folder, "include")
            zlib_lib = os.path.join(zlib_dep.package_folder, "lib")
            self.output.info(f"zlib include: {zlib_include}")
            os.environ["CPPFLAGS"] = f"-I{zlib_include} " + os.environ.get("CPPFLAGS", "")
            os.environ["LDFLAGS"] = f"-L{zlib_lib} -lz " + os.environ.get("LDFLAGS", "")
        # R10: Add openssl include/lib path (openssl/ssl.h needed by astrometry.net source)
        openssl_dep = self.dependencies.get("openssl")
        if openssl_dep and openssl_dep.package_folder:
            openssl_include = os.path.join(openssl_dep.package_folder, "include")
            openssl_lib = os.path.join(openssl_dep.package_folder, "lib")
            self.output.info(f"openssl include: {openssl_include}")
            os.environ["CPPFLAGS"] = f"-I{openssl_include} " + os.environ.get("CPPFLAGS", "")
            os.environ["LDFLAGS"] = f"-L{openssl_lib} -lssl -lcrypto " + os.environ.get("LDFLAGS", "")
        # R13: Add cairo include/lib path (cairo.h needed by upstream test plot module)
        cairo_dep = self.dependencies.get("cairo")
        if cairo_dep and cairo_dep.package_folder:
            cairo_include = os.path.join(cairo_dep.package_folder, "include")
            cairo_lib = os.path.join(cairo_dep.package_folder, "lib")
            self.output.info(f"cairo include: {cairo_include}")
            # cairo.h lives in include/cairo/ subdir — add both roots
            os.environ["CPPFLAGS"] = f"-I{cairo_include} -I{cairo_include}/cairo " + os.environ.get("CPPFLAGS", "")
            os.environ["LDFLAGS"] = f"-L{cairo_lib} -lcairo " + os.environ.get("LDFLAGS", "")
        # R14: Add libpng include/lib path (png.h needed by cairoutils.c)
        libpng_dep = self.dependencies.get("libpng")
        if libpng_dep and libpng_dep.package_folder:
            libpng_include = os.path.join(libpng_dep.package_folder, "include")
            libpng_lib = os.path.join(libpng_dep.package_folder, "lib")
            self.output.info(f"libpng include: {libpng_include}")
            os.environ["CPPFLAGS"] = f"-I{libpng_include} " + os.environ.get("CPPFLAGS", "")
            os.environ["LDFLAGS"] = f"-L{libpng_lib} -lpng16 " + os.environ.get("LDFLAGS", "")
        # R33: get compiler from Conan conf (dict form, conan 2.29.1 compatible)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"
        ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"
        self.run(f"make CC={cc} CXX={cxx} AR={ar} -j1", cwd=self.source_folder)

    def package(self):
        # R09: Copy .a archives from all subdirectories (solver, util, libkd, catalogs, qfits-an, gsl-an)
        for sub in ["solver", "util", "libkd", "catalogs", "qfits-an", "gsl-an"]:
            src = os.path.join(self.source_folder, sub)
            for a_file in os.listdir(src):
                if a_file.endswith(".a"):
                    copy(self, a_file, src, os.path.join(self.package_folder, "lib"))
        # Also copy any .so if shared
        copy(self, "*.so*", self.source_folder, os.path.join(self.package_folder, "lib"))
        # Copy headers (astrometry.net has .h, .ph, .inc in include/astrometry/)
        copy(self, "*.h", os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"))
        copy(self, "*.*", os.path.join(self.source_folder, "include", "astrometry"),
             os.path.join(self.package_folder, "include", "astrometry"))

    def package_info(self):
        # R09: only list archives actually built (gsl-an is OPTIONAL — skipped when SYSTEM_GSL=yes)
        # Dependency order: high-level first, leaf last (static linker resolves right-to-left)
        self.cpp_info.libs = [
            "astrometry", "catalogs", "anfiles", "kd",
            "anutils", "qfits", "anbase",
        ]
        self.cpp_info.system_libs = ["m"]