#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Raft, raft, 0.18.1, Raft consensus algorithm library, Apache-2.0, https://github.com/canonical/raft
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class RaftConan(ConanFile):
    name = "raft"
    version = "0.18.1"
    description = "Raft consensus algorithm library"
    license = "LGPL-3.0"
    homepage = "https://github.com/canonical/raft"
    url = "https://github.com/canonical/raft"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libuv/1.52.1")
        self.requires("lz4/1.10.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # raft is a library (not a terminal tool), use dynamic linking
        # Add project-specific configure args here:
        # tc.configure_args.append("--without-bash-malloc")
        # ncurses: tc.configure_args.append("--without-shared")  # R4
        tc.generate()
        # Inject dependency include/lib paths so the unit-test targets
        # (test/unit/core) can compile and link against libuv/lz4.
        # The custom Makefile's TEST_CFLAGS/TEST_BIN rules consume
        # $(CPPFLAGS), $(LDFLAGS) and $(LIBS) from the environment;
        # LD_LIBRARY_PATH lets the runner load the shared libs at runtime.
        from conan.tools.env import Environment
        env = Environment()
        for dep in self.dependencies.values():
            cpp_info = dep.cpp_info
            for inc in cpp_info.includedirs:
                env.append("CPPFLAGS", "-I" + inc)
            for libdir in cpp_info.libdirs:
                env.append("LDFLAGS", "-L" + libdir)
                env.append_path("LD_LIBRARY_PATH", libdir)
            for lib in cpp_info.libs:
                env.append("LIBS", "-l" + lib)
        env.vars(self).save_script("conan_raft_test_env")

    def build(self):
        apply_conandata_patches(self)
        import os as _os
        # Build in source folder (custom Makefile, no VPATH support)
        build_dir = self.source_folder
        _cfg = _os.path.join(build_dir, "configure")
        if _os.path.exists(_cfg):
            _os.chmod(_cfg, 0o755)
        # Run configure and make in source folder
        # --disable-uv: OHOS lacks Linux AIO syscalls (io_setup etc.)
        self.run("cd {} && ./configure --prefix=/ --disable-uv".format(build_dir))
        self.run("cd {} && make -j1".format(build_dir))
        # Build and run the upstream munit unit tests (test/unit/core).
        # Requires lz4 + libuv from the dependency graph; TMPDIR must point to
        # a writable dir because OHOS /tmp is read-only (patched munit uses it).
        self.run("cd {} && make test".format(build_dir))
        self.run("cd {} && make check".format(build_dir))

    def package(self):
        copy(self, "libraft.so*", self.source_folder, os.path.join(self.package_folder, "lib"))
        copy(self, "libraft.a", self.source_folder, os.path.join(self.package_folder, "lib"))
        copy(self, "raft.h", os.path.join(self.source_folder, "include"), os.path.join(self.package_folder, "include"))
        if os.path.isdir(os.path.join(self.source_folder, "include", "raft")):
            copy(self, "*.h", os.path.join(self.source_folder, "include", "raft"), os.path.join(self.package_folder, "include", "raft"))

    def package_info(self):
        self.cpp_info.libs = ["raft"]
