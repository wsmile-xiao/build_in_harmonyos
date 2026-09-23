#!/usr/bin/env python3
"""Conan recipe — libff 0.2.1 (cmake)

libff 是 zk-SNARKs 基础的 C++ 配对密码学库（有限域 / 椭圆曲线 / 双线性配对）。
上游: https://github.com/scipr-lab/libff

OHOS 适配要点（证据链见 archives/l/libff/0.2.1/notes.md）:
- BN128（上游默认曲线）不可用的双重证据（对照实验见 notes.md）：
  (a) 官方 tag 归档的 depends/ate-pairing、depends/xbyak 为空目录（git 子模块
      不进 tag 归档），默认 CURVE=BN128 在 configure 阶段即失败
      （Cannot find source file "ate-pairing/src/zm.cpp"）；
  (b) 按 .gitmodules gitlink 精确 commit（ate-pairing=e6989012、xbyak=f0a8f7fa）
      下载并组装子模块后 configure 成功，但编译失败于 zm2.cpp:3644 ——
      该处在 MIE_USE_X64ASM 守卫（3574 行已 #endif）之外无条件引用 Xbyak
      （x86-64 运行时 JIT）；aarch64 上 zm.h:68 #undef MIE_USE_X64ASM 且
      xbyak.h 不被 include。BN128 路径为上游 x86-64-only 设计。
  因此固定 CURVE=ALT_BN128：同一条 BN254 曲线（q/r 常数与 BN128 逐位一致，
  见 notes.md 差异对照表），实现自包含于 libff/ 源码树，aarch64 可移植。
- **后端契约（公开声明）**：本包只提供 ALT_BN128 一种曲线路径，不提供上游
  默认 BN128。两者密码学常数一致但**非等价替换**：公开类型名（alt_bn128_*
  vs bn128_*，bn::Fp vs Fp_model）、ABI 对象布局、operator<</>> 流序列化
  格式均不同，既有 BN128 消费者源码/数据不能默认直接迁移（差异对照见
  notes.md）。该契约经 package_info() cpp_info.defines 下发 CURVE_ALT_BN128，
  并由 test_package 以 static_assert 门禁验证。
- **序列化宏契约（E543）**：上游 BINARY_OUTPUT/MONTGOMERY_OUTPUT 默认 ON，
  影响已安装公共模板（bigint.tcc/fp.tcc/serialization.* 的 operator<</>>），
  而这些模板在消费者侧实例化——宏不同即序列化格式不同。故二者作为配方
  option（默认对齐上游 ON），进 package ID，并经 cpp_info.defines 同步下发。
  LOWMEM/MULTICORE 默认 OFF，仅影响 multiexp.tcc 模板，启用时同样下发。
- WITH_PROCPS 默认 ON，pkg-config 探测 libprocps；OHOS 无 procps，关闭后上游
  自带 -DNO_PROCPS 回退路径（libff/common/profiling.cpp:26 已实测编译通过）。
- USE_ASM 的汇编仅在 __x86_64__ 激活（fp.tcc:26 等），aarch64 自动走可移植路径。
- CMake 4.x 需要 CMAKE_POLICY_VERSION_MINIMUM=3.5（上游要求 2.8，E103/E187）。
- 上游 cmake_minimum_required(2.8) 时代写法 + -std=c++11 硬编码进 CMAKE_CXX_FLAGS，
  与 Conan cppstd=17 注入冲突时会拼接（前者在前）——c++11 语法在该库源码内自洽，
  实测 gcc/clang 均接受双重 -std（后者覆盖），无需 patch。
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get


class LibffConan(ConanFile):
    name = "libff"
    version = "0.2.1"
    description = "C++ library for Finite Fields and Elliptic Curves (zk-SNARKs arithmetic, pairings)"
    license = "MIT"
    homepage = "https://github.com/scipr-lab/libff"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("zk-snarks", "cryptography", "finite-fields", "elliptic-curves", "pairing")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_openssl": [True, False],
        "lowmem": [True, False],
        "multicore": [True, False],
        # 序列化格式契约（E543）：影响已安装公共模板 operator<</>> 的
        # 实例化结果，默认值对齐上游 CMake option 默认（均 ON）
        "binary_output": [True, False],
        "montgomery_output": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_openssl": True,
        "lowmem": False,
        "multicore": False,
        "binary_output": True,
        "montgomery_output": True,
    }

    def export_sources(self):
        # 本配方无源码 patch（ALT_BN128 + NO_PROCPS 均为上游原生 CMake 选项），
        # conandata.yml 仅含 sources。
        pass

    def requirements(self):
        # GMP 是硬依赖（find_path/find_library REQUIRED 语义），且 libff 公开
        # 头 bigint.hpp 直接 #include <gmp.h> —— 属于传递依赖，消费者可见。
        self.requires("gmp/6.3.0.1", transitive_headers=True)
        if self.options.with_openssl:
            # OpenSSL 供 multiexp_profile 的 OPENSSL_LIBRARIES 链接（可选路径），
            # 与上游 find_package(OpenSSL REQUIRED) 对齐
            self.requires("openssl/3.5.6")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def validate(self):
        # ALT_BN128 是唯一能在官方归档上自包含构建的曲线路径（见模块 docstring 证据链）
        if self.settings.os == "OHOS" and self.info.settings.arch not in ("armv8", "x86_64"):
            raise ConanInvalidConfiguration(
                f"libff 0.2.1 OHOS 支持仅在 aarch64(armv8) 验证，当前 arch={self.info.settings.arch}"
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E103/E187: CMake 4.x 移除 <3.5 兼容模式，上游要求 2.8
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # 官方归档子模块为空，BN128/EDWARDS 路径不可构建；ALT_BN128 自包含
        tc.cache_variables["CURVE"] = "ALT_BN128"
        # OHOS 无 libprocps；上游提供 NO_PROCPS 回退（profiling.cpp）
        tc.cache_variables["WITH_PROCPS"] = False
        # 曲线/序列化选项与上游语义对齐（默认值保持上游默认）
        tc.cache_variables["LOWMEM"] = bool(self.options.lowmem)
        tc.cache_variables["MULTICORE"] = bool(self.options.multicore)
        # E543：序列化宏是包契约而非内部开关（见模块 docstring），
        # 由 option 决定并同步进 package ID 与 cpp_info.defines
        tc.cache_variables["BINARY_OUTPUT"] = bool(self.options.binary_output)
        tc.cache_variables["MONTGOMERY_OUTPUT"] = bool(self.options.montgomery_output)
        # IS_LIBFF_PARENT=ON 时才注册上游测试目标与 install() 规则（上游默认 ON）
        tc.cache_variables["IS_LIBFF_PARENT"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # ── 上游官方测试（L1 层）──
        # 上游 3 个测试目标均为 EXCLUDE_FROM_ALL（挂在 check target 下），
        # 默认 all target 不构建，必须显式指定 target 编译测试二进制。
        upstream_tests = (
            "algebra_bilinearity_test",
            "algebra_groups_test",
            "algebra_fields_test",
        )
        for target in upstream_tests:
            cmake.build(target=target)
        # 运行测试需要两个条件同时满足（E294 双构建树法变体）：
        # (1) can_run：本机（OHOS PC 自身即 armv8）可原生执行；
        # (2) 无 NDEBUG：上游测试以 assert() 为 oracle（test_*.cpp 源码
        #     #ifndef NDEBUG 门控，NDEBUG 下打印提示后直接空转返回）。
        #     Conan Release 注入 -O3 -DNDEBUG，所以正式树二进制不能用作测试，
        #     用同一 toolchain 另起 Debug 测试树（无 NDEBUG）构建并运行。
        if can_run(self):
            self._run_upstream_tests_debug_tree()

    def _run_upstream_tests_debug_tree(self):
        """第二个构建树：CMAKE_BUILD_TYPE=Debug（无 NDEBUG），复用主树 toolchain，
        构建上游全部测试并 ctest 执行。测试树不安装、不影响正式产物。"""
        build_dir = os.path.join(self.build_folder, "build-tests")
        toolchain = os.path.join(
            self.generators_folder, "conan_toolchain.cmake"
        )
        # 主树 GMP/OpenSSL 已由 CMakeDeps 注入（CMAKE_PREFIX_PATH/env），
        # Debug 树复用同一 conanbuild 环境即可解析相同依赖。
        cfg_cmd = [
            "cmake",
            "-S", self.source_folder,
            "-B", build_dir,
            f"-DCMAKE_TOOLCHAIN_FILE={toolchain}",
            "-DCURVE=ALT_BN128",
            "-DWITH_PROCPS=OFF",
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
            "-DCMAKE_BUILD_TYPE=Debug",
        ]
        self.run(" ".join(cfg_cmd), env="conanbuild")
        for target in (
            "algebra_bilinearity_test",
            "algebra_groups_test",
            "algebra_fields_test",
        ):
            self.run(
                f'cmake --build "{build_dir}" --target {target} -- -j2',
                env="conanbuild",
            )
        # 运行期需解析 gmp 共享库（LD_LIBRARY_PATH 由 conanrun 环境提供，
        # conanbuild 不含依赖包的 lib 路径）
        self.run(
            f'ctest --test-dir "{build_dir}" --output-on-failure --timeout 600',
            env="conanrun",
        )

    def package(self):
        # 上游 install(TARGETS ff DESTINATION lib) + install(DIRECTORY "" DESTINATION include/libff)
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libff")
        self.cpp_info.set_property("cmake_target_name", "libff::ff")
        self.cpp_info.set_property("pkg_config_name", "libff")
        self.cpp_info.libs = ["ff"]
        self.cpp_info.libdirs = ["lib"]
        # 上游 target_include_directories(ff PUBLIC ..)：消费者需 #include "libff/..."
        self.cpp_info.includedirs = ["include"]
        # 消费者宏契约全集（E543）：凡影响已安装公共头/模板实例化结果的
        # 特性宏必须随包下发，否则消费者与库本体按不同配置实例化同一模板。
        # 1) CURVE_ALT_BN128：上游 ec_pp.hpp 依 CURVE_* 宏选择 default_ec_pp，
        #    构建侧由根 CMakeLists 的 add_definitions(-DCURVE_${CURVE}) 注入。
        # 2) BINARY_OUTPUT/MONTGOMERY_OUTPUT：影响 bigint.tcc/fp.tcc/
        #    serialization.* 中 operator<</>> 的实例化（模板在消费者侧编译），
        #    与库本体构建选项逐一对齐（默认 ON，随 option 变化）。
        # 3) LOWMEM/MULTICORE：影响 multiexp.tcc 模板路径选择，启用时下发。
        defines = ["CURVE_ALT_BN128"]
        if self.options.binary_output:
            defines.append("BINARY_OUTPUT")
        if self.options.montgomery_output:
            defines.append("MONTGOMERY_OUTPUT")
        # Conan 2: package_info() 中禁用 self.info，option 读取用 self.options
        if self.options.lowmem:
            defines.append("LOWMEM")
        if self.options.multicore:
            defines.append("MULTICORE")
        self.cpp_info.defines = defines

    def package_id(self):
        # with_openssl 仅影响 multiexp_profile 的链接路径，不影响 libff.a
        # 公共 ABI；序列化宏与曲线契约影响已安装头的实例化结果，保留在
        # package ID 中（不同配置不得复用同一包）。
        del self.info.options.with_openssl
