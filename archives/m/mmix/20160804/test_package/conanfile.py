#!/usr/bin/env python3
"""MMIX installed command consumer tests."""
from pathlib import Path
import shlex
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.layout import basic_layout


class MmixTest(ConanFile):
    settings = 'os', 'arch', 'compiler', 'build_type'
    test_type = 'explicit'

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        runner = self.conf.get('user.mmix:runner', default='')
        if runner or can_run(self):
            self.run(shlex.join(['python3', str(Path(self.source_folder) / 'test_mmix.py'),
                                 '--package', self.dependencies['mmix'].package_folder,
                                 '--runner', runner, '--out', str(Path(self.build_folder) / 'consumer-report.json')]),
                     env='conanrun')
        else:
            self.output.warning('Native consumer testing pending: this is a cross build.')
