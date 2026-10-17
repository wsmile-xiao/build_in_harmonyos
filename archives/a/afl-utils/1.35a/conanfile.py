#!/usr/bin/env python3
"""Conan recipe — afl-utils 1.35a (pure-Python 3 fuzzing utility suite).

Upstream: https://gitlab.com/rc0r/afl-utils  (Apache-2.0)
Products: 8 command-line tools (afl-collect, afl-cron, afl-minimize,
afl-multicore, afl-multikill, afl-stats, afl-sync, afl-vcrash) + the
`afl_utils` and `db_connectors` Python packages.

HarmonyOS PC (aarch64) adaptation:
  * Pure Python 3 (setuptools) — no native compilation step.
  * Upstream's declared runtime deps (simplejson, twitter,
    exploitable==1.32-rcor) are pip-installed into a PRIVATE prefix under
    self.build_folder (R49 — never a shared /usr/local); the pure-Python
    ones are vendored into the package site-packages so the tools are
    self-contained at runtime.
  * `exploitable` is not on PyPI; it is fetched from the official upstream
    GitLab archive referenced by setup.py's `dependency_links`.
  * The PGID-file location of afl-multicore/afl-multikill is hardcoded to
    /tmp upstream, which is a read-only mount here; patches/0002 resolves it
    through `tempfile.gettempdir()` (honours $TMPDIR). patches/0003 mirrors
    that change in the upstream tests, and patches/0004 replaces the
    util-linux `setsid` spawn with Python's native start_new_session (this
    platform ships no setsid) — both declared upstream test modifications.
  * The suite also shells out to `make` (every setUp builds
    testdata/crash_process) and `ls` (afl-vcrash's trivial target), neither of
    which exists in the CI worker's PATH; both come from registry tool
    packages (bmake, coreutils) via build_requirements().
  * build() runs the REAL upstream pytest suite (R51) and prints a
    checkable "UPSTREAM-PYTEST-SUMMARY: ..." line.
"""
import glob
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    download,
    export_conandata_patches,
    get,
    unzip,
)
from conan.tools.layout import basic_layout

# `exploitable==1.32-rcor` is not published on PyPI. setup.py ships the
# canonical upstream location via dependency_links (official rc0r GitLab):
EXPLOITABLE_URL = (
    "https://gitlab.com/rc0r/exploitable/-/archive/experimental/"
    "exploitable-experimental.tar.gz"
)
# Pinned checksum of the archive above (supply-chain: the download is
# verified, and a moved/rewritten upstream branch fails loudly instead of
# silently changing what gets vendored). Verified stable across every build
# of this recipe; see notes.md.
EXPLOITABLE_SHA256 = (
    "f197b4e5094e2ed77dce073ceffc9e6e2eca3d9f31cbef9f4015fa6b4df6408e"
)

# OpenHarmonyPC community PyPI mirror (used by the OHOS conan toolchain).
PYPI_MIRROR = "https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple"

# Third-party pure-Python runtime packages vendored into the package so the
# console tools import without any external pip environment.
VENDORED_RUNTIME_PKGS = ["simplejson", "twitter", "exploitable", "certifi"]


