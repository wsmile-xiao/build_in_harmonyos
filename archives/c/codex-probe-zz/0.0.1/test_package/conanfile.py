import os
from conan import ConanFile
from conan.tools.build import can_run

class CodexProbeZzTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "test_consumer.py", "MANIFEST.yml"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            dep = self.dependencies["codex-probe-zz"]
            lib = os.path.join(dep.package_folder, "lib")
            script = os.path.join(self.source_folder, "test_consumer.py")
            self.run('python3 "{}" "{}"'.format(script, lib))
