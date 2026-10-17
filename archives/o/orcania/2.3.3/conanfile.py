# conanfile.py 鈥?orcania 2.3.3
# Auto-generated for HarmonyOS PC adaptation
import os
import subprocess

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rmdir, save
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.microsoft import is_msvc

required_conan_version = ">=1.52.0"


class OrcaniaConan(ConanFile):
    name = "orcania"
    version = "2.3.3"
    description = "Potluck with different functions for different purposes that can be shared among C programs"
    homepage = "https://github.com/babelouest/orcania"
    topics = ("utility", "functions")
    license = "LGPL-2.1-or-later"
    url = "https://github.com/babelouest/orcania"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_strstr": [True, False],
        "build_base64url": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_strstr": False,
        "build_base64url": True,
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

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            destination=self.source_folder, strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def build_requirements(self):
        # check/0.15.2 (published on ohpcd) is needed to build and run the
        # upstream CTest suite (4 official test programs). It is a test-only
        # requirement: available to this recipe while building/running the
        # upstream tests, but never propagated to consumers and not part of the
        # package_id. Same pattern as the repo precedent (libwbxml).
        if not self.options.shared:
            self.test_requires("check/0.15.2")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED"] = self.options.shared
        tc.variables["BUILD_STATIC"] = not self.options.shared
        tc.variables["BUILD_BASE64URL"] = self.options.build_base64url
        # BUILD_ORCANIA_TESTING is toggled in build() (the upstream test tree
        # only builds when Check is found, which needs the conan check/0.15.2
        # headers/libs wired in at configure time).
        tc.variables["BUILD_ORCANIA_DOCUMENTATION"] = False
        tc.variables["BUILD_RPM"] = False
        tc.variables["WITH_STRSTR"] = self.options.with_strstr
        tc.variables["INSTALL_HEADER"] = True
        tc.generate()
        # No CMakeDeps here on purpose: orcania has no consumer (host) requires.
        # check/0.15.2 is a test-only requirement that upstream resolves through
        # its OWN cmake-modules/FindCheck.cmake (module mode -> Check::Check,
        # CHECK_FOUND). If we let CMakeDeps generate a check-config.cmake, CMake
        # finds the config target Check::check instead and upstream's
        # `if (CHECK_FOUND)` guard never fires, so the CTest tree is skipped.

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
        # Run the unmodified upstream CTest suite (4 programs, upstream marks
        # them EXCLUDE_FROM_ALL) for the static build the recipe defaults to,
        # and only when the conan check dependency is present. Upstream
        # test/*.c are never modified; the portability patch only relaxes the
        # Subunit hard requirement because the OHOS libcheck is self-contained.
        enable_upstream_tests = bool(check_pkg) and not self.options.shared
        cfg_vars = {"BUILD_ORCANIA_TESTING": "ON" if enable_upstream_tests else "OFF"}
        if enable_upstream_tests:
            # Seed orcania's bundled cmake-modules/FindCheck.cmake with the conan
            # check package paths (private OHOS prefix). Never fall back to a host
            # /usr same-name lib.
            #
            # Deliberately NO CMAKE_PREFIX_PATH here: the conan toolchain sets
            # CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON, so find_package(Check) would
            # resolve in CONFIG mode against the check package's installed
            # config (target Check::check / Check_FOUND) and upstream's own
            # FindCheck.cmake (Check::Check / CHECK_FOUND) would never run, so the
            # `if (CHECK_FOUND)` CTest tree would be skipped. With no config
            # discoverable, find_package falls back to MODULE mode and the bundled
            # module consumes these two seeds.
            cfg_vars["CHECK_INCLUDE_DIR"] = os.path.join(check_pkg, "include")
            cfg_vars["CHECK_LIBRARY"] = os.path.join(check_pkg, "lib", "libcheck.a")
        cmake.configure(variables=cfg_vars)
        cmake.build()
        if enable_upstream_tests:
            self._run_upstream_ctests(check_pkg)

    def _run_upstream_ctests(self, check_pkg):
        # Layer-1 upstream tests (docs/TEST_QUALITY_SPEC.md). Same env handling
        # as the libwbxml recipe: writable TMPDIR for libcheck's fork IPC, plus
        # LD_LIBRARY_PATH. Full ctest output is logged so the CI gates see it.
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
        tests = "str_test split_test memory_test pointer_list_test"
        # The 4 executables are EXCLUDE_FROM_ALL upstream: build them explicitly
        # so they are guaranteed to exist before ctest runs.
        self.output.info("[orcania] build upstream test executables (EXCLUDE_FROM_ALL)")
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
                "building upstream orcania test executables failed (%d)" % r.returncode)
        self.output.info("[orcania] run upstream CTest (4 official tests)")
        c = subprocess.run(
            'ctest --test-dir "{b}" --output-on-failure'.format(b=bdir),
            shell=True, env=env, cwd=bdir, capture_output=True, text=True, timeout=900)
        if c.stdout:
            self.output.info(c.stdout[-4000:] if len(c.stdout) > 4000 else c.stdout)
        if c.stderr:
            self.output.info("[stderr] " + c.stderr[-2000:])
        if c.returncode != 0:
            raise RuntimeError("upstream orcania CTest failed (%d)" % c.returncode)

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
        libname = "orcania"
        if is_msvc(self) and not self.options.shared:
            libname += "-static"
        self.cpp_info.libs = [libname]

        self.cpp_info.set_property("cmake_file_name", "Orcania")
        self.cpp_info.set_property("cmake_target_name",
            "Orcania::Orcania" if self.options.shared else "Orcania::Orcania-static")
        self.cpp_info.set_property("pkg_config_name", "liborcania")
        self.cpp_info.builddirs.append(os.path.join("lib", "cmake"))

        self.cpp_info.names["cmake_find_package"] = "Orcania"
        self.cpp_info.names["cmake_find_package_multi"] = "Orcania"
        self.cpp_info.names["pkg_config"] = "liborcania"
        if self.options.shared:
            self.cpp_info.filenames["cmake_find_package"] = "Orcania"
            self.cpp_info.filenames["cmake_find_package_multi"] = "Orcania"
        else:
            self.cpp_info.filenames["cmake_find_package"] = "Orcania"
            self.cpp_info.filenames["cmake_find_package_multi"] = "Orcania"
