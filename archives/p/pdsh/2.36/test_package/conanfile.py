from conan import ConanFile


class PdshTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # R34: Compile test source that verifies pdsh binary is runnable
        cc = str(self.settings.get_safe("compiler", "")) == "clang" and "clang" or "gcc"
        self.run(f"{cc} test_pdsh.c -o test_pdsh", env="conanbuild")

    def test(self):
        # R34: Run the test binary which calls pdsh -V
        self.run("./test_pdsh", env="conanrun")
