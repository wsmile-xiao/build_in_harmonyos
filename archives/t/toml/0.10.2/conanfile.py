from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout
import os


class TomlConan(ConanFile):
    name = "toml"
    version = "0.10.2"
    package_type = "library"
    license = "MIT"
    author = "William Pearson"
    url = "https://github.com/uiri/toml"
    homepage = "https://github.com/uiri/toml"
    description = "Python Library for Tom's Obvious, Minimal Language"
    topics = ("toml", "python", "parser")
    settings = "os", "compiler", "build_type", "arch"
    # Pure Python package: never shared in the C/C++ sense, but Conan
    # requires a `shared` option for `package_type = "library"`.
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # Pure Python package: install via pip into a flat target directory.
        # --no-deps: toml has no runtime dependencies; avoids touching PyPI.
        install_target = os.path.join(self.build_folder, "install")
        self.run(
            f'python3 -m pip install --no-deps --target="{install_target}" "{self.source_folder}"'
        )

    def package(self):
        # Ship the installed Python module.
        install_target = os.path.join(self.build_folder, "install")
        copy(self, "*", dst=self.package_folder, src=install_target)
        # Ship the upstream pytest suite alongside the package so that
        # test_package can run the real upstream tests against the installed
        # toml module (R34: tests must exercise the real API).
        copy(self, "*",
             dst=os.path.join(self.package_folder, "upstream_tests"),
             src=os.path.join(self.source_folder, "tests"))
        # test_api.py::test_paths / test_warnings load "test.toml" from the
        # current working directory; ship it next to the suite and chdir
        # there before running pytest.
        copy(self, "test.toml",
             dst=os.path.join(self.package_folder, "upstream_tests"),
             src=self.source_folder)

    def package_info(self):
        # Pure Python: no C/C++ artifacts.
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

        # Expose the module directory on PYTHONPATH for consumers.
        self.runenv_info.prepend_path("PYTHONPATH", self.package_folder)
