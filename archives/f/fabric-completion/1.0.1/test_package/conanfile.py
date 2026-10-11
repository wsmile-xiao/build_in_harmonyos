"""Execute the actual completion with a fixed official dynamic loader."""
import os
import shlex
import shutil
import sys
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import download
from conan.tools.env import VirtualBuildEnv
from urllib.parse import urlsplit

def loader_urls(recipe):
    official = "https://raw.githubusercontent.com/scop/bash-completion/79d225bad8939a3833314b5af93509131c03f2f8/bash_completion"
    urls = recipe.conf.get("user.fabric-completion:loader_urls", default=[official, "https://gh-proxy.org/" + official], check_type=list)
    if not urls:
        raise RuntimeError("At least one HTTPS loader source is required")
    for url in urls:
        if not isinstance(url, str):
            raise RuntimeError("Loader sources must be HTTPS URL strings")
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
            raise RuntimeError("Loader sources must be HTTPS without credentials or fragments")
    return urls

def target_bash(recipe):
    explicit = recipe.conf.get("user.fabric-completion:bash", default="", check_type=str)
    explicit = explicit or recipe.conf.get("tools.microsoft.bash:path", default="", check_type=str)
    if explicit:
        candidates = [explicit]
    else:
        candidates = [os.environ.get("CONFIG_SHELL", ""), shutil.which("bash")]
        if str(recipe.settings.os) == "OHOS":
            candidates.append("/data/service/hnp/bin/bash")
    for value in candidates:
        if value and os.path.isabs(value) and os.path.isfile(value) and os.access(value, os.X_OK):
            return value
    raise RuntimeError("Actual executable Bash required; configure user.fabric-completion:bash or buildenv CONFIG_SHELL with an absolute path")

class FabricCompletionTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        download(self, loader_urls(self),
                 os.path.join(self.build_folder, "bash_completion"),
                 sha256="f347b832c91d44358bb335e69fa7576241d67040795a1a4d8897317c739d35b1")

    def test(self):
        if not can_run(self):
            self.output.info("Runtime tests require the target Bash; not marked PASS on a cross host")
            return
        with VirtualBuildEnv(self).vars().apply():
            bash = target_bash(self)
        product = os.path.join(self.dependencies["fabric-completion"].package_folder, "share", "bash-completion", "completions", "fab")
        command = [sys.executable, os.path.join(self.source_folder, "consumer.py"), "--bash", bash,
                   "--product", product, "--loader", os.path.join(self.build_folder, "bash_completion"),
                   "--work", os.path.join(self.build_folder, "functional-work")]
        self.run(shlex.join(command), env="conanrun")
        if str(self.settings.os) == "OHOS":
            self.run(shlex.join([*command, "--harmony"]), env="conanrun")
