import os
import shutil

from conan import ConanFile


class Ros2ColconCdTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        package = self.dependencies["ros2-colcon-cd"]
        function_dir = os.path.join(package.package_folder, "share", "colcon_cd", "function")
        python_module = None
        for root, _, files in os.walk(os.path.join(package.package_folder, "lib")):
            if os.path.basename(root) == "colcon_cd" and "__init__.py" in files:
                python_module = os.path.dirname(root)
                break
        if not python_module:
            raise RuntimeError("Packaged colcon_cd Python module was not found")
        bash = shutil.which("bash")
        if not bash:
            raise RuntimeError("Bash is required to test the packaged colcon_cd function")
        test_script = os.path.join(self.source_folder, "test.sh")
        python_test = os.path.join(self.source_folder, "test.py")
        work_dir = os.path.join(self.build_folder, "test-work")
        os.makedirs(work_dir, exist_ok=True)
        if str(self.settings.os) == "Windows":
            function_dir = function_dir.replace("\\", "/")
            test_script = test_script.replace("\\", "/")
            work_dir = work_dir.replace("\\", "/")
        self.run(
            f'python3 "{python_test}" "{python_module}"',
            env="conanrun",
        )
        self.run(
            f'"{bash}" "{test_script}" "{function_dir}" "{work_dir}"',
            env="conanrun",
        )
