from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
import os


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "CMakeDeps"
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
        # 实质依赖被测包：链接 i18n-demo 并实际执行它安装的 CLI
        exe = os.path.join(self.cpp.build.bindirs[0], "test_i18n-demo")
        out_file = os.path.join(self.build_folder, "i18n-cli.out")
        self.run(f'"{exe}"')

        cli = os.path.join(self.dependencies[self.tested_reference_str].cpp_info.bindirs[0],
                           "i18n-demo-cli")
        self.run(f'"{cli}" demo "hello from sample" > "{out_file}"')
        with open(out_file, "r") as fh:
            got = fh.read().strip()
        # 无可用翻译目录时 gettext 返回 msgid 原样 → 输出可确定性校验
        assert got == "hello from sample", f"unexpected gettext output: {got!r}"
