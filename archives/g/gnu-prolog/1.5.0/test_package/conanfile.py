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
        with open(test_file, "w", encoding="utf-8") as handle:
            handle.write("main :- 2 + 3 =:= 5, write('PASS'), nl, halt.\n")
        self.run(
            f'gprolog --quiet --consult-file "{test_file}" --query-goal main',
            env="conanrun",
        )
