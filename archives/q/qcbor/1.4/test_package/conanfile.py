import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class QcborTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _sign_ohos_elf(self, path):
        # E077: device enforces signatures on freshly built ELFs; CI does not.
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(signer) and os.path.isfile(readelf) and os.path.isfile(objcopy)):
            print("OHOS signing tools missing; running consumer unsigned")
            return
        sections = subprocess.run(
            [readelf, "-SW", path], capture_output=True, text=True, timeout=30
        ).stdout
        if ".codesign" in sections:
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", path], check=True, timeout=60
            )
        env = dict(os.environ)
        env.pop("LD_LIBRARY_PATH", None)
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", path + ".signed", "-selfSign", "1"],
            check=True, timeout=60, env=env,
        )
        os.replace(path + ".signed", path)
        os.chmod(path, 0o755)

    def test(self):
        exe = os.path.join(self.cpp.build.bindir, "consumer")
        self._sign_ohos_elf(exe)
        # The exec gate can swallow the first exec of a fresh binary; retry.
        ret = -1
        for attempt in range(3):
            ret = self.run(f'"{exe}"', env="conanrun", ignore_errors=True)
            if ret == 0:
                return
            print(f"consumer attempt {attempt + 1}: rc={ret}")
        raise ConanException(f"consumer test failed rc={ret}")
