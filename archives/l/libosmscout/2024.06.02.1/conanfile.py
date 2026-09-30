#!/usr/bin/env python3
"""Conan recipe for libosmscout 2024.06.02.1 on HarmonyOS PC (OHOS / aarch64).

libosmscout is an OpenStreetMap based offline vector map rendering, routing
and POI search library written in C++17.  The release tarball 2024.06.02.1
carries the internal library version 1.1.1 and bundles the map style sheet
compiler, the routing/POI/basemap databases and the GPX reader.

OHOS notes
----------
* Every optional dependency of the upstream CMake build is probed through
  ``find_package(<Dep> QUIET)`` and degrades silently when missing, so the
  package is built from a minimal, fully reproducible component set:
  core + map + map-svg + import + gpx + client + the test helper library.
  The Qt backends, the agg/cairo/OpenGL/DirectX raster backends, the demos
  and all command line tools stay OFF (their dependencies - Qt6, libagg,
  cairo, GLEW/GLM/Pango - are not required by the library itself).
* ``libxml2`` is the single external requirement.  It switches on the OSM
  XML reader (``PreprocessOSM``) and the GPX XML reader; without it the
  import library could only read PBF (needs protobuf) or ``.poly`` files.
* ``OSMSCOUT_BUILD_WITH_OPENMP`` is forced OFF *and* the ``OpenMP`` package
  lookup is disabled with ``CMAKE_DISABLE_FIND_PACKAGE_OpenMP``.  The option
  alone is not enough: the OHOS clang SDK ships libomp, so upstream's
  ``find_package(OpenMP QUIET)`` succeeds and ``libosmscout-import`` links
  ``OpenMP::OpenMP_CXX`` unconditionally (guarded only by target existence),
  which compiles the import library with ``-fopenmp`` regardless of the option
  and leaves ``__kmpc_*`` undefined for every consumer.  The import pipeline
  therefore runs single threaded; ``HAVE_STD_EXECUTION``/TBB stays negative as
  well.
* The upstream suite (52 ctest targets under ``Tests/``) is compiled and
  executed inside :meth:`build`.  A Conan 2 ``conan create`` never calls the
  recipe ``test()`` method, therefore "run the upstream suite" has to live
  in ``build()``.  The installed test executables are pruned again in
  :meth:`package` - shipping 52 unsigned OHOS binaries is pointless.
* ``CMAKE_FIND_PACKAGE_PREFER_CONFIG`` makes the ``find_package(LibXml2 QUIET)``
  probe in ``cmake/features.cmake`` resolve to the Conan package instead of
  a host CMake module.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)

# component -> (installed library name, upstream CMake target, component deps)
COMPONENTS = {
    "osmscout": ("osmscout", "OSMScout::OSMScout", []),
    "map": ("osmscout_map", "OSMScout::Map", ["osmscout"]),
    "map-svg": ("osmscout_map_svg", "OSMScout::MapSVG", ["map"]),
    "import": ("osmscout_import", "OSMScout::Import",
               ["osmscout", "libxml2::libxml2"]),
    "gpx": ("osmscout_gpx", "OSMScout::GPX",
            ["osmscout", "libxml2::libxml2"]),
    "client": ("osmscout_client", "OSMScout::Client", ["osmscout", "map"]),
    "test": ("osmscout_test", "OSMScout::Test", ["osmscout", "import"]),
}


class LibosmscoutConan(ConanFile):
    name = "libosmscout"
    version = "2024.06.02.1"
    description = ("OpenStreetMap based offline vector map rendering, routing "
                   "and POI search library")
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/Framstag/libosmscout"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        # Conan export_sources 机制：把 patches/ 一并导出到 recipe 缓存，
        # 否则 build()/package() 在缓存副本里找不到补丁文件。
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # libxml2 enables the OSM XML reader (PreprocessOSM) and the GPX XML
        # reader; both are guarded by `if(TARGET LibXml2::LibXml2)` upstream.
        self.requires("libxml2/2.15.3.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------
    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # no host CMake module may win over the Conan generated config files
        tc.variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = True

        # component selection (see module docstring)
        tc.variables["OSMSCOUT_BUILD_IMPORT"] = True
        tc.variables["OSMSCOUT_BUILD_GPX"] = True
        tc.variables["OSMSCOUT_BUILD_CLIENT"] = True
        tc.variables["OSMSCOUT_BUILD_TESTS"] = True
        tc.variables["OSMSCOUT_BUILD_MAP_SVG"] = True

        tc.variables["OSMSCOUT_BUILD_MAP_AGG"] = False
        tc.variables["OSMSCOUT_BUILD_MAP_CAIRO"] = False
        tc.variables["OSMSCOUT_BUILD_MAP_OPENGL"] = False
        tc.variables["OSMSCOUT_BUILD_MAP_QT"] = False
        tc.variables["OSMSCOUT_BUILD_CLIENT_QT"] = False

        tc.variables["OSMSCOUT_BUILD_DEMOS"] = False
        tc.variables["OSMSCOUT_BUILD_TOOL_IMPORT"] = False
        tc.variables["OSMSCOUT_BUILD_TOOL_DUMPDATA"] = False
        tc.variables["OSMSCOUT_BUILD_TOOL_PUBLICTRANSPORTMAP"] = False
        tc.variables["OSMSCOUT_BUILD_TOOL_OSMSCOUT2"] = False
        tc.variables["OSMSCOUT_BUILD_TOOL_OSMSCOUTOPENGL"] = False
        tc.variables["OSMSCOUT_BUILD_TOOL_STYLEEDITOR"] = False
        tc.variables["OSMSCOUT_BUILD_DOC_API"] = False
        tc.variables["OSMSCOUT_BUILD_WEBPAGE"] = False
        tc.variables["OSMSCOUT_BUILD_EXTERN_MATLAB"] = False

        # OpenMP: the OHOS clang SDK ships libomp, so upstream's
        # `find_package(OpenMP QUIET)` succeeds and `libosmscout-import`
        # *unconditionally* does `target_link_libraries(OSMScoutImport
        # OpenMP::OpenMP_CXX)` (it is only guarded by TARGET existence, not by
        # OSMSCOUT_BUILD_WITH_OPENMP).  That silently compiles the import
        # library with -fopenmp even when the option is OFF, and the resulting
        # archive is unusable for consumers because nothing provides the
        # __kmpc_* runtime.  Disabling the package lookup is therefore required
        # in addition to switching the option off.
        tc.variables["OSMSCOUT_BUILD_WITH_OPENMP"] = False
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_OpenMP"] = True
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    # ------------------------------------------------------------------
    def _ctest(self):
        """Locate ctest without relying on a bare-name lookup (OHOS posix_spawn)."""
        candidates = [
            os.environ.get("CTEST"),
            shutil.which("ctest"),
            "/data/service/hnp/bin/ctest",
        ]
        for cand in candidates:
            if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
        for entry in os.environ.get("PATH", "").split(os.pathsep):
            if not entry:
                continue
            cand = os.path.join(entry, "ctest")
            if os.path.isfile(cand):
                return cand
        raise ConanInvalidConfiguration("ctest could not be located on this host")

    def _run_upstream_tests(self):
        """Run the upstream ctest suite (layer 1 evidence, see module docstring)."""
        ctest = self._ctest()
        self.output.info("running upstream ctest suite: %s" % ctest)
        self.run('"%s" --output-on-failure --timeout 900 -j4' % ctest,
                 cwd=self.build_folder)

    # ------------------------------------------------------------------
    def package(self):
        cmake = CMake(self)
        cmake.install()

        # The upstream test macro installs its test executables below
        # share/osmscout/tests and the benchmark helper below
        # share/osmscout/demos.  Unsigned OHOS executables are unusable for
        # consumers (and would turn this library package into an application
        # one), so both directories are pruned again.
        for sub in ("tests", "demos"):
            extra_dir = os.path.join(self.package_folder, "share", "osmscout", sub)
            if os.path.isdir(extra_dir):
                rm(self, "*", extra_dir, recursive=True)
                os.rmdir(extra_dir)

        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    # ------------------------------------------------------------------
    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libosmscout")
        self.cpp_info.set_property("pkg_config_name", "libosmscout")

        for name, (output, target, requires) in COMPONENTS.items():
            comp = self.cpp_info.components[name]
            comp.libs = [output]
            comp.requires = list(requires)
            comp.set_property("cmake_target_name", target)
            comp.set_property("pkg_config_name", output)

        core = self.cpp_info.components["osmscout"]
        core.system_libs = ["m", "pthread"]
        # the map stylesheets are shipped as data, consumers need the path
        core.set_property(
            "libosmscout:stylesheets",
            os.path.join("share", "osmscout", "stylesheets"),
        )
