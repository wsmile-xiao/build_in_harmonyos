#!/usr/bin/env python3
"""Conan recipe — sedparse 0.1.2 (pure Python, setuptools metadata)."""

import json
import os
import re
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

UPSTREAM_TEST_FILES = [
    "test_errors.py",
    "test_misc.py",
    "test_output.py",
    "test_parser.py",
    "test_repr.py",
    "test_str.py",
]


class SedparseConan(ConanFile):
    name = "sedparse"
    version = "0.1.2"
    description = "GNU sed's parser translated from C to Python"
    license = "GPL-3.0-only"
    homepage = "https://github.com/aureliojargas/sedparse"
    url = "https://github.com/aureliojargas/sedparse"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "sedparse 0.1.2 supports Linux and OHOS only, got %s" % self.settings.os
            )

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        module = os.path.join(self.source_folder, "sedparse.py")
        with open(module, encoding="utf-8") as handle:
            source = handle.read()
        compile(source, module, "exec")
        if '__version__ = "0.1.2"' not in source:
            raise ConanException("sedparse.py does not declare version 0.1.2")
        self._run_upstream_tests()

    def _python(self):
        for candidate in (os.environ.get("HMBS_PYTHON3", ""), sys.executable):
            if candidate and os.path.isfile(candidate):
                return candidate
        return "python3"

    def _run_upstream_tests(self):
        python = self._python()
        proc = subprocess.run(
            [python, "-m", "unittest", "discover", "-s", "tests", "-v"],
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
            "command": "python -m unittest discover -s tests -v",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False)
        )
        self._run_doctest(python)
        self._run_reference_check(python)
        if status != "passed" or failed:
            raise ConanException(
                "upstream unittest failed: executed=%s failed=%s" % (executed, failed)
            )

    def _run_doctest(self, python):
        readme = os.path.join(self.source_folder, "README.md")
        if not os.path.isfile(readme):
            raise ConanException("README.md is missing, cannot run doctest")
        proc = subprocess.run(
            [python, "-m", "doctest", "README.md"],
            cwd=self.source_folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if proc.stdout:
            self.output.info("doctest output: %s" % proc.stdout.strip()[-1000:])
        if proc.returncode != 0:
            raise ConanException("README doctest failed: %s" % proc.stdout[-2000:])

    def _run_reference_check(self, python):
        ref_sed = os.path.join(self.source_folder, "tests", "reference.sed")
        ref_json = os.path.join(self.source_folder, "tests", "reference.json")
        if not os.path.isfile(ref_sed) or not os.path.isfile(ref_json):
            raise ConanException("reference.sed/reference.json are missing")
        proc = subprocess.run(
            [python, "sedparse.py", "-f", "tests/reference.sed"],
            cwd=self.source_folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if proc.returncode != 0:
            raise ConanException("reference parse failed: %s" % proc.stderr[-2000:])
        with open(ref_json, encoding="utf-8") as handle:
            expected = json.load(handle)
        actual = json.loads(proc.stdout)
        if actual != expected:
            raise ConanException("reference.json mismatch: parsed output differs")

    def package(self):
        site_packages = os.path.join(
            self.package_folder, "lib", "python", "site-packages"
        )
        copy(self, "sedparse.py", src=self.source_folder, dst=site_packages)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        wrapper = os.path.join(bindir, "sedparse")
        with open(wrapper, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("#!/bin/sh\n")
            handle.write('exec python3 -m sedparse "$@"\n')
        try:
            os.chmod(wrapper, 0o755)
        except OSError:
            pass

    def package_info(self):
        site_packages = os.path.join(
            self.package_folder, "lib", "python", "site-packages"
        )
        self.runenv_info.prepend_path("PYTHONPATH", site_packages)
        self.runenv_info.define_path("SEDPARSE_PACKAGE_ROOT", site_packages)
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
