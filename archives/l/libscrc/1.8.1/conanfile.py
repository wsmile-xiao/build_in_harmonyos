"""Conan recipe for the libscrc CPython extension package."""
import glob
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LibscrcConan(ConanFile):
    name = "libscrc"
    version = "1.8.1"
    description = "CPython extension modules for CRC and checksum algorithms"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/hex-in/libscrc"
    url = "https://github.com/hex-in/libscrc"
    package_type = "python-require"

    settings = "os", "arch", "compiler", "build_type"
    # The CI worker currently runs CPython 3.12, while the device brew
    # environment runs CPython 3.14. Keep the interpreter ABI explicit in the
    # package ID so each runtime receives matching extension modules.
    options = {"python_abi": ["3.12", "3.14"]}
    default_options = {"python_abi": "3.12"}

    _extensions = {
        "_crcx": ("crcx", "_crcxmodule.c", "_crcxtables.c"),
        "_canx": ("canx", "_canxmodule.c", "_canxtables.c"),
        "_crc8": ("crc8", "_crc8module.c", "_crc8tables.c"),
        "_crc16": ("crc16", "_crc16module.c", "_crc16tables.c"),
        "_crc24": ("crc24", "_crc24module.c", "_crc24tables.c"),
        "_crc32": ("crc32", "_crc32module.c", "_crc32tables.c"),
        "_crc64": ("crc64", "_crc64module.c", "_crc64tables.c"),
    }
    _upstream_modules = (
        "modbus", "hacker", "crcx", "crc8", "crc16", "crc24", "crc32", "crc64", "canx"
    )

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        source_package = os.path.join(self.source_folder, "libscrc")
        if not os.path.isfile(os.path.join(source_package, "__init__.py")):
            raise ConanException("upstream libscrc Python package was not found")

        python = shutil.which("python3.14") or sys.executable
        probe = subprocess.run(
            [python, "-c", (
                "import json,sys,sysconfig; "
                "print(json.dumps({'version': '%d.%d' % sys.version_info[:2], "
                "'include': sysconfig.get_path('include'), "
                "'ext_suffix': sysconfig.get_config_var('EXT_SUFFIX'), "
                "'cc': sysconfig.get_config_var('CC'), "
                "'ldshared': sysconfig.get_config_var('LDSHARED'), "
                "'ccshared': sysconfig.get_config_var('CCSHARED'), "
                "'cflags': sysconfig.get_config_var('CFLAGS')}))"
            )], capture_output=True, text=True, check=True,
        )
        import json
        config = json.loads(probe.stdout)
        if config["version"] != str(self.options.python_abi):
            raise ConanException(
                "libscrc package ABI is CPython {}; found {}".format(
                    self.options.python_abi, config["version"]
                )
            )
        include = config["include"]
        if not os.path.isfile(os.path.join(include, "Python.h")):
            raise ConanException("Python.h is missing from the selected CPython include directory")

        # The sdist's setup.py imports setuptools, which is not part of the target
        # CPython install. Build the exact seven Extension() source pairs directly.
        package_build = os.path.join(self.build_folder, "python", "libscrc")
        shutil.copytree(source_package, package_build, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        compiler_tools = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compiler_tools.get("c") or shlex.split(config["cc"] or "clang")[0]
        # LDSHARED carries CPython executable link flags (including -lintl),
        # which are not part of a Python extension module's link requirements.
        link = [compiler, "-shared"]
        compile_flags = shlex.split(config["ccshared"] or "-fPIC")
        compile_flags += shlex.split(config["cflags"] or "")
        suffix = config["ext_suffix"]
        if not suffix:
            raise ConanException("target CPython did not report EXT_SUFFIX")

        for module, (directory, module_source, tables_source) in self._extensions.items():
            src_dir = os.path.join(self.source_folder, "src", directory)
            output = os.path.join(package_build, module + suffix)
            command = link + compile_flags + [
                "-I" + include,
                "-I" + src_dir,
                os.path.join(src_dir, module_source),
                os.path.join(src_dir, tables_source),
                "-o", output,
            ]
            self.output.info("Building CPython extension {}".format(module))
            self.run(shlex.join(command), cwd=self.source_folder, env="conanbuild")

        extensions = glob.glob(os.path.join(package_build, "_*.so"))
        if len(extensions) != len(self._extensions):
            raise ConanException("expected seven CPython extensions, found {}".format(len(extensions)))
        self._run_upstream_tests(python, package_build)

    def _run_upstream_tests(self, python, package_build):
        # HNP CPython workers have a read-only platlib under /data/service/hnp.
        # E212/E502 also prohibit dlopen from writable user paths, so no
        # writable staging directory can make the extension tests run there.
        try:
            test_root = self._python_runtime_tmpdir(python, "libscrc-1.8.1-")
        except ConanException as exc:
            if str(self.settings.os) != "OHOS" or not self._uses_readonly_hnp_runtime(python):
                raise
            self.output.warning(
                "E212/E502: active CPython platlib is not writable; the OHOS HNP "
                "worker also blocks dlopen from user paths. Upstream runtime tests "
                "NOT RUN on this worker; checking extension ELF/ABI/entry points instead."
            )
            self.output.info("UPSTREAM_TEST_SUMMARY: NOT_RUN=22 (E212/E502 HNP loader policy)")
            self._verify_extensions_static(package_build, str(self.options.python_abi))
            return
        self.output.info("Running upstream tests from Python runtime path {}".format(test_root))
        try:
            shutil.copytree(package_build, os.path.join(test_root, "libscrc"))
            modules = ["libscrc.test." + name for name in self._upstream_modules]
            runner = os.path.join(test_root, "run_upstream.py")
            with open(runner, "w", encoding="utf-8") as stream:
                stream.write(
                    "import sys, unittest\n"
                    "names = {}\n".format(repr(modules))
                    + "suite = unittest.defaultTestLoader.loadTestsFromNames(names)\n"
                    + "result = unittest.TextTestRunner(verbosity=2).run(suite)\n"
                    + "passed = result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped)\n"
                    + "print('UPSTREAM_TEST_SUMMARY: PASS={}/{} FAIL={} SKIP={}'.format(\n"
                    + "    passed, result.testsRun, len(result.failures) + len(result.errors), len(result.skipped)))\n"
                    + "sys.exit(0 if result.wasSuccessful() and not result.skipped else 1)\n"
                )
            command = "{} {}".format(shlex.quote(python), shlex.quote(runner))
            try:
                self.run(command, cwd=test_root, env="conanrun")
            except ConanException as exc:
                probe = subprocess.run(
                    [python, runner], cwd=test_root, capture_output=True, text=True
                )
                detail = (probe.stderr or "") + (probe.stdout or "") + str(exc)
                e212 = self._is_native_loader_denial(detail)
                if str(self.settings.os) == "OHOS" and e212:
                    self.output.warning(
                        "E212/E502: HNP worker denied dlopen of upstream extension modules; "
                        "upstream runtime tests NOT RUN. Checking extension ELF/ABI/entry points instead."
                    )
                    self.output.info("UPSTREAM_TEST_SUMMARY: NOT_RUN=22 (E212/E502 HNP loader policy)")
                    self._verify_extensions_static(package_build, str(self.options.python_abi))
                else:
                    raise ConanException(
                        "upstream runtime tests failed (exit={}): {}".format(
                            probe.returncode, detail.strip() or str(exc)
                        )
                    ) from exc
        finally:
            shutil.rmtree(test_root, ignore_errors=True)

    @staticmethod
    def _python_runtime_tmpdir(python, prefix):
        # Do not fall back to HOME/.cache or app-storage TMPDIR: OHOS can allow
        # writing there but reject dlopen of native extensions from those paths.
        probe = subprocess.run(
            [python, "-c", "import sysconfig; print(sysconfig.get_path('platlib'))"],
            capture_output=True, text=True, check=True,
        )
        temp_root = probe.stdout.strip()
        if not temp_root or not os.path.isdir(temp_root):
            raise ConanException("active Python platlib is unavailable for native test modules")
        if not os.access(temp_root, os.W_OK | os.X_OK):
            raise ConanException("active Python platlib is not writable for native test modules: {}".format(temp_root))
        try:
            return tempfile.mkdtemp(prefix=prefix, dir=temp_root)
        except OSError as exc:
            raise ConanException("cannot stage native test modules in Python platlib {}: {}".format(
                temp_root, exc
            ))

    @staticmethod
    def _uses_readonly_hnp_runtime(python):
        public_home = os.environ.get("HNP_PUBLIC_HOME")
        if not public_home:
            return False
        probe = subprocess.run(
            [python, "-c", "import os,sysconfig; print(os.path.realpath(sysconfig.get_path('platlib') or ''))"],
            capture_output=True, text=True, check=True,
        )
        platlib = probe.stdout.strip()
        public_home = os.path.realpath(public_home)
        return bool(platlib and (platlib == public_home or platlib.startswith(public_home + os.sep)))

    @staticmethod
    def _is_native_loader_denial(detail):
        lower = detail.lower()
        permission_error = "permission denied" in lower or "operation not permitted" in lower
        return permission_error and ".so" in lower

    def _verify_extensions_static(self, package_build, python_abi):
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        if not readelf:
            raise ConanException("E212 fallback requires llvm-readelf or readelf")
        checked = 0
        for module in self._extensions:
            paths = glob.glob(os.path.join(package_build, module + ".*.so"))
            if len(paths) != 1:
                raise ConanException("expected one {} extension, found {}".format(module, len(paths)))
            path = paths[0]
            suffix = os.path.basename(path)
            if "cpython-{}".format(python_abi.replace(".", "")) not in suffix:
                raise ConanException("{} does not match CPython {} ABI: {}".format(module, python_abi, suffix))
            with open(path, "rb") as stream:
                if stream.read(4) != b"\x7fELF":
                    raise ConanException("{} is not an ELF shared object".format(path))
            result = subprocess.run(
                [readelf, "-h", "--dyn-syms", path], capture_output=True, text=True
            )
            if result.returncode:
                raise ConanException("readelf failed for {}: {}".format(path, result.stderr.strip()))
            if "AArch64" not in result.stdout or not re.search(
                r"\bPyInit_{}\b".format(re.escape(module)), result.stdout
            ):
                raise ConanException("{} has wrong architecture or missing PyInit entry point".format(path))
            checked += 1
        self.output.info("STATIC_EXTENSION_CHECKS: PASS={}/{}".format(checked, len(self._extensions)))

    def package(self):
        site_packages = os.path.join(
            self.package_folder, "lib", "python{}".format(self.options.python_abi), "site-packages"
        )
        os.makedirs(site_packages, exist_ok=True)
        shutil.copytree(
            os.path.join(self.build_folder, "python", "libscrc"),
            os.path.join(site_packages, "libscrc"),
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )

    def package_info(self):
        site_packages = os.path.join(
            self.package_folder, "lib", "python{}".format(self.options.python_abi), "site-packages"
        )
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PYTHONPATH", site_packages)
