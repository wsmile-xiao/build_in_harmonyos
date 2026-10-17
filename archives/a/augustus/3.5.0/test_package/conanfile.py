#!/usr/bin/env python3
"""Consumer test for augustus 3.5.0 (application).

minimal 构建（ZIPINPUT=false COMPGENEPRED=false）的 augustus 二进制本身
即完整基因预测程序：--version 抛 HelpException(GREETING) 正常 exit 0 输出
"AUGUSTUS (3.5.0) ..."；--species=human examples/example.fa 真实运行基因
预测并输出 "Predicted genes"（Homebrew 官方 test 同款断言）。具体断言逻辑
在 test.sh（CI L0c 门禁要求 test_package 下有测试源文件）。
"""
import os

from conan import ConanFile


class AugustusTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if self.settings.os not in ("Linux", "OHOS"):
            return
        pkg = self.dependencies["augustus"].package_folder
        exe = os.path.join(pkg, "bin", "augustus")
        config_dir = os.path.join(pkg, "config")
        example_fa = os.path.join(pkg, "examples", "example.fa")
        assert os.path.isfile(exe), f"augustus binary not found at {exe}"
        assert os.path.isdir(config_dir), f"augustus config dir not found at {config_dir}"
        assert os.path.isfile(example_fa), f"augustus example.fa not found at {example_fa}"
        # OHOS: /system/bin/sh (mksh) 不能直接执行 ELF，用 bash 包装；
        # AUGUSTUS_CONFIG_PATH 指向包内 config/（运行时数据必需）。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(
            f'{bash} "{os.path.join(self.source_folder, "test.sh")}" '
            f'"{exe}" "{config_dir}" "{example_fa}"',
            env="conanrun")
        # HMBS_UPSTREAM_TEST_RESULT — 上游测试审计证据（hmbs 硬门禁）。
        # 结论：augustus 3.5.0 上游 make test 依赖 Linux x86_64 + 完整 CGP
        # 构建（tests/short 的 execute_test.py --compare），minimal 配置
        # （ZIPINPUT=false COMPGENEPRED=false）与 OHOS aarch64 无法运行；
        # 详见 test_package/MANIFEST.yml upstream_test_audit。test.sh 已输出
        # 该标记，此处再冗余 print 一行（xeyes/xidle 同款双保险）。
        print('HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",'
              '"framework":"makefile",'
              '"command":"make test (n/a)",'
              '"discovered":0,"executed":0,"passed":0,"failed":0,'
              '"skipped":0,'
              '"reason":"augustus 3.5.0 上游 make test 依赖 Linux x86_64 + '
              '完整 CGP 构建，minimal 配置与 OHOS aarch64 无法运行；由 '
              'test_package 对打包二进制做真实功能断言"}')