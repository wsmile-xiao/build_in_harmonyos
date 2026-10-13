"""Installed tools plus exact official parser; no physical/virtual input effects."""
import hashlib, os, shlex, sys
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout

class InterceptionTestConan(ConanFile):
    settings = 'os', 'compiler', 'build_type', 'arch'
    test_type = 'explicit'
    generators = 'PkgConfigDeps', 'VirtualRunEnv'

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires('libevdev/1.13.7')
        self.requires('yaml-cpp/0.9.0')

    def layout(self):
        cmake_layout(self)

    def generate(self):
        pkg = self.dependencies['interception'].package_folder
        source = os.path.join(pkg, 'share', 'interception', 'testable', 'uinput.cpp')
        if not os.path.isfile(source):
            raise ConanException('Package lacks the exact official parser source')
        with open(source, 'rb') as stream:
            if hashlib.sha256(stream.read()).hexdigest() != '95d3188b4cf99d1a19a6714f8e07ac8c726871bbd10414040fdc7765de4581b3':
                raise ConanException('Official parser source byte identity drift')
        tc = CMakeToolchain(self)
        tc.cache_variables['INTERCEPTION_SOURCE'] = source.replace('\\', '/')
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        pkg = self.dependencies['interception'].package_folder
        for name in ('udevmon', 'intercept', 'uinput'):
            if not os.path.isfile(os.path.join(pkg, 'bin', name)):
                raise ConanException('Missing installed product executable: '+name)
        if not can_run(self):
            self.output.info('Cross host: target execution deferred, not PASS')
            return
        probe = os.path.join(self.cpp.build.bindir, 'interception_config_probe')
        script = os.path.join(self.source_folder, 'consumer_tests.py')
        command = ' '.join(shlex.quote(x) for x in [sys.executable, script, 'consumer', probe, pkg, self.build_folder])
        self.run(command, env='conanrun')
        if str(self.settings.os) == 'OHOS':
            command = ' '.join(shlex.quote(x) for x in [sys.executable, script, 'harmony', probe, pkg, self.build_folder])
            self.run(command, env='conanrun')
