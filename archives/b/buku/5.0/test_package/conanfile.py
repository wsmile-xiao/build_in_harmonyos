"""test_package for buku 5.0 — binary smoke test (R34)."""
from conan import ConanFile
from conan.errors import ConanException


class BukuTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Verify buku binary exists and is executable
        ret = self.run("which buku", env="conanrun")
        if ret != 0:
            raise ConanException(f"buku binary not found on PATH (exit code {ret})")
        # 直接 import buku 拿 __version__，绕开交互式 CLI 子进程（buku --version 在
        # OHOS CI 的非 tty 环境下会挂在 stdin 等待上，被 timeout 杀为 exit 124，
        # 这是 PR #2800 反复咬的根因）。import 不走子进程交互，必立即返回。
        ret = self.run(
            'python3 -c "import buku; print(buku.__version__)"',
            env="conanrun",
        )
        if ret != 0:
            raise ConanException(f"import buku failed with exit code {ret}")
