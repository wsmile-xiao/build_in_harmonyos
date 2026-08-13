#!/usr/bin/env python3
"""Conan recipe for packaging Pygments 2.20.0."""

import os
import queue
import subprocess
import sys
import threading
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)


class PygmentsConan(ConanFile):
    name = "pygments"
    version = "2.20.0.1"
    description = "Syntax highlighting package written in Python"
    license = "BSD-2-Clause"
    homepage = "https://pygments.org"
    url = "https://github.com/pygments/pygments"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        self.settings.rm_safe("os.version")

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _run_with_heartbeat(self, command, cwd=None, heartbeat=30):
        self.output.info("running: " + " ".join(command))
        proc = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        lines = queue.Queue()

        def reader():
            for line in proc.stdout:
                lines.put(line)

        thread = threading.Thread(target=reader, daemon=True)
        thread.start()
        last_output = time.monotonic()

        while proc.poll() is None or not lines.empty():
            try:
                line = lines.get(timeout=1)
            except queue.Empty:
                if proc.poll() is None and time.monotonic() - last_output >= heartbeat:
                    self.output.info("heartbeat: command still running")
                    last_output = time.monotonic()
                continue

            self.output.info(line.rstrip())
            last_output = time.monotonic()

        thread.join(timeout=1)
        if proc.returncode != 0:
            raise ConanException(
                "command failed with exit code {}: {}".format(
                    proc.returncode,
                    " ".join(command),
                )
            )

    def build(self):
        apply_conandata_patches(self)

        test_deps = os.path.join(self.build_folder, "_test_deps")
        self._run_with_heartbeat(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "--no-compile",
                "--target",
                test_deps,
                "pytest==8.4.2",
                "coverage==7.8.0",
                "pytest-cov==6.2.1",
                "pytest-randomly==4.1.0",
                "wcag-contrast-ratio==0.9",
            ]
        )

        test_env = Environment()
        test_env.prepend_path("PYTHONPATH", test_deps)
        test_env.prepend_path("PYTHONPATH", self.source_folder)
        with test_env.vars(self).apply():
            self._run_with_heartbeat(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    "--randomly-seed=1",
                    "tests",
                ],
                cwd=self.source_folder,
            )

    def package(self):
        module_src = os.path.join(self.source_folder, "pygments")
        module_dst = os.path.join(
            self.package_folder,
            "lib",
            "python",
            "site-packages",
            "pygments",
        )
        copy(self, "*.py", src=module_src, dst=module_dst, keep_path=True)
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "AUTHORS",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

        command = os.path.join(self.package_folder, "bin", "pygmentize")
        save(
            self,
            command,
            "#!/usr/bin/env python3\n"
            "from pygments.cmdline import main\n\n"
            'if __name__ == "__main__":\n'
            "    raise SystemExit(main())\n",
        )
        os.chmod(command, 0o755)

    def package_info(self):
        site_packages = os.path.join(
            self.package_folder,
            "lib",
            "python",
            "site-packages",
        )
        bin_path = os.path.join(self.package_folder, "bin")
        self.runenv_info.prepend_path("PYTHONPATH", site_packages)
        self.runenv_info.prepend_path("PATH", bin_path)
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
