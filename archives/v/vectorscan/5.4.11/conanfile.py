#!/usr/bin/env python3
"""Conan recipe for vectorscan 5.4.11 on HarmonyOS."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
)


required_conan_version = ">=2.0"


class VectorscanConan(ConanFile):
    name = "vectorscan"
    version = "5.4.11"
    package_type = "library"

    description = (
        "A portable fork of the high-performance regular expression "
        "matching library"
    )
    homepage = "https://github.com/VectorCamp/vectorscan"
    license = "BSD-3-Clause"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "debug_output": [True, False],
        "dump_support": [True, False, "auto"],
        "with_cpu_native": [True, False],
        "with_fat_runtime": [True, False],
        "with_avx": [False, "avx2", "avx512", "avx512vbmi"],
        "with_sve": [False, "sve", "sve2", "sve2_bitperm"],
        "with_chimera": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "debug_output": False,
        "dump_support": "auto",
        "with_cpu_native": False,
        "with_fat_runtime": False,
        "with_avx": False,
        "with_sve": False,
        "with_chimera": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")
        if self.settings.os != "Linux":
            self.options.rm_safe("with_fat_runtime")
        if self.settings.arch not in ("x86", "x86_64"):
            self.options.rm_safe("with_avx")

    def configure(self):
        if self.options.shared or self.options.with_cpu_native:
            self.options.rm_safe("fPIC")
        if self.options.with_cpu_native:
            self.options.rm_safe("with_fat_runtime")
        if self.options.get_safe("with_fat_runtime"):
            self.options.rm_safe("with_avx")
            self.options.rm_safe("with_sve")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # Boost is used by the public hs component and must remain visible to
        # consumers through cpp_info.components["hs"].requires.
        self.requires("boost/1.84.0")
        if self.options.with_chimera:
            self.requires("pcre/8.45")

    def validate(self):
        check_min_cppstd(self, 17)
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "vectorscan 5.4.11 supports Linux and OHOS builds only"
            )
        if self.options.shared and self.options.with_chimera:
            raise ConanInvalidConfiguration(
                "Chimera requires a static vectorscan build"
            )

    def source(self):
        get(
            self,
            **self.conan_data["sources"][self.version],
            destination=self.source_folder,
            strip_root=True,
        )
        # The OHOS Conan remote does not publish a runnable ragel/6.10
        # tool package. Keep the build reproducible by bootstrapping the
        # exact upstream Ragel release from a pinned archive instead of
        # silently relying on a host installation.
        get(
            self,
            **self.conan_data["tools"]["ragel"]["6.10"],
            destination=os.path.join(self.source_folder, "ragel-source"),
            strip_root=True,
        )
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["BUILD_STATIC_LIBS"] = not bool(self.options.shared)
        tc.variables["DEBUG_OUTPUT"] = bool(self.options.debug_output)
        tc.variables["BUILD_CHIMERA"] = bool(self.options.with_chimera)
        tc.variables["BUILD_EXAMPLES"] = False
        tc.variables["BUILD_BENCHMARKS"] = False
        tc.variables["BUILD_UNIT_TESTS"] = False
        tc.variables["CMAKE_POLICY_DEFAULT_CMP0167"] = "OLD"

        if self.options.dump_support != "auto":
            tc.variables["DUMP_SUPPORT"] = self.options.dump_support
        tc.variables["WITH_CPU_NATIVE"] = bool(self.options.with_cpu_native)

        if "with_avx" in self.options:
            if not self.options.with_avx:
                tc.cache_variables["BUILD_AVX2"] = False
            elif self.options.with_avx == "avx2":
                tc.cache_variables["BUILD_AVX2"] = True
            elif self.options.with_avx == "avx512":
                tc.variables["BUILD_AVX512"] = True
            elif self.options.with_avx == "avx512vbmi":
                tc.variables["BUILD_AVX512VBMI"] = True

        if "with_sve" in self.options:
            if not self.options.with_sve:
                tc.cache_variables["BUILD_SVE"] = False
                tc.cache_variables["BUILD_SVE2"] = False
                tc.cache_variables["BUILD_SVE2_BITPERM"] = False
            elif self.options.with_sve == "sve":
                tc.cache_variables["BUILD_SVE"] = True
            elif self.options.with_sve == "sve2":
                tc.cache_variables["BUILD_SVE2"] = True
            elif self.options.with_sve == "sve2_bitperm":
                tc.cache_variables["BUILD_SVE2_BITPERM"] = True

        if str(self.settings.os) == "OHOS":
            # CMake 4's generic platform name does not match the installed
            # OHOS module unless these values are explicit.
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values[
                "cmake_system_processor"
            ] = "aarch64"

        # CMake generates Parser.cpp and control_verbs.cpp through Ragel at
        # configure time. The binary is built into a private build prefix
        # immediately before CMake runs, so it never leaks into the device
        # or Conan global PATH.
        tc.cache_variables["RAGEL"] = self._ragel_binary()

        tc.generate()
        CMakeDeps(self).generate()
        VirtualBuildEnv(self).generate()

    def build(self):
        self._build_ragel()
        cmake = CMake(self)
        cmake.configure()
        # HMDFS does not permit GNU make's named-pipe jobserver. Conan's
        # default tools.build:jobs setting otherwise adds -j20 and causes
        # generated headers/dependency files to race or disappear. Keep the
        # OHOS package build serial and retain the host default elsewhere.
        if str(self.settings.os) == "OHOS":
            cmake.build(build_tool_args=["-j1"])
        else:
            cmake.build()

    def _ragel_binary(self):
        return os.path.join(self.build_folder, "ragel-prefix", "bin", "ragel")

    def _build_ragel(self):
        ragel_binary = self._ragel_binary()
        if os.path.isfile(ragel_binary):
            return

        ragel_source = os.path.join(self.source_folder, "ragel-source")
        configure = os.path.join(ragel_source, "configure")
        if not os.path.isfile(configure):
            raise ConanInvalidConfiguration(
                "Ragel 6.10 source archive is missing configure"
            )

        prefix = os.path.dirname(os.path.dirname(ragel_binary))
        configure_script = os.path.join(
            self.build_folder, "ragel-configure-hmdfs"
        )
        with open(configure, encoding="utf-8") as handle:
            configure_text = handle.read()
        # config.status creates a mode-700 temporary directory by default.
        # On the device HMDFS worker this prevents its generated awk script
        # from being reopened, so use a normal private build-directory mode.
        configure_text = configure_text.replace("umask 077", "umask 022")
        with open(configure_script, "w", encoding="utf-8") as handle:
            handle.write(configure_text)
        os.chmod(configure_script, 0o755)
        # HMDFS can report getcwd() failures for a directory created inside
        # the task folder immediately before launching a child process. Use
        # Conan's existing build folder as the configure working directory
        # and keep the source tree out-of-tree via --srcdir.
        self.run(
            "CC=clang CXX=clang++ PWD={} bash {} --srcdir={} --disable-manual --prefix={}".format(
                shlex.quote(self.build_folder),
                shlex.quote(configure_script),
                shlex.quote(ragel_source),
                shlex.quote(prefix),
            ),
            cwd=self.build_folder,
            env="conanbuild",
        )
        # The OHOS profile's Bash is suitable for configure, but its HMDFS
        # getcwd handling breaks recursive Autotools recipe commands. Force
        # the generated Makefiles to use the device POSIX shell.
        self.run("make SHELL=/bin/sh -j1", cwd=self.build_folder, env="conanbuild")
        self.run(
            "make SHELL=/bin/sh install",
            cwd=self.build_folder,
            env="conanbuild",
        )
        if not os.path.isfile(ragel_binary):
            raise ConanInvalidConfiguration(
                "Ragel 6.10 bootstrap completed without producing ragel"
            )

    def package(self):
        CMake(self).install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        # Examples/docs and the generated pkg-config file are not part of the
        # Conan CMake target contract; the consumer uses CMakeDeps instead.
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        hs_include_dir = os.path.join("include", "hs")

        hs = self.cpp_info.components["hs"]
        hs.set_property("pkg_config_name", "libhs")
        hs.set_property("cmake_target_name", "hs")
        hs.libs = ["hs"]
        # libhs exposes a C API but its static implementation is C++. Ask
        # CMakeDeps to use the C++ linker for C-language consumers so the
        # OHOS libc++ runtime is linked automatically.
        hs.languages = ["C++"]
        hs.requires = ["boost::boost_headers"]
        hs.includedirs = [hs_include_dir]

        hs_runtime = self.cpp_info.components["hs_runtime"]
        hs_runtime.set_property("cmake_target_name", "hs_runtime")
        hs_runtime.libs = ["hs_runtime"]
        hs_runtime.includedirs = [hs_include_dir]

        if str(self.settings.os) in ("Linux", "OHOS"):
            hs.system_libs = ["m"]
            hs_runtime.system_libs = ["m"]
            if str(self.settings.os) == "OHOS":
                # Classic CMakeDeps emits system_libs for C linkers too;
                # OHOS needs libc++ when a C consumer links static libhs.a.
                hs.system_libs.append("c++")

        if self.options.with_chimera:
            chimera = self.cpp_info.components["chimera"]
            chimera.set_property("pkg_config_name", "libch")
            chimera.set_property("cmake_target_name", "chimera")
            chimera.libs = ["chimera"]
            chimera.requires = ["pcre::pcre", "hs"]
            chimera.includedirs = [hs_include_dir]
            if str(self.settings.os) in ("Linux", "OHOS"):
                chimera.system_libs = ["m"]
