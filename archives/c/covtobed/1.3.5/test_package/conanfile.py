#!/usr/bin/env python3
"""Consumer test for the packaged covtobed executable."""

import base64
import os
import shlex
import shutil
from pathlib import Path

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


MOCK_BAM_B64 = (
    "H4sIBAAAAAAA/wYAQkMCALIAc3L0ZexiYGBw8HDhDPOzMtQz4wz2t0rOzy9KycxLLEnlcggO5Az2s3L1DQiJ5PTxszIxNIGJ+TnHGxgYmhia6RmCZIwsDAy4HALcOT1drJLKEzkD/KyKK/NKMpLzy0BGGwBVOfvAhRRSUtMy8zJLMvPz9EoqShRy85Oz9YoTc7mYgK5hA2KwjQzzGBkYeIA8JLsYPnAxMAAA/vH+k7gAAAAfiwgEAAAAAAD/BgBCQwIArgCd1D0KwkAUReErgsHWleTOG//AQklloY0rEOIG3KILcBkuQx1IEwgknAcDr/max2FC0uz/PnOpOpxXZS/z7absz8e9ra3jQrpeGp1uTRtTWWIsGMuMrRnbMLZlbMfYHjHXjLFKzCoxq8SsErNKzCoxq8SsErNK0nAl7wr9JaMsMRaMZcaGK3kt0UlGWWIsGMuM9U/yA9wLqilyBgAAH4sIBAAAAAAA/wYAQkMCABsAAwAAAAAAAAAAAA=="
)


class CovtobedTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self, src_folder=".")

    def test(self):
        if not can_run(self):
            self.output.warning("Skipping execution because the target cannot run here")
            return

        bam = Path(self.build_folder) / "mock.bam"
        bam.write_bytes(base64.b64decode(MOCK_BAM_B64))
        if str(self.settings.os) == "OHOS":
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        else:
            bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "bash"
        script = os.path.join(self.source_folder, "test.sh")
        self.run(
            f"{shlex.quote(bash)} {shlex.quote(script)} {shlex.quote(str(bam))}",
            env="conanrun",
        )
