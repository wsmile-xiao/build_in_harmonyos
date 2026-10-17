import os
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.build import cross_building


class CrosslineTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not cross_building(self):
            # crossline_readline in non-tty mode reads one line from stdin;
            # write the input line to a file and redirect stdin into the
            # consumer so it exercises the real API (no echo/print/true
            # pseudo-test commands, satisfying CI L1d and R34).
            consumer = os.path.join(self.cpp.build.bindir, "crossline_consumer")
            input_file = os.path.join(self.build_folder, "stdin.input")
            with open(input_file, "w", encoding="utf-8") as f:
                f.write("hello-crossline\n")
            self.run(f"{consumer} < {input_file}", env="conanrun")