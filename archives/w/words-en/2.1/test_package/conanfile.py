#!/usr/bin/env python3
"""Consumer tests for the installed words-en data package."""

import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class WordsEnTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def package_id(self):
        # The test recipe produces no reusable binary. Clearing its ID also
        # avoids requiring os.version on HarmonyOS profiles that omit it.
        self.info.clear()

    def test(self):
        if not can_run(self):
            self.output.info(
                "Cross build: run test_words_en.py with WORDS_EN_FILE on HarmonyOS."
            )
            return

        test_script = os.path.join(self.source_folder, "test_words_en.py")
        python = f'"{sys.executable}"'
        harmony_arg = " --harmony" if str(self.settings.os) == "OHOS" else ""
        self.run(f'{python} "{test_script}"{harmony_arg}', env="conanrun")

        word_file = os.path.join(
            self.dependencies["words-en"].package_folder,
            "share",
            "dict",
            "words-en",
        )
        self.run(
            f'{python} "{test_script}" --expect-missing "{word_file}.missing"',
            env="conanrun",
        )
