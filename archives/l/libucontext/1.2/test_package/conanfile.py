import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


def _sdk_llvm_libdir(compiler):
    """Return the active SDK llvm/lib containing lld's libxml2 runtime."""
    candidates = []
    if compiler:
        try:
            resource_dir = subprocess.check_output(
                [compiler, "-print-resource-dir"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            candidates.append(os.path.dirname(os.path.dirname(resource_dir)))
        except (OSError, subprocess.CalledProcessError):
            pass
        compiler = os.path.realpath(compiler)
        candidates.append(
            os.path.join(os.path.dirname(os.path.dirname(compiler)), "lib")
        )

    for candidate in dict.fromkeys(candidates):
        if os.path.isfile(os.path.join(candidate, "libxml2.so.16")):
            return candidate
    return ""


class LibucontextTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _build_environment(self):
        environment = Environment()
        if str(self.settings.os) != "OHOS":
            return environment

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        sdk_llvm_lib = _sdk_llvm_libdir(compilers.get("c") or "clang")
        if not sdk_llvm_lib:
            return environment

        lld = os.path.join(os.path.dirname(sdk_llvm_lib), "bin", "lld")
        probe_env = os.environ.copy()
        probe_env["LD_LIBRARY_PATH"] = os.pathsep.join(
            part
            for part in (sdk_llvm_lib, probe_env.get("LD_LIBRARY_PATH", ""))
            if part
        )
        try:
            probe = subprocess.run(
                [lld, "-flavor", "gnu", "--version"],
                env=probe_env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise ConanException(
                f"Cannot execute the active OHOS SDK linker {lld}: {error}"
            ) from error
        if probe.returncode != 0:
            raise ConanException(
                f"The active OHOS SDK linker failed its GNU-flavor probe: "
                f"{lld}; stderr={probe.stderr.strip()!r}"
            )

        self.output.info(
            f"Prepending OHOS SDK linker runtime path: {sdk_llvm_lib}"
        )
        environment.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        return environment

    def build(self):
        cmake = CMake(self)
        with self._build_environment().vars(self).apply():
            cmake.configure()
            cmake.build()

    def test(self):
        if not can_run(self):
            return
        bindir = self.cpp.build.bindirs[0]
        self.run(os.path.join(bindir, "test_libucontext"), env="conanrun")
        if str(self.settings.os) == "OHOS":
            self.run(os.path.join(bindir, "test_ohos_ucontext"), env="conanrun")
