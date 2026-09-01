# conanfile.py — mstch 1.0.2 (C++ Mustache template library)
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
import os


class MstchConan(ConanFile):
    name = "mstch"
    version = "1.0.2"
    description = "C++ implementation of the Mustache template system ({{mustache}})."
    license = "MIT"
    topics = ("mustache", "template", "text", "html")
    homepage = "https://github.com/no1msd/mstch"
    url = "https://github.com/no1msd/mstch"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports_sources = "patches/*"

    def configure(self):
        # Upstream CMakeLists.txt pins -std=c++11 in CMAKE_CXX_FLAGS, but the
        # profile's compiler.cppstd=17 makes the toolchain set
        # CMAKE_CXX_STANDARD=17 whose -std=c++17 is appended AFTER it and wins,
        # breaking the vendored Catch v1.12.2 test framework
        # (std::random_shuffle was removed in C++17). Drop cppstd so the
        # toolchain leaves the standard alone and everything builds with
        # upstream's own -std=c++11, exactly as upstream CI does. The package
        # id becomes cppstd-agnostic — correct for a C++11 library consumable
        # from any consumer standard.
        self.settings.rm_safe("compiler.cppstd")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # mstch uses boost::variant (header-only Boost.Variant) at build and
        # consumer time (it appears in the public header mstch.hpp), so the
        # dependency is transitive_headers. The boost recipe propagates the
        # BOOST_SP_NO_PTHREAD_SETCANCELSTATE define (musl compatibility).
        self.requires("boost/1.84.0", transitive_headers=True)

    def source(self):
        get(
            self,
            **self.conan_data["sources"][self.version],
            strip_root=True,
        )

    def generate(self):
        tc = CMakeToolchain(self)
        # Build the upstream unit-test suite (Catch v1). The tests are
        # compiled AND executed in build() — see build() for details.
        tc.variables["WITH_UNIT_TESTS"] = True
        tc.variables["WITH_BENCHMARK"] = False
        # Upstream src/CMakeLists.txt uses the FindBoost module variable
        # ${Boost_INCLUDE_DIR} (not the Boost::headers target), so we must
        # provide the value explicitly. CMakeDeps generates BoostConfig.cmake
        # which sets the Boost::* targets but not this legacy variable.
        tc.variables["Boost_INCLUDE_DIR"] = self.dependencies["boost"].cpp_info.includedirs[0]
        # Same legacy-variable problem for the test-time headerize tool:
        # its CMakeLists links ${Boost_PROGRAM_OPTIONS_LIBRARY} /
        # ${Boost_REGEX_LIBRARY} (FindBoost module outputs) but CMP0167 NEW
        # resolves find_package(Boost) via CMakeDeps config mode, which only
        # defines Boost:: targets. Point the legacy variables at the static
        # archives shipped in the boost package.
        boost_libdir = self.dependencies["boost"].cpp_info.libdirs[0]
        tc.variables["Boost_PROGRAM_OPTIONS_LIBRARY"] = os.path.join(
            boost_libdir, "libboost_program_options.a")
        tc.variables["Boost_REGEX_LIBRARY"] = os.path.join(
            boost_libdir, "libboost_regex.a")
        # boost's musl workaround define lives on the boost_headers component
        # and only propagates through the Boost::headers target; upstream
        # consumes bare ${Boost_INCLUDE_DIR}, so inject the define globally
        # (needed by vendor/headerize which includes boost/program_options).
        tc.extra_cxxflags = ["-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE"]
        # Modern CMake rejects the upstream cmake_minimum_required(VERSION 3.0.2)
        # — the patch bumps it to 3.5...3.31; also set the policy floor for the
        # vendor/headerize subtree which is fetched after patching.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def _fetch_test_submodules(self):
        """Materialize the upstream git submodules pinned by the 1.0.2 tag.

        The GitHub tag tarball ships vendor/{Catch,rapidjson,headerize,spec}
        as EMPTY directories (gitlinks are not materialized in archives).
        The upstream test suite cannot compile without them:
          - Catch     — test framework (vendor/Catch/single_include/catch.hpp)
          - rapidjson — spec JSON parsing in test_main.cpp
          - headerize — build-time tool that embeds test data as headers
          - spec      — the official mustache/spec conformance JSON files
        Each tarball is fetched at the exact SHA recorded in the tag's
        gitlink (verified against `git ls-tree 1.0.2 vendor/`):
          Catch=35f4266d, rapidjson=54eb069f, headerize=fba2f012, spec=83b07216.
        These are test-only deps fetched into the source folder (Conan cache,
        not the package); nothing from them is redistributed.
        """
        test_sources = self.conan_data.get("upstream_test_sources") or {}
        for name in ("Catch", "rapidjson", "headerize", "spec"):
            entry = test_sources.get(name)
            if not entry:
                raise ConanException(
                    f"upstream_test_sources.{name} missing from conandata.yml")
            vendor_dir = os.path.join(self.source_folder, "vendor", name)
            marker = os.path.join(vendor_dir, ".conan_fetched")
            if os.path.exists(marker):
                continue
            # Clean the empty gitlink directory the tarball left behind.
            if os.path.isdir(vendor_dir):
                for root, dirs, files in os.walk(vendor_dir, topdown=False):
                    for f in files:
                        os.remove(os.path.join(root, f))
                    for d in dirs:
                        os.rmdir(os.path.join(root, d))
            get(self, url=entry["url"], sha256=entry["sha256"],
                strip_root=True, destination=vendor_dir)
            save_marker = os.path.join(vendor_dir, ".conan_fetched")
            with open(save_marker, "w") as fh:
                fh.write(entry["sha256"])

    def build(self):
        apply_conandata_patches(self)
        # Materialize pinned test submodules before configuring so the
        # WITH_UNIT_TESTS=ON tree can compile.
        self._fetch_test_submodules()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # ── Run the upstream official test suite (Catch v1 via ctest) ──
        # Upstream registers 65 ctest targets: 58 MSTCH_TEST /
        # MSTCH_PARTIAL_TEST cases (from test/data/*.hpp) + 7 SPECS_TEST
        # conformance groups (from vendor/spec/specs/*.json). This is the
        # real upstream test system — it must actually run; a build-only
        # pass is not acceptable (no || true, no ignore_errors).
        ctest_args = ["--output-on-failure"]
        if self.settings.get_safe("build_type") == "Release":
            pass  # upstream sets CMAKE_BUILD_TYPE=Release itself
        self.run(f"ctest {' '.join(ctest_args)}", cwd=self.build_folder, env="conanbuild")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # The upstream config files hardcode ${mstch_INCLUDE_DIR} from the
        # build tree and are redundant with CMakeDeps-generated files.
        # Remove them so consumers use the Conan-generated config instead.
        for root, dirs, files in os.walk(os.path.join(self.package_folder, "lib", "cmake"),
                                         topdown=False):
            for f in files:
                os.remove(os.path.join(root, f))
            for d in dirs:
                os.rmdir(os.path.join(root, d))
        for root, dirs, files in os.walk(os.path.join(self.package_folder, "lib", "cmake"),
                                         topdown=False):
            try:
                os.rmdir(root)
            except OSError:
                pass

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "mstch")
        self.cpp_info.set_property("cmake_target_name", "mstch::mstch")
        self.cpp_info.libs = ["mstch"]
        self.cpp_info.includedirs = ["include"]
        # Cross-package component reference (<dep>::<component>) — mstch's
        # public header uses boost::variant, so consumers need boost headers.
        self.cpp_info.requires = ["boost::boost_headers"]
