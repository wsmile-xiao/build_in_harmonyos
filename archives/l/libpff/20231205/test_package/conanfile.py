#!/usr/bin/env python3
"""Consumer test for libpff 20231205."""
import os

from conan import ConanFile


class LibpffTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _compiler(self):
        """Return the C compiler the active profile pins (R33).

        The profile declares ``tools.build:compiler_executables``; reading it
        here keeps the consumer build on the same toolchain as the package
        build instead of silently falling back to whatever ``clang`` happens to
        be on PATH.  The PATH name is only a last resort for profiles that
        carry no pin at all (never an undefined shell variable).
        """
        compiler_executables = {}
        try:
            compiler_executables = self.conf.get(
                "tools.build:compiler_executables", default={}
            ) or {}
        except Exception:
            compiler_executables = {}
        if isinstance(compiler_executables, dict):
            return compiler_executables.get("c") or "clang"
        return "clang"

    def build(self):
        dependency = self.dependencies["libpff"]
        cpp_info = dependency.cpp_info
        include_flags = " ".join(f"-I{path}" for path in cpp_info.includedirs)
        library_flags = " ".join(f"-L{path}" for path in cpp_info.libdirs)
        link_flags = " ".join(f"-l{name}" for name in cpp_info.libs)
        compiler = self._compiler()
        self.run(
            f"{compiler} test_libpff.c -o test_libpff "
            f"{include_flags} {library_flags} {link_flags}"
        )
        if str(self.settings.os) == "OHOS":
            self.run(
                f"{compiler} test_ohos.c -o test_ohos "
                f"{include_flags} {library_flags} {link_flags}"
            )

    def test(self):
        if str(self.settings.os) == "OHOS":
            # The OHOS device has no /bin/bash; the profile pins the device
            # bash via [buildenv] CONFIG_SHELL, the absolute path is the
            # fallback for environments that do not carry it.
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        else:
            bash = os.environ.get("CONFIG_SHELL", "bash")
        dependency = self.dependencies["libpff"]
        library_dirs = ":".join(str(path) for path in dependency.cpp_info.libdirs)
        self.run(
            f"{bash} -c 'export LD_LIBRARY_PATH={library_dirs}:$LD_LIBRARY_PATH; "
            "./test_libpff'",
            env="conanrun",
        )
        if str(self.settings.os) == "OHOS":
            self.run(
                f"{bash} -c 'export LD_LIBRARY_PATH={library_dirs}:$LD_LIBRARY_PATH; "
                "./test_ohos'",
                env="conanrun",
            )
