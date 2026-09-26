#!/usr/bin/env python3
"""Conan test_package — coinor-cbc 2.10.13（真跑打包产物 bin/cbc 的消费者测试）。

断言（R34：真跑被测产物，非空壳）：
1. 版本自报一致性：cbc 输出横幅含 "Version: 2.10.13"（与配方版本一致）。
2. 真实求解：内置整数模型（max 3x+2y, s.t. x+y<=4.5, x、y 经 General 段声明为整数、
   x<=3, y<=3；LP 格式变量默认连续，不声明会被当纯 LP 求解。LP 松弛最优 12，必须
   分支；MIP 最优 11 @ x=3,y=1）必须报告
   "Result - Optimal solution found" 且 "Objective value: 11..."。
3. OHOS 上运行前对 ELF 自签（binary-sign-tool），否则加载器 EPERM。
"""
import os
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class CoinorCbcTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "test_cbc.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _sign_ohos_elf(self, path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not (os.path.isfile(signer) and os.path.isfile(readelf)):
            raise ConanException("required OHOS signing tools are missing")
        output = path + ".signed"
        if os.path.lexists(output):
            os.unlink(output)
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", output, "-selfSign", "1"],
            check=True, timeout=120,
        )
        sections = subprocess.run(
            [readelf, "-SW", output], check=True, capture_output=True, text=True, timeout=60,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"Signed ELF has invalid .codesign count: {path}")
        os.chmod(output, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(output, path)

    def test(self):
        if cross_building(self):
            self.output.warning("cross-building: cannot run packaged cbc here")
            return
        pkg = self.dependencies["coinor-cbc"].package_folder
        cbc = os.path.join(pkg, "bin", "cbc")
        if not os.path.isfile(cbc):
            raise ConanException(f"packaged cbc binary not found: {cbc}")
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_elf(cbc)
        script = os.path.join(self.source_folder, "test_cbc.sh")
        os.chmod(script, (os.stat(script).st_mode & 0o777) | 0o755)
        # 工作目录用仓库外临时目录：脚本会写 model.lp，落 CWD 会污染 checkout
        # （test_package 的 source folder 即仓库内目录，残留未跟踪文件会触发
        # CI/门禁的 junk 误报）；用完即删。
        work = tempfile.mkdtemp(prefix="cbc-tp-")
        try:
            # conanrun 环境（PATH 等）
            self.run(f'"{script}" "{cbc}" "{work}"', env="conanrun")
        finally:
            shutil.rmtree(work, ignore_errors=True)
