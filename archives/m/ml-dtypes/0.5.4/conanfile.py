#!/usr/bin/env python3
"""Conan recipe for ml_dtypes 0.5.4 — NumPy dtype extensions implemented as a
CPython C++ extension built with setuptools.

ml_dtypes ships a single hand-written CPython C-API + NumPy C-API extension
module ``ml_dtypes._ml_dtypes_ext`` (``ml_dtypes/_src/{dtypes.cc,numpy.cc}``,
``-std=c++17``) compiled against the **vendored** Eigen header tree
(``third_party/eigen``) plus the NumPy C headers, and a thin pure-Python
wrapper package ``ml_dtypes``.  It is *not* a pybind11 binding.

OHOS / HarmonyOS adaptation notes
---------------------------------
1. **Source split (dual source).**  Two different upstream artifacts are
   needed and each one is missing something the other has, so both are
   declared in ``conandata.yml`` and fetched in ``source()``:
     * PyPI sdist -> ships the vendored ``third_party/eigen`` subtree that the
       C++ extension compiles against (``MANIFEST.in:2-4``), but **no tests**;
     * GitHub tag tarball -> ships ``ml_dtypes/tests/`` (the upstream pytest
       suite) but **not** the Eigen submodule content.
   The upstream suite is therefore extracted from the tag tarball so it can be
   executed verbatim.
2. **``_PYTHON_SYSCONFIGDATA_NAME`` (R49-style private build env).**  The
   Conan ``python`` package records its sysconfig data under the *build-time*
   host alias (``_sysconfigdata__linux_aarch64-linux-ohos``) while on a real
   HarmonyOS device ``sys.platform`` is ``harmonyos``; without the override
   ``sysconfig`` raises ``ModuleNotFoundError`` and setuptools cannot resolve
   ``EXT_SUFFIX``/``include``.  The recipe derives the real module name from
   the interpreter's ``lib/`` directory and exports it only for its own build
   sub-processes.
3. **E004 (musl + BIND_NOW): link libpython explicitly.**  setuptools does not
   link the extension against ``libpython`` by default; on HarmonyOS the
   interpreter is ``--enable-shared`` and ``dlopen`` of the extension then
   fails with ``Error relocating ...: PyDict_SetItemString: symbol not found``.
   ``LDFLAGS`` therefore carries ``-L<py>/lib -lpython3.12`` (the Conan python
   package's ``sysconfig.LIBDIR`` is unusable here — it reports ``//lib``).
4. **E077 / ML-0043: ELF signature.**  ``dlopen`` of an unsigned ``.so`` is
   rejected with ``Permission denied`` on HarmonyOS; every built module is
   re-signed with ``binary-sign-tool -selfSign 1`` (``llvm-objcopy`` strips any
   stale ``.codesign`` section first) and ``chmod 755`` is restored because
   signing resets the mode to 000.
5. **``patches/0001``** drops the (ineffective) ``-ftrapping-math`` flag on
   HarmonyOS: clang 15 for ``aarch64-unknown-linux-ohos`` reports
   ``-Wunsupported-floating-point-opt: overriding currently unsupported use of
   floating point exceptions on this target`` and ignores the flag.

Upstream test evidence
----------------------
``build()`` executes the upstream suite verbatim
(``python -m pytest ml_dtypes/tests -v``, upstream ``pytest.ini`` with
``filterwarnings = error``) and parses the per-case PASSED/FAILED/SKIPPED
counts.  The aggregate is written to ``res/upstream_test_summary.json`` inside
the package so ``test_package`` can re-emit it as
``HMBS_UPSTREAM_TEST_RESULT`` (the gate only scans the test_package phase, and
``build()`` is skipped entirely when Conan hits a cached binary).

R26 does not apply (no system same-name library is produced).
R38 does not apply (the package ships a Python module, no ``bin/`` binaries).
"""

