import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class TestPkg(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    exports_sources = "test.cpp"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["googletest"].cpp_info
        # 头闭包自检要用「所有依赖」的 include。
        incs = []
        for _ref, _d in self.dependencies.items():
            incs += ["-I" + p for p in _d.cpp_info.includedirs]
        inc = " ".join(incs)
        libs = " ".join(f"-L{ldir}" for ldir in dep.libdirs)
        cxx = os.environ.get("CXX", "clang++")
        # 静态链接 gtest/gmock（gtest_main 提供 main）；-lgmock -lgtest_main -lgtest 依次在后。
        self.run(f"{cxx} test.cpp -o test_probe {inc} {libs} "
                 f"-lgmock -lgtest_main -lgtest -lpthread -std=c++14")

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        probe = os.path.join(self.build_folder, "test_probe")
        if not os.path.isfile(probe):
            raise ConanException(f"consumer probe missing: {probe}")
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_elf(probe)
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} -c './test_probe'", env="conanrun")

    def _sign_ohos_elf(self, path):
        # cdecode/mbw 消费者同法：OHOS 运行 ELF 前须 binary-sign-tool 自签并校验 .codesign。
        signer = shutil.which("binary-sign-tool") or (
            "/data/service/hnp/bin/binary-sign-tool"
        )
        readelf = shutil.which("llvm-readelf") or (
            "/data/service/hnp/bin/llvm-readelf"
        )
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("required OHOS signing tools are missing")
        temporary = f"{path}.signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", temporary, "-selfSign", "1"],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", temporary],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"signed probe has invalid .codesign: {path}")
        os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(temporary, path)
