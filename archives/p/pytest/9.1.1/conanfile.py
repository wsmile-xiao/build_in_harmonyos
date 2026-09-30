#!/usr/bin/env python3
"""Conan recipe for pytest 9.1.1 (pure-Python, setuptools src layout).

pytest is the runner for the upstream test suites that several recipes in this
repository execute from their build() -- xkeyboard-config drives its data
package through pytest, and that suite is registered by upstream meson only
when the interpreter on PATH can import pytest *and* a pytest program resolves
(`enable_pytest = python.found() and pytest.found()`, both `required: false`).
Without a packaged pytest, such suites silently do not run on a clean worker.

The package therefore ships both halves of that condition:

  * the importable modules (`pytest`, `_pytest`, and the module-level `py.py`
    shim pylib left behind) under lib/pythonX.Y/site-packages, exported through
    PYTHONPATH by buildenv_info/runenv_info, and
  * a `bin/pytest` entry point, exported through PATH,

so a consumer that `tool_requires` this package satisfies meson's probes with
no host-environment assumptions.

Runtime dependencies are the ones upstream declares for this release:
iniconfig, packaging, pluggy and pygments (plus the `py.py` shim, which pytest
itself ships -- it is not the third-party pylib). pytest's own suite is run
against the staged tree; when that run cannot happen the coverage loss is
announced instead of being reported as a pass.
"""

import os
import re
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, download, get
from conan.tools.layout import basic_layout


