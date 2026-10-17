import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class BundlerCompletionTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        resdirs = self.dependencies["bundler-completion"].cpp_info.resdirs
        completion_file = os.path.join(str(resdirs[0]), "bash-completion", "completions", "bundler")
        test_script = os.path.join(self.source_folder, "test_bundler_completion.sh")
        self.run(f'bash "{test_script}" "{completion_file}"')
