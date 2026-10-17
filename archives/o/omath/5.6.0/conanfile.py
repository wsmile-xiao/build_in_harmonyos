#!/usr/bin/env python3
"""Conan recipe for omath 5.6.0 — header-first C++ math/gameplay library.

OHOS PC 适配要点（完整证据见 notes.md）：

1. 编译器：上游核心模板 ``omath::Angle<Type, Min, Max, Flags>`` 的 ``Min``/``Max`` 是
   C++20 **浮点非类型模板参数**（连默认实参 ``Type min = Type(0)`` 都是），OHOS SDK 自带
   clang 15.0.4 直接拒绝：``sorry, non-type template argument of type 'float' is not yet
   supported``（-std=c++20 / c++2b / gnu++2b / -fexperimental-new-constant-interpreter 均复现）。
   因此本包用 ``tool_requires("clang/22.1.8")``（ohpcd 制品仓预编译工具链）作编译器；
   C++ 标准库仍是 SDK 自带 libcxx-ohos 15.0.4（clang22 配 libc++15 头实测可编译/链接/运行）。
2. libc++15 缺 <expected>/<print>/<source_location>/<memory_resource>，且 <format> 被
   ``_LIBCPP_HAS_NO_INCOMPLETE_FORMAT`` 关闭：前四个以**同名兼容头**随包交付
   （files/compat，构建期 -isystem、安装期落 package include/，消费者 include 即得）；
   <format> 走 ``-fexperimental-library`` + ``-lc++experimental``（ladybug 0.18.2 / poppler
   25.12.0.2 既有先例，libc++experimental.a 提供 std::format_error 的 typeinfo/vtable/dtor）。
3. AVX2：aarch64 上 ``check_cxx_compiler_flag("-mavx2")`` 仍返回真（clang 只报
   unused-command-line-argument 警告），上游会因此默认打开 OMATH_USE_AVX2 并给所有目标加
   ``-mfma -mavx2``、把 ``OMATH_USE_AVX2`` 作为 PUBLIC 宏，导致
   ``include/omath/linear_algebra/mat.hpp`` 无条件 ``#include <immintrin.h>``——
   故显式 ``-DOMATH_USE_AVX2=OFF`` 规避 x86 intrinsic 路径。
4. 上游单测在 build() 内以 ctest 全量执行（OMATH_BUILD_TESTS=ON），gstatic 之外无运行期依赖。
"""

import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


def _ohos_sdk_root() -> str:
    roots = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native"))
    if not roots:
        raise ConanInvalidConfiguration("OHOS SDK not found under /data/service/hnp/ohos-sdk.org")
    return roots[-1]


def _ohos_toolchain_flags(package_folder: str, source_folder: str) -> tuple:
    """拼出 clang22 + SDK libc++15 所需的编译/链接旗标（R33：全部显式写死，不依赖环境变量）。"""
    sdk = _ohos_sdk_root()
    sysroot = os.path.join(sdk, "sysroot")
    libcxx_include = os.path.join(sdk, "llvm", "include", "libcxx-ohos", "include", "c++", "v1")
    libcxx_lib = os.path.join(sdk, "llvm", "lib", "aarch64-linux-ohos")
    sysroot_lib = os.path.join(sysroot, "usr", "lib", "aarch64-linux-ohos")
    compat = os.path.join(source_folder, "files", "compat")

    cxx_flags = " ".join(
        [
            "-stdlib=libc++",
            # libc++15 的 <format> 只在 experimental 打开时提供 std::format/std::formatter
            "-fexperimental-library",
            # 打包 clang22 没有默认 sysroot/libc++ 搜索路径（其 test_package 用 CPATH 注入 C 头）
            "-isystem {}".format(libcxx_include),
            "-isystem {}".format(os.path.join(sysroot, "usr", "include", "aarch64-linux-ohos")),
            "-isystem {}".format(os.path.join(sysroot, "usr", "include")),
            # omath 上游 #include <expected>/<print>/<source_location>/<memory_resource>
            # 落到本包交付的同名兼容头
            "-isystem {}".format(compat),
        ]
    )
    link_flags = " ".join(
        [
            "-stdlib=libc++",
            "-B{}".format(sysroot_lib),
            "-L{}".format(libcxx_lib),
            "-L{}".format(sysroot_lib),
            # std::format_error 的 typeinfo/vtable/析构只在 libc++experimental.a 里
            "-lc++experimental",
        ]
    )
    return cxx_flags, link_flags, [libcxx_lib, sysroot_lib]


