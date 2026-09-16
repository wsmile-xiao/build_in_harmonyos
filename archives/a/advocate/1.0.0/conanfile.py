#!/usr/bin/env python3
"""Conan recipe — advocate 1.0.0 (Python, setuptools sdist)."""
import json
import os
import re
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


# advocate 1.0.0 only works with urllib3 1.x: poolmanager.py imports
# urllib3.poolmanager._default_key_normalizer, which was removed in
# urllib3 2.x. requests is not published on ohpcd either, so the
# era-appropriate pins are vendored via pip (aresponses precedent:
# pip install --target into an isolated dir) instead of conan requires.
# netifaces (C extension, addrvalidator local-address detection) is
# intentionally NOT vendored: it fails to link on HarmonyOS musl
# (ld.lld: unable to find library -lintl) and advocate works without it
# via patches/0002-netifaces-optional.patch (determine_local_addresses
# returns [] when the import is missing; callers using
# autodetect_local_addresses=False are unaffected).
_RUNTIME_DEPS = [
    "requests==2.32.3",
    "urllib3==1.26.20",
    "six",
]
_TEST_DEPS = [
    "mock",
    "requests-mock",
    # Pin to 1.0.2: 1.1.0 (2026-08-29, requires-python >=3.10) rewrote
    # FuturesSession.request()/close() around _owned_executor,
    # _pending_futures and contextvars. advocate 1.0.0's FuturesSession
    # subclass bypasses FuturesSession.__init__ (calls Session.__init__
    # directly), so _owned_executor is never set and every futures test
    # dies with AttributeError on `if self._owned_executor or ...`.
    # 1.0.2 keeps the era-contemporary `return self.executor.submit(...)`
    # path that advocate was written against. No assertion is changed.
    "requests-futures==1.0.2",
    "pytest",
    "pytest-cov",
]


