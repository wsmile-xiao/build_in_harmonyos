import os

from conan import ConanFile
from conan.tools.env import Environment


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv"

    def requirements(self):
        # conan 2：test_package 必须显式声明被测包引用（sherlock 先例）
        self.requires(self.tested_reference_str)

    def test(self):
        # mda-lv2 是 LV2 插件 bundle：三级验证
        #  1) test_mda_lv2.c：bundle 结构 + 36 ELF64/AArch64 + TestTone
        #     完整生命周期（dlopen/instantiate/run/cleanup）
        #  2) test_ohos_mda_lv2.sh：readelf 逐插件 NEEDED/RPATH 校验
        #     （OHOS 专项）
        #  3) test_ohos_load_all.c：全部 36 插件 dlopen + URI 校验 +
        #     4 插件抽样生命周期（OHOS 专项）
        bundle = os.path.join(self.dependencies["mda-lv2"].package_folder,
                              "lib", "lv2", "mda.lv2")
        if not os.path.isdir(bundle):
            raise Exception(f"mda.lv2 bundle missing: {bundle}")

        # LD_LIBRARY_PATH：DRAFT-13536——OHOS 默认环境带 el1/bundle 条目
        # 使 musl ldso 放弃后续搜索，libc++_shared.so 解析失败；把
        # /system/lib64 prepend 保证 C++ 插件可加载（R33：用 conan
        # Environment API，不裸用 shell 变量）
        env = Environment()
        if self.settings.os == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")

        # 1) 主测试：编译运行 test_mda_lv2.c（-ldl：dlopen/dlsym）
        src = os.path.join(self.source_folder, "src", "test_mda_lv2.c")
        test_bin = os.path.join(self.build_folder, "test_mda_lv2")
        self.run(f'${{CC:-clang}} ${{CFLAGS}} -o "{test_bin}" "{src}" -ldl',
                 env="conanbuild")
        with env.vars(self).apply():
            self.run(f'"{test_bin}" "{bundle}"', env="conanrun")

        # 2) OHOS 专项（readelf）：平台无关脚本，仅 OHOS 运行
        if self.settings.os == "OHOS":
            import shutil
            bash = (os.environ.get("CONFIG_SHELL")
                    or shutil.which("bash") or "/data/service/hnp/bin/bash")
            script = os.path.join(self.source_folder, "src",
                                  "test_ohos_mda_lv2.sh")
            with env.vars(self).apply():
                self.run(f'"{bash}" "{script}" "{bundle}"', env="conanrun")

            # 3) OHOS 专项（全插件加载）：编译运行 test_ohos_load_all.c
            src2 = os.path.join(self.source_folder, "src",
                                "test_ohos_load_all.c")
            bin2 = os.path.join(self.build_folder, "test_ohos_load_all")
            self.run(f'${{CC:-clang}} ${{CFLAGS}} -o "{bin2}" "{src2}" -ldl',
                     env="conanbuild")
            with env.vars(self).apply():
                self.run(f'"{bin2}" "{bundle}"', env="conanrun")

        self.output.info("mda-lv2 test_package PASS")
