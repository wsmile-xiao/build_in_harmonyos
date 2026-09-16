#!/usr/bin/env python3
"""Conan recipe — mapnik 4.2.2 (CMake)

Mapnik C++ mapping toolkit (rendering library + datasource plugins).

OHOS adaptation notes:
- CMake >= 3.30 required upstream; system cmake 4.1.2 is fine.
- Upstream find_package module targets are re-wired to conan CMakeDeps
  config targets via patches 0001/0003 (icu4c, freetype, libpng,
  libjpeg-turbo, libtiff, WebP, libavif, cairo, sqlite3, libpq).
- harfbuzz conan package exposes headers as <hb.h> (includedirs
  include/harfbuzz), patched via 0002.
- boost/1.91.0.1.3 is a tailored closure without the header-only
  Boost.Geometry/Gil/Msm libraries mapnik requires; they are vendored
  from the official boost-1.91.0 tarball into deps/boost_extra during
  build() (see _vendor_boost_headers).
- boost::assign was removed in Boost 1.87; patched away in 0005.
- Upstream tests use Catch2 v2.13.7 via FetchContent (network); the
  release tarball ships the same vendored test/catch.hpp single header,
  so the FetchContent is replaced by an INTERFACE target (0004).
- PROJ is disabled (ohpcd proj 9.3.1.1 < upstream minimum 9.4.0);
  gdal/ogr/postgis/pgraster/tiles plugins are disabled to shrink the
  dependency surface (tiles additionally needs Boost::url/context which
  the conan boost closure does not provide). All affected code paths
  have upstream compile-time guards; the datasource tests have runtime
  plugin_registered() guards.
- std::cmp_equal (C++20 <utility>) is not available in the OHOS libc++
  (clang 15); test-only usages are replaced with plain comparisons (0004).
"""
import hashlib
import os
import subprocess
import tarfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, download, export_conandata_patches, get


