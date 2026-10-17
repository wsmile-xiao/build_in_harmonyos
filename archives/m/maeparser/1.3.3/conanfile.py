#!/usr/bin/env python3
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, save
from conan.tools.build import build_jobs
from conan.errors import ConanInvalidConfiguration


class MaeparserConan(ConanFile):
    name = "maeparser"
    version = "1.3.3"
    description = "Parser for Schrodinger Maestro formatted files"
    license = "MIT"
    url = "https://github.com/schrodinger/maeparser"
    homepage = "https://github.com/schrodinger/maeparser"
    topics = ("maestro", "schrodinger", "chemistry", "parser")
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

    @property
    def _min_cppstd(self):
        return 11

    def export_sources(self):
        # Boost.Test implementation stub used to compile the upstream test
        # suite in build() — see notes.md.
        copy(self, "ut_stub.cpp",
             os.path.join(self.recipe_folder, "test_package"),
             os.path.join(self.export_sources_folder, "test_sources"))

    def requirements(self):
        # maeparser streams gzip-compressed .maegz files through
        # boost::iostreams, which needs zlib as its compression backend.
        # The upstream tests additionally use boost::filesystem.
        self.requires("boost/1.84.0")
        self.requires("zlib/1.3.1")

    def validate_build(self):
        # cppstd values like "gnu98" carry a prefix; strip non-digits.
        cppstd = str(self.settings.compiler.get_safe("cppstd") or "")
        digits = "".join(ch for ch in cppstd if ch.isdigit())
        if digits and int(digits) < self._min_cppstd:
            raise ConanInvalidConfiguration(
                f"{self.ref} requires C++{self._min_cppstd} or higher")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # Upstream CMakeLists expects the CMake module target ZLIB::ZLIB
        # while the conan zlib package exposes zlib::zlib; it also consumes
        # the Boost_LIBRARIES variable form. Consumer-side target-name
        # overrides (precedent: MilkyTracker recipe) make both resolvable
        # without patching upstream.
        self.dependencies["zlib"].cpp_info.set_property(
            "cmake_target_name", "ZLIB::ZLIB")
        self.dependencies["boost"].cpp_info.set_property(
            "cmake_target_name", "Boost::boost")
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        cmake = CMake(self)
        cmake.configure(variables={
            "MAEPARSER_BUILD_SHARED_LIBS": self.options.shared,
            "MAEPARSER_USE_BOOST_IOSTREAMS": True,
            "MAEPARSER_BUILD_TESTS": False,
            "CMAKE_CXX_STANDARD": self._min_cppstd,
        })
        cmake.build()
        self._build_and_run_upstream_tests()

    def _build_and_run_upstream_tests(self):
        """Compile the 7 upstream test translation units (test/*.cpp) with a
        statically compiled Boost.Test implementation and execute them.

        The boost/1.84.0 package ships the boost/test/impl/*.ipp sources but
        no prebuilt unit-test-framework library; compiling those .ipp files
        with BOOST_TEST_SOURCE in a dedicated TU (test_sources/ut_stub.cpp,
        exported with this recipe) is Boost.Test's documented manual static
        compile mode. No upstream source is modified."""
        test_src = os.path.join(self.source_folder, "test")
        # During conan create, exported sources are copied into the source
        # tree root (next to CMakeLists.txt).
        stub = os.path.join(self.source_folder, "test_sources", "ut_stub.cpp")
        if not os.path.isfile(stub):
            stub = os.path.join(self.export_sources_folder, "test_sources",
                                "ut_stub.cpp")
        if not os.path.isfile(stub):
            raise ConanInvalidConfiguration(
                f"Boost.Test stub not found: {stub}")

        boost_info = self.dependencies["boost"].cpp_info.aggregated_components()
        boost_inc = boost_info.includedirs[0]
        boost_libdir = boost_info.libdirs[0]
        zlib_info = self.dependencies["zlib"].cpp_info.aggregated_components()
        zlib_inc = zlib_info.includedirs[0]
        zlib_libdir = zlib_info.libdirs[0]

        out = os.path.join(self.build_folder, "ut_tests")
        os.makedirs(out, exist_ok=True)
        test_tus = [
            "MainTestSuite.cpp", "BufferTest.cpp", "MaeBlockTest.cpp",
            "MaeParserTest.cpp", "ReaderTest.cpp", "WriterTest.cpp",
            "UsageDemo.cpp",
        ]
        objs = []
        defines = [
            f'TEST_SAMPLES_PATH="{test_src}"',
            # OHOS musl does not provide pthread_setcancelstate.
            "BOOST_SP_NO_PTHREAD_SETCANCELSTATE",
        ]
        # self.run() goes through a shell: escape the quotes of the path
        # macro so the compiler receives -DTEST_SAMPLES_PATH="/abs/path".
        shell_defines = " ".join("-D" + d.replace('"', '\\"') for d in defines)
        cxx_flags = f"-std=c++11 -I{self.source_folder} " \
                    f"-I{boost_inc} -I{zlib_inc} -fPIC"
        for tu in test_tus:
            obj = os.path.join(out, f"ut_{tu}.o")
            self.run(
                f"clang++ --target=aarch64-unknown-linux-ohos "
                f"{cxx_flags} {shell_defines} "
                f"-c {os.path.join(test_src, tu)} -o {obj}")
            objs.append(obj)
        obj = os.path.join(out, "ut_stub.o")
        self.run(
            f"clang++ --target=aarch64-unknown-linux-ohos "
            f"{cxx_flags} {shell_defines} "
            f"-c {stub} -o {obj}")
        objs.append(obj)

        test_bin = os.path.join(out, "maeparser_upstream_tests")
        self.run(
            f"clang++ --target=aarch64-unknown-linux-ohos {' '.join(objs)} "
            f"{os.path.join(self.build_folder, 'libmaeparser.a')} "
            f"-L{boost_libdir} -lboost_iostreams -lboost_filesystem "
            f"-L{zlib_libdir} -lz -o {test_bin}")
        # The tests run natively on the OHOS aarch64 host.
        self.run(f"{test_bin} --report_format=HRF --report_level=detailed",
                 env="conanbuild")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.txt", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "maeparser")
        self.cpp_info.set_property("cmake_target_name", "maeparser::maeparser")
        self.cpp_info.libs = ["maeparser"]
        # Component names as defined by the repo boost/1.84.0 recipe.
        self.cpp_info.requires = ["boost::boost_iostreams", "zlib::zlib"]
