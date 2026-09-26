import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.layout import basic_layout

# OHOS bash locations, in preference order (see test() for why `which` is not
# used).  /data/service/hnp/bin/bash is the one the ohos-aarch64 profile
# declares as CONFIG_SHELL.
_OHOS_BASH_CANDIDATES = (
    "/data/service/hnp/bin/bash",
    "/bin/bash",
    "/usr/bin/bash",
)


class ZpaqTestConan(ConanFile):
    """test_package for zpaq 7.15 — really runs the CLI that the package installs.

    zpaq is an application package, so the L1 test is a behaviour contract on
    the installed executable rather than a link/API test.  All assertions live
    in test.sh (bash); see the header of that file for the check list.
    """
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        # Resolve the binary from the package folder explicitly: removing the
        # package must make this test fail (CI L1e destructive reverse check).
        zpaq_bin = os.path.join(
            self.dependencies["zpaq"].package_folder, "bin", "zpaq"
        )
        script = os.path.join(self.source_folder, "test.sh")
        # OHOS: /system/bin/sh (mksh) cannot reliably spawn ELF binaries, so the
        # script is executed by a real bash.  Both resolution branches are
        # validated with os.path.exists() — $CONFIG_SHELL first (the
        # ohos-aarch64 profile declares an absolute path in [buildenv]), then
        # the known OHOS bash locations — so that a missing interpreter fails
        # loudly with the message below instead of being silently masked by a
        # baked-in default.  `shutil.which("bash")` is deliberately NOT used:
        # it picks up the invoking runtime's bundled bash
        # (/data/storage/el1/bundle/.../bash/bin/bash), which conan's spawned
        # shell cannot execute (measured: "Permission denied", exit 126).
        shell = os.environ.get("CONFIG_SHELL")
        if not shell or not os.path.exists(shell):
            shell = next(
                (p for p in _OHOS_BASH_CANDIDATES if os.path.exists(p)), None
            )
        if not shell:
            raise ConanException(
                "no bash found to run test_package/test.sh: set CONFIG_SHELL "
                "(see ci/conan/profiles/ohos-aarch64) or install bash under "
                + " / ".join(_OHOS_BASH_CANDIDATES)
            )
        self.run(f'"{shell}" "{script}" "{zpaq_bin}"', env="conanrun")
