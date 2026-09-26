from conan import ConanFile


class LibqrtrTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "PkgConfigDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        self.run(
            "clang test_package.c -o test_package "
            "$(PKG_CONFIG_PATH=. pkg-config --cflags --libs qrtr-glib)",
            env="conanbuild",
        )

    def test(self):
        self.run("./test_package", env="conanrun")

