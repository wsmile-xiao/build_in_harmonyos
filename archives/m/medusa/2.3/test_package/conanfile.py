#!/usr/bin/env python3
"""Conan test_package for medusa 2.3 - Conan L1 official test.

medusa is a command-line tool, so instead of linking against a library the test
executes the packaged `medusa' binary.  Two layers run:

  test_medusa.sh      artefact-level: the binary starts (OpenSSL default +
                      legacy providers load) and dlopen()s the packaged
                      lib/medusa/modules/*.mod service modules;
  test_medusa_e2e.sh  consumer-level (L0d): a deterministic FTP server with one
                      valid credential pair is started on loopback and a real
                      audit is driven through it, so the packaged binary has to
                      connect, speak the FTP protocol, recognise the valid
                      credential, report the find and reject a wrong password.
"""
import json
import os

from conan import ConanFile
from conan.errors import ConanException


class MedusaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies["medusa"].package_folder
        medusa = os.path.join(
            self.dependencies["medusa"].cpp_info.bindirs[0], "medusa"
        )
        if not os.path.isfile(medusa):
            raise FileNotFoundError(f"medusa binary not packaged: {medusa}")
        os.chmod(medusa, 0o755)

        # OHOS has no /bin/sh that can run an ELF: always go through bash.
        bash = os.environ.get("CONFIG_SHELL") or "bash"

        test_script = os.path.join(self.source_folder, "test_medusa.sh")
        self.run(f'{bash} "{test_script}" "{medusa}"', env="conanrun")

        # Complete consumer case: drive a real audit against a live (loopback)
        # service instead of only asserting properties of the artefact.
        e2e_script = os.path.join(self.source_folder, "test_medusa_e2e.sh")
        if not os.path.isfile(e2e_script):
            raise ConanException(f"test_medusa_e2e.sh missing: {e2e_script}")
        module_dir = os.path.join(package, "lib", "medusa", "modules")
        if not os.path.isdir(module_dir):
            raise ConanException(f"medusa module dir missing: {module_dir}")
        self.run(f'{bash} "{e2e_script}" "{medusa}" "{module_dir}"',
                 env="conanrun")
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(
                {
                    "executed": True,
                    "passed": True,
                    "command": "test_medusa.sh + test_medusa_e2e.sh",
                    "discovered": 17,
                    "passedCount": 17,
                },
                ensure_ascii=False,
            )
        )
