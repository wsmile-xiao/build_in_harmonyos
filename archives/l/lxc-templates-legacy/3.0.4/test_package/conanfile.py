import os
import glob

from conan import ConanFile


class LxcTemplatesLegacyTestConan(ConanFile):
    """test_package for lxc-templates-legacy — verifies template scripts are installed."""
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["lxc-templates-legacy"]
        pkg_root = dep.package_folder
        share_dir = os.path.join(pkg_root, "usr", "share", "lxc")
        templates_dir = os.path.join(share_dir, "templates")
        config_dir = os.path.join(share_dir, "config")

        # Run the test.sh script that verifies installed files
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        os.environ["CONAN_PKG_ROOT"] = pkg_root
        self.run(f"{bash} test.sh", env="conanrun")

        # Also verify via Python assertions
        assert os.path.isdir(templates_dir), f"Templates directory not found: {templates_dir}"
        templates = glob.glob(os.path.join(templates_dir, "lxc-*"))
        assert len(templates) >= 20, f"Expected >= 20 template scripts, found {len(templates)}"
        configs = glob.glob(os.path.join(config_dir, "*.conf"))
        assert len(configs) >= 30, f"Expected >= 30 config files, found {len(configs)}"
        self.output.info(f"Verified {len(templates)} templates and {len(configs)} config files")
