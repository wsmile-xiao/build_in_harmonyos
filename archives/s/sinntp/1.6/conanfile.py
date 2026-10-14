#!/usr/bin/env python3
"""Conan recipe — sinntp 1.6 (pure Python, stdlib only)."""

import json
import os
import re
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class SinntpConan(ConanFile):
    name = "sinntp"
    version = "1.6"
    description = "tiny non-interactive NNTP client (get/list/pull/push plus plugins)"
    license = "GPL-2.0-only"
    homepage = "https://jwilk.net/software/sinntp"
    url = "https://github.com/jwilk/sinntp"
    topics = ("nntp", "news", "usenet", "client")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "sinntp 1.6 supports Linux and OHOS only, got %s" % self.settings.os
            )

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        self._patch_nntplib_compat()

    def _patch_nntplib_compat(self):
        # sinntp 1.6 imports nntplib at module top, but nntplib was removed
        # from the stdlib in Python 3.13 (PEP 594). Without this, even
        # `sinntp --version/--help` fails with ModuleNotFoundError on the
        # HarmonyOS PC toolchain (Python 3.14). Make the import lazy with a
        # minimal stub so offline entry points work; network commands raise
        # a clear NNTPError when the real nntplib is absent.
        path = os.path.join(self.source_folder, "sinntp")
        with open(path, encoding="utf-8") as handle:
            content = handle.read()
        if "_SinntpNntplibStub" in content:
            return
        old_from = (
            "from nntplib import NNTP, NNTP_PORT, "
            "NNTPTemporaryError, NNTPError"
        )
        new_from = (
            "try:\n"
            "    from nntplib import NNTP, NNTP_PORT, "
            "NNTPTemporaryError, NNTPError\n"
            "except ImportError:  # Python >= 3.13 removed nntplib (PEP 594)\n"
            "    NNTP_PORT = 119\n"
            "    class NNTPError(Exception):\n"
            "        pass\n"
            "    class NNTPTemporaryError(NNTPError):\n"
            "        pass\n"
            "    class NNTP:\n"
            "        def __init__(self, *args, **kwargs):\n"
            "            raise NNTPError(\n"
            "                'nntplib is unavailable on this Python '\n"
            "                '(removed in Python 3.13, PEP 594); '\n"
            "                'network commands require a Python with nntplib'\n"
            "            )"
        )
        if old_from not in content:
            raise ConanException(
                "sinntp nntplib import line not found; cannot apply compat patch"
            )
        content = content.replace(old_from, new_from, 1)
        old_import = "\nimport nntplib\n"
        new_import = (
            "\ntry:\n"
            "    import nntplib\n"
            "except ImportError:  # Python >= 3.13 removed nntplib (PEP 594)\n"
            "    class _SinntpNntplibStub:\n"
            "        _MAXLINE = 1 << 20\n"
            "    nntplib = _SinntpNntplibStub()\n"
        )
        if old_import not in content:
            raise ConanException(
                "sinntp 'import nntplib' not found; cannot apply compat patch"
            )
        content = content.replace(old_import, new_import, 1)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        compile(content, path, "exec")

    def build(self):
        main = os.path.join(self.source_folder, "sinntp")
        with open(main, encoding="utf-8") as handle:
            source = handle.read()
        compile(source, main, "exec")
        if "__version__ = '1.6'" not in source:
            raise ConanException("sinntp main script does not declare version 1.6")
        self._run_upstream_tests()

    def _python(self):
        for candidate in (os.environ.get("HMBS_PYTHON3", ""), sys.executable):
            if candidate and os.path.isfile(candidate):
                return candidate
        return "python3"

    def _run_upstream_tests(self):
        python = self._python()
        proc = subprocess.run(
            [python, "tests.py", "-v"],
            cwd=self.source_folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        output = proc.stdout or ""
        tail = output.splitlines()[-25:]
        for line in tail:
            self.output.info("upstream: %s" % line)
        discovered = None
        for line in output.splitlines():
            match = re.search(r"^Ran (\d+) tests?", line.strip())
            if match:
                discovered = int(match.group(1))
        passed = 0
        failed = 0
        skipped = 0
        for line in output.splitlines():
            stripped = line.strip()
            if re.search(r"\.\.\. ok$", stripped):
                passed += 1
            elif re.search(r"\.\.\. FAIL$", stripped):
                failed += 1
            elif re.search(r"\.\.\. ERROR$", stripped):
                failed += 1
            elif re.search(r"\.\.\. skipped", stripped):
                skipped += 1
            elif re.search(r"\.\.\. expected failure$", stripped):
                passed += 1
            elif re.search(r"\.\.\. unexpected success$", stripped):
                failed += 1
        if discovered is None:
            raise ConanException(
                "unittest printed no 'Ran N tests' summary; output tail: %s" % tail
            )
        executed = passed + failed
        if not (passed + failed == executed
                and executed + skipped <= discovered
                and executed <= discovered):
            raise ConanException(
                "unittest counts inconsistent "
                "(discovered=%s executed=%s passed=%s failed=%s skipped=%s)"
                % (discovered, executed, passed, failed, skipped)
            )
        if discovered != executed + skipped:
            raise ConanException(
                "unittest verbose lines (%s) do not match 'Ran %s tests'"
                % (executed + skipped, discovered)
            )
        status = "passed" if (failed == 0 and proc.returncode == 0) else "failed"
        result = {
            "status": status,
            "framework": "unittest",
            "command": "python3 tests.py -v",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False)
        )
        if status != "passed" or failed:
            raise ConanException(
                "upstream unittest failed: executed=%s failed=%s" % (executed, failed)
            )

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        for script in ("sinntp", "nntp-get", "nntp-list", "nntp-pull", "nntp-push"):
            copy(self, script, src=self.source_folder, dst=bindir)
        for module in ("plugins.py", "utils.py", "tests.py"):
            copy(self, module, src=self.source_folder, dst=bindir)
        site_packages = os.path.join(
            self.package_folder, "lib", "python", "site-packages"
        )
        os.makedirs(site_packages, exist_ok=True)
        for module in ("plugins.py", "utils.py"):
            copy(self, module, src=self.source_folder, dst=site_packages)
        for executable in ("sinntp", "nntp-get", "nntp-list", "nntp-pull", "nntp-push"):
            path = os.path.join(bindir, executable)
            if os.path.isfile(path):
                try:
                    os.chmod(path, 0o755)
                except OSError:
                    pass
        copy(self, "COPYING", src=os.path.join(self.source_folder, "doc"),
             dst=os.path.join(self.package_folder, "licenses"))
        _ = shutil.which("python3")

    def package_info(self):
        site_packages = os.path.join(
            self.package_folder, "lib", "python", "site-packages"
        )
        self.runenv_info.prepend_path("PYTHONPATH", site_packages)
        self.runenv_info.define_path("SINNTP_PACKAGE_ROOT", site_packages)
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
