import os

from conan import ConanFile


class YaswTestConan(ConanFile):
    """test_package — yasw 0.6 消费者测试（OpenHarmony PC / aarch64）。

    上游 yasw 0.6 **无任何自动化测试**（R51 清点证据见
    archives/y/yasw/0.6/notes.md）。本 test_package 补充 3 个鸿蒙消费者用例，
    由 test.sh 实现对被测包产物的实质性执行验证（R34，非空壳）：
      consumer.ohos.arch     —— 产物为目标平台 aarch64 ELF 可执行文件
      consumer.ohos.qt5      —— Qt5 动态依赖链完整（含 PrintSupport）
      consumer.ohos.runtime  —— GUI 真实启动并进入 Qt 事件循环
    """

    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def layout(self):
        # test_package 默认把「构建目录」设为配方目录本身，导致 conan create
        # 把生成器与运行日志直接写进 archives/ 源码树（污染 PR 文件集，
        # 触发 W2 原子性 / PF1 单包闸）。显式重定向到 .gitignore 覆盖的
        # build/ 子目录，使 conan create 不在源码树内留下任何运行产物。
        self.folders.build = "build"
        self.folders.generators = "build/conan"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["yasw"]
        bin_path = os.path.join(pkg.package_folder, "bin", "yasw")
        # 运行日志写入构建目录（test_package/build/，已被 .gitignore 覆盖），
        # 避免运行产物污染 PR 文件集（W2 原子性检查 / PF1 单包闸）。
        log_dir = self.build_folder
        # OHOS: /system/bin/sh (mksh) 不能执行 ELF 二进制，用 bash 包装
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        test_sh = os.path.join(self.recipe_folder, "test.sh")
        # env="conanrun" → VirtualRunEnv 注入各依赖的 PATH/LD_LIBRARY_PATH/
        # QT_PLUGIN_PATH（qt/5.15.19.1 的 runenv_info 已声明后两者）。
        self.run(f'{bash} "{test_sh}" "{bin_path}" "{log_dir}"', env="conanrun")
