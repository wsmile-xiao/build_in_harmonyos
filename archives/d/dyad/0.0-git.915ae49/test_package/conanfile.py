import os
from conan import ConanFile
from conan.tools.build import can_run


class DyadTestConan(ConanFile):
    """test_package for dyad — TCP socket loopback on 127.0.0.1.

    Compiles test_dyad.c against the installed libdyad.a + dyad.h and runs
    it. dyad is a select()-based event-loop TCP library; the whole consumer
    path (listen/connect/accept/write/read/line event/counters/shutdown)
    is exercised over the loopback interface, which is available inside
    the OHOS sandbox (no external network access required).
    """
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
            dyad = self.dependencies["dyad"]
            inc = dyad.cpp_info.includedirs[0]
            lib = dyad.cpp_info.libdirs[0]
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
                f'{cc} {sysroot_flag} -fuse-ld=lld -Wl,--code-sign '
                f'-L{sysroot}/usr/lib/aarch64-linux-ohos '
                f'test_dyad.c -o test_dyad -I"{inc}" -L"{lib}" -ldyad',
                env="conanrun",
            )
            self.run("./test_dyad", env="conanrun")
