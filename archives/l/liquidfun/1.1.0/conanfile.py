#!/usr/bin/env python3
"""Conan recipe — liquidfun 1.1.0 (CMake, headless).

LiquidFun is Google's extension of the Box2D 2.3.0 rigid body physics
engine with a particle system (b2ParticleSystem). The Box2D 2.3.0 sources
are vendored in full under liquidfun/Box2D/Box2D (no external Box2D
dependency is used or needed — the in-repo box2d recipe tracks the 2.4.1
line which has a different API).

Upstream's own CMake tree is cmake-2.8 era with -Wall -Werror and a
case-broken "Unittests" reference, so patch 0001 replaces the top-level
build with a headless CMakeLists that builds the 54 library sources and
installs headers in the upstream include layout (include/Box2D/...).

Upstream unit tests (13 gtest binaries, 179 TEST cases under
liquidfun/Box2D/UnitTests) are built and run during the conan build()
phase against the vendored googletest sibling (googletest/ at the
archive root): the recipe generates a small CMake project that links
gtest from source with the library and runs each test binary through a
bash wrapper (mksh cannot exec OHOS ELF binaries directly).
"""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LiquidfunConan(ConanFile):
    name = "liquidfun"
    version = "1.1.0"
    description = "LiquidFun: Box2D 2.3.0-based 2D rigid-body + particle physics engine"
    license = "Zlib"
    homepage = "https://google.github.io/liquidfun/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    exports_sources = "patches/*"

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        # Upstream unit tests: 13 gtest binaries, 179 TEST cases. Build them
        # against the vendored googletest sibling, then run each through a
        # bash wrapper (OHOS mksh cannot exec the cross-built ELF directly).
        lf_root = os.path.join(self.source_folder, "liquidfun", "Box2D")
        gtest_root = os.path.join(self.source_folder, "googletest")
        if not os.path.isdir(gtest_root):
            self.output.warn("vendored googletest missing; skipping upstream tests")
            return
        tests_dir = os.path.join(self.build_folder, "upstream-tests")
        os.makedirs(tests_dir, exist_ok=True)
        lists = os.path.join(tests_dir, "CMakeLists.txt")
        with open(lists, "w") as f:
            f.write(
                "cmake_minimum_required(VERSION 3.15)\n"
                "project(lf_upstream_tests CXX)\n"
                "set(CMAKE_CXX_STANDARD 11)\n"
                "include_directories(\"%s\")\n"
                "add_subdirectory(\"%s\" googletest EXCLUDE_FROM_ALL)\n"
                "include_directories(\"${gtest_SOURCE_DIR}/include\")\n"
                "set(LF_LIB \"%s\")\n"
                "set(SUPPORT \"%s/UnitTests/BodyTracker.cpp\")\n"
                "set(UT \"%s/UnitTests\")\n"
                "add_definitions(-DLIQUIDFUN_UNIT_TESTS=1 -DLIQUIDFUN_EXTERNAL_LANGUAGE_API=1)\n"
                "find_package(Threads)\n"
                "foreach(T BlockAllocator BodyContacts Callback Color Common Confinement Conservation FreeList Function HelloWorld IntrusiveList SlabAllocator TrackedBlock)\n"
                "  add_executable(${T}Tests ${UT}/${T}/${T}Tests.cpp ${SUPPORT})\n"
                "  target_include_directories(${T}Tests PRIVATE ${UT})\n"
                "  target_link_libraries(${T}Tests gtest ${LF_LIB} Threads::Threads)\n"
                "endforeach()\n"
                % (lf_root, gtest_root,
                   os.path.join(self.build_folder, "libliquidfun.a"),
                   lf_root, lf_root)
            )
        cc = os.environ.get("CC", "clang")
        cxx = os.environ.get("CXX", "clang++")
        self.run(
            "cmake -S %s -B %s -DCMAKE_BUILD_TYPE=Release "
            "-DCMAKE_C_COMPILER=%s -DCMAKE_CXX_COMPILER=%s "
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5 "
            "-DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64"
            % (tests_dir, tests_dir, cc, cxx),
            env="conanbuild",
        )
        self.run("cmake --build %s -- -j2" % tests_dir, env="conanbuild")

        # The HelloWorld PositionAngleTest compares generated position/angle
        # data against baselines/HelloWorldPositionAngle.txt located next to
        # the test binary (BodyTracker::SetWorkingDirectory uses argv[0]).
        copy(self, "HelloWorldPositionAngle.txt",
             src=os.path.join(lf_root, "UnitTests", "baselines"),
             dst=os.path.join(tests_dir, "baselines"))

        # Run the 13 upstream test binaries (bash-wrapped for OHOS).
        bash = os.environ.get("CONFIG_SHELL") or next(
            (p for p in ("/data/service/hnp/bin/bash", "/bin/bash") if os.path.exists(p)),
            "bash",
        )
        total_pass, total_fail = 0, 0
        for t in ("BlockAllocator", "BodyContacts", "Callback", "Color", "Common",
                  "Confinement", "Conservation", "FreeList", "Function",
                  "HelloWorld", "IntrusiveList", "SlabAllocator", "TrackedBlock"):
            binpath = os.path.join(tests_dir, "%sTests" % t)
            if not os.path.exists(binpath):
                self.output.warn("missing test binary %s" % t)
                continue
            ret = self.run('%s -c "%s"' % (bash, binpath), env="conanbuild", ignore_errors=True)
            if ret == 0:
                total_pass += 1
            else:
                total_fail += 1
        self.output.info("upstream gtest binaries: %d passed / %d failed" % (total_pass, total_fail))
        if total_fail:
            raise Exception("liquidfun upstream tests failed: %d binaries" % total_fail)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "Readme.md", src=os.path.join(self.source_folder, "liquidfun"),
             dst="licenses", keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["liquidfun"]
        self.cpp_info.set_property("cmake_file_name", "liquidfun")
        self.cpp_info.set_property("cmake_target_name", "liquidfun::liquidfun")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
