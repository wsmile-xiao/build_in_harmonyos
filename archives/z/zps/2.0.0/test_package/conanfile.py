import os
import shutil

from conan import ConanFile
from conan.errors import ConanException


class ZpsTestConan(ConanFile):
    """test_package for zps/2.0.0 — drives the packaged CLI binary.

    zps 是可执行文件包（没有可链接的库接口），因此消费者测试直接执行
    打包后的 ``bin/zps``：
      - test.sh     —— CLI 契约 + 真僵尸进程「检测 → 回收」闭环
      - test_ohos.sh —— HarmonyOS 专项（ELF/musl、DT_NEEDED、RPATH、
        OHOS 签名段、/proc 语义、内核线程过滤、非终端颜色）
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _resolve_bash():
        # OHOS: /system/bin/sh（mksh）不能可靠执行 ELF 二进制，测试脚本必须
        # 用 bash 包裹。按 CONFIG_SHELL → SHELL（basename 必须是 bash 且可执行）
        # → PATH 中的 bash 依次解析；都不可用时 fail closed。
        cfg = os.environ.get("CONFIG_SHELL")
        if cfg:
            return cfg
        shell = os.environ.get("SHELL")
        if shell and os.path.basename(shell) == "bash" and os.access(shell, os.X_OK):
            return shell
        found = shutil.which("bash")
        if found:
            return found
        raise ConanException(
            "no usable bash for zps test_package: set CONFIG_SHELL, "
            "export SHELL to a bash, or add bash to PATH"
        )

    def test(self):
        bash = self._resolve_bash()
        self.run("{} test.sh".format(bash), env="conanrun")
        # HarmonyOS 专项检查只在「目标即当前主机」时有意义（os=OHOS），
        # 从 Linux 开发机交叉构建时按设计跳过。
        if str(self.settings.os) == "OHOS":
            self.run("{} test_ohos.sh".format(bash), env="conanrun")
