#!/usr/bin/env python3
"""Conan recipe — libmsv 1.1.1 (Autotools)."""
import json
import os
import subprocess
import sys
import time

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.env import Environment
from conan.tools.files import (
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibmsvConan(ConanFile):
    name = "libmsv"
    version = "1.1.1"
    description = "Monkeysphere Validation Agent client library"
    license = "GPL-3.0-or-later"
    homepage = "https://salsa.debian.org/clint/libmsv"
    url = "https://salsa.debian.org/clint/libmsv"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def export_sources(self):
        export_conandata_patches(self)
        copy(
            self,
            "mock_msva.py",
            src=os.path.join(self.recipe_folder, "test_package"),
            dst=os.path.join(self.export_sources_folder, "test_package"),
        )

    def requirements(self):
        self.requires("curl/8.15.0.1")
        self.requires("jansson/2.15.1.1")

    def build_requirements(self):
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libmsv is supported only on Linux and OHOS"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS" and self.settings_build.os == "OHOS":
            # GNU config.guess does not recognise `uname -s = HarmonyOS` on
            # native workers.  The generated config.sub accepts the canonical
            # OHOS triplet, which is also correct for local cross builds.
            tc.configure_args.extend([
                # Keep build != host so configure does not execute conftest
                # binaries from the HMDFS Conan build tree (which is noexec).
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-ohos",
            ])
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        tc.generate()

    def build(self):
        # HarmonyOS PC stores the Conan build tree on HMDFS.  The HNP bash
        # used by the CI profile cannot always reconstruct that directory via
        # getcwd(2), while it does correctly honour a matching logical PWD.
        # Seed PWD for each out-of-source phase so Autoconf never starts with
        # an indeterminate working directory.
        if self.settings.os == "OHOS":
            os.environ["PWD"] = self.source_folder
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        if self.settings.os == "OHOS":
            # Autoconf creates config.status helpers below mode-0700
            # directories.  HMDFS permission normalisation makes those
            # directories inaccessible to the CI shell (E129), so use 0755.
            replace_in_file(
                self,
                os.path.join(self.source_folder, "configure"),
                "umask 077",
                "umask 022",
            )
        if self.settings.os == "OHOS":
            try:
                os.chdir(self.build_folder)
            except OSError:
                pass
            os.environ["PWD"] = self.build_folder
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        self._run_upstream_test(autotools)

    def _run_upstream_test(self, autotools):
        """Run upstream's one Automake test against an offline MSVA fixture."""
        if cross_building(self):
            self.output.warning(
                "make check requires native execution; it runs in the "
                "HarmonyOS CI profile and is covered by test_package locally"
            )
            return

        port_file = os.path.join(self.build_folder, "upstream-msva.port")
        if os.path.exists(port_file):
            os.remove(port_file)
        fixture = os.path.join(
            self.export_sources_folder, "test_package", "mock_msva.py"
        )
        server = subprocess.Popen(
            [sys.executable, fixture, port_file], cwd=self.build_folder
        )
        try:
            for _ in range(100):
                if os.path.isfile(port_file):
                    break
                if server.poll() is not None:
                    raise RuntimeError("mock MSVA exited before becoming ready")
                time.sleep(0.05)
            else:
                raise RuntimeError("mock MSVA did not become ready")

            with open(port_file, "r", encoding="utf-8") as stream:
                port = stream.read().strip()
            runtime = Environment()
            runtime.define(
                "MONKEYSPHERE_VALIDATION_AGENT_SOCKET",
                "http://127.0.0.1:{}".format(port),
            )
            for dependency in self.dependencies.values():
                for libdir in dependency.cpp_info.libdirs:
                    runtime.prepend_path("LD_LIBRARY_PATH", libdir)
            with runtime.vars(self).apply():
                autotools.make(target="check", args=["-j1"])
            result = {
                "status": "passed",
                "framework": "automake-check",
                "command": "make check -j1",
                "discovered": 1,
                "executed": 1,
                "passed": 1,
                "failed": 0,
                "skipped": 0,
            }
            self.output.info(
                "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result)
            )
        finally:
            server.terminate()
            server.wait(timeout=10)

    def package(self):
        Autotools(self).install(args=["-j1"])
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["msv"]
        self.cpp_info.requires = ["curl::curl", "jansson::jansson"]
        self.cpp_info.set_property("cmake_file_name", "libmsv")
        self.cpp_info.set_property("cmake_target_name", "libmsv::libmsv")
        self.cpp_info.set_property("pkg_config_name", "libmsv")
