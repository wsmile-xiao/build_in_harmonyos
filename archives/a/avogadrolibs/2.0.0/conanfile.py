#!/usr/bin/env python3
"""Conan recipe for avogadrolibs 2.0.0 (headless C++ libraries)."""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class AvogadroLibsConan(ConanFile):
    name = "avogadrolibs"
    version = "2.0.0"
    description = "Reusable C++ chemistry and molecular data libraries from Avogadro"
    license = "BSD-3-Clause"
    homepage = "https://github.com/OpenChemistry/avogadrolibs"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "testing": [True, False]}
    default_options = {"shared": False, "testing": False}

    def requirements(self):
        self.requires("eigen/3.4.0", transitive_headers=True)

    def build_requirements(self):
        if self.options.testing:
            self.test_requires("gtest/1.17.0")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} is not supported")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        cmake_lists = os.path.join(self.source_folder, "CMakeLists.txt")
        with open(cmake_lists, "r", encoding="utf-8") as source_file:
            contents = source_file.read()
        marker = '  install(EXPORT "AvogadroLibsTargets"\n'
        insertion = (
            '  # IO exports these bundled static dependencies.\n'
            '  install(TARGETS struct pugixml\n'
            '    EXPORT "AvogadroLibsTargets"\n'
            '    ARCHIVE DESTINATION "${INSTALL_LIBRARY_DIR}"\n'
            '    LIBRARY DESTINATION "${INSTALL_LIBRARY_DIR}"\n'
            '    RUNTIME DESTINATION "${INSTALL_RUNTIME_DIR}")\n'
        )
        if contents.count(marker) != 1:
            raise ConanException("avogadrolibs 2.0.0: expected one export-set marker")
        if "install(TARGETS struct pugixml" not in contents:
            contents = contents.replace(marker, insertion + marker, 1)
            with open(cmake_lists, "w", encoding="utf-8", newline="\n") as source_file:
                source_file.write(contents)

    @staticmethod
    def _executable_path(value, label):
        if not value:
            raise ConanInvalidConfiguration(f"{label} is not configured")
        path = shutil.which(str(value))
        if not path or not os.path.isfile(path) or not os.access(path, os.X_OK):
            raise ConanInvalidConfiguration(f"{label} is not an executable: {value}")
        return os.path.abspath(path)

    def _configured_path(self, conf_name, env_name, default):
        value = self.conf.get(conf_name, default=None) or os.getenv(env_name) or default
        path = os.path.abspath(os.path.expanduser(str(value)))
        if not os.path.exists(path):
            raise ConanInvalidConfiguration(f"Configured path does not exist: {path}")
        return path

    def _ohos_toolchain(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        c_compiler = self._executable_path(
            executables.get("c") or os.getenv("CC"), "OHOS C compiler"
        )
        cxx_compiler = self._executable_path(
            executables.get("cpp") or os.getenv("CXX"), "OHOS C++ compiler"
        )
        compiler_bin = os.path.dirname(c_compiler)
        real_llvm_bin = os.path.dirname(os.path.realpath(c_compiler))
        if os.path.dirname(os.path.realpath(cxx_compiler)) != real_llvm_bin:
            raise ConanInvalidConfiguration(
                "OHOS C and C++ compilers must come from the same LLVM bin directory"
            )

        native_root = os.path.dirname(os.path.dirname(real_llvm_bin))
        sysroot = self._configured_path(
            "user.avogadrolibs:ohos_sysroot", "OHOS_SYSROOT",
            os.path.join(native_root, "sysroot")
        )
        if not os.path.isdir(os.path.join(sysroot, "usr", "include")):
            raise ConanInvalidConfiguration(
                f"OHOS sysroot has no usr/include directory: {sysroot}"
            )

        llvm_ar = self._executable_path(self._configured_path(
            "user.avogadrolibs:llvm_ar", "OHOS_LLVM_AR",
            os.path.join(compiler_bin, "llvm-ar")
        ), "OHOS llvm-ar")
        llvm_ranlib = self._executable_path(self._configured_path(
            "user.avogadrolibs:llvm_ranlib", "OHOS_LLVM_RANLIB",
            os.path.join(compiler_bin, "llvm-ranlib")
        ), "OHOS llvm-ranlib")
        if os.path.dirname(llvm_ar) != compiler_bin:
            raise ConanInvalidConfiguration("llvm-ar must match the configured compiler directory")
        if os.path.dirname(llvm_ranlib) != compiler_bin:
            raise ConanInvalidConfiguration("llvm-ranlib must match the configured compiler directory")
        return c_compiler, cxx_compiler, sysroot, llvm_ar, llvm_ranlib

    def generate(self):
        c_compiler, cxx_compiler, sysroot, llvm_ar, llvm_ranlib = self._ohos_toolchain()
        deps = CMakeDeps(self)
        if self.options.testing:
            deps.set_property("gtest", "cmake_file_name", "GTest")
        deps.generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["CMAKE_SYSTEM_NAME"] = "OHOS"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["CMAKE_SYSROOT"] = sysroot
        tc.variables["CMAKE_C_COMPILER"] = c_compiler
        tc.variables["CMAKE_CXX_COMPILER"] = cxx_compiler
        tc.variables["CMAKE_C_COMPILER_TARGET"] = "aarch64-unknown-linux-ohos"
        tc.variables["CMAKE_CXX_COMPILER_TARGET"] = "aarch64-unknown-linux-ohos"
        tc.variables["CMAKE_AR"] = llvm_ar
        tc.variables["CMAKE_RANLIB"] = llvm_ranlib
        tc.variables["CMAKE_FIND_ROOT_PATH"] = [sysroot, self.generators_folder]
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_PROGRAM"] = "NEVER"
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_LIBRARY"] = "ONLY"
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_INCLUDE"] = "ONLY"
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "ONLY"
        tc.variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = True
        tc.variables["Eigen3_DIR"] = self.generators_folder
        if self.options.testing:
            tc.variables["GTest_DIR"] = self.generators_folder
        tc.variables["ENABLE_TESTING"] = bool(self.options.testing)
        disabled_options = (
            "USE_OPENGL", "USE_QT", "USE_LIBARCHIVE",
            "USE_LIBMSYM", "USE_SPGLIB", "USE_PLOTTER", "USE_HDF5",
            "USE_MMTF", "USE_PYTHON", "ENABLE_CALC_BENCHMARKS",
            "BUILD_DOCUMENTATION",
        )
        for option in disabled_options:
            tc.variables[option] = False
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        tc.generate()

    def _llvm_runtime_library_dir(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = executables.get("cpp") or executables.get("c") or os.getenv("CXX") or os.getenv("CC")
        if not compiler:
            raise ConanException("Cannot derive LLVM runtime directory: no configured clang")
        real_bin = os.path.dirname(os.path.realpath(str(compiler)))
        runtime_dir = os.path.abspath(os.path.join(os.path.dirname(real_bin), "lib"))
        if not os.path.isfile(os.path.join(runtime_dir, "libxml2.so.16")):
            raise ConanException(
                "Derived LLVM runtime directory lacks libxml2.so.16: " + runtime_dir
            )
        self.output.info("LLVM runtime loader directory: " + runtime_dir)
        return runtime_dir

    def _with_llvm_runtime_loader_path(self):
        runtime_dir = self._llvm_runtime_library_dir()
        old_path = os.environ.get("LD_LIBRARY_PATH")
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            [runtime_dir] + ([old_path] if old_path else [])
        )
        return old_path

    @staticmethod
    def _restore_llvm_runtime_loader_path(old_path):
        if old_path is None:
            os.environ.pop("LD_LIBRARY_PATH", None)
        else:
            os.environ["LD_LIBRARY_PATH"] = old_path

    def build(self):
        old_path = self._with_llvm_runtime_loader_path()
        try:
            cmake = CMake(self)
            cmake.configure()
            cmake.build()
        finally:
            self._restore_llvm_runtime_loader_path(old_path)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE*", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "AvogadroLibs")
        components = {
            "headers": ("Avogadro::Headers", [], []),
            "core": ("Avogadro::Core", ["Core"], ["headers"]),
            "calc": ("Avogadro::Calc", ["Calc"], ["core"]),
            "struct": ("AvogadroLibs::struct", ["struct"], []),
            "pugixml": ("AvogadroLibs::pugixml", ["pugixml"], []),
            "io": ("Avogadro::IO", ["IO"], ["core", "struct", "pugixml"]),
            "quantumio": ("Avogadro::QuantumIO", ["QuantumIO"], ["io"]),
        }
        for name, (target, libs, requires) in components.items():
            component = self.cpp_info.components[name]
            component.set_property("cmake_target_name", target)
            component.libs = libs
            component.requires = requires
        self.cpp_info.components["headers"].requires = ["eigen::eigen"]
