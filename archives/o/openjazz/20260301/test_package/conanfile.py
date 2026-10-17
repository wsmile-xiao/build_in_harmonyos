#!/usr/bin/env python3
"""Conan test_package for openjazz 20260301 (application).

运行被测包的可执行文件，只走 argparse 的纯 IO 退出路径：
-v/--version 由 version_cb 打印版本后 exit(EXIT_SUCCESS)，
--help 由 OPT_HELP 打印 usage 后退出；两者都在 startUp()（SDL 视频/音频
初始化）之前 return，因此无头环境安全。由 test.sh 断言二进制存在性、
版本输出 "OpenJazz 20260301"、--help usage 输出（共 4 项断言）。

OHOS 上可执行文件必须先用 binary-sign-tool 签名，否则运行报
Operation not permitted。签名在临时副本上进行，不修改依赖包内容。
"""
import os
import shutil
import tempfile

from conan import ConanFile


class OpenJazzTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _sign_elf(self, path):
        """OHOS ELF 签名：先剥离可能存在的 .codesign 段，再用 binary-sign-tool 自签名。"""
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            print(f"[warn] binary-sign-tool not found at {signer}, skip ELF signing")
            return
        self.run(f'{objcopy} --remove-section .codesign "{path}" 2>/dev/null', ignore_errors=True)
        tmp = path + ".signed"
        self.run(f'{signer} sign -inFile "{path}" -outFile "{tmp}" -selfSign 1')
        if os.path.exists(tmp):
            shutil.move(tmp, path)
        os.chmod(path, 0o755)

    def test(self):
        dep = self.dependencies["openjazz"]
        src = os.path.join(dep.package_folder, "bin", "OpenJazz")
        assert os.path.isfile(src), f"OpenJazz binary not found: {src}"
        # 复制到临时目录再签名，不修改依赖包内容（包不变原则）
        tmpdir = tempfile.mkdtemp(prefix="openjazz-test-")
        exe = os.path.join(tmpdir, "OpenJazz")
        shutil.copy2(src, exe)
        os.chmod(exe, 0o755)
        # OHOS ELF 必须先签名才能执行
        self._sign_elf(exe)
        # R34/PF3/L0d：self.run 真实执行测试脚本（脚本内断言 -v 输出与退出码）
        test_script = os.path.join(self.recipe_folder, "test.sh")
        self.run(f'/data/service/hnp/bin/bash "{test_script}" "{exe}"')
        shutil.rmtree(tmpdir, ignore_errors=True)
