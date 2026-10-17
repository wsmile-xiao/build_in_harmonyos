#!/usr/bin/env python3
"""CMake Conan recipe for the Boost 1.91.0.1 components required by Redex."""

import glob
import inspect
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    collect_libs,
    copy,
    export_conandata_patches,
    get,
)


class BoostConan(ConanFile):
    name = "boost"
    version = "1.91.0.1"
    description = "Boost C++ libraries, including Boost.Graph, required by Redex"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/"
    url = "https://github.com/boostorg/boost"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["BUILD_TESTING"] = False
        # Keep headers and library names stable on Windows as well as POSIX.
        # The upstream Windows default is the versioned install layout, which
        # does not match the Conan component names published below.
        tc.variables["BOOST_INSTALL_LAYOUT"] = "system"
        tc.variables["BOOST_INCLUDE_LIBRARIES"] = (
            "filesystem;graph;iostreams;program_options;regex;thread"
        )

        # ICU is optional for Boost.Regex and is not needed by Redex.
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_ICU"] = True
        tc.variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"

        # Redex uses mapped_file and generic filtering streams only. Disable
        # every optional compression backend so this prerequisite stays exact.
        tc.variables["BOOST_IOSTREAMS_ENABLE_ZLIB"] = False
        tc.variables["BOOST_IOSTREAMS_ENABLE_BZIP2"] = False
        tc.variables["BOOST_IOSTREAMS_ENABLE_LZMA"] = False
        tc.variables["BOOST_IOSTREAMS_ENABLE_ZSTD"] = False

        if self.settings.os == "OHOS":
            # E127: HarmonyOS does not provide POSIX thread cancellation APIs.
            tc.preprocessor_definitions[
                "BOOST_THREAD_DONT_PROVIDE_INTERRUPTIONS"
            ] = "1"
            tc.variables["BOOST_INSTALL_NO_VERSIONED_LIBS"] = True
            # Use portable fallbacks for Linux syscalls not guaranteed by OHOS.
            tc.variables["BOOST_FILESYSTEM_DISABLE_STATX"] = True
            tc.variables["BOOST_FILESYSTEM_DISABLE_COPY_FILE_RANGE"] = True

            # CMake has no built-in HarmonyOS platform module, so its generic
            # linker rules omit SONAME and build-tree RPATH flags. Without
            # these values, linked targets embed stage-relative DT_NEEDED
            # entries that cannot be resolved from CTest or an installed package.
            for language in ("C", "CXX"):
                tc.variables[
                    f"CMAKE_SHARED_LIBRARY_SONAME_{language}_FLAG"
                ] = "-Wl,-soname,"
                tc.variables[
                    f"CMAKE_SHARED_LIBRARY_RUNTIME_{language}_FLAG"
                ] = "-Wl,-rpath,"
                tc.variables[
                    f"CMAKE_SHARED_LIBRARY_RUNTIME_{language}_FLAG_SEP"
                ] = ":"
                tc.variables[
                    f"CMAKE_SHARED_LIBRARY_RPATH_LINK_{language}_FLAG"
                ] = "-Wl,-rpath-link,"
            tc.variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = True

        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            # The CMake superproject exposes the official ProgramOptions unit
            # suite for the selected dependency closure. BoostTest excludes
            # these executables from the default all target.
            self._run_component_tests()
            # These unmodified upstream CMake projects cover build-tree
            # integration for Iostreams and the Regex CMake consumption path.
            self._run_upstream_cmake_test(
                "libs/iostreams/test/cmake_subdir_test", "upstream-iostreams"
            )
            self._run_upstream_cmake_test(
                "libs/regex/test/cmake_subdir_test", "upstream-regex"
            )

    def _run_component_tests(self):
        cmake = CMake(self)
        cmake.configure(
            variables={
                "BUILD_TESTING": True,
                "BOOST_INCLUDE_LIBRARIES": (
                    "regex;filesystem;graph;program_options;iostreams;thread"
                ),
            },
            subfolder="upstream-components",
        )
        cmake.build(target="tests", subfolder="upstream-components")
        self._run_ctest(os.path.join(self.build_folder, "upstream-components"))

    def _run_upstream_cmake_test(self, source_subfolder, build_subfolder):
        cmake = CMake(self)
        cmake.configure(
            build_script_folder=os.path.join(self.source_folder, source_subfolder),
            subfolder=build_subfolder,
        )
        cmake.build(subfolder=build_subfolder)
        test_folder = os.path.join(self.build_folder, build_subfolder)

        self._run_ctest(test_folder)

    def _run_ctest(self, test_folder):
        self._sign_ohos_runtime_tree(test_folder)
        self._run_fail_closed(
            "ctest --output-on-failure --no-tests=error",
            env="conanrun",
            cwd=test_folder,
        )

    def _run_fail_closed(self, command, **kwargs):
        parameters = inspect.signature(self.run).parameters
        if "ignore_errors" in parameters:
            kwargs["ignore_errors"] = False
        elif "check" in parameters:
            kwargs["check"] = True
        else:
            raise ConanInvalidConfiguration(
                "Unsupported ConanFile.run API: expected ignore_errors or check"
            )
        self.run(command, **kwargs)

    def _sign_ohos_runtime_tree(self, root):
        if self.settings.os != "OHOS":
            return

        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS upstream tests require llvm-objcopy and binary-sign-tool"
            )

        for path in glob.glob(os.path.join(root, "**", "*"), recursive=True):
            if not os.path.isfile(path) or os.path.islink(path):
                continue
            if ".so" not in os.path.basename(path) and not os.access(path, os.X_OK):
                continue
            with open(path, "rb") as binary:
                if binary.read(4) != b"\x7fELF":
                    continue
            self._sign_elf_atomically(path, objcopy, signer)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE_1_0.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        self._sign_shared_libraries()

    def _sign_shared_libraries(self):
        if self.settings.os != "OHOS" or not self.options.shared:
            return

        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            self.output.warning(
                "OHOS signing tools are unavailable in this cross-build environment; "
                "the native release worker must sign shared libraries."
            )
            return

        libraries = glob.glob(
            os.path.join(self.package_folder, "lib", "**", "*.so*"), recursive=True
        )
        for library in libraries:
            if os.path.islink(library):
                continue
            self._sign_elf_atomically(library, objcopy, signer)

    def _sign_elf_atomically(self, path, objcopy, signer):
        original_mode = os.stat(path).st_mode
        temporary = f"{path}.signing"
        try:
            shutil.copy2(path, temporary)
            self._run_fail_closed(
                f'"{objcopy}" --remove-section .codesign "{temporary}"',
            )
            self._run_fail_closed(
                f'"{signer}" sign -inFile "{temporary}" '
                f'-outFile "{temporary}" -selfSign 1',
            )
            os.chmod(temporary, original_mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _find_ohos_tool(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        ]
        return next((path for path in candidates if os.path.isfile(path)), "")

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Boost")
        self.cpp_info.includedirs = ["include"]
        available_libraries = set(collect_libs(self))

        compiled_components = (
            "atomic",
            "chrono",
            "container",
            "date_time",
            "filesystem",
            "graph",
            "iostreams",
            "program_options",
            "random",
            "serialization",
            "thread",
            "wserialization",
        )
        for name in compiled_components:
            component = self.cpp_info.components[name]
            component.includedirs = ["include"]
            component.defines = ["BOOST_ALL_NO_LIB=1"]
            if self.options.shared:
                component.defines.append("BOOST_ALL_DYN_LINK=1")
            library = next(
                (
                    candidate
                    for candidate in (
                        f"boost_{name}",
                        f"boost_{name}.dll",
                        f"libboost_{name}",
                    )
                    if candidate in available_libraries
                ),
                None,
            )
            if library:
                component.libs = [library]
            component.set_property("cmake_target_name", f"Boost::{name}")

        # Boost.Regex 1.91 is an INTERFACE target in the official CMake
        # release. Its consumer test proves that no libboost_regex entry is
        # needed here; adding one would make CMakeDeps emit a phantom library.
        for name in ("headers", "regex", "system"):
            component = self.cpp_info.components[name]
            component.includedirs = ["include"]
            component.defines = ["BOOST_ALL_NO_LIB=1"]
            component.set_property("cmake_target_name", f"Boost::{name}")

        self.cpp_info.components["filesystem"].requires = ["atomic", "system"]
        self.cpp_info.components["date_time"].requires = ["container"]
        self.cpp_info.components["graph"].requires = [
            "headers",
            "random",
            "serialization",
            "regex",
        ]
        self.cpp_info.components["program_options"].requires = [
            "container",
            "headers",
        ]

        self.cpp_info.components["iostreams"].requires = [
            "random",
            "regex",
        ]
        self.cpp_info.components["random"].requires = ["headers", "system"]
        self.cpp_info.components["serialization"].requires = ["headers"]
        self.cpp_info.components["thread"].requires = [
            "atomic",
            "chrono",
            "container",
            "date_time",
            "system",
        ]
        self.cpp_info.components["wserialization"].requires = ["serialization"]

        self.cpp_info.components["graph"].defines.append("BOOST_GRAPH_NO_LIB=1")
        for name in ("serialization", "wserialization"):
            self.cpp_info.components[name].defines.append(
                "BOOST_SERIALIZATION_NO_LIB=1"
            )
        if self.options.shared:
            self.cpp_info.components["graph"].defines.append(
                "BOOST_GRAPH_DYN_LINK=1"
            )
            for name in ("serialization", "wserialization"):
                self.cpp_info.components[name].defines.append(
                    "BOOST_SERIALIZATION_DYN_LINK=1"
                )
        else:
            self.cpp_info.components["graph"].defines.append(
                "BOOST_GRAPH_STATIC_LINK=1"
            )
            for name in ("serialization", "wserialization"):
                self.cpp_info.components[name].defines.append(
                    "BOOST_SERIALIZATION_STATIC_LINK=1"
                )

        if self.settings.os == "OHOS":
            self.cpp_info.components["thread"].defines.append(
                "BOOST_THREAD_DONT_PROVIDE_INTERRUPTIONS=1"
            )
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.components["atomic"].system_libs = ["pthread"]
            self.cpp_info.components["thread"].system_libs = ["pthread"]
        elif self.settings.os == "Windows":
            self.cpp_info.components["atomic"].system_libs = [
                "synchronization"
            ]
