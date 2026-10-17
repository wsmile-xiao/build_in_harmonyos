"""Consumer tests for the packaged xva-img command-line application."""

import os
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class XvaImgTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test_xva_img.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _sign_program(self, path):
        if str(self.settings.os) != "OHOS":
            return

        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(signer):
            raise ConanException("OHOS test execution requires binary-sign-tool")
        if not os.path.isfile(objcopy):
            raise ConanException("OHOS test execution requires llvm-objcopy")

        # The SDK linker leaves a placeholder .codesign section. Remove it
        # before asking the HarmonyOS signer to insert the real signature.
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        signed = path + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", signed, "-selfSign", "1"],
            check=True,
        )
        os.replace(signed, path)
        os.chmod(
            path,
            stat.S_IMODE(os.stat(path).st_mode)
            | stat.S_IXUSR
            | stat.S_IXGRP
            | stat.S_IXOTH,
        )

    def test(self):
        if not can_run(self):
            self.output.info("Cross-building: target execution skipped")
            return

        package = self.dependencies["xva-img"].package_folder
        packaged_binary = os.path.join(package, "bin", "xva-img")
        if not os.path.isfile(packaged_binary):
            raise ConanException("The packaged xva-img binary was not found")

        binary = packaged_binary
        args = []
        runtime_dir = None
        if str(self.settings.os) == "OHOS":
            runtime_dir = tempfile.mkdtemp(prefix="xva-img-test-", dir=self.build_folder)
            binary = os.path.join(runtime_dir, "xva-img-test")
            shutil.copy2(packaged_binary, binary)
            self._sign_program(binary)
            args.append("--harmonyos")

        driver = os.path.join(self.source_folder, "test_xva_img.py")
        workdir = os.path.join(self.build_folder, "xva-img-test-data")
        command = 'python3 "{}" "{}" "{}" {}'.format(
            driver, binary, workdir, " ".join(args)
        ).strip()
        try:
            self.run(command, env="conanrun")
        finally:
            if runtime_dir:
                shutil.rmtree(runtime_dir, ignore_errors=True)
