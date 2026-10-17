#!/usr/bin/env python3
"""Conan recipe for the ircd-hybrid 8.2.46 IRC server on HarmonyOS PC."""

import json
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import (
    Autotools,
    AutotoolsDeps,
    AutotoolsToolchain,
    PkgConfigDeps,
)
from conan.tools.layout import basic_layout


class IrCdHybridConan(ConanFile):
    name = "ircd-hybrid"
    version = "8.2.46-dfsg.1"
    description = "Modular Internet Relay Chat server daemon"
    license = "GPL-2.0-or-later"
    homepage = "https://www.ircd-hybrid.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "ircd-hybrid/8.2.46-dfsg.1 is validated for OHOS/aarch64 only"
            )

    def requirements(self):
        self.requires("openssl/3.5.8.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--prefix=/",
                "--sysconfdir=/etc/ircd-hybrid",
                "--with-tls=openssl",
                # The release's config.guess does not know uname -s=HarmonyOS.
                # Its config.sub accepts this OHOS triplet and canonicalizes it.
                "--build=aarch64-linux-ohos",
            ]
        )
        tc.generate()
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

        # The release contains no registered TESTS/check_PROGRAMS. Still run
        # Automake's check target, then record the audited no-tests result.
        autotools.make(target="check")
        upstream_result = {
            "status": "in_tree_tests_not_registered_external_suite_not_run",
            "in_tree": {
                "framework": "automake",
                "command": "make check",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "8.2.46 registers no in-tree TESTS or check_PROGRAMS.",
            },
            "external_upstream_ci": {
                "suite": "progval/irctest hybrid target with Anope services",
                "revision": "aaa2e26b6e468112665ad7b15d144574a969b411",
                "command": "make -C irctest/ hybrid",
                "collected": 517,
                "selected": 458,
                "deselected": 59,
                "executed": 0,
                "not_run": 458,
                "reason": (
                    "The workflow requires external irctest, Anope 2.1.1, "
                    "pytest, and faketime; these were unavailable on the "
                    "HarmonyOS device."
                ),
            },
        }
        result_dir = os.path.join(self.build_folder, "res")
        os.makedirs(result_dir, exist_ok=True)
        result_path = os.path.join(result_dir, "upstream_test_result.json")
        with open(result_path, "w", encoding="utf-8") as result_file:
            json.dump(upstream_result, result_file, ensure_ascii=False, indent=2)
            result_file.write("\n")
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(upstream_result, ensure_ascii=False)
        )

    def package(self):
        autotools = Autotools(self)
        autotools.install()

        package_bin = os.path.join(self.package_folder, "bin")
        module_dir = os.path.join(
            self.package_folder, "lib", "ircd-hybrid", "modules"
        )
        required = [
            os.path.join(package_bin, "ircd"),
            os.path.join(package_bin, "mkpasswd"),
            os.path.join(module_dir, "m_nick.la"),
            os.path.join(module_dir, "m_user.la"),
            os.path.join(module_dir, "m_ping.la"),
            os.path.join(module_dir, "m_pong.la"),
            os.path.join(module_dir, "m_quit.la"),
            os.path.join(module_dir, "m_message.la"),
        ]
        missing = [path for path in required if not os.path.isfile(path)]
        if missing:
            raise ConanException(
                "ircd-hybrid install is incomplete; missing: " + ", ".join(missing)
            )

        copy(
            self,
            "COPYING.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "upstream_test_result.json",
            src=os.path.join(self.build_folder, "res"),
            dst=os.path.join(self.package_folder, "res"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.append_path("PATH", os.path.join(self.package_folder, "bin"))

