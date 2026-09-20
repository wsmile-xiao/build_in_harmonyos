#!/usr/bin/env python3
"""Consumer test for libfwnt 20240415 (upstream 20240415)."""
import os

from conan import ConanFile


class LibfwntTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dependency = self.dependencies["libfwnt"]
        cpp_info = dependency.cpp_info
        include_flags = " ".join(f"-I{path}" for path in cpp_info.includedirs)
        library_flags = " ".join(f"-L{path}" for path in cpp_info.libdirs)
        link_flags = " ".join(f"-l{lib}" for lib in cpp_info.libs)
        compiler = os.environ.get("CC", "clang")
        self.run(
            f"{compiler} test_libfwnt.c -o test_libfwnt "
            f"{include_flags} {library_flags} {link_flags}"
        )
        if str(self.settings.os) == "OHOS":
            self.run(
                f"{compiler} test_ohos.c -o test_ohos "
                f"{include_flags} {library_flags} {link_flags}"
            )

    def test(self):
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        dependency = self.dependencies["libfwnt"]
        library_dirs = ":".join(str(path) for path in dependency.cpp_info.libdirs)
        self.run(
            f"{bash} -c 'export LD_LIBRARY_PATH={library_dirs}:$LD_LIBRARY_PATH; "
            "./test_libfwnt'",
            env="conanrun",
        )
        if str(self.settings.os) == "OHOS":
            self.run(
                f"{bash} -c 'export LD_LIBRARY_PATH={library_dirs}:$LD_LIBRARY_PATH; "
                "./test_ohos'",
                env="conanrun",
            )
