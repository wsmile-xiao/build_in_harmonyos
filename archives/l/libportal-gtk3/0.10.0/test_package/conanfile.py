import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.gnu import PkgConfigDeps


class LibportalGtk3TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "PkgConfigDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return
        # conan's test() runs "./test_package" through a plain shell; inject
        # the runtime library path through os.environ directly so the OHOS
        # musl loader finds the conan-cached shared objects (alkimia
        # test_package precedent). /system/lib64 provides libc++_shared.so
        # needed by the harfbuzz dependency chain.
        lib_dirs = [
            os.path.join(dep.package_folder, "lib")
            for dep in self.dependencies.values()
            if dep.package_folder
        ]
        if str(self.settings.os) == "OHOS":
            lib_dirs.append("/system/lib64")
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(lib_dirs)
        os.environ.setdefault("HOME", os.path.expanduser("~"))
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_libportal_gtk3")
        self.run(f'"{bin_path}"', cwd=self.build_folder)
