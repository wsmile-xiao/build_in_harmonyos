#!/usr/bin/env python3
"""Conan recipe for libical 4.0.1 on HarmonyOS PC."""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    replace_in_file,
    save,
)


class LibicalConan(ConanFile):
    name = "libical"
    version = "4.0.1"
    description = "iCalendar and vCard protocol library"
    license = "LGPL-2.1-only OR MPL-2.0"
    homepage = "https://github.com/libical/libical"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        if self.settings.os != "Windows":
            self.tool_requires("perl/5.42.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            rules = os.path.join(self.generators_folder, "ohos-cmake-rules.cmake")
            save(
                self,
                rules,
                "\n".join(
                    (
                        'set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,./")',
                        'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG "-Wl,-rpath,")',
                        'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG_SEP ":")',
                        'set(CMAKE_SHARED_LIBRARY_RPATH_LINK_C_FLAG "-Wl,-rpath-link,")',
                        'set(CMAKE_SHARED_LIBRARY_RPATH_ORIGIN_TOKEN "$ORIGIN")',
                    )
                )
                + "\n",
            )
            tc.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_C"] = rules
        elif self.settings.os == "Windows":
            cmake_make_program = os.environ.get("CMAKE_MAKE_PROGRAM")
            if cmake_make_program:
                cmake_make_program = cmake_make_program.replace("\\", "/")
                tc.cache_variables["CMAKE_MAKE_PROGRAM"] = cmake_make_program
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["LIBICAL_CXX_BINDINGS"] = "OFF"
        tc.variables["LIBICAL_JAVA_BINDINGS"] = "OFF"
        tc.variables["LIBICAL_GLIB"] = "OFF"
        tc.variables["LIBICAL_GOBJECT_INTROSPECTION"] = "OFF"
        tc.variables["LIBICAL_GLIB_VAPI"] = "OFF"
        tc.variables["LIBICAL_BUILD_DOCS"] = "OFF"
        tc.variables["LIBICAL_GLIB_BUILD_DOCS"] = "OFF"
        tc.variables["LIBICAL_BUILD_EXAMPLES"] = "OFF"
        tc.variables["LIBICAL_BUILD_TESTING"] = "ON"
        tc.variables["LIBICAL_BUILD_TESTING_BIGFUZZ"] = "OFF"
        tc.variables["LIBICAL_BUILD_VZIC"] = "OFF"
        tc.variables["LIBICAL_ENABLE_BUILTIN_TZDATA"] = "ON"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_ICU"] = "ON"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_BerkeleyDB"] = "ON"
        perl = next(
            (
                dep
                for dep in self.dependencies.build.values()
                if dep.ref and dep.ref.name == "perl"
            ),
            None,
        )
        if perl and perl.package_folder:
            tc.variables["PERL_EXECUTABLE"] = os.path.join(perl.package_folder, "bin", "perl")
        elif self.settings.os == "Windows":
            perl_executable = os.environ.get("PERL_EXECUTABLE") or shutil.which("perl")
            if not perl_executable:
                raise ConanInvalidConfiguration(
                    "Perl is required to build libical on Windows"
                )
            perl_executable = perl_executable.replace("\\", "/")
            tc.variables["PERL_EXECUTABLE"] = perl_executable
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os == "OHOS":
            self._use_ohos_relative_sonames()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        self._prepare_builtin_timezone_data()
        self._prepare_ctest_runtime_links()
        test_env = Environment()
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        for dep in self.dependencies.build.values():
            if dep and dep.package_folder:
                test_env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
        for rel in (
            "bin",
            "lib",
            os.path.join("src", "libical"),
            os.path.join("src", "libicalss"),
            os.path.join("src", "libicalvcal"),
            os.path.join("src", "libicalvcard"),
        ):
            test_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
            test_env.prepend_path("PATH", os.path.join(self.build_folder, rel))
        ctest = self._ctest_executable()
        with test_env.vars(self).apply():
            self.run(
                '{} --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self._quote(ctest),
                    self.build_folder
                )
            )

    def _ctest_executable(self):
        ctest = os.environ.get("CTEST_EXECUTABLE") or shutil.which("ctest")
        if ctest:
            return ctest
        cmake_program = self.conf.get("tools.cmake:cmake_program")
        if cmake_program:
            candidate = os.path.join(os.path.dirname(cmake_program), "ctest.exe")
            if os.path.isfile(candidate):
                return candidate
            candidate = os.path.join(os.path.dirname(cmake_program), "ctest")
            if os.path.isfile(candidate):
                return candidate
        return "ctest"

    def _prepare_ctest_runtime_links(self):
        lib_sources = glob.glob(os.path.join(self.build_folder, "lib", "lib*.so*"))
        if not lib_sources:
            return

        base_dirs = {self.build_folder}
        for root, _, files in os.walk(self.build_folder):
            if "CTestTestfile.cmake" in files:
                base_dirs.add(root)

        allowed_root = os.path.abspath(self.build_folder)
        for base in sorted(base_dirs):
            for rel in (
                ".",
                "lib",
                os.path.join("..", "lib"),
                os.path.join("..", "..", "lib"),
                os.path.join("..", "..", "..", "lib"),
            ):
                target_dir = os.path.abspath(os.path.normpath(os.path.join(base, rel)))
                if os.path.commonpath([allowed_root, target_dir]) != allowed_root:
                    continue
                os.makedirs(target_dir, exist_ok=True)
                for src in lib_sources:
                    dst = os.path.join(target_dir, os.path.basename(src))
                    if os.path.abspath(src) == os.path.abspath(dst):
                        continue
                    shutil.copy2(src, dst)

    def _prepare_builtin_timezone_data(self):
        source_zoneinfo = os.path.join(self.source_folder, "zoneinfo")
        if os.path.isdir(source_zoneinfo):
            for build_zoneinfo in (
                os.path.join(self.build_folder, "zoneinfo"),
                os.path.normpath(os.path.join(self.build_folder, "..", "zoneinfo")),
            ):
                shutil.copytree(source_zoneinfo, build_zoneinfo, dirs_exist_ok=True)

    def _use_ohos_relative_sonames(self):
        for target, rel in (
            ("ical", os.path.join("src", "libical", "CMakeLists.txt")),
            ("icalss", os.path.join("src", "libicalss", "CMakeLists.txt")),
            ("icalvcal", os.path.join("src", "libicalvcal", "CMakeLists.txt")),
            ("icalvcard", os.path.join("src", "libicalvcard", "CMakeLists.txt")),
        ):
            path = os.path.join(self.source_folder, rel)
            replace_in_file(
                self,
                path,
                """if(NOT ANDROID)
  set_target_properties(
    {target}
    PROPERTIES
      VERSION
        ${{CMAKE_PROJECT_VERSION}}
      SOVERSION
        ${{LIBICAL_LIB_SOVERSION_STRING}}
  )
endif()
""".format(target=target),
                "",
            )

    def package(self):
        CMake(self).install()
        if self.settings.os == "OHOS":
            self._sign_ohos_elf_tree(self.package_folder)

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.set_property("pkg_config_name", "libical")
        self.cpp_info.builddirs = [
            os.path.join("lib", "cmake", "LibIcal"),
            os.path.join("lib", "cmake"),
        ]
        self.cpp_info.libs = ["icalvcard", "icalvcal", "icalss", "ical"]
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))

    def _sign_ohos_elf_tree(self, root_folder):
        objcopy = shutil.which("llvm-objcopy")
        signer = shutil.which("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS llvm-objcopy and binary-sign-tool are required for ELF signing"
            )
        for root, _, files in os.walk(root_folder):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path) or not os.path.isfile(path) or not self._is_elf(path):
                    continue
                self.run(
                    f"{self._quote(objcopy)} --remove-section .codesign "
                    f"{self._quote(path)} 2>/dev/null || true"
                )
                self.run(
                    f"{self._quote(signer)} sign -inFile {self._quote(path)} "
                    f"-outFile {self._quote(path)} -selfSign 1"
                )

    @staticmethod
    def _is_elf(path):
        with open(path, "rb") as f:
            return f.read(4) == b"\x7fELF"

    @staticmethod
    def _quote(value):
        return '"' + value.replace('"', '\\"') + '"'
