#!/usr/bin/env python3
"""Conan recipe — msgpack-c 7.0.1 (msgpack for C).

msgpack-c 7.0.1 is a real compiled C library (NOT header-only): the upstream
CMakeLists.txt builds libmsgpack-c from src/{objectc,unpack,version,
vrefbuffer,zone}.c and installs it together with the public C headers under
include/msgpack/ plus msgpack-c.pc and the CMake config package.

It has no runtime dependencies (only the C standard library). The upstream
unit tests (test/*.cpp) require GTest + ZLIB and are disabled here via
MSGPACK_BUILD_TESTS=OFF; examples and coverage are likewise disabled.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    collect_libs,
    copy,
    export_conandata_patches,
    get,
    load,
    save,
)


class MsgpackConan(ConanFile):
    name = "msgpack"
    version = "7.0.1"
    description = "MessagePack for C — binary-based efficient object serialization library"
    license = "BSL-1.0"
    homepage = "https://github.com/msgpack/msgpack-c"
    url = ""  # CI fills this

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

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"msgpack is validated only for Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        # Pass retry/retry_wait as explicit ints so get() does not fall back to
        # the profile conf tools.files.download:retry_wait (which the OHOS
        # profile sets to the str "0s" — rejected by Conan 2.x as non-int).
        get(
            self,
            **self.conan_data["sources"],
            strip_root=True,
            retry=2,
            retry_wait=5,
        )

    def generate(self):
        tc = CMakeToolchain(self)
        # R26: system-name libraries default to static.
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Disable non-essential upstream targets, confirmed from 7.0.1 CMakeLists.txt.
        tc.variables["MSGPACK_BUILD_TESTS"] = False
        tc.variables["MSGPACK_BUILD_EXAMPLES"] = False
        tc.variables["MSGPACK_GEN_COVERAGE"] = False
        # Select shared/static artifacts explicitly (upstream has MSGPACK_ENABLE_*).
        tc.variables["MSGPACK_ENABLE_SHARED"] = bool(self.options.shared)
        tc.variables["MSGPACK_ENABLE_STATIC"] = not bool(self.options.shared)
        if not self.options.shared and self.options.get_safe("fPIC"):
            tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        if self.settings.os == "OHOS":
            # CMake has no built-in HarmonyOS platform module. Complete its
            # shared-linker contract so in-tree consumers record basename
            # SONAMEs and a build-only runtime path (same approach as jsoncpp).
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

    def build(self):
        apply_conandata_patches(self)
        self._redirect_ci_compilers()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _redirect_ci_compilers(self):
        """Point CMake/env scripts at the real compiler when run off a CI worker.

        The OHOS profile pins tools.build:compiler_executables and [buildenv] to
        /data/service/hnp/bin/{clang,clang++,bash}, which only exist on CI
        release workers. Conan bakes those absolute paths into
        conan_toolchain.cmake (set(CMAKE_C_COMPILER ...)) and the conanbuildenv
        *.sh scripts. On a developer machine those paths are absent and CMake
        configure dies with "is not a full path to an existing compiler".

        speex/1.2.1 established the validated pattern: detect that the hnp
        prefix is missing and rewrite every generator artifact to the local
        clang/clang++/bash discovered via PATH. On CI the hnp prefix exists and
        this is a no-op. We never touch the ci/ tree itself.
        """
        if os.path.exists("/data/service/hnp/bin/clang"):
            return
        import shutil

        bash = shutil.which("bash") or "bash"
        cc = shutil.which("clang") or "clang"
        cxx = shutil.which("clang++") or "clang++"
        gen = getattr(self, "generators_folder", "") or ""
        if not gen or not os.path.isdir(gen):
            return
        for name in os.listdir(gen):
            path = os.path.join(gen, name)
            if not os.path.isfile(path):
                continue
            content = load(self, path)
            if "/data/service/hnp/bin/" not in content:
                continue
            content = content.replace("/data/service/hnp/bin/bash", bash)
            content = content.replace("/data/service/hnp/bin/clang++", cxx)
            content = content.replace("/data/service/hnp/bin/clang", cc)
            save(self, path, content)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE_1_0.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = collect_libs(self)
        # The upstream CMake config package is msgpack-c-config.cmake and the
        # pkg-config file is msgpack-c.pc; expose both so consumers can use
        # find_package(msgpack-c) / pkg-config --cflags msgpack-c.
        self.cpp_info.set_property("cmake_file_name", "msgpack-c")
        self.cpp_info.set_property("cmake_target_name", "msgpack-c::msgpack-c")
        self.cpp_info.set_property("pkg_config_name", "msgpack-c")
