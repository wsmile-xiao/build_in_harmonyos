"""Real functional tests for the packaged xtitle and xtctl commands."""
import os

from conan import ConanFile


class XtitleTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test_xtitle.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bin_dir = os.path.join(self.dependencies["xtitle"].package_folder, "bin")
        script = os.path.join(self.source_folder, "test_xtitle.py")
        self.run(f'python3 "{script}" "{bin_dir}"', env="conanrun")
        self.output.info(
            'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests","framework":"none",'
            '"discovered":0,"executed":0,"passed":0,"failed":0,"skipped":0,'
            '"reason":"upstream archive has no tests directory or registered tests"}'
        )
