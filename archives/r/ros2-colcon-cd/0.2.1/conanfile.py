import os
import shutil
import sys

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class Ros2ColconCdConan(ConanFile):
    name = "ros2-colcon-cd"
    version = "0.2.1"
    description = "A shell function for colcon to change the working directory"
    license = "Apache-2.0"
    homepage = "https://github.com/colcon/colcon-cd"
    url = "https://github.com/colcon/colcon-cd"
    package_type = "application"
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        python = shutil.which("python3") or shutil.which("python") or sys.executable
        bash = shutil.which("bash")
        # Ensure setuptools is available — OHOS system Python may lack it.
        # --no-build-isolation below requires setuptools.build_meta to be importable.
        self.run(
            f'"{python}" -m pip install --break-system-packages '
            f'--timeout 120 --retries 3 setuptools wheel'
        )
        self.run(f'"{python}" -m compileall -q colcon_cd', cwd=self.source_folder)
        if bash:
            for script in ("colcon_cd.sh", "colcon_cd-argcomplete.bash"):
                path = os.path.join(self.source_folder, "function", script)
                self.run(f'"{bash}" -n "{path}"')
        staging = os.path.join(self.build_folder, "staging")
        self.run(
            f'"{python}" -m pip install --no-deps --no-build-isolation '
            f'--prefix="{staging}" "{self.source_folder}"'
        )

    def package(self):
        copy(
            self,
            "*",
            src=os.path.join(self.build_folder, "staging"),
            dst=self.package_folder,
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        python_path = None
        for root, _, files in os.walk(self.package_folder):
            if os.path.basename(root) == "colcon_cd" and "__init__.py" in files:
                python_path = os.path.dirname(root)
                break
        if not python_path:
            raise RuntimeError("Packaged colcon_cd Python module was not found")
        function_path = os.path.join(
            self.package_folder, "share", "colcon_cd", "function"
        )
        self.runenv_info.prepend_path("PYTHONPATH", python_path)
        self.runenv_info.define_path("COLCON_CD_FUNCTION_PATH", function_path)
