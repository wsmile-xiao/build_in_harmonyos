import os

from conan import ConanFile


class GnuPrologTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        self.run("gprolog --version", env="conanrun")
        test_file = os.path.join(self.build_folder, "test.pl")
        executable = os.path.join(self.build_folder, "test_program")
        with open(test_file, "w", encoding="utf-8") as handle:
            handle.write(
                ":- initialization(main).\n"
                "main :- 2 + 3 =:= 5, write('PASS'), nl, halt.\n"
            )
        self.run(
            f'gplc -o "{executable}" "{test_file}"',
            env="conanrun",
        )
        self.run(
            f'"{executable}"',
            env="conanrun",
        )