class MapnikConan(ConanFile):
    name = "mapnik"
    version = "4.2.2"
    description = "Mapnik is an open source toolkit for developing mapping applications"
    license = "LGPL-2.1-or-later"
    homepage = "https://mapnik.org/"
    url = "https://github.com/mapnik/mapnik"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_cairo": [True, False],
        "with_libxml2": [True, False],
        "with_png": [True, False],
        "with_jpeg": [True, False],
        "with_tiff": [True, False],
        "with_webp": [True, False],
        "with_avif": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "with_cairo": True,
        "with_libxml2": True,
        "with_png": True,
        "with_jpeg": True,
        "with_tiff": True,
        "with_webp": True,
        "with_avif": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # zlib/1.3.1.1 ecosystem (libpng/1.6.58 + libtiff/4.7.2 + cairo/1.18.4
        # all pin zlib/1.3.1.1; freetype is pinned to 2.14.3 by harfbuzz).
        self.requires("icu4c/78")
        self.requires("boost/1.91.0.1.3")
        self.requires("freetype/2.14.3")
        self.requires("harfbuzz/14.3.0")
        self.requires("zlib/1.3.1.1")
        if self.options.with_libxml2:
            self.requires("libxml2/2.15.3.1")
        if self.options.with_png:
            self.requires("libpng/1.6.58")
        if self.options.with_jpeg:
            self.requires("libjpeg-turbo/3.2.0")
        if self.options.with_tiff:
            self.requires("libtiff/4.7.2")
        if self.options.with_webp:
            self.requires("libwebp/1.6.0")
        if self.options.with_avif:
            self.requires("libavif/1.4.2.2")
        if self.options.with_cairo:
            self.requires("cairo/1.18.4")
        # sqlite3 plugin + pgsql2sqlite utility
        self.requires("sqlite3/3.53.4")
        # unit test sources include plugins/input/postgis headers which
        # include <libpq-fe.h>; upstream test/CMakeLists links
        # PostgreSQL::PostgreSQL unconditionally.
        self.requires("libpq/18.6")
        # NOTE: upstream tests use the vendored test/catch.hpp single header
        # (Catch2 v2.13.7, same version upstream pins via FetchContent), so
        # no conan catch2 dependency is needed.

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        # The official mapnik-v4.2.2.tar.bz2 is a macOS-authored archive: it
        # contains AppleDouble "._*" metadata entries (and a "._mapnik-4.2.2"
        # root entry) which break conan's get(strip_root=True) root detection.
        # Unpack manually, dropping the AppleDouble files.
        import bz2
        import shutil as _sh
        data = self.conan_data["sources"]["mapnik"]
        archive = os.path.join(self.source_folder, "mapnik.tar")
        download(self, data["url"], archive + ".bz2", verify=False,
                 retry=5, retry_wait=10)
        with bz2.open(archive + ".bz2", "rb") as fin, open(archive, "wb") as fout:
            _sh.copyfileobj(fin, fout)
        import tarfile as _tf
        with _tf.open(archive, "r:") as tf:
            members = [m for m in tf.getmembers()
                       if "/._" not in m.name and not m.name.startswith("._")]
            tf.extractall(self.source_folder, members=members)
        os.remove(archive)
        os.remove(archive + ".bz2")
        # flatten the single root directory into the source root
        roots = [d for d in os.listdir(self.source_folder)
                 if os.path.isdir(os.path.join(self.source_folder, d))
                 and d not in ("test",)]
        # pick the archive root (the only dir not created by conan)
        archive_root = None
        for d in roots:
            if os.path.exists(os.path.join(self.source_folder, d, "CMakeLists.txt")):
                archive_root = d
                break
        if archive_root is None and len(roots) == 1:
            archive_root = roots[0]
        if archive_root:
            root = os.path.join(self.source_folder, archive_root)
            for entry in os.listdir(root):
                os.rename(os.path.join(root, entry),
                          os.path.join(self.source_folder, entry))
            os.rmdir(root)
        # test/data is an empty submodule directory in the release tarball;
        # populate it from the exact upstream commit referenced by v4.2.2.
        get(self, **self.conan_data["sources"]["test_data"], strip_root=True,
            destination=os.path.join(self.source_folder, "test", "data"))

    def _vendor_boost_headers(self):
        """Vendor the header-only Boost.Geometry/Gil/Msm libraries (absent
        from the tailored conan boost closure) from the official boost
        tarball into deps/boost_extra. Only the needed subtrees are
        extracted from the archive."""
        data = self.conan_data["sources"]["boost_headers"]
        dest = os.path.join(self.source_folder, "deps", "boost_extra")
        os.makedirs(dest, exist_ok=True)
        archive = os.path.join(self.build_folder, "boost-headers.tar.xz")
        download(self, data["url"], archive, verify=False)
        actual = hashlib.sha256(open(archive, "rb").read()).hexdigest()
        if actual != data["sha256"]:
            raise ConanInvalidConfiguration(
                "boost headers archive sha256 mismatch: got %s" % actual)
        members = (
            "geometry", "geometry.hpp",
            "gil", "gil.hpp",
            "msm",
            "qvm",
            "format", "format.hpp",
            "rational.hpp",
            "circular_buffer.hpp", "circular_buffer_fwd.hpp",
        )
        root = data["root"]  # e.g. "boost-1.91.0-1/boost"
        prefix = root + "/"
        # members land under deps/boost_extra/boost/<member>
        boost_dest = os.path.join(dest, "boost")
        with tarfile.open(archive, "r:xz") as tf:
            wanted = []
            for x in tf.getmembers():
                rel = x.name[len(prefix):] if x.name.startswith(prefix) else None
                if rel is None:
                    continue
                if rel in members or any(rel.startswith(m + "/") for m in members):
                    x.name = rel
                    wanted.append(x)
            tf.extractall(boost_dest, members=wanted)
        self.output.info("vendored boost headers -> deps/boost_extra/boost")

    def generate(self):
        # ── 依赖 CMake 命名适配 ──
        # icu4c conan package has no cmake_file_name/target properties; expose
        # the config file + target names mapnik's patched CMakeLists expects.
        icu = self.dependencies["icu4c"].cpp_info
        icu.set_property("cmake_file_name", "icu4c")
        icu.set_property("cmake_target_name", "icu4c::icu4c")

        # libpq package has no cmake config properties; patched sources call
        # find_package(libpq CONFIG REQUIRED).
        libpq = self.dependencies["libpq"].cpp_info
        libpq.set_property("cmake_file_name", "libpq")
        libpq.set_property("cmake_target_name", "libpq::libpq")

        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "BOTH"
        # ── plugin/feature switches (OHOS dependency surface) ──
        tc.variables["USE_PROJ"] = False                 # ohpcd proj 9.3.1.1 < 9.4.0 minimum
        tc.variables["USE_PLUGIN_INPUT_GDAL_OGR"] = False
        tc.variables["USE_PLUGIN_INPUT_POSTGIS_PGRASTER"] = False
        tc.variables["USE_PLUGIN_INPUT_TILES"] = False    # needs Boost::url/context (excluded from conan boost closure)
        tc.variables["USE_PLUGIN_INPUT_CSV"] = True
        tc.variables["USE_PLUGIN_INPUT_GEOBUF"] = True
        tc.variables["USE_PLUGIN_INPUT_GEOJSON"] = True
        tc.variables["USE_PLUGIN_INPUT_RASTER"] = True
        tc.variables["USE_PLUGIN_INPUT_SHAPE"] = True
        tc.variables["USE_PLUGIN_INPUT_SQLITE"] = True
        tc.variables["USE_PLUGIN_INPUT_TOPOJSON"] = True
        tc.variables["USE_CAIRO"] = bool(self.options.with_cairo)
        tc.variables["USE_LIBXML2"] = bool(self.options.with_libxml2)
        tc.variables["USE_PNG"] = bool(self.options.with_png)
        tc.variables["USE_JPEG"] = bool(self.options.with_jpeg)
        tc.variables["USE_TIFF"] = bool(self.options.with_tiff)
        tc.variables["USE_WEBP"] = bool(self.options.with_webp)
        tc.variables["USE_AVIF"] = bool(self.options.with_avif)
        tc.variables["USE_GRID_RENDERER"] = True
        tc.variables["USE_SVG_RENDERER"] = True
        tc.variables["USE_MEMORY_MAPPED_FILE"] = True
        # ── build what's needed only ──
        tc.variables["BUILD_DEMO_VIEWER"] = False        # needs Qt
        tc.variables["BUILD_DEMO_CPP"] = False
        tc.variables["BUILD_BENCHMARK"] = False
        tc.variables["BUILD_TESTING"] = True             # upstream tests (catch2 based)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["BUILD_SHARED_PLUGINS"] = bool(self.options.shared)
        tc.variables["INSTALL_DEPENDENCIES"] = False
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._vendor_boost_headers()
        cmake = CMake(self)
        cmake.configure()
        # Build library + plugins + tests (upstream test binaries are the
        # validation vehicle; they are registered via ctest in the build tree).
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "mapnik")
        self.cpp_info.set_property("cmake_target_name", "mapnik::mapnik")
        self.cpp_info.set_property("pkg_config_name", "mapnik")
        self.cpp_info.libs = ["mapnik"]
        # json/wkt helper libs (built as part of mapnik, STATIC upstream)
        self.cpp_info.libs += ["mapnikjson", "mapnikwkt"]
        # propagate runtime deps so consumers' CMakeDeps/PkgConfigDeps can
        # resolve mapnik's link closure
        # NOTE: entries are <conan-pkg>::<component> as declared by the
        # dependency recipes (component-less packages use <pkg>::<pkg>).
        reqs = ["boost::headers", "icu4c::icu4c", "freetype::freetype",
                "harfbuzz::harfbuzz", "sqlite3::sqlite3", "libpq::libpq",
                "zlib::zlib"]
        if self.options.with_libxml2:
            reqs.append("libxml2::libxml2")
        if self.options.with_png:
            reqs.append("libpng::libpng")
        if self.options.with_jpeg:
            reqs.append("libjpeg-turbo::libjpeg-turbo")
        if self.options.with_tiff:
            reqs.append("libtiff::libtiff")
        if self.options.with_webp:
            reqs.append("libwebp::libwebp")
        if self.options.with_avif:
            reqs.append("libavif::libavif")
        if self.options.with_cairo:
            reqs.append("cairo::cairo")
        self.cpp_info.requires = reqs
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "dl", "m"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_find_mode", "both")
