#!/usr/bin/env python3
"""Consumer test for the public barvinok library and iscc executable."""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class BarvinokTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    _OHOS_SYSTEM_LIB_DIRS = ("/system/lib64", "/system/lib")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _signed_runtime_dir(self):
        return os.path.join(self.build_folder, "signed-libs")

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        if str(self.settings_build.os) == "OHOS":
            # E135: the OHOS loader only maps shared libraries carrying a
            # valid ELF signature.  test() fills this directory with freshly
            # signed copies of the non-system NEEDED closure, and the
            # CMakeLists prepends it to the ctest LD_LIBRARY_PATH.
            tc.variables["TEST_PACKAGE_LD_LIBRARY_PATH"] = self._signed_runtime_dir()
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            return

        signed_dir = None
        if str(self.settings_build.os) == "OHOS":
            tested = self.dependencies[self.tested_reference_str]
            roots = [
                os.path.join(self.build_folder, "test_barvinok"),
                os.path.join(tested.package_folder, "bin", "iscc"),
            ]
            signed_dir = self._prepare_ohos_signed_runtime_dir(
                [root for root in roots if os.path.isfile(root)])

        cmake = CMake(self)
        cmake.test()
        shell = "/system/bin/sh" if str(self.settings.os) == "OHOS" else "sh"
        tested = self.dependencies[self.tested_reference_str]
        iscc = os.path.join(tested.package_folder, "bin", "iscc")
        env_prefix = (
            f'LD_LIBRARY_PATH="{signed_dir}:$LD_LIBRARY_PATH" '
            if signed_dir else "")
        self.run(
            f'{env_prefix}{shell} "{os.path.join(self.source_folder, "test_iscc.sh")}" "{iscc}"',
            cwd=self.source_folder,
            env="conanrun",
        )

    def _prepare_ohos_signed_runtime_dir(self, roots):
        """Copy and self-sign the shared library closure of the test binaries.

        Published dependency packages are read-only, and their pre-signed
        copies may not satisfy every OHOS executor (E135), so the test walks
        the DT_NEEDED closure of its own executables and materializes one
        freshly signed regular file per non-system library under
        ``signed-libs``.  Both ctest and the iscc driver put that directory
        at the front of LD_LIBRARY_PATH.
        """
        import shutil

        signed_dir = self._signed_runtime_dir()
        os.makedirs(signed_dir, exist_ok=True)
        dep_dirs = []
        for dep in self.dependencies.host.values():
            lib_dir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(lib_dir):
                dep_dirs.append(lib_dir)

        pending = list(roots)
        seen = set()
        signed = []
        while pending:
            current = pending.pop(0)
            for name in self._needed_shared_libraries(current):
                if name in seen:
                    continue
                seen.add(name)
                if any(os.path.exists(os.path.join(system_dir, name))
                       for system_dir in self._OHOS_SYSTEM_LIB_DIRS):
                    continue
                source = next((os.path.join(lib_dir, name)
                               for lib_dir in dep_dirs
                               if os.path.lexists(os.path.join(lib_dir, name))),
                              None)
                if source is None:
                    raise ConanException(
                        f"E135 cannot resolve test runtime dependency "
                        f"'{name}' from dependency packages")
                target = os.path.join(signed_dir, name)
                if os.path.lexists(target):
                    os.unlink(target)
                shutil.copyfile(os.path.realpath(source), target)
                os.chmod(target, 0o755)
                self._sign_ohos_elf(target)
                signed.append(name)
                pending.append(target)
        self.output.info(
            f"E135 signed test runtime closure: {len(signed)} libraries in "
            "signed-libs")
        return signed_dir

    def _needed_shared_libraries(self, path):
        import subprocess

        readelf = "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(readelf):
            raise ConanException(
                "E135 cannot inspect NEEDED: llvm-readelf is missing")
        result = subprocess.run([readelf, "-d", path], capture_output=True,
                                text=True, timeout=60)
        if result.returncode != 0:
            raise ConanException(f"E135 llvm-readelf -d failed for {path}")
        needed = []
        marker = "Shared library: ["
        for line in result.stdout.splitlines():
            if marker in line:
                needed.append(line.rsplit("]", 1)[0].rsplit(marker, 1)[1])
        return needed

    def _sign_ohos_elf(self, path):
        import subprocess

        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, sign_tool):
            if not os.path.isfile(tool):
                raise ConanException(f"E135 signing tool missing: {tool}")
        subprocess.run([objcopy, "--remove-section", ".codesign", path],
                       capture_output=True, timeout=30)
        tmp = path + ".signed.tmp"
        result = subprocess.run(
            [sign_tool, "sign", "-inFile", path, "-outFile", tmp,
             "-selfSign", "1"],
            capture_output=True, text=True, timeout=60)
        if result.returncode != 0 or not os.path.isfile(tmp):
            raise ConanException(
                f"E135 failed to sign {path}: "
                f"{(result.stdout + result.stderr).strip()}")
        os.replace(tmp, path)
        os.chmod(path, 0o755)
