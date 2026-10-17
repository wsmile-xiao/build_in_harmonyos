#!/usr/bin/env python3
"""Conan recipe — libdwarfp 2.1.0.

libdwarfp — the DWARF *producer* (write) library of the libdwarf
project, packaged separately from its consumer (read) library.
构建系统：CMake
平台：OHOS aarch64 / Linux / Windows / macOS
链接闭包：静态 libdwarfp.a 对消费者库公开符号（dwarf_encode_leb128
等）存在未定义引用，而 libdwarfp/2.1.0 无法独立于 libdwarf 工程构建
（上游 dwarfp 目标与 libdwarf 同工程且 PRIVATE 链接 dwarf），因此本
包连同同工程的消费者库一起打包：cpp_info.libs 同时含 dwarfp + dwarf
（同 libdwarf 配方 with_dwarfgen=True 路径的打包形态）。

上游要点（v2.1.0）：
- libdwarfp 目标只在 BUILD_DWARFGEN=TRUE 时进入构建
  （顶层 CMakeLists.txt: if (BUILD_DWARFGEN) add_subdirectory(src/lib/libdwarfp)），
  因此本配方必须连同整个 libdwarf 工程一起构建。
- 上游测试入口是 -DDO_TESTING=ON + ctest（上游没有 BUILD_TESTING 选项）。

Based on the upstream conan-center-index recipe, adapted for HarmonyOS PC.
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rename, rm, rmdir
from conan.tools.scm import Version


class LibdwarfpConan(ConanFile):
    name = "libdwarfp"
    version = "2.1.0"
    description = "DWARF producer (write) library from the libdwarf project"
    license = "LGPL-2.1-only"
    homepage = "https://www.prevanders.net/dwarf.html"
    url = ""
    topics = ("debug", "dwarf", "dwarf2", "elf", "producer")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_NON_SHARED"] = not self.options.shared
        tc.variables["BUILD_SHARED"] = self.options.shared
        #  libdwarfp target is only added to the build when BUILD_DWARFGEN
        #  is TRUE (upstream gate), which also builds the dwarfgen tool.
        #  The tool is stripped from the package in package().
        tc.variables["BUILD_DWARFGEN"] = True
        tc.variables["BUILD_DWARFDUMP"] = False
        tc.variables["BUILD_DWARFEXAMPLE"] = False
        #  Upstream testing entry point: DO_TESTING (there is no
        #  BUILD_TESTING option in libdwarf 2.1.0).
        tc.variables["DO_TESTING"] = True
        if cross_building(self):
            tc.variables["HAVE_UNUSED_ATTRIBUTE_EXITCODE"] = "0"
            tc.variables["HAVE_UNUSED_ATTRIBUTE_EXITCODE__TRYRUN_OUTPUT"] = ""
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        #  Upstream self-contained unit tests (selfteststring,
        #  selftestextrastring, selfleb, selftied, ... 20 targets).
        #  The selfdwarfdump* regression tests drive the dwarfdump
        #  binary via python3; dwarfdump is not part of this package
        #  build (BUILD_DWARFDUMP=OFF), so they are excluded here.
        #  The full upstream suite (26/26 incl. selfdwarfdump* and the
        #  BUILD_DWARFEXAMPLE tests) was verified passing natively on
        #  the OHOS aarch64 device; see notes.md.
        ctest_filter = 'ctest --test-dir "{}" --output-on-failure -E selfdwarfdump'.format(
            self.build_folder
        )
        self.run(ctest_filter)

    def package(self):
        copy(
            self,
            pattern="COPYING",
            dst=os.path.join(self.package_folder, "licenses"),
            src=os.path.join(self.source_folder, "src", "lib", "libdwarfp"),
        )
        rename(
            self,
            os.path.join(self.package_folder, "licenses", "COPYING"),
            os.path.join(self.package_folder, "licenses", "COPYING-libdwarfp"),
        )
        #  The consumer-library headers/archives shipped by this package
        #  carry their own license copy.
        copy(
            self,
            pattern="COPYING",
            dst=os.path.join(self.package_folder, "licenses"),
            src=os.path.join(self.source_folder, "src", "lib", "libdwarf"),
        )
        rename(
            self,
            os.path.join(self.package_folder, "licenses", "COPYING"),
            os.path.join(self.package_folder, "licenses", "COPYING-libdwarf"),
        )

        cmake = CMake(self)
        cmake.install()

        #  Keep the producer library AND the consumer library it needs
        #  at link time (static libdwarfp.a references consumer public
        #  symbols); strip tools and project packaging metadata.
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        #  Both archives: libdwarfp.a carries undefined references to
        #  consumer-lib public symbols (dwarf_encode_leb128, ...) and
        #  both come from the same upstream project/build here.
        self.cpp_info.libs = ["dwarfp", "dwarf"]
        #  For static builds (>= 2.1.0), define LIBDWARF_STATIC=1
        if Version(self.version) >= "2.1.0" and not self.options.shared:
            self.cpp_info.defines = ["LIBDWARF_STATIC=1"]