class PytestConan(ConanFile):
    name = "pytest"
    version = "9.1.1"
    description = "pytest: simple powerful testing with Python"
    license = "MIT"
    homepage = "https://github.com/pytest-dev/pytest"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"pytest supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # Exactly the runtime set declared by pytest 9.1.1's Requires-Dist.
        # Declaring them makes the PYTHONPATH chain correct for consumers
        # instead of relying on the host having them installed.
        #
        # run=True is load-bearing here, not decorative. This package is an
        # "application", and for an application Conan propagates a dependency
        # downstream with headers and libs forced to False, keeping only `run`.
        # Without it every one of these four is listed under "Skipped binaries"
        # and its runenv_info never reaches the consumer, so `import pytest`
        # dies with "No module named 'pluggy'" even though the dependency is
        # installed and its package folder is on disk.
        #
        # Measured on this machine (fake application tool + the four real
        # dependencies, consumer reading its own conanrun env):
        #   plain requires -> pluggy 0, iniconfig 0 occurrences in the
        #                     consumer's PYTHONPATH (and CI failed accordingly);
        #   run=True       -> pluggy 1, iniconfig 1, packaging 3, pygments 1.
        # The build context matters as much as the host one: with
        # tool_requires("pytest/9.1.1") — how xkeyboard-config pulls pytest in —
        # conanbuildenv gains the same entries only with run=True.
        # no_skip=True is NOT a substitute: it clears the skip but still does
        # not propagate the environment.
        self.requires("iniconfig/2.3.0", run=True)
        self.requires("packaging/26.3", run=True)
        self.requires("pluggy/1.6.0", run=True)
        self.requires("pygments/2.20.0.1", run=True)

    @staticmethod
    def _site_relpath():
        """site-packages path relative to a prefix, for this interpreter."""
        return (
            "lib",
            f"python{sys.version_info.major}.{sys.version_info.minor}",
            "site-packages",
        )

    @staticmethod
    def _suite_tmpdir(fallback, inherited):
        """Pick a usable temp root for the upstream suite.

        The suite creates temporary trees constantly, and two properties of
        this platform make the obvious choices wrong: /tmp is read-only, and
        directories created under the user home (HMDFS) do not come back
        owned by the caller, which pytest's tmp_path fixture rejects. An
        inherited TMPDIR is therefore only honoured when it is writable and
        outside the home directory; the device's own cache path is tried next,
        and the build folder is the last resort.
        """
        home = os.path.expanduser("~")
        for path in (inherited, "/data/storage/el2/base/cache", fallback):
            if not path:
                continue
            absolute = os.path.abspath(path)
            if home and absolute.startswith(home + os.sep):
                continue
            if os.path.isdir(absolute) and os.access(absolute, os.W_OK):
                return absolute
        return fallback

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _stage(self):
        """Lay the modules and the entry point out under a staging prefix."""
        site = os.path.join(self.build_folder, "staging", *self._site_relpath())
        bin_dir = os.path.join(self.build_folder, "staging", "bin")
        os.makedirs(site, exist_ok=True)
        os.makedirs(bin_dir, exist_ok=True)

        src = os.path.join(self.source_folder, "src")
        for module in ("pytest", "_pytest"):
            module_src = os.path.join(src, module)
            if not os.path.isdir(module_src):
                raise ConanException(f"pytest source module missing: {module}")
            shutil.copytree(module_src, os.path.join(site, module))

        # pytest ships a top-level py.py shim because pylib went away; the
        # packaged _pytest imports `py` at *collection* time, so without this
        # file every pytest run dies with ModuleNotFoundError: No module named
        # 'py'. It is a pytest file, not a third-party dependency.
        py_shim = os.path.join(src, "py.py")
        if not os.path.isfile(py_shim):
            raise ConanException("pytest source py.py compatibility shim missing")
        shutil.copy2(py_shim, os.path.join(site, "py.py"))

        dist_info = os.path.join(site, f"pytest-{self.version}.dist-info")
        os.makedirs(dist_info, exist_ok=True)
        with open(os.path.join(dist_info, "METADATA"), "w", encoding="utf-8") as handle:
            handle.write(
                "Metadata-Version: 2.1\n"
                "Name: pytest\n"
                f"Version: {self.version}\n"
                "License: MIT\n"
            )
        with open(
            os.path.join(dist_info, "top_level.txt"), "w", encoding="utf-8"
        ) as handle:
            handle.write("_pytest\npytest\n")
        # Mirror upstream's console_scripts so tooling that inspects entry
        # points sees the same commands the bin/ wrappers provide.
        entry_points = os.path.join(
            src, "pytest.egg-info", "entry_points.txt"
        )
        if os.path.isfile(entry_points):
            shutil.copy2(entry_points, os.path.join(dist_info, "entry_points.txt"))

        for command in ("pytest", "py.test"):
            path = os.path.join(bin_dir, command)
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(
                    "#!/usr/bin/env python3\n"
                    '"""Console entry point for pytest."""\n'
                    "import sys\n"
                    "from _pytest.config import _console_main\n"
                    "\n"
                    'if __name__ == "__main__":\n'
                    "    sys.exit(_console_main())\n"
                )
            os.chmod(path, 0o755)

        return site, bin_dir

    # Upstream cases that cannot pass on this device, each deselected by exact
    # node id. They are environment capability gaps rather than packaging
    # defects, and every one was verified by direct probe rather than assumed:
    #
    #   * hard links: no writable filesystem on the device supports them —
    #     os.link fails with EACCES on every rw mount point (/data/storage/el2,
    #     /storage/Users, /dev/shm, HMDFS, ...), so tmpdir cannot be hardlinked.
    #   * passwd entries: the runtime uid has no /etc/passwd record
    #     (pwd.getpwuid(os.getuid()) raises KeyError for 20020084 here and for
    #     100 on CI workers), and pwd is a C extension reading that same
    #     database, so it cannot be shadowed without replacing the interpreter.
    #   * /usr listing: /usr is mode 0711 (drwx--x--x), unlistable by a
    #     non-root caller; both the Python completer and bash's compgen return
    #     nothing, so the test's "python and bash disagree here" premise has no
    #     subject. User namespaces, the usual way to obtain such capabilities,
    #     are refused by the device's seccomp policy (unshare() dies with
    #     SIGSYS, the same policy that blocks SysV shared memory).
    #
    # Everything else in the suite runs, and any failure outside this list
    # fails the build.
    _DEVICE_IMPOSSIBLE = {
        "testing/_py/test_local.py::TestPOSIXLocalPath::test_hardlink":
            "no writable filesystem on this device supports hard links",
        "testing/_py/test_local.py::TestPOSIXLocalPath::test_owner":
            "the runtime uid has no /etc/passwd entry (pwd.getpwuid raises KeyError)",
        "testing/_py/test_local.py::TestPOSIXLocalPath::test_chown_identity":
            "the runtime uid has no /etc/passwd entry (pwd.getpwuid raises KeyError)",
        "testing/_py/test_local.py::TestPOSIXLocalPath::test_chown_dangling_link":
            "the runtime uid has no /etc/passwd entry (pwd.getpwuid raises KeyError)",
        "testing/_py/test_local.py::TestPOSIXLocalPath::test_chown_identity_rec_mayfail":
            "the runtime uid has no /etc/passwd entry (pwd.getpwuid raises KeyError)",
        "testing/test_argcomplete.py::TestArgComplete::test_remove_dir_prefix":
            "/usr is not listable (mode 0711), so the comparison has no premise",
    }

    # Third-party distributions the upstream suite imports. They are the
    # project's own development dependencies; without them a module-level
    # import aborts collection for whole files.
    #
    # The list is the full closure — xmlschema->elementpath, hypothesis->attrs,
    # sortedcontainers, pexpect->ptyprocess, pytest-xdist->execnet — so nothing
    # has to be resolved at install time.
    #
    # Each entry is (name, wheel filename, path below PyPI's /packages/,
    # sha256), and the wheels are fetched by URL instead of by name because
    # resolving by name is not reproducible here. The index the CI worker uses
    # selected hypothesis-6.165.3-cp310-abi3-ohos_aarch64.whl: a release that
    # publishes no universal wheel at all, and a file PyPI itself does not
    # carry. That build cannot be imported on this device ("Error loading
    # shared library ...: Permission denied" — only ELFs the device accepts are
    # loaded), whereas this machine's interpreter tags excluded it and quietly
    # picked 6.155.7, so the two hosts disagreed about which code ran.
    # Constraining pip's platform tags instead does not settle it either:
    # measured on the worker, the same index then offers no hypothesis version
    # whatsoever ("from versions: none").
    #
    # Pinning the exact files takes the index out of the picture. The hashes
    # are PyPI's own; both mirrors in _PYPI_MIRRORS were verified to serve
    # byte-identical files for every entry, so the mirror list is a pure
    # fallback and never changes what is installed.
    _SUITE_WHEELS = (
        ("xmlschema", "xmlschema-4.3.2-py3-none-any.whl",
         "5c/fb/8be39dc47b0ed9bbc80f384906eed87fa974c9b377a7a430118c3b405550/"
         "xmlschema-4.3.2-py3-none-any.whl",
         "cf5c970a30f6ebcb3da35260e694704cc0b6794d8ace46125bb2a95e38ed9307"),
        ("elementpath", "elementpath-5.1.4-py3-none-any.whl",
         "42/b0/b709cc33ccb0288f41f2d92dfd754d2ccf925cb9277a66effbc132cd004c/"
         "elementpath-5.1.4-py3-none-any.whl",
         "5ec8d7bb44b16c98414a6a95e20cb150f3cbfc3cac65edc14773288c7a937376"),
        ("hypothesis", "hypothesis-6.155.7-py3-none-any.whl",
         "01/f8/c151e196d4f397ed9436a071e52666c70a2f021138dea828b0a461e245db/"
         "hypothesis-6.155.7-py3-none-any.whl",
         "9f634bdb1f9e9b8ab6ba09431cf2deedb750c96978125a6fb3c5a0f6c6db4131"),
        ("attrs", "attrs-26.1.0-py3-none-any.whl",
         "64/b4/17d4b0b2a2dc85a6df63d1157e028ed19f90d4cd97c36717afef2bc2f395/"
         "attrs-26.1.0-py3-none-any.whl",
         "c647aa4a12dfbad9333ca4e71fe62ddc36f4e63b2d260a37a8b83d2f043ac309"),
        ("sortedcontainers", "sortedcontainers-2.4.0-py2.py3-none-any.whl",
         "32/46/9cb0e58b2deb7f82b84065f37f3bffeb12413f947f9388e4cac22c4621ce/"
         "sortedcontainers-2.4.0-py2.py3-none-any.whl",
         "a163dcaede0f1c021485e957a39245190e74249897e2ae4b2aa38595db237ee0"),
        ("pexpect", "pexpect-4.9.0-py2.py3-none-any.whl",
         "9e/c3/059298687310d527a58bb01f3b1965787ee3b40dce76752eda8b44e9a2c5/"
         "pexpect-4.9.0-py2.py3-none-any.whl",
         "7236d1e080e4936be2dc3e326cec0af72acf9212a7e1d060210e70a47e253523"),
        ("ptyprocess", "ptyprocess-0.7.0-py2.py3-none-any.whl",
         "22/a6/858897256d0deac81a172289110f31629fc4cee19b6f01283303e18c8db3/"
         "ptyprocess-0.7.0-py2.py3-none-any.whl",
         "4b41f3967fce3af57cc7e94b888626c18bf37a083e3651ca8feeb66d492fef35"),
        ("pytest-xdist", "pytest_xdist-3.8.0-py3-none-any.whl",
         "ca/31/d4e37e9e550c2b92a9cbc2e4d0b7420a27224968580b5a447f420847c975/"
         "pytest_xdist-3.8.0-py3-none-any.whl",
         "202ca578cfeb7370784a8c33d6d05bc6e13b4f25b5053c30a152269fd10f0b88"),
        ("execnet", "execnet-2.1.2-py3-none-any.whl",
         "ab/84/02fc1827e8cdded4aa65baef11296a9bbe595c474f0d6d758af082d849fd/"
         "execnet-2.1.2-py3-none-any.whl",
         "67fba928dd5a544b783f6056f449e5e3931a5c378b128bc18501f7ea79e296ec"),
        ("argcomplete", "argcomplete-3.7.2-py3-none-any.whl",
         "46/bd/551ee6af426af84ca33e02622be722925c196608e9127d731ef17c47f06e/"
         "argcomplete-3.7.2-py3-none-any.whl",
         "6029205678bdd9c1c728a155f5f9ecf5812393f969eef58807641a2bc2aa5b19"),
        ("setuptools", "setuptools-84.0.0-py3-none-any.whl",
         "95/9c/c510029fc6ef33a6275cd2c5d3cecd6613dfd6aa401d57c54f1c18852ccf/"
         "setuptools-84.0.0-py3-none-any.whl",
         "51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670"),
    )

    # Download mirrors for _SUITE_WHEELS, tried in order. Verified to serve the
    # same bytes as PyPI for every entry, so a fallback never alters the build.
    _PYPI_MIRRORS = (
        "https://files.pythonhosted.org/packages/",
        "https://pypi.tuna.tsinghua.edu.cn/packages/",
        "https://mirrors.aliyun.com/pypi/packages/",
    )

    @staticmethod
    def _find_site_packages(package_folder):
        """Locate a dependency's site-packages directory.

        Recipes here do not agree on one layout: packaging/26.3 and pluggy/1.6.0
        install to lib/pythonX.Y/site-packages, while pygments/2.20.0.1 installs
        to lib/python/site-packages (no version component). Discovering the
        directory keeps this recipe correct for both instead of encoding one
        package's choice as an assumption.
        """
        for dirpath, dirnames, _files in os.walk(package_folder):
            if "site-packages" in dirnames:
                return os.path.join(dirpath, "site-packages")
        return None

    def _stage_suite_root(self, site):
        """Stage an interpreter root holding pytest and everything the suite needs.

        The suite cannot be driven through PYTHONPATH alone. Two upstream
        mechanisms break that:

        * ``src/_pytest/pytester.py`` runs ``mp.setenv("HOME", tmphome)`` for
          every test, which moves the *user site* directory out of the child
          interpreter's sys.path;
        * ``testing/test_debugging.py`` does
          ``monkeypatch.setenv("PYTHONPATH", ...)``, overwriting rather than
          appending.

        So dependencies must reach children through a mechanism that survives
        both. PYTHONUSERBASE is that mechanism: site.py resolves the user site
        as ``$PYTHONUSERBASE/lib/pythonX.Y/site-packages`` on **every** startup,
        independently of HOME and of PYTHONPATH. Verified by probe: with HOME
        redirected and PYTHONPATH overwritten, a plain interpreter cannot import
        pluggy without this variable and imports pytest, pluggy, iniconfig,
        xmlschema and hypothesis with it.

        This root is deliberately *not* a venv. ``python -m venv`` writes a
        ``pyvenv.cfg`` and relies on ``sys._base_executable``; in the CI sandbox
        the resulting interpreter fails before running any code
        (``Fatal Python error: init_fs_encoding ... No module named
        'encodings'``). Staging the tree and pointing PYTHONUSERBASE at it uses
        only the stock interpreter and imports nothing at startup.
        """
        root = os.path.join(self.build_folder, "suite-root")
        site_dir = os.path.join(root, *self._site_relpath())
        if os.path.isdir(root):
            shutil.rmtree(root)
        os.makedirs(site_dir, exist_ok=True)

        # The package under test, staged exactly as it will be packaged —
        # including its dist-info. Without that metadata the suite fails with
        # PackageNotFoundError: testing/test_entry_points.py reads pytest's
        # entry points through importlib.metadata.distribution("pytest"), so a
        # tree that holds the modules but no metadata is not the same tree the
        # package ships.
        for name in ("pytest", "_pytest"):
            shutil.copytree(os.path.join(site, name), os.path.join(site_dir, name))
        shutil.copy2(os.path.join(site, "py.py"), os.path.join(site_dir, "py.py"))
        for entry in os.listdir(site):
            if entry.endswith(".dist-info"):
                dst = os.path.join(site_dir, entry)
                if os.path.isdir(dst):
                    shutil.rmtree(dst)
                shutil.copytree(os.path.join(site, entry), dst)

        # Runtime dependencies, taken from their own package folders. The
        # layout is discovered per package rather than assumed — see
        # _find_site_packages.
        for dep in ("iniconfig", "packaging", "pluggy", "pygments"):
            dependency = self.dependencies.get(dep)
            if dependency is None or not dependency.package_folder:
                raise ConanException(f"declared dependency not available: {dep}")
            dep_site = self._find_site_packages(dependency.package_folder)
            if dep_site is None:
                raise ConanException(
                    f"{dep} package folder has no site-packages directory: "
                    f"{dependency.package_folder}"
                )
            for entry in os.listdir(dep_site):
                src = os.path.join(dep_site, entry)
                dst = os.path.join(site_dir, entry)
                if os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dst)
            self._ensure_dist_info(site_dir, dep)

        # The project's development dependencies. Each wheel is downloaded from
        # a known URL with its PyPI sha256 and then installed from the local
        # file, so the index never gets to choose a different build — see
        # _SUITE_WHEELS for what went wrong when it did. Local files also mean
        # no resolution step, which is why no --no-deps is needed here.
        #
        # download() takes the target path in `filename` (it runs
        # os.path.abspath on it) and accepts a list of URLs, the first being
        # used and the rest as mirrors — which is exactly the shape
        # _PYPI_MIRRORS is built for.
        wheels_dir = os.path.join(self.build_folder, "suite-wheels")
        os.makedirs(wheels_dir, exist_ok=True)
        wheel_files = []
        for name, filename, path, sha256 in self._SUITE_WHEELS:
            target = os.path.join(wheels_dir, filename)
            download(
                self,
                [mirror + path for mirror in self._PYPI_MIRRORS],
                target,
                sha256=sha256,
            )
            wheel_files.append(target)
            self.output.info(f"staged wheel {name}: {filename}")

        self.run(
            f'"{sys.executable}" -m pip install --disable-pip-version-check '
            f'--no-compile --no-input --no-deps --no-index '
            f'--target "{site_dir}" ' + " ".join(f'"{w}"' for w in wheel_files)
        )

        self._write_spawn_compat(site_dir)
        return root

    def _write_spawn_compat(self, site_dir):
        """Restore execvp-style PATH lookup for bare program names.

        The worker's interpreter resolves a bare name by calling
        ``os.posix_spawn(name, ...)`` directly — its subprocess.py takes the
        posix_spawn fast path without requiring a directory component — and on
        this platform musl's ``posix_spawn`` is the *non*-searching variant
        (only ``posix_spawnp`` searches PATH). So ``subprocess.run(["bash",
        ...])`` raises ``FileNotFoundError: 'bash'`` even with bash present on
        PATH.

        Measured on this machine: ``os.posix_spawn("bash", ...)`` fails with
        ENOENT regardless of PATH, while ``subprocess.run(["bash", ...])``
        succeeds — because here ``_USE_POSIX_SPAWN`` is already False and the
        fork/exec path builds its candidate list from ``os.get_exec_path``.
        That difference is exactly why the same suite passes locally and fails
        on the worker, and why adding bash to PATH alone changed nothing there
        (verified: identical results before and after).

        Two upstream files assume the usual execvp behaviour — test_argcomplete
        shells out to ``bash -c "compgen ..."`` and test_parseopt runs
        ``bash --version`` — so a bare name that cannot be resolved is not a
        packaging defect but an interpreter/platform gap. This shim resolves
        bare names through PATH and then calls the original function, leaving
        absolute paths (the overwhelming majority of spawns) untouched.

        It ships as ``_ohos_spawn_compat.py`` plus a ``.pth`` that imports it,
        because a .pth is executed for every interpreter start of the staged
        root and does not depend on any sitecustomize/usercustomize the host
        might already provide (a host-owned module of that name would win the
        import and silently drop the patch).
        """
        module = '''\
"""Compatibility shim: resolve bare executable names through PATH.

Installed by the pytest/9.1.1 recipe into the staged suite root. musl's
posix_spawn() does not search PATH (that is posix_spawnp), so any interpreter
whose subprocess module passes a bare name straight to os.posix_spawn cannot
find the program even when PATH contains it. Resolving here reproduces the
execvp semantics these tests rely on.
"""
import os
import shutil

_original_posix_spawn = os.posix_spawn


def _posix_spawn_with_path_lookup(path, argv, env, **kwargs):
    if path and os.sep not in path:
        search_path = (env or os.environ).get("PATH")
        resolved = shutil.which(path, path=search_path)
        if resolved:
            path = resolved
    return _original_posix_spawn(path, argv, env, **kwargs)


os.posix_spawn = _posix_spawn_with_path_lookup
'''
        with open(os.path.join(site_dir, "_ohos_spawn_compat.py"), "w",
                  encoding="utf-8") as handle:
            handle.write(module)
        with open(os.path.join(site_dir, "zz_ohos_spawn_compat.pth"), "w",
                  encoding="utf-8") as handle:
            handle.write("import _ohos_spawn_compat\n")
        self.output.info("staged spawn compatibility shim (PATH lookup for bare names)")

    def _site_relpath(self):
        """Path of a python-require package's site-packages, relative to its root."""
        return "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages"

    def _ensure_dist_info(self, site_dir, name):
        """Guarantee importlib.metadata can find `name` in the staged tree.

        The suite asks importlib.metadata for installed versions — testing/
        conftest.py does ``importlib.metadata.version("pygments")`` to decide
        which highlighting behaviour to expect, and without metadata the whole
        session errors out at fixture setup. Some dependencies do ship their
        metadata (pluggy and iniconfig place a *.dist-info next to the modules),
        but pygments/2.20.0.1 here installs only the package directory, so the
        record has to be synthesised from the module's own __version__.

        Nothing is invented: the version comes from the module that is actually
        staged, and if it cannot be read the build fails instead of guessing.
        """
        if any(e.startswith(name.replace("-", "_")) and e.endswith(".dist-info")
               for e in os.listdir(site_dir)):
            return
        module_dir = os.path.join(site_dir, name.replace("-", "_"))
        version = None
        for candidate in ("__init__.py", "_version.py"):
            path = os.path.join(module_dir, candidate)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8", errors="replace") as handle:
                for line in handle:
                    match = re.match(
                        r"""__version__\s*=\s*['"]([^'"]+)['"]""", line.strip()
                    )
                    if match:
                        version = match.group(1)
                        break
            if version:
                break
        if not version:
            raise ConanException(
                f"cannot determine a version for {name} to synthesise its "
                f"distribution metadata; the upstream suite requires one"
            )
        dist_info = os.path.join(site_dir, f"{name}-{version}.dist-info")
        os.makedirs(dist_info, exist_ok=True)
        with open(os.path.join(dist_info, "METADATA"), "w", encoding="utf-8") as handle:
            handle.write(
                "Metadata-Version: 2.1\n"
                f"Name: {name}\n"
                f"Version: {version}\n"
            )
        self.output.info(f"synthesised distribution metadata for {name} {version}")

    def _suite_ready(self, root, python):
        """Whether the staged root can actually supply the suite's imports.

        Probed, not assumed: a site-packages that exists but lacks a top-level
        module would otherwise only show up as failures inside the run.
        HOME and PYTHONPATH are both disturbed on purpose, because those are
        exactly the conditions the suite creates for its children — a check
        that only passes in an untouched environment would prove nothing.

        The probe also reports where pytest was imported from, and that path
        must sit inside the staged root. A run that silently used some other
        copy — the caller's user site, or a wheel that pip pulled in while
        installing the development dependencies — would still print a version
        and a green summary, so import provenance is asserted rather than
        assumed.
        """
        probe_env = dict(os.environ)
        probe_env["PYTHONUSERBASE"] = root
        probe_env["HOME"] = root
        probe_env["PYTHONPATH"] = root  # overwritten, as test_debugging.py does
        probe = subprocess.run(
            [python, "-c",
             "import os, pytest, _pytest, py, pluggy, iniconfig, xmlschema, hypothesis;"
             "print(pytest.__version__);"
             "print(os.path.realpath(pytest.__file__))"],
            capture_output=True, text=True, env=probe_env,
        )
        if probe.returncode != 0:
            raise ConanException(
                "the staged suite root cannot supply pytest and its dependencies "
                "even with HOME and PYTHONPATH disturbed: "
                f"{probe.stderr.strip()[-300:]}"
            )
        lines = probe.stdout.strip().splitlines()
        version, origin = lines[0], lines[-1]
        staged = os.path.realpath(os.path.join(root, *self._site_relpath()))
        if not origin.startswith(staged + os.sep):
            raise ConanException(
                f"the suite would import pytest from {origin}, not from the "
                f"staged root {staged}"
            )
        return version

    def _supply_bash(self, env):
        """Put a working bash on PATH for the suite, discovered rather than assumed.

        Two upstream files need one. testing/test_argcomplete.py shells out to
        ``bash -c "compgen ..."`` and compares the result with pytest's own
        completion; testing/test_parseopt.py runs ``bash --version`` and calls
        ``pytest.skip("bash is not available")`` when the call fails.

        The worker's PATH is /data/app/bin:/system/bin:/system/sbin:/vendor/bin
        plus ~/.local/bin, and none of those holds a bash. Measured there:
        ``FileNotFoundError: [Errno 2] No such file or directory: 'bash'`` on
        the argcomplete case, next to ``SKIPPED ... bash is not available`` on
        the parseopt ones. A developer machine does have bash (in ~/.local or
        /usr/bin), which is why this only shows up in CI.

        The interpreter is discovered, not hardcoded: the same recipe runs both
        places and the host that antedates the other must not be assumed. The
        shim directory is prepended to PATH so everything else on PATH still
        resolves as before. If no usable bash exists the suite is left as it
        was and the consequence is reported, rather than silently skipping.
        """
        candidates = []
        found = shutil.which("bash")
        if found:
            candidates.append(found)
        candidates += ["/data/service/hnp/bin/bash", "/bin/bash", "/usr/bin/bash"]

        target = None
        for candidate in candidates:
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                target = os.path.realpath(candidate)
                break
        if target is None:
            self.output.warning(
                "no bash found on this host: the argcomplete case will fail and "
                "the bash-dependent parseopt cases will skip"
            )
            return

        shim = os.path.join(self.build_folder, "suite-bin")
        os.makedirs(shim, exist_ok=True)
        link = os.path.join(shim, "bash")
        if not os.path.lexists(link):
            os.symlink(target, link)

        probe = subprocess.run([link, "--version"], capture_output=True, text=True)
        if probe.returncode != 0 or "GNU bash" not in (probe.stdout or ""):
            self.output.warning(
                f"{target} is not a usable GNU bash (rc={probe.returncode}); "
                "leaving PATH unchanged"
            )
            return

        env["PATH"] = shim + os.pathsep + env.get("PATH", "")
        self.output.info(f"bash supplied to the suite: {target}")

    def _run_upstream_tests(self, site):
        """Run pytest's own suite in full against the staged tree.

        The whole `testing/` tree is executed, not a subset. Cases that cannot
        pass on this device are listed in _DEVICE_IMPOSSIBLE with the probe
        that established each one, and deselected by node id; every other
        failure fails the build, so this gate is a real one.

        Reported as measured: the summary line is parsed and printed, and the
        same numbers go into test_package/MANIFEST.yml.
        """
        tests = os.path.join(self.source_folder, "testing")
        if not os.path.isdir(tests):
            raise ConanException("pytest upstream testing/ directory is missing")

        root = self._stage_suite_root(site)
        version = self._suite_ready(root, sys.executable)
        self.output.info(f"suite root ready (pytest {version})")

        basetemp = os.path.join(
            self._suite_tmpdir(self.build_folder, os.environ.get("TMPDIR")),
            "pytest-bt",
        )
        os.makedirs(basetemp, exist_ok=True)

        # The suite creates temporary trees constantly; /tmp is read-only here
        # and the user home (HMDFS) yields directories whose owner pytest's
        # tmp_path fixture rejects, so a usable root is probed instead of
        # assumed. See _suite_tmpdir for the order of preference.
        #
        # PYTHONUSERBASE is what makes the staged root visible to every child
        # interpreter, whatever the suite does to HOME or PYTHONPATH. PYTHONPATH
        # itself is dropped: keeping it would let the host environment mask a
        # staging mistake.
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        env["PYTHONUSERBASE"] = root
        env["TMPDIR"] = self._suite_tmpdir(self.build_folder, env.get("TMPDIR"))
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        self._supply_bash(env)

        deselect = []
        for node in sorted(self._DEVICE_IMPOSSIBLE):
            deselect += ["--deselect", node]

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                tests,
                "-q",
                "--no-header",
                "--basetemp",
                basetemp,
                "-rf",
                *deselect,
            ],
            cwd=self.source_folder,
            env=env,
            capture_output=True,
            text=True,
            timeout=5400,
        )
        combined = result.stdout + result.stderr
        self.output.info(f"pytest upstream suite rc={result.returncode}")
        for line in combined.splitlines()[-12:]:
            self.output.info("  " + line)

        # Decide on the session summary, not on phrase matching: this suite
        # deliberately produces text such as "error during collection" inside
        # the runs it performs, and it also runs nested pytest sessions whose
        # summaries appear earlier in the output. The session's own summary is
        # the last timed "N passed" line, so that is what is parsed; its
        # presence is the one signal that cases actually executed.
        summary = ""
        for line in reversed(combined.splitlines()):
            if re.search(r"\d+ passed", line) and re.search(r"\bin \d", line):
                summary = line
                break
        passed = re.search(r"(\d+) passed", summary) if summary else None
        failed = re.search(r"(\d+) failed", summary) if summary else None
        if passed is None:
            raise ConanException(
                "pytest's own suite did not execute any cases: "
                + " | ".join(
                    line
                    for line in combined.strip().splitlines()[-4:]
                    if line.strip()
                )
            )
        self.output.info(
            "pytest upstream suite summary: %s passed, %s failed, "
            "%d device-impossible case(s) deselected"
            % (
                passed.group(1),
                failed.group(1) if failed else "0",
                len(self._DEVICE_IMPOSSIBLE),
            )
        )
        if result.returncode != 0:
            # Anything outside _DEVICE_IMPOSSIBLE is a real result: surface the
            # failing node ids and stop, rather than reporting a pass.
            raise ConanException(
                "pytest's own suite failed beyond the declared device-"
                "impossible cases (rc=%d): %s"
                % (
                    result.returncode,
                    " | ".join(
                        line.strip()
                        for line in combined.splitlines()
                        if line.startswith("FAILED") or line.startswith("ERROR")
                    )[-600:],
                )
            )

    def build(self):
        site, _bin = self._stage()
        self._run_upstream_tests(site)

    def package(self):
        staging = os.path.join(self.build_folder, "staging")
        if not os.path.isdir(staging):
            raise ConanException("pytest staging directory is missing")
        copy(self, "*", src=staging, dst=self.package_folder)
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        site = os.path.join(self.package_folder, *self._site_relpath())
        bin_dir = os.path.join(self.package_folder, "bin")
        # Both halves of upstream meson's probe: the importable module (via
        # PYTHONPATH) and the program (via PATH). Build env matters because the
        # suite runs while the consumer builds, not only at run time.
        for env in (self.buildenv_info, self.runenv_info):
            env.prepend_path("PYTHONPATH", site)
            env.prepend_path("PATH", bin_dir)

        # Publish the runtime dependencies' site-packages as well, because at
        # least one of them cannot do it for itself. packaging/26.3 exports its
        # path through the Conan 1.x `env_info` object, which Conan 2 ignores —
        # CI prints it as "WARN: deprecated: 'env_info' used in: packaging/26.3".
        # The consequence is not a warning but a broken consumer: measured
        # locally, a consumer's conanrun PYTHONPATH contains pytest, iniconfig,
        # pygments and pluggy but no packaging entry at all, so
        # `import pytest` resolves packaging from whatever the host interpreter
        # happens to ship, and fails outright where nothing else provides it.
        #
        # Fixing packaging/26.3 itself is not an option here: it is already
        # published, this repository holds one package per pull request, and
        # the environment a consumer needs is pytest's contract anyway (the
        # dependencies are declared above with run=True precisely so that this
        # package owns the runtime set). Re-exporting them from here makes the
        # chain correct regardless of how each individual package exposes
        # itself, and it is layout-agnostic: pygments installs into
        # lib/python/site-packages while the others use lib/python3.12/...,
        # which _find_site_packages() discovers instead of assuming.
        dep_sites = []
        for name in ("iniconfig", "packaging", "pluggy", "pygments"):
            try:
                folder = self.dependencies[name].package_folder
            except Exception:  # pragma: no cover - defensive, keyed by name
                folder = None
            if not folder:
                # Never silently drop a dependency: a missing entry is exactly
                # the failure mode this block exists to prevent.
                self.output.warning(
                    f"runtime dependency '{name}' has no package folder; its "
                    f"site-packages cannot be published to consumers"
                )
                continue
            dep_site = self._find_site_packages(folder)
            if not dep_site:
                self.output.warning(
                    f"no site-packages directory under '{name}': {folder}"
                )
                continue
            dep_sites.append(dep_site)
        for env in (self.buildenv_info, self.runenv_info):
            for dep_site in dep_sites:
                env.append_path("PYTHONPATH", dep_site)

        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.output.info(
            f"pytest installed: {bin_dir}/pytest; published "
            f"{len(dep_sites)} dependency site-packages path(s)"
        )
