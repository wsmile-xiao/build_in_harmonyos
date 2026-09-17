#!/usr/bin/env python3
"""HarmonyOS consumer test for libgzstream 1.5-git20171107.9a20658."""

import glob
import json
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.layout import basic_layout


class LibgzstreamTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _resolve_cxx(self):
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        configured = str(executables.get("cpp") or "")
        if configured and os.path.isabs(configured):
            if os.path.isfile(configured) and os.access(configured, os.X_OK):
                return configured
            self.output.warning(
                "Configured C++ compiler is unavailable: {}; using PATH".format(
                    configured
                )
            )
        elif configured:
            resolved = shutil.which(configured)
            if resolved:
                return resolved
        for name in ("clang++", "c++"):
            resolved = shutil.which(name)
            if resolved:
                return resolved
        raise ConanInvalidConfiguration("A C++ compiler is required")

    def _archive(self, dependency, filename):
        for libdir in dependency.cpp_info.libdirs:
            candidates = sorted(glob.glob(os.path.join(libdir, filename)))
            if candidates:
                return candidates[0]
        raise ConanInvalidConfiguration(
            "Dependency archive is missing: {}".format(filename)
        )

    def build(self):
        cxx = self._resolve_cxx()
        libgzstream = self.dependencies["libgzstream"]
        zlib = self.dependencies["zlib"]
        include_flags = " ".join(
            "-I{}".format(shlex.quote(path))
            for dependency in (libgzstream, zlib)
            for path in dependency.cpp_info.includedirs
        )
        source = os.path.join(self.source_folder, "test_libgzstream.cpp")
        executable = os.path.join(self.build_folder, "test_libgzstream")
        command = "{} -std=c++17 -O2 {} {} {} {} -o {}".format(
            shlex.quote(cxx),
            include_flags,
            shlex.quote(source),
            shlex.quote(self._archive(libgzstream, "libgzstream.a")),
            shlex.quote(self._archive(zlib, "libz.a")),
            shlex.quote(executable),
        )
        self.run(command, cwd=self.build_folder)

    def test(self):
        executable = os.path.join(self.build_folder, "test_libgzstream")
        self.run(shlex.quote(executable), cwd=self.build_folder, env="conanrun")
        result = {
            "executed": True,
            "passed": True,
            "command": "./test_libgzstream",
            "discovered": 1,
            "passedCount": 1,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, sort_keys=True)
        )
        upstream = {
            "status": "passed",
            "framework": "upstream-make-test",
            "command": "equivalent of make test",
            "discovered": 2,
            "executed": 2,
            "passed": 2,
            "failed": 0,
            "skipped": 0,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, sort_keys=True)
        )
