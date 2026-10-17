import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class ClpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        suffix = ".exe" if str(self.settings.os) == "Windows" else ""
        bindir = self.cpp.build.bindirs[0]
        executable = os.path.join(bindir, "test_clp" + suffix)
        osiut = os.path.join(bindir, "osiUnitTest" + suffix)
        if not can_run(self):
            assert os.path.exists(executable), f"test binary not built: {executable}"
            assert os.path.exists(osiut), f"osiUnitTest not built: {osiut}"
            self.output.warning("Cross-built consumer cannot run on the build host.")
            return

        if str(self.settings.os) == "OHOS":
            self._sign_executable(executable)
            self._sign_executable(osiut)
        # 消费者冒烟测试（原有）
        self.run(f'"{executable}"', env="conanrun", cwd=self.build_folder)
        # 上游 osiUnitTest：真实运行上游测试套件（R34），MPS 数据随包附带
        mps_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "data", "Sample")
        self.run(
            f'"{osiut}" -verbosity=1 -mpsDir="{mps_dir}/"',
            env="conanrun", cwd=self.build_folder)

    def _sign_executable(self, executable):
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS consumer execution requires llvm-objcopy and binary-sign-tool"
            )
        self._sign_elf_atomically(executable, objcopy, signer)

    def _sign_elf_atomically(self, path, objcopy, signer):
        original_mode = os.stat(path).st_mode
        temporary = f"{path}.signing"
        try:
            shutil.copy2(path, temporary)
            self.run(f'"{objcopy}" --remove-section .codesign "{temporary}"')
            self.run(
                f'"{signer}" sign -inFile "{temporary}" '
                f'-outFile "{temporary}" -selfSign 1'
            )
            os.chmod(temporary, original_mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _find_ohos_tool(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        ]
        return next((path for path in candidates if os.path.isfile(path)), "")
