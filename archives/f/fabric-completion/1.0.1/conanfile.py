"""Repair: install the upstream fab completion under its command lookup name."""
import os
import subprocess
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get

class FabricCompletionConan(ConanFile):
    name = "fabric-completion"
    version = "1.0.1"
    license = "MIT"
    description = "Bash completion for Fabric's fab command"
    homepage = "https://github.com/n0740/fabric-completion"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    settings = "os", "arch", "compiler", "build_type"
    package_type = "unknown"

    def export_sources(self):
        copy(self, "*.patch", src=os.path.join(self.recipe_folder, "patches"),
             dst=os.path.join(self.export_sources_folder, "patches"))

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS", "Macos", "FreeBSD"):
            raise ConanInvalidConfiguration("Requires a POSIX Bash environment")

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        bash = self.conf.get("tools.microsoft.bash:path", default="bash", check_type=str) or "bash"
        result = subprocess.run([bash, "-n", os.path.join(self.source_folder, "fabric-completion.bash")], capture_output=True)
        if result.returncode:
            raise ConanInvalidConfiguration("Bash syntax failed: " + result.stderr.decode("utf-8", "replace"))

    def package(self):
        dest = os.path.join(self.package_folder, "share", "bash-completion", "completions")
        copy(self, "fabric-completion.bash", src=self.source_folder, dst=dest)
        os.rename(os.path.join(dest, "fabric-completion.bash"), os.path.join(dest, "fab"))
        copy(self, "README.md", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "doc", self.name))
        copy(self, "fabric-completion.bash", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.resdirs = ["share/bash-completion/completions"]
