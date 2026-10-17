#!/usr/bin/env python3
"""Conan recipe for undertime — pick a meeting time across timezones.

Upstream: https://gitlab.com/anarcat/undertime (AGPL-3.0-or-later)

undertime is a pure Python 3 command-line program: the tool itself is the
`undertime` script (installed by setup.cfg `[options] scripts`). There is no
native compilation step.

HarmonyOS PC (aarch64) adaptation notes:
  * setuptools_scm derives the version from git tags and the release tarball is
    not a git checkout, so the version is supplied through
    SETUPTOOLS_SCM_PRETEND_VERSION instead of letting the build fail.
  * The upstream script carries a `#!/usr/bin/python3` shebang, which does not
    exist on this platform. The packaged copy gets a portable
    `#!/usr/bin/env python3` shebang plus a package-relative site-packages
    bootstrap so it runs standalone (the L2 smoke test executes it from a
    plain environment, with no conan runenv applied).
  * The pip runtime dependencies are vendored into the package (there is no
    conan package for pip distributions). Only pure-Python packages (or ones
    with a pure-Python fallback, like pyyaml) are vendored: the CI worker's
    HNP python runs in an AppSpawn sandbox that refuses to dlopen user-space
    C-extension .so files (verified: even a suffix-renamed ephem/regex .so
    fails with "Permission denied"), so `dateparser` (hard-depends on the
    `regex` C extension) and `ephem` (C extension) are NOT vendored. Upstream
    already imports `python-dateutil`; a source patch makes
    `parse_date_dateparser()` fall back to it when `dateparser` is missing,
    which keeps the whole upstream test suite green on the CI interpreter.
  * The upstream `moonphases` companion script depends on `ephem` (C
    extension), which cannot load in the OHOS CI sandbox; it is therefore not
    shipped in this package (documented in notes.md).
  * build() runs the real upstream pytest suite (R51).
"""
import os
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

# OpenHarmonyPC community PyPI mirror: also publishes the cp312 ohos_aarch64
# wheels required by the C-extension dependencies.
PYPI_MIRROR = "https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple"
PYPI_HOST = "pypi.cnb.cool"

# setup.cfg `install_requires` minus the C-extension packages; all of it is
# vendored into the package so the console script is self-contained.
#   * excluded: `dateparser` (hard-depends on `regex`, a C extension the CI
#     sandbox cannot dlopen) — parse_date falls back to python-dateutil via
#     patches/0001;
#   * excluded: `ephem` (C extension) — the `moonphases` companion that needs
#     it is not shipped;
#   * included: pyyaml (its `_yaml` C extension fails to load in CI but the
#     pure-Python parser fallback works), pytz, tabulate, tzlocal, tzdata,
#     python-dateutil.
# `tzdata` is not an upstream dependency: this platform ships no system
# /usr/share/zoneinfo, so the stdlib `zoneinfo` module (used by tzlocal) has
# no database to read without it.
RUNTIME_PKGS = [
    "pytz", "pyyaml", "termcolor", "tabulate", "tzlocal", "tzdata",
    "python-dateutil",
]

# Build/test tooling, kept in its own private target and never packaged.
# setuptools/wheel/setuptools_scm are the PEP 517 backend for the
# `--no-build-isolation` install below (the interpreter ships no setuptools).
BUILD_PKGS = [
    "setuptools", "wheel", "setuptools_scm",
    "pytest", "pytest-cov", "pytest-timeout",
]

# Console script shipped by this package. The upstream `moonphases` companion
# is excluded: it hard-depends on `ephem` (C extension), which cannot load in
# the OHOS CI sandbox (see module docstring).
SCRIPTS = ["undertime"]

# Injected right after the shebang of each packaged script: makes the vendored
# runtime dependencies importable without an external PYTHONPATH.
_SITE_BOOTSTRAP = (
    "import os as _os, sys as _sys\n"
    "_sys.path.insert(0, _os.path.join(\n"
    "    _os.path.dirname(_os.path.dirname(_os.path.realpath(__file__))),\n"
    '    "lib", "python%d.%d" % _sys.version_info[:2], "site-packages"))\n'
)


