#!/usr/bin/env python3
"""Conan test_package -- Dune 3.17.0

Verifies dune build tool functionality on OHOS:
1. Version check
2. Simple executable build
3. Executable execution
4. Multi-module build with library dependency
5. Clean + incremental rebuild
"""
import os

from conan import ConanFile


class DuneTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # dune build/exec 需要 ocaml 编译器来编译 OCaml 源码
        self.tool_requires("ocaml/4.14.1.1.2")

    def build(self):
        pass

    def test(self):
        bin_dir = os.path.join(self.dependencies["dune"].package_folder, "bin")
        dune = os.path.join(bin_dir, "dune")
        dune_cmd = f'"{dune}"' if os.path.isfile(dune) else "dune"

        # Test 1: Version check
        self.run(f"{dune_cmd} --version", env="conanbuild")

        # Create a temporary project for functional tests
        test_dir = os.path.join(self.build_folder, "_dune_test")
        os.makedirs(os.path.join(test_dir, "src"), exist_ok=True)

        with open(os.path.join(test_dir, "dune-project"), "w") as f:
            f.write("(lang dune 3.0)\n(name test_project)\n")

        with open(os.path.join(test_dir, "src", "dune"), "w") as f:
            f.write("(executable (name hello))\n")

        with open(os.path.join(test_dir, "src", "hello.ml"), "w") as f:
            f.write('let () = print_endline "Hello from Dune on OHOS!"\n')

        # Test 2: Build simple executable
        self.run(f"{dune_cmd} build", cwd=test_dir, env="conanbuild")

        # Test 3: Execute built program
        self.run(f"{dune_cmd} exec src/hello.exe", cwd=test_dir, env="conanbuild")

        # Test 4: Build with library dependency
        os.makedirs(os.path.join(test_dir, "lib"), exist_ok=True)
        with open(os.path.join(test_dir, "lib", "dune"), "w") as f:
            f.write("(library (name mylib) (modules mylib))\n")
        with open(os.path.join(test_dir, "lib", "mylib.ml"), "w") as f:
            f.write('let greet name = Printf.sprintf "Hello, %s!" name\n')
        with open(os.path.join(test_dir, "src", "dune"), "w") as f:
            f.write("(executable (name hello) (libraries mylib))\n")
        with open(os.path.join(test_dir, "src", "hello.ml"), "w") as f:
            f.write('let () = print_endline (Mylib.greet "OHOS")\n')
        self.run(f"{dune_cmd} build", cwd=test_dir, env="conanbuild")
        self.run(f"{dune_cmd} exec src/hello.exe", cwd=test_dir, env="conanbuild")

        # Test 5: Clean + rebuild
        self.run(f"{dune_cmd} clean", cwd=test_dir, env="conanbuild")
        self.run(f"{dune_cmd} build", cwd=test_dir, env="conanbuild")
