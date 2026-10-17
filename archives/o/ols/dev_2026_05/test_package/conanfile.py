import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException


class OlsTestConan(ConanFile):
    """test_package for ols — 调用 run_tests.sh，以无头 LSP 会话（stdin/stdout 管道、
    Content-Length 分帧 JSON-RPC）驱动包内 bin/ols，断言 initialize 能力协商、
    documentSymbol 符号索引与 shutdown/exit 优雅退出，共 6 项检查。"""
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["ols"].package_folder
        ols = os.path.join(pkg, "bin", "ols")
        script = os.path.join(self.source_folder, "run_tests.sh")

        # run_tests.sh 需要 bash（数组 + PIPESTATUS）
        candidates = [
            os.environ.get("CONFIG_SHELL", ""),
            "/data/service/hnp/bin/bash",
            "/bin/bash",
            shutil.which("bash") or "",
        ]
        bash = next((c for c in candidates if c and os.path.exists(c)), None)
        if bash is None:
            raise ConanException("bash not found; run_tests.sh requires bash")

        work = os.path.join(self.build_folder, "ols_lsp_test")
        q = shlex.quote
        cmd = " ".join([q(bash), q(script), q(ols), q(pkg), q(work)])
        self.run(cmd)
