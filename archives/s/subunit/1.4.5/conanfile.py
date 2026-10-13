#!/usr/bin/env python3
"""Conan recipe — subunit 1.4.5 (C binding, OHOS PC / aarch64).

subunit is a streaming test-protocol library: this recipe packages the C
binding (libsubunit: child.c + child.h, Apache-2.0 / BSD-3-clause).  The
upstream GitHub tag tarball ships only autotools *inputs* (configure.ac,
Makefile.am — no generated configure, and regenerating one would need an
autotools chain the OHOS build hosts do not carry).  Since the C binding is
a single translation unit, the recipe contributes a minimal, reviewable
CMakeLists.txt (embedded in build(), written to the source root at build
time; cmake/CMakeLists.txt is a readable comparison, not an exported input)
that wraps exactly that translation unit — no upstream product sources are
modified. All six original C/Check cases are built and run through the
published test framework in a private temporary directory.

The Python binding (python/subunit, "python-subunit" on PyPI) and the
check-framework patches (c/check-subunit-*.patch, for the host-side check
library) are intentionally not packaged: they target a host toolchain and a
different consumer, and are tracked separately.
"""
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout
from conan.tools.build import cross_building


class SubunitConan(ConanFile):
    name = "subunit"
    version = "1.4.5"
    description = "subunit 1.4.5 — streaming test-protocol C binding (libsubunit)"
    license = "Apache-2.0 OR BSD-3-Clause"
    homepage = "https://github.com/testing-cabal/subunit"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "upstream_test.py"

    def build_requirements(self):
        self.test_requires("check/0.15.2#6d41c3078e77093b6b9dfe97b95e0f9c")

    # (包装不再走 export_sources:见 _CMAKE_WRAPPER 注释。仓库保留的
    #  cmake/CMakeLists.txt 仅作文档对照。)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # pure C binding
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        source_data = self.conan_data["sources"][self.version]
        get(self, url=source_data["url"], sha256=source_data["sha256"],
            filename="subunit-1.4.5.tar.gz", strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        framework = self.dependencies["check"].package_folder
        tc.variables["CHECK_STATIC_ARCHIVE"] = os.path.join(framework, "lib", "libcheck.a").replace("\\", "/")
        tc.variables["CHECK_HEADERS"] = os.path.join(framework, "include").replace("\\", "/")
        tc.generate()

    # 包装 CMakeLists 由配方内嵌字符串在 build() 写出——conan 的
    # copy()/export 链在本 CI cache 布局上四轮不可靠(65973/66029/66154/
    # 66367:导出落点被匹配前缀剥离拍平、candidates 全空等),字符串直写
    # 是零依赖路径。内容与仓库 cmake/CMakeLists.txt 保持一致。
    _CMAKE_WRAPPER = """cmake_minimum_required(VERSION 3.15)
project(subunit C)

# Minimal build script contributed by the OHOS PC packaging recipe: upstream
# 1.4.5 ships only autotools inputs (configure.ac, no generated configure),
# and regenerating it would require an autotools chain that the OHOS build
# hosts do not provide.  The C binding is a single translation unit, so a
# plain CMake wrapper around it is exact and reviewable.

add_library(subunit c/lib/child.c)
target_include_directories(subunit PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/c/include)
set_target_properties(subunit PROPERTIES
    OUTPUT_NAME subunit
    VERSION 1.4.5
    SOVERSION 0)
if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
    # Generic HarmonyOS CMake rules omit the usual SONAME flag.
    target_link_options(subunit PRIVATE "-Wl,-soname,libsubunit.so")
endif()

# Run the original complete C binding suite, not a replacement smoke test.
enable_testing()
add_executable(test_child c/tests/test_child.c)
target_include_directories(test_child PRIVATE ${CHECK_HEADERS})
target_link_libraries(test_child PRIVATE subunit ${CHECK_STATIC_ARCHIVE})
if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS")
    target_link_options(test_child PRIVATE "-Wl,-rpath,$ORIGIN")
endif()
if(UNIX)
    target_link_libraries(test_child PRIVATE m rt pthread)
endif()
add_test(NAME upstream-child COMMAND test_child)

include(GNUInstallDirs)
install(TARGETS subunit
        LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
        ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR})
install(FILES c/include/subunit/child.h
        DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/subunit)
"""

    def build(self):
        # 写到 CMake.configure() 的源目录(源根,含 c/)。
        wrapper_path = os.path.join(self.source_folder, "CMakeLists.txt")
        with open(wrapper_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(self._CMAKE_WRAPPER)
        self.output.info("wrapper written: %s" % wrapper_path)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if cross_building(self):
            self.output.info("Upstream suite compiled only; target execution remains required")
            return
        binary = os.path.join(self.build_folder, "test_child")
        if str(self.settings.os) == "OHOS":
            signer = shutil.which("binary-sign-tool")
            if not signer:
                raise ConanException("Native binary-sign-tool required")
            if self.options.shared:
                library = os.path.realpath(os.path.join(self.build_folder, "libsubunit.so"))
                if os.path.commonpath([library, os.path.realpath(self.build_folder)]) != os.path.realpath(self.build_folder):
                    raise ConanException("Shared library escaped this build directory")
                signed_library = library + ".signed"
                subprocess.run([signer, "sign", "-inFile", library, "-outFile", signed_library, "-selfSign", "1"], check=True)
                os.chmod(signed_library, 0o700)
                os.replace(signed_library, library)
            signed = binary + ".signed"
            subprocess.run([signer, "sign", "-inFile", binary, "-outFile", signed, "-selfSign", "1"], check=True)
            os.chmod(signed, 0o700)
            binary = signed
        script = os.path.join(self.export_sources_folder, "upstream_test.py")
        subprocess.run([sys.executable, script, "--source", self.source_folder,
                        "--binary", binary, "--output", os.path.join(self.build_folder, "upstream-evidence")],
                       check=True, timeout=120)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # dual-license files travel with the sources
        copy(self, "Apache-2.0", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "BSD", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["subunit"]
        self.cpp_info.includedirs = [os.path.join("include", "subunit", "..")]
        self.cpp_info.includedirs = ["include"]
