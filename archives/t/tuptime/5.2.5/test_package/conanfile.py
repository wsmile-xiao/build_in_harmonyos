#!/usr/bin/env python3
"""Conan consumer test for tuptime 5.2.5.

The package ships a command line program (Python script), so the consumer test
really executes the installed ``bin/tuptime`` (R34) — no C/C++ compilation is
involved anywhere in this package.  The script is resolved from the tested
package's own ``cpp_info.bindirs`` (absolute) instead of a PATH lookup:
HarmonyOS/HMDFS does not reliably honour the executable bit for ``access(X_OK)``
probes, so ``shutil.which`` would report the installed tool as missing.

The assertion suite (11 cases, including the HarmonyOS-only
``ohos-platform-backend`` case) lives in ``test_tuptime.py``.  See
``MANIFEST.yml`` for the full ledger.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class TuptimeTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        if not can_run(self):
            return
        bindirs = list(
            self.dependencies[self.tested_reference_str]
            .cpp_info.aggregated_components().bindirs
        )
        if not bindirs:
            raise ConanException("tuptime: tested package exposes no bin/ directory")
        tuptime = os.path.join(bindirs[0], "tuptime")
        if not os.path.isfile(tuptime):
            raise ConanException(f"tuptime: installed program missing at {tuptime}")
        script = os.path.join(self.source_folder, "test_tuptime.py")
        # The installed script carries a `#!/usr/bin/env python3` shebang; it is
        # started through an explicit interpreter so the test does not depend on
        # `python3` being resolvable in PATH.
        self.run(f'"{sys.executable}" "{script}" "{tuptime}"', env="conanrun")
