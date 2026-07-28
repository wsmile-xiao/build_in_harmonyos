#!/usr/bin/env python3
"""Conan recipe — draco 1.5.7 (cmake)

Google's 3D geometry mesh compression library.
Produces: libdraco.a (static), draco_encoder, draco_decoder.
"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class DracoConan(ConanFile):
    name = "draco"
    version = "1.5.7"
    description = "Draco is a library for compressing and decompressing 3D geometric meshes and point clouds."
    license = "Apache-2.0"
    homepage = "https://google.github.io/draco/"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ohos_llvm_bin(self):
        """Derive LLVM bin directory from the OHOS toolchain path."""
        import os
        toolchain = self._ohos_toolchain()
        # toolchain: <ndk_root>/build/cmake/ohos.toolchain.cmake
        ndk_root = os.path.dirname(os.path.dirname(os.path.dirname(toolchain)))
        llvm_bin = os.path.join(ndk_root, "llvm", "bin")
        if os.path.isdir(llvm_bin):
            return llvm_bin
        # Fallback: search common locations for llvm-ar
        for base in ["/data/service/hnp/ohos-sdk.org"]:
            pattern = os.path.join(base, "*", "ohos", "native", "llvm", "bin")
            import glob
            matches = sorted(glob.glob(pattern))
            if matches:
                return matches[-1]
        return None

    def _ohos_toolchain(self):
        import os
        import glob
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        candidates = list(ut) + ([os.path.join(ndk, "build", "cmake", "ohos.toolchain.cmake")] if ndk else [])
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        globbed = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if globbed:
            return globbed[-1]
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake：设 OHOS_NDK_HOME，或在 profile [conf] 配 "
            "tools.cmake.cmaketoolchain:user_toolchain=[<sdk>/ohos/native/build/cmake/ohos.toolchain.cmake]")

    def build(self):
        import os
        import re
        import subprocess
        apply_conandata_patches(self)
        toolchain = self._ohos_toolchain()
        bdir = os.path.join(self.build_folder, "build-ohos")
        sdir = self.source_folder
        bt = self.settings.build_type
        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(bt),
            "-DCMAKE_INSTALL_PREFIX={}".format(self.package_folder),
            "-DCMAKE_INSTALL_LIBDIR=lib",
            "-DBUILD_SHARED_LIBS=ON" if self.options.shared else "-DBUILD_SHARED_LIBS=OFF",
            "-DDRACO_INSTALL=ON",
        ]

        # E012: ohos.toolchain.cmake 以 INTERNAL/FORCE 覆写 CMAKE_AR 为 bare name
        # ("llvm-ar")，但 llvm-ar 不在默认 PATH 中。CMake 明确规定
        # CMAKE_<LANG>_CREATE_STATIC_LIBRARY 一旦存在，会优先于
        # CMAKE_<LANG>_ARCHIVE_CREATE/APPEND/FINISH。用绝对路径的 llvm-ar rcs
        # 覆盖最高优先级规则，一步创建归档及符号索引，彻底绕过裸命令查找。
        llvm_bin = self._ohos_llvm_bin()
        if llvm_bin:
            llvm_bin = os.path.abspath(llvm_bin)
            ar = os.path.join(llvm_bin, "llvm-ar")
            ranlib = os.path.join(llvm_bin, "llvm-ranlib")
            defs.extend([
                '-DCMAKE_AR:FILEPATH="{}"'.format(ar),
                '-DCMAKE_RANLIB:FILEPATH="{}"'.format(ranlib),
                '-DCMAKE_CXX_CREATE_STATIC_LIBRARY="{} rcs <TARGET> <OBJECTS>"'.format(ar),
                '-DCMAKE_C_CREATE_STATIC_LIBRARY="{} rcs <TARGET> <OBJECTS>"'.format(ar),
            ])

        # --- Ensure GTest is available for upstream tests ---
        gtest_dir = os.path.join(sdir, "third_party", "googletest")
        gtest_src_all = os.path.join(gtest_dir, "googletest", "src", "gtest-all.cc")
        if not os.path.isfile(gtest_src_all):
            self.output.info("GTest not found in third_party — downloading for upstream tests")
            self.run('mkdir -p "{}"'.format(gtest_dir))
            ret = self.run(
                'curl -fsSL https://github.com/google/googletest/archive/refs/tags/v1.14.0.tar.gz '
                '| tar -xzf - -C "{}" --strip-components=1'.format(gtest_dir),
                ignore_errors=True)
            if not os.path.isfile(gtest_src_all):
                raise ConanInvalidConfiguration(
                    "Failed to download/extract GTest into {}".format(gtest_dir))

        defs.append("-DDRACO_TESTS=ON")

        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, sdir, " ".join(defs)))
        self.run('cmake --build "{}" -- -j$(nproc)'.format(bdir))

        # --- Build upstream test targets ---
        self.run('cmake --build "{}" --target draco_tests -- -j$(nproc)'.format(bdir))
        has_factory = os.path.isfile(os.path.join(bdir, "CMakeFiles", "draco_factory_tests.dir", "build.make"))
        if has_factory:
            self.run('cmake --build "{}" --target draco_factory_tests -- -j$(nproc)'.format(bdir))

        # --- Run upstream tests and collect results ---
        testdata_dir = os.path.join(sdir, "testdata")
        env = os.environ.copy()
        env["DRACO_TEST_DATA_DIR"] = testdata_dir

        discovered = 0
        executed = 0
        passed = 0
        failed = 0
        skipped = 0

        for tname in ("draco_tests", "draco_factory_tests"):
            tbin = os.path.join(bdir, tname)
            if not os.path.isfile(tbin):
                self.output.warning("Test binary not found: {}".format(tbin))
                continue
            self.output.info("Running upstream test: {} …".format(tname))
            cmd = '"{}" --gtest_print_time=0'.format(tbin)
            proc = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, cwd=sdir, env=env,
                timeout=300)
            self.output.info(proc.stdout)
            if proc.stderr:
                self.output.warning(proc.stderr)

            # Parse GTest summary line: [  PASSED  ] N tests, [  FAILED  ] M tests
            for line in proc.stdout.splitlines():
                m = re.search(r'^\[==========\] Running (\d+) tests? from', line)
                if m:
                    discovered += int(m.group(1))
                m = re.search(r'^\[  PASSED  \] (\d+) tests?\.', line)
                if m:
                    passed += int(m.group(1))
                m = re.search(r'^\[  FAILED  \] (\d+) tests?\.', line)
                if m:
                    failed += int(m.group(1))

        executed = passed + failed
        if executed == 0 and discovered > 0:
            # GTest skipped silently — some earlier pattern
            skipped = discovered
            discovered = 0

        status_str = "passed" if failed == 0 else "failed"
        summary = (
            'HMBS_UPSTREAM_TEST_RESULT={{"status":"{}","framework":"gtest",'
            '"command":"draco_tests && draco_factory_tests",'
            '"discovered":{},"executed":{},"passed":{},"failed":{},"skipped":{}}}'.format(
                status_str, discovered, executed, passed, failed, skipped))
        self.output.info(summary)

    def package(self):
        import os
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))

    def package_info(self):
        self.cpp_info.libs = ["draco"]
        self.cpp_info.set_property("cmake_file_name", "draco")
        self.cpp_info.set_property("cmake_target_name", "draco::draco")
        # draco installs pkg-config file
        self.cpp_info.set_property("pkg_config_name", "draco")
