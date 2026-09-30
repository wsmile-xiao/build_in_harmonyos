import os
import platform
import shutil

from conan import ConanFile


class LambdaAlign2TestConan(ConanFile):
    """test_package for lambda-align2 — 消费者端到端用例。

    真实调用安装产物完成完整工作流（不是纯断言）：
      蛋白链路: lambda2 mkindexp 建 FM 索引 -> lambda2 searchp 检索 -> 校验命中
                （m8 命中表 / m9 带程序标签 / sam 记录 / m9.gz 压缩输出 / bam(BGZF) / sam.bz2）
      核苷酸链路: lambda2 mkindexn 建索引 -> lambda2 searchn 检索 -> 校验命中
    覆盖 zlib（gz/BGZF）、bzip2（bz2）两条依赖链路的真实读写。
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _run_prefix(self):
        """执行 aarch64 产物所需前缀（本地 qemu 验证用；设备/CI 本机为空）。

        既看签名工具是否存在，也看本机架构 —— 交叉构建主机上也装了同名工具。
        """
        if platform.machine() in ("aarch64", "arm64") and \
                os.path.isfile("/data/service/hnp/bin/binary-sign-tool"):
            return ""
        wrapper = os.environ.get("OHOS_QEMU_WRAPPER", "/root/ohpc/bin/ohos-qemu-aarch64")
        if os.path.isfile(wrapper):
            return wrapper
        qemu = os.environ.get("OHOS_QEMU") or shutil.which("qemu-aarch64-static")
        runroot = os.environ.get("OHOS_RUNROOT", "")
        if qemu and runroot:
            return "{} -L {}".format(qemu, runroot)
        return ""

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if not os.path.isfile(bash):
            bash = "bash"
        os.environ["LAMBDA2_RUN_PREFIX"] = self._run_prefix()
        self.run('{} test.sh'.format(bash), env="conanrun")
