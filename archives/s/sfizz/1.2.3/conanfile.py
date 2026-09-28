#!/usr/bin/env python3
"""Conan recipe for sfizz 1.2.3 — CMake project.

sfizz is a SFZ parser and synth C++ library, with an offline render CLI
(sfizz_render); JACK standalone client disabled by default. The upstream
source tarball does not include its git submodules
(external/abseil-cpp, external/filesystem, external/simde and the
st_audiofile third-party dirs), so source() fetches each pinned submodule
commit from the official codeload.github.com URLs.
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class SfizzConan(ConanFile):
    name = "sfizz"
    version = "1.2.3"
    description = "SFZ parser and synth C++ library, with an offline render CLI (sfizz_render); JACK standalone client disabled by default"
    license = "BSD-2-Clause"
    homepage = "https://github.com/sfztools/sfizz"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Fetch pinned git submodules missing from the source tarball.
        # Each entry carries the locked-commit tarball sha256 (verified locally).
        submodules = {
            "external/abseil-cpp": ("https://codeload.github.com/abseil/abseil-cpp/tar.gz/c2435f8342c2d0ed8101cb43adfd605fdc52dca2", "abseil-cpp", "9892836ab0d3f099b8c15076c6f4168144f452d097bd49da215fe0df36a2d48c"),
            "external/filesystem": ("https://codeload.github.com/gulrak/filesystem/tar.gz/8a2edd6d92ed820521d42c94d179462bf06b5ed3", "filesystem", "3742a0d47da885da0e671008d72e7de5b7dbc3ccd3eed731166268b52e176cd4"),
            "external/simde": ("https://codeload.github.com/simd-everywhere/simde/tar.gz/2bf459d4ed6d7ed6b9f31bd9e07c91bace5009e0", "simde", "03f466eae94075d8bf5224d81eb9a396d2acfd2a37fc622d0941dfba1bf52e5d"),
            "external/st_audiofile/thirdparty/dr_libs": ("https://codeload.github.com/mackron/dr_libs/tar.gz/4b3d07849537ce0b71b22180c0b1335eacc6e9be", "dr_libs", "65ecc2859a85457bd6ded7956d4773044edff0cc6ca84a5e0fcbd86e47278a2e"),
            "external/st_audiofile/thirdparty/libaiff": ("https://codeload.github.com/sfztools/libaiff/tar.gz/78864a4a2e769e426be8cfd78ae7f5f72e236c33", "libaiff", "a0db06448a9cf8de4df08f40d7ad7169c73e97b78a4477feb31dfbd2662277df"),
            "external/st_audiofile/thirdparty/wavpack": ("https://codeload.github.com/dbry/WavPack/tar.gz/07ffb331d23c16e2d2979370441f63ea722760bc", "wavpack", "d96f0b92720cd222eb869ad0db1068bfd5abc5f9dc37746ebce68ba73c4790f4"),
        }
        for dest, (url, name, sha) in submodules.items():
            get(self, url=url, destination=dest, strip_root=True,
                filename=name + ".tar.gz", sha256=sha)

    def generate(self):
        tc = CMakeToolchain(self)
        # 注意：BUILD_SHARED_LIBS 由补丁 0001 在顶层 CMakeLists 以普通变量设为 OFF
        # （Conan SharedLibBock 会以 CACHE 变量覆盖 tc.variables 设置，配方层无效）
        # sfizz project options
        tc.variables["SFIZZ_SHARED"] = "ON" if self.options.shared else "OFF"
        tc.variables["SFIZZ_TESTS"] = "OFF"
        tc.variables["BUILD_TESTING"] = "OFF"
        tc.variables["SFIZZ_RENDER"] = "ON"
        tc.variables["SFIZZ_JACK"] = "OFF"
        tc.variables["SFIZZ_USE_SNDFILE"] = "OFF"
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        # OHOS 平台无 Platform/HarmonyOS.cmake，CMake 不会自动生成 DT_SONAME。
        # 包内实际安装文件名为 libsfizz.so（无版本号符号链接），SONAME 必须与之一致，
        # 否则下游按 SONAME 寻址找不到库。该补偿仅对 OHOS 目标生效。
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = "-Wl,-soname,libsfizz.so"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["sfizz"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
