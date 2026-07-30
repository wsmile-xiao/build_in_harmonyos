#!/usr/bin/env python3
"""Conan recipe for nextvi 7."""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get, mkdir, rmdir
from conan.tools.layout import basic_layout


class NextviConan(ConanFile):
    name = "nextvi"
    version = "7.0"
    description = "Small vi/ex terminal text editor"
    license = "ISC"
    homepage = "https://github.com/kyx0r/nextvi"
    url = "https://github.com/kyx0r/nextvi"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self, src_folder=".")

    def validate(self):
        if str(self.settings.os) == "Windows":
            raise ConanInvalidConfiguration("nextvi requires POSIX terminal APIs such as poll/termios")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c")
        if not cc:
            raise ConanInvalidConfiguration(
                "nextvi requires tools.build:compiler_executables.c for cross compilation"
            )
        profile_cflags = self.conf.get("tools.build:cflags", default=[], check_type=list) or []
        profile_ldflags = self.conf.get("tools.build:exelinkflags", default=[], check_type=list) or []
        cflags = [
            "-D_POSIX_C_SOURCE=200809L",
            "-D_DEFAULT_SOURCE",
            "-pedantic",
            "-Wall",
            "-Wextra",
            "-Wno-implicit-fallthrough",
            "-Wno-missing-field-initializers",
            "-Wno-unused-parameter",
        ]
        if str(self.settings.build_type) == "Release":
            cflags.extend(["-O2", "-DNDEBUG"])
        cmd = [cc] + profile_cflags + cflags + ["-o", "vi", "vi.c"] + profile_ldflags
        self.run(" ".join(shlex.quote(arg) for arg in cmd), cwd=self.source_folder)
        self._run_upstream_tests(os.path.join(self.source_folder, "vi"))

    def _run_upstream_tests(self, vi_path):
        test_src = os.path.join(self.source_folder, "test.sh")
        if not os.path.isfile(test_src):
            self.output.info("upstream test.sh not found; skipping upstream tests")
            return

        test_dir = os.path.join(self.build_folder, "upstream-tests")
        tmp_dir = os.path.join(test_dir, "tmp")
        rmdir(self, test_dir)
        mkdir(self, test_dir)
        mkdir(self, tmp_dir)

        with open(test_src, "r", encoding="utf-8") as handle:
            script = handle.read()
        tmp_dir_shell = tmp_dir.replace("\\", "/")
        script = script.replace("/tmp/nextvi_test_", tmp_dir_shell + "/nextvi_test_")
        script = script.replace("/tmp/nextvi_out_", tmp_dir_shell + "/nextvi_out_")
        script = script.replace("VI=./vi", "VI=" + shlex.quote(vi_path.replace("\\", "/")))

        test_dst = os.path.join(test_dir, "test.sh")
        with open(test_dst, "w", encoding="utf-8") as handle:
            handle.write(script)
        self.run("/bin/sh " + shlex.quote(test_dst), cwd=test_dir)

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "vi.exe", src=self.source_folder, dst=bin_dir, keep_path=False)
        copy(self, "vi", src=self.source_folder, dst=bin_dir, keep_path=False)
        copy(self, "vi.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
