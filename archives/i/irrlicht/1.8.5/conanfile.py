#!/usr/bin/env python3
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class IrrlichtConan(ConanFile):
    name = "irrlicht"
    version = "1.8.5"
    description = "Cross-platform realtime 3D engine written in C++"
    license = "Zlib"
    homepage = "https://irrlicht.sourceforge.io/"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

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
            raise ConanInvalidConfiguration("irrlicht/1.8.5 recipe is validated only for Linux and OHOS")

    def requirements(self):
        self.requires("zlib/1.3.1.1")
        self.requires("libpng/1.6.58")
        self.requires("libjpeg/10")
        self.requires("bzip2/1.0.8")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.generate()

    def _config_shell(self):
        return os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

    def _compiler_executable(self, lang, fallback):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return compilers.get(lang, fallback)

    def _make_vars(self):
        cc = self._compiler_executable("c", "clang")
        cxx = self._compiler_executable("cpp", "clang++")
        ar = self._compiler_executable("ar", "llvm-ar")
        ranlib = self._compiler_executable("ranlib", "llvm-ranlib")
        ndebug = "1" if str(self.settings.build_type) != "Debug" else ""
        fpic = "-fPIC" if self.options.get_safe("fPIC", True) else ""

        disabled_platforms = [
            "NO_IRR_COMPILE_WITH_X11_",
            "NO_IRR_COMPILE_WITH_SDL_DEVICE_",
            "NO_IRR_COMPILE_WITH_FB_DEVICE_",
            "NO_IRR_COMPILE_WITH_OSX_DEVICE_",
            "NO_IRR_COMPILE_WITH_WINDOWS_DEVICE_",
            "NO_IRR_COMPILE_WITH_WINDOWS_CE_DEVICE_",
            "NO_IRR_COMPILE_WITH_DIRECT3D_8_",
            "NO_IRR_COMPILE_WITH_DIRECT3D_9_",
            "NO_IRR_COMPILE_WITH_OPENGL_",
            "NO_IRR_COMPILE_WITH_OPENGLES1_",
            "NO_IRR_COMPILE_WITH_OPENGLES2_",
        ]
        platform_defs = " ".join(f"-D{name}" for name in disabled_platforms)
        if fpic:
            platform_defs = f"{platform_defs} {fpic}"

        # 上游 Makefile 缺 %.o:%.cpp 编译 rule（只有 %.d:%.cpp 建依赖
        # 和 %.o:%.mm Objective-C），.cpp→.o 走 make <builtin> 内置规则，
        # 只引 $(CXXFLAGS) 不引 $(CXXINCS)/$(CPPFLAGS)。所以无论命令行
        # 怎么传 CXXINCS="-I../../include ..."，编译命令里都没 -I 标志，
        # 触发 fatal error: 'IrrCompileConfig.h' file not found（头文件
        # 在源码顶层 include/，make 在 source/Irrlicht/ 跑）。
        # 改为：把 -I../../include 及依赖 include 标志挪到 CXXFLAGS
        # （builtin rule 引 $(CXXFLAGS)），platform defs 也挪到 CXXFLAGS
        # 避免 CPPFLAGS 覆盖 Makefile 第 67 行 CPPFLAGS += $(CXXINCS)。
        cxxincs = "-I../../include -Izlib -Ijpeglib -Ilibpng"
        cxxflags_extra = f"{cxxincs} {platform_defs}"

        return (
            f'CC="{cc}" '
            f'CXX="{cxx}" '
            f'AR="{ar}" '
            f'RANLIB="{ranlib}" '
            f'NDEBUG="{ndebug}" '
            f'CXXFLAGS="{cxxflags_extra}"'
        )

    def _make_cmd(self, target):
        shell = self._config_shell()
        cmd = f"make {self._make_vars()} {target} -j1"
        return f"{shell} -lc {shlex.quote(cmd)}"

    def build(self):
        apply_conandata_patches(self)

        makefile_dir = os.path.join(self.source_folder, "source", "Irrlicht")
        self.run(self._make_cmd("sharedlib staticlib"), cwd=makefile_dir, env="conanbuild")

    def package(self):
        makefile_dir = os.path.join(self.source_folder, "source", "Irrlicht")
        install_dir = os.path.join(self.package_folder, "lib")
        self.run(
            f'{self._config_shell()} -lc {shlex.quote(f"make {self._make_vars()} install INSTALL_DIR={install_dir} -j1")}',
            cwd=makefile_dir,
            env="conanbuild",
        )
        from conan.tools.files import copy
        licenses = os.path.join(self.package_folder, "licenses")
        copy(self, "irrlicht-license.txt", src=os.path.join(self.source_folder, "doc"), dst=licenses)

    def package_info(self):
        self.cpp_info.libs = ["Irrlicht"]
        self.cpp_info.includedirs = ["include/irrlicht"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "Irrlicht")
        self.cpp_info.set_property("cmake_target_name", "Irrlicht::Irrlicht")
        self.cpp_info.requires = [
            "zlib::zlib",
            "libpng::libpng",
            "libjpeg::libjpeg",
            "bzip2::bzip2",
        ]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
