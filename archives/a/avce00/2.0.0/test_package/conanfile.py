import os
from conan import ConanFile
from conan.tools.build import can_run


class Avce00TestConan(ConanFile):
    """test_package for avce00 library — compiles and runs test.c."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            comp_execs = self.conf.get("tools.build:compiler_executables",
                                       default={}, check_type=dict)
            if isinstance(comp_execs, str):
                import json
                comp_execs = json.loads(comp_execs)
            cc = comp_execs.get("c") or "clang" if comp_execs else "clang"
            avce00 = self.dependencies["avce00"]
            inc = avce00.cpp_info.includedirs[0]
            lib = avce00.cpp_info.libdirs[0]
            # Ensure TMPDIR is set for the compiler
            tmpdir = os.environ.get("TMPDIR",
                                    os.path.join(os.path.expanduser("~"), "tmp-build"))
            os.environ["TMPDIR"] = tmpdir
            # Detect sysroot from compiler location
            cc_dir = os.path.dirname(cc)
            sysroot = os.path.normpath(os.path.join(cc_dir, "..", "sysroot"))
            sysroot_flag = f"--sysroot={sysroot}" if os.path.isdir(sysroot) else ""
            # Code-sign the binary (required for OHOS ELF execution)
            self.run(
                f'{cc} {sysroot_flag} -D__MUSL__ -fuse-ld=lld -Wl,--code-sign '
                f'-L{sysroot}/usr/lib/aarch64-linux-ohos '
                f'test.c -o test -I"{inc}" -L"{lib}" -lavce00 -lm',
                env="conanrun",
            )
            self.run("./test", env="conanrun")
