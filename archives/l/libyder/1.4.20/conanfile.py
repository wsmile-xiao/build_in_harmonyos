# conanfile.py — libyder 1.4.20
# HarmonyOS PC adaptation (babelouest logging library, ulfius chain)
import os
import subprocess

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rmdir
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.microsoft import is_msvc

required_conan_version = ">=1.52.0"


class YderConan(ConanFile):
    name = "libyder"
    version = "1.4.20"
    description = "Logging library for C applications (console, file, syslog, callback)"
    homepage = "https://github.com/babelouest/yder/"
    topics = ("logging", "log", "logger")
    license = "LGPL-2.1-or-later"
    url = "https://github.com/babelouest/yder"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_journald": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_journald": False,
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
        # yder has a hard runtime dependency on orcania (o_malloc/o_strdup/
        # split_string/... used throughout src/yder.c). orcania/2.3.3 is
        # published on the ohpcd registry (W0 verified).
        self.requires("orcania/2.3.3")

    def build_requirements(self):
        # check/0.15.2 (published on ohpcd) is needed to build and run the
        # upstream CTest suite (yder_test, 15 official check cases). It is a
        # test-only requirement: available to this recipe while building/
        # running the upstream tests, never propagated to consumers and not
        # part of the package_id. Same pattern as the repo precedent
        # (orcania 2.3.3, libwbxml).
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
        from conan.tools.cmake import CMakeDeps
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED"] = self.options.shared
        tc.variables["BUILD_STATIC"] = not self.options.shared
        # journald (systemd sd_journal_print) does not exist on OHOS; the
        # upstream WITH_JOURNALD option turns it off and defines
        # Y_DISABLE_JOURNALD in yder-cfg.h.
        tc.variables["WITH_JOURNALD"] = self.options.with_journald
        tc.variables["BUILD_YDER_TESTING"] = False  # toggled in build()
        tc.variables["BUILD_YDER_DOCUMENTATION"] = False
        tc.variables["BUILD_RPM"] = False
        tc.variables["INSTALL_HEADER"] = True
        tc.generate()
        # CMakeDeps generates OrcaniaConfig.cmake (target
        # Orcania::Orcania-static) for the host requirement orcania/2.3.3.
        # Check is deliberately NOT declared as a CMakeDeps requirement:
        # upstream resolves it through its own bundled
        # cmake-modules/FindCheck.cmake in MODULE mode (see build()).
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
        # Run the unmodified upstream CTest suite (yder_test, 15 check
        # cases; upstream registers it EXCLUDE_FROM_ALL) for the static
        # build the recipe defaults to, and only when the conan check
        # dependency is present.
        enable_upstream_tests = bool(check_pkg) and not self.options.shared
        cfg_vars = {"BUILD_YDER_TESTING": "ON" if enable_upstream_tests else "OFF"}
        if enable_upstream_tests:
            # Seed yder's bundled cmake-modules/FindCheck.cmake with the conan
            # check package paths. The recipe's portability patch forces
            # find_package(Check MODULE) so the bundled module (CHECK_FOUND /
            # Check::Check) runs even though the conan toolchain sets
            # CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON. Never fall back to a host
            # /usr same-name lib.
            cfg_vars["CHECK_INCLUDE_DIR"] = os.path.join(check_pkg, "include")
            cfg_vars["CHECK_LIBRARY"] = os.path.join(check_pkg, "lib", "libcheck.a")
        cmake.configure(variables=cfg_vars)
        cmake.build()
        if enable_upstream_tests:
            self._run_upstream_ctests(check_pkg)

    def _run_upstream_ctests(self, check_pkg):
        # Layer-1 upstream tests (docs/TEST_QUALITY_SPEC.md). Same env
        # handling as the orcania recipe: writable TMPDIR for libcheck's
        # fork IPC AND for the upstream /tmp/test.log file fixture (OHOS
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
        if env.get("LD_LIBRARY_PATH"):
            ld.append(env["LD_LIBRARY_PATH"])
        env["LD_LIBRARY_PATH"] = ":".join(ld)
        tests = "yder_test"
        # The test executable is EXCLUDE_FROM_ALL upstream: build it
        # explicitly so it is guaranteed to exist before ctest runs.
        self.output.info("[libyder] build upstream test executable (EXCLUDE_FROM_ALL)")
        # -j1: the OHOS make cannot create a jobserver fifo (Operation not
        # permitted), which GNU make only tolerates in non-parallel mode.
        r = subprocess.run(
            'cmake --build "{b}" --target {t} -- -j1'.format(b=bdir, t=tests),
            shell=True, env=env, cwd=bdir, capture_output=True, text=True, timeout=900)
        if r.stdout:
            self.output.info(r.stdout[-4000:] if len(r.stdout) > 4000 else r.stdout)
        if r.stderr:
            self.output.info("[stderr] " + r.stderr[-2000:])
        if r.returncode != 0:
            raise RuntimeError(
                "building upstream libyder test executable failed (%d)" % r.returncode)
        self.output.info("[libyder] run upstream CTest (15 official check cases)")
        c = subprocess.run(
            'ctest --test-dir "{b}" --output-on-failure'.format(b=bdir),
            shell=True, env=env, cwd=bdir, capture_output=True, text=True, timeout=900)
        if c.stdout:
            self.output.info(c.stdout[-6000:] if len(c.stdout) > 6000 else c.stdout)
        if c.stderr:
            self.output.info("[stderr] " + c.stderr[-2000:])
        if c.returncode != 0:
            raise RuntimeError("upstream libyder CTest failed (%d)" % c.returncode)

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
        libname = "yder"
        if is_msvc(self) and not self.options.shared:
            libname += "-static"
        self.cpp_info.libs = [libname]

        self.cpp_info.set_property("cmake_file_name", "Yder")
        self.cpp_info.set_property("cmake_target_name",
            "Yder::Yder" if self.options.shared else "Yder::Yder-static")
        self.cpp_info.set_property("pkg_config_name", "libyder")
        self.cpp_info.builddirs.append(os.path.join("lib", "cmake"))

        self.cpp_info.names["cmake_find_package"] = "Yder"
        self.cpp_info.names["cmake_find_package_multi"] = "Yder"
        self.cpp_info.names["pkg_config"] = "libyder"
        self.cpp_info.filenames["cmake_find_package"] = "Yder"
        self.cpp_info.filenames["cmake_find_package_multi"] = "Yder"
