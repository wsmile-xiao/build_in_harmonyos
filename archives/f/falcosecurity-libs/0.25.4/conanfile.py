#!/usr/bin/env python3
"""Conan recipe for the Falco userspace libraries on OpenHarmony."""

import glob
import json
import os
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, download, export_conandata_patches, get


SCAP_FILES = (
    {"filename": "kexec_arm64.scap", "url": "https://s3.eu-west-1.amazonaws.com/falco-distribution/fixtures/libs/scap_files/kexec_arm64.scap", "sha256": "fdb49126fcf318baa9b0f23243c89d4573dc339f8386171a66ba2a46adacbecd"},
    {"filename": "kexec_x86.scap", "url": "https://s3.eu-west-1.amazonaws.com/falco-distribution/fixtures/libs/scap_files/kexec_x86.scap", "sha256": "e3173873aedbbfab1b078f9ecaa08003a0367d5f46bf1ad88ea5ea35ccb818f6"},
    {"filename": "sample.scap", "url": "https://s3.eu-west-1.amazonaws.com/falco-distribution/fixtures/libs/scap_files/sample.scap", "sha256": "ac88f617b9076087ae204f0342b7d5927bd8361cce8729703ea0b3fc5633120f"},
    {"filename": "scap_2013.scap", "url": "https://s3.eu-west-1.amazonaws.com/falco-distribution/fixtures/libs/scap_files/scap_2013.scap", "sha256": "a022bddc26c4e971827fd54611817b34df8e8c045f56c92fccd96ccd0dd52d8a"},
    {"filename": "ptrace.scap", "url": "https://s3.eu-west-1.amazonaws.com/falco-distribution/fixtures/libs/scap_files/ptrace.scap", "sha256": "2cf3ee77ac35ffdd63b357aac2c0b721771a5ba362efa45dade2a0344aba0951"},
    {"filename": "mkdir.scap", "url": "https://s3.eu-west-1.amazonaws.com/falco-distribution/fixtures/libs/scap_files/mkdir.scap", "sha256": "09bc43ae6c40f6d0649867d211f640aed9af55b360039ef7213d8ee5ead8102b"},
    {"filename": "fchdir.scap", "url": "https://s3.eu-west-1.amazonaws.com/falco-distribution/fixtures/libs/scap_files/fchdir.scap", "sha256": "6b7c3e8a3d366272efcc7ea9ad7e91e60cdc9677be0c88c1987826641f80ad44"},
)


BUNDLED_SOURCES = (
    {
        "prefix": "uthash",
        "filename": "v1.9.8.tar.gz",
        "url": "https://codeload.github.com/troydhanson/uthash/tar.gz/refs/tags/v1.9.8",
        "sha256": "d9d123ce81c5d127442876fc3b12fab3ad632bee6aca685be7d461c08e24c046",
    },
    {
        "prefix": "tbb",
        "filename": "v2022.1.0.tar.gz",
        "url": "https://codeload.github.com/oneapi-src/oneTBB/tar.gz/refs/tags/v2022.1.0",
        "sha256": "ed067603ece0dc832d2881ba5c516625ac2522c665d95f767ef6304e34f961b5",
    },
    {
        "prefix": "jsoncpp",
        "filename": "1.9.5.tar.gz",
        "url": "https://codeload.github.com/open-source-parsers/jsoncpp/tar.gz/refs/tags/1.9.5",
        "sha256": "f409856e5920c18d0c2fb85276e24ee607d2a09b5e7d5f0a371368903c275da2",
    },
    {
        "prefix": "valijson",
        "filename": "v1.0.2.tar.gz",
        "url": "https://codeload.github.com/tristanpenman/valijson/tar.gz/refs/tags/v1.0.2",
        "sha256": "35d86e54fc727f1265226434dc996e33000a570f833537a25c8b702b0b824431",
    },
    {
        "prefix": "re2",
        "filename": "2022-06-01.tar.gz",
        "url": "https://codeload.github.com/google/re2/tar.gz/refs/tags/2022-06-01",
        "sha256": "f89c61410a072e5cbcf8c27e3a778da7d6fd2f2b5b1445cd4f4508bee946ab0f",
    },
    {
        "prefix": "zlib",
        "filename": "zlib-1.3.1.tar.gz",
        "url": "https://github.com/madler/zlib/releases/download/v1.3.1/zlib-1.3.1.tar.gz",
        "sha256": "9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23",
    },
)