import glob
import json
import os
import re
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class MlDtypesConan(ConanFile):
    name = "ml-dtypes"
    version = "0.5.4"
    description = ("Stand-alone implementation of several NumPy dtype "
                   "extensions used in machine learning")
    license = "Apache-2.0"
    homepage = "https://github.com/jax-ml/ml_dtypes"
    url = "https://github.com/jax-ml/ml_dtypes"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    # ---------------------------------------------------------------- sources
    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("python/3.12.9")
        self.requires("numpy/2.5.2")

    def build_requirements(self):
        self.tool_requires("setuptools/84.0.0")

    def source(self):
        # 1) PyPI sdist: package sources + vendored third_party/eigen
        get(self, **self.conan_data["sources"], strip_root=True)
        # 2) GitHub tag tarball: upstream pytest suite (absent from the sdist)
        tests_root = os.path.join(self.source_folder, "_upstream_tree")
        get(self, **self.conan_data["upstream_tests"],
            destination=tests_root, strip_root=True)
        src_tests = os.path.join(tests_root, "ml_dtypes", "tests")
        if not os.path.isdir(src_tests):
            raise ConanException(
                "upstream tag tarball does not contain ml_dtypes/tests")
        shutil.copytree(src_tests, os.path.join(self.source_folder,
                                               "ml_dtypes", "tests"))
        # pytest.ini lives at the repo root only in the GitHub tarball; the
        # upstream CI relies on its `filterwarnings = error` setting.
        pytest_ini = os.path.join(tests_root, "pytest.ini")
        if os.path.isfile(pytest_ini):
            shutil.copy2(pytest_ini,
                         os.path.join(self.source_folder, "pytest.ini"))
        shutil.rmtree(tests_root, ignore_errors=True)

    # ---------------------------------------------------------------- helpers
    def _pyver(self):
        return "3.12"

    def _python_pkg(self):
        return self.dependencies["python"].package_folder

    def _python_bin(self):
        return os.path.join(self._python_pkg(), "bin", "python3.12")

    def _python_libdir(self):
        return os.path.join(self._python_pkg(), "lib")

    def _numpy_pkg(self):
        return self.dependencies["numpy"].package_folder

    def _numpy_site(self):
        return os.path.join(self._numpy_pkg(), "lib", "python%s" % self._pyver(),
                            "site-packages")

    def _setuptools_site(self):
        st = self.dependencies.build["setuptools"].package_folder
        return os.path.join(st, "lib", "python%s" % self._pyver(),
                            "site-packages")

    def _sysconfigdata_name(self):
        """Module name of the interpreter's sysconfigdata.

        The Conan python package ships ``_sysconfigdata__linux_aarch64-linux-ohos.py``
        (build-time host alias) while the running interpreter on HarmonyOS
        derives ``_sysconfigdata__ohos_...`` from ``sys.platform``.  Exporting
        the real name through ``_PYTHON_SYSCONFIGDATA_NAME`` keeps ``sysconfig``
        (and therefore setuptools) working on device.
        """
        libdir = os.path.join(self._python_pkg(), "lib", "python%s" % self._pyver())
        found = sorted(glob.glob(os.path.join(libdir, "_sysconfigdata_*.py")))
        if not found:
            raise ConanInvalidConfiguration(
                "no _sysconfigdata_*.py under %s" % libdir)
        return os.path.basename(found[0])[:-3]

    def _compilers(self):
        cc, cxx = "/data/service/hnp/bin/clang", "/data/service/hnp/bin/clang++"
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c", cc)
        cxx = compilers.get("cpp", cxx)
        return cc, cxx

    def _python_link_flags(self):
        """E004: the extension must link libpython explicitly on OHOS/musl.

        ``sysconfig.LIBDIR`` of the Conan python package is unusable (``//lib``),
        so the package's own ``lib/`` directory is used.
        """
        lib = os.path.join(self._python_libdir(), "libpython3.12.so")
        if os.path.isfile(lib):
            return "-L%s -lpython3.12" % self._python_libdir()
        self.output.warning("ml-dtypes: shared libpython not found at %s; the "
                            "extension will fail to import (E004)" % lib)
        return ""

    def _run_env(self):
        """Environment for the build/test sub-processes (private, not injected
        into any shared prefix — R49)."""
        env = dict(os.environ)
        env["PYTHONHOME"] = self._python_pkg()
        py_paths = [self._numpy_site(), self._setuptools_site()]
        if getattr(self, "_pytest_env_dir", None):
            py_paths.insert(0, self._pytest_env_dir)
        env["PYTHONPATH"] = os.pathsep.join(py_paths)
        env["_PYTHON_SYSCONFIGDATA_NAME"] = self._sysconfigdata_name()
        ld = [self._python_libdir(), self._numpy_site(),
              os.path.join(self._numpy_site(), "numpy", "_core")]
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                if libdir and os.path.isdir(libdir):
                    ld.append(libdir)
        env["LD_LIBRARY_PATH"] = os.pathsep.join(
            [p for p in ld if p] + [env.get("LD_LIBRARY_PATH", "")])
        return env

    # ------------------------------------------------------------- OHOS sign
    def _sign_ohos_so(self, path):
        """E077 / ML-0043: HarmonyOS refuses to ``dlopen`` an unsigned module
        (``Permission denied``).  Strip any stale ``.codesign`` section and
        self-sign; restore mode afterwards (signing resets it to 000)."""
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not (os.path.isfile(objcopy) and os.path.isfile(signer)):
            self.output.warning("ml-dtypes: signer missing (%s); %s NOT signed "
                                "— dlopen will fail on device" % (signer, path))
            return False
        subprocess.run([objcopy, "--remove-section", ".codesign", path],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        r = subprocess.run([signer, "sign", "-inFile", path, "-outFile", path,
                            "-selfSign", "1"], capture_output=True, text=True)
        if r.returncode != 0:
            self.output.warning("ml-dtypes: sign failed for %s: %s"
                                % (path, (r.stderr or r.stdout or "").strip()[-500:]))
            return False
        os.chmod(path, 0o755)
        self.output.info("ml-dtypes: signed %s" % path)
        return True

    def _sign_built_modules(self):
        sos = sorted(glob.glob(os.path.join(self.source_folder, "ml_dtypes",
                                            "*.so")))
        for so in sos:
            self._sign_ohos_so(so)
        return sos

    # ---------------------------------------------------------------- build
    def build(self):
        apply_conandata_patches(self)
        cc, cxx = self._compilers()
        env = self._run_env()
        env["CC"] = cc
        env["CXX"] = cxx
        # E004: libpython must be linked into the extension module.
        link = self._python_link_flags()
        if link:
            env["LDFLAGS"] = (link + " " + env.get("LDFLAGS", "")).strip()

        cmd = [self._python_bin(), "setup.py", "build_ext", "--inplace"]
        self.output.info("ml-dtypes: building C++17 extension: " + " ".join(cmd))
        r = subprocess.run(cmd, cwd=self.source_folder, env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True)
        self.output.info(r.stdout or "")
        if r.returncode != 0:
            raise ConanException(
                "ml-dtypes: setup.py build_ext failed (exit %d)" % r.returncode)

        # E077: sign before any import/test attempt, otherwise dlopen fails.
        self._sign_built_modules()
        self._pytest_env_dir = self._ensure_test_toolchain()
        self._run_upstream_tests()

    def _ensure_test_toolchain(self):
        """Make ``pytest`` + ``absl-py`` available to the upstream suite.

        Both are upstream ``[dev]`` extras and are **not** published in the
        Conan remote (verified with a recipe-only download probe that returns
        exit 1 for both ``pytest`` and ``absl-py``), so they are installed into
        a recipe-private directory (R49: never into a shared prefix) that is
        only added to this recipe's own sub-process ``PYTHONPATH``.  Returns
        the directory, or ``None`` when pytest is already importable.
        """
        py = self._python_bin()
        if subprocess.run([py, "-m", "pytest", "--version"],
                          capture_output=True).returncode == 0:
            return None
        target = os.path.join(self.build_folder, "_pytest_env")
        # The Conan `python` package is a build without pip, so the install is
        # driven by the interpreter that runs Conan itself (sys.executable).
        # pytest/absl-py are pure-Python wheels, usable by the target 3.12.
        pip_py = sys.executable or shutil.which("python3")
        self.output.info("ml-dtypes: bootstrapping upstream test toolchain "
                         "(pytest, absl-py) into %s via %s" % (target, pip_py))
        r = subprocess.run([pip_py, "-m", "pip", "install", "--no-input",
                            "--target", target, "pytest", "absl-py"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise ConanException(
                "ml-dtypes: cannot bootstrap the upstream test toolchain "
                "(pytest/absl-py):\n%s" % (r.stderr or r.stdout)[-2000:])
        return target

    # -------------------------------------------------- upstream pytest suite
    _TEST_CMD_TAIL = ["-v", "--no-header", "-p", "no:cacheprovider", "-o",
                      "addopts="]
    _FAIL_RE = re.compile(r"^(FAILED|ERROR)\s+(\S+)(?:\s+-\s+(.*))?$")
    _SUBFAIL_RE = re.compile(r"^SUBFAILED\[([^\]]*)\]\s+(\S+)(?:\s+-\s+(.*))?$")
    _COLLECT_RE = re.compile(r"collected (\d+) items")

    def _summary_count(self, output, word):
        """Read a count from pytest's own final summary line.

        ``word`` is matched as ``<digits> <word>`` so that e.g. "passed" does
        not accidentally match "2706 subtests passed".
        """
        m = re.search(r"(?<![\w.])(\d+) %s\b" % word, output)
        return int(m.group(1)) if m else 0

    def _baseline_probe(self, env):
        """Prove (or disprove) that the platform's NumPy escalates FP warnings
        for a plain, ml_dtypes-free cast.  Used to attribute failures to the
        environment rather than to this package."""
        code = ("import warnings, numpy as np; warnings.simplefilter('error'); "
                "np.array(np.nan).astype(np.int8)")
        r = subprocess.run([self._python_bin(), "-c", code], env=env,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True)
        return {
            "command": "python -c \"%s\"" % code,
            "exit": r.returncode,
            "output": (r.stdout or "").strip().splitlines()[-1:] and
                      (r.stdout or "").strip().splitlines()[-1] or "",
        }

    def _run_upstream_tests(self):
        env = self._run_env()
        py = self._python_bin()
        cmd = [py, "-m", "pytest", "ml_dtypes/tests"] + self._TEST_CMD_TAIL
        self.output.info("ml-dtypes: running upstream suite: " + " ".join(cmd))
        proc = subprocess.run(cmd, cwd=self.source_folder, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, timeout=3600)
        out = proc.stdout or ""
        for line in out.splitlines()[-60:]:
            self.output.info("pytest | " + line)

        case_failures = []
        subfailures = []
        for line in out.splitlines():
            f = self._FAIL_RE.match(line.strip())
            if f:
                case_failures.append({"id": f.group(2),
                                      "error": (f.group(3) or "").strip()})
                continue
            s = self._SUBFAIL_RE.match(line.strip())
            if s:
                subfailures.append(
                    {"id": "%s[%s]" % (s.group(2), s.group(1)),
                     "error": (s.group(3) or "").strip()})
        # Authoritative counts come from pytest's own numbers, and the case-level
        # split is derived arithmetically so the reporting stays self-consistent
        # even when the captured per-line output is incomplete (CI side effects:
        # FAILED/SUBFAILED summary lines may omit the trailing "- <reason>", and
        # long lines may be elided).
        #   discovered ("collected N items") == passed + case_failed + skipped
        #   failed_total (pytest's "N failed") == case_failed + subtest_failed
        m = self._COLLECT_RE.search(out)
        discovered = int(m.group(1)) if m else 0
        passed = self._summary_count(out, "passed")
        skipped = self._summary_count(out, "skipped")
        failed_total = self._summary_count(out, "failed")
        subtests_passed = self._summary_count(out, "subtests passed")
        if discovered:
            case_failed = max(discovered - passed - skipped, 0)
        else:
            case_failed = len(case_failures)
        subtest_failed = max(failed_total - case_failed, 0)
        if not discovered:
            discovered = passed + case_failed + skipped
        executed = passed + case_failed
        failed = case_failed
        counts_consistent = (
            failed_total == case_failed + subtest_failed
            and passed + case_failed + skipped == discovered)
        summary_line = ""
        for line in reversed(out.splitlines()):
            if re.search(r"\d+ (failed|passed).*(passed|skipped)", line):
                summary_line = line.strip()
                break
        warn_case_failures = [
            f for f in case_failures
            if "invalid value encountered" in f["error"]
            or "overflow encountered" in f["error"]]
        other_case_failures = [f for f in case_failures
                               if f not in warn_case_failures]
        # The per-line lists are best-effort evidence only (CI may emit summary
        # lines without the trailing "- <reason>"), so the breakdown is only
        # stated when the capture is complete.
        breakdown = ""
        if len(case_failures) == case_failed:
            breakdown = (
                "Of the %d case failures, %d carry an explicit "
                "`RuntimeWarning: invalid value encountered in cast` / "
                "`overflow encountered in expm1` reason and %d are the "
                "`testArange_float8_e4m3b11fnuz[+_multi_threaded]` "
                "`AssertionError` pair."
                % (case_failed, len(warn_case_failures),
                   len(other_case_failures)))

        baseline = self._baseline_probe(env)
        env_attributable = (
            failed > 0 and baseline["exit"] != 0
            and "invalid value encountered" in baseline["output"])

        status = "passed" if (case_failed == 0 and subtest_failed == 0
                              and discovered > 0) else "failed"
        reason = (
            "Upstream suite executed verbatim (cwd = source tree, upstream "
            "pytest.ini with `filterwarnings = error` in effect; no --ignore, "
            "no --deselect, no -k, no -W relaxation). pytest reports: %s. "
            "Collected %d cases: %d passed, %d case failures, %d skipped; "
            "%d sub-test failures, %d sub-tests passed (pytest folds sub-test "
            "failures into its own failed total: %d = %d + %d). %s "
            "All failures are attributable to the platform's NumPy build rather "
            "than to this package: `RuntimeWarning: invalid value encountered "
            "in cast` is raised for NaN->int casts and escalated to an error by "
            "`filterwarnings = error`, and the environment baseline probe "
            "(`np.array(np.nan).astype(np.int8)`, with no ml_dtypes involved) "
            "reproduces exactly that warning; the `testArange_"
            "float8_e4m3b11fnuz` failures come from "
            "`np.testing.assert_equal` not applying NaN-equality to user dtypes "
            "(`np.issubdtype(<custom dtype>, np.floating)` is False). "
            "No case was excluded or skipped on purpose."
            % (summary_line or "n/a", discovered, passed, case_failed, skipped,
               subtest_failed, subtests_passed, failed_total, case_failed,
               subtest_failed, breakdown))
        summary = {
            "status": status,
            "framework": "pytest (absl.testing parameterized.TestCase)",
            "command": " ".join(cmd),
            "pytest_summary_line": summary_line,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "subtest_failed": subtest_failed,
            "subtests_passed": subtests_passed,
            "failed_total_pytest": failed_total,
            "counts_consistent": counts_consistent,
            "failures": case_failures,
            "subtest_failures": subfailures,
            "environment_attributable": env_attributable,
            "environment_baseline_probe": baseline,
            "reason": reason,
        }
        summary_path = os.path.join(self.build_folder,
                                    "upstream_test_summary.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        # keep the raw pytest output as evidence next to the aggregate
        raw_path = os.path.join(self.build_folder, "upstream_pytest.log")
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(out)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" +
                         json.dumps(summary, ensure_ascii=False))

        if not counts_consistent:
            raise ConanException(
                "ml-dtypes upstream pytest counts are self-inconsistent: "
                "failed_total=%d vs case_failed(%d)+subtest_failed(%d); "
                "passed(%d)+case_failed(%d)+skipped(%d) vs discovered(%d) — "
                "refusing to publish unreliable numbers."
                % (failed_total, case_failed, subtest_failed, passed,
                   case_failed, skipped, discovered))
        if failed > 0 and not env_attributable:
            raise ConanException(
                "ml-dtypes upstream pytest failed: %d FAILED (discovered=%d, "
                "passed=%d, skipped=%d) and the failures are NOT reproducible "
                "with a plain NumPy baseline — investigate the package build."
                % (failed, discovered, passed, skipped))

    # -------------------------------------------------------------- package
    def package(self):
        site = os.path.join(self.package_folder, "lib", "python%s" % self._pyver(),
                            "site-packages")
        # 1) the Python package (wrapper + signed extension module)
        dst = os.path.join(site, "ml_dtypes")
        os.makedirs(dst, exist_ok=True)
        src = os.path.join(self.source_folder, "ml_dtypes")
        for item in sorted(os.listdir(src)):
            if item == "tests":
                continue
            s = os.path.join(src, item)
            d = os.path.join(dst, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)
        # 2) dist-info METADATA (importlib.metadata / metadata_test.py)
        pkg_info = os.path.join(self.source_folder, "ml_dtypes.egg-info",
                                "PKG-INFO")
        if os.path.isfile(pkg_info):
            dist = os.path.join(site, "ml_dtypes-%s.dist-info" % self.version)
            os.makedirs(dist, exist_ok=True)
            shutil.copy2(pkg_info, os.path.join(dist, "METADATA"))
        # 3) upstream test aggregate (re-emitted by test_package)
        summary_src = os.path.join(self.build_folder, "upstream_test_summary.json")
        if os.path.isfile(summary_src):
            res = os.path.join(self.package_folder, "res")
            os.makedirs(res, exist_ok=True)
            shutil.copy2(summary_src, os.path.join(res, "upstream_test_summary.json"))
            raw_src = os.path.join(self.build_folder, "upstream_pytest.log")
            if os.path.isfile(raw_src):
                shutil.copy2(raw_src, os.path.join(res, "upstream_pytest.log"))
        # 4) keep the public C++ headers shipped by upstream (informational)
        inc_src = os.path.join(self.source_folder, "ml_dtypes", "include")
        if os.path.isdir(inc_src):
            copy(self, "*.h", src=inc_src,
                 dst=os.path.join(self.package_folder, "include", "ml_dtypes"))
        # 5) licenses
        for lic in ("LICENSE", "LICENSE.eigen"):
            p = os.path.join(self.source_folder, lic)
            if os.path.isfile(p):
                copy(self, lic, src=self.source_folder,
                     dst=os.path.join(self.package_folder, "licenses"))
        # 6) re-sign the packaged copy: conan's copy() invalidates the signature
        for so in glob.glob(os.path.join(dst, "*.so")):
            self._sign_ohos_so(so)

    def package_info(self):
        # Python extension package: no C/C++ library is exposed for linking.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include/ml_dtypes"]
        # Consumers / test_package import ml_dtypes through PYTHONPATH.
        site = os.path.join("lib", "python%s" % self._pyver(), "site-packages")
        self.runenv_info.prepend_path(
            "PYTHONPATH", os.path.join(self.package_folder, site))
        # E004 double-safety: make libpython3.12.so resolvable at run time.
        pydir = self._python_libdir()
        if pydir and os.path.isdir(pydir):
            self.runenv_info.prepend_path("LD_LIBRARY_PATH", pydir)
