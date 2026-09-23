import os
from conan import ConanFile
from conan.tools.cmake import CMake,cmake_layout
class DoctestTestConan(ConanFile):
    settings="os","compiler","build_type","arch"
    generators="CMakeDeps","CMakeToolchain"
    def requirements(self): self.requires(self.tested_reference_str)
    def layout(self): cmake_layout(self)
    def build(self):
        cm=CMake(self); cm.configure(); cm.build()
    def test(self):
        CMake(self).test()
        self.run(os.path.join(self.build_folder,"test_doctest"),env="conanrun")
