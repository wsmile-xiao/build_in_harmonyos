"""Conan test_package - tack 1.11-20251210

R34：tack 是纯命令行工具（无库产物），所以这里**真实执行打包产物**，
由退出码/输出决定成败；`self.run` 不套 try，非零退出码直接让 conan create 失败。

载体 = 同目录的 test.sh（21 个检查点），入参：
    $1 被测二进制   $2 包根目录   $3 该二进制是否已自签（1/0）

为什么要"先自签再测"：本仓 CI 从不给产物签名（sign_elf 只挂在本地 package_builder），
而 OHOS 加载器会拒载没有 .codesign 段的 ELF —— 直接 exec 安装件会在 CI 上恒红。
所以这里把包内 ELF **复制到归档树之外的临时目录**、去掉旧签名、用
`binary-sign-tool -selfSign 1` 重新自签，再对**同一枚产物**跑断言；临时目录在
finally 里删除，归档树内绝不留 staged ELF / build-release / conanenv*.sh。
（同先例：archives/a/alfa/2.2、archives/b/bandwidthd/2.0.1-cvs20090917 的 test_package。）

conanrun 提供 ncurses/6.6 传导来的 TERMINFO/TERMINFO_DIRS：检查点 E1/E2 正是用
"未知终端名 -> setupterm 报 '... listed as generic'" 证明 terminfo 库经 conan
运行期环境真的可达（TERMINFO 没注入时会改报 'database could not be found'）。
"""

import os
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException

_HNP_BIN = "/data/service/hnp/bin"


class TackTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package_folder = self.dependencies["tack"].package_folder
        installed = os.path.join(package_folder, "bin", "tack")
        if not os.path.isfile(installed):
            raise ConanException(f"packaged tack binary missing: {installed}")

        signed = False
        stage = None
        target = installed
        if str(self.settings.os) == "OHOS":
            # CI worker 可能没有 ~/tmp（tempfile 不建中间目录），先确保父目录在
            basedir = os.path.join(os.path.expanduser("~"), "tmp")
            os.makedirs(basedir, exist_ok=True)
            stage = tempfile.mkdtemp(prefix="tack-consumer-", dir=basedir)
            target = self._self_sign(installed, stage)
            signed = True

        script = os.path.join(self.recipe_folder, "test.sh")
        try:
            self.run(f'sh "{script}" "{target}" "{package_folder}" '
                     f'{"1" if signed else "0"}', env="conanrun")
        finally:
            if stage:
                shutil.rmtree(stage, ignore_errors=True)

    def _tool(self, name):
        conf = self.conf.get("tools.build:compiler_executables",
                             default={}, check_type=dict) or {}
        compiler_dir = os.path.dirname(conf.get("cpp", "") or conf.get("c", ""))
        for candidate in (os.path.join(compiler_dir, name) if compiler_dir else "",
                          os.path.join(_HNP_BIN, name),
                          shutil.which(name) or ""):
            if candidate and os.path.isfile(candidate):
                return candidate
        raise ConanException(
            f"OHOS consumer test needs {name} (looked in the toolchain dir and {_HNP_BIN})")

    def _self_sign(self, installed, stage):
        """去旧签 + 自签，落到归档树外的临时目录；失败一律抛错，不静默降级。"""
        objcopy = self._tool("llvm-objcopy")
        signer = self._tool("binary-sign-tool")
        staged = os.path.join(stage, "tack")
        shutil.copy2(installed, staged)
        mode = os.stat(staged).st_mode
        subprocess.run([objcopy, "--remove-section", ".codesign", staged], check=True)
        out = os.path.join(stage, "tack.signed")
        subprocess.run([signer, "sign", "-inFile", staged, "-outFile", out,
                        "-selfSign", "1"], check=True)
        os.replace(out, staged)
        os.chmod(staged, mode | 0o111)
        self.output.info(f"SELF_SIGNED stage={stage} (outside the archive tree)")
        return staged