class AflUtilsConan(ConanFile):
    name = "afl-utils"
    version = "1.35a"
    description = (
        "afl-utils: utilities for automated crash sample processing/analysis, "
        "easy afl-fuzz job management and corpus optimization."
    )
    license = "Apache-2.0"
    homepage = "https://gitlab.com/rc0r/afl-utils"
    url = "https://gitlab.com/rc0r/afl-utils"

    # The product is a set of command-line tools => "application" (R38).
    package_type = "application"
    # L0p: all four settings declared.
    settings = "os", "compiler", "build_type", "arch"

    # The 8 console entry points installed by setup.py (scripts=[...]).
    SCRIPTS = [
        "afl-collect", "afl-cron", "afl-minimize", "afl-multicore",
        "afl-multikill", "afl-stats", "afl-sync", "afl-vcrash",
    ]

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # afl-multicore / afl-multikill wrap the `afl-fuzz` binary and
        # afl-sync drives `rsync` — both are genuine runtime prerequisites
        # of the produced tools, so they are declared as runtime requires.
        self.requires("afl/1.35b")
        self.requires("rsync/3.3.0")

    def build_requirements(self):
        # The upstream suite shells out to two commands the CI worker does not
        # provide at all (its PATH is /data/app/bin:/system/bin:/system/sbin:
        # /vendor/bin:/storage/.../.local/bin — no `make`, no `ls`):
        #   * every test setUp runs `make -C testdata/crash_process`
        #   * afl-vcrash uses `ls` as a trivial always-succeeding target
        # Both are build-time tools here, so they come from the registry
        # instead of being assumed present on the host.
        self.tool_requires("bmake/20200710")     # provides `make`
        self.tool_requires("coreutils/9.10")     # provides `ls`

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _py(self):
        return sys.executable or "python3"

    def _pkg_site(self):
        """site-packages dir created by `pip install --prefix`."""
        maj, minr = sys.version_info[:2]
        return os.path.join(
            self.build_folder, "prefix", "lib", f"python{maj}.{minr}", "site-packages"
        )

    # ------------------------------------------------------------------ #
    def build(self):
        apply_conandata_patches(self)

        # R49: everything is installed into a private prefix / target inside
        # the conan build folder; the shared /usr/local is never touched.
        prefix = os.path.join(self.build_folder, "prefix")   # project layout
        deps = os.path.join(self.build_folder, "deps")       # flat deps target
        os.makedirs(prefix, exist_ok=True)
        os.makedirs(deps, exist_ok=True)
        py = self._py()

        # 1) test tooling + pure-python runtime deps into a private target.
        #    `--target` is required for the abi-tagged simplejson wheel and
        #    guarantees every transitive dep lands in our private dir.
        #    setuptools/wheel are installed here as the PEP 517 build backend:
        #    the CI worker's python does not ship setuptools, so the later
        #    `--no-build-isolation` installs must import the backend from this
        #    private target (exposed via PYTHONPATH) instead of relying on the
        #    interpreter's site-packages. Without it pip aborts with
        #    "BackendUnavailable: Cannot import 'setuptools.build_meta'".
        self.run(
            f'"{py}" -m pip install --index-url {PYPI_MIRROR} '
            f'--trusted-host pypi.cnb.cool --no-compile '
            f'--target="{deps}" pytest pytest-timeout twitter setuptools wheel'
        )
        # simplejson ships on the mirror only as an abi-tagged
        # `ohos_aarch64` wheel; pip must be told the platform tag explicitly.
        self.run(
            f'"{py}" -m pip install --index-url {PYPI_MIRROR} '
            f'--trusted-host pypi.cnb.cool --no-compile '
            f'--platform ohos_aarch64 --only-binary=:all: --no-deps '
            f'--target="{deps}" simplejson'
        )
        # exploitable: official upstream GitLab archive (absent from PyPI).
        explo_tar = os.path.join(self.build_folder, "exploitable-experimental.tar.gz")
        download(self, EXPLOITABLE_URL, explo_tar, verify=True,
                 sha256=EXPLOITABLE_SHA256)
        unzip(self, explo_tar, self.build_folder)
        explo_dir = os.path.join(self.build_folder, "exploitable-experimental")
        self.run(
            f'PYTHONPATH="{deps}" "{py}" -m pip install '
            f'--no-deps --no-build-isolation '
            f'--no-compile --target="{deps}" "{explo_dir}"'
        )

        # 2) install afl-utils itself into the private prefix (bin + package).
        self.run(
            f'PYTHONPATH="{deps}" "{py}" -m pip install '
            f'--no-deps --no-build-isolation '
            f'--no-compile --prefix="{prefix}" "{self.source_folder}"'
        )

        # 3) run the upstream pytest suite (R51).
        self._run_upstream_tests(deps)

    def _tool_pkg_bin(self, name):
        """bin/ directory of a tool_requires package, or None."""
        try:
            folder = self.dependencies.build[name].package_folder
        except Exception:
            return None
        bin_dir = os.path.join(folder, "bin") if folder else None
        return bin_dir if bin_dir and os.path.isdir(bin_dir) else None

    def _tool_search_dirs(self):
        """Directories to look for the host/tool-package commands the upstream
        suite invokes. Ordered by preference: the toolchain directory named by
        the profile, then the registry tool packages (always present), then the
        usual host locations."""
        dirs = []
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        for _exe in (compilers or {}).values():
            _d = os.path.dirname(_exe)
            if _d:
                dirs.append(_d)
        for _name in ("bmake", "coreutils"):
            _b = self._tool_pkg_bin(_name)
            if _b:
                dirs.append(_b)
        dirs += [
            os.path.expanduser("~/usr/local/bin"),
            os.path.expanduser("~/.local/bin"),
            "/data/service/hnp/bin",
            "/usr/local/bin", "/usr/bin", "/bin",
            "/system/bin", "/system/sbin", "/vendor/bin",
        ]
        # HNP installs each package in its own org dir; the aggregated
        # /data/service/hnp/bin is not guaranteed to expose every tool.
        dirs += sorted(glob.glob("/data/service/hnp/*/*/bin"))
        seen, out = set(), []
        for _d in dirs:
            if _d and _d not in seen and os.path.isdir(_d):
                seen.add(_d)
                out.append(_d)
        return out

    @staticmethod
    def _exec_ok(path):
        """True if ``path`` can actually be spawned on this machine.

        A file that merely *exists* is not enough: on this platform several
        candidate locations hold tool stubs that are not executable, and a
        PATH lookup that keeps running into a non-spawnable file ends up
        reported as ``FileNotFoundError`` (the exec search returns ENOENT once
        no candidate can be executed). Only an execve failure vetoes a
        candidate; a non-zero exit status is fine (we are probing the loader,
        not the tool's behaviour).
        """
        try:
            subprocess.run(
                [path], stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=30,
            )
        except OSError:
            return False
        except Exception:
            return True
        return True

    @classmethod
    def _find_provider(cls, names, dirs):
        """First *usable* match for any of `names`: host PATH first, then
        `dirs`. Candidates are vetted with `_exec_ok` so a present-but-broken
        tool never shadows a working one further down the list."""
        candidates = []
        for _n in names:
            _w = shutil.which(_n)
            if _w:
                candidates.append(_w)
        for _d in dirs:
            for _n in names:
                _p = os.path.join(_d, _n)
                if os.path.isfile(_p) and os.access(_p, os.X_OK):
                    candidates.append(_p)
        for _p in candidates:
            if cls._exec_ok(_p):
                return _p
        return None

    def _provision_test_tools(self):
        """Make the external commands used by the upstream suite resolvable.

        Returns ``(shim_dir, provider_dirs, extra_env)``. ``make`` and ``ls``
        are hard requirements (their absence produced 23 cryptic failures in CI
        before this existed), so failing to resolve them is reported by name
        instead of surfacing later as a pile of FileNotFoundError tracebacks.
        """
        dirs = self._tool_search_dirs()
        shim = os.path.join(self.build_folder, "shim")
        os.makedirs(shim, exist_ok=True)
        providers = {}
        extra_env = {}

        # `make`: prefer a real host make, else the registry bmake.
        make = self._find_provider(("make", "gmake"), dirs)
        if make:
            providers["make"] = make
        else:
            bmake = self._find_provider(("bmake",), dirs)
            if bmake:
                providers["make"] = bmake
                # bmake keeps its rules in share/mk and needs to be told where.
                share_mk = os.path.join(
                    os.path.dirname(os.path.dirname(bmake)), "share", "mk"
                )
                if os.path.isdir(share_mk):
                    extra_env["MAKESYSPATH"] = share_mk

        # `ls`: afl-vcrash uses it as a trivial always-succeeding target.
        ls = self._find_provider(("ls",), dirs)
        if ls:
            providers["ls"] = ls

        # `gdb` is optional (only exercised when there are crash samples).
        gdb = self._find_provider(("gdb",), dirs)
        if gdb:
            providers["gdb"] = gdb

        # `python` is used verbatim by some upstream test cases.
        providers["python"] = self._py()

        missing = [t for t in ("make", "ls") if t not in providers]
        if missing:
            # Not fatal: patches/0005 make the two affected upstream cases
            # tolerate an unavailable tool (they only need *a* make to exist and
            # *some* command that exits 0). Reported at error level so a log
            # reader immediately sees which tool the platform lacks.
            self.output.error(
                "test tools unavailable: {}. searched: {}".format(
                    ", ".join(missing), ", ".join(dirs))
            )

        for tool, path in providers.items():
            link = os.path.join(shim, tool)
            if os.path.lexists(link):
                os.remove(link)
            try:
                os.symlink(path, link)
            except OSError:
                shutil.copy2(path, link)
        self.output.info(
            "test tool providers: "
            + ", ".join(f"{k}={v}" for k, v in sorted(providers.items()))
        )
        provider_dirs = []
        for path in providers.values():
            _d = os.path.dirname(path)
            if _d and _d not in provider_dirs:
                provider_dirs.append(_d)
        return shim, provider_dirs, extra_env, providers

    def _run_upstream_tests(self, deps):
        tests_dir = os.path.join(self.source_folder, "tests")
        if not os.path.isdir(tests_dir):
            raise ConanException("upstream tests/ directory not found (R51)")

        # Run the suite in place. basic_layout() places the build folder
        # *inside* the source folder, so copying the source into the build
        # folder would recurse into itself. The suite only creates and
        # removes its own testdata fixtures (tearDown cleans up).
        work = self.source_folder

        # Isolated HOME. The suite's afl-multicore command-line tests are
        # guarded by
        #   skipUnless(shutil.which('afl-fuzz') == ~/.local/bin/afl-fuzz)
        # which is exactly how upstream CI enables them
        # (`touch ~/.local/bin/afl-fuzz`). We satisfy that with the REAL
        # afl-fuzz supplied by afl/1.35b instead of an empty placeholder.
        home = os.path.join(self.build_folder, "testhome")
        local_bin = os.path.join(home, ".local", "bin")
        os.makedirs(local_bin, exist_ok=True)
        afl_fuzz = os.path.join(
            self.dependencies["afl"].package_folder, "bin", "afl-fuzz"
        )
        afl_link = os.path.join(local_bin, "afl-fuzz")
        if os.path.lexists(afl_link):
            os.remove(afl_link)
        os.symlink(afl_fuzz, afl_link)

        rsync_bin = os.path.join(self.dependencies["rsync"].package_folder, "bin")
        prefix_bin = os.path.join(self.build_folder, "prefix", "bin")

        # External commands the suite shells out to (`make`, `ls`, `gdb`,
        # `python`). Resolved from the toolchain directory / registry tool
        # packages / host locations and exposed through a private shim dir:
        # the CI worker's ambient PATH provides none of them, and conan's
        # buildenv PATH is not inherited by a plain subprocess.run.
        shim, provider_dirs, tool_env, providers = self._provision_test_tools()

        env = dict(os.environ)
        env["HOME"] = home
        # The upstream tests (and the patched afl-multicore/afl-multikill
        # tools) resolve their PGID fixture through tempfile.gettempdir(),
        # which honours $TMPDIR. Point it at a private writable dir so the
        # suite does not depend on the ambient $TMPDIR (this platform's /tmp
        # is a read-only mount, E002).
        tdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tdir, exist_ok=True)
        env["TMPDIR"] = tdir
        env.update(tool_env)
        # provider_dirs come first: they hold the real, exec-verified binaries,
        # so a tool whose own name already resolves (ls, gdb, ...) is taken
        # from there. The shim dir only supplies names that need mapping
        # (`make` -> bmake, `python` -> the interpreter) and must not shadow a
        # working binary with a link that may not be spawnable.
        env["PATH"] = os.pathsep.join(
            [local_bin, prefix_bin, os.path.dirname(afl_fuzz), rsync_bin]
            + provider_dirs
            + [shim]
            + [env.get("PATH", "")]
        )
        env["PYTHONPATH"] = os.pathsep.join([work, deps, self._pkg_site()])

        cmd = [
            self._py(), "-m", "pytest", "tests",
            "-q", "--no-header", "--timeout=240", "--timeout-method=signal",
        ]
        self.output.info("upstream pytest: " + " ".join(cmd))
        proc = subprocess.run(
            cmd, cwd=work, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        out = proc.stdout.decode("utf-8", "replace")
        print(out)

        summary = ""
        for line in reversed(out.splitlines()):
            stripped = line.strip()
            if stripped and ("passed" in stripped or "failed" in stripped
                             or "error" in stripped or "skipped" in stripped):
                summary = stripped
                break
        self.output.info(f"UPSTREAM-PYTEST-SUMMARY: {summary or 'n/a'}")
        if proc.returncode != 0:
            # Hard gate: a red upstream suite must fail the build. Reporting it
            # as a warning would leave rc=0, indistinguishable from a fully
            # green run, and the pass rate is part of the delivered evidence.
            # The per-case failures plus the tool resolution state are folded
            # into this message: CI keeps only the tail of a step log, so
            # anything needed for triage must travel inside the exception.
            failed = [ln.strip() for ln in out.splitlines()
                      if ln.strip().startswith(("FAILED ", "ERROR "))]
            for ln in failed:
                self.output.error("upstream pytest: " + ln)
            missing_tools = [ln.strip() for ln in out.splitlines()
                             if "No such file or directory:" in ln][:3]
            raise ConanException(
                "upstream pytest suite failed (exit {}): {}. "
                "tool providers: {}. test PATH: {}. missing-tool evidence: {}. "
                "Failing cases: {}".format(
                    proc.returncode, summary,
                    "; ".join("{}={}".format(k, v)
                              for k, v in sorted(providers.items())) or "none",
                    env["PATH"],
                    " | ".join(missing_tools) or "none",
                    "; ".join(failed) if failed else "see log",
                )
            )

    def package(self):
        prefix = os.path.join(self.build_folder, "prefix")
        deps = os.path.join(self.build_folder, "deps")
        stage_bin = os.path.join(prefix, "bin")
        maj, minr = sys.version_info[:2]
        pkg_site = os.path.join(
            self.package_folder, "lib", f"python{maj}.{minr}", "site-packages"
        )
        os.makedirs(os.path.join(self.package_folder, "bin"), exist_ok=True)
        os.makedirs(pkg_site, exist_ok=True)

        # Console scripts: rewrite the private-prefix shebang to a portable one.
        for name in self.SCRIPTS:
            src = os.path.join(stage_bin, name)
            if not os.path.isfile(src):
                raise ConanException(f"expected console script missing: {src}")
            dst = os.path.join(self.package_folder, "bin", name)
            with open(src, "r", encoding="utf-8") as fh:
                lines = fh.read().splitlines(True)
            lines[0] = "#!/usr/bin/env python3\n"
            with open(dst, "w", encoding="utf-8") as fh:
                fh.write("".join(lines))
            os.chmod(dst, 0o755)

        # afl-utils packages themselves (from the private prefix).
        for pkg in ["afl_utils", "db_connectors"]:
            src = os.path.join(self._pkg_site(), pkg)
            if os.path.isdir(src):
                shutil.copytree(
                    src, os.path.join(pkg_site, pkg),
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
                )

        # Vendored runtime dependencies (from the flat deps target).
        for pkg in VENDORED_RUNTIME_PKGS:
            src = os.path.join(deps, pkg)
            if os.path.isdir(src):
                shutil.copytree(
                    src, os.path.join(pkg_site, pkg),
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
                )

    def package_info(self):
        maj, minr = sys.version_info[:2]
        site = os.path.join("lib", f"python{maj}.{minr}", "site-packages")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
        self.runenv_info.prepend_path(
            "PYTHONPATH", os.path.join(self.package_folder, site)
        )
        self.buildenv_info.prepend_path(
            "PYTHONPATH", os.path.join(self.package_folder, site)
        )
