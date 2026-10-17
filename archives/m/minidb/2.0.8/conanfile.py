import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, get


class MiniDBConan(ConanFile):
    name = "minidb"
    version = "2.0.8"
    # This is an installable runtime Python package, not a recipe extension.
    # Conan's special "python-require" type exports recipe code only and skips
    # binary package creation, which would also skip build() and upstream tests.
    package_type = "unknown"
    license = "ISC"
    homepage = "https://github.com/thp/minidb"
    description = "Simple Python object store backed by SQLite 3"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"
    tool_requires = "pytest/9.1.1"

    def layout(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"]["minidb"], strip_root=True)
        apply_conandata_patches(self)

    def _pytest_env(self):
        env = os.environ.copy()
        site_paths = [self.source_folder]
        bin_paths = []
        for dep in self.dependencies.build.values():
            folder = getattr(dep, "package_folder", None)
            if not folder:
                continue
            lib = os.path.join(folder, "lib")
            if os.path.isdir(lib):
                for current, directories, _ in os.walk(lib):
                    if os.path.basename(current) == "site-packages":
                        site_paths.append(current)
                        directories[:] = []
            bindir = os.path.join(folder, "bin")
            if os.path.isdir(bindir):
                bin_paths.append(bindir)

        current_pythonpath = env.get("PYTHONPATH")
        if current_pythonpath:
            site_paths.append(current_pythonpath)
        env["PYTHONPATH"] = os.pathsep.join(dict.fromkeys(site_paths))
        current_path = env.get("PATH")
        if current_path:
            bin_paths.append(current_path)
        env["PATH"] = os.pathsep.join(dict.fromkeys(bin_paths))
        return env

    def build(self):
        # pytest is a pinned Conan build tool; load its package paths explicitly
        # because the package layout may target another Python minor version.
        expected_tests = 42  # 42 top-level test_* functions in the pinned sdist.
        env = self._pytest_env()
        collect_log = os.path.join(self.build_folder, "minidb-pytest-collect.log")
        collect = subprocess.run(
            [sys.executable, "-m", "pytest", "--collect-only", "-q",
             "-p", "no:cacheprovider", "test/test_minidb.py"],
            cwd=self.source_folder, env=env, text=True, capture_output=True,
            timeout=180, check=False)
        summary = collect.stdout + collect.stderr
        with open(collect_log, "w", encoding="utf-8") as handle:
            handle.write(summary)
        if collect.returncode != 0:
            raise ConanException("minidb upstream pytest collection failed: %s" %
                                 summary[-3000:])
        counts = re.findall(r"(\d+) tests? collected", summary)
        if not counts or int(counts[-1]) != expected_tests:
            raise ConanException(
                "minidb upstream pytest collected %s tests; expected %d: %s" %
                (counts[-1] if counts else "unknown", expected_tests,
                 summary[-1000:]))
        self.output.info("minidb upstream pytest collected %d/%d tests" %
                         (int(counts[-1]), expected_tests))

        report = os.path.join(self.build_folder, "minidb-upstream-tests.xml")
        run_log = os.path.join(self.build_folder, "minidb-pytest-run.log")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "test/test_minidb.py", "-q",
             "-p", "no:cacheprovider", "--junitxml=" + report],
            cwd=self.source_folder, env=env, text=True, capture_output=True,
            timeout=600, check=False)
        run_output = result.stdout + result.stderr
        with open(run_log, "w", encoding="utf-8") as handle:
            handle.write(run_output)
        self.output.info(run_output.strip())
        if result.returncode != 0 or not os.path.isfile(report):
            raise ConanException(
                "minidb upstream pytest run failed (exit %s): %s" %
                (result.returncode, run_output[-3000:]))
        suite = ET.parse(report).getroot()
        suites = [suite] if suite.tag == "testsuite" else list(suite.iter("testsuite"))
        executed = sum(int(item.get("tests", "0")) for item in suites)
        failures = sum(int(item.get("failures", "0")) for item in suites)
        errors = sum(int(item.get("errors", "0")) for item in suites)
        skipped = sum(int(item.get("skipped", "0")) for item in suites)
        passed = executed - failures - errors - skipped
        self.output.info(
            "minidb upstream pytest result: %d/%d passed; failed=%d, errors=%d, skipped=%d" %
            (passed, expected_tests, failures, errors, skipped))
        if executed != expected_tests or passed != expected_tests or failures or errors or skipped:
            raise ConanException(
                "minidb upstream pytest must pass all %d tests; got %d/%d passed" %
                (expected_tests, passed, executed))

    def package(self):
        source_path = os.path.join(self.source_folder, "minidb.py")
        if not os.path.isfile(source_path):
            raise ConanException("upstream minidb.py is missing")
        site = os.path.join(self.package_folder, "lib", "python3",
                            "site-packages")
        os.makedirs(site, exist_ok=True)
        shutil.copy2(source_path, os.path.join(site, "minidb.py"))

    def package_info(self):
        self.cpp_info.libs = []
        self.runenv_info.append_path(
            "PYTHONPATH",
            os.path.join(self.package_folder, "lib", "python3", "site-packages"))
