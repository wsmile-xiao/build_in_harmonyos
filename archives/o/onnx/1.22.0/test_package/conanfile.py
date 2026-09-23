from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class OnnxTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # protobuf keeps its own CMake config (cmake_find_mode=none), so
        # CMakeDeps does not emit find files for it; point every consumed
        # package at its installed config directly, including ONNX itself
        # (verifies the packaged ONNXConfig.cmake consumer path).
        onnx = self.dependencies["onnx"]
        protobuf = self.dependencies["protobuf"]
        abseil = self.dependencies["abseil-cpp"]
        tc = CMakeToolchain(self)
        tc.variables["onnx_DIR"] = f"{onnx.package_folder}/lib/cmake/ONNX".replace("\\", "/")
        tc.variables["Protobuf_DIR"] = f"{protobuf.package_folder}/lib/cmake/protobuf".replace("\\", "/")
        tc.variables["absl_DIR"] = f"{abseil.package_folder}/lib/cmake/absl".replace("\\", "/")
        tc.variables["utf8_range_DIR"] = f"{protobuf.package_folder}/lib/cmake/utf8_range".replace("\\", "/")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            self.run("ctest --output-on-failure --no-tests=error", cwd=self.build_folder, env="conanrun")
