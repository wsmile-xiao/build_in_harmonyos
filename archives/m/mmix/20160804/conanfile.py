#!/usr/bin/env python3
"""Conan recipe — MMIX 20160804 (CWEB and direct C compiler)."""
import os
from pathlib import Path
import shlex
import shutil
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run, cross_building
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout


class MmixConan(ConanFile):
    name = 'mmix'
    version = '20160804'
    description = 'MMIX assembler, simulator, object inspector and pipeline meta-simulator'
    license = 'LicenseRef-Knuth-MMIXware'
    homepage = 'https://mmix.cs.hm.edu/'
    package_type = 'application'
    settings = 'os', 'arch', 'compiler', 'build_type'
    options = {'static': [True, False]}
    default_options = {'static': False}
    exports_sources = 'upstream_tests.py'

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        self.tool_requires('cweb/4.12.2')

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data['sources'], strip_root=False)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        work = Path(self.build_folder) / 'work'
        work.mkdir(parents=True, exist_ok=True)
        for item in Path(self.source_folder).iterdir():
            if item.is_file() and (item.suffix in ('.w', '.h', '.ch', '.mms', '.run', '.out', '.mmconfig', '.mmix') or item.name == 'README'):
                shutil.copy2(item, work / item.name)
        ctangle = Path(self.dependencies.build['cweb'].package_folder) / 'bin' / 'ctangle'
        modules = ('mmix-arith', 'mmix-io', 'mmix-sim', 'mmixal', 'mmix-mem', 'mmix-pipe', 'mmix-config', 'mmmix', 'mmotype')
        for module in modules:
            args = [str(ctangle), module + '.w']
            if module in ('mmmix', 'mmotype'):
                args.append(module + '-portability.ch')
            self.run(shlex.join(args), cwd=str(work))
        # Exact output of upstream abstime.w; avoids executing an AArch64 bootstrap on the build host.
        (work / 'abstime.h').write_text('#define ABSTIME %d\n' % int(time.time()), encoding='ascii')
        executables = self.conf.get('tools.build:compiler_executables', default={}, check_type=dict)
        compiler = executables.get('c')
        if not compiler:
            if cross_building(self):
                raise ConanException('Cross builds require tools.build:compiler_executables.c')
            compiler = 'gcc' if str(self.settings.compiler) == 'gcc' else 'clang'
        flags = ['-std=gnu89', '-O2', '-fstack-protector-strong']
        flags += ['-static'] if self.options.static else ['-fPIE', '-pie', '-Wl,-z,relro,-z,now']
        programs = {
            'mmixal': ['mmixal.c', 'mmix-arith.c'],
            'mmix': ['mmix-sim.c', 'mmix-arith.c', 'mmix-io.c'],
            'mmotype': ['mmotype.c'],
            'mmmix': ['mmmix.c', 'mmix-arith.c', 'mmix-pipe.c', 'mmix-config.c', 'mmix-mem.c', 'mmix-io.c'],
        }
        for program, sources in programs.items():
            self.run(shlex.join([compiler] + flags + sources + ['-o', program]), cwd=str(work))
            binary = work / program
            binary.chmod(0o755)
            if str(self.settings.os) == 'OHOS' and not cross_building(self):
                signer = self.conf.get('user.mmix:sign_tool', default='/data/service/hnp/bin/binary-sign-tool')
                self.run(shlex.join([signer, 'sign', '-inFile', str(binary), '-outFile', str(binary), '-selfSign', '1']))
                binary.chmod(0o755)
        runner = self.conf.get('user.mmix:runner', default='')
        if runner or can_run(self):
            environment = 'QEMU AArch64 on Linux; not HarmonyOS device' if runner else str(self.settings.os) + ' native'
            self.run(shlex.join(['python3', str(Path(self.source_folder) / 'upstream_tests.py'), '--src', str(work),
                                 '--bin', str(work), '--out', str(Path(self.build_folder) / 'upstream-report.json'),
                                 '--runner', runner, '--environment', environment]))
        else:
            self.output.warning('Cross-built only: native execution and ELF signing require a HarmonyOS PC.')

    def package(self):
        work = str(Path(self.build_folder) / 'work')
        for program in ('mmixal', 'mmix', 'mmotype', 'mmmix'):
            copy(self, program, src=work, dst=os.path.join(self.package_folder, 'bin'))
        copy(self, 'boilerplate.w', src=work, dst=os.path.join(self.package_folder, 'licenses'))
        copy(self, 'README', src=work, dst=os.path.join(self.package_folder, 'share', 'mmix'))
        for pattern in ('*.mms', '*.run', '*.out', '*.mmconfig', '*.mmix'):
            copy(self, pattern, src=work, dst=os.path.join(self.package_folder, 'share', 'mmix', 'examples'))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ['bin']
        self.buildenv_info.prepend_path('PATH', os.path.join(self.package_folder, 'bin'))
        self.runenv_info.prepend_path('PATH', os.path.join(self.package_folder, 'bin'))
