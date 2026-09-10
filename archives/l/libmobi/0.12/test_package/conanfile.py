import os
import shutil
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration

class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["libmobi"].cpp_info
        # 头闭包自检要用「所有依赖」的 include（libmobi 无外部依赖，仅自身）
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        libdirs = []
        for _ref, _d in self.dependencies.items():
            libdirs += _d.cpp_info.libdirs
        cc = os.environ.get("CC", "clang")
        # C 测试不能收 C++ 标准开关；musl 上用 gnu 方言（POSIX 函数声明）
        std_flag = "-std=gnu99"
        link = " ".join(["-L" + p for p in libdirs]
                        + ["-l" + l for l in dep.libs]
                        + ["-Wl,-rpath," + p for p in libdirs])
        self.run(f"{cc} {std_flag} test.c -o test_probe {inc} {link}")
        # 鸿蒙特有测试（独立入口）：ELF64 AArch64 / musl NEEDED / .codesign /
        # SONAME / 真实文件解析，检查点不与 test.c 的 39 项内部断言重复计数
        self.run(f"{cc} {std_flag} test_ohos_libmobi.c -o test_ohos_probe {inc} {link}")

    def test(self):
        # Resolve Bash from CONFIG_SHELL or PATH.
        bash = shutil.which(os.environ.get("CONFIG_SHELL") or "bash")
        if not bash:
            raise ConanInvalidConfiguration("bash not found in CONFIG_SHELL or PATH")
        self.run(f"{bash} -c './test_probe'", env="conanrun")
        # 鸿蒙特有入口 1/1：被测包的 lib/bin 目录以参数传入，测试内不硬编码布局
        dep = self.dependencies["libmobi"]
        pkg = dep.package_folder
        self.run(f"{bash} -c './test_ohos_probe {pkg}/lib {pkg}/bin'",
                 env="conanrun")
