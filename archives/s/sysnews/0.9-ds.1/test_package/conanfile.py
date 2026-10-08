#!/usr/bin/env python3
import os
import platform

from conan import ConanFile


class SysnewsTestConan(ConanFile):
    """Consumer test: compile a C checker, then run the packaged `news`
    binary against a generated news directory and feed its output to the checker."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        comp = self.conf.get("tools.build:compiler_executables", check_type=dict, default={})
        cc = comp.get("c", "clang") if comp else "clang"
        src = os.path.join(self.source_folder, "check_news.c")
        out = os.path.join(self.build_folder, "check_news")
        self.run(f"'{cc}' -Wall -O2 -o '{out}' '{src}'")

    def test(self):
        news = os.path.join(self.dependencies["sysnews"].package_folder, "bin", "news")
        assert os.path.isfile(news), f"news binary not found: {news}"

        # An x86 build host without the musl loader cannot execute the aarch64
        # OHOS binary at all (not a package defect): report an explicit skip.
        if (platform.machine().lower() not in ("aarch64", "arm64")
                and not os.path.exists("/lib/ld-musl-aarch64.so.1")):
            with open(news, "rb") as f:
                head = f.read(20)
            assert head[:4] == b"\x7fELF" and head[18:20] == b"\xb7\x00", "news is not an aarch64 ELF"
            self.output.warning("SKIPPED test.sh: host cannot execute aarch64 OHOS binaries "
                                "(no /lib/ld-musl-aarch64.so.1); only ELF/aarch64 header checked")
            return

        bash = os.environ.get("CONFIG_SHELL", "bash")
        script = os.path.join(self.source_folder, "test.sh")
        check = os.path.join(self.build_folder, "check_news")
        self.run(f"{bash} {script} {check}", env="conanrun")
