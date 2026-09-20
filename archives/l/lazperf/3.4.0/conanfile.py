#!/usr/bin/env python3
"""Conan recipe — lazperf 3.4.0 (CMake)

lazperf is the C++ LAS/LAZ reader-writer and compression codec used by PDAL.
It implements the LASzip chunked-LAZ codec plus the LAS 1.2/1.3/1.4 header
models and the stream-level file API (`reader::named_file` /
`writer::named_file` / chunk compressor-decompressor pairs).

OHOS notes
----------
* The upstream test harness (`cpp/test/io_tests.cpp::makeTempFileName()`)
  hardcodes `/var/tmp/fnXXXXXX` for the scratch LAS/LAZ files it round-trips.
  HarmonyOS' root filesystem is read-only and `/var/tmp` may not exist at all,
  so `mkstemp()` fails, its return value is ignored, and the following
  `ofstream` silently produces nothing - 7 of the 21 io_tests cases then fail
  for reasons unrelated to lazperf (measured with /var/tmp mounted read-only:
  21 ran / 14 PASSED / 7 FAILED, and 21/21 once patched).  `patches/0001-...`
  resolves the scratch path through `$TMPDIR` instead (E002 family).
* The recipe creates a writable `$TMPDIR` under the build folder and exports it
  for the `ctest` run, because the upstream `add_test()` uses
  `WORKING_DIRECTORY "${CMAKE_RUNTIME_OUTPUT_DIRECTORY}/../.."`, which resolves
  to `/` when `CMAKE_RUNTIME_OUTPUT_DIRECTORY` is unset.
* `patches/0002-...` puts the configure-time `file(DOWNLOAD)` of the autzen
  benchmark asset behind an opt-in option: nothing in this build consumes it
  (only the `laszip` benchmark reads it, and that target needs an external
  LASzip that is not present), while CI must not reach github.com directly.
* `cpp/test/gtest/gtest-10-06-21/googletest/CMakeLists.txt` still declares
  `cmake_minimum_required(VERSION 2.8.12)`, which CMake >= 4 rejects outright;
  `CMAKE_POLICY_VERSION_MINIMUM` is pinned so the vendored gtest configures on
  both old and new CMake.
* gtest 1.10.0 is vendored inside the tarball (no configure-time network fetch)
  and compiles with `-Wall -Wshadow -Werror -Wconversion`; the OHOS clang
  driver emits `-Wunused-command-line-argument` for the flags its wrapper
  injects, so that one diagnostic is disabled.  No test assertion is touched.
* Upstream's `install()` rules only ship the six stream-level headers plus
  `lazperf_user_base.hpp` renamed to `lazperf_base.hpp`; the packaged header
  set mirrors that exactly.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches, copy, export_conandata_patches, get,
)

required_conan_version = ">=2.0"


class LazperfConan(ConanFile):
    name = "lazperf"
    version = "3.4.0"

    description = (
        "C++ library for reading and writing LAS/LAZ LiDAR files; implements "
        "the LASzip chunked compression codec used by PDAL."
    )
    homepage = "https://github.com/hobuinc/laz-perf"
    license = "Apache-2.0"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("lazperf", "las", "laz", "laszip", "lidar", "point-cloud",
              "compression")

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

    exports_sources = "conandata.yml", "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Build the upstream test suite: it is the L1 "上游官方测试" evidence.
        tc.variables["WITH_TESTS"] = True
        # The vendored gtest declares cmake_minimum_required(VERSION 2.8.12);
        # CMake >= 4 refuses policies below 3.5 unless a floor is given.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # gtest builds with -Werror; the OHOS clang wrapper injects flags that
        # it then reports as unused.  Disable only that diagnostic (E293
        # pattern - no blanket -Wno-error).
        tc.extra_cxxflags.append("-Wno-unused-command-line-argument")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        self._run_upstream_tests(cmake)

    def _run_upstream_tests(self, cmake):
        """Run the upstream ctest suite (L1) with a writable scratch directory.

        E002 family: HarmonyOS' root filesystem is read-only and `/var/tmp` may
        be absent.  7 io_tests cases round-trip a LAS/LAZ file through
        `makeTempFileName()`, which patch 0001 makes resolve `$TMPDIR`.  The
        upstream `add_test()` runs with `WORKING_DIRECTORY` that resolves to
        `/`, so an explicit writable TMPDIR is required for those cases; the
        same directory is also what a POSIX ctest run would use.
        """
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)

        env = Environment()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)   # Windows GetTempPath fallback
        env.define("TEMP", tmpdir)
        env.vars(self, scope="build").save_script("lazperf_ctest_env")

        # `ctest` is launched by `CMake.ctest()` from `self.build_folder` (Conan
        # runs `build()` chdir'ed there), which is exactly where
        # `CTestTestfile.cmake` lands, so no `--test-dir` is needed.  Keep the
        # default conanbuild/conanrun scripts alongside ours so the runtime
        # library path survives in the shared build.
        cmake.ctest(cli_args=["--output-on-failure"],
                    env=["lazperf_ctest_env", "conanbuild", "conanrun"])

    def package(self):
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

        # Public headers: exactly the set upstream's install() ships.
        # Upstream installs lazperf_user_base.hpp *renamed* to
        # lazperf_base.hpp (the user-facing base header carrying the
        # LAZPERF_*_VERSION macros); mirror that, including the rename.
        #
        # One copy() per header rather than a "*.hpp" glob: conan.tools.files
        # .copy() 的签名是
        #   copy(conanfile, pattern, src, dst, keep_path, excludes,
        #        ignore_case, overwrite)
        # —— 没有 includes 参数（那是 CMake install() 的写法）。之前写成
        # copy(self, "*.hpp", src=..., dst=..., includes=[...]) 会在 package()
        # 阶段直接 TypeError: copy() got an unexpected keyword argument
        # 'includes'（构建与 3 个 ctest 用例都过了，倒在打包这一步）。
        # 也不能退回裸 "*.hpp"：它会连 cpp/lazperf/detail/*.hpp 一起拷进去，
        # 而上游 install() 只装这 7 个头。逐个点名最贴近上游语义。
        src_inc = os.path.join(self.source_folder, "cpp", "lazperf")
        dst_inc = os.path.join(self.package_folder, "include", "lazperf")
        for hdr in ("lazperf.hpp", "filestream.hpp", "header.hpp",
                    "readers.hpp", "vlr.hpp", "writers.hpp",
                    "lazperf_user_base.hpp"):
            copy(self, hdr, src=src_inc, dst=dst_inc, keep_path=False)
        os.rename(os.path.join(dst_inc, "lazperf_user_base.hpp"),
                  os.path.join(dst_inc, "lazperf_base.hpp"))

        # Library: taken from the build tree.  Upstream's install() ships only
        # the SHARED flavour of the target, so consuming it would leave the
        # default static build with no library at all; the on-disk names are
        # also the only stable contract between the two flavours.
        #
        # 每个 pattern 前面的 "*" 不是通配冗余，而是必须的：conan.tools.files
        # .copy() 用 fnmatch 拿 pattern 去匹配 **相对 src 的整条路径**，而不是
        # 文件名。产物在 build 树里位于子目录（cpp/liblazperf_s.a，因为
        # CMakeLists 对 cpp/ 用了 add_subdirectory），所以裸 "liblazperf_s.a"
        # 一个都匹配不上、package() 静默打包 0 个库文件，最后由 test_package
        # 的 CMakeDeps 报 "Library 'lazperf_s' not found in package"。
        # "*liblazperf_s.a" 让 "*" 吃掉 "cpp/" 这一段前缀。
        libdir = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            copy(self, "*liblazperf.so*", src=self.build_folder, dst=libdir,
                 keep_path=False)
            copy(self, "*liblazperf.*dylib", src=self.build_folder, dst=libdir,
                 keep_path=False)
            copy(self, "*lazperf.dll", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "bin"), keep_path=False)
            copy(self, "*lazperf.lib", src=self.build_folder, dst=libdir,
                 keep_path=False)
            copy(self, "*liblazperf.dll.a", src=self.build_folder, dst=libdir,
                 keep_path=False)
        else:
            copy(self, "*liblazperf_s.a", src=self.build_folder, dst=libdir,
                 keep_path=False)
            copy(self, "*lazperf_s.lib", src=self.build_folder, dst=libdir,
                 keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "lazperf")
        self.cpp_info.set_property("cmake_target_name", "lazperf::lazperf")
        self.cpp_info.libs = ["lazperf"] if self.options.shared else ["lazperf_s"]
        self.cpp_info.includedirs = ["include"]
