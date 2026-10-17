#!/usr/bin/env python3
"""Consumer test for libolecf 20240427 (upstream 20240427)."""
import os

from conan import ConanFile


class LibolecfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dependency = self.dependencies["libolecf"]
        cpp_info = dependency.cpp_info
        include_flags = " ".join(f"-I{path}" for path in cpp_info.includedirs)
        library_flags = " ".join(f"-L{path}" for path in cpp_info.libdirs)
        link_flags = " ".join(f"-l{lib}" for lib in cpp_info.libs)
        compiler = os.environ.get("CC", "clang")
        self.run(
            f"{compiler} test_libolecf.c -o test_libolecf "
            f"{include_flags} {library_flags} {link_flags}"
        )
        if str(self.settings.os) == "OHOS":
            self.run(
                f"{compiler} test_ohos.c -o test_ohos "
                f"{include_flags} {library_flags} {link_flags}"
            )

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        dependency = self.dependencies["libolecf"]
        library_dirs = ":".join(str(path) for path in dependency.cpp_info.libdirs)
        self.run(
            f"{bash} -c 'export LD_LIBRARY_PATH={library_dirs}:$LD_LIBRARY_PATH; "
            "./test_libolecf'",
            env="conanrun",
        )
        if str(self.settings.os) == "OHOS":
            self.run(
                f"{bash} -c 'export LD_LIBRARY_PATH={library_dirs}:$LD_LIBRARY_PATH; "
                "./test_ohos'",
                env="conanrun",
            )
