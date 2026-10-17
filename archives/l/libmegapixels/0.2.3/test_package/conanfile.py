import os
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout

class LibMegapixelsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def layout(self):
        cmake_layout(self)

    def test(self):
        if can_run(self):
            cmd = os.path.join(self.cpp.build.bindir, "test_package")

            # 拼接所有依赖的 lib 目录
            lib_paths = []
            for dep in self.dependencies.values():
                libdir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(libdir):
                    lib_paths.append(libdir)

            old_ld = os.environ.get("LD_LIBRARY_PATH", "")
            if old_ld:
                lib_paths.append(old_ld)
            ld_path = ":".join(lib_paths)

            self.output.info(f"LD_LIBRARY_PATH={ld_path}")

            # 用 self.run 执行 shell 命令，在命令中设置 LD_LIBRARY_PATH
            self.run(f'LD_LIBRARY_PATH="{ld_path}" "{cmd}"')
