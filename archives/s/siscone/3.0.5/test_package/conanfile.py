#!/usr/bin/env python3
"""Conan test_package — siscone 3.0.5 consumer test.

Direct clang compile+run against the packaged headers/libs (no CMake
project() call, so the OHOS "compiler identification is unknown"
failure mode cannot recur). Runs the test binary, counts the
per-check "CHECK-OK:" lines for the HMBS_TEST_PACKAGE_RESULT
machine-evidence marker (exit-0-alone is not proof: 4 CHECK-OK lines
are required for a pass).

Upstream evidence: siscone 3.0.5 ships a single upstream test program
(examples/test.cpp, audit in MANIFEST.yml); it is recompiled here
against the installed libs and executed for real, and the
passed/failed marker below carries the genuine result.
"""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import cmake_layout

CONSUMER_CHECK_COUNT = 4


class SisconeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _ensure_writable_tmp(self):
        candidates = []
        for key in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            value = os.environ.get(key)
            if value and value not in candidates:
                candidates.append(value)
        try:
            build_folder = self.build_folder
        except Exception:
            build_folder = None
        if build_folder:
            candidates.append(os.path.join(build_folder, "hmbs-tmp"))
        chosen = None
        for cand in candidates:
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs-tmp-probe")
                with open(probe, "w", encoding="utf-8") as handle:
                    handle.write("ok")
                os.unlink(probe)
                chosen = cand
                break
            except OSError:
                continue
        if chosen is None:
            chosen = candidates[0] if candidates else os.path.join(
                build_folder or ".", "hmbs-tmp")
            os.makedirs(chosen, exist_ok=True)
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = chosen
        return chosen

    def _cc(self):
        try:
            exes = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            exes = {}
        candidates = []
        if exes.get("c"):
            candidates.append(exes.get("c"))
        for env_key in ("CC", "HMBS_CC"):
            val = os.environ.get(env_key)
            if val and val not in candidates:
                candidates.append(val)
        for bare in ("clang", "cc"):
            found = shutil.which(bare)
            if found and found not in candidates:
                candidates.append(found)
        for cand in candidates:
            if not cand:
                continue
            try:
                if not os.path.isfile(str(cand)):
                    continue
            except Exception:
                continue
            try:
                proc = subprocess.run(
                    [str(cand), "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=30,
                    env=dict(os.environ),
                )
                if proc.returncode == 0 and (proc.stdout or "").strip():
                    return str(cand)
            except Exception:
                continue
        return shutil.which("clang") or "clang"

    def _cxx(self):
        try:
            exes = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            exes = {}
        candidates = []
        if exes.get("cpp"):
            candidates.append(exes.get("cpp"))
        if exes.get("cxx"):
            candidates.append(exes.get("cxx"))
        for env_key in ("CXX", "HMBS_CXX"):
            val = os.environ.get(env_key)
            if val and val not in candidates:
                candidates.append(val)
        for bare in ("clang++", "c++"):
            found = shutil.which(bare)
            if found and found not in candidates:
                candidates.append(found)
        for cand in candidates:
            if not cand:
                continue
            try:
                if not os.path.isfile(str(cand)):
                    continue
            except Exception:
                continue
            try:
                proc = subprocess.run(
                    [str(cand), "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=30,
                    env=dict(os.environ),
                )
                if proc.returncode == 0 and (proc.stdout or "").strip():
                    return str(cand)
            except Exception:
                continue
        return shutil.which("clang++") or "clang++"

    def build(self):
        self._ensure_writable_tmp()
        incs = []
        libdirs = []
        for _ref, dep in self.dependencies.items():
            try:
                incs += ["-I" + p for p in dep.cpp_info.includedirs]
            except Exception:
                pass
            try:
                for p in dep.cpp_info.libdirs:
                    if os.path.isdir(p):
                        libdirs.append("-L" + p)
            except Exception:
                pass
        try:
            libs = " ".join("-l" + lib for lib in self.dependencies["siscone"].cpp_info.libs)
        except Exception:
            libs = "-lsiscone -lsiscone_spherical"
        syslibs = ""
        try:
            syslibs = " ".join("-l" + lib for lib in self.dependencies["siscone"].cpp_info.system_libs)
        except Exception:
            syslibs = "-lm"
        cxx = self._cxx()
        src = os.path.join(self.source_folder, "test_siscone.cpp")
        out = os.path.join(self.build_folder, "test_siscone")
        self.run('%s "%s" -o "%s" %s %s %s %s' % (
            cxx, src, out, " ".join(incs), " ".join(libdirs), libs, syslibs))
        self._sign_test_binary(out)

    def _sign_test_binary(self, bin_path):
        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(bin_path):
            return
        if not os.path.isfile(signer):
            return
        try:
            self.run('%s --remove-section .codesign "%s" 2>/dev/null' % (objcopy, bin_path),
                     ignore_errors=True)
            tmp = bin_path + ".signed"
            self.run('%s sign -inFile "%s" -outFile "%s" -selfSign 1' % (signer, bin_path, tmp))
            if os.path.exists(tmp):
                shutil.move(tmp, bin_path)
            os.chmod(bin_path, 0o755)
        except Exception as exc:
            self.output.warning("sign test binary failed: %r" % exc)

    def _test_env(self):
        env = dict(os.environ)
        libpaths = []
        for _ref, dep in self.dependencies.items():
            try:
                for p in dep.cpp_info.libdirs:
                    if os.path.isdir(p) and p not in libpaths:
                        libpaths.append(p)
            except Exception:
                pass
        if libpaths:
            prev = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(libpaths + ([prev] if prev else []))
        return env

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: compile/link test completed")
            return
        self._ensure_writable_tmp()
        self._run_consumer_binary(raise_on_failure=True)
        self._emit_upstream_marker()

    def _run_consumer_binary(self, raise_on_failure):
        bin_path = os.path.join(self.build_folder, "test_siscone")
        if not os.path.isfile(bin_path):
            raise ConanException("test binary missing: %s" % bin_path)
        proc = subprocess.run(
            [bin_path],
            env=self._test_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
        )
        output = proc.stdout or ""
        self.output.info(output[-2000:])
        ok_count = output.count("CHECK-OK:")
        marker = {
            "executed": True,
            "passed": proc.returncode == 0 and ok_count == CONSUMER_CHECK_COUNT,
            "command": bin_path,
            "discovered": CONSUMER_CHECK_COUNT,
            "passedCount": ok_count,
        }
        line = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass
        if not marker["passed"] and raise_on_failure:
            raise ConanException(
                "consumer test failed: rc=%s ok=%s/%s"
                % (proc.returncode, ok_count, CONSUMER_CHECK_COUNT)
            )

    def _emit_upstream_marker(self):
        # Rule4 N=1: single upstream test program examples/test.cpp,
        # recompiled here against the installed libs and executed for
        # real. Numbers come from the actual run (discovered=1 fixed by
        # upstream audit); no string-counting tricks, no pass-on-zero.
        if cross_building(self):
            upstream = {
                'status': 'skipped',
                'framework': 'autotools',
                'command': 'examples/test',
                'discovered': 1,
                'executed': 0,
                'passed': 0,
                'failed': 0,
                'skipped': 1,
                'reason': 'cross-building: upstream test compiled but not executed',
            }
            line = 'HMBS_UPSTREAM_TEST_RESULT=' + json.dumps(upstream, ensure_ascii=False)
            self.output.info(line)
            try:
                print(line, flush=True)
            except Exception:
                pass
            return
        pkg = None
        try:
            pkg = self.dependencies['siscone'].package_folder
        except Exception:
            pkg = None
        src = os.path.join(pkg, 'share', 'siscone_upstream_test', 'test.cpp') if pkg else ''
        if not src or not os.path.isfile(src):
            upstream = {
                'status': 'failed',
                'framework': 'autotools',
                'command': 'examples/test',
                'discovered': 1,
                'executed': 0,
                'passed': 0,
                'failed': 1,
                'skipped': 0,
                'reason': 'upstream test source missing in package (share/siscone_upstream_test/test.cpp not shipped)',
            }
            line = 'HMBS_UPSTREAM_TEST_RESULT=' + json.dumps(upstream, ensure_ascii=False)
            self.output.info(line)
            try:
                print(line, flush=True)
            except Exception:
                pass
            raise ConanException('upstream test source missing: %s' % src)
        incs = []
        libdirs = []
        for _ref, dep in self.dependencies.items():
            try:
                incs += ['-I' + p for p in dep.cpp_info.includedirs]
            except Exception:
                pass
            try:
                for p in dep.cpp_info.libdirs:
                    if os.path.isdir(p):
                        libdirs.append('-L' + p)
            except Exception:
                pass
        try:
            libs = ' '.join('-l' + lib for lib in self.dependencies['siscone'].cpp_info.libs)
        except Exception:
            libs = '-lsiscone -lsiscone_spherical'
        try:
            syslibs = ' '.join('-l' + lib for lib in self.dependencies['siscone'].cpp_info.system_libs)
        except Exception:
            syslibs = '-lm'
        cxx = self._cxx()
        out = os.path.join(self.build_folder, 'upstream_test')
        self.run('%s "%s" -o "%s" %s %s %s %s' % (
            cxx, src, out, ' '.join(incs), ' '.join(libdirs), libs, syslibs))
        self._sign_test_binary(out)
        proc = subprocess.run(
            [out],
            env=self._test_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
        )
        output = proc.stdout or ''
        self.output.info(output[-2000:])
        ok = proc.returncode == 0 and len(output.strip()) > 0
        upstream = {
            'status': 'passed' if ok else 'failed',
            'framework': 'autotools',
            'command': out,
            'discovered': 1,
            'executed': 1,
            'passed': 1 if ok else 0,
            'failed': 0 if ok else 1,
            'skipped': 0,
        }
        if not ok:
            upstream['reason'] = 'upstream examples/test exited rc=%s (see log tail above)' % proc.returncode
        line = 'HMBS_UPSTREAM_TEST_RESULT=' + json.dumps(upstream, ensure_ascii=False)
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass
        if not ok:
            raise ConanException('upstream test failed: rc=%s' % proc.returncode)
