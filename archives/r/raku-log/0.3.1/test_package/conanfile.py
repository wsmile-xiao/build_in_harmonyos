import os
import shutil
import subprocess
import sys

from conan import ConanFile


class RakuLogTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test_module.raku", "test_ohos.raku", "test_runner.py"

    def requirements(self):
        self.requires(self.tested_reference_str, run=True)

    def test(self):
        package = self.dependencies[self.tested_reference_str].package_folder
        rakudo = self.dependencies["rakudo"].package_folder
        platform = str(self.settings.os)
        runner = os.path.join(self.source_folder, "test_runner.py")
        # Use the interpreter already running Conan: a bare "python3" is not
        # guaranteed to be on PATH on the CI workers.
        interpreter = sys.executable or shutil.which("python3") or shutil.which("python")
        args = [interpreter, runner, package, rakudo, platform]
        if platform == "OHOS":
            env = os.environ.copy()
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                filter(None, [os.path.join(rakudo, "lib"), env.get("LD_LIBRARY_PATH", "")])
            )
            subprocess.run(args, check=True, env=env)
        else:
            self.run(" ".join(f'"{arg}"' for arg in args), env="conanrun")
