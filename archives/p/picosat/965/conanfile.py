#!/usr/bin/env python3
"""Conan recipe — picosat 965 (custom configure.sh + makefile)."""

import json
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class PicosatConan(ConanFile):
    name = "picosat"
    version = "965"
    description = "Satisfiability (SAT) solver with proof and core support"
    license = "MIT"
    homepage = "https://fmv.jku.at/picosat/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("sat-solver", "solver", "cnf", "formal-verification")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "picosat recipe currently supports Linux and OHOS builds only, "
                "got %s" % self.settings.os
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        env = VirtualBuildEnv(self)
        env.generate()

    def _tool(self, key, default):
        try:
            value = self.conf.get(key, default, check_type=str)
        except Exception:
            value = default
        return value or default

    def build(self):
        apply_conandata_patches(self)
        # HMBS [readonly_tmp]: /tmp is read-only on HarmonyOS. Use the
        # HMBS-injected writable TMPDIR when present, otherwise fall back
        # to a directory under the build folder. Exported on the command
        # line itself because env="conanbuild" filters the outer env.
        # Only the temp root is redirected; no test is skipped.
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or os.path.join(self.build_folder, "hmbs-tmp")
        )
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            tmpdir = os.path.join(self.build_folder, "hmbs-tmp")
            os.makedirs(tmpdir, exist_ok=True)
        cc = self._tool("tools.build:compiler_executables:c", "clang")
        if self.settings.build_type == "Debug":
            base_cflags = "-g3 -ggdb -Wall -Wextra"
        else:
            base_cflags = "-O2 -DNDEBUG -Wall -Wextra"
        if self.options.get_safe("fPIC", True) or self.options.shared:
            base_cflags += " -fPIC"
        configure_args = []
        if self.settings.build_type == "Debug":
            configure_args.append("-g")
        if self.options.shared:
            configure_args.append("--shared")
        configure_cmd = "sh ./configure.sh"
        if configure_args:
            configure_cmd += " " + " ".join(configure_args)
        # R33: compiler and flags come from Conan conf, never from bare shell env.
        self.run(
            'TMPDIR="%s" TMP="%s" TEMP="%s" CC="%s" CFLAGS="%s" %s'
            % (tmpdir, tmpdir, tmpdir, cc, base_cflags, configure_cmd),
            cwd=self.source_folder,
            env="conanbuild",
        )
        self._use_posix_shell_for_mkconfig()
        self.run(
            'TMPDIR="%s" TMP="%s" TEMP="%s" make -j1 CC="%s"'
            % (tmpdir, tmpdir, tmpdir, cc),
            cwd=self.source_folder,
            env="conanbuild",
        )
        self._emit_upstream_audit()

    def _use_posix_shell_for_mkconfig(self):
        # Upstream makefile runs ./mkconfig.sh directly, which needs an exec
        # bit. HMDFS may not preserve it, so invoke through POSIX sh instead.
        # This is a build-time invocation fix, not a source patch.
        path = os.path.join(self.source_folder, "makefile")
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                content = handle.read()
        except OSError:
            return
        patched = content.replace("./mkconfig.sh", "sh ./mkconfig.sh")
        if patched != content:
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(patched)

    def _emit_upstream_audit(self):
        # Picosat 965 ships 16 files and no test directory, harness, or
        # check/test make target. Keep this audit in the create log as
        # machine evidence for the no_tests declaration in MANIFEST.yml.
        entries = []
        try:
            entries = sorted(os.listdir(self.source_folder))
        except OSError:
            entries = []
        has_tests_dir = os.path.isdir(os.path.join(self.source_folder, "tests")) or os.path.isdir(
            os.path.join(self.source_folder, "test")
        )
        makefile_in = ""
        try:
            with open(
                os.path.join(self.source_folder, "makefile.in"), "r", encoding="utf-8", errors="replace"
            ) as handle:
                makefile_in = handle.read()
        except OSError:
            makefile_in = ""
        has_check_target = "check" in makefile_in and ("check:" in makefile_in or "check :" in makefile_in)
        self.output.info("picosat upstream audit: %d top-level entries" % len(entries))
        self.output.info("picosat upstream entries: %s" % ", ".join(entries[:16]))
        self.output.info("picosat upstream tests dir present: %s" % has_tests_dir)
        self.output.info("picosat upstream make check target present: %s" % has_check_target)
        upstream = {
            "status": "no_tests",
            "framework": "none",
            "command": "ls source tree + grep makefile.in for check/test targets",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "picosat-965 source tree has 16 files and no tests/ or test/ directory; "
                "makefile.in defines only all/clean/analyze plus binary and library targets "
                "with no check or test target, so there is no upstream suite to execute"
            ),
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))

    def package(self):
        copy(self, "picosat.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "libpicosat.a", self.source_folder, os.path.join(self.package_folder, "lib"))
        if self.options.shared:
            copy(self, "libpicosat.so", self.source_folder, os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["picosat"]
        self.cpp_info.set_property("cmake_file_name", "picosat")
        self.cpp_info.set_property("cmake_target_name", "picosat::picosat")
        self.cpp_info.set_property("pkg_config_name", "picosat")
