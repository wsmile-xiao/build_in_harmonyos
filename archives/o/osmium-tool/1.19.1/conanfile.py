#!/usr/bin/env python3
"""Conan recipe — osmium-tool 1.19.1 (CMake, CLI application).

osmium is a multipurpose command line tool based on the Osmium library for
working with OpenStreetMap data. It ships 23 sub-commands (cat, extract,
export, diff, merge, renumber, ...) and is a single executable.

OHOS notes
----------
* package_type = "application" — the deliverable is ``bin/osmium``.
* The upstream build uses its own *module-mode* find modules
  (``cmake/FindOsmium.cmake`` / ``FindProtozero.cmake`` / ``FindLZ4.cmake``)
  which only look at legacy ``*_INCLUDE_DIR`` / ``*_LIBRARY`` cache variables
  and never at Conan's imported targets. Those variables are injected from
  ``generate()`` so libosmium's five I/O dependencies (zlib/bzip2/lz4/expat/
  protozero) are all resolved to the Conan packages instead of host libraries.
* ``FindOsmium.cmake`` requires Osmium >= 2.23.1 and the registry only has
  libosmium/2.23.0, so libosmium 2.23.1 and protozero are downloaded as
  header-only vendored sources (see conandata.yml).
* ``cmake --install`` rewrites the RPATH of the executable, which invalidates
  the OHOS ``.codesign`` fs-verity hash and makes the binary unloadable, so
  ``package()`` copies the build-tree executable byte-for-byte instead.
"""
import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm


