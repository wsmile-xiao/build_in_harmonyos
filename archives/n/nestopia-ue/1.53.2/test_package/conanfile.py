import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class NestopiaUeTestConan(ConanFile):
    """test_package for nestopia-ue 1.53.2 (headless emulator).

    Runs test_package/test.sh against the packaged `nestopia` binary:
      1. ELF sanity checks (magic / 64-bit / AArch64)
      2. `nestopia --version` smoke test
      3. `nestopia --frames 120 <rom>` real emulation test: the core
         (CPU/PPU/APU) executes 120 frames headless on a generated
         minimal NROM ROM

    The binary links libc++_shared.so (OHOS toolchain soname); on the
    OHOS build host it resolves via LD_LIBRARY_PATH=/system/lib64.
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: skipping run test")
            return

        pkg = self.dependencies["nestopia-ue"].package_folder
        binary = os.path.join(pkg, "bin", "nestopia")
        datadir = os.path.join(pkg, "share", "nestopia")

        assert os.path.isfile(binary), f"nestopia binary missing: {binary}"
        assert os.path.isfile(os.path.join(datadir, "NstDatabase.xml")), \
            "NstDatabase.xml missing from share/nestopia"

        # work dir for the generated ROM (writable, outside the package)
        work = os.path.join(self.build_folder, "test_work")
        os.makedirs(work, exist_ok=True)

        # FR5: use SHELL env or PATH lookup instead of hardcoded paths
        bash = (os.environ.get("CONFIG_SHELL")
                or os.environ.get("SHELL")
                or shutil.which("bash")
                or "bash")

        # libc++_shared.so resolves via /system/lib64 on the OHOS host
        libs = "/system/lib64"
        if "LD_LIBRARY_PATH" in os.environ:
            libs = libs + ":" + os.environ["LD_LIBRARY_PATH"]

        script = os.path.join(self.source_folder, "test.sh")
        self.run(
            f'export LD_LIBRARY_PATH="{libs}"; "{bash}" "{script}" '
            f'"{binary}" "{datadir}" "{work}"',
            env="conanrun")
        self.output.info("nestopia-ue headless emulation test PASSED")
