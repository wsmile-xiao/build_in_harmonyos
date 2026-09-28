import os

from conan import ConanFile
from conan.tools.build import can_run


class KylinScannerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        tested = self.dependencies[self.tested_reference_str]
        qtbase = self.dependencies["qt5-qtbase"]
        bin_path = os.path.join(tested.package_folder, "bin", "kylin-scanner")
        assert os.path.isfile(bin_path), f"kylin-scanner binary not found at {bin_path}"

        # ── 测试 1：冒烟测试 ──
        # 验证二进制可加载全部依赖库并完成 Qt 初始化
        # OHOS 适配：HOME 指向可写目录（OHOS /tmp 只读）
        plugins = os.path.join(qtbase.package_folder, "plugins")
        prefix = f"QT_QPA_PLATFORM=offscreen HOME={os.path.expanduser('~')}/tmp"
        if os.path.isdir(plugins):
            prefix += f" QT_PLUGIN_PATH={plugins}"
        self.run(f"{prefix} {bin_path}", env="conanrun")

        # ── 测试 2：消费者用例（端到端运行验证）──
        # 启动应用并验证其在 offscreen 模式下稳定运行 10s 无崩溃
        # OHOS 适配：consumer_test.sh 通过 KYLIN_SCANNER_LOCK_FILE 环境变量
        # 将锁文件重定向到可写目录（OHOS /tmp 只读），使程序能进入事件循环
        consumer_script = os.path.join(self.source_folder, "consumer_test.sh")
        if os.path.isfile(consumer_script):
            self.run(f'{consumer_script} "{bin_path}" 10', env="conanrun")
