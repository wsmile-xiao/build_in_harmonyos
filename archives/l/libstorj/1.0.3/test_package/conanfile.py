#!/usr/bin/env python3
"""test_package for libstorj 1.0.3 (OHOS PC).

Consumer-level test (R34): compiles test_consumer.c against the installed
libstorj archive and its dependency graph, runs it on the OHOS device, and
smoke-tests the installed `storj` CLI.

Note on spawn discipline (2026-09-11 dinit-shutdown precedent): the consumer
locates the CLI by absolute path baked in at compile time — never a bare
command name (OHOS Python/posix_spawn would work here since we go through
/bin/sh, but the absolute path also makes the assertion independent of cwd).
"""
import os
import tempfile

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _dep_link_flags(self):
        """-I/-L/-l for the consumer: storj.h pulls dep headers
        (<json-c/json.h> etc.) and the static libstorj.a needs the dep
        archives at link time (static archives don't record DT_NEEDED)."""
        flags = []
        dep_names = ("libcurl", "nettle", "json-c", "libuv")
        for name in dep_names:
            dep = self.dependencies[name]
            for d in dep.cpp_info.includedirs:
                flags.append("-I%s" % d)
            for d in dep.cpp_info.libdirs:
                flags.append("-L%s" % d)
            for lib in dep.cpp_info.libs:
                flags.append("-l%s" % lib)
        return flags

    def build(self):
        ccs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        cc = ccs.get("c", "clang")

        dep = self.dependencies["libstorj"]
        inc = os.path.join(dep.package_folder, "include")
        libdir = os.path.join(dep.package_folder, "lib")
        cli = os.path.join(dep.package_folder, "bin", "storj")

        src = os.path.join(self.source_folder, "test_consumer.c")
        # keep the worktree clean: output to a scratch dir, not the
        # (in-tree) build folder
        out = os.path.join(tempfile.mkdtemp(prefix="tp-libstorj-"),
                           "test_consumer")
        # -DCLI_PATH=\"...\": the escapes must survive the /bin/sh -c layer
        # so clang receives a quoted string literal
        cmd = [cc, src, "-I%s" % inc, "-L%s" % libdir, "-lstorj",
               '-DCLI_PATH=\\"%s\\"' % cli]
        cmd += self._dep_link_flags()
        cmd += ["-lm", "-o", out]
        self.run(" ".join(cmd), env="conanbuild")
        self._consumer_bin = out

    def test(self):
        exe = getattr(self, "_consumer_bin", None) or os.path.join(
            self.build_folder, "test_consumer")
        self.run(exe, env="conanrun")
