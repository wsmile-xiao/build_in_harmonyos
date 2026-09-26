import base64
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class ProbabelTestConan(ConanFile):
    """test_package for the ProbABEL executables — runs test.sh which
    drives palinear on bundled upstream inputs and diffs against the
    upstream verified result."""

    # The two genotype fixtures are binary files.  The platform CI checks
    # out PR branches with git-am(1) without --binary, so a binary file in
    # the PR diff fails with "patch does not apply" (measured on PR !11933:
    # every CI round died on test.dose.fvd/.fvi, the verdicts mislabelled
    # as network errors).  They therefore travel as base64 text in git and
    # are restored here, into the conan source copy; the git worktree and
    # the PR diff never contain the binaries.
    _B64_FIXTURES = ("test.dose.fvd", "test.dose.fvi")

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = (
        "test.sh",
        "input/*",
        "expected/*",
    )

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _restore_b64_fixtures(self):
        for name in self._B64_FIXTURES:
            b64_path = os.path.join(self.source_folder, "input", name + ".b64")
            out_path = os.path.join(self.source_folder, "input", name)
            with open(b64_path, "r") as f:
                data = base64.b64decode(f.read())
            with open(out_path, "wb") as f:
                f.write(data)

    def test(self):
        self._restore_b64_fixtures()
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries.
        # Use bash to wrap binary execution; run the script from the
        # source folder so its input/ and expected/ trees resolve.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.source_folder, "test.sh")
        self.run(f'{bash} "{script}"', env="conanrun")
