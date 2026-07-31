#!/usr/bin/env python3
"""Conan recipe for libitl 0.8.0 (Islamic Tools and Libraries).

CMake project (hijri + prayertime). Debian patches enable shared library,
GNUInstallDirs install paths, and C99 forward declarations.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class LibitlConan(ConanFile):
    name = "libitl"
    version = "0.8.0"
    description = (
        "Islamic Tools and Libraries — Hijri/Gregorian conversion "
        "and Muslim prayer time / Qibla calculations"
    )
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/arabeyes-org/ITL"
    url = "https://github.com/arabeyes-org/ITL"
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
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def validate(self):
        os_name = str(self.settings.os)
        if os_name not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libitl is packaged for Linux/OHOS")
        if os_name == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("libitl supports OHOS armv8 only")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream CMake always builds both static and shared (Debian patch);
        # BUILD_SHARED_LIBS is unused by the project.
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = self.options.get_safe(
            "fPIC", True
        )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream CMake has no ctest suite; demos are built as smoke targets.
        # Resolve demo binaries under the CMake build tree (not package bin/).
        if not cross_building(self):
            build_type = str(self.settings.build_type)
            candidates_roots = (
                self.build_folder,
                os.path.join(self.build_folder, build_type),
            )
            for demo in ("demo_hijri", "demo_prayer"):
                demo_path = None
                for root in candidates_roots:
                    cand = os.path.join(root, demo)
                    if os.path.isfile(cand):
                        demo_path = cand
                        break
                if demo_path is None:
                    raise ConanException(f"{demo} not found under {self.build_folder}")
                ret = self.run(demo_path, env="conanrun")
                if ret != 0:
                    raise ConanException(f"{demo} smoke test failed with code {ret}")

    def package(self):
        copy(
            self,
            "COPYING",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )
        cmake = CMake(self)
        cmake.install()
        # Prefer shared or static artifact according to the option.
        libdir = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            for pattern in ("*.a",):
                for path in glob.glob(os.path.join(libdir, pattern)):
                    os.remove(path)
        else:
            for path in glob.glob(os.path.join(libdir, "*.so*")):
                if os.path.islink(path) or os.path.isfile(path):
                    os.remove(path)
        self._sign_shared_libraries()

    def _sign_shared_libraries(self):
        if not self.options.shared or str(self.settings.os) != "OHOS":
            return
        libraries = glob.glob(
            os.path.join(self.package_folder, "lib", "**", "*.so*"), recursive=True
        )
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            # 无真机签名工具时跳过（容器/非真机验证场景）
            self.output.warning(
                "OHOS signing tools not found; skipping ELF self-sign"
            )
            return
        for library in libraries:
            if os.path.islink(library):
                continue
            ret = self.run('{} --remove-section .codesign "{}"'.format(objcopy, library))
            if ret != 0:
                raise ConanException(f"objcopy failed for {library}")
            ret = self.run(
                '{} sign -inFile "{}" -outFile "{}" -selfSign 1'.format(
                    signer, library, library
                )
            )
            if ret != 0:
                raise ConanException(f"sign failed for {library}")

    def package_info(self):
        self.cpp_info.libs = ["itl"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "libitl")
        self.cpp_info.set_property("cmake_target_name", "libitl::libitl")
        self.cpp_info.set_property("pkg_config_name", "libitl")
