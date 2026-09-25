#!/usr/bin/env python3
"""Conan recipe — rkcommon 1.15.2 (cmake)"""
from conan import ConanFile
from conan.tools.files import collect_libs, get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
import os


class RkcommonConan(ConanFile):
    name = "rkcommon"
    version = "1.15.2"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder=".")

    def generate(self):
        tc = CMakeToolchain(self)
        # 同 hdf5 路线：conan 默认 CMAKE_SYSTEM_NAME=HarmonyOS 与平台文件 OHOS.cmake 不匹配，
        # 不显式指回 OHOS 会丢 SONAME 并传染下游 DT_NEEDED。
        tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
        tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.variables["BUILD_SHARED_LIBS"] = True
        # 上游测试（bundled catch 单套件 16 个 CTest 注册项）随构建真实执行。
        tc.variables["BUILD_TESTING"] = "ON"
        # tasking 用源内捆绑 enkiTS：上游用户开关是缓存变量 RKCOMMON_TASKING_SYSTEM（默认 TBB），
        # 设 Internal 走自带 enkiTS，不引 TBB 外部依赖；RKCOMMON_TASKING_TBB 是宏输出变量，设了会被覆盖。
        tc.variables["RKCOMMON_TASKING_SYSTEM"] = "Internal"
        tc.variables["RKCOMMON_WARN_AS_ERRORS"] = "OFF"
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        CMake(self).install()
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # 鸿蒙 PC XPM 要求 dlopen 的 .so 代码签名，否则加载报 Permission denied。
        import glob
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.libs = collect_libs(self)
        self.cpp_info.set_property("cmake_file_name", "rkcommon")
        self.cpp_info.set_property("cmake_target_name", "rkcommon::rkcommon")
        pkg = self._detect_pkg_config_name()
        if pkg:
            self.cpp_info.set_property("pkg_config_name", pkg)

    def _detect_pkg_config_name(self):
        import glob
        pcs = sorted(glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")))
        if not pcs:
            return ""
        return os.path.splitext(os.path.basename(pcs[0]))[0]
