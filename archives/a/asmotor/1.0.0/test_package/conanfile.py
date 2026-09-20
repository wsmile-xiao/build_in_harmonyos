from conan import ConanFile


class AsmotorTestConan(ConanFile):
    """test_package for asmotor — runs test.sh which invokes the installed
    assembler binaries (motorz80 etc.) on real assembly source."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        self.run("sh test.sh", env="conanrun")