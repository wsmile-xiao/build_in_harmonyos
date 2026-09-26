#!/usr/bin/env python3
"""Conan recipe - metaeuk 7-bba0d80 (CMake).

MetaEuk: sensitive gene-finding and protein annotation tool for large
eukaryotic genomes, built on a vendored MMseqs2 source tree (lib/mmseqs,
shipped inside the upstream tag tarball - no external dependency).

OHOS adaptation notes:
  - cmake_minimum_required(2.8.12) is rejected by CMake >= 4; the repo
    standard CMAKE_POLICY_VERSION_MINIMUM=3.5 workaround is applied.
  - Upstream derives its version string from `git rev-parse`; tag tarballs
    carry no .git, so VERSION_OVERRIDE=7-bba0d80 is passed (the upstream
    supported mechanism).  Measured effect: bare `metaeuk` (non-tty) exits 0
    and prints `metaeuk Version: 7-bba0d80`.  Note `--version` is NOT a valid
    subcommand here (it exits non-zero), so the version banner is asserted
    from the bare invocation only.
  - SIMD: explicit HAVE_ARM8=1 (aarch64 baseline NEON, -march=armv8-a+simd),
    NATIVE_ARCH=0 to avoid host-dependent probing in the CI worker.
  - Upstream registers no automated tests, so N_static = 0: `add_test(` /
    `enable_testing` / `include(CTest)` hit 0/0/0 across every CMakeLists.txt
    and .cmake in the tree, and there is no Makefile.am/configure.ac either
    (no automake TESTS entry point).  Two things are test-shaped but are not
    registered cases: the vendored lib/mmseqs/src/test/ directory is upstream
    MMseqs2's manual self-test harness (doubling as a regression tool) - 35 of
    its sources carry a `main`, deliberately NOT converted into a case count -
    and its only entry point, `add_subdirectory(test)`
    (lib/mmseqs/src/CMakeLists.txt:254), sits inside the double gate
    `if (NOT FRAMEWORK_ONLY)` (line 243; root CMakeLists.txt:6 force-sets
    FRAMEWORK_ONLY) plus `if (HAVE_TESTS)` (line 253; defaults to 0), so a
    self-contained build of this recipe never adds that subdirectory; and
    `mmseqs_setup_test()` (lib/mmseqs/cmake/MMseqsSetupTest.cmake) only calls
    add_executable(), never add_test(), so it registers nothing even when
    enabled.  `tests/` (metaeuk-regression) and lib/mmseqs/util/regression are
    git submodules left empty in the tag tarball; azure-pipelines drives them
    externally (clone submodules + -DHAVE_TESTS=1).  Because N_static = 0, the
    consumer test_package exercises the real binary instead (version banner,
    help, argument validation, and an end-to-end easy-predict run on
    synthetic data).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches


class MetaeukConan(ConanFile):
    name = "metaeuk"
    version = "7-bba0d80"
    description = "MetaEuk: sensitive gene-finding and protein annotation for large eukaryotic genomes (MMseqs2 based)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/soedinglab/metaeuk"
    url = ""  # CI fills this
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "metaeuk is only supported on Linux/OHOS, not " + str(self.settings.os))
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds currently support armv8 only")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # tag tarball 无 .git：用上游支持的 VERSION_OVERRIDE 注入真实版本
        # （普通编译定义，经 toolchain 注入无时序问题）
        tc.variables["VERSION_OVERRIDE"] = self.version
        # aarch64 基线 NEON，固定 ARM8 路径，避免 CI 探测主机差异
        tc.variables["NATIVE_ARCH"] = False
        tc.variables["HAVE_ARM8"] = True
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(variables={
            # CMake 4 拒绝 <3.5 的 cmake_minimum_required。出处更正：本机制
            # 的知识库条目是 knowledge/drafts/
            # DRAFT-E321-cmake4-policy-version-minimum.kv，其 `# Software:`
            # 实测为 etcd-cpp-apiv3 0.15.4（即该条目的原始验证实例）；知识库内
            # 不存在「cpputest + CMAKE_POLICY_VERSION_MINIMUM」条目，cpputest
            # 与本机制无关。本包是该机制在 CMake 2.8.x 老基线上的再次命中。
            # 该变量必须经命令行 -D 在任何 CMakeLists 解析前生效——
            # tc.variables 写入 toolchain 文件时序无效，必须走
            # cmake.configure(variables=...)
            "CMAKE_POLICY_VERSION_MINIMUM": "3.5",
        })
        cmake.build()
        # 上游无任何测试注册入口（全树 add_test( / enable_testing /
        # include(CTest) 命中 0/0/0，亦无 Makefile.am/configure.ac），
        # N_static=0，R51 如实申报。lib/mmseqs/src/test/ 那批文件是 vendored
        # MMseqs2 的上游手工自测 harness（兼回归工具），不是注册用例：其唯一
        # 入口 add_subdirectory(test) 位于 root CMakeLists.txt:6 FORCE 的
        # FRAMEWORK_ONLY 与默认 0 的 HAVE_TESTS 双闸之内，本包自含构建下永不
        # 加入，且 mmseqs_setup_test() 自身只 add_executable 不 add_test，
        # 故其 35 个含 main 的文件不折算为用例数。验证以 test_package 消费者
        # 真实运行被测二进制替代。

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENCE.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