class OsmiumToolConan(ConanFile):
    name = "osmium-tool"
    version = "1.19.1"
    description = "Command line tool for working with OpenStreetMap data based on the Osmium library"
    license = "GPL-3.0-or-later"
    homepage = "https://osmcode.org/osmium-tool/"
    url = "https://github.com/osmcode/osmium-tool"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    options = {"with_lz4": [True, False]}
    default_options = {"with_lz4": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Boost program_options is a hard requirement (option parsing), see
        # CMakeLists.txt:64 (find_package(Boost CONFIG 1.55.0 REQUIRED
        # COMPONENTS program_options)).
        self.requires("boost/1.90.0.4")
        # command_export.cpp / command_export.hpp include <nlohmann/json.hpp>
        # unconditionally, so the headers are a build requirement.
        self.requires("nlohmann-json/3.11.2")
        # libosmium I/O dependencies (PBF: zlib + protozero(header-only) +
        # lz4; XML: expat + bzip2 + zlib).
        self.requires("zlib/1.3.1.1.1")
        self.requires("bzip2/1.0.8")
        self.requires("expat/2.8.2.1")
        if self.options.with_lz4:
            self.requires("lz4/1.10.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        vendored = self.conan_data["vendored"]
        for name in ("libosmium", "protozero"):
            dest = os.path.join(self.source_folder, "vendor", name)
            rm(self, "*", dest)
            get(self, **vendored[name], strip_root=True, destination=dest)

    # ------------------------------------------------------------------
    # dependency helpers (module-mode cache variables)
    # ------------------------------------------------------------------
    def _vendor_inc(self, name):
        return os.path.join(self.source_folder, "vendor", name, "include")

    def _dep_inc(self, name):
        dep = self.dependencies[name]
        inc = dep.cpp_info.includedirs[0] if dep.cpp_info.includedirs else "include"
        return os.path.join(dep.package_folder, inc).replace("\\", "/")

    def _dep_lib(self, name, stems):
        dep = self.dependencies[name]
        pkg = dep.package_folder
        libdirs = [os.path.join(pkg, d) for d in (dep.cpp_info.libdirs or ["lib"])]
        for stem in stems:
            for libdir in libdirs:
                for cand in ("lib%s.so" % stem, "lib%s.a" % stem):
                    path = os.path.join(libdir, cand)
                    if os.path.isfile(path):
                        return path.replace("\\", "/")
        for stem in stems:
            hits = []
            for libdir in libdirs:
                hits += sorted(glob.glob(os.path.join(libdir, "lib%s.*" % stem)))
            hits = [h for h in hits if not h.endswith((".la", ".dll.a"))]
            if hits:
                return hits[0].replace("\\", "/")
        raise ConanException("library for '%s' (%s) not found in Conan package" % (name, stems))

    def generate(self):
        osmium_inc = self._vendor_inc("libosmium")
        protozero_inc = self._vendor_inc("protozero")
        for path, header in ((osmium_inc, "osmium/version.hpp"),
                             (protozero_inc, "protozero/version.hpp")):
            if not os.path.isfile(os.path.join(path, header)):
                raise ConanException("vendored header %s not found under %s" % (header, path))

        zlib_inc = self._dep_inc("zlib")
        zlib_lib = self._dep_lib("zlib", ("z",))
        expat_inc = self._dep_inc("expat")
        expat_lib = self._dep_lib("expat", ("expat",))
        bzip2_inc = self._dep_inc("bzip2")
        bzip2_lib = self._dep_lib("bzip2", ("bz2",))
        nlohmann_inc = self._dep_inc("nlohmann-json")

        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["USE_CPP_VERSION"] = "17"
        tc.variables["WITH_LZ4"] = "ON" if self.options.with_lz4 else "OFF"

        # Header-only vendored dependencies.
        tc.cache_variables["OSMIUM_INCLUDE_DIR"] = osmium_inc
        tc.cache_variables["PROTOZERO_INCLUDE_DIR"] = protozero_inc
        tc.cache_variables["NLOHMANN_INCLUDE_DIR"] = nlohmann_inc

        # Module-mode find modules used by cmake/FindOsmium.cmake. Conan's
        # toolchain sets CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON, so zlib/bzip2/
        # expat/lz4 are resolved through the generated *-config.cmake files,
        # which only define lowercase variables and imported targets. The
        # upstream build still consumes the legacy UPPERCASE variables, so the
        # ones the generated configs do not provide are injected here.
        tc.cache_variables["ZLIB_INCLUDE_DIR"] = zlib_inc
        tc.cache_variables["ZLIB_LIBRARY"] = zlib_lib
        tc.cache_variables["ZLIB_LIBRARY_RELEASE"] = zlib_lib
        tc.cache_variables["ZLIB_LIBRARIES"] = zlib_lib
        tc.cache_variables["EXPAT_INCLUDE_DIR"] = expat_inc
        tc.cache_variables["EXPAT_LIBRARY"] = expat_lib
        tc.cache_variables["EXPAT_LIBRARIES"] = expat_lib
        tc.cache_variables["BZIP2_INCLUDE_DIR"] = bzip2_inc
        tc.cache_variables["BZIP2_LIBRARY"] = bzip2_lib
        tc.cache_variables["BZIP2_LIBRARIES"] = bzip2_lib
        tc.cache_variables["BZIP2_LIBRARY_RELEASE"] = bzip2_lib
        if self.options.with_lz4:
            lz4_inc = self._dep_inc("lz4")
            lz4_lib = self._dep_lib("lz4", ("lz4",))
            # osmium-tool itself consumes the plural spellings
            # (CMakeLists.txt: include_directories(${LZ4_INCLUDE_DIRS}) and
            # list(APPEND OSMIUM_LIBRARIES ${LZ4_LIBRARIES})).
            tc.cache_variables["LZ4_INCLUDE_DIR"] = lz4_inc
            tc.cache_variables["LZ4_INCLUDE_DIRS"] = lz4_inc
            tc.cache_variables["LZ4_LIBRARY"] = lz4_lib
            tc.cache_variables["LZ4_LIBRARIES"] = lz4_lib

        tc.generate()
        CMakeDeps(self).generate()

    # ------------------------------------------------------------------
    # upstream test suite
    # ------------------------------------------------------------------
    def _ctest(self):
        cmake = self.conf.get("tools.cmake:cmake_program", default="cmake")
        cmake_bin = shutil.which(cmake) or cmake
        cand = os.path.join(os.path.dirname(cmake_bin), "ctest")
        if os.path.isfile(cand):
            return cand
        found = shutil.which("ctest")
        if found:
            return found
        raise ConanException("ctest not found")

    def _run_upstream_tests(self):
        # The upstream suite is plain CTest: one Catch2 `unit_tests` binary plus
        # per-command output-comparison tests that invoke the just-built
        # `osmium` executable (wired through $<TARGET_FILE:osmium>).
        # LD_LIBRARY_PATH for shared dependencies (expat) comes from the
        # `conanrun` environment.
        cmd = "%s --output-on-failure" % shlex.quote(self._ctest())
        self.run(cmd, cwd=self.build_folder, env="conanrun")
        self.output.info("UPSTREAM TESTS: ctest completed successfully")

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def package(self):
        # Byte-for-byte copy of the build-tree executable: `cmake --install`
        # rewrites the RPATH which invalidates the OHOS `.codesign` fs-verity
        # hash and makes the binary fail to load (EPERM).
        src_exe = os.path.join(self.build_folder, "src", "osmium")
        if not os.path.isfile(src_exe):
            raise ConanException("built executable not found at %s" % src_exe)
        copy(self, "osmium", src=os.path.dirname(src_exe),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
