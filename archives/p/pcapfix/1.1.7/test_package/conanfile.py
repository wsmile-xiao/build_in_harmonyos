import os
import shutil

from conan import ConanFile


class PcapfixTestConan(ConanFile):
    """Conan test_package — pcapfix 1.1.7 consumer functional test.

    pcapfix has no upstream test suite (see MANIFEST.yml), so this test
    exercises real repair behavior end-to-end via test_pcapfix.sh:
    - no-args invocation prints a usage banner and exits non-zero
    - a pcap whose 4 global-header magic bytes were zeroed gets repaired:
      exit code 0, "[+] SUCCESS: 1 Corruption(s) fixed!" banner, magic
      restored, output file size preserved
    """
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # R5/OHOS: use CONFIG_SHELL bash (no /bin/sh for complex scripts)
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder
        bin_dir = os.path.join(pkg_folder, "bin")
        for script in ("test_pcapfix.sh", "consumer_pcap_repair_pipeline.sh"):
            path = os.path.join(self.source_folder, script)
            self.run(f'{bash} {path} "{bin_dir}"', env="conanrun")
