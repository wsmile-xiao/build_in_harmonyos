from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
import os


class TestPackageConan(ConanFile):
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

    def test(self):
        # The test_package binary is a tiny C consumer that links
        # Yder::Yder-static (and thus orcania) and exercises the public
        # logging API. The binary's return code is the canonical PASS/FAIL
        # signal.
        bin_path = os.path.join(self.build_folder, "test_yder")
        if not os.path.exists(bin_path):
            # CmakeLayout puts binaries under build/<config>/; fall back.
            bin_path = os.path.join(self.build_folder, "test_package")
        # Writable TMPDIR: the file-mode check writes its log there
        # (OHOS /tmp is read-only). os.environ is inherited by the
        # subprocess spawned from self.run().
        test_tmp = os.path.join(self.build_folder, ".test-tmp")
        os.makedirs(test_tmp, exist_ok=True)
        saved = {k: os.environ.get(k) for k in ("TMPDIR", "TMP", "TEMP")}
        os.environ["TMPDIR"] = test_tmp
        os.environ["TMP"] = test_tmp
        os.environ["TEMP"] = test_tmp
        try:
            self.run(f'"{bin_path}"', cwd=self.build_folder)
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
