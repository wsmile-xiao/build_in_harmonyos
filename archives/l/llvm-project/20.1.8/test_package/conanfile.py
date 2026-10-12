import os
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class LlvmProjectTestConan(ConanFile):
    """test_package — 按下游 ispc 1.28.2 的真实消费姿势验证本包开发面（R34 反空壳）。

    ① CMake 面：find_package(LLVM) + find_package(Clang)，并用 ispc 的原判据
       find_library(clangFrontend/clangBasic/clangEdit/clangLex/clangSupport/clangASTMatchers
                    HINTS ${LLVM_LIBRARY_DIRS}) 逐项定位（CMakeLists.txt 内断言）；
    ② 链接并真实运行探针：调用 6 个 clang 组件库 + libLLVM.so 的导出符号；
    ③ 工具面：包内 llvm-config（ispc cmake/FindLLVM.cmake 的入口，含 --targets-built 的
       AArch64+ARM 断言）与 FileCheck。
    """

    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        pkg = self.dependencies["llvm-project"].package_folder
        q = shlex.quote

        # ① 开发面探针：链接 6 个 clang 组件静态库 + libLLVM.so，真实运行。
        #    必须用 conanrun 环境（package_type=library + shared=True ⇒ traits=shared-library
        #    ⇒ run=True ⇒ VirtualRunEnv 会把本包 lib/ 放进 LD_LIBRARY_PATH）；否则宿主
        #    LD_LIBRARY_PATH（profile buildenv 的 OHOS SDK llvm/lib）会遮蔽 libLLVM.so.20.1。
        probe = os.path.join(self.build_folder, "clang_devface_probe")
        self.run(q(probe), env="conanrun")

        # ② 工具面：llvm-config（ispc FindLLVM.cmake 必须找到并能执行）
        llvm_config = os.path.join(pkg, "bin", "llvm-config")
        for arg in ("--version", "--libdir", "--includedir", "--libfiles aarch64 arm x86"):
            self.run("{} {}".format(q(llvm_config), arg), env="conanrun")
        # ispc 用 `llvm-config --targets-built` 判定 LLVM_SUPPORTS_ARM：必须同时含 AArch64 与 ARM，
        # 否则 ispc 的 ARM_ENABLED=OFF，在 aarch64 宿主上会 "Either X86, ARM, WASM or XE targets
        # need to be enabled." FATAL_ERROR；X86 是 ispc lit 套件 X86_ENABLED 用例的需求。
        targets = subprocess.run([llvm_config, "--targets-built"],
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 universal_newlines=True)
        if targets.returncode != 0:
            raise ConanException("llvm-config --targets-built rc={}: {}".format(
                targets.returncode, targets.stdout))
        built = targets.stdout
        for want in ("AArch64", "ARM", "X86"):
            if want not in built:
                raise ConanException("llvm-config --targets-built 必须含 {}，实测: {}".format(want, built))

        # ③ FileCheck（ispc ISPC_INCLUDE_TESTS 时必需）
        filecheck = os.path.join(pkg, "bin", "FileCheck")
        check_in = os.path.join(self.source_folder, "filecheck_input.txt")
        check_pat = os.path.join(self.source_folder, "filecheck_pattern.txt")
        self.run("{} --input-file={} {}".format(q(filecheck), q(check_in), q(check_pat)),
                 env="conanrun")
