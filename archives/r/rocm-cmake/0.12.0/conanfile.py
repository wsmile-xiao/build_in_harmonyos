from conan import ConanFile
from conan.tools.files import copy
import os

class RocmCMakeConan(ConanFile):
    name = "rocm-cmake"
    version = "0.12.0"
    package_type = "build-scripts"
    # 将这两个目录作为源文件导出到 Conan 缓存
    exports_sources = "rocm/*", "rocmcmakebuildtools/*"

    def package(self):
        src = self.source_folder
        dst = self.package_folder
        copy(self, "*", src=os.path.join(src, "rocm"), dst=os.path.join(dst, "share", "rocm"))
        copy(self, "*", src=os.path.join(src, "rocmcmakebuildtools"), dst=os.path.join(dst, "share", "rocmcmakebuildtools"))

    def package_info(self):
        self.cpp_info.builddirs = ["share/rocm/cmake", "share/rocmcmakebuildtools/cmake"]
        self.cpp_info.set_property("cmake_find_package_name", "ROCM")
        self.cpp_info.set_property("cmake_find_mode", "both")