class OmathConan(ConanFile):
    name = "omath"
    version = "5.6.0"
    description = "General purpose C++ math library (vectors, matrices, quaternions, collision, pathfinding)"
    license = "Zlib"
    homepage = "https://github.com/orange-cpp/omath"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports_sources = "conandata.yml", "patches/*", "files/*"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # OHOS profile 带 os.version，本配方不使用，去掉以免无谓的 package_id 分裂
        self.settings.rm_safe("os.version")

    def validate(self):
        # R32：settings.os 只允许 Linux / OHOS
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "omath 5.6.0 only supports Linux and OHOS, got os={}".format(self.settings.os)
            )

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        # 上游零运行依赖（vcpkg.json 只有 vcpkg-cmake* 宿主工具）；gtest 仅测试用
        pass

    def build_requirements(self):
        # clang15 不支持浮点非类型模板参数（见模块 docstring 第 1 条）
        self.tool_requires("clang/22.1.8")
        self.test_requires("gtest/1.17.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()

        # 设备 affinity=8 而 os.cpu_count()=20（device-facts §一.7）：显式限并发，避免 2.5x 超订
        self.conf.define("tools.build:jobs", 4)

        # profile 的 tools.build:compiler_executables 指向 SDK clang15，改写成 tool_requires
        # 拿到的 clang22（CMakeToolchain 的 CompilersBlock 读的就是这份 conf）
        clang = self.dependencies.build["clang"]
        self.conf.update(
            "tools.build:compiler_executables",
            {
                "c": os.path.join(clang.package_folder, "bin", "clang"),
                "cpp": os.path.join(clang.package_folder, "bin", "clang++"),
            },
        )

        cxx_flags, link_flags, _ = _ohos_toolchain_flags(clang.package_folder, self.source_folder)

        tc = CMakeToolchain(self)
        # —— omath 构建选项 ——
        tc.variables["OMATH_BUILD_TESTS"] = True       # 上游单测随包构建并在 build() 里跑
        tc.variables["OMATH_USE_AVX2"] = False         # aarch64：见 docstring 第 3 条
        tc.variables["OMATH_BUILD_BENCHMARK"] = False
        tc.variables["OMATH_BUILD_EXAMPLES"] = False
        tc.variables["OMATH_ENABLE_LUA"] = False       # 可选依赖 lua/sol2 缺省禁用
        tc.variables["OMATH_ENABLE_HOOKING"] = False   # 可选依赖 safetyhook 缺省禁用
        tc.variables["OMATH_IMGUI_INTEGRATION"] = False
        tc.variables["OMATH_ENABLE_MODULES"] = False   # C++20 modules 需 CMake>=3.28 + 扩展模块支持
        tc.variables["OMATH_ENABLE_VALGRIND"] = False   # 设备无 valgrind，上游默认 ON 会打 warning
        # —— 工具链旗标 ——
        tc.variables["CMAKE_CXX_FLAGS"] = cxx_flags
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = link_flags
        tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = link_flags
        tc.generate()

    def _strip_tool_libdir_from_buildenv(self):
        """把 tool_requires(clang/22.1.8) 的 lib/ 从**已生成**的 buildenv 脚本里摘掉（notes.md 问题表 10）。

        conan 的 VirtualBuildEnv 会把 tool_requires 的 libdirs 拼在 LD_LIBRARY_PATH 最前面，而
        clang/22.1.8 的 lib/ 里带一份 **libc++_shared.so**。CI worker 上（build 62055）它抢在系统库
        之前被 /data/service/hnp/bin/cmake 解析，cmake 在重定位阶段报
        `_ZTVN10__cxxabiv120__si_class_type_infoE: symbol not found`，`cmake.configure()` 直接 rc=127
        （本机因镜像相同未能复现）。本包只需要 clang 的 bin/——它的二进制自带 `RUNPATH=$ORIGIN/../lib`；
        profile 的 SDK llvm/lib（lld 需要的 libxml2.so.16）与调用方继承值全部原样保留，
        PATH 里的 clang bin/ 也保留。幂等：已剥离则不再改动。
        """
        gens = self.generators_folder
        if not gens:
            return
        libdir = os.path.join(self.dependencies.build["clang"].package_folder, "lib")
        for path in glob.glob(os.path.join(glob.escape(gens), "conanbuildenv*.sh")):
            with open(path, "r", encoding="utf-8") as fh:
                lines = fh.readlines()
            changed = False
            out = []
            for line in lines:
                if line.startswith("export LD_LIBRARY_PATH=") or line.startswith("export DYLD_LIBRARY_PATH="):
                    fixed = line.replace(libdir + ":", "").replace(libdir, "")
                    changed = changed or fixed != line
                    line = fixed
                out.append(line)
            if changed:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.writelines(out)
                self.output.info("buildenv 已剥离 tool libdir（保留 bin/ 与 profile 路径）: %s"
                                 % os.path.basename(path))

    def build(self):
        apply_conandata_patches(self)
        # CI 红修复：见 _strip_tool_libdir_from_buildenv docstring（必须在 cmake.configure() 之前）
        self._strip_tool_libdir_from_buildenv()
        # 上游测试夹具 mem_fd_helper.hpp 的回退路径用 std::filesystem::temp_directory_path()；
        # OHOS 的 /tmp 只读（device-facts §一.1），显式把 TMPDIR 指到本包构建目录，
        # 保证设备与 CI worker 上都落在可写目录。
        os.environ["TMPDIR"] = self.build_folder
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            # 上游单测（tests/，ctest 注册在 tests 子构建目录）
            self.run("ctest --test-dir tests --output-on-failure --no-tests=error")
        else:
            self.output.info("cross-building: skip running upstream unit tests")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        # libc++15 缺失的 4 个标准头以同名兼容头随包交付：消费者拿到的 include/ 即可
        # 直接满足上游 ``#include <expected>`` 等（详见模块 docstring 第 2 条）
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "files", "compat"),
            dst=os.path.join(self.package_folder, "include"),
        )

    def package_info(self):
        self.cpp_info.libs = ["omath"]
        self.cpp_info.set_property("cmake_file_name", "omath")
        self.cpp_info.set_property("cmake_target_name", "omath::omath")
        self.cpp_info.includedirs = ["include"]
        # omath 头文件使用 std::format（libc++15 需 experimental 才提供），随包传递给消费者
        self.cpp_info.cxxflags = ["-fexperimental-library"]
        if str(self.settings.os) == "OHOS":
            # std::format_error 的运行时符号在 libc++experimental.a（共享 libc++ 缺该符号）
            self.cpp_info.system_libs = ["c++experimental"]