class UndertimeConan(ConanFile):
    name = "undertime"
    version = "4.3.1"
    description = ("Pick a meeting time across multiple timezones: prints an "
                   "aligned table of simultaneous local times.")
    license = "AGPL-3.0-or-later"
    homepage = "https://gitlab.com/anarcat/undertime"
    url = "https://gitlab.com/anarcat/undertime"

    # The product is a command-line tool => "application" (R38).
    package_type = "application"
    # L0p: all four settings declared.
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _py(self):
        return sys.executable or "python3"

    @staticmethod
    def _clean_env(extra=None):
        """Return an environment for pip.

        The ambient ``PIP_*`` overrides point every install at a shared target
        directory and force ``--only-binary``; left in place they conflict with
        the private ``--target``/``--prefix`` used here, so they are dropped
        before the explicit mirror flags are applied.
        """
        env = {k: v for k, v in os.environ.items() if not k.startswith("PIP_")}
        env["PIP_NO_INPUT"] = "1"
        env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
        if extra:
            env.update(extra)
        return env

    def _pip(self, args, extra_env=None):
        cmd = [self._py(), "-m", "pip", "install",
               "--index-url", PYPI_MIRROR,
               "--trusted-host", PYPI_HOST,
               "--no-input", "--no-compile"] + args
        self.output.info("pip: " + " ".join(cmd))
        subprocess.run(cmd, check=True, env=self._clean_env(extra_env))

    # ------------------------------------------------------------------ #
    def build(self):
        # R49: everything is staged inside the conan build folder; the shared
        # /usr/local prefix is never touched.
        prefix = os.path.join(self.build_folder, "prefix")
        deps_build = os.path.join(self.build_folder, "deps-build")
        deps_run = os.path.join(self.build_folder, "deps-run")
        for d in (prefix, deps_build, deps_run):
            os.makedirs(d, exist_ok=True)

        # 1) PEP 517 backend + test tooling into a private target.
        self._pip(["--target=" + deps_build] + BUILD_PKGS)

        # 2) Runtime dependencies into a private target. --only-binary keeps pip
        #    from attempting a source build of the C extensions: the mirror
        #    serves cp312 ohos_aarch64 wheels for ephem/pyyaml/regex.
        self._pip(["--only-binary=:all:", "--target=" + deps_run] + RUNTIME_PKGS)

        # 3) undertime itself into the private prefix (bin/ + dist-info + etc/).
        self._pip(
            ["--no-deps", "--no-build-isolation", "--prefix=" + prefix,
             self.source_folder],
            extra_env={
                "PYTHONPATH": deps_build,
                # setuptools_scm cannot read a version out of a tarball.
                "SETUPTOOLS_SCM_PRETEND_VERSION": str(self.version),
            },
        )

        # 4) Upstream test suite (R51).
        self._run_upstream_tests(deps_build, deps_run, prefix)

    def _run_upstream_tests(self, deps_build, deps_run, prefix):
        test_file = os.path.join(self.source_folder, "test_undertime.py")
        if not os.path.isfile(test_file):
            raise ConanException("upstream test_undertime.py not found (R51)")

        maj, minr = sys.version_info[:2]
        prefix_site = os.path.join(prefix, "lib", f"python{maj}.{minr}",
                                   "site-packages")

        env = self._clean_env()
        # tox.ini pins the suite to UTC ("test suite expects UTC"): several cases
        # assert absolute local times, so the zone must be fixed.
        env["TZ"] = "UTC"
        # prefix_site carries the installed dist-info; test_version resolves the
        # version through importlib.metadata.
        env["PYTHONPATH"] = os.pathsep.join(
            [self.source_folder, deps_build, deps_run, prefix_site])
        env["PATH"] = os.pathsep.join(
            [os.path.dirname(self._py()), env.get("PATH", "")])

        cmd = [self._py(), "-m", "pytest", "test_undertime.py",
               "-v", "--no-header", "--timeout=300", "--timeout-method=signal"]
        self.output.info("upstream pytest: " + " ".join(cmd))
        proc = subprocess.run(cmd, cwd=self.source_folder, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        out = proc.stdout.decode("utf-8", "replace")
        self.output.info(out)

        summary = ""
        for line in reversed(out.splitlines()):
            stripped = line.strip()
            if stripped and ("passed" in stripped or "failed" in stripped
                             or "error" in stripped):
                summary = stripped
                break
        self.output.info(f"UPSTREAM-PYTEST-SUMMARY: {summary or 'n/a'}")
        if proc.returncode != 0:
            failed = [ln.strip() for ln in out.splitlines()
                      if ln.strip().startswith(("FAILED ", "ERROR "))]
            for ln in failed:
                self.output.error("upstream pytest: " + ln)
            raise ConanException(
                "upstream pytest suite failed (exit {}): {}. Failing cases: {}"
                .format(proc.returncode, summary,
                        "; ".join(failed) if failed else "see log"))

    def package(self):
        maj, minr = sys.version_info[:2]
        stage_prefix = os.path.join(self.build_folder, "prefix")
        stage_site = os.path.join(stage_prefix, "lib",
                                  f"python{maj}.{minr}", "site-packages")
        deps_run = os.path.join(self.build_folder, "deps-run")

        pkg_bin = os.path.join(self.package_folder, "bin")
        pkg_site = os.path.join(self.package_folder, "lib",
                                f"python{maj}.{minr}", "site-packages")
        os.makedirs(pkg_bin, exist_ok=True)
        os.makedirs(pkg_site, exist_ok=True)

        # Console scripts: portable shebang + package-relative bootstrap.
        for name in SCRIPTS:
            src = os.path.join(stage_prefix, "bin", name)
            if not os.path.isfile(src):
                raise ConanException(f"expected console script missing: {src}")
            dst = os.path.join(pkg_bin, name)
            with open(src, encoding="utf-8") as fh:
                lines = fh.read().splitlines(True)
            lines[0] = "#!/usr/bin/env python3\n"
            lines.insert(1, _SITE_BOOTSTRAP)
            with open(dst, "w", encoding="utf-8") as fh:
                fh.write("".join(lines))
            os.chmod(dst, 0o755)

        # Distribution metadata: `undertime --version` reads it through
        # importlib.metadata, so the dist-info has to travel with the package.
        copy(self, "*", src=stage_site, dst=pkg_site)

        # Vendored runtime dependencies (skip the entry-point dirs of the
        # dependencies themselves — only their importable packages are wanted).
        copy(self, "*", src=deps_run, dst=pkg_site, excludes=["bin/*"])

        # setup.cfg `[options.data_files]`: etc/undertime.yml
        stage_etc = os.path.join(stage_prefix, "etc")
        if os.path.isdir(stage_etc):
            copy(self, "*", src=stage_etc,
                 dst=os.path.join(self.package_folder, "etc"))

    def package_info(self):
        maj, minr = sys.version_info[:2]
        site = os.path.join("lib", f"python{maj}.{minr}", "site-packages")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.prepend_path(
            "PYTHONPATH", os.path.join(self.package_folder, site))
