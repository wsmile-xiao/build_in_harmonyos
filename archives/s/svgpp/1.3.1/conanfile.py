#!/usr/bin/env python3
"""Conan recipe for svgpp 1.3.1 - a header-only C++ SVG parsing library.

svgpp turns SVG attribute values (path data, transforms, colours, lengths,
view boxes) and whole SVG documents into calls on a user supplied context
object.  It ships no compiled code: the upstream INSTALL file says "As SVG++
is a header-only library, no installation is required. Just add path to
'include' subfolder to your project include dirs."

Boost is a *public* dependency: 79 headers below include/svgpp include Boost
headers (mpl 76, preprocessor 32, spirit 23, phoenix, range, fusion, optional,
gil, ...), therefore consumers must see the Boost include directories.  The
package follows templates/conanfile-headeronly.py.tmpl (variant A) and the
merged header-only precedent archives/b/burst/3.1.1.

Layer 1 of docs/TEST_QUALITY_SPEC.md is executed inside build(): the upstream
GoogleTest suite (single binary ParserGTest from src/test, vendored
third_party/googletest sources) is configured as a standalone CMake project
with zero upstream file modifications and run on the build machine.  The
mechanism (standalone src/test configuration + -DCMAKE_PROJECT_INCLUDE
injection + OHOS->Linux CMake platform model) is the one proven out-of-band in
notes.md「关键适配点」8/9 and follows the merged burst/3.1.1 precedent.

Adaptation notes: archives/s/svgpp/1.3.1/notes.md
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.layout import basic_layout


class SvgppConan(ConanFile):
    name = "svgpp"
    version = "1.3.1"
    description = ("Header-only C++ SVG parser: Boost.Spirit grammars and "
                   "policies for path data, transforms, colours, lengths and "
                   "SVG document traversal")
    license = "BSL-1.0"
    homepage = "https://github.com/svgpp/svgpp"
    url = "https://github.com/svgpp/svgpp"
    topics = ("svg", "parser", "path", "transform", "header-only", "boost")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        # Standard conandata hook: exports the patch files declared in
        # conandata.yml.  This package ships zero patches ("patches: {}"), so
        # the call exports nothing; it is kept so that a future adaptation fix
        # only has to declare the patch, exactly as in the merged header-only
        # precedent archives/b/burst/3.1.1.
        export_conandata_patches(self)

    def requirements(self):
        # Public svgpp headers #include <boost/...> (Spirit/Qi, MPL, Phoenix,
        # Range, Fusion), so the Boost headers have to be visible to any
        # consumer of this package.
        self.requires("boost/1.90.0", transitive_headers=True)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if self.settings.compiler.cppstd:
            check_min_cppstd(self, "11")

    def generate(self):
        # The toolchain here is *not* used to produce package content (this is
        # a header-only package whose package() copies files): it configures
        # the standalone build of the upstream GoogleTest suite that build()
        # compiles and runs, i.e. layer 1 of docs/TEST_QUALITY_SPEC.md.
        src = self.source_folder.replace("\\", "/")
        boost = self.dependencies["boost"]
        boost_incs = [os.path.join(boost.package_folder, d).replace("\\", "/")
                      for d in boost.cpp_info.includedirs]
        inject = os.path.join(self.generators_folder,
                              "svgpp-upstream-test-inject.cmake")
        inject = inject.replace("\\", "/")
        # svgpp's src/test/CMakeLists.txt is designed to be added through
        # src/CMakeLists.txt, which supplies Boost includes from the parent
        # scope (the test file itself never calls find_package(Boost)) and
        # would also compile the agg-based demo.  Configure src/test
        # standalone and inject the missing include directories through
        # CMAKE_PROJECT_INCLUDE; upstream files stay byte-identical.
        lines = ["include_directories(",
                 '    "%s/include"' % src,
                 '    "%s/third_party"' % src]
        lines += ['    "%s"' % inc for inc in boost_incs]
        lines.append(")")
        save(self, inject, "\n".join(lines) + "\n")

        tc = CMakeToolchain(self,
                            generator="Ninja" if shutil.which("ninja") else None)
        # Upstream CMakeLists declare cmake_minimum_required(VERSION 2.8),
        # rejected outright by the CMake 4.x on this machine (notes.md 关键适配
        # 点 9); the documented shim is the policy-version floor.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["CMAKE_PROJECT_INCLUDE"] = inject
        if str(self.settings.os) == "OHOS":
            # Same CMake platform model as the merged burst/3.1.1 recipe: this
            # makes UNIX true so the vendored gtest and upstream
            # target_link_libraries(... pthread) branch behave exactly like on
            # upstream's CI, while the OHOS clang from the profile is retained.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # Layer 1 (docs/TEST_QUALITY_SPEC.md): compile and run the real
        # upstream GoogleTest suite (ParserGTest: 22 registered test TUs +
        # vendored gtest/gmock sources) inside this recipe, then execute it on
        # this machine.  A failing case fails conan create, as the spec
        # requires.  CheckHeadersAutonomy (compile-only header autonomy check)
        # and FullParseTest (benchmark tool needing an SVG file argument) are
        # deliberately not built here: see notes.md「测试五维账本」for the
        # accounting of both.
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join("src", "test"))
        build_tool_args = ["-j4"]
        if not shutil.which("ninja"):
            # GNU Make >= 4.4 defaults to a FIFO jobserver which HMDFS rejects
            # (notes.md「环境与踩坑留痕」); pipe style works there.
            build_tool_args.append("--jobserver-style=pipe")
        cmake.build(target="ParserGTest", build_tool_args=build_tool_args)
        exe = os.path.join(self.build_folder, "ParserGTest").replace("\\", "/")
        xml = os.path.join(self.build_folder, "parser_gtest.xml").replace("\\", "/")
        # gtest console output (per-case lines plus [  PASSED  ]/[  FAILED  ]
        # summaries) is captured into the conan create log by the CI harness;
        # the XML report gives the machine-readable per-case record.
        self.run('"%s" --gtest_color=no --gtest_output=xml:"%s"' % (exe, xml),
                 env="conanrun")

    def package(self):
        include_dir = os.path.join(self.source_folder, "include")
        # svgpp headers (include/svgpp/**) plus the vendored exboost/parameter
        # headers (include/exboost/**) that the public headers include.
        copy(self, "*.hpp", src=include_dir,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "*.inc", src=include_dir,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE_1_0.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_id(self):
        # Headers only: the package is identical for every os/compiler/arch.
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
        self.cpp_info.requires = ["boost::boost"]
        self.cpp_info.set_property("cmake_file_name", "svgpp")
        self.cpp_info.set_property("cmake_target_name", "svgpp::svgpp")
