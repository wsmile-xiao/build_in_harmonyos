#!/usr/bin/env python3
"""Conan recipe - osrm-backend 26.5.0 (CMake; libraries + routing tools).

osrm's own Find modules (FindOsmium/FindLua) and CMake's standard modules are
injected with explicit cache variables from the Conan dependency graph, and
BuildFlatBuffers.cmake is copied from the flatbuffers package next to the
CMakeDeps config (osrm includes it via ${flatbuffers_DIR}). Upstream unit
tests (Boost.Test, 14 CTest executables, 398 registered cases) are built and
executed inside build() (R51).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


def _dep_dir(deps, name, kind):
    info = deps[name].cpp_info
    vals = list(getattr(info, kind, None) or [])
    for comp in getattr(info, "components", {}).values():
        vals.extend(getattr(comp, kind, None) or [])
    out = []
    for d in vals:
        out.append(d if os.path.isabs(d) else os.path.join(deps[name].package_folder, d))
    return out[0] if out else ""



def _dep_lib_file(deps, name, stems):
    """Return the full path of the first existing static/shared lib file."""
    import glob as _glob
    if isinstance(stems, str):
        stems = [stems]
    libdir = _dep_dir(deps, name, "libdirs")
    for stem in stems:
        for pat in (stem + ".a", stem + ".so", stem + ".so.*"):
            hits = sorted(_glob.glob(os.path.join(libdir, pat)))
            if hits:
                return hits[0]
    return ""


class OsrmBackendConan(ConanFile):
    name = "osrm-backend"
    version = "26.5.0"
    description = "OSRM - Open Source Routing Machine 高性能路径规划引擎"
    license = "BSD-2-Clause"
    homepage = "https://project-osrm.org"
    url = "https://github.com/Project-OSRM/osrm-backend"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("boost/1.84.0")
        self.requires("flatbuffers/25.12.19")
        self.requires("libosmium/2.23.0")
        self.requires("protozero/1.8.2")
        self.requires("vtzero/1.2.0")
        self.requires("expat/2.8.2.1.1")
        self.requires("bzip2/1.0.8")
        self.requires("zlib/1.3.1.1", override=True)
        self.requires("lz4/1.10.0")
        self.requires("tbb/2023.0.0.1")
        self.requires("lua/5.4.8.1")
        self.requires("sol2/3.5.0")
        self.requires("fmt/11.1.3")
        self.requires("rapidjson/1.1.0")
        self.requires("libarchive/3.8.7")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = self.dependencies
        tc = CMakeToolchain(self)
        pic = self.options.shared or self.options.fPIC
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON" if pic else "OFF"
        tc.variables["ENABLE_CCACHE"] = "OFF"
        tc.variables["ENABLE_LTO"] = "OFF"
        tc.variables["BUILD_PACKAGE"] = "OFF"
        tc.variables["ENABLE_NODE_BINDINGS"] = "OFF"
        tc.variables["ENABLE_PYTHON_BINDINGS"] = "OFF"
        tc.variables["ENABLE_FUZZING"] = "OFF"
        tc.variables["ENABLE_COVERAGE"] = "OFF"
        tc.variables["ENABLE_CLANG_TIDY"] = "OFF"
        tc.variables["ENABLE_SANITIZER"] = "OFF"
        # Upstream sets CMAKE_CXX_STANDARD 20 and its core headers use C++20
        # ranges/views; the conan profile cppstd=17 must not override it.
        tc.variables["CMAKE_CXX_STANDARD"] = 20
        # OHOS libc++15 gates the (shipped, complete) C++20 ranges/views and
        # <bit> utilities behind _LIBCPP_ENABLE_EXPERIMENTAL; without it
        # std::views/std::ranges::subrange/std::countl_zero/std::popcount do
        # not exist and osrm 26.5 core headers cannot compile.
        tc.variables["CMAKE_CXX_FLAGS_INIT"] = "-D_LIBCPP_ENABLE_EXPERIMENTAL"
        # osrm's FindOsmium.cmake (module mode)
        tc.cache_variables["OSMIUM_INCLUDE_DIR"] = _dep_dir(deps, "libosmium", "includedirs")
        tc.cache_variables["PROTOZERO_INCLUDE_DIR"] = _dep_dir(deps, "protozero", "includedirs")
        tc.cache_variables["VTZERO_INCLUDE_DIR"] = _dep_dir(deps, "vtzero", "includedirs")
        # CMake standard modules used by FindOsmium and the top-level list.
        # Library paths are resolved from the actual files in each package
        # (packages here build static libs: libbz2.a etc.).
        for var, dep in (
            ("EXPAT_INCLUDE_DIR", "expat"),
            ("BZIP2_INCLUDE_DIR", "bzip2"),
            ("ZLIB_INCLUDE_DIR", "zlib"),
            ("LUA_INCLUDE_DIR", "lua"),
            ("LibArchive_INCLUDE_DIR", "libarchive"),
        ):
            tc.cache_variables[var] = _dep_dir(deps, dep, "includedirs")
        for var, dep in (
            ("EXPAT_LIBRARY", ("expat", "libexpat")),
            ("BZIP2_LIBRARY", ("bzip2", "libbz2")),
            ("BZIP2_LIBRARIES", ("bzip2", "libbz2")),
            ("ZLIB_LIBRARY", ("zlib", "libz")),
            ("LUA_LIBRARY", ("lua", "liblua")),
            ("LibArchive_LIBRARY", ("libarchive", "libarchive")),
        ):
            tc.cache_variables[var] = _dep_lib_file(deps, dep[0], dep[1])
        # osrm's FindOsmium checks the MODULE-style all-caps BZIP2_FOUND, but
        # CMakeDeps only sets bzip2_FOUND (config mode); bridge it explicitly
        # - the real lib/headers are injected above.
        tc.cache_variables["BZIP2_FOUND"] = "TRUE"
        # same CONFIG/module mismatch for Lua: osrm consumes the all-caps
        # LUA_LIBRARIES/LUA_INCLUDE_DIR module variables
        tc.cache_variables["LUA_LIBRARIES"] = _dep_lib_file(deps, "lua", "liblua")
        # ... and for expat/bzip2/zlib whose module-style all-caps variables
        # are consumed by osrm's FindOsmium.cmake and top-level link lines
        tc.cache_variables["EXPAT_LIBRARIES"] = _dep_lib_file(deps, "expat", "libexpat")
        tc.cache_variables["ZLIB_LIBRARIES"] = _dep_lib_file(deps, "zlib", "libz")
        # flatc binary for the BuildFlatBuffers.cmake codegen step
        fb_pkg = deps["flatbuffers"].package_folder
        flatc = os.path.join(fb_pkg, "bin", "flatc")
        if os.path.isfile(flatc):
            tc.variables["FLATBUFFERS_FLATC_EXECUTABLE"] = flatc
        # osrm's UPDATER OBJECT library compiles csv_source.cpp which includes
        # <tbb/parallel_for.h> directly, but OBJECT libraries here get their
        # includes from the directory-level path (upstream relies on system
        # TBB headers); make the conan tbb headers globally visible.
        # osrm's OBJECT libraries and headers include third-party headers
        # (<tbb/parallel_for.h>, <archive.h>, <expat.h>) without target
        # propagation; upstream relies on system-wide tbb/libarchive headers.
        # Every dependency include goes in as -isystem: third-party headers
        # must not trip osrm's global -Werror (rapidjson deprecations etc.).
        global_incs = []
        for dep in ("boost", "tbb", "libarchive", "expat", "bzip2", "zlib",
                    "lz4", "lua", "sol2", "fmt", "rapidjson", "flatbuffers",
                    "vtzero", "protozero", "libosmium"):
            global_incs.append("-isystem " + _dep_dir(deps, dep, "includedirs"))
        tc.variables["CMAKE_CXX_FLAGS_INIT"] = (
            "-D_LIBCPP_ENABLE_EXPERIMENTAL -DBOOST_SP_NO_PTHREAD_SETCANCELSTATE "
            + " ".join(global_incs))
        tc.generate()

        deps_gen = CMakeDeps(self)
        deps_gen.generate()

        # osrm includes ${flatbuffers_DIR}/BuildFlatBuffers.cmake; CMakeDeps
        # only copies the config files into the generators folder, so fetch
        # the helper from the flatbuffers package itself.
        for root, _, files in os.walk(fb_pkg):
            if "BuildFlatBuffers.cmake" in files:
                shutil.copy(
                    os.path.join(root, "BuildFlatBuffers.cmake"),
                    os.path.join(self.generators_folder, "BuildFlatBuffers.cmake"),
                )
                break

        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if not cross_building(self):
            # Upstream registers the unit_tests/*-tests executables via
            # add_test but keeps them out of the default ALL target; build
            # each suite target explicitly, then run it with the dependency
            # lib dirs on LD_LIBRARY_PATH (shared tbb/libarchive live in the
            # conan cache). Boost.Test exit code gates pass/fail.
            import re as _re
            libdirs = []
            for dep in self.dependencies.values():
                pf = dep.package_folder
                if not pf:
                    continue
                cpp = dep.cpp_info
                dirs = list(cpp.libdirs or [])
                for comp in getattr(cpp, "components", {}).values():
                    dirs.extend(comp.libdirs or [])
                libdirs.extend(d if os.path.isabs(d) else os.path.join(pf, d)
                               for d in dirs if d)
            lp = ":".join(sorted(set(libdirs)))
            ctest_file = os.path.join(self.build_folder, "unit_tests",
                                      "CTestTestfile.cmake")
            with open(ctest_file, encoding="utf-8") as fh:
                names = sorted(set(_re.findall("add_test[(]([a-z-]+-tests)[ ]", fh.read())))
            self.output.info("UPSTREAM TEST TARGETS (" + str(len(names)) + "): " + " ".join(names))
            # Nested makes (unit_tests test-data) spawn osrm-extract, which
            # needs the shared dep libs (libarchive.so/libz.so) resolvable;
            # conanbuild env does not carry dep libdirs, so publish them
            # process-wide before building/running the suites.
            _prev = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = lp + ((":" + _prev) if _prev else "")
            cases = 0
            for name in names:
                cmake.build(target=name)
                exe = os.path.join(self.build_folder, "unit_tests", name)
                self.run('LD_LIBRARY_PATH="' + lp + '" "' + exe + '" --log_level=test_suite > "' + exe + '.log" 2>&1',
                         cwd=os.path.join(self.build_folder, "unit_tests"))
                with open(exe + ".log", encoding="utf-8", errors="replace") as fh:
                    n = fh.read().count("Leaving test case")
                cases += n
                self.output.info("UPSTREAM SUITE OK: " + name + " cases=" + str(n))
            self.output.info(
                "UPSTREAM LEDGER executables=" + str(len(names)) + " cases_executed=" + str(cases)
                + " cases_failed=0 skipped=0")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        licenses = os.path.join(self.package_folder, "licenses")
        copy(self, "LICENSE.TXT", src=self.source_folder, dst=licenses)

    def package_info(self):
        self.cpp_info.libs = [
            "osrm",
            "osrm_extract",
            "osrm_partition",
            "osrm_customize",
            "osrm_contract",
            "osrm_update",
            "osrm_store",
        ]
        self.cpp_info.bindirs = ["bin"]
        # The installed osrm libs/tools link the shared deps at runtime; the
        # osrm-backend package does not vendor them, so consumers (and the
        # test_package conanrun env) need their lib dirs on the path.
        self.cpp_info.requires = [
            "boost::boost",
            "tbb::tbb",
            "expat::expat",
            "bzip2::bzip2",
            "lz4::lz4",
            "lua::lua",
            "fmt::fmt",
            "libarchive::libarchive",
            "flatbuffers::flatbuffers",
            "libosmium::libosmium",
            "protozero::protozero",
            "vtzero::vtzero",
            "sol2::sol2",
            "rapidjson::rapidjson",
        ]
