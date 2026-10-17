import os

from conan import ConanFile


class VprerexTestConan(ConanFile):
    """test_package for the vprerex executable (Qt5 GUI application).

    R51: the upstream vprerex-6.5.1 tarball ships no test suite (no tests/
    directory, no CTest registration, no `make check` target — the upstream
    build is a plain qmake project). See MANIFEST.yml for the inventory.

    R34/R40: OHOS PC has no guaranteed graphical session, so the OHOS-specific
    verification is headless:
      * `vprerex --version` / `--help` — QApplication construction, argument
        handling and the Qt5 + poppler-qt5 shim link/load chain.
      * `vprerex --check-pdf selftest.pdf` — loads a PDF through the shim,
        renders every page and extracts the link annotations (the OHOS-only
        API surface added by patches/0002 + patches/0003).
    """
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries reliably
        # from arbitrary paths; run through bash (acetoneiso/diffpdf pattern).
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # 1) shim-level functional test (non-GUI entry points).
        self.run(f"{bash} test.sh", env="conanrun")
        # 2) real GUI-path test (QApplication + MainWindow + DocumentWidget +
        #    real render) — the HarmonyOS-specific end-to-end check.
        self.run(f"{bash} test_gui_ohos.sh", env="conanrun")
