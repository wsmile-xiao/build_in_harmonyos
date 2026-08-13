import glob
import hashlib
import json
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class PythonCairoConan(ConanFile):
    name = "python-cairo"
    version = "1.29.0"
    description = "Python bindings for the cairo graphics library"
    license = "LGPL-2.1-only OR MPL-1.1"
    homepage = "https://pycairo.readthedocs.io"
    url = "https://github.com/pygobject/pycairo"

    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "test_tmpfile_shim.c"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        self.requires("cairo/1.18.4")

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        python = self._python3()
        tc.project_options["python"] = python
        tc.project_options["tests"] = True
        tc.project_options["wheel"] = False
        tc.project_options["no-x11"] = True
        tc.project_options["wrap_mode"] = "nodownload"
        if self.settings.os == "OHOS":
            python_info = self._python_info()
            tc.project_options["libpython"] = python_info["libpython"]
            tc.project_options["test-runtime-dir"] = self._test_runtime_dir()
            tc.project_options["pytest-pythonpath"] = self._pytest_pythonpath()
            self._sanitize_build_environment()
            tc.project_options["test-library-path"] = self._test_library_path()
            tc.project_options["test-ld-preload"] = self._tmpfile_shim_path()
        tc.generate()
        self._inject_meson_archive_tools()

    def build(self):
        runtime_dir = self._test_runtime_dir() if self.settings.os == "OHOS" else None
        try:
            apply_conandata_patches(self)
            self._use_writable_tmpdir()
            meson = Meson(self)
            meson.configure()
            meson.build()
            if can_run(self):
                if self.settings.os == "OHOS":
                    self._build_tmpfile_shim()
                    self._sign_extension_modules(self._build_extension_modules())
                    self._stage_upstream_tests()
                meson.test()
            else:
                self.output.info(
                    "Cross-building: skip upstream pytest because target extensions are not runnable"
                )
        finally:
            if runtime_dir:
                shutil.rmtree(runtime_dir, ignore_errors=True)

    def package(self):
        Meson(self).install()
        self._sign_extension_modules()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.set_property("pkg_config_name", "py3cairo")
        for site_packages in self._site_packages_dirs():
            self.runenv_info.prepend_path("PYTHONPATH", site_packages)

    def _python3(self):
        if self.settings.os == "OHOS":
            return self._python_info()["executable"]
        for candidate in self._python_candidates():
            if candidate and os.path.isfile(candidate):
                return candidate
        raise ConanInvalidConfiguration(
            "python-cairo requires a target python3 >= 3.10; set PYCAIRO_PYTHON if it is not on PATH"
        )

    def _python_candidates(self):
        candidates = [
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
        candidates.extend(
            [
                shutil.which("python3"),
                "/usr/local/bin/python3",
                "/usr/bin/python3",
            ]
        )
        result = []
        seen = set()
        for candidate in candidates:
            if not candidate:
                continue
            normalized = os.path.normpath(candidate)
            if normalized not in seen:
                seen.add(normalized)
                result.append(candidate)
        return result

    def _is_hnp_python(self, path):
        normalized = (path or "").replace("\\", "/")
        return "/data/service/hnp/" in normalized or "/hnp/bin/python" in normalized

    def _python_info(self):
        cached = getattr(self, "_cached_python_info", None)
        if cached:
            return cached
        code = (
            "import json,os,sys,sysconfig;"
            "d=dict(ver=sysconfig.get_python_version(),"
            "libdir=sysconfig.get_config_var('LIBDIR'),"
            "libpl=sysconfig.get_config_var('LIBPL'),"
            "prefix=sys.base_prefix,"
            "include=sysconfig.get_path('include'),"
            "executable=sys.executable,"
            "real_executable=os.path.realpath(sys.executable));"
            "m=[l.split()[-1] for l in open('/proc/self/maps') if 'libpython' in l] "
            "if os.path.exists('/proc/self/maps') else [];"
            "d['loaded_libpython']=m[0] if m else '';"
            "print(json.dumps(d))"
        )
        errors = []

        def inspect_candidate(py):
            if not os.path.isfile(py) or self._is_hnp_python(os.path.realpath(py)):
                return None
            try:
                info = json.loads(
                    subprocess.check_output([py, "-c", code], timeout=15).decode()
                )
                if self._is_hnp_python(info.get("real_executable")):
                    errors.append(f"{py}: resolves to HNP Python")
                    return None
                major, minor = [int(x) for x in info["ver"].split(".")[:2]]
                if (major, minor) < (3, 10):
                    errors.append(f"{py}: Python {info['ver']} is too old")
                    return None
                python_h = os.path.join(info.get("include") or "", "Python.h")
                if not os.path.isfile(python_h):
                    errors.append(f"{py}: Python.h is missing")
                    return None
                info["libpython"] = self._libpython_file(py, info)
                info["executable"] = py
                self._cached_python_info = info
                self.output.info(
                    f"Using non-HNP Python {py} ({info['ver']}) for upstream pytest"
                )
                return info
            except (
                ConanInvalidConfiguration,
                OSError,
                ValueError,
                KeyError,
                subprocess.SubprocessError,
            ) as exc:
                errors.append(f"{py}: {exc}")

        for py in self._python_candidates():
            info = inspect_candidate(py)
            if info:
                return info

        try:
            bootstrapped = self._bootstrap_non_hnp_python()
        except (
            ConanException,
            OSError,
            ValueError,
            KeyError,
            subprocess.SubprocessError,
        ) as exc:
            errors.append(f"bootstrapped Python: {exc}")
        else:
            info = inspect_candidate(bootstrapped)
            if info:
                return info

        detail = "; ".join(errors) or "no non-HNP candidate was executable"
        raise ConanInvalidConfiguration(
            "OHOS full upstream pytest requires a non-HNP target Python >= 3.10 "
            f"with headers and libpython; set PYCAIRO_PYTHON ({detail})"
        )

    def _bootstrap_non_hnp_python(self):
        cached = getattr(self, "_bootstrapped_python", None)
        if cached and os.path.isfile(cached):
            return cached
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
            raise ConanInvalidConfiguration("HNP Python is unavailable for runtime bootstrap")
        probe = (
            "import json,os,sys;"
            "print(json.dumps({'home':sys.base_prefix,"
            "'executable':os.path.realpath(sys.executable)}))"
        )
        data = json.loads(
            subprocess.check_output([provider, "-c", probe], timeout=15).decode()
        )
        python_home = data.get("home") or ""
        if not os.path.isdir(python_home):
            raise ConanInvalidConfiguration(
                f"HNP Python reported an invalid base prefix: {python_home}"
            )
        source = data.get("executable") or ""
        if not os.path.isfile(source):
            raise ConanInvalidConfiguration(
                f"HNP Python reported an invalid executable: {source}"
            )
        with open(source, "rb") as stream:
            if stream.read(4) != b"\x7fELF":
                raise ConanInvalidConfiguration(
                    f"HNP Python executable is not an ELF file: {source}"
                )
        bin_dir = os.path.join(self.build_folder, "pycairo-python-runtime", "bin")
        os.makedirs(bin_dir, exist_ok=True)
        target = os.path.join(bin_dir, "python3.bin")
        launcher = os.path.join(bin_dir, "python3")
        shutil.copy2(source, target)
        os.chmod(target, 0o755)
        self._sign_extension_modules([target])
        python_lib = os.path.join(python_home, "lib")
        launcher_script = (
            "#!/bin/sh\n"
            f"export PYTHONHOME={shlex.quote(python_home)}\n"
            f"python_lib={shlex.quote(python_lib)}\n"
            "if [ -n \"${LD_LIBRARY_PATH:-}\" ]; then\n"
            "    export LD_LIBRARY_PATH=\"$python_lib:$LD_LIBRARY_PATH\"\n"
            "else\n"
            "    export LD_LIBRARY_PATH=\"$python_lib\"\n"
            "fi\n"
            f"exec {shlex.quote(target)} \"$@\"\n"
        )
        with open(launcher, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(launcher_script)
        os.chmod(launcher, 0o755)
        self._bootstrapped_python = launcher
        self.output.info(
            f"Bootstrapped signed non-HNP Python {launcher} with isolated runtime environment"
        )
        return launcher

    def _pytest_pythonpath(self):
        cached = getattr(self, "_cached_pytest_pythonpath", None)
        if cached is not None:
            return cached
        python = self._python_info()["executable"]
        if self._can_import_pytest(python):
            self._cached_pytest_pythonpath = ""
            return ""

        probe = (
            "import os,pytest;"
            "print(os.path.dirname(os.path.dirname(os.path.realpath(pytest.__file__))))"
        )
        for provider in (shutil.which("python3"), "/data/service/hnp/bin/python3"):
            if not provider or not os.path.isfile(provider):
                continue
            try:
                completed = subprocess.run(
                    [provider, "-c", probe],
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=15,
                )
            except (OSError, subprocess.SubprocessError):
                continue
            if completed.returncode != 0:
                continue
            output = completed.stdout.strip()
            if not output:
                continue
            pytest_root = output.splitlines()[-1]
            if os.path.isdir(pytest_root) and self._can_import_pytest(python, pytest_root):
                self._cached_pytest_pythonpath = pytest_root
                self.output.info(f"Using pytest modules from {pytest_root}")
                return pytest_root
        raise ConanInvalidConfiguration(
            f"Upstream tests require pytest for {python}; install pytest or expose it via PYTHONPATH"
        )

    def _can_import_pytest(self, python, pythonpath=None):
        env = os.environ.copy()
        if pythonpath:
            existing = env.get("PYTHONPATH")
            env["PYTHONPATH"] = (
                pythonpath + (os.pathsep + existing if existing else "")
            )
        try:
            completed = subprocess.run(
                [python, "-c", "import pytest"],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                timeout=15,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        return completed.returncode == 0

    def _libpython_file(self, py, info):
        loaded = info.get("loaded_libpython") or ""
        if loaded and os.path.isfile(loaded):
            return loaded
        version = info["ver"]
        roots = [
            info.get("libpl"),
            info.get("libdir"),
            os.path.join(info.get("prefix", ""), "lib"),
            os.path.join(os.path.dirname(os.path.dirname(py)), "lib"),
            os.path.expanduser("~/usr/local/lib"),
            "/usr/local/lib",
        ]
        names = [f"libpython{version}.so", f"libpython{version}.so.1.0"]
        for root in roots:
            if not root:
                continue
            for name in names:
                candidate = os.path.join(root, name)
                if os.path.isfile(candidate):
                    return candidate
            hits = glob.glob(os.path.join(root, f"libpython{version}.so*"))
            if hits:
                return hits[0]
        raise ConanInvalidConfiguration(
            "OHOS Python extensions must link libpython explicitly; "
            f"could not find libpython{version}.so for {py}"
        )

    def _site_packages_dirs(self):
        pattern = os.path.join(self.package_folder, "lib", "python*", "site-packages")
        return [path for path in sorted(glob.glob(pattern)) if os.path.isdir(path)]

    def _use_writable_tmpdir(self):
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir

    def _inject_meson_archive_tools(self):
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(native_file):
            return
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c") or ""
        search_dirs = []
        for path in (cc, os.path.realpath(cc) if cc else ""):
            if path and os.path.sep in path:
                search_dirs.append(os.path.dirname(path))
        search_dirs.append("/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin")

        ar = ""
        ranlib = ""
        for directory in search_dirs:
            ar_candidate = os.path.join(directory, "llvm-ar")
            if os.path.isfile(ar_candidate):
                ar = ar_candidate
                ranlib_candidate = os.path.join(directory, "llvm-ranlib")
                if os.path.isfile(ranlib_candidate):
                    ranlib = ranlib_candidate
                break
        if not ar:
            return

        with open(native_file, encoding="utf-8") as handle:
            content = handle.read()
        if "\nar =" in content or "[binaries]" not in content:
            return
        insert = "[binaries]\n"
        insert += f"ar = '{ar}'\n"
        if ranlib:
            insert += f"ranlib = '{ranlib}'\n"
        content = content.replace("[binaries]\n", insert, 1)
        with open(native_file, "w", encoding="utf-8") as handle:
            handle.write(content)

    def _build_extension_modules(self):
        groups = {
            "_cairo": glob.glob(os.path.join(self.build_folder, "cairo", "_cairo*.so")),
            "cmod": glob.glob(os.path.join(self.build_folder, "tests", "cmod*.so")),
        }
        missing = [name for name, modules in groups.items() if not modules]
        if missing:
            raise ConanException(
                "Missing upstream pytest extension modules: " + ", ".join(missing)
            )
        return sorted(module for modules in groups.values() for module in modules)

    def _sanitize_build_environment(self):
        removed = [
            name
            for name in ("LD_LIBRARY_PATH", "PYTHONHOME")
            if os.environ.pop(name, None) is not None
        ]
        if removed:
            self.output.info(
                "Cleared inherited runtime variables before Meson configure: "
                + ", ".join(removed)
            )

    def _tmpfile_shim_path(self):
        return os.path.join(self.build_folder, "pycairo-test-runtime", "libtmpfile-shim.so")

    def _build_tmpfile_shim(self):
        source = os.path.join(self.source_folder, "test_tmpfile_shim.c")
        output = self._tmpfile_shim_path()
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compiler_executables.get("c") or shutil.which("clang") or shutil.which("cc")
        if not compiler or not os.path.isfile(compiler):
            raise ConanException("A C compiler is required to build the OHOS tmpfile test shim")
        os.makedirs(os.path.dirname(output), exist_ok=True)
        subprocess.run(
            [compiler, "-shared", "-fPIC", "-O2", source, "-o", output],
            check=True,
        )
        os.chmod(output, 0o755)
        self._sign_extension_modules([output])
        self.output.info(f"Built signed OHOS tmpfile test shim {output}")

    def _test_runtime_dir(self):
        digest = hashlib.sha256(os.path.realpath(self.build_folder).encode()).hexdigest()[:12]
        candidates = [
            os.environ.get("PYCAIRO_TEST_TMPDIR"),
            "/data/storage/el2/base/cache",
            self.build_folder,
        ]
        for root in candidates:
            if not root:
                continue
            try:
                os.makedirs(root, exist_ok=True)
                runtime_dir = os.path.join(root, f"pycairo-upstream-tests-{digest}")
                os.makedirs(runtime_dir, exist_ok=True)
                return runtime_dir
            except OSError:
                continue
        raise ConanInvalidConfiguration(
            "OHOS upstream pytest requires a writable non-HNP runtime directory"
        )

    def _stage_upstream_tests(self):
        runtime_dir = self._test_runtime_dir()
        if os.path.isdir(runtime_dir):
            shutil.rmtree(runtime_dir)
        os.makedirs(runtime_dir)
        try:
            for directory in ("cairo", "tests"):
                source = os.path.join(self.build_folder, directory)
                if not os.path.isdir(source):
                    raise ConanException(f"Missing upstream pytest build directory: {source}")
                shutil.copytree(
                    source,
                    os.path.join(runtime_dir, directory),
                    copy_function=shutil.copy2,
                )
        except Exception:
            shutil.rmtree(runtime_dir, ignore_errors=True)
            raise
        self.output.info(f"Staged upstream pytest under {runtime_dir}")
        return runtime_dir

    def _test_library_path(self):
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
        loader_path = os.pathsep.join(unique)
        self.output.info(
            "Configured Meson test loader path with Conan host dependencies"
        )
        return loader_path

    def _sign_extension_modules(self, modules=None):
        if self.settings.os != "OHOS":
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        readelf = "/data/service/hnp/bin/llvm-readelf"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in (objcopy, readelf, signer):
            if not os.path.isfile(tool):
                raise ConanException(f"Required OHOS signing tool is missing: {tool}")
        if modules is None:
            pattern = os.path.join(
                self.package_folder, "lib", "python*", "site-packages", "cairo", "*.so"
            )
            modules = sorted(glob.glob(pattern))
        if not modules:
            raise ConanException("No pycairo extension modules found to sign")
        for so in modules:
            unsigned = so + ".unsigned"
            signed = so + ".signed"
            for temporary in (unsigned, signed):
                if os.path.lexists(temporary):
                    os.remove(temporary)
            os.chmod(so, 0o755)
            try:
                sign_input = so
                if self._has_codesign_section(so, readelf):
                    subprocess.run(
                        [objcopy, "--remove-section", ".codesign", so, unsigned],
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                    )
                    sign_input = unsigned
                self._sign_ohos_elf(signer, readelf, sign_input, signed)
                os.chmod(signed, 0o755)
                os.replace(signed, so)
                os.chmod(so, 0o755)
            finally:
                for temporary in (unsigned, signed):
                    if os.path.lexists(temporary):
                        os.remove(temporary)
            if not self._has_codesign_section(so, readelf):
                raise ConanException(f"Signed pycairo extension lacks .codesign: {so}")

    def _has_codesign_section(self, path, readelf):
        completed = subprocess.run(
            [readelf, "-SW", path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return any(".codesign" in line.split() for line in completed.stdout.splitlines())

    def _sign_ohos_elf(self, signer, readelf, source, signed):
        base = [signer, "sign", "-inFile", source, "-outFile", signed, "-selfSign", "1"]
        errors = []
        for command in (base + ["-signAlg", "SHA256withECDSA"], base):
            if os.path.lexists(signed):
                os.remove(signed)
            completed = subprocess.run(
                command,
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            if (
                completed.returncode == 0
                and os.path.isfile(signed)
                and self._has_codesign_section(signed, readelf)
            ):
                return
            errors.append((completed.stdout or "") + (completed.stderr or ""))
        raise ConanException(
            "Failed to sign pycairo extension module: "
            + " | ".join(error.strip() for error in errors if error.strip())
        )
