#!/usr/bin/env python3
"""Functional runtime test for the packaged plugin~ Pure Data external."""
import os
import shlex
import shutil
import tempfile

from conan import ConanFile


class PdPluginTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("puredata/0.54.1")
        self.requires("ladspa-sdk/1.17")

    @staticmethod
    def _find(root, filename):
        for directory, _, files in os.walk(root):
            if filename in files:
                return os.path.join(directory, filename)
        return None

    @staticmethod
    def _scratch():
        for root in (os.environ.get("TMPDIR"), os.path.join(os.path.expanduser("~"), "tmp")):
            if root:
                try:
                    os.makedirs(root, exist_ok=True)
                    return tempfile.mkdtemp(prefix="pd-plugin-test-", dir=root)
                except OSError:
                    pass
        return tempfile.mkdtemp(prefix="pd-plugin-test-")

    def test(self):
        package = self.dependencies[self.tested_reference_str].package_folder
        pd_package = self.dependencies["puredata"].package_folder
        ladspa_package = self.dependencies["ladspa-sdk"].package_folder
        plugin = self._find(package, "plugin~.pd_linux")
        pd_header = self._find(pd_package, "m_pd.h")
        ladspa_header = self._find(ladspa_package, "ladspa.h")
        amp = self._find(ladspa_package, "amp.so")
        missing = [name for name, path in (
            ("plugin~.pd_linux", plugin), ("m_pd.h", pd_header),
            ("ladspa.h", ladspa_header), ("amp.so", amp)) if not path]
        if missing:
            raise Exception(f"required test artifacts not found: {', '.join(missing)}")

        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = executables.get("c") or "clang"
        work = self._scratch()
        binary = os.path.join(work, "pd_plugin_test")
        try:
            self.run(
                f"{shlex.quote(cc)} -std=gnu11 -O1 -Wall -Wextra -rdynamic "
                f"-I{shlex.quote(os.path.dirname(pd_header))} "
                f"-I{shlex.quote(os.path.dirname(ladspa_header))} "
                f"{shlex.quote(os.path.join(self.source_folder, 'pd_plugin_test.c'))} "
                f"-o {shlex.quote(binary)} -ldl",
                env="conanbuild",
            )
            self.run(
                f"{shlex.quote(binary)} {shlex.quote(plugin)} {shlex.quote(amp)}",
                env="conanrun",
            )
        finally:
            shutil.rmtree(work, ignore_errors=True)
