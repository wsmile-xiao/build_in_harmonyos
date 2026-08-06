import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class DockerCompletionTestConan(ConanFile):
    settings = "os", "arch"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        resdirs = self.dependencies["docker-completion"].cpp_info.resdirs
        resdir = str(resdirs[0])
        completion_file = os.path.join(resdir, "bash-completion", "completions", "docker")
        test_script = os.path.join(self.source_folder, "test_completion.sh")
        self.run(f"bash {test_script} {completion_file}")
