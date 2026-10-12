#!/usr/bin/env python3
"""test_package for xsct 2.3 —— CLI 工具消费者端到端用例（HarmonyOS PC）。

真实测试逻辑在 consumer_test.sh 中执行（非空壳、非 print-only），
入口通过 self.run() 真实运行测试脚本并校验退出码：

  A. HarmonyOS 专有非断言测试 —— 原生 ELF 与动态依赖闭包（静态）
     A1 xsct 必须是 OHOS aarch64 原生 ELF 可执行文件
     A2 xsct 的 DT_NEEDED 动态依赖闭包必须含 libX11.so.6 / libXrandr.so.2

  B. 端到端消费者用例（原生进程真实执行 + 上游语义校验）
     B1 无 DISPLAY 原生执行 xsct：动态加载器必须先完整解析并加载整个
        DT_NEEDED 闭包才能进入 main()，随后按上游源码语义优雅返回
        EXIT_FAILURE(1)——闭包在本机真实加载的直接证据
     B2 伪造不可达 DISPLAY 执行 xsct，仍优雅失败（非崩溃 / 非信号终止）

设计约束（CI 实证，PR #15143 build #80198）：加载验证不依赖 conan 宿主
python3 —— HNP 安装的 python3（如 /data/service/hnp/bin/python3）运行在
受限 linker namespace 中，dlopen 缓存目录下的共享库会得到
EACCES(Permission denied)，而 exec 时按 DT_NEEDED 加载不受此限；故不向
脚本传递 sys.executable，使结果不随「哪个 python3 运行 conan」而变化。

全部判定基于命令退出码（self.run / 脚本内 grep），不使用 Python assert。
"""
import os

from conan import ConanFile


class XsctTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindir = self.dependencies["xsct"].cpp_info.bindirs[0]
        script = os.path.join(self.recipe_folder, "consumer_test.sh")
        self.output.info(f"运行消费者端到端用例: sh {script} {bindir}")
        # 通过解释器调用，避免 HMDFS 上脚本文件的 execve 限制；
        # 不传 sys.executable —— 加载验证不依赖宿主 python（见 docstring 设计约束）
        self.run(f'sh "{script}" "{bindir}"', env="conanrun")
