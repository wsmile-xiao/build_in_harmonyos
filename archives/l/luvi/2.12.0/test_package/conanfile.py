import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import copy


class LuviTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["luvi"].package_folder
        luvi = os.path.join(pkg, "bin", "luvi")
        if not os.path.isfile(luvi):
            raise ConanInvalidConfiguration(f"luvi binary missing: {luvi}")
        if not can_run(self):
            self.output.warning("Cross-built consumer cannot run on the build host.")
            return
        if str(self.settings.os) == "OHOS":
            self._sign_executable(luvi)
        script = os.path.join(os.path.dirname(__file__), "test.sh")
        self.run(f'sh "{script}" "{luvi}"', env="conanrun")

    def _sign_executable(self, executable):
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS consumer execution requires llvm-objcopy and binary-sign-tool")
        self._sign_elf_atomically(executable, objcopy, signer)

    def _sign_elf_atomically(self, path, objcopy, signer):
        original_mode = os.stat(path).st_mode
        temporary = f"{path}.signing"
        try:
            shutil.copy2(path, temporary)
            self.run(f'"{objcopy}" --remove-section .codesign "{temporary}"')
            self.run(f'"{signer}" sign -inFile "{temporary}" '
                     f'-outFile "{temporary}" -selfSign 1')
            os.chmod(temporary, original_mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _find_ohos_tool(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        ]
        return next((p for p in candidates if os.path.isfile(p)), "")
