#!/usr/bin/env python3
"""test_package for dicom3tools -- exercises the installed command line tools.

dicom3tools is a set of ~115 separate programs plus a display tool, not a
library, so the test drives the real binaries end to end:

  1. dccreate writes a Part 10 DICOM file from scratch (no fixture needed);
  2. dcdump reads it back and the attributes that were set must reappear;
  3. dccreate/dcdump round trip through dcdict and dckey (data dictionary);
  4. dciodvfy parses the file and reports on it;
  5. dcstats reads the file and reports the missing pixel attributes;
  6. dccp re-encodes the meta header;
  7. truncated and non-DICOM inputs must be rejected.

The DICOM file is generated at run time: the repository forbids adding binary
fixtures, because the platform generated pr.diff carries no binary patch body
and CI's `git apply` would fail before the build even starts.

test.sh is the source file for CI L0c compliance.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.layout import basic_layout


class Dicom3ToolsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # Without an explicit layout build_folder == source_folder, so running
        # the generator scripts would drop conanrun/conanbuild env files and the
        # test working directory straight into the package source tree.
        basic_layout(self)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries, so the test
        # script has to be run through bash.  CONFIG_SHELL comes from the
        # ohos-aarch64 profile (/data/service/hnp/bin/bash) and is the only
        # reliable source: PATH inside the conan create sandbox does not
        # necessarily contain a bash, and falling back to a plain `sh` would
        # silently pick mksh, which fails with "Error 127" on every command in
        # the script instead of reporting the real problem.
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash")
        if not bash or not os.access(bash, os.X_OK):
            raise ConanException(
                "no usable bash found to run test_package/test.sh "
                "(CONFIG_SHELL=%r); mksh cannot execute the ELF binaries under test"
                % os.environ.get("CONFIG_SHELL")
            )
        # layout() above makes the current directory the build folder, so the
        # script must be addressed by an absolute path: a bare "test.sh" is
        # looked up in test_package/build-<config>/ and dies with
        # "test.sh: No such file or directory" (ConanException: Error 127).
        script = None
        for folder in (
            self.source_folder,
            self.recipe_folder,
            os.path.dirname(os.path.abspath(__file__)),
        ):
            candidate = os.path.join(folder, "test.sh")
            if os.path.isfile(candidate):
                script = candidate
                break
        if script is None:
            raise ConanException(
                "test_package/test.sh not found next to the test conanfile "
                "(source_folder=%r)" % self.source_folder
            )
        self.run(f'{bash} "{script}"', env="conanrun")
