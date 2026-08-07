#!/usr/bin/env python3
"""Conan recipe for libxc 7.1.0."""

import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibxcConan(ConanFile):
    name = "libxc"
    version = "7.1.0"
    description = "Exchange-correlation functionals for density-functional theory"
    license = "MPL-2.0"
    homepage = "https://libxc.gitlab.io/"
    url = "https://gitlab.com/libxc/libxc"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_tests": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_tests": False,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if bool(self.options.shared):
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="libxc-7.1.0.tar.gz",
            strip_root=True,
        )

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        self._set_cmake_variables(tc.variables)
        tc.generate()

    def _set_cmake_variables(self, variables):
        variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        variables["BUILD_FPIC"] = bool(
            self.options.get_safe("fPIC", default=True)
        )
        variables["BUILD_TESTING"] = bool(self.options.with_tests)
        variables["ENABLE_FORTRAN"] = False
        variables["ENABLE_PYTHON"] = False
        variables["ENABLE_CUDA"] = False
        variables["ENABLE_HIP"] = False
        variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        variables["NAMESPACE_INSTALL_INCLUDEDIR"] = "/"

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            self._build_ohos()
            return

        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if bool(self.options.with_tests):
            cmake.test()

    def _build_ohos(self):
        toolchain = self._ohos_toolchain()
        ninja = shutil.which("ninja")
        if not ninja:
            raise ConanInvalidConfiguration("OHOS CMake build requires ninja in PATH")
        ar = self._find_ohos_tool(
            "llvm-ar",
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin/llvm-ar",
        )
        ranlib = self._find_ohos_tool(
            "ranlib",
            "/data/service/hnp/binutils.org/*/bin/ranlib",
        )
        if not ar or not ranlib:
            raise ConanInvalidConfiguration("OHOS static build requires ar and ranlib")
        build_dir = os.path.join(self.build_folder, "build-ohos")
        defs = {
            "CMAKE_TOOLCHAIN_FILE": toolchain,
            "OHOS_ARCH": "arm64-v8a",
            "CMAKE_BUILD_TYPE": str(self.settings.build_type),
            "CMAKE_MAKE_PROGRAM": ninja,
            "CMAKE_AR": ar,
            "CMAKE_RANLIB": ranlib,
            "BUILD_SHARED_LIBS": "ON" if bool(self.options.shared) else "OFF",
            "BUILD_FPIC": "ON"
            if bool(self.options.get_safe("fPIC", default=True))
            else "OFF",
            "BUILD_TESTING": "ON" if bool(self.options.with_tests) else "OFF",
            "ENABLE_FORTRAN": "OFF",
            "ENABLE_PYTHON": "OFF",
            "ENABLE_CUDA": "OFF",
            "ENABLE_HIP": "OFF",
            "CMAKE_INSTALL_LIBDIR": "lib",
            "NAMESPACE_INSTALL_INCLUDEDIR": "/",
        }
        cmake_defs = " ".join(
            '-D{}="{}"'.format(key, str(value).replace('"', '\\"'))
            for key, value in defs.items()
        )
        self.run(
            'cmake -G Ninja -B "{}" -S "{}" {}'.format(
                build_dir, self.source_folder, cmake_defs
            )
        )
        self.run('cmake --build "{}"'.format(build_dir))
        if bool(self.options.with_tests):
            self.run('ctest --test-dir "{}" --output-on-failure'.format(build_dir))

    def _ohos_toolchain(self):
        user_toolchains = self.conf.get(
            "tools.cmake.cmaketoolchain:user_toolchain",
            default=[],
            check_type=list,
        )
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        candidates = list(user_toolchains)
        if ndk:
            candidates.append(
                os.path.join(ndk, "build", "cmake", "ohos.toolchain.cmake")
            )
        candidates.extend(
            sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/"
                    "ohos.toolchain.cmake"
                )
            )
        )
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        raise ConanInvalidConfiguration(
            "OHOS build requires ohos.toolchain.cmake; set OHOS_NDK_HOME "
            "or tools.cmake.cmaketoolchain:user_toolchain"
        )

    def package(self):
        if str(self.settings.os) == "OHOS":
            build_dir = os.path.join(self.build_folder, "build-ohos")
            self.run(
                'cmake --install "{}" --prefix "{}"'.format(
                    build_dir, self.package_folder
                )
            )
            self._sign_shared_libs()
        else:
            CMake(self).install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def _sign_shared_libs(self):
        libdir = os.path.join(self.package_folder, "lib")
        shared_libs = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        shared_libs += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not shared_libs:
            return
        objcopy = self._find_ohos_tool(
            "llvm-objcopy",
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin/llvm-objcopy",
        )
        signer = self._find_ohos_tool(
            "binary-sign-tool",
            "/data/service/hnp/ohos-sdk.org/*/ohos/toolchains/lib/binary-sign-tool",
        )
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS shared library signing requires llvm-objcopy and binary-sign-tool"
            )
        for shared_lib in shared_libs:
            if os.path.islink(shared_lib):
                continue
            self.run(
                '{objcopy} --remove-section .codesign "{lib}" 2>/dev/null || true'.format(
                    objcopy=objcopy, lib=shared_lib
                )
            )
            self.run(
                '{signer} sign -inFile "{lib}" -outFile "{lib}" -selfSign 1'.format(
                    signer=signer, lib=shared_lib
                )
            )

    def _find_ohos_tool(self, tool_name, fallback_glob):
        tool = shutil.which(tool_name)
        if tool:
            return tool
        matches = sorted(glob.glob(fallback_glob))
        if matches:
            return matches[-1]
        return None

    def package_info(self):
        self.cpp_info.libs = ["xc"]
        self.cpp_info.set_property("cmake_file_name", "Libxc")
        self.cpp_info.set_property("cmake_target_name", "Libxc::xc")
        self.cpp_info.set_property("pkg_config_name", "libxc")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
