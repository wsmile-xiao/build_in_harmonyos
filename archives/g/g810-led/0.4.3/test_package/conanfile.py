import os

from conan import ConanFile


class G810LedTestConan(ConanFile):
    """test_package — 消费者验证：编译链接公开 API + 运行 CLI 冒烟测试。

    consumer.cpp 仅通过公开头文件 include/g810-led/Keyboard.h 与
    libg810-led 链接，模拟业务上层组件使用三方库。
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pkg = self.dependencies["g810-led"]
        inc = os.path.join(pkg.package_folder, "include")
        lib = os.path.join(pkg.package_folder, "lib")
        # 与主配方一致：字典型 conf 先取整个 dict 再取子键（R33）
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"
        self.run(f"{cxx} -std=gnu++11 -I{inc} consumer.cpp -L{lib} -lg810-led -o consumer")

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run("./consumer", env="conanrun")
        self.run(f"{bash} cli_smoke.sh", env="conanrun")
