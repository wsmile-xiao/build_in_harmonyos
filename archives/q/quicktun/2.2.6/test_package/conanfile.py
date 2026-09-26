import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class QuicktunTestConan(ConanFile):
    """quicktun 是应用包：消费者面 = 随包发布的可执行文件。

    test_quicktun.c 以绝对路径调用包内 quicktun.keypair，并用 libsodium 在进程内
    独立算出同一标量的 Curve25519 公钥做交叉核对，断言结果决定退出码。
    """

    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 预言机要独立链 libsodium（它同时也是被测包的依赖，这里显式直链，
        # 好让 CMakeDeps 稳定产出 libsodium::libsodium 目标）
        self.requires("libsodium/1.0.22")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        qt = self.dependencies["quicktun"]
        # bindirs 可能是相对 package_folder 的路径；os.path.join 对已是绝对路径的
        # 第二段会直接返回第二段，因此两种情形都安全。
        candidates = [os.path.join(qt.package_folder, d, "quicktun.keypair")
                      for d in qt.cpp_info.bindirs]
        tool = next((p for p in candidates if os.path.isfile(p)),
                    candidates[0] if candidates else "quicktun.keypair")
        tc = CMakeToolchain(self)
        tc.variables["QUICKTUN_KEYPAIR"] = tool.replace("\\", "/")
        tc.variables["QUICKTUN_VERSION"] = str(qt.ref.version)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        exe = os.path.join(self.cpp.build.bindirs[0], "test_quicktun")
        if not can_run(self):
            # 交叉构建时产物无法在本机执行 —— 如实报跳过并给出原因，不伪造通过
            self.output.warning(
                f"SKIP: build arch != host arch，无法执行 {exe}（交叉构建限制，"
                "非测试失败）")
            return
        self.run(f'"{exe}"', env="conanrun")
