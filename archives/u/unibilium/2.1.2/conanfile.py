#!/usr/bin/env python3
"""Conan recipe for unibilium 2.1.2 on HarmonyOS PC (aarch64).

unibilium is a very basic terminfo library: it can read and write
ncurses-style terminfo files and interpret terminfo format strings.
It depends on no curses or any other library.

Build: upstream provides both autotools (needs autoreconf/automake) and a
       CMakeLists.txt.  This recipe uses the CMake path because it is
       self-contained (a C compiler is all that is required) and CI has no
       automake available.
"""
import os
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, save, export_conandata_patches, apply_conandata_patches


class UnibiliumConan(ConanFile):
    name = "unibilium"
    version = "2.1.2"
    package_type = "library"
    description = "Very basic terminfo library (no curses dependency)"
    license = "MIT"
    homepage = "https://github.com/neovim/unibilium"
    url = "https://github.com/neovim/unibilium"

    settings = "os", "compiler", "build_type", "arch"

    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 纯 C 库，无外部依赖（不依赖 curses）
        pass

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # TERMINFO_DIRS 为编译期宏，上游 CMakeLists 在 configure 阶段探测
        # ncurses*-config 获取；CI 与本机构建环境均无 ncurses*-config，显式
        # 指定与上游 fallback 一致的默认值，保证编译结果可复现（P3-1）。
        tc.variables["TERMINFO_DIRS"] = (
            "/etc/terminfo:/lib/terminfo:/usr/share/terminfo:"
            "/usr/lib/terminfo:/usr/local/share/terminfo:/usr/local/lib/terminfo"
        )
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream CMakeLists.txt installs only the library and header;
        # libtermkey and other consumers locate unibilium via pkg-config,
        # so ship the .pc file.  The file lives at <prefix>/lib/pkgconfig,
        # so ${pcfiledir}/../.. resolves to the prefix (pkg-config defines
        # ${pcfiledir} automatically at parse time).
        # 若上游 CMake 未来开始安装同名 .pc，则直接复用上游产物，
        # 避免手工生成内容与上游模板漂移（P2-1）。覆盖 lib 与 lib64
        # 两种常见布局（P3 R2-2：不硬编码 lib）。
        installed_pc = None
        for libsub in ("lib", "lib64"):
            cand = os.path.join(self.package_folder, libsub,
                                "pkgconfig", "unibilium.pc")
            if os.path.exists(cand):
                installed_pc = cand
                break
        if installed_pc:
            self.output.info(f"upstream already installed unibilium.pc, "
                             f"reuse it: {installed_pc}")
        else:
            libdir = os.path.join(self.package_folder, "lib")
            pc_path = os.path.join(libdir, "pkgconfig", "unibilium.pc")
            os.makedirs(os.path.join(libdir, "pkgconfig"), exist_ok=True)
            pc = textwrap.dedent(f"""\
                prefix=${{pcfiledir}}/../..
                libdir=${{prefix}}/lib
                includedir=${{prefix}}/include
                version={self.version}

                Name: unibilium
                Description: terminfo parser and utility functions
                Version: ${{version}}
                Libs: -L${{libdir}} -lunibilium
                Cflags: -I${{includedir}}
                """)
            save(self, pc_path, pc)

    def package_info(self):
        self.cpp_info.libs = ["unibilium"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "unibilium")
        self.cpp_info.set_property("cmake_target_name", "unibilium::unibilium")
        self.cpp_info.set_property("pkg_config_name", "unibilium")