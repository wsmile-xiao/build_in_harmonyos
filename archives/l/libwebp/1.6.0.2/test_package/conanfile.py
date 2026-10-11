import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv

class TestConan(ConanFile):
    settings="os", "arch", "compiler", "build_type"
    test_type="explicit"
    def requirements(self):self.requires(self.tested_reference_str)
    def layout(self):cmake_layout(self)
    def generate(self):
        CMakeDeps(self).generate();CMakeToolchain(self).generate();VirtualRunEnv(self).generate()
    def build(self):
        cmake=CMake(self);cmake.configure();cmake.build()
        if self.settings.os=="OHOS":
            tools={name:shutil.which(name) for name in ("llvm-readelf","llvm-objcopy","binary-sign-tool")}
            if not all(tools.values()):raise ConanInvalidConfiguration("Missing real signing tools")
            for name in ("consumer","harmony_native_loader"):
                binary=Path(self.build_folder)/"bin"/name
                sections=subprocess.run([tools["llvm-readelf"],"-S",str(binary)],capture_output=True,check=True)
                if b".codesign" in sections.stdout:self.run(" ".join(shlex.quote(x) for x in (tools["llvm-objcopy"],"--remove-section",".codesign",str(binary))))
                self.run(" ".join(shlex.quote(x) for x in (tools["binary-sign-tool"],"sign","-inFile",str(binary),"-outFile",str(binary),"-selfSign","1")))
                after=subprocess.run([tools["llvm-readelf"],"-S",str(binary)],capture_output=True,check=True)
                if after.stdout.count(b".codesign")!=1:raise ConanInvalidConfiguration("Missing or duplicate actual codesign section")
                binary.chmod(0o755)
    def test(self):
        if not can_run(self):raise ConanInvalidConfiguration("Consumer must actually run")
        self.run(shlex.quote(str(Path(self.build_folder)/"bin/consumer")),env="conanrun")
        if self.settings.os=="OHOS":
            package=self.dependencies["libwebp"].package_folder
            readelf=shutil.which("llvm-readelf")
            if not readelf:raise ConanInvalidConfiguration("Missing actual ELF reader")
            script=Path(self.source_folder)/"harmony_tests/signed_loader.py"
            native=Path(self.build_folder)/"bin/harmony_native_loader"
            self.run(" ".join(shlex.quote(str(x)) for x in (sys.executable,script,package,readelf,native)),env="conanrun")
