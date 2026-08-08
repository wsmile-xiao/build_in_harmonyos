#!/usr/bin/env python3
"""Conan recipe — parallel-hashmap 2.0.0 (CMake header-only / INTERFACE library).

Reference: archives/r/range-v3/0.12.0/ (header-only CMake pattern).

Downstream expects:
  find_package(phmap REQUIRED)
  target_link_libraries(... PRIVATE phmap::phmap)
"""
import os
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class ParallelHashmapConan(ConanFile):
    name = "parallel-hashmap"
    version = "2.0.0"
    description = "A family of header-only, very fast and memory-friendly hashmap and btree containers"
    license = "Apache-2.0"
    homepage = "https://github.com/greg7mdp/parallel-hashmap"
    url = "https://github.com/greg7mdp/parallel-hashmap"

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS: CMake may not recognize OHOS as a known system name
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            arch_map = {"armv8": "aarch64", "x86_64": "x86_64"}
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = arch_map.get(str(self.settings.arch), str(self.settings.arch))
        tc.cache_variables["PHMAP_BUILD_TESTS"] = "OFF"
        tc.cache_variables["PHMAP_BUILD_EXAMPLES"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # Fix 0: Make DownloadGTest.cmake support offline googletest.
        # Without this, cmake tries to git-clone from GitHub at configure time.
        download_gtest = os.path.join(self.source_folder, "cmake", "DownloadGTest.cmake")
        if os.path.exists(download_gtest):
            with open(download_gtest, "r") as f:
                content = f.read()
            offline_block = (
                '# If googletest source already exists (e.g. pre-extracted for\n'
                '# offline builds), skip the download and go to add_subdirectory.\n'
                'if(EXISTS "${CMAKE_BINARY_DIR}/googletest-src/CMakeLists.txt")\n'
                '    message(STATUS "googletest source already present, skipping download")\n'
                '    set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)\n'
                '    add_subdirectory(${CMAKE_BINARY_DIR}/googletest-src\n'
                '                     ${CMAKE_BINARY_DIR}/googletest-build\n'
                '                     EXCLUDE_FROM_ALL)\n'
                '    return()\n'
                'endif()\n\n'
            )
            if offline_block not in content:
                marker = (
                    "# Downloads and unpacks googletest at configure time."
                )
                replacement = offline_block + marker
                new_content = content.replace(marker, replacement, 1)
                if new_content == content:
                    raise ConanException(
                        "Failed to patch cmake/DownloadGTest.cmake: "
                        "marker string not found."
                    )
                with open(download_gtest, "w") as f:
                    f.write(new_content)

        # Fix 1/2/3: parallel-hashmap declares throw_bad_optional_access(),
        # bad_optional_access::~bad_optional_access(), and what() but
        # never defines them (original absl defines them in a .cc file).
        # Provide inline definitions for this header-only library.
        phmap_base = os.path.join(self.source_folder, "parallel_hashmap", "phmap_base.h")
        if os.path.exists(phmap_base):
            with open(phmap_base, "r") as f:
                content = f.read()
            # Fix 1: throw_bad_optional_access()
            new_content = content.replace(
                "[[noreturn]] void throw_bad_optional_access();",
                "[[noreturn]] inline void throw_bad_optional_access() {\n"
                "#ifdef PHMAP_HAVE_EXCEPTIONS\n"
                "    throw bad_optional_access();\n"
                "#else\n"
                "    std::abort();\n"
                "#endif\n"
                "}"
            )
            if new_content == content:
                raise ConanException(
                    "Failed to patch throw_bad_optional_access() in phmap_base.h: "
                    "declaration string not found. The upstream library may have "
                    "changed the declaration format."
                )
            content = new_content
            # Fix 2: ~bad_optional_access() and what() — both needed for vtable
            new_content = content.replace(
                "    ~bad_optional_access() override;\n"
                "    const char* what() const noexcept override;",
                "    ~bad_optional_access() override {}\n"
                "    const char* what() const noexcept override { return \"bad_optional_access\"; }"
            )
            if new_content == content:
                raise ConanException(
                    "Failed to patch ~bad_optional_access()/what() in phmap_base.h: "
                    "declaration string not found. The upstream library may have "
                    "changed the declaration format."
                )
            content = new_content
            with open(phmap_base, "w") as f:
                f.write(content)

        # Main build: header-only, just configure for install
        cmake = CMake(self)
        cmake.configure()

        # Build upstream tests in an isolated temporary directory.
        # Upstream tests require googletest which is normally git-cloned
        # at cmake configure time. On offline CI workers, pre-extract
        # googletest via GTEST_TARBALL_PATH env var. If neither works,
        # skip upstream tests — the consumer test_package still validates
        # the library.
        test_build_dir = tempfile.mkdtemp(prefix="phmap-tests-")
        try:
            gtest_tarball = os.environ.get("GTEST_TARBALL_PATH", "")
            gtest_src = os.path.join(test_build_dir, "googletest-src")
            gtest_available = False
            if gtest_tarball and os.path.exists(gtest_tarball):
                os.makedirs(gtest_src, exist_ok=True)
                subprocess.check_call(
                    ["tar", "xzf", gtest_tarball, "-C", gtest_src, "--strip-components=1"],
                    cwd=test_build_dir,
                )
                os.makedirs(os.path.join(test_build_dir, "googletest-build"), exist_ok=True)
                gtest_available = True

            if not gtest_available:
                self.output.warning(
                    "GTEST_TARBALL_PATH not set or tarball not found; "
                    "skipping upstream test build (googletest download "
                    "requires network access)."
                )
            else:
                toolchain = os.path.join(
                    self.generators_folder, "conan_toolchain.cmake"
                ).replace("\\", "/")
                qemu = shutil.which("qemu-aarch64")
                cmake_cmd = [
                    "cmake", self.source_folder,
                    "-G", "Unix Makefiles",
                    "-DCMAKE_TOOLCHAIN_FILE=" + toolchain,
                    "-DPHMAP_BUILD_TESTS=ON",
                    "-DPHMAP_BUILD_EXAMPLES=OFF",
                ]
                if self.settings.os == "OHOS":
                    arch_map = {"armv8": "aarch64", "x86_64": "x86_64"}
                    cmake_arch = arch_map.get(str(self.settings.arch), str(self.settings.arch))
                    cmake_cmd += [
                        "-DCMAKE_SYSTEM_NAME=Linux",
                        f"-DCMAKE_SYSTEM_PROCESSOR={cmake_arch}",
                        "-DCMAKE_CXX_FLAGS=-fexceptions",
                    ]
                if cross_building(self) and qemu:
                    cmake_cmd += [f"-DCMAKE_CROSSCOMPILING_EMULATOR={qemu}"]
                subprocess.check_call(cmake_cmd, cwd=test_build_dir)
                subprocess.check_call(
                    ["make", "-j20", "-k"],
                    cwd=test_build_dir,
                )
                if cross_building(self) and not qemu:
                    self.output.warning(
                        "qemu-aarch64 not found; skipping upstream test execution"
                    )
                else:
                    test_env = os.environ.copy()
                    if self.settings.os == "OHOS":
                        test_env["TMPDIR"] = test_build_dir
                        test_env["TMP"] = test_build_dir
                        test_env["TEMP"] = test_build_dir
                        test_env["GTEST_FILTER"] = "-*DeathTest*:*Death*"
                    subprocess.check_call(
                        ["ctest", "--output-on-failure", "-j20"],
                        cwd=test_build_dir,
                        env=test_env,
                    )
        finally:
            shutil.rmtree(test_build_dir, ignore_errors=True)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Header-only: no link libraries
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]

        self.cpp_info.set_property("cmake_file_name", "phmap")
        self.cpp_info.set_property("cmake_target_name", "phmap::phmap")
        self.cpp_info.set_property("pkg_config_name", "parallel-hashmap")
