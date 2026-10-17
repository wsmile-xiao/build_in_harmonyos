import os
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class CoinmpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _sdk_libcpp_dir(self):
        """Locate the OHOS SDK directory containing libc++_shared.so.

        test_coinmp links against libc++_shared.so; the runtime loader must
        find it via LD_LIBRARY_PATH (the SDK dir is not on the default
        search path).  Derive the dir from the active compiler, same spirit
        as the abseil test_package locating the SDK llvm/lib.
        """
        if str(self.settings.os) != "OHOS":
            return ""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = compilers.get("cpp") or compilers.get("c")
        candidates = []
        if cxx:
            compiler = os.path.realpath(cxx)
            # <sdk>/llvm/bin/clang -> <sdk>/llvm/lib/aarch64-linux-ohos
            candidates.append(
                os.path.join(os.path.dirname(os.path.dirname(compiler)),
                             "lib", "aarch64-linux-ohos")
            )
            try:
                resource_dir = subprocess.check_output(
                    [cxx, "-print-resource-dir"],
                    stderr=subprocess.DEVNULL,
                    text=True,
                ).strip()
                candidates.append(os.path.join(
                    os.path.dirname(os.path.dirname(resource_dir)),
                    "lib", "aarch64-linux-ohos"))
            except (OSError, subprocess.CalledProcessError):
                pass
        for candidate in dict.fromkeys(candidates):
            if os.path.isfile(os.path.join(candidate, "libc++_shared.so")):
                return candidate
        return ""

    def test(self):
        if not can_run(self):
            self.output.warning("Cross-built consumer cannot run here; skip.")
            return
        bindir = self.cpp.build.bindirs[0]
        executable = os.path.join(bindir, "test_coinmp")
        sdk_libcpp = self._sdk_libcpp_dir()
        if sdk_libcpp:
            self.output.info(f"Runtime libc++ dir: {sdk_libcpp}")
            self.run(
                f"export LD_LIBRARY_PATH='{sdk_libcpp}:$LD_LIBRARY_PATH' && "
                f"'{executable}'",
                env="conanrun",
                cwd=self.build_folder,
            )
        else:
            self.run(f"'{executable}'", env="conanrun", cwd=self.build_folder)
