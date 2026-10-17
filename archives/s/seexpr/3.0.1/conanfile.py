#!/usr/bin/env python3
"""Conan recipe for seexpr 3.0.1 (Disney SeExpr expression language) on HarmonyOS PC.

Scope: core libSeExpr2 shared library + upstream ctest suite. Qt5 UI/demos
(need Qt5+OpenGL), python bindings (need boost_python, unpublished), docs and
the optional legacy-LLVM JIT backend are disabled (see notes.md).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class SeexprConan(ConanFile):
    name = "seexpr"
    version = "3.0.1"
    description = "SeExpr: Disney's embeddable expression language for procedural graphics"
    license = "Apache-2.0"
    homepage = "https://github.com/wdas/SeExpr"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    # Upstream builds SHARED on all non-Windows platforms; the option exists
    # for conan package_type conformance and is fixed to shared.
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Only the upstream test suite (src/tests) consumes these; the
        # packaged library itself has no third-party runtime dependency.
        # zlib is declared directly (not just transitively via libpng)
        # because conan skips downloading transitive shared-dependency
        # binaries, leaving FindZLIB (and thus FindPNG) without a
        # package folder at configure time.
        self.test_requires("zlib/1.3.2")
        self.test_requires("libpng/1.6.58.3")
        self.test_requires("gtest/1.17.0.2")

    def build_requirements(self):
        # src/SeExpr2/generated/ ships empty in the v3.0.1 tarball, so the
        # ExprParser lexer/grammar must be regenerated with flex/bison/sed at
        # build time. The OHOS CI worker has no system copies (tool_requires);
        # a macOS dev box simulating the worker with an OHOS-settings profile
        # uses its host tools instead (user.build:flex_bison_native conf,
        # same pattern as libidl2/0.8.14).
        if self.settings_build.os == "OHOS" and not self.conf.get(
                "user.build:flex_bison_native", default=False):
            self.tool_requires("bison/3.8.2")
            self.tool_requires("flex/2.6.4.2")
            self.tool_requires("m4/1.4.19")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["ENABLE_QT5"] = "OFF"
        tc.variables["USE_PYTHON"] = "OFF"
        tc.variables["BUILD_DEMOS"] = "OFF"
        tc.variables["BUILD_UTILS"] = "OFF"
        tc.variables["BUILD_DOC"] = "OFF"
        tc.variables["BUILD_TESTS"] = "ON"
        # -msse4.1 is x86-only; the aarch64 build must take the portable
        # (#ifndef __SSE4_1__) path in Noise.cpp.
        tc.variables["ENABLE_SSE4"] = "OFF"
        # The optional LLVM JIT backend targets a legacy LLVM API.
        tc.variables["ENABLE_LLVM_BACKEND"] = "OFF"
        # test_requires land in self.dependencies but NOT in .host.values()
        # (conan 2.29); fetch them by name (they are always declared above).
        # Upstream src/tests/CMakeLists.txt finds gtest only via GTEST_DIR and
        # PNG via module-mode find_package, so the dependency package folders
        # must also be on CMAKE_PREFIX_PATH.
        gtest = self.dependencies.get("gtest")
        if gtest and gtest.package_folder:
            tc.variables["GTEST_DIR"] = gtest.package_folder
        prefix_paths = []
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                prefix_paths.append(dep.package_folder)
        tc.cache_variables["CMAKE_PREFIX_PATH"] = ";".join(prefix_paths)
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            # CMake has no Platform/HarmonyOS module, so the soname flag
            # variables from Platform/Linux.cmake stay empty and the linker
            # never receives -Wl,-soname (libSeExpr2.so would have no
            # DT_SONAME and fail the CI L5a gate). Supply unversioned,
            # relocatable soname flags at toolchain level
            # (DRAFT-libharu-2.3.0-missing-dt-soname pattern).
            tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
            tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with self._tool_environment().vars(self).apply():
            cmake.configure()
            cmake.build()
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            self._sign_test_executables()
        if self._can_execute_target():
            self._run_upstream_tests()

    def _can_execute_target(self):
        if not can_run(self):
            return False
        # A macOS dev box simulating the OHOS worker (ohos-local profile with
        # user.build:flex_bison_native=True) cannot exec OHOS binaries; the
        # real run happens on the OHOS CI worker.
        if self.conf.get("user.build:flex_bison_native", default=False):
            return False
        return True

    def _run_upstream_tests(self):
        # Upstream ctest suite: basic (gtest BasicTests.*, 12 cases),
        # dirtSimple, plus two soft-skip python scripts (imageTestsReport /
        # basicPython, exit 0 by upstream design). BlockTests is excluded:
        # it consists solely of Expression::UseLLVM evaluations and throws
        # "LLVM is not enabled in build" by upstream design when the LLVM
        # JIT backend is disabled (ENABLE_LLVM_BACKEND=OFF).
        test_env = Environment()
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        # test_requires (libpng/gtest) are not in .host.values() (conan 2.29);
        # iterate the full dependency set so LD_LIBRARY_PATH covers them —
        # otherwise the loader cannot find libpng16.so.16 at test runtime
        # (CI round 1 failure).
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                test_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
        test_env.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.build_folder, "src", "SeExpr2"))
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error '
                '--timeout 300 -E "^BlockTests$"'.format(self.build_folder))
            # ctest only reports pass/fail per entry; run the gtest binary
            # directly so the build log carries the authoritative case count
            # ("[==========] N tests from 1 test suite ran") for the PR table.
            testmain = os.path.join(
                self.build_folder, "src", "tests", "testmain2")
            if os.path.isfile(testmain):
                self.run('"{}" --gtest_filter=BasicTests.*'.format(testmain))

    def _tool_environment(self):
        # bison binary locates its m4 data relative to the install prefix;
        # inject the tool_requires prefixes explicitly (solid/6.26.0 pattern).
        env = Environment()
        for dep_name in ("bison", "flex", "m4"):
            dep = self._build_dep(dep_name)
            if dep and dep.package_folder:
                env.prepend_path("PATH", os.path.join(dep.package_folder, "bin"))
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
        bison = self._build_dep("bison")
        if bison and bison.package_folder:
            env.define(
                "BISON_PKGDATADIR",
                os.path.join(bison.package_folder, "share", "bison"))
        m4 = self._build_dep("m4")
        if m4 and m4.package_folder:
            env.define("M4", os.path.join(m4.package_folder, "bin", "m4"))
        return env

    def _build_dep(self, name):
        # tool_requires are skipped under user.build:flex_bison_native
        # (local macOS simulation), so look them up defensively.
        return next(
            (d for d in self.dependencies.build.values() if d.ref.name == name),
            None)

    def _sign_test_executables(self):
        # OHOS refuses to exec unsigned ELF binaries (E077); sign the upstream
        # test executables so ctest can run them on the worker. Shared
        # libraries load via DT_NEEDED without signing (libopencsd/1.5.5).
        signer = shutil.which("binary-sign-tool")
        if not signer:
            candidate = "/data/service/hnp/bin/binary-sign-tool"
            signer = candidate if os.path.isfile(candidate) else None
        if not signer:
            self.output.warning(
                "binary-sign-tool unavailable; skipping test executable "
                "signing (local simulation only, CI worker signs)")
            return
        for name in ("testmain2", "dirtSimple", "BlockTests",
                     "VarBlockExample", "typeTests", "multiTests"):
            path = os.path.join(self.build_folder, "src", "tests", name)
            if os.path.isfile(path):
                self.run(
                    '"{}" sign -inFile "{}" -outFile "{}" -selfSign 1'.format(
                        signer, path, path))

    def package(self):
        CMake(self).install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["SeExpr2"]
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
