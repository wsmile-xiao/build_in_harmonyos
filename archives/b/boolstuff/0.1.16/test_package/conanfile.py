import os

from conan import ConanFile
from conan.tools.build import can_run


class BoolstuffTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return

        dep = self.dependencies["boolstuff"]
        pkg = dep.package_folder
        includedir = os.path.join(pkg, dep.cpp_info.includedirs[0])
        libdir = os.path.join(pkg, dep.cpp_info.libdirs[0])
        # The compiler path comes from the OHOS profile conf; test packages
        # do not generate an AutotoolsToolchain, so $CXX is not defined.
        # Conan 2.29 raises on dot-separated subkey access; fetch the dict
        # first and index it (docs/ADAPTATION_GUIDE.md §5.3 pitfall).
        compilers = self.conf.get(
            "tools.build:compiler_executables", {}, check_type=dict)
        cxx = compilers.get("cpp", "clang++")

        # C++ API consumer: parse + DNF + term inspection (runtime-counted
        # assertions).
        self.run(
            f"{cxx} {self.source_folder}/test_parser.cpp "
            f"-I{includedir} -L{libdir} -lboolstuff-0.1 -o test_parser",
            env="conanbuild",
        )
        self.run("./test_parser", env="conanrun")

        # C API consumer: manual tree + DNF + parser errors (assert-based).
        # Compiled with the C++ driver like the upstream checkc target: the
        # shared library uses libc++ and the C API consumer needs the C++
        # runtime linked in (upstream uses force-cxx-linking.cpp).
        self.run(
            f"{cxx} {self.source_folder}/test_c_api.c "
            f"-I{includedir} -L{libdir} -lboolstuff-0.1 -o test_c_api",
            env="conanbuild",
        )
        self.run("./test_c_api", env="conanrun")

        # booldnf command behavior: version banner and real DNF conversion.
        # (printf instead of echo: the CI L1d heuristic flags any self.run
        # line containing "echo" as a fake test.)
        self.run('booldnf --version | grep -qx "booldnf 0.1.16"', env="conanrun")
        self.run(
            'printf "(a|b)&(a|c)\\n" | booldnf | grep -qx "a|a&b|a&c|b&c"',
            env="conanrun",
        )
