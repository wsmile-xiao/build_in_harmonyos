"""Execute the actual completion with a fixed official dynamic loader."""
import os
import shlex
import sys
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import download

class FabricCompletionTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        download(self, "https://raw.githubusercontent.com/scop/bash-completion/79d225bad8939a3833314b5af93509131c03f2f8/bash_completion",
                 os.path.join(self.build_folder, "bash_completion"),
                 sha256="f347b832c91d44358bb335e69fa7576241d67040795a1a4d8897317c739d35b1")

    def test(self):
        if not can_run(self):
            self.output.info("Runtime tests require the target Bash; not marked PASS on a cross host")
            return
        bash = self.conf.get("tools.microsoft.bash:path", default="bash", check_type=str) or "bash"
        product = os.path.join(self.dependencies["fabric-completion"].package_folder, "share", "bash-completion", "completions", "fab")
        command = [sys.executable, os.path.join(self.source_folder, "consumer.py"), "--bash", bash,
                   "--product", product, "--loader", os.path.join(self.build_folder, "bash_completion"),
                   "--work", os.path.join(self.build_folder, "functional-work")]
        self.run(shlex.join(command), env="conanrun")
        if str(self.settings.os) == "OHOS":
            self.run(shlex.join([*command, "--harmony"]), env="conanrun")
