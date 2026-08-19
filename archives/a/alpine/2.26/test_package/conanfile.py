import os

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # alpine 是工具型包：编译运行 test_alpine.c，用 alpine --version
        # 输出检查（"Alpine" 关键字）验证二进制可运行
        alpine_bin = os.path.join(self.dependencies["alpine"].package_folder,
                                  "bin", "alpine")
        if not os.path.exists(alpine_bin):
            raise Exception(f"alpine binary not found: {alpine_bin}")
        self.output.info(f"alpine binary found: {alpine_bin}")
        src = os.path.join(self.source_folder, "src", "test_alpine.c")
        test_bin = os.path.join(self.build_folder, "test_alpine")
        self.run(f"${{CC:-clang}} ${{CFLAGS}} -o \"{test_bin}\" \"{src}\"",
                 env="conanbuild")
        self.run(f"\"{test_bin}\" \"{alpine_bin}\"", env="conanrun")
