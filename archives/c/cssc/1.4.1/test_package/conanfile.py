#!/usr/bin/env python3
"""test_package — cssc 1.4.1 consumer test (L1).

CSSC is a command line tool suite (SCCS-compatible version control).
The test drives the packaged `sccs` front-end: version check, then an
`admin` + `get` round trip that creates an SCCS history file from the
bundled sample and checks it back out, verifying the content — so the
test actually exercises the binaries provided by the package.
"""
import os

from conan import ConanFile
from conan.tools.env import Environment


class CsscTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def generate(self):
        # `sccs` honours $PATH (execvp) when locating the SCCS
        # sub-tools (admin, get, ... live in libexec/cssc/); the tools
        # link libc++_shared.so from the toolchain sysroot, so prepend
        # that directory to LD_LIBRARY_PATH as well.  The env file is
        # sourced by self.run(env=...) below.
        pkg = self.dependencies[self.tested_reference_str]
        bin_dir = pkg.cpp_info.bindirs[0]
        libexec = os.path.join(os.path.dirname(bin_dir), "libexec", "cssc")
        env = Environment()
        env.prepend_path("PATH", libexec)
        env.prepend_path(
            "LD_LIBRARY_PATH",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos/c++",
        )
        env.define("USER", "conan")
        # save_script("cssc_test_env") writes cssc_test_env.sh
        env.vars(self, scope="conanrun").save_script("cssc_test_env")

    def build(self):
        pass

    def test(self):
        pkg = self.dependencies[self.tested_reference_str]
        bin_dir = pkg.cpp_info.bindirs[0]
        sccs = os.path.join(bin_dir, "sccs")
        workdir = os.path.join(self.build_folder, "scm")
        os.makedirs(workdir, exist_ok=True)
        # Copy the sample source into the scratch directory (remove
        # any leftovers from a previous run so the test is idempotent).
        sample_src = os.path.join(self.source_folder, "hello_fixture.sh")
        sample = os.path.join(workdir, "hello_fixture.sh")
        sfile = os.path.join(workdir, "s.hello_fixture.sh")
        for stale in (sample, sfile, os.path.join(workdir, "p.hello_fixture.sh")):
            if os.path.exists(stale):
                os.remove(stale)
        with open(sample_src) as src, open(sample, "w") as dst:
            dst.write(src.read())

        # The generated cssc_test_env.sh (PATH + LD_LIBRARY_PATH + USER)
        # is applied to each run below.  Its absolute location is the
        # test generators folder.
        env_file = os.path.join(self.generators_folder, "cssc_test_env.sh")
        env = [env_file]

        # 1) version check — the sccs front-end must run
        self.run(f'"{sccs}" --version', cwd=workdir, env=env, scope="run")

        # 2) create an SCCS history file from the sample...
        self.run(f'"{sccs}" admin -ihello_fixture.sh s.hello_fixture.sh',
                 cwd=workdir, env=env, scope="run")
        # ...and check it back out (round trip).  `get` refuses to
        # overwrite an existing writable g-file, so remove it first.
        os.remove(sample)
        self.run(f'"{sccs}" get -s s.hello_fixture.sh', cwd=workdir, env=env, scope="run")
        with open(sample) as f:
            content = f.read()
        expected = "hello cssc"
        assert expected in content, (
            f"unexpected content after 'sccs get': {content!r}"
        )
        self.output.success(f"cssc round-trip OK (content contains {expected!r})")