class FalcoSecurityLibsConan(ConanFile):
    name = "falcosecurity-libs"
    version = "0.25.4"
    description = "Falco libscap and libsinsp userspace libraries"
    license = "Apache-2.0"
    homepage = "https://github.com/falcosecurity/libs"
    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"
    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def build_requirements(self):
        if self._is_ohos():
            self.test_requires("gtest/1.17.0")

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="falcosecurity-libs.tar.gz",
            strip_root=True,
        )
        source_groups = (
            ("scap_files", SCAP_FILES),
            ("bundled_sources", BUNDLED_SOURCES),
        )
        for directory_name, entries in source_groups:
            target_dir = Path(self.source_folder) / directory_name
            target_dir.mkdir(parents=True, exist_ok=True)
            for entry in entries:
                download(
                    self,
                    entry["url"],
                    str(target_dir / entry["filename"]),
                    sha256=entry["sha256"],
                )

    def _is_ohos(self):
        return str(self.settings.os) == "OHOS"

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["FALCOSECURITY_LIBS_VERSION"] = str(self.version)
        tc.cache_variables["BUILD_SHARED_LIBS"] = True
        tc.cache_variables["USE_BUNDLED_DEPS"] = True
        if self._is_ohos():
            gtest = self.dependencies["gtest"]
            tc.cache_variables["USE_BUNDLED_GTEST"] = False
            tc.cache_variables["GTest_DIR"] = str(
                Path(gtest.package_folder) / "lib" / "cmake" / "GTest"
            )
        tc.cache_variables["USE_BUNDLED_DRIVER"] = False
        tc.cache_variables["CREATE_TEST_TARGETS"] = True
        tc.cache_variables["ENABLE_LIBSCAP_TESTS"] = True
        tc.cache_variables["ENABLE_LIBSINSP_E2E_TESTS"] = False
        tc.cache_variables["ENABLE_DRIVERS_TESTS"] = False
        tc.cache_variables["ENABLE_E2E_TESTS"] = False
        tc.cache_variables["ENABLE_LIBSCAP_FUZZERS"] = False
        tc.cache_variables["ENABLE_LIBSCAP_FUZZ_TOOLS"] = False
        tc.cache_variables["BUILD_LIBSCAP_EXAMPLES"] = False
        tc.cache_variables["BUILD_LIBSINSP_EXAMPLES"] = False
        tc.cache_variables["ENABLE_BENCHMARKS"] = False

        if self._is_ohos():
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "HarmonyOS"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            tc.cache_variables["CMAKE_C_COMPILER_TARGET"] = "aarch64-linux-ohos"
            tc.cache_variables["CMAKE_CXX_COMPILER_TARGET"] = "aarch64-linux-ohos"
            tc.cache_variables["MUSL_OPTIMIZED_BUILD"] = True
            # The SDK defines __linux__, but the Linux platform implementation
            # is not part of this userspace-only build.
            tc.cache_variables["HAS_LINUX_PLATFORM"] = False
            # CMake does not provide SONAME flags for unknown HarmonyOS.
            tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
            tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        else:
            tc.cache_variables["MUSL_OPTIMIZED_BUILD"] = False
            tc.cache_variables["HAS_LINUX_PLATFORM"] = True
        tc.generate()

    def _stage_scap_files(self):
        fixtures = SCAP_FILES
        if not fixtures:
            return
        source_dir = Path(self.source_folder) / "scap_files"
        build_dir = Path(self.build_folder) / "scap_files"
        build_dir.mkdir(parents=True, exist_ok=True)
        for fixture in fixtures:
            source = source_dir / fixture["filename"]
            if not source.is_file():
                raise FileNotFoundError(
                    f"missing downloaded scap-file: {source}"
                )
            shutil.copy2(source, build_dir / fixture["filename"])
            self.output.info(
                f"Staged pre-fetched scap-file: {fixture['filename']}"
            )

    def _stage_bundled_sources(self):
        source_dir = Path(self.source_folder) / "bundled_sources"
        for entry in BUNDLED_SOURCES:
            source = source_dir / entry["filename"]
            if not source.is_file():
                raise FileNotFoundError(
                    f"missing downloaded bundled source: {source}"
                )
            destination = (
                Path(self.build_folder)
                / f"{entry['prefix']}-prefix"
                / "src"
                / entry["filename"]
            )
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            self.output.info(
                f"Staged bundled source archive: {entry['prefix']}/{entry['filename']}"
            )

    def _compiler_executable(self, language):
        executables = self.conf.get("tools.build:compiler_executables", {})
        if isinstance(executables, str):
            try:
                executables = json.loads(executables)
            except json.JSONDecodeError:
                executables = {}
        default = "/data/service/hnp/bin/clang++" if language == "cpp" else "/data/service/hnp/bin/clang"
        return str(executables.get(language, default))

    def _ohos_sdk_library_paths(self):
        compiler = Path(os.path.realpath(self._compiler_executable("cpp")))
        llvm_root = compiler.parent.parent
        sdk_lib = llvm_root / "lib"
        candidates = [
            sdk_lib / "aarch64-linux-ohos",
            sdk_lib / "aarch64-linux-ohos" / "c++",
            sdk_lib,
        ]
        return [str(path) for path in candidates if path.is_dir()]

    def _runtime_library_paths(self):
        build = Path(self.build_folder)
        paths = [
            build / "libsinsp",
            build / "libscap",
            build / "libscap" / "engine" / "nodriver",
            build / "libscap" / "engine" / "test_input",
            build / "libscap" / "engine" / "source_plugin",
            build / "lib",
            build / "tbb-prefix" / "src" / "tbb" / "lib_release",
            build / "jsoncpp-prefix" / "src" / "lib",
            build / "re2-prefix" / "src" / "re2" / "lib",
            build / "zlib-prefix" / "src" / "zlib",
        ]
        if self._is_ohos():
            paths.extend(Path(path) for path in self._ohos_sdk_library_paths())
            compiler = self._compiler_executable("cpp")
            try:
                runtime = subprocess.check_output(
                    [compiler, "-print-file-name=libc++_shared.so"],
                    text=True,
                ).strip()
                runtime_path = Path(runtime)
                if runtime_path.is_absolute():
                    paths.extend([runtime_path.parent, runtime_path.parent.parent])
            except (OSError, subprocess.CalledProcessError):
                pass
        return [str(path) for path in paths if path.is_dir()]

    def _test_runtime_layout(self):
        build = Path(self.build_folder)
        root = build / "_test_run"
        cwd = root / "a" / "b"
        cwd.mkdir(parents=True, exist_ok=True)
        links = {
            root / "lib": build / "lib",
            root / "libscap": build / "libscap",
            root / "tbb-prefix": build / "tbb-prefix",
            root / "jsoncpp-prefix": build / "jsoncpp-prefix",
            root / "re2-prefix": build / "re2-prefix",
            root / "zlib-prefix": build / "zlib-prefix",
            root / "a" / "libsinsp.so": build / "libsinsp" / "libsinsp.so",
            root / "a" / "libscap": build / "libscap",
            root / "a" / "jsoncpp-prefix": build / "jsoncpp-prefix",
            root / "a" / "re2-prefix": build / "re2-prefix",
            root / "a" / "tbb-prefix": build / "tbb-prefix",
            root / "a" / "zlib-prefix": build / "zlib-prefix",
            root / "a" / "b" / "engine": build / "libscap" / "engine",
            root / "a" / "b" / "libscap_event_schema.so": build / "libscap" / "libscap_event_schema.so",
            root / "libscap_event_schema.so": build / "libscap" / "libscap_event_schema.so",
        }
        for link, target in links.items():
            if not target.exists():
                if link == root / "lib":
                    # The top-level build/lib directory is created by install(),
                    # which runs after the upstream tests in build().
                    link.mkdir(parents=True, exist_ok=True)
                    continue
                raise RuntimeError(f"missing test runtime target: {target}")
            if not os.path.lexists(link):
                os.symlink(os.path.relpath(target, link.parent), link)
        return cwd

    def _run_upstream_tests(self):
        cwd = self._test_runtime_layout()
        old_ld = os.environ.get("LD_LIBRARY_PATH")
        paths = self._runtime_library_paths()
        if old_ld:
            paths.append(old_ld)
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(paths)
        try:
            tests = [
                Path(self.build_folder) / "libsinsp" / "test" / "unit-test-libsinsp",
                Path(self.build_folder) / "test" / "libscap" / "libscap_test",
            ]
            for test in tests:
                self.output.info(f"Running upstream test suite: {test.name}")
                self.run(f'"{test}" --gtest_color=no', cwd=str(cwd))
        finally:
            if old_ld is None:
                os.environ.pop("LD_LIBRARY_PATH", None)
            else:
                os.environ["LD_LIBRARY_PATH"] = old_ld

    def build(self):
        apply_conandata_patches(self)
        self._stage_scap_files()
        self._stage_bundled_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _remove_test_only_install(self):
        for relative in ("include/gtest", "include/gmock", "lib/cmake/GTest"):
            path = Path(self.package_folder) / relative
            if path.is_dir():
                shutil.rmtree(path)
        for pattern in (
            "lib/libgtest*.so*",
            "lib/libgmock*.so*",
            "lib/pkgconfig/gtest*.pc",
            "lib/pkgconfig/gmock*.pc",
        ):
            for path in glob.glob(str(Path(self.package_folder) / pattern)):
                if os.path.lexists(path):
                    os.unlink(path)

    def _materialize_bundled_symlinks(self):
        bundled_dir = Path(self.package_folder) / "lib" / "falcosecurity"
        source_dirs = [
            Path(self.build_folder) / "zlib-prefix" / "src" / "zlib",
            Path(self.build_folder) / "tbb-prefix" / "src" / "tbb" / "lib_release",
            Path(self.build_folder) / "jsoncpp-prefix" / "src" / "lib",
            Path(self.build_folder) / "re2-prefix" / "src" / "re2" / "lib",
        ]
        for link in bundled_dir.glob("*.so*"):
            if not link.is_symlink():
                continue
            target = Path(os.readlink(link))
            if not target.is_absolute():
                target = link.parent / target
            if target.is_file():
                continue
            for source_dir in source_dirs:
                source = source_dir / target.name
                if source.is_file():
                    shutil.copy2(source, target)
                    break
            if not target.is_file():
                raise RuntimeError(f"bundled shared-library symlink target missing: {target}")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._remove_test_only_install()
        self._materialize_bundled_symlinks()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "falcosecurity-libs")
        self.cpp_info.set_property("cmake_target_name", "falcosecurity-libs::falcosecurity-libs")
        self.cpp_info.includedirs = ["include/falcosecurity", "include/falcosecurity/include"]
        self.cpp_info.libdirs = ["lib", "lib/falcosecurity"]
        self.cpp_info.libs = ["sinsp", "scap", "scap_event_schema"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "pthread"]
        if self._is_ohos():
            self.runenv_info.append_path("LD_LIBRARY_PATH", str(Path(self.package_folder) / "lib"))
            self.runenv_info.append_path(
                "LD_LIBRARY_PATH", str(Path(self.package_folder) / "lib" / "falcosecurity")
            )
            try:
                runtime = subprocess.check_output(
                    [self._compiler_executable("cpp"), "-print-file-name=libc++_shared.so"],
                    text=True,
                ).strip()
                runtime_path = Path(runtime)
                if runtime_path.is_absolute():
                    self.runenv_info.append_path("LD_LIBRARY_PATH", str(runtime_path.parent))
                    self.runenv_info.append_path("LD_LIBRARY_PATH", str(runtime_path.parent.parent))
            except (OSError, subprocess.CalledProcessError):
                pass
            for path in self._ohos_sdk_library_paths():
                self.runenv_info.append_path("LD_LIBRARY_PATH", path)
