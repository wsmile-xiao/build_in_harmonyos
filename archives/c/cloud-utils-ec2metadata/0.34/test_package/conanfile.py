#!/usr/bin/env python3
"""Conan test_package for cloud-utils-ec2metadata.

Consumer-view verification (R34): executes the *installed* ec2metadata
binary against a local mock IMDS (via http_proxy) and validates the
OHOS adaptation (env shebang resolution + real IMDSv2 metadata flow).
"""
import os

from conan import ConanFile


class CloudutilsEc2MetadataTestConan(ConanFile):
    settings = ("os", "arch")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        script = os.path.join(os.path.dirname(__file__), "test_ohos_ec2metadata.py")
        # 显式把依赖包 bin/ 的绝对路径传给测试脚本（EC2METADATA_BIN /
        # WRITE_MIME_MULTIPART_BIN），确保消费安装包内可执行文件而非
        # 依赖 PATH 解析（CI #42673：conanrun PATH 未注入包 bin 时报
        # [Errno 2] No such file or directory）
        dep = self.dependencies["cloud-utils-ec2metadata"]
        bindir = os.path.join(dep.package_folder, "bin")
        self.run(
            f"EC2METADATA_BIN={bindir}/ec2metadata "
            f"WRITE_MIME_MULTIPART_BIN={bindir}/write-mime-multipart "
            f"python3 {script}",
            env="conanrun")
