import os

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv"

    def requirements(self):
        # conan 2：test_package 必须显式声明被测包引用，否则
        # "doesn't declare any requirement" 报错
        self.requires(self.tested_reference_str)

    def test(self):
        # sherlock.lv2 是 LV2 插件 bundle（库型）：编译运行 test_sherlock.c，
        # 验证插件 bundle（manifest.ttl 含插件声明 + sherlock.so 存在）
        bundle = os.path.join(self.dependencies["sherlock.lv2"].package_folder,
                              "lib", "lv2", "sherlock.lv2")
        src = os.path.join(self.source_folder, "src", "test_sherlock.c")
        test_bin = os.path.join(self.build_folder, "test_sherlock")
        # -ldl：test_sherlock.c 用 dlopen/dlsym 加载 sherlock.so 并调用
        # lv2_descriptor()（R34 非空壳——需链接 libdl）
        self.run(f"${{CC:-clang}} ${{CFLAGS}} -o \"{test_bin}\" \"{src}\" -ldl",
                 env="conanbuild")
        self.run(f"\"{test_bin}\" \"{bundle}\"", env="conanrun")
