#!/usr/bin/env python3
"""Conan test_package -- libcds 2.3.3 consumer test (direct-cc, no CMake).

Vanilla CMake on the device has no Platform/HarmonyOS (nor a working
OHOS) file for the profile toolchain, so every CMakeToolchain-based
configure dies at project() with a CMAKE_CXX_COMPILER sanity-check
failure on /data/service/hnp/bin/clang++; OHOS /tmp is also a
read-only erofs mount, which breaks CMake try-compile temp files. This
consumer therefore compiles test.cpp with the Conan-profile compiler
directly (cthreadpool precedent: conf-first tool resolution, writable
TMPDIR wrapping, include/lib/link args assembled from the package
cpp_info), then runs it.

test.cpp really calls the packaged library (cds::Initialize/Terminate,
HP GC, TreiberStack LIFO, MSQueue FIFO). The binary prints one
"CHECK <name>: PASS" line per check plus a "RESULT: N passed, M failed"
trailer; test() parses the trailer into HMBS_TEST_PACKAGE_RESULT and
re-emits the persisted HMBS_UPSTREAM_TEST_RESULT
(res/hmbs_upstream.json written by the main recipe build(), so evidence
survives Conan cache-hit rounds where build() is skipped).
"""

import json
import os
import re
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout

CONSUMER_CHECK_COUNT = 3


class LibcdsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _resolve_tool(self, name, fallback):
        # Same conf-first/PATH-fallback policy as the main recipe.
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            compilers = {}
        value = compilers.get(name) or (
            compilers.get("cxx") if name == "cpp" else None
        ) or fallback
        if "/" in value or "\\" in value:
            if not os.path.isfile(value):
                self.output.warning(
                    "conf tools.build:compiler_executables:%s=%s is not a "
                    "file, falling back to '%s' via PATH"
                    % (name, value, fallback)
                )
                return fallback
            if not os.access(value, os.X_OK):
                self.output.warning(
                    "conf tools.build:compiler_executables:%s=%s is not "
                    "executable, falling back to '%s' via PATH"
                    % (name, value, fallback)
                )
                return fallback
        return value

    @staticmethod
    def _dir_writable(path):
        # Same real-probe policy as the main recipe: isdir alone also
        # matches the device's read-only /tmp itself (exists, erofs).
        try:
            if not path or not os.path.isdir(path):
                return False
            if not os.access(path, os.W_OK | os.X_OK):
                return False
            fd, tmp = tempfile.mkstemp(prefix="hmbs-probe-", dir=path)
            try:
                os.close(fd)
            finally:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
            return True
        except OSError:
            return False

    def _writable_tmpdir(self):
        # E002 readonly_tmp: device /tmp is read-only; prefer the
        # HMBS-injected HMBS_TMPDIR/TMPDIR/TMP/TEMP (probe-verified),
        # else a build-folder tmpdir.
        candidates = [os.environ.get("HMBS_TMPDIR")]
        for key in ("TMPDIR", "TMP", "TEMP"):
            candidates.append(os.environ.get(key))
        for cand in candidates:
            if cand and self._dir_writable(cand):
                return cand
        fallback = os.path.join(self.build_folder, "hmbs-tmp")
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            pass
        return fallback

    def _with_tmpdir(self, command):
        tmp = self._writable_tmpdir()
        return 'TMPDIR="%s" TMP="%s" TEMP="%s" %s' % (tmp, tmp, tmp, command)

    def _compile_args(self):
        dep = self.dependencies["libcds"].cpp_info
        includes = " ".join('"-I%s"' % str(p) for p in dep.includedirs)
        libdirs = " ".join('"-L%s"' % str(p) for p in dep.libdirs)
        libs = " ".join("-l%s" % str(lib) for lib in dep.libs)
        sysflags = []
        for system_lib in dep.system_libs:
            if system_lib == "pthread":
                sysflags.append("-pthread")
            else:
                sysflags.append("-l%s" % system_lib)
        return includes, libdirs, libs, " ".join(sysflags)

    def build(self):
        tmpdir = self._writable_tmpdir()
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        cxx = self._resolve_tool("cpp", "clang++")
        includes, libdirs, libs, sysflags = self._compile_args()
        src = os.path.join(self.source_folder, "test.cpp")
        if not os.path.isfile(src):
            raise ConanException("consumer test source missing: test.cpp")
        exe = os.path.join(self.build_folder, "test_libcds")
        self.run(
            self._with_tmpdir(
                '"%s" -O2 -std=c++17 %s "%s" -o "%s" %s %s %s'
                % (cxx, includes, src, exe, libdirs, libs, sysflags)
            ),
            cwd=self.build_folder,
        )

    def _find_binary(self, name):
        candidate = os.path.join(self.build_folder, name)
        if os.path.isfile(candidate):
            return candidate
        for root, _dirs, files in os.walk(self.build_folder):
            if name in files:
                return os.path.join(root, name)
        return ""

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: consumer test built, not run")
            return
        binary = self._find_binary("test_libcds")
        if not binary:
            raise ConanException("consumer test binary not built")
        tmpdir = self._writable_tmpdir()
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        logfile = os.path.join(self.build_folder, "test_package.log")
        env = os.environ.copy()
        env["TMPDIR"] = tmpdir
        env["TMP"] = tmpdir
        env["TEMP"] = tmpdir
        try:
            proc = subprocess.run(
                [binary], cwd=self.build_folder,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=600, env=env,
            )
            output = proc.stdout or ""
            with open(logfile, "w", encoding="utf-8",
                      errors="replace") as handle:
                handle.write(output)
            rc = proc.returncode
        except (OSError, subprocess.SubprocessError) as exc:
            raise ConanException("test_libcds launch failed: %s" % exc)
        self.output.info(
            "test_libcds log:\n" + "\n".join(output.splitlines()[-20:])
        )
        if rc != 0:
            raise ConanException(
                "test_libcds exited with rc=%s and output:\n%s"
                % (rc, output[-2000:])
            )
        match = re.search(r"RESULT: (\d+) passed, (\d+) failed", output)
        if not match:
            raise ConanException(
                "test_libcds produced no RESULT line -- harness broken"
            )
        passed = int(match.group(1))
        failed = int(match.group(2))
        discovered = passed + failed
        ok = failed == 0 and discovered == CONSUMER_CHECK_COUNT
        marker = {
            "executed": True,
            "passed": ok,
            "command": "./test_libcds (TreiberStack LIFO + MSQueue FIFO + HP GC)",
            "discovered": discovered,
            "passedCount": passed,
        }
        message = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(
            marker, ensure_ascii=False
        )
        print(message, flush=True)
        self.output.info(message)
        if not ok:
            raise ConanException(
                "consumer test failed: %d/%d checks failed"
                % (failed, discovered)
            )

        # Re-emit the real in-build upstream result on every run so the
        # evidence gate also sees it when build() was skipped (cache hit).
        try:
            upstream = None
            dep = self.dependencies["libcds"]
            package_folder = getattr(dep, "package_folder", "")
            if package_folder:
                candidate = os.path.join(
                    package_folder, "res", "hmbs_upstream.json"
                )
                if os.path.isfile(candidate):
                    with open(candidate, "r", encoding="utf-8") as handle:
                        upstream = json.load(handle)
            if isinstance(upstream, dict) and upstream.get("discovered"):
                umsg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
                    upstream, ensure_ascii=False
                )
                print(umsg, flush=True)
                self.output.info(umsg)
            else:
                self.output.warning(
                    "persisted hmbs_upstream.json missing; upstream "
                    "evidence only available on fresh build"
                )
        except Exception as exc:
            self.output.warning("upstream re-emit failed: %r" % (exc,))
        self.output.info("libcds consumer test_package passed")
