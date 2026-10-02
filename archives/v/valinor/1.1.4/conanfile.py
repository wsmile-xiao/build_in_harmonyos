#!/usr/bin/env python3
"""Conan recipe for valinor 1.1.4 (pure Python).

Valinor generates IDE project files to debug ELF files (ARMmbed/valinor,
proxy debug command for yotta targets). Pure-Python noarch package:
the valinor/ module is patched in-place (distutils->shutil,
_winreg->winreg, lazy --version) then copied into site-packages,
runtime/test dependencies are pip-installed into the same staging dir
(--target, isolated, no system pollution).

project_generator 0.8.x is sdist-only with a setup.py that imports the
long-removed pip.req/PipSession API, so it is downloaded, repaired
(pip.req removed, argparse backport skipped) and installed from a local
tree pinned at 0.8.4; setuptools is capped at <81 to keep pkg_resources.

Upstream tests (3 total, python_def):
- valinor/test/test_outputdir.py: TestCLIOutputDirectory with 2 methods
  (testUVision, testARMNoneEABIGDB), each generates .uvproj/.gdbstartup
  via the real CLI with -n (no-open) and asserts output files exist.
- valinor/test/test_exporter.py: 1 nose function test_exporter_location
  (@raises NotImplementedError, generic Builder.build_project must fail;
  on Python>=3.12 nose itself is unimportable due to removed `imp`, so an
  identical direct Builder assertion is used and logged).

build() runs the real upstream suite via unittest result objects
(deterministic, no stdout string counting) and emits
HMBS_UPSTREAM_TEST_RESULT with true counts, persisted to res/ for
test_package re-emit on cached builds.
"""

import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get, replace_in_file
from conan.tools.layout import basic_layout


