from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class UnadfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    # Tool-package: a pure CLI test needs no CMake and no build toolchain.
    # VirtualRunEnv alone puts the packaged bin/ on PATH and the packaged
    # lib/ on the link/load path.
    generators = "VirtualRunEnv"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Same shape as the main recipe: the profile keeps
        # tools.build:compiler_executables as a dict, so read it whole.
        ce = self.conf.get("tools.build:compiler_executables", default={},
                           check_type=dict) or {}
        cc = ce.get("c") or "clang"
        # Conan 2 exposes a dependency's package folder as an attribute of the
        # dependency object. `self.dependencies["x"].package_folder` is what
        # main's merged test_package recipes use (1893 of them); the
        # `self.deps_cpp_info["x"]` mapping was removed in conan 2.x, and
        # `.cpp_info.package_folder` is a _Component without the attribute.
        # Device runs Conan 2.29.1.
        pkg = self.dependencies["unadf"].package_folder
        # Link against the packaged libadf.a and the packaged headers.
        self.run(
            f"{cc} -std=gnu99 -I{pkg}/include "
            f"{self.source_folder}/test_unadf_lib.c "
            f"-L{pkg}/lib -ladf -o test_unadf_lib"
        )

    def test(self):
        if not can_run(self):
            return
        # VirtualRunEnv is already declared in `generators`, so conan has
        # written conanrun.sh for us. Instantiating it again and calling
        # generate() here is a hard error ("VirtualRunEnv is declared in the
        # generators attribute, but was instantiated in the generate()
        # method too") -- the tool must appear in exactly one of the two.
        #
        # test() runs with the CWD set to the test_package *build* folder, so
        # the script has to be addressed by absolute path. A bare
        # "bash test_unadf_cli.sh" fails with "No such file or directory"
        # even though the file is right there in source_folder.
        self.run(f"bash {self.source_folder}/test_unadf_cli.sh", env="conanrun")
