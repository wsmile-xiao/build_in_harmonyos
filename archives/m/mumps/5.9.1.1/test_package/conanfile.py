import os
import shutil
import subprocess
from pathlib import Path
from shlex import quote
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake,CMakeDeps,CMakeToolchain,cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.build import can_run

class MumpsConsumer(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    def requirements(self):
        self.requires(self.tested_reference_str)
    def layout(self):
        cmake_layout(self)
    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()
        VirtualRunEnv(self).generate()
    def build(self):
        c=CMake(self);c.configure();c.build()
    def test(self):
        if not can_run(self):
            raise ConanInvalidConfiguration("Native OHOS execution is required; tests cannot be skipped")
        root=Path(self.build_folder)
        tools={n:shutil.which(n) for n in ('llvm-readelf','llvm-objcopy','binary-sign-tool')}
        if not all(tools.values()):raise ConanInvalidConfiguration("Missing native signing tools")
        for name in ('mumps_consumer','mumps_harmony'):
            binary=root/name;temporary=Path(str(binary)+'.sign-input');signed=Path(str(binary)+'.signed')
            if temporary.exists() or signed.exists():raise ConanInvalidConfiguration("Stale signing transaction")
            shutil.copyfile(binary,temporary)
            if b'.codesign' in subprocess.check_output([tools['llvm-readelf'],'-S',str(temporary)]):
                subprocess.run([tools['llvm-objcopy'],'--remove-section','.codesign',str(temporary)],check=True)
            subprocess.run([tools['binary-sign-tool'],'sign','-inFile',str(temporary),'-outFile',str(signed),'-selfSign','1'],check=True)
            if b'.codesign' not in subprocess.check_output([tools['llvm-readelf'],'-S',str(signed)]):
                raise ConanInvalidConfiguration("No actual OHOS signature section")
            os.replace(signed,binary);temporary.unlink();binary.chmod(0o755)
            launcher=Path(self.dependencies['mpich'].package_folder)/'bin/mpiexec'
            self.run(' '.join(quote(x) for x in (str(launcher),'-n','2',str(binary))),env='conanrun')
