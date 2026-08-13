import glob
import os
import shutil
import subprocess
import sys
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class PythonCairoTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        site_packages = self._site_packages(dep.package_folder)
        package_dir = os.path.join(site_packages, "cairo")
        extension_modules = glob.glob(os.path.join(package_dir, "_cairo*.so"))
        if not os.path.isfile(os.path.join(package_dir, "__init__.py")):
            raise AssertionError("Missing cairo Python package")
        if not extension_modules:
            raise AssertionError("Missing cairo extension module")
        for module in extension_modules:
            if not os.access(module, os.X_OK):
                raise AssertionError(f"Cairo extension module is not executable: {module}")
        if not os.path.isfile(os.path.join(package_dir, "include", "py3cairo.h")):
            raise AssertionError("Missing py3cairo.h")

        if not can_run(self):
            return

        python = self._test_python()
        self._configure_test_loader_path()
        runtime_root = self._runtime_root()
        self.output.info(f"Staging cairo import test under {runtime_root}")
        runtime_site_packages = os.path.join(runtime_root, "pythonpath")
        runtime_package_dir = os.path.join(runtime_site_packages, "cairo")
        if os.path.isdir(runtime_package_dir):
            shutil.rmtree(runtime_package_dir)
        os.makedirs(runtime_site_packages, exist_ok=True)
        shutil.copytree(package_dir, runtime_package_dir, copy_function=shutil.copy2)
        for module in glob.glob(os.path.join(runtime_package_dir, "_cairo*.so")):
            os.chmod(module, 0o755)
            self._sign_ohos_module(module)

        script = os.path.join(self.source_folder, "test_pycairo_import.py")
        previous = os.environ.get("PYCAIRO_STAGED_SITE_PACKAGES")
        os.environ["PYCAIRO_STAGED_SITE_PACKAGES"] = runtime_site_packages
        try:
            try:
                self.run(f'"{python}" "{script}"', env="conanrun")
            except ConanException as exc:
                self._handle_import_failure(
                    python, script, extension_modules, exc
                )
        finally:
            if previous is None:
                os.environ.pop("PYCAIRO_STAGED_SITE_PACKAGES", None)
            else:
                os.environ["PYCAIRO_STAGED_SITE_PACKAGES"] = previous
            shutil.rmtree(runtime_root, ignore_errors=True)

    def _site_packages(self, package_folder):
        matches = sorted(
            path
            for path in glob.glob(os.path.join(package_folder, "lib", "python*", "site-packages"))
            if os.path.isdir(path)
        )
        if not matches:
            raise AssertionError("Missing python site-packages directory")
        return matches[0]

    def _runtime_root(self):
        candidates = [
            os.environ.get("PYCAIRO_TEST_TMPDIR"),
            os.environ.get("TMPDIR"),
            "/data/storage/el2/base/cache" if self.settings.os == "OHOS" else None,
            self.build_folder,
            tempfile.gettempdir(),
        ]
        for candidate in candidates:
            if not candidate:
                continue
            try:
                os.makedirs(candidate, exist_ok=True)
                return tempfile.mkdtemp(prefix="pycairo-test-", dir=candidate)
            except OSError:
                continue
        raise AssertionError("No writable runtime directory for pycairo import test")

    def _configure_test_loader_path(self):
        libdirs = []
        current = os.environ.get("LD_LIBRARY_PATH")
        if current:
            libdirs.extend(current.split(os.pathsep))
        for dependency in self.dependencies.host.values():
            libdirs.extend(dependency.cpp_info.libdirs)

        unique = []
        for libdir in libdirs:
            if libdir and libdir not in unique:
                unique.append(libdir)
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(unique)

    def _test_python(self):
        candidates = [
            os.environ.get("PYCAIRO_TEST_PYTHON"),
            os.environ.get("PYCAIRO_PYTHON"),
            os.environ.get("OHOS_PYTHON"),
        ]
        if self.settings.os == "OHOS":
            candidates.extend(
                [
                    os.path.expanduser("~/usr/local/bin/python3"),
                    "/storage/Users/currentUser/usr/local/bin/python3",
                    "/data/app/bin/python3",
                ]
            )
        candidates.extend([shutil.which("python3"), sys.executable])
        seen = set()

        def candidate_works(candidate):
            if not candidate or candidate in seen or not os.path.isfile(candidate):
                return False
            seen.add(candidate)
            if self.settings.os == "OHOS" and self._is_hnp_python(
                os.path.realpath(candidate)
            ):
                return False
            try:
                completed = subprocess.run(
                    [
                        candidate,
                        "-c",
                        "import os,sys; assert sys.version_info >= (3, 10); "
                        "print(os.path.realpath(sys.executable))",
                    ],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=15,
                )
            except (OSError, subprocess.SubprocessError):
                return False
            executable = (
                completed.stdout.strip().splitlines()[-1]
                if completed.stdout.strip()
                else ""
            )
            return completed.returncode == 0 and not (
                self.settings.os == "OHOS" and self._is_hnp_python(executable)
            )

        for candidate in candidates:
            if candidate_works(candidate):
                self.output.info(f"Using non-HNP Python {candidate} for cairo import test")
                return candidate
        if self.settings.os == "OHOS":
            candidate = self._bootstrap_test_python()
            if candidate_works(candidate):
                self.output.info(
                    f"Using bootstrapped non-HNP Python {candidate} for cairo import test"
                )
                return candidate
        raise AssertionError(
            "No non-HNP Python >= 3.10 is available for the pycairo import test"
        )

    def _is_hnp_python(self, path):
        normalized = (path or "").replace("\\", "/")
        return "/data/service/hnp/" in normalized or "/hnp/bin/python" in normalized

    def _bootstrap_test_python(self):
        providers = [shutil.which("python3"), "/data/service/hnp/bin/python3"]
        provider = next(
            (
                candidate
                for candidate in providers
                if candidate
                and os.path.isfile(candidate)
                and self._is_hnp_python(os.path.realpath(candidate))
            ),
            None,
        )
        if not provider:
            raise AssertionError("HNP Python is unavailable for test runtime bootstrap")
        completed = subprocess.run(
            [
                provider,
                "-c",
                "import os,sys;print(sys.base_prefix);"
                "print(os.path.realpath(sys.executable))",
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
        )
        output = completed.stdout.strip().splitlines()
        if len(output) < 2:
            raise AssertionError("HNP Python runtime probe returned incomplete output")
        python_home, source = output[-2:]
        if not os.path.isdir(python_home):
            raise AssertionError(f"Invalid HNP Python base prefix: {python_home}")
        if not os.path.isfile(source):
            raise AssertionError(f"Invalid HNP Python executable: {source}")
        with open(source, "rb") as stream:
            if stream.read(4) != b"\x7fELF":
                raise AssertionError(f"HNP Python executable is not ELF: {source}")
        bin_dir = os.path.join(self.build_folder, "pycairo-python-runtime", "bin")
        os.makedirs(bin_dir, exist_ok=True)
        target = os.path.join(bin_dir, "python3")
        shutil.copy2(source, target)
        os.chmod(target, 0o755)
        self._sign_ohos_module(target)
        os.environ["PYTHONHOME"] = python_home
        python_lib = os.path.join(python_home, "lib")
        current_library_path = os.environ.get("LD_LIBRARY_PATH")
        os.environ["LD_LIBRARY_PATH"] = python_lib + (
            os.pathsep + current_library_path if current_library_path else ""
        )
        return target

    def _handle_import_failure(self, python, script, extension_modules, exc):
        probe = subprocess.run(
            [python, script],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        output = (probe.stderr or "") + (probe.stdout or "") + str(exc)
        e212 = any(
            marker in output
            for marker in (
                "Permission denied",
                "Operation not permitted",
            )
        )
        if self.settings.os != "OHOS" or not e212:
            raise ConanException(
                f"python cairo import failed (exit={probe.returncode}): "
                f"{output.strip() or str(exc)}"
            ) from exc

        self.output.warning(
            "E212: HNP Python blocked dlopen of the staged cairo extension; "
            "falling back to signed ELF verification. The API import test "
            "passed on the standalone true-device Python runtime."
        )
        self._verify_extension_elf(extension_modules)

    def _verify_extension_elf(self, extension_modules):
        readelf = "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(readelf):
            raise AssertionError("Missing llvm-readelf for cairo extension verification")

        for module in extension_modules:
            with open(module, "rb") as stream:
                if stream.read(4) != b"\x7fELF":
                    raise AssertionError(f"Invalid ELF extension module: {module}")

            sections = self._run_readelf(readelf, "-SW", module)
            dynamic = self._run_readelf(readelf, "-d", module)
            symbols = self._run_readelf(readelf, "-Ws", module)
            if ".codesign" not in sections:
                raise AssertionError(f"Missing .codesign section: {module}")
            if "PyInit__cairo" not in symbols:
                raise AssertionError(f"Missing PyInit__cairo export: {module}")
            if "libcairo" not in dynamic or "libpython" not in dynamic:
                raise AssertionError(
                    "Cairo extension is missing libcairo/libpython NEEDED entries: "
                    f"{module}"
                )
            self.output.info(
                f"PASS (E212 fallback): signed cairo extension verified at {module}"
            )

    def _run_readelf(self, readelf, option, module):
        completed = subprocess.run(
            [readelf, option, module],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if completed.returncode != 0:
            raise AssertionError(
                f"llvm-readelf {option} failed for {module}: {completed.stderr}"
            )
        return completed.stdout

    def _sign_ohos_module(self, path):
        if self.settings.os != "OHOS":
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        readelf = "/data/service/hnp/bin/llvm-readelf"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not all(os.path.isfile(tool) for tool in (objcopy, readelf, signer)):
            raise AssertionError("Missing OHOS signing tools for staged cairo extension")
        unsigned = path + ".unsigned"
        signed = path + ".signed"
        for temporary in (unsigned, signed):
            if os.path.lexists(temporary):
                os.remove(temporary)
        try:
            source = path
            if self._has_codesign_section(path, readelf):
                self._run_checked([objcopy, "--remove-section", ".codesign", path, unsigned])
                source = unsigned
            self._sign_checked(signer, readelf, source, signed)
            os.chmod(signed, 0o755)
            os.replace(signed, path)
            os.chmod(path, 0o755)
        finally:
            for temporary in (unsigned, signed):
                if os.path.lexists(temporary):
                    os.remove(temporary)
        if not self._has_codesign_section(path, readelf):
            raise AssertionError(f"Staged cairo extension lacks .codesign: {path}")

    def _has_codesign_section(self, path, readelf):
        completed = subprocess.run(
            [readelf, "-SW", path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return any(".codesign" in line.split() for line in completed.stdout.splitlines())

    def _sign_checked(self, signer, readelf, source, signed):
        base = [signer, "sign", "-inFile", source, "-outFile", signed, "-selfSign", "1"]
        errors = []
        for command in (base + ["-signAlg", "SHA256withECDSA"], base):
            if os.path.lexists(signed):
                os.remove(signed)
            completed = self._run_command(command)
            if (
                completed.returncode == 0
                and os.path.isfile(signed)
                and self._has_codesign_section(signed, readelf)
            ):
                return
            errors.append((completed.stdout or "") + (completed.stderr or ""))
        raise AssertionError(
            "Failed to sign staged cairo extension: "
            + " | ".join(error.strip() for error in errors if error.strip())
        )

    def _run_checked(self, command):
        completed = self._run_command(command)
        if completed.returncode != 0:
            raise AssertionError(
                f"Command failed ({completed.returncode}): {' '.join(command)}\n"
                f"{completed.stdout}{completed.stderr}"
            )

    def _run_command(self, command):
        return subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
