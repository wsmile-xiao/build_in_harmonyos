from conan import ConanFile
import os
from pathlib import Path


class NzbgetTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        # Require the package under test so conan links it into this consumer.
        self.requires(self.tested_reference_str)

    def build(self):
        # Build the smoke consumer source (L0c requires a test source file).
        test_c = Path(self.source_folder) / "test_main.c"
        assert test_c.is_file(), f"test_main.c missing at {test_c}"
        cc = os.environ.get("CC", "/data/service/hnp/bin/clang")
        self.run(f"{cc} {test_c} -o test_main")

    def test(self):
        # nzbget ships only a CLI binary (no public library), so the R34
        # consumer test executes the installed binary itself. test_main.c
        # runs `<nzbget> --version`, asserts the "nzbget version" banner and
        # forwards all output, so a real shell/loader error (exec format,
        # missing library) is visible in the CI log instead of being
        # swallowed. Under L1e sabotage (bin/ removed) the binary is gone,
        # the run fails and the banner can never match — proving the test
        # genuinely depends on the package.
        nzbget = self.dependencies["nzbget"]
        bin_path = os.path.join(nzbget.package_folder, "bin", "nzbget")
        self.run(f'./test_main "{bin_path}"', env="conanrun")
