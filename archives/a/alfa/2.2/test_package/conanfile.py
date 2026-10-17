import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import copy


class AlfaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["alfa"].package_folder
        alfa_bin = os.path.join(pkg, "bin", "alfa")
        if not os.path.isfile(alfa_bin):
            raise ConanInvalidConfiguration(f"alfa binary missing: {alfa_bin}")
        if not can_run(self):
            self.output.warning("Cross-built consumer cannot run on the build host.")
            return
        if str(self.settings.os) == "OHOS":
            self._sign_executable(alfa_bin)
        # alfa 编译时 PREFIX 硬编码为 /storage/Users/currentUser/usr/local，
        # 运行时从 PREFIX/share/alfa 加载 linelists（不查当前目录）。
        # CI Worker 上该目录不存在，需在运行前创建并复制 linelists。
        import tempfile
        pkg_share = os.path.join(pkg, "share", "alfa")
        import glob as _glob
        prefix_share = "/storage/Users/currentUser/usr/local/share/alfa"
        os.makedirs(prefix_share, exist_ok=True)
        for cat in _glob.glob(os.path.join(pkg_share, "*.cat")):
            shutil.copy2(cat, os.path.join(prefix_share, os.path.basename(cat)))
        workdir = tempfile.mkdtemp(prefix="alfa-tp-")
        try:
            testdata = os.path.join(pkg_share, "testdata", "1d.ascii")
            if os.path.isfile(testdata):
                shutil.copy2(testdata, os.path.join(workdir, "1d.ascii"))
            script = os.path.join(os.path.dirname(__file__), "test.sh")
            self.run(f'sh "{script}" "{alfa_bin}" "{workdir}"', env="conanrun")
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

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
