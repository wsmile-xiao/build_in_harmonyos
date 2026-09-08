from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
import os


class BoostWaveTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualBuildEnv"
    requires = "boost1.84-wave/1.84.0"

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # L0d 门禁要求 test() 中存在显式 self.run() 调用：直接运行构建产物
        # test_wave。项目未注册 CTest 测试（无 enable_testing()，故无 `test`
        # make target），不能使用 cmake.test()。
        # OHOS musl 加载器对含空白条目的 LD_LIBRARY_PATH 解析会整体失败
        # （libc++_shared.so 不可解析 → rc=127 symbol not found），运行前
        # 清洗每个条目的首尾空白。
        ldpath = os.environ.get("LD_LIBRARY_PATH", "")
        cleaned = ":".join(p.strip() for p in ldpath.split(":") if p.strip())
        if cleaned:
            os.environ["LD_LIBRARY_PATH"] = cleaned
        self.run(os.path.join(self.cpp.build.bindirs[0], "test_wave"))