class AdvocateConan(ConanFile):
    name = "advocate"
    version = "1.0.0"
    description = "SSRF-preventing wrapper around Python requests"
    license = "Apache-2.0"
    homepage = "https://github.com/JordanMilne/Advocate"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "python-require"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Runtime deps are pip-vendored (see _RUNTIME_DEPS): requests is
        # not published on ohpcd, and ohpcd urllib3 is 2.x which advocate
        # 1.0.0 cannot import (see module docstring). netifaces is
        # optional via 0002 patch and therefore not vendored.
        pass

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self._ensure_test_package_marker()
        self._ensure_py312_test_compat()
        self._ensure_canonicalize_bytes_fix()
        deps_dir = os.path.join(self.build_folder, "deps")
        self._pip_install(_RUNTIME_DEPS + _TEST_DEPS, deps_dir)
        self._run_upstream_tests(deps_dir)

    def _ensure_test_package_marker(self):
        # The PyPI sdist omits test/__init__.py, which exists as an empty
        # file in the upstream v1.0.0 git tag (test/test_advocate.py needs
        # it for the relative import "from .monkeypatching import ...").
        # It is created here instead of via conandata patch: the conan
        # patch parser rejects the zero-line hunk (@@ -0,0 +0,0 @@) of an
        # empty new file ("invalid hunk" in build()), so a patch cannot
        # carry it. Idempotent: kept only when the sdist lacks it.
        init = os.path.join(self.source_folder, "test", "__init__.py")
        if not os.path.isfile(init):
            with open(init, "w"):
                pass
            self.output.info("[advocate] created empty test/__init__.py")

    def _ensure_py312_test_compat(self):
        # Upstream test_advocate.py uses self.assertRegexpMatches (4 sites),
        # removed in Python 3.12 (renamed to assertRegex since 3.2). The
        # true-machine interpreter is 3.12+, so all four wrapper/futures
        # tests die with AttributeError. Insert a 5-line alias shim after
        # `import unittest` (idempotent, test-only, no assertion changed);
        # doing it here instead of via conandata patch avoids the conan
        # patch parser's blank-line/hunk fragility (see notes issue #4).
        # Additionally fix canonname_supported() py3 bytes/str bug, enable
        # the two upstream-skipped tests for complete execution, and
        # normalize the missing-canonname precondition for musl resolvers
        # (see below). All four fixes are idempotent and test-only;
        # no assertion changed.
        path = os.path.join(self.source_folder, "test", "test_advocate.py")
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        changed = False
        if "assertRegexpMatches" in text and "_PY312_ASSERT_ALIAS" not in text:
            anchor = "import unittest\n"
            shim = (anchor +
                    "# _PY312_ASSERT_ALIAS: Python 3.12 removed assertRegexpMatches.\n"
                    "if not hasattr(unittest.TestCase, \"assertRegexpMatches\"):\n"
                    "    unittest.TestCase.assertRegexpMatches = unittest.TestCase.assertRegex\n")
            if anchor not in text:
                raise ConanException("cannot apply py312 test compat: anchor missing")
            text = text.replace(anchor, shim, 1)
            changed = True
            self.output.info("[advocate] added py312 assertRegexpMatches alias shim")
        # Fix 2 (portability, test-only): canonname_supported() compares
        # addrinfo canonname to b"example.com" (bytes). On Python 3
        # socket.getaddrinfo returns canonname as str, so `str == bytes` is
        # always False -> HostnameTests (4 tests) + 2 wrapper hostname tests
        # are silently skipped via skipIf(not canonname_supported()). This is
        # an upstream py2-era bug, not a platform limitation: normalize bytes
        # to str before comparing so the 6 hostname tests actually execute.
        # No assertion changed; previously-skipped tests now run.
        old_canon = 'return addrinfo[0][3] == b"example.com"'
        if old_canon in text:
            new_canon = (
                '# _PY3_CANONNAME_FIX: py3 getaddrinfo returns str, not bytes.\n'
                '    canon = addrinfo[0][3]\n'
                '    if isinstance(canon, bytes):\n'
                '        try:\n'
                '            canon = canon.decode("utf-8")\n'
                '        except Exception:\n'
                '            canon = str(canon)\n'
                '    return canon == "example.com"'
            )
            text = text.replace(old_canon, new_canon, 1)
            changed = True
            self.output.info("[advocate] fixed canonname_supported py3 bytes/str comparison")
        # Fix 3 (complete execution, test-only): upstream marks
        # test_safecurl_blacklist (@unittest.skip: "takes half an hour") and
        # test_redirect (@unittest.skip: broken httpbin endpoint) as skipped,
        # so default `pytest test/ -q` reports 46/48 at best (40/48 with the
        # canonname bug). HMBS requires executed == discovered, so enable both
        # to actually run. No assertion changed; decorators only.
        old_safecurl = '    @unittest.skip("takes half an hour or so to run")\n    def test_safecurl_blacklist(self):'
        if old_safecurl in text:
            new_safecurl = ('    # _HMBS_ENABLE: run upstream slow test for complete execution.\n'
                            '    def test_safecurl_blacklist(self):')
            text = text.replace(old_safecurl, new_safecurl, 1)
            changed = True
            self.output.info("[advocate] enabled test_safecurl_blacklist for complete execution")
        old_redirect = ('    # Disabled for now because the redirection endpoint appears to be broken.\n'
                        '    @unittest.skip\n'
                        '    def test_redirect(self):')
        if old_redirect in text:
            new_redirect = ('    # _HMBS_ENABLE: run upstream redirect test for complete execution.\n'
                            '    def test_redirect(self):')
            text = text.replace(old_redirect, new_redirect, 1)
            changed = True
            self.output.info("[advocate] enabled test_redirect for complete execution")
        # Fix 4 (musl portability, test-only): test_missing_canonname builds
        # addrinfo via plain socket.getaddrinfo("127.0.0.1", ...) without
        # AI_CANONNAME and expects an empty canonname so that
        # is_addrinfo_allowed raises NameserverException. glibc returns ""
        # here, but the HarmonyOS (musl-based) resolver returns a non-empty
        # canonname, so no exception is raised and the test fails. Clear
        # the canonname field to exercise the intended missing-canonname
        # path deterministically on every resolver. No assertion changed.
        old_missing = ('        addrinfo = socket.getaddrinfo(\n'
                       '            "127.0.0.1",\n'
                       '            1,\n'
                       '            0,\n'
                       '            socket.SOCK_STREAM,\n'
                       '        )\n'
                       '        self.assertTrue(addrinfo)')
        if old_missing in text:
            new_missing = ('        addrinfo = socket.getaddrinfo(\n'
                           '            "127.0.0.1",\n'
                           '            1,\n'
                           '            0,\n'
                           '            socket.SOCK_STREAM,\n'
                           '        )\n'
                           '        # _HMBS_MUSL: musl resolvers may return a non-empty\n'
                           '        # canonname without AI_CANONNAME; force the\n'
                           '        # missing-canonname precondition this test means\n'
                           '        # to exercise (assertion unchanged).\n'
                           '        addrinfo = [(f, t, p, "", s) for (f, t, p, c, s) in addrinfo]\n'
                           '        self.assertTrue(addrinfo)')
            text = text.replace(old_missing, new_missing, 1)
            changed = True
            self.output.info("[advocate] normalized missing-canonname precondition for musl")
        if changed:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)

    def _ensure_canonicalize_bytes_fix(self):
        # Library fix (portability): canonicalize_hostname(hostname) calls
        # hostname.encode("idna") directly. Upstream HostnameTests.test_idn
        # builds addrinfo records with a bytes canonname (valid on Python 2
        # where str is bytes); on Python 3 bytes has no encode("idna") and
        # the test dies with AttributeError. Decode bytes to str first; str
        # input behavior is unchanged. Done here instead of via conandata
        # patch: conan's patch parser rejects the hunk once 0002 shifts
        # line numbers in the same file ("extra lines for hunk no.1",
        # "Failed to parse patch"), while a python edit is idempotent and
        # offset-independent. No assertion changed.
        path = os.path.join(self.source_folder, "advocate", "addrvalidator.py")
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        if "_HMBS_BYTES_CANONNAME" in text:
            return
        old = '    return six.text_type(hostname.encode("idna").lower(), \'utf-8\')'
        if old not in text:
            raise ConanException("cannot apply bytes canonname fix: anchor missing")
        new = ('    # _HMBS_BYTES_CANONNAME: py3 portability, bytes canonname.\n'
               '    if isinstance(hostname, bytes):\n'
               '        hostname = hostname.decode("utf-8")\n' + old)
        text = text.replace(old, new, 1)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        self.output.info("[advocate] fixed canonicalize_hostname bytes input")

    def _pip_install(self, packages, target):
        os.makedirs(target, exist_ok=True)
        # True-machine /tmp can be read-only (HMBS readonly_tmp): route
        # pip/wheel temp files through the HMBS-injected TMPDIR when
        # present, else the build-local tmp dir. Only the temp root is
        # redirected; no test is skipped.
        tmp_dir = (os.environ.get("TMPDIR") or os.environ.get("TMP") or
                   os.environ.get("TEMP") or
                   os.path.join(self.build_folder, "tmp"))
        os.makedirs(tmp_dir, exist_ok=True)
        env = dict(os.environ)
        for var in ("TMPDIR", "TMP", "TEMP"):
            env.setdefault(var, tmp_dir)
        cmd = [sys.executable, "-m", "pip", "install", "--target", target]
        cmd.extend(packages)
        self.output.info("[advocate] pip install: %s" % " ".join(packages))
        proc = subprocess.run(cmd, cwd=self.build_folder, env=env,
                              capture_output=True,
                              text=True, timeout=1200)
        for line in (proc.stdout + proc.stderr).splitlines()[-15:]:
            self.output.info("[advocate pip] %s" % line)
        if proc.returncode != 0:
            raise ConanException("pip install failed: %s" % " ".join(packages))

    def _run_upstream_tests(self, deps_dir):
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join([self.source_folder, deps_dir])
        tmp_dir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        for var in ("TMPDIR", "TMP", "TEMP"):
            env.setdefault(var, tmp_dir)
        cmd = [sys.executable, "-m", "pytest", "test/", "-q", "--no-header",
               "-p", "no:cacheprovider"]
        # Timeout 3600: test_safecurl_blacklist iterates ~4.6M IPs (upstream
        # comment "takes half an hour"); 1200s would kill it mid-run.
        proc = subprocess.run(cmd, cwd=self.source_folder, env=env,
                              capture_output=True, text=True, timeout=3600)
        out = proc.stdout + proc.stderr
        for line in out.splitlines()[-20:]:
            self.output.info("[advocate upstream] %s" % line)
        marker = {"status": "passed" if proc.returncode == 0 else "failed",
                  "framework": "pytest",
                  "command": "python -m pytest test/ -q",
                  "discovered": 0, "executed": 0, "passed": 0,
                  "failed": 0, "skipped": 0}
        marker.update(self._parse_pytest_summary(out))
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(marker))
        if proc.returncode != 0:
            raise ConanException("upstream pytest failed:\n%s" % out[-4000:])

    @staticmethod
    def _parse_pytest_summary(out):
        for line in reversed(out.splitlines()):
            nums = dict((word, int(num)) for num, word in
                        re.findall(r"(\d+)\s+(passed|failed|skipped|error|xfailed|xpassed)", line))
            if "passed" in nums or "failed" in nums or "error" in nums:
                passed = nums.get("passed", 0) + nums.get("xpassed", 0)
                failed = nums.get("failed", 0) + nums.get("error", 0)
                skipped = nums.get("skipped", 0) + nums.get("xfailed", 0)
                return {"discovered": passed + failed + skipped,
                        "executed": passed + failed,
                        "passed": passed, "failed": failed,
                        "skipped": skipped}
        return {}

    def package(self):
        py_ver = "python%d.%d" % (sys.version_info.major, sys.version_info.minor)
        site = os.path.join(self.package_folder, "lib", py_ver, "site-packages")
        os.makedirs(site, exist_ok=True)
        shutil.copytree(os.path.join(self.source_folder, "advocate"),
                        os.path.join(site, "advocate"))
        # Vendor runtime deps so consumers can import advocate offline.
        self._pip_install(_RUNTIME_DEPS, os.path.join(self.package_folder, "deps"))

    def package_info(self):
        self.cpp_info.libs = []
        py_ver = "python%d.%d" % (sys.version_info.major, sys.version_info.minor)
        self.runenv_info.prepend_path(
            "PYTHONPATH",
            os.path.join(self.package_folder, "lib", py_ver, "site-packages"))
        self.runenv_info.prepend_path(
            "PYTHONPATH", os.path.join(self.package_folder, "deps"))
