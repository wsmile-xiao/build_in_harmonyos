#!/usr/bin/env python3
"""Conan recipe for mongoc-driver 1.29.0 — MongoDB C driver.

The MongoDB C driver (libmongoc + libbson) provides a C API for
connecting to and working with MongoDB. Built as static libraries only
(shared lib has RPATH issues on OHOS with the Ninja generator).

Build system: CMake
Library output:
  - libbson-static-1.0.a  (BSON serialization)
  - libmongoc-static-1.0.a (MongoDB C driver)

Dependencies:
  - openssl/1.1.1w  (TLS)
  - zlib/1.3.1       (compression)
  - zstd/1.5.7       (compression)
  - snappy/1.2.2     (compression)
  - utf8proc         (bundled, SCRAM-SHA-256 non-ASCII passwords)
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class MongocDriverConan(ConanFile):
    name = "mongoc-driver"
    version = "1.29.0"
    description = "MongoDB C client driver (libmongoc + libbson)"
    license = "Apache-2.0"
    homepage = "https://mongoc.org/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "with_ssl": [True, False],
        "with_snappy": [True, False],
        "with_zstd": [True, False],
        "with_zlib": [True, False],
    }
    default_options = {
        "shared": False,
        "with_ssl": True,
        "with_snappy": True,
        "with_zstd": True,
        "with_zlib": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        if self.options.with_ssl:
            self.requires("openssl/1.1.1w")
        if self.options.with_zlib:
            self.requires("zlib/1.3.1")
        if self.options.with_zstd:
            self.requires("zstd/1.5.7")
        if self.options.with_snappy:
            self.requires("snappy/1.2.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Support local builds where GitHub may be unreachable:
        # check several locations for a pre-downloaded tarball before falling
        # back to the official URL. Also handle CI mirror fallback that
        # converts url from string to list format.
        import os
        from conan.tools.files import unzip
        src_data = self.conan_data["sources"]
        url = src_data.get("url", "")
        if isinstance(url, list):
            url = url[0] if url else ""
        filename = os.path.basename(url) if url else ""

        # 1. Source folder (Conan may have cached a partial download)
        candidates = []
        if filename:
            candidates.append(os.path.join(self.source_folder, filename))
        # 2. Directory pointed by MONGOC_LOCAL_SOURCE env var
        env_dir = os.environ.get("MONGOC_LOCAL_SOURCE", "")
        if env_dir and filename:
            candidates.append(os.path.join(env_dir, filename))
        # 3. Recipe folder parent (export cache layout: <hash>/e/ and <hash>/s/)
        if self.recipe_folder and filename:
            candidates.append(
                os.path.join(os.path.dirname(self.recipe_folder), "s", filename)
            )

        for local_file in candidates:
            if os.path.isfile(local_file) and os.path.getsize(local_file) > 1000000:
                unzip(self, local_file, strip_root=True)
                return

        get(self, **src_data, strip_root=True)

    def generate(self):
        import os
        from conan.tools.env import Environment

        # Create corrected pkg-config files for dependencies whose
        # upstream .pc files have a hardcoded prefix that doesn't match
        # the Conan package layout.
        pkgconfig_dir = os.path.join(self.build_folder, "pkgconfig")
        os.makedirs(pkgconfig_dir, exist_ok=True)

        env = Environment()

        if self.options.with_zstd:
            zstd = self.dependencies["zstd"]
            # Write a corrected libzstd.pc pointing to the Conan package
            zstd_pc = (
                f"prefix={zstd.package_folder}\n"
                f"exec_prefix=${{prefix}}\n"
                f"includedir=${{prefix}}/include\n"
                f"libdir=${{exec_prefix}}/lib\n"
                f"\n"
                f"Name: zstd\n"
                f"Description: fast lossless compression algorithm library\n"
                f"Version: {zstd.ref.version}\n"
                f"Libs: -L${{libdir}} -lzstd\n"
                f"Cflags: -I${{includedir}}\n"
            )
            with open(os.path.join(pkgconfig_dir, "libzstd.pc"), "w") as f:
                f.write(zstd_pc)
            env.prepend_path("PKG_CONFIG_PATH", pkgconfig_dir)

        envvars = env.vars(self)
        envvars.save_script("conanbuildenv")

        tc = CMakeToolchain(self)

        # OpenSSL: find_package(OpenSSL) uses OPENSSL_ROOT_DIR
        if self.options.with_ssl:
            openssl = self.dependencies["openssl"]
            tc.variables["OPENSSL_ROOT_DIR"] = openssl.package_folder

        # zlib: include(FindZLIB) uses ZLIB_ROOT
        if self.options.with_zlib:
            zlib_dep = self.dependencies["zlib"]
            tc.variables["ZLIB_ROOT"] = zlib_dep.package_folder

        # snappy: custom FindSnappy.cmake uses find_path/find_library
        prefix_paths = []
        if self.options.with_snappy:
            snappy = self.dependencies["snappy"]
            prefix_paths.append(snappy.package_folder)
        if prefix_paths:
            tc.variables["CMAKE_PREFIX_PATH"] = ";".join(prefix_paths)

        # Build options
        tc.variables["ENABLE_STATIC"] = "ON"
        tc.variables["ENABLE_SHARED"] = "OFF"
        tc.variables["ENABLE_TESTS"] = False
        tc.variables["ENABLE_EXAMPLES"] = False
        tc.variables["ENABLE_MAN_PAGES"] = False
        tc.variables["ENABLE_HTML_DOCS"] = False
        tc.variables["ENABLE_UNINSTALL"] = False
        tc.variables["ENABLE_CLIENT_SIDE_ENCRYPTION"] = "OFF"

        # Compression and TLS options
        tc.variables["ENABLE_SSL"] = "OPENSSL" if self.options.with_ssl else "OFF"
        tc.variables["ENABLE_SNAPPY"] = "ON" if self.options.with_snappy else "OFF"
        tc.variables["ENABLE_ZSTD"] = "ON" if self.options.with_zstd else "OFF"
        tc.variables["ENABLE_ZLIB"] = "SYSTEM" if self.options.with_zlib else "OFF"

        # Use bundled utf8proc (no external dependency needed)
        tc.variables["USE_BUNDLED_UTF8PROC"] = True

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["mongoc-static-1.0", "bson-static-1.0"]
        self.cpp_info.includedirs = [
            os.path.join("include", "libmongoc-1.0"),
            os.path.join("include", "libbson-1.0"),
        ]
        self.cpp_info.defines = ["MONGOC_STATIC", "BSON_STATIC"]
        self.cpp_info.set_property("cmake_file_name", "mongoc-driver")
        self.cpp_info.set_property("cmake_target_name", "mongoc-driver::mongoc-driver")
        if self.options.with_ssl:
            self.cpp_info.system_libs = ["dl", "pthread"]