class ValinorConan(ConanFile):
    name = "valinor"
    version = "1.1.4"
    description = "Generate IDE project files to debug ELF files"
    license = "Apache-2.0"
    homepage = "https://github.com/ARMmbed/valinor"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("debug", "elf", "ide", "embedded", "yotta")
    package_type = "python-require"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _pip_index_candidates(self):
        # Ordered pip index fallback: the default/internal mirror
        # (PIP_INDEX_URL or cnb.cool) is tried first, then public mirrors
        # known reachable from the preflight box (urllib sdist download
        # via tuna/aliyun already succeeds there). The internal mirror is
        # a subset allowlist: on 2026-09-30 it returned zero versions for
        # pyYAML ("No matching distribution found for pyYAML" while
        # resolving the repaired project_generator local tree), so pip
        # must not be pinned to that single index.
        primary = os.environ.get(
            "PIP_INDEX_URL",
            "https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple",
        ).strip()
        primary_host = os.environ.get("PIP_TRUSTED_HOST", "pypi.cnb.cool").strip()
        candidates = []
        if primary:
            candidates.append((primary, primary_host))
        candidates += [
            ("https://pypi.tuna.tsinghua.edu.cn/simple", "pypi.tuna.tsinghua.edu.cn"),
            ("https://mirrors.aliyun.com/pypi/simple/", "mirrors.aliyun.com"),
            ("https://pypi.org/simple", ""),
        ]
        seen = set()
        ordered = []
        for url, host in candidates:
            if url and url not in seen:
                seen.add(url)
                ordered.append((url, host))
        return ordered

    def _run_pip_with_fallback(self, base_args, pip_env, label):
        # base_args: pip args WITHOUT the interpreter prefix and WITHOUT
        # index args, e.g. ["install", "--no-cache-dir", ..., "pkg"].
        # Each candidate index is tried in order with --retries/--timeout;
        # first success wins. All attempts are logged (last 8 lines each)
        # so preflight logs show which index served the install.
        last_err = None
        for index, host in self._pip_index_candidates():
            args = [sys.executable, "-m", "pip"] + base_args[:2]
            args += ["--index-url", index]
            if host:
                args += ["--trusted-host", host]
            args += ["--retries", "5", "--timeout", "60"]
            args += base_args[2:]
            self.output.info("valinor pip %s try index %s" % (label, index))
            r = subprocess.run(args, capture_output=True, text=True, env=pip_env)
            self.output.info("valinor pip %s [%s] rc=%d" % (label, index, r.returncode))
            for line in (r.stdout + r.stderr).splitlines()[-8:]:
                self.output.info("valinor pip %s [%s]: %s" % (label, index, line))
            if r.returncode == 0:
                return r
            last_err = (r.stdout + r.stderr).splitlines()[-5:] if (r.stdout + r.stderr) else []
        raise ConanException(
            "pip install %s failed on all indexes; last error tail: %s" % (label, last_err))

    def _pip_index_args(self):
        # Kept for compatibility; new code uses _run_pip_with_fallback.
        index = os.environ.get(
            "PIP_INDEX_URL",
            "https://pypi.cnb.cool/OpenHarmonyPCDeveloper/pypi/-/packages/simple",
        ).strip()
        host = os.environ.get("PIP_TRUSTED_HOST", "pypi.cnb.cool").strip()
        if index:
            args = ["--index-url", index]
            if host:
                args += ["--trusted-host", host]
            return args
        return []

    def _sha256_of(self, path):
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def _pip_install_project_generator(self, staging, pip_env):
        # project_generator 0.8.x is sdist-only AND its setup.py is broken
        # under any modern pip: it does `from pip.req import
        # parse_requirements` with `pip.download.PipSession()`, both removed
        # from pip in 2018 (pip 10). Every 0.8.x release shares it, so no
        # version pin inside valinor's >=0.8.0,<0.9.0 range can succeed and
        # no pip flag (--no-build-isolation or otherwise) can help: the
        # failure is `Preparing metadata (pyproject.toml) ...
        # ModuleNotFoundError: No module named 'pip.req'` inside setup.py
        # itself. Different route: fetch the sdist, repair setup.py in a
        # scratch dir, then install from that local tree (pip still resolves
        # its requirements.txt deps normally). Pinned to 0.8.4, the top of
        # valinor's allowed range.
        # NOTE (preflight 2026-09-30): `pip download --no-deps
        # project_generator==0.8.4` itself now fails on modern pip with
        # "Failed to build 'project_generator' when getting requirements
        # to build wheel" because pip tries to build metadata for the
        # sdist even during download. So the sdist is fetched with a plain
        # HTTP GET (no setup.py execution, no build isolation) from an
        # ordered mirror list, verified by sha256, then repaired/installed
        # from the local tree as before.
        pg_ver = "0.8.4"
        pg_file = "project_generator-%s.zip" % pg_ver
        pg_sha256 = "1e1359a12e1710ef24ea886e001edece1f7e4b7968639a335cd358360f1b7232"
        pg_path = "packages/d2/10/3435f8cfd5758982d9115be9bd2b14548441d711bfee144f3ae4a4ee9ebc/" + pg_file
        pg_urls = [
            "https://pypi.tuna.tsinghua.edu.cn/" + pg_path,
            "https://mirrors.aliyun.com/pypi/" + pg_path,
            "https://files.pythonhosted.org/" + pg_path,
        ]
        dl_dir = os.path.join(self.build_folder, "pg_dl")
        os.makedirs(dl_dir, exist_ok=True)
        dl_dest = os.path.join(dl_dir, pg_file)
        if not (os.path.isfile(dl_dest) and self._sha256_of(dl_dest) == pg_sha256):
            last_err = None
            for _url in pg_urls:
                try:
                    self.output.info("valinor pg direct download: %s" % _url)
                    _req = urllib.request.Request(_url, headers={"User-Agent": "conan-valinor/1.1.4"})
                    with urllib.request.urlopen(_req, timeout=60) as _resp, \
                            open(dl_dest, "wb") as _out:
                        shutil.copyfileobj(_resp, _out)
                except Exception as e:
                    last_err = e
                    self.output.info("valinor pg download failed %s: %s" % (_url, e))
                    try:
                        if os.path.isfile(dl_dest):
                            os.unlink(dl_dest)
                    except Exception:
                        pass
                    continue
                _got = self._sha256_of(dl_dest)
                if _got != pg_sha256:
                    self.output.info("valinor pg sha256 mismatch from %s: %s" % (_url, _got))
                    try:
                        os.unlink(dl_dest)
                    except Exception:
                        pass
                    last_err = ValueError("sha256 mismatch: %s" % _got)
                    continue
                last_err = None
                break
            if last_err is not None or not os.path.isfile(dl_dest):
                raise ConanException("direct download of project_generator sdist failed: %s" % last_err)
            self.output.info("valinor pg sdist downloaded+verified: %s" % dl_dest)
        else:
            self.output.info("valinor pg sdist cache hit: %s" % dl_dest)
        zips = [dl_dest]
        pgwork = os.path.join(self.build_folder, "pg_src")
        if os.path.isdir(pgwork):
            shutil.rmtree(pgwork)
        os.makedirs(pgwork)
        with zipfile.ZipFile(zips[0]) as z:
            z.extractall(pgwork)
        pgdir = os.path.join(pgwork, "project_generator-0.8.4")
        setup_py = os.path.join(pgdir, "setup.py")
        if not os.path.isfile(setup_py):
            raise ConanException("project_generator setup.py missing in sdist")
        replace_in_file(
            self, setup_py,
            "import os\n"
            "import pip\n"
            "\n"
            "from pip.req import parse_requirements\n"
            "from setuptools import setup, find_packages\n"
            "\n"
            "def read(fname):\n"
            "    return open(os.path.join(os.path.dirname(__file__), fname)).read()\n"
            "\n"
            "requirements = [str(requirement.req) for requirement in parse_requirements('requirements.txt', session=pip.download.PipSession())]\n",
            "import os\n"
            "\n"
            "from setuptools import setup, find_packages\n"
            "\n"
            "def read(fname):\n"
            "    return open(os.path.join(os.path.dirname(__file__), fname)).read()\n"
            "\n"
            "def _local_requirements(fname):\n"
            "    reqs = []\n"
            "    with open(os.path.join(os.path.dirname(__file__), fname)) as f:\n"
            "        for line in f:\n"
            "            line = line.strip()\n"
            "            if not line or line.startswith('#'):\n"
            "                continue\n"
            "            # argparse has been stdlib since 3.2; the PyPI\n"
            "            # backport must not shadow it\n"
            "            if line.lower().startswith('argparse'):\n"
            "                continue\n"
            "            reqs.append(line)\n"
            "    return reqs\n"
            "\n"
            "requirements = _local_requirements('requirements.txt')\n",
        )
        self.output.info("valinor pg setup.py repaired (pip.req removed)")
        # Install the repaired tree with --no-deps first: its requirements
        # (pyYAML/Jinja2/xmltodict/project_generator_definitions) are then
        # installed explicitly below, each via the ordered index fallback.
        # Rationale: a single `pip install <dir>` lets the resolver pull
        # all deps from the FIRST index only; when that index (internal
        # mirror) has zero versions for pyYAML the whole install fails
        # with "No matching distribution found for pyYAML" (preflight
        # 2026-09-30) without ever trying the public mirrors.
        pg_base = (
            ["install", "--no-cache-dir",
             "--prefer-binary", "--no-build-isolation", "--no-deps",
             "--target", staging]
            + [pgdir]
        )
        self._run_pip_with_fallback(pg_base, pip_env, "pg-ndeps")
        # project_generator 0.8.4 requirements.txt (argparse is stdlib
        # since 3.2 and is skipped by the repaired setup.py as well).
        for _pgdep in ["pyYAML", "Jinja2", "xmltodict",
                       "project_generator_definitions>=0.2.2,<0.3.0"]:
            _pgbase = (
                ["install", "--no-cache-dir",
                 "--prefer-binary", "--no-build-isolation",
                 "--target", staging]
                + [_pgdep]
            )
            self._run_pip_with_fallback(_pgbase, pip_env, "pg-dep %s" % _pgdep)

    def _patch_staged_pycompat(self, staging):
        # pyelftools 0.23 vendors an old `construct` that does
        # `from collections import MutableMapping` (ABC aliases removed in
        # 3.10). Patch the staged copy only; exact match, loud on drift.
        replace_in_file(
            self,
            os.path.join(staging, "elftools", "construct", "lib", "container.py"),
            "from collections import MutableMapping",
            "try:\n"
            "    from collections.abc import MutableMapping\n"
            "except ImportError:\n"
            "    from collections import MutableMapping",
        )
        # project_generator_definitions<=0.2.9 calls yaml.load() without a
        # Loader (TypeError on PyYAML>=6). Newer releases already pass
        # Loader=FullLoader; normalize only if the old spelling is present.
        defs = os.path.join(staging, "project_generator_definitions", "definitions.py")
        if not os.path.isfile(defs):
            raise ConanException("project_generator_definitions not staged")
        with open(defs, encoding="utf-8") as f:
            content = f.read()
        if "config = yaml.load(project_file)" in content:
            replace_in_file(
                self, defs,
                "config = yaml.load(project_file)",
                "config = yaml.load(project_file, Loader=yaml.FullLoader)",
            )
            self.output.info("valinor staged definitions.py yaml.load normalized")
        else:
            self.output.info("valinor staged definitions.py already Loader-safe")

    def build(self):
        # Python 3.12 removed distutils: replace the import in-place instead
        # of a context-diff patch (no fuzz/strip-level fragility on the
        # preflight box). Exact-string match, fails loudly if upstream moves.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "valinor", "ide_detection.py"),
            "from distutils.spawn import find_executable",
            "try:\n"
            "    from distutils.spawn import find_executable\n"
            "except ImportError:\n"
            "    # Python 3.12 removed distutils; shutil.which is the replacement\n"
            "    from shutil import which as find_executable",
        )
        # _winreg only exists on Python 2; Python 3 renamed it to winreg.
        # (Only reachable on Windows; the os.name guard skips it on Linux.)
        replace_in_file(
            self,
            os.path.join(self.source_folder, "valinor", "ide_detection.py"),
            "    import _winreg as winreg",
            "    try:\n"
            "        import winreg\n"
            "    except ImportError:\n"
            "        import _winreg as winreg",
        )
        # main() builds --version from pkg_resources.require("valinor"), but
        # the staged tree ships no egg-info/dist-info (only valinor/ is
        # copied) and optional deps such as pyOCD are intentionally absent,
        # so require() always raises DistributionNotFound and every CLI run
        # exits 1. Resolve lazily with a static fallback instead.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "valinor", "main.py"),
            "import pkg_resources\nimport shutil",
            "import shutil",
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "valinor", "main.py"),
            "import valinor.logging_setup as logging_setup",
            "def _valinor_version():\n"
            "    try:\n"
            "        import pkg_resources\n"
            "        return pkg_resources.require(\"valinor\")[0].version\n"
            "    except Exception:\n"
            "        return \"1.1.4\"\n"
            "\n"
            "\n"
            "import valinor.logging_setup as logging_setup",
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "valinor", "main.py"),
            "        version=pkg_resources.require(\"valinor\")[0].version,",
            "        version=_valinor_version(),",
        )
        pyver = "python%d.%d" % (sys.version_info.major, sys.version_info.minor)
        staging = os.path.join(self.build_folder, "staging", "lib", pyver, "site-packages")
        os.makedirs(staging, exist_ok=True)
        src_pkg = os.path.join(self.source_folder, "valinor")
        if not os.path.isdir(src_pkg):
            raise ConanException("valinor source package directory is missing")
        dst_pkg = os.path.join(staging, "valinor")
        if os.path.isdir(dst_pkg):
            shutil.rmtree(dst_pkg)
        shutil.copytree(src_pkg, dst_pkg)

        # Runtime/test deps (setup.py install_requires + nose for
        # test_exporter). Installed --target into staging so neither the
        # system site nor the recipe graph is polluted (R36 safe, no Conan
        # requires for PyPI-only deps). pyOCD is only needed when actually
        # launching a debug session (tests use -n no-open), so it is
        # intentionally not installed: keeps the closure small and avoids
        # pulling old pyOCD (<1.0) onto Python 3.12+.
        # Staged setuptools/wheel are exposed to every pip subprocess via
        # PYTHONPATH so --no-build-isolation backends stay importable
        # without touching the system site. setuptools is capped at <81
        # because 81+ removed pkg_resources, which valinor/main.py imports.
        # Low-peak pip env (Signal 9/OOM guard): every pip subprocess runs
        # --no-cache-dir with cache/version-check/input disabled so no
        # wheel cache or self-check work inflates the preflight RSS peak.
        pip_env = dict(os.environ)
        pip_env["PYTHONPATH"] = staging + os.pathsep + pip_env.get("PYTHONPATH", "")
        pip_env["PIP_NO_CACHE_DIR"] = "1"
        pip_env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
        pip_env["PIP_NO_INPUT"] = "1"
        pip_env["PYTHONDONTWRITEBYTECODE"] = "1"
        chk = subprocess.run(
            [sys.executable, "-c", "import setuptools.build_meta, wheel"],
            capture_output=True, text=True, env=pip_env)
        if chk.returncode != 0:
            # Sequential bootstrap as well: two tiny resolver runs peak
            # far lower than one combined run on the preflight box.
            for _boot in ["setuptools<81", "wheel"]:
                _bootbase = (
                    ["install", "--no-cache-dir",
                     "--prefer-binary", "--target", staging]
                    + [_boot]
                )
                self._run_pip_with_fallback(_bootbase, pip_env, "bootstrap %s" % _boot)
            recheck = subprocess.run(
                [sys.executable, "-c", "import setuptools.build_meta, wheel; print('backend ok')"],
                capture_output=True, text=True, env=pip_env)
            self.output.info("valinor pip backend recheck rc=%d" % recheck.returncode)
            for line in (recheck.stdout + recheck.stderr).splitlines()[-5:]:
                self.output.info("valinor pip backend: %s" % line)
            if recheck.returncode != 0:
                raise ConanException("pip backend setuptools.build_meta still not importable via staged PYTHONPATH")
        self._pip_install_project_generator(staging, pip_env)
        # Low-peak sequential installs (Signal 9/OOM guard): one pip
        # resolver process per distribution instead of a single combined
        # `pip install a b c d` whose resolver peak killed the preflight
        # box with SIGKILL and empty logs. pytest was dropped here: the
        # upstream runner below uses unittest result objects plus a nose/
        # direct Builder check, and test_package uses plain python, so
        # pytest (+pluggy/iniconfig/packaging closure) is dead weight.
        for _dep in ["pyelftools==0.23", "colorama", "nose"]:
            _base = (
                ["install", "--no-cache-dir",
                 "--prefer-binary", "--no-build-isolation",
                 "--target", staging]
                + [_dep]
            )
            self._run_pip_with_fallback(_base, pip_env, "deps %s" % _dep)
        self._patch_staged_pycompat(staging)

        # Run the real upstream suite with unittest result objects.
        # discovered=3 is the audited total (2 TestCase methods +
        # 1 nose function); executed/passed/failed/skipped come from the
        # result objects below, never from stdout string counting.
        runner_py = os.path.join(self.build_folder, "run_valinor_upstream.py")
        with open(runner_py, "w", encoding="utf-8") as f:
            f.write(
                "import sys, unittest\n"
                "sys.path.insert(0, %r)\n" % staging
                + "sys.path.insert(0, %r)\n" % self.source_folder
                + "loader = unittest.TestLoader()\n"
                + "suite = unittest.TestSuite()\n"
                + "suite.addTests(loader.loadTestsFromName('valinor.test.test_outputdir'))\n"
                + "import io\n"
                + "stream = io.StringIO()\n"
                + "runner = unittest.TextTestRunner(stream=stream, verbosity=2)\n"
                + "result = runner.run(suite)\n"
                + "out_tests = result.testsRun\n"
                + "out_fail = len(result.failures)\n"
                + "out_err = len(result.errors)\n"
                + "out_skip = len(result.skipped)\n"
                + "exp_passed = False\n"
                + "exp_failed = 0\n"
                + "exp_mode = 'unknown'\n"
                + "try:\n"
                + "    from valinor.test.test_exporter import test_exporter_location\n"
                + "    try:\n"
                + "        test_exporter_location()\n"
                + "        exp_passed = True\n"
                + "        exp_mode = 'nose_decorator'\n"
                + "    except NotImplementedError:\n"
                + "        exp_passed = True\n"
                + "        exp_mode = 'direct_raise'\n"
                + "    except Exception as e:\n"
                + "        print('exporter unexpected error: %s' % e)\n"
                + "        exp_failed = 1\n"
                + "        exp_mode = 'nose_error'\n"
                + "except Exception as e:\n"
                + "    print('exporter nose import failed (%s); direct Builder check' % e)\n"
                + "    exp_mode = 'direct_builder'\n"
                + "    try:\n"
                + "        from project_generator.tools.tool import Builder\n"
                + "        try:\n"
                + "            Builder().build_project()\n"
                + "            exp_failed = 1\n"
                + "        except NotImplementedError:\n"
                + "            exp_passed = True\n"
                + "        except Exception as e2:\n"
                + "            print('exporter direct error: %s' % e2)\n"
                + "            exp_failed = 1\n"
                + "    except Exception as e3:\n"
                + "        print('exporter direct import error: %s' % e3)\n"
                + "        exp_failed = 1\n"
                + "discovered = 3\n"
                + "executed = out_tests + 1\n"
                + "passed = (out_tests - out_fail - out_err - out_skip) + (1 if exp_passed else 0)\n"
                + "failed = out_fail + out_err + exp_failed\n"
                + "skipped = out_skip\n"
                + "status = 'passed' if (failed == 0 and executed == discovered and passed == discovered) else 'failed'\n"
                + "print('UPSTREAM_SUMMARY discovered=%d executed=%d passed=%d failed=%d skipped=%d exporter=%s' % (discovered, executed, passed, failed, skipped, exp_mode))\n"
                + "print(stream.getvalue())\n"
                + "import json\n"
                + "marker = {'status': status, 'framework': 'unittest', 'command': 'python -m unittest valinor.test.test_outputdir + test_exporter_location', 'discovered': discovered, 'executed': executed, 'passed': passed, 'failed': failed, 'skipped': skipped}\n"
                + "print('HMBS_UPSTREAM_JSON=' + json.dumps(marker))\n"
                + "sys.exit(0 if status == 'passed' else 1)\n"
            )
        env = dict(os.environ)
        env["PYTHONPATH"] = staging + os.pathsep + self.source_folder
        # HMBS injects an isolated TMPDIR; pytest/unittest temp dirs must
        # stay under it (hmdfs-safe). unittest mkdtemp honors TMPDIR.
        r = subprocess.run([sys.executable, runner_py], capture_output=True,
                           text=True, env=env, timeout=600)
        self.output.info("valinor upstream rc=%d" % r.returncode)
        for line in (r.stdout + r.stderr).splitlines()[-25:]:
            self.output.info("valinor upstream: %s" % line)
        marker = None
        for line in r.stdout.splitlines():
            if line.startswith("HMBS_UPSTREAM_JSON="):
                marker = json.loads(line[len("HMBS_UPSTREAM_JSON="):])
                break
        if marker is None:
            raise ConanException("upstream runner did not emit counts")
        # Self-check the counting identities before persisting.
        assert marker["passed"] + marker["failed"] == marker["executed"], marker
        assert marker["executed"] + marker["skipped"] <= marker["discovered"], marker
        assert marker["executed"] <= marker["discovered"], marker
        res_dir = os.path.join(self.build_folder, "res")
        os.makedirs(res_dir, exist_ok=True)
        with open(os.path.join(res_dir, "upstream_test_result.json"), "w",
                  encoding="utf-8") as f:
            json.dump(marker, f, ensure_ascii=False)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        if r.returncode != 0:
            raise ConanException("upstream tests failed: %s" % marker)

    def package(self):
        pyver = "python%d.%d" % (sys.version_info.major, sys.version_info.minor)
        staging = os.path.join(self.build_folder, "staging", "lib", pyver, "site-packages")
        site = os.path.join(self.package_folder, "lib", pyver, "site-packages")
        if not os.path.isdir(staging):
            raise ConanException("valinor staging directory is missing")
        copy(self, "*", src=staging, dst=site)
        copy(self, "upstream_test_result.json",
             src=os.path.join(self.build_folder, "res"),
             dst=os.path.join(self.package_folder, "res"))

    def package_info(self):
        pyver = "python%d.%d" % (sys.version_info.major, sys.version_info.minor)
        site = os.path.join(self.package_folder, "lib", pyver, "site-packages")
        self.buildenv_info.prepend_path("PYTHONPATH", site)
        self.runenv_info.prepend_path("PYTHONPATH", site)
