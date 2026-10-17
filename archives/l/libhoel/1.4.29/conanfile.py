# conanfile.py — libhoel 1.4.29
# HarmonyOS PC adaptation (babelouest database abstraction library, ulfius chain)
import os
import subprocess

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rmdir
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.microsoft import is_msvc

required_conan_version = ">=1.52.0"


class HoelConan(ConanFile):
    name = "libhoel"
    version = "1.4.29"
    description = "C Database abstraction library with json based language"
    homepage = "https://github.com/babelouest/hoel/"
    topics = ("database", "json", "sql", "abstraction")
    license = "LGPL-2.1-or-later"
    url = "https://github.com/babelouest/hoel"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_sqlite3": [True, False],
        "with_mariadb": [True, False],
        "with_pgsql": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_sqlite3": True,
        "with_mariadb": False,
        "with_pgsql": False,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            try:
                del self.options.fPIC
            except Exception:
                pass
        try:
            del self.settings.compiler.libcxx
        except Exception:
            pass
        try:
            del self.settings.compiler.cppstd
        except Exception:
            pass

    def requirements(self):
        # hoel has hard runtime dependencies on orcania (o_malloc/o_free/
        # split_string used throughout src/hoel.c), yder (y_log_message
        # error paths, hoel.h includes <yder.h>) and jansson (json_t based
        # query language). All three are published on the ohpcd registry
        # (W0 verified with conan download).
        self.requires("orcania/2.3.3")
        self.requires("libyder/1.4.20")
        self.requires("jansson/2.14")
        if self.options.with_sqlite3:
            self.requires("sqlite3/3.53.4")

    def build_requirements(self):
        # check/0.15.2 (published on ohpcd) is needed to build and run the
        # upstream CTest suite (core + multi, 21 official check cases). It is
        # a test-only requirement: available to this recipe while building/
        # running the upstream tests, never propagated to consumers and not
        # part of the package_id. Same pattern as the repo precedent
        # (orcania 2.3.3, libyder 1.4.20).
        if not self.options.shared:
            self.test_requires("check/0.15.2")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            destination=self.source_folder, strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED"] = False  # upstream always builds the shared target too
        tc.variables["BUILD_STATIC"] = not self.options.shared
        tc.variables["WITH_SQLITE3"] = self.options.with_sqlite3
        tc.variables["WITH_MARIADB"] = self.options.with_mariadb
        tc.variables["WITH_PGSQL"] = self.options.with_pgsql
        tc.variables["BUILD_HOEL_TESTING"] = False  # toggled in build()
        tc.variables["BUILD_HOEL_DOCUMENTATION"] = False
        tc.variables["BUILD_RPM"] = False
        tc.variables["INSTALL_HEADER"] = True
        tc.generate()
        # CMakeDeps generates OrcaniaConfig.cmake / YderConfig.cmake /
        # janssonConfig.cmake / sqlite3-config.cmake for the host
        # requirements. Jansson/sqlite3/check are deliberately NOT part of
        # the CMakeDeps pass for the bundled find-modules: upstream resolves
        # them through its own cmake-modules (MODULE mode, see the
        # portability patch), seeded with the conan package paths in
        # build(). orcania/libyder HAVE no bundled module upstream, so they
        # resolve through CMakeDeps config files.
        deps = CMakeDeps(self)
        deps.generate()

    def _dep_folder(self, name):
        try:
            dep = self.dependencies.get(name)
        except Exception:
            dep = None
        return dep.package_folder if dep else ""

    def _patch_sources(self):
        apply_conandata_patches(self)

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        check_pkg = self._dep_folder("check")
        # Run the unmodified upstream CTest suite (core + multi, 21 check
        # cases; upstream registers them EXCLUDE_FROM_ALL) for the static
        # build the recipe defaults to, and only when the conan check
        # dependency is present.
        enable_upstream_tests = bool(check_pkg) and not self.options.shared
        cfg_vars = {"BUILD_HOEL_TESTING": "ON" if enable_upstream_tests else "OFF"}
        if enable_upstream_tests:
            # Seed hoel's bundled cmake-modules/FindCheck.cmake with the conan
            # check package paths. The recipe's portability patch forces
            # find_package(Check MODULE) so the bundled module (CHECK_FOUND /
            # Check::Check) runs even though the conan toolchain sets
            # CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON. Never fall back to a host
            # /usr same-name lib.
            cfg_vars["CHECK_INCLUDE_DIR"] = os.path.join(check_pkg, "include")
            cfg_vars["CHECK_LIBRARY"] = os.path.join(check_pkg, "lib", "libcheck.a")
        # Jansson: hoel's bundled FindJansson.cmake (MODULE mode after the
        # portability patch) needs the conan jansson package paths — the
        # CMakeDeps config exports the lowercase jansson::jansson target
        # which the upstream Jansson::Jansson gate never sees.
        jansson_pkg = self._dep_folder("jansson")
        if jansson_pkg:
            cfg_vars["JANSSON_INCLUDE_DIR"] = os.path.join(jansson_pkg, "include")
            cfg_vars["JANSSON_LIBRARY"] = os.path.join(jansson_pkg, "lib", "libjansson.so")
        # SQLite3: CMake's bundled FindSQLite3.cmake (MODULE mode after the
        # portability patch) needs the conan sqlite3 package paths.
        sqlite_pkg = self._dep_folder("sqlite3")
        if sqlite_pkg and self.options.with_sqlite3:
            cfg_vars["SQLITE3_INCLUDE_DIR"] = os.path.join(sqlite_pkg, "include")
            cfg_vars["SQLITE3_LIBRARY"] = os.path.join(sqlite_pkg, "lib", "libsqlite3.a")
        cmake.configure(variables=cfg_vars)
        cmake.build()
        if enable_upstream_tests:
            self._run_upstream_ctests(check_pkg)

    def _run_upstream_ctests(self, check_pkg):
        # Layer-1 upstream tests (docs/TEST_QUALITY_SPEC.md). Same env
        # handling as the libyder recipe: writable TMPDIR for libcheck's
        # fork IPC AND for the upstream /tmp/test.db sqlite fixture (OHOS
        # /tmp is read-only; the portability patch routes the fixture
        # through $TMPDIR), plus LD_LIBRARY_PATH.
        bdir = self.build_folder
        test_tmp = os.path.join(bdir, ".test-tmp")
        os.makedirs(test_tmp, exist_ok=True)
        env = dict(os.environ)
        env["TMPDIR"] = test_tmp
        env["TMP"] = test_tmp
        env["TEMP"] = test_tmp
        ld = [p for p in (bdir, os.path.join(check_pkg, "lib")) if os.path.isdir(p)]
        # jansson/2.14 ships a shared library (libjansson.so) on ohpcd; the
        # test executables resolve it at runtime through LD_LIBRARY_PATH.
        jansson_pkg = self._dep_folder("jansson")
        if jansson_pkg:
            ld.append(os.path.join(jansson_pkg, "lib"))
        if env.get("LD_LIBRARY_PATH"):
            ld.append(env["LD_LIBRARY_PATH"])
        env["LD_LIBRARY_PATH"] = ":".join(ld)
        # The sqlite fixture expected by the tests is created from the
        # upstream test/test.sqlite3.sql schema (same file the upstream CI
        # feeds to `sqlite3 /tmp/test.db < test/test.sqlite3.sql`). The
        # sqlite3 CLI is not available on OHOS, so the schema is applied
        # through python's sqlite3 module.
        fixture = os.path.join(test_tmp, "test.db")
        if os.path.exists(fixture):
            os.unlink(fixture)
        schema = os.path.join(self.source_folder, "test", "test.sqlite3.sql")
        import sqlite3 as _sqlite3
        conn = _sqlite3.connect(fixture)
        with open(schema, "r") as f:
            conn.executescript(f.read())
        conn.close()
        self.output.info("[libhoel] sqlite fixture seeded at %s" % fixture)
        tests = "core multi"
        # The test executables are EXCLUDE_FROM_ALL upstream: build them
        # explicitly so they are guaranteed to exist before ctest runs.
        self.output.info("[libhoel] build upstream test executables (EXCLUDE_FROM_ALL)")
        # -j1: the OHOS make cannot create a jobserver fifo (Operation not
        # permitted), which GNU make only tolerates in non-parallel mode.
        r = subprocess.run(
            'cmake --build "{b}" --target {t} -- -j1'.format(b=bdir, t=tests),
            shell=True, env=env, cwd=bdir, capture_output=True, text=True, timeout=1800)
        if r.stdout:
            self.output.info(r.stdout[-4000:] if len(r.stdout) > 4000 else r.stdout)
        if r.stderr:
            self.output.info("[stderr] " + r.stderr[-2000:])
        if r.returncode != 0:
            raise RuntimeError(
                "building upstream libhoel test executables failed (%d)" % r.returncode)
        self.output.info("[libhoel] run upstream CTest (core + multi, 21 official check cases)")
        c = subprocess.run(
            'ctest --test-dir "{b}" --output-on-failure'.format(b=bdir),
            shell=True, env=env, cwd=bdir, capture_output=True, text=True, timeout=1800)
        if c.stdout:
            self.output.info(c.stdout[-6000:] if len(c.stdout) > 6000 else c.stdout)
        if c.stderr:
            self.output.info("[stderr] " + c.stderr[-2000:])
        if c.returncode != 0:
            raise RuntimeError("upstream libhoel CTest failed (%d)" % c.returncode)

    def package(self):
        copy(self, "LICENSE", os.path.join(self.source_folder),
             os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

        rmdir(self, os.path.join(self.package_folder, "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        libname = "hoel"
        if is_msvc(self) and not self.options.shared:
            libname += "-static"
        self.cpp_info.libs = [libname]

        self.cpp_info.set_property("cmake_file_name", "Hoel")
        self.cpp_info.set_property("cmake_target_name",
            "Hoel::Hoel" if self.options.shared else "Hoel::Hoel-static")
        self.cpp_info.set_property("pkg_config_name", "libhoel")
        self.cpp_info.builddirs.append(os.path.join("lib", "cmake"))

        self.cpp_info.names["cmake_find_package"] = "Hoel"
        self.cpp_info.names["cmake_find_package_multi"] = "Hoel"
        self.cpp_info.names["pkg_config"] = "libhoel"
        self.cpp_info.filenames["cmake_find_package"] = "Hoel"
        self.cpp_info.filenames["cmake_find_package_multi"] = "Hoel"
