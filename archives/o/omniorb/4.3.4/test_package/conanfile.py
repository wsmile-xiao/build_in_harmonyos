#!/usr/bin/env python3
"""Conan test_package — omniorb 4.3.4

Consumer validation (2 cases):
  1. omniidl_codegen — run the packaged omniidl IDL compiler on mini.idl
     and require non-empty generated stubs (proves the tool + its Python
     backends work from the package layout).
  2. echo_collocated — build the upstream echo example pattern against
     the packaged libraries (ORB_init, RootPOA servant activation,
     collocated call, exact reply match).
"""
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class OmniorbTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def generate(self):
        # E092: CMake has no Platform/HarmonyOS module, so the default
        # CMakeToolchain (CMAKE_SYSTEM_NAME=HarmonyOS from the OHOS
        # profile) fails configure with "System is unknown to cmake" and
        # the compiler check errors out. OHOS is Linux-kernel based and
        # this consumer test is a plain POSIX C++ binary with no
        # Linux-only platform logic, so build it under the Linux platform
        # module (precedent: ball/1.5.0, uchardet/0.0.7, zstr/1.1.0, ruy).
        # Both variables and cache_variables are set (ruy precedent) so
        # the toolchain file and the -D command line agree. Non-OHOS
        # builds see no change.
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Consumer-side mirror of the main recipe compiler fallback
        # (aggregated #1, adapted): the toolchain file bakes the
        # profile-pinned compiler path
        # (/data/service/hnp/bin/clang(++), see ci/conan/profiles/ohos-aarch64).
        # On runners where that driver is dead (Error 127 / identification
        # unknown, 2026-10-01 preflight: CMAKE_CXX_COMPILER pointed at the
        # dead hnp clang++ while the main package had already fallen back
        # to .harmonybrew clang), probe here and pin the working fallback
        # directly in the toolchain so healthy runners see zero change
        # (only CC/CXX paths, never flags).
        (_pin_c, _pin_cxx), (_eff_c, _eff_cxx) = self._effective_compilers()
        if _eff_c != _pin_c:
            tc.variables["CMAKE_C_COMPILER"] = _eff_c
            tc.cache_variables["CMAKE_C_COMPILER"] = _eff_c
        if _eff_cxx != _pin_cxx:
            tc.variables["CMAKE_CXX_COMPILER"] = _eff_cxx
            tc.cache_variables["CMAKE_CXX_COMPILER"] = _eff_cxx
        # The packaged omniidl lives in the tested package's bindir, which
        # is not on PATH during cmake.configure (2026-10-01 preflight:
        # find_program(OMNIIDL_BIN omniidl REQUIRED) failed even though the
        # main package had installed bin/omniidl). Pass its absolute path
        # explicitly so the consumer build does not depend on PATH luck
        # (precedent: acorn/afdko test_packages resolve
        # self.dependencies[tested_reference_str].package_folder/bin).
        # Healthy runners: same file find_program would have found.
        _omniidl = self._omniidl_bin()
        if _omniidl:
            tc.variables["OMNIIDL_BIN"] = _omniidl
            tc.cache_variables["OMNIIDL_BIN"] = _omniidl
        tc.generate()
        self._scrub_toolchain(_pin_c, _eff_c, _pin_cxx, _eff_cxx)
        # 2026-10-02: omniidl is a Python script (`import _omniidl` +
        # `import omniidl.main`). The main recipe now normalizes the
        # install layout AND exports PYTHONPATH via runenv/buildenv, but
        # keep an explicit consumer-side belt-and-suspenders here so the
        # CMake custom command (build time) and `self.run(env="conanrun")`
        # (test time) resolve the backends even if aggregation ordering
        # differs. Only existing package dirs are exported.
        self._export_omniidl_pythonpath()

    def _package_folder(self):
        try:
            return self.dependencies[
                self.tested_reference_str].package_folder
        except Exception:
            try:
                return self.dependencies["omniorb"].package_folder
            except Exception:
                return None

    def _package_python_dirs(self):
        import glob as _glob
        pkg = self._package_folder()
        if not pkg:
            return []
        dirs = []
        for cand in (_glob.glob(os.path.join(
                pkg, "lib", "python*", "site-packages"))
                + [os.path.join(pkg, "lib", "python"),
                   os.path.join(pkg, "lib")]):
            try:
                ok = os.path.isdir(cand)
            except Exception:
                ok = False
            if ok and cand not in dirs:
                dirs.append(cand)
        return dirs

    def _export_omniidl_pythonpath(self):
        from conan.tools.env import Environment
        dirs = self._package_python_dirs()
        if not dirs:
            self.output.warning("test_package omniidl PYTHONPATH: "
                                "no package python dirs found")
            return
        self.output.info("test_package omniidl PYTHONPATH: %s"
                         % os.pathsep.join(dirs))
        env = Environment()
        for cand in dirs:
            try:
                env.append_path("PYTHONPATH", cand)
            except Exception:
                pass
        try:
            env.vars(self, scope="build").save_script(
                "zz_omniidl_pythonpath")
        except Exception as exc:
            self.output.warning("test_package PYTHONPATH build script "
                                "failed: %s" % (exc,))
        try:
            env.vars(self, scope="run").save_script(
                "zz_omniidl_pythonpath_run")
        except Exception as exc:
            self.output.warning("test_package PYTHONPATH run script "
                                "failed: %s" % (exc,))

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _omniidl_bin(self):
        # Resolve the packaged IDL compiler to an absolute path. Never rely
        # on bare-name PATH lookup inside build()/test().
        try:
            pkg = self.dependencies[self.tested_reference_str].package_folder
        except Exception:
            try:
                pkg = self.dependencies["omniorb"].package_folder
            except Exception:
                pkg = None
        if pkg:
            for name in ("omniidl", "omniidl.exe"):
                cand = os.path.join(pkg, "bin", name)
                if os.path.isfile(cand):
                    self.output.info("test_package omniidl: %s" % cand)
                    return cand
            # Fallback: search bin/ for any omniidl* executable.
            bindir = os.path.join(pkg, "bin")
            try:
                names = os.listdir(bindir)
            except OSError:
                names = []
            for name in names:
                if name.startswith("omniidl"):
                    cand = os.path.join(bindir, name)
                    if os.path.isfile(cand):
                        self.output.info("test_package omniidl: %s" % cand)
                        return cand
            self.output.warning("test_package omniidl not found under %s/bin (%s)"
                                % (pkg, sorted(names)))
        found = shutil.which("omniidl")
        if found:
            self.output.info("test_package omniidl from PATH: %s" % found)
            return found
        return None

    def _pinned_compilers(self):
        # self.conf may miss the entry in the test_package context, so
        # fall back to the repo-canonical profile values instead of
        # returning None (which previously silenced the fallback and left
        # the dead hnp path in the toolchain).
        comp_c = comp_cxx = None
        try:
            comp = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict)
        except Exception:
            comp = {}
        if isinstance(comp, dict):
            comp_c = comp.get("c")
            comp_cxx = comp.get("cpp", comp.get("cxx"))
        if not comp_c:
            comp_c = "/data/service/hnp/bin/clang"
        if not comp_cxx:
            comp_cxx = "/data/service/hnp/bin/clang++"
        return comp_c, comp_cxx

    @staticmethod
    def _probe_compiler(exe):
        import subprocess
        if not exe or not isinstance(exe, str):
            return False, "empty compiler entry"
        binpath = exe.split()[0]
        if not os.path.isfile(binpath):
            found = shutil.which(binpath)
            if not found:
                return False, "not a file and not on PATH: %s" % binpath
            binpath = found
        try:
            proc = subprocess.run(
                [binpath, "--version"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=60, text=True, errors="replace")
        except Exception as exc:
            return False, "exec failed: %r" % (exc,)
        out = (proc.stdout or "")[:400]
        if proc.returncode != 0:
            return False, "rc=%s out=%s" % (proc.returncode, out)
        first = out.splitlines()[0] if out.strip() else "<empty output>"
        return True, "%s [%s]" % (binpath, first)

    def _fallback_compiler(self, kind, pinned):
        names = (["clang", "cc", "gcc"] if kind == "c"
                 else ["clang++", "c++", "g++", "clang"])
        cands = []
        try:
            sibdir = os.path.dirname((pinned or "").split()[0])
        except Exception:
            sibdir = ""
        if sibdir:
            for name in names:
                path = os.path.join(sibdir, name)
                if os.path.isfile(path) and path not in cands:
                    cands.append(path)
        # The 2026-10-01 preflight main package fell back to
        # /storage/Users/currentUser/.harmonybrew/bin/clang(++); that dir
        # is not in the profile PATH, so check it explicitly before the
        # generic PATH lookup. Same-device static prefixes only.
        for base in ("/storage/Users/currentUser/.harmonybrew/bin",
                     "/storage/Users/currentUser/usr/local/bin"):
            for name in names:
                path = os.path.join(base, name)
                if os.path.isfile(path) and path not in cands:
                    cands.append(path)
        for name in names:
            path = shutil.which(name)
            if path and path not in cands:
                cands.append(path)
        for path in cands:
            ok, info = self._probe_compiler(path)
            self.output.info("test_package compiler fallback probe %s=%s ok=%s (%s)"
                             % (kind, path, ok, info))
            if ok:
                return path
        return None

    def _effective_compilers(self):
        pin_c, pin_cxx = self._pinned_compilers()
        ok_c, info_c = self._probe_compiler(pin_c)
        ok_cxx, info_cxx = self._probe_compiler(pin_cxx)
        self.output.info("test_package compiler probe c=%s ok=%s (%s)"
                         % (pin_c, ok_c, info_c))
        self.output.info("test_package compiler probe cpp=%s ok=%s (%s)"
                         % (pin_cxx, ok_cxx, info_cxx))
        eff_c = pin_c if ok_c else self._fallback_compiler("c", pin_c)
        eff_cxx = (pin_cxx if ok_cxx
                   else self._fallback_compiler("cpp", pin_cxx))
        if (not ok_c and not eff_c) or (not ok_cxx and not eff_cxx):
            raise ConanException(
                "test_package: pinned compiler dead (c=%s (%s) cpp=%s (%s)) "
                "and no working fallback on PATH; refusing to configure "
                "against a dead driver" % (pin_c, info_c, pin_cxx, info_cxx))
        return (pin_c, pin_cxx), (eff_c, eff_cxx)

    def _scrub_toolchain(self, pin_c, eff_c, pin_cxx, eff_cxx):
        # CMakeToolchain already wrote conan_toolchain.cmake with the
        # pinned paths; when a fallback is active, replace the dead paths
        # on disk as well so any direct -P/toolchain use agrees with the
        # -D command line. No-op on healthy runners.
        if eff_c == pin_c and eff_cxx == pin_cxx:
            return
        roots = [self.build_folder, getattr(self, "base_build_folder", None)]
        seen = set()
        for root in roots:
            if not root or root in seen:
                continue
            seen.add(root)
            if not os.path.isdir(root):
                continue
            for dirpath, _dirnames, filenames in os.walk(root):
                for name in filenames:
                    if name != "conan_toolchain.cmake":
                        continue
                    path = os.path.join(dirpath, name)
                    try:
                        with open(path, "r", encoding="utf-8", errors="replace") as handle:
                            content = handle.read()
                    except OSError:
                        continue
                    fixed = content
                    if eff_c != pin_c:
                        fixed = fixed.replace(pin_c, eff_c)
                    if eff_cxx != pin_cxx:
                        fixed = fixed.replace(pin_cxx, eff_cxx)
                    if fixed != content:
                        try:
                            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                                handle.write(fixed)
                        except OSError as exc:
                            self.output.warning("cannot scrub %s: %s" % (path, exc))
                            continue
                        self.output.info("scrubbed dead compiler path in %s" % path)

    def _compiler_fallback_vars(self):
        # Explicit -D variables for cmake.configure (same effective
        # compilers as generate() plus the packaged omniidl path);
        # healthy runners return only OMNIIDL_BIN.
        (_pin_c, _pin_cxx), (_eff_c, _eff_cxx) = self._effective_compilers()
        variables = {}
        if _eff_c != _pin_c:
            variables["CMAKE_C_COMPILER"] = _eff_c
        if _eff_cxx != _pin_cxx:
            variables["CMAKE_CXX_COMPILER"] = _eff_cxx
        _omniidl = self._omniidl_bin()
        if _omniidl:
            variables["OMNIIDL_BIN"] = _omniidl
        return variables

    def _parse_upstream_output(self, out):
        # Deterministic log source: parse test_upstream_checks output line
        # by line. discovered/executed/passed/failed/skipped come ONLY
        # from the UPSTREAM_CHECK_SUMMARY line, cross-checked against the
        # per-case UPSTREAM_CHECK_CASE lines; mismatch means the data
        # source is contradictory. No string counting with arithmetic
        # fix-ups.
        case_re = re.compile(r"^UPSTREAM_CHECK_CASE\s+\S+\s+(PASS|FAIL)\b", re.M)
        summary_re = re.compile(
            r"^UPSTREAM_CHECK_SUMMARY\s+discovered=(\d+)\s+executed=(\d+)\s+passed=(\d+)"
            r"\s+failed=(\d+)\s+skipped=(\d+)\s*$",
            re.M)
        cpass = cfail = 0
        for m in case_re.finditer(out or ""):
            if m.group(1) == "PASS":
                cpass += 1
            else:
                cfail += 1
        nlines = 0
        vals = None
        for m in summary_re.finditer(out or ""):
            nlines += 1
            try:
                vals = tuple(int(m.group(i)) for i in range(1, 6))
            except ValueError:
                vals = None
        if vals is None:
            return -1, -1, cpass, cfail, -1, nlines
        discovered, executed, passed, failed, skipped = vals
        if (passed, failed) != (cpass, cfail):
            return -1, -1, cpass, cfail, skipped, -2
        return discovered, executed, passed, failed, skipped, nlines

    def _gather_bin(self, names):
        # Locate a test binary in the CMake build bindirs (PATH fallback).
        try:
            bindirs = self.cpp.build.bindirs
        except Exception:
            bindirs = []
        for bindir in bindirs or []:
            for name in names:
                cand = os.path.join(bindir, name)
                if os.path.isfile(cand):
                    return cand
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        return None

    def _run_upstream_checks(self):
        # Upstream evidence: run test_upstream_checks (8 hardware-free
        # functional checks against the packaged 4.3.4 artifacts), measured
        # on the real machine. Formal upstream suite is 0 (no tests/ dir,
        # no check target in any of the 267 GNUmakefile.in/mk files; audit
        # retained in MANIFEST.yml); these 8 checks are the upstream
        # evidence reported with framework custom.
        EXPECTED_TOTAL = 8
        binary = self._gather_bin(
            ["test_upstream_checks", "test_upstream_checks.exe"])
        if not binary:
            reason = "upstream check binary missing: test_upstream_checks"
            self.output.error(reason)
            umarker = {"status": "failed", "framework": "custom",
                       "command": "test_upstream_checks (+ omniidl -V)",
                       "discovered": EXPECTED_TOTAL, "executed": 0, "passed": 0,
                       "failed": 0, "skipped": EXPECTED_TOTAL, "reason": reason}
            uline = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(umarker, ensure_ascii=False)
            self.output.info(uline)
            print(uline, flush=True)
            raise ConanException(reason)
        # The check binary links the packaged shared libs and popen()s
        # the packaged omniidl (Python backends via PYTHONPATH), so the
        # subprocess env must carry the same runenv the self.run(conanrun)
        # channel provides: package lib dir for the loader plus the
        # package python dirs for omniidl. Only existing dirs are added.
        env = dict(os.environ)
        try:
            pkg = self._package_folder()
            if pkg:
                libdir = os.path.join(pkg, "lib")
                if os.path.isdir(libdir):
                    old = env.get("LD_LIBRARY_PATH", "")
                    if libdir not in old.split(os.pathsep):
                        env["LD_LIBRARY_PATH"] = (
                            libdir + (os.pathsep + old if old else ""))
                for pydir in self._package_python_dirs():
                    old_py = env.get("PYTHONPATH", "")
                    if pydir not in old_py.split(os.pathsep):
                        env["PYTHONPATH"] = (
                            pydir + (os.pathsep + old_py if old_py else ""))
        except Exception as exc:
            self.output.warning("upstream env setup failed: %s" % (exc,))
        proc = subprocess.run([binary], stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT,
                              text=True, timeout=300, check=False,
                              cwd=self.build_folder, env=env)
        out = proc.stdout or ""
        tail = out[-4000:]
        self.output.info("upstream checks rc=%s tail:\n%s" % (proc.returncode, tail))
        discovered, executed, passed, failed, skipped, nlines = \
            self._parse_upstream_output(out)
        # Self-check identities: passed+failed==executed,
        # executed+skipped==discovered==8, all fields non-negative ints,
        # exactly 1 summary line, per-case counts agree with the summary.
        # On violation fix the data source, never fudge the numbers.
        ok_identity = (discovered == EXPECTED_TOTAL and nlines == 1
                       and passed + failed == executed
                       and executed + skipped == discovered
                       and executed > 0
                       and all(v is not None and v >= 0
                               for v in (discovered, executed, passed,
                                         failed, skipped)))
        # Non-empty evidence: the CLI check must really have run and passed
        # (an empty-vs-empty comparison reporting 0 failures is not a pass).
        has_cli_evidence = ("cli/omniidl_version PASS" in out)
        if not ok_identity or not has_cli_evidence:
            reason = ("upstream checks incomplete: rc=%s summary_lines=%s discovered=%s "
                      "executed=%s passed=%s failed=%s skipped=%s cli_evidence=%s; tail: %s"
                      % (proc.returncode, nlines, discovered, executed, passed, failed,
                         skipped, has_cli_evidence, tail[-800:]))
            self.output.warning(reason)
            umarker = {"status": "failed", "framework": "custom",
                       "command": "test_upstream_checks (+ omniidl -V)",
                       "discovered": discovered if discovered >= 0 else EXPECTED_TOTAL,
                       "executed": executed if executed >= 0 else 0,
                       "passed": passed if passed >= 0 else 0,
                       "failed": failed if failed >= 0 else 0,
                       "skipped": skipped if skipped is not None and skipped >= 0 else EXPECTED_TOTAL,
                       "reason": reason[:1500]}
            uline = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(umarker, ensure_ascii=False)
            self.output.info(uline)
            print(uline, flush=True)
            raise ConanException(reason[:2000])
        status = "passed" if (failed == 0 and skipped == 0
                              and executed == discovered == EXPECTED_TOTAL
                              and proc.returncode == 0) else "failed"
        umarker = {"status": status, "framework": "custom",
                   "command": "test_upstream_checks (+ omniidl -V)",
                   "discovered": discovered, "executed": executed, "passed": passed,
                   "failed": failed, "skipped": skipped,
                   "reason": ("Formal upstream suite is 0 for omniORB-4.3.4 "
                              "(no tests/ dir, no check target in any of the 267 "
                              "GNUmakefile.in/mk files; audit retained in "
                              "MANIFEST.yml); 8 hardware-free functional checks against "
                              "upstream 4.3.4 artifacts (public C++ ORB API + omniidl -V) "
                              "executed as upstream evidence.")[:800]}
        if status != "passed":
            umarker["gaps"] = [{"count": failed if failed else skipped,
                                "category": "test_failure",
                                "detail": "upstream functional check(s) reported non-pass; see log tail",
                                "evidence": tail[-800:]}]
        uline = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(umarker, ensure_ascii=False)
        self.output.info(uline)
        print(uline, flush=True)
        if status != "passed":
            raise ConanException("upstream functional checks failed: %s" % tail[-2000:])

    def build(self):
        # Same CC/CXX env channel as the main recipe (conanbuild.sh is
        # sourced after Python sets os.environ, so both channels carry the
        # working driver; healthy runners: no-op).
        (_pin_c, _pin_cxx), (_eff_c, _eff_cxx) = self._effective_compilers()
        if _eff_c != _pin_c:
            os.environ["CC"] = _eff_c
        if _eff_cxx != _pin_cxx:
            os.environ["CXX"] = _eff_cxx
        # The IDL compiler runs during the build (add_custom_command), so
        # its directory must be on PATH even when CMake is invoked with an
        # absolute OMNIIDL_BIN (the script's own child processes resolve
        # through PATH).
        _omniidl = self._omniidl_bin()
        if _omniidl:
            _bindir = os.path.dirname(_omniidl)
            os.environ["PATH"] = _bindir + os.pathsep + os.environ.get("PATH", "")
        # Same for the IDL compiler's Python backends: the CMake custom
        # command inherits this process env, so prepend the package's
        # python dirs here as well (generate() already saved them to
        # build/run env scripts for the conanrun channel).
        for _pydir in self._package_python_dirs():
            _cur = os.environ.get("PYTHONPATH", "")
            if _pydir not in _cur.split(os.pathsep):
                os.environ["PYTHONPATH"] = (
                    _pydir + (os.pathsep + _cur if _cur else ""))
        if os.environ.get("PYTHONPATH"):
            self.output.info("test_package build PYTHONPATH=%s"
                             % os.environ.get("PYTHONPATH"))
        cmake = CMake(self)
        cmake.configure(variables=self._compiler_fallback_vars())
        cmake.build()

    def test(self):
        if can_run(self):
            passed = 0
            # Case 1: the packaged omniidl must turn IDL into non-empty
            # C++ stubs. Empty outputs fail the case (a dead compiler
            # that exits 0 must not count as passing).
            codegen_dir = os.path.join(self.build_folder, "codegen")
            os.makedirs(codegen_dir, exist_ok=True)
            shutil.copy(os.path.join(self.source_folder, "mini.idl"),
                        codegen_dir)
            _omniidl = self._omniidl_bin()
            _cmd = ("\"%s\" -bcxx mini.idl" % _omniidl) if _omniidl else "omniidl -bcxx mini.idl"
            self.run(_cmd, cwd=codegen_dir, env="conanrun")
            for generated in ("mini.hh", "miniSK.cc"):
                path = os.path.join(codegen_dir, generated)
                if not os.path.isfile(path) or os.path.getsize(path) == 0:
                    raise ConanException(
                        "omniidl produced no usable %s in %s"
                        % (generated, codegen_dir))
            self.output.info("omniorb test: omniidl codegen ok "
                             "(mini.hh/miniSK.cc non-empty)")
            passed += 1
            # Case 2: collocated Echo call against the packaged runtime.
            bin_path = os.path.join(self.cpp.build.bindirs[0], "test_echo")
            self.run(bin_path, env="conanrun")
            passed += 1
            marker = {
                "executed": True,
                "passed": passed == 2,
                "command": "omniidl -bcxx mini.idl + ./test_echo",
                "discovered": 2,
                "passedCount": passed,
            }
            self.output.info("HMBS_TEST_PACKAGE_RESULT="
                             + json.dumps(marker))
            if passed != 2:
                raise ConanException(
                    "omniorb consumer tests failed: %d/2 passed" % passed)
            # Upstream evidence: 4.3.4 ships no formal suite (audit in
            # MANIFEST.yml); run the 8 hardware-free functional checks
            # against the packaged artifacts and report with framework
            # custom. ctest registers upstream_checks for reference; the
            # deterministic count comes from the single run below.
            self._run_upstream_checks()
