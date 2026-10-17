import os
import shutil

from conan import ConanFile
from conan.errors import ConanException


class MdpTestConan(ConanFile):
    """test_package for the mdp executable — runs test.sh which invokes the binary.

    mdp 1.0.18 upstream has no test target (Makefile targets:
    all/clean/install/uninstall only; upstream CI does make + ./mdp -v).
    Consumer tests below drive the real binary with programmatic Markdown
    input: -d debug dump (parser stats, no terminal needed) and -v/--help.
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _resolve_bash():
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries, so the
        # test scripts must run under bash. Resolve per invocation:
        # CONFIG_SHELL → SHELL (basename must be bash and executable) →
        # shutil.which("bash"); fail closed when none is usable — never
        # fall back to a hardcoded absolute path.
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
            "no usable bash for mdp test_package: set CONFIG_SHELL, "
            "export SHELL to a bash, or add bash to PATH"
        )

    def test(self):
        bash = self._resolve_bash()
        self.run(f"{bash} test.sh", env="conanrun")
        # OHOS-specific binary-form and real-terminal checks; only make
        # sense when host == target (cross builds from a Linux dev box
        # would fail the readelf/musl/pty assertions by design).
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) == "armv8":
            try:
                self.run(f"{bash} test_ohos.sh", env="conanrun")
            except Exception as e:
                self.output.error(f"test_ohos.sh failed: {e}")
                raise
