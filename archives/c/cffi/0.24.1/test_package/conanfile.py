import os
from conan import ConanFile
from conan.tools.layout import basic_layout
from conan.tools.files import copy


class CffiTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # Separate source and build folders so copy() works
        basic_layout(self)

    def generate(self):
        # Copy test.c from test_package/ to build folder for compilation
        copy(self, "test.c", self.source_folder, self.build_folder)

    def build(self):
        # In Conan 2.x, find package folder via self.dependencies
        dep = self.dependencies["cffi"]
        pkg = dep.package_folder
        if not pkg:
            raise AssertionError("package_folder not found — package may not be installed correctly")

        # Verify key Lisp source files are installed (source-level package)
        expected_src = [
            "cffi.asd",
            "README.md",
            "src/package.lisp",
            "libffi/libffi.lisp",
        ]
        for f in expected_src:
            path = os.path.join(pkg, f)
            assert os.path.exists(path), f"Missing: {path}"

        # Verify compiled test shared libraries exist (built by main recipe's build())
        so_files = ["tests/libtest.so", "tests/libtest2.so", "tests/libfsbv.so"]
        for so in so_files:
            so_path = os.path.join(pkg, so)
            assert os.path.exists(so_path), f"Missing compiled test .so: {so_path}"

        # Compile test.c against the installed libtest.so and run it
        # test.c calls exported symbols from libtest.so (my_strdup, dll_version, etc.)
        test_exe = os.path.join(self.build_folder, "cffi_test")
        libtest_so = os.path.join(pkg, "tests", "libtest.so")
        self.run(
            f"clang -o {test_exe} {os.path.join(self.build_folder, 'test.c')} "
            f"-Wl,-rpath,{os.path.dirname(libtest_so)} {libtest_so}",
            env="conanbuild",
        )

    def test(self):
        # Run the compiled test executable — it must exit 0
        test_exe = os.path.join(self.build_folder, "cffi_test")
        assert os.path.exists(test_exe), f"test executable not built: {test_exe}"
        self.run(test_exe, env="conanrun")
