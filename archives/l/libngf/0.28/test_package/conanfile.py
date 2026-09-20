#!/usr/bin/env python3
"""Conan test_package for libngf (L1 consumer test).

Builds test.c with the C compiler from the conanbuild env and links it
via pkg-config against the packaged libngf0 (PkgConfigDeps flow — the
canonical consumer path for autotools-era libraries; avoids the E216
class CMakeDeps empty-include issue seen on OHOS glib binaries).

The consumer performs 8 proplist lifecycle checks, each printing one
"CHECK-OK: <name>" line; the count feeds the HMBS_TEST_PACKAGE_RESULT
machine-evidence marker (exit-0-alone is not proof).

Upstream evidence: the 7-case proplist suite runs in the main recipe
build() and persists res/hmbs_upstream.json in the package, so this
re-emits HMBS_UPSTREAM_TEST_RESULT from that file on every run
(cache-hit rounds skip the main build, the gate still needs the marker).
"""
import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import load
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


# Expected consumer check names emitted as "CHECK-OK: <name>" lines by
# test.c. The test() method counts matches against this list from the
# captured output file (single deterministic source).


class LibngfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def _cc(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        configured = compilers.get("c")
        if configured and os.path.isfile(configured):
            return configured
        found = shutil.which("clang") or shutil.which("cc")
        return found or configured or "cc"

    def _dep_flags(self):
        """Aggregate -I/-D/-L/-l from all deps' cpp_info in Python (R33).

        The previous '$(pkg-config --cflags --libs libngf0)' shell capture
        fails on device with '/bin/sh: pkg-config: inaccessible or not
        found' (sandbox/shell-substitution class): the pkg-config binary
        is not executable from the test shell and $(...) needs temp
        files. Assembling the same closure in Python needs no extra
        binary and no shell substitution.
        """
        incs = []
        defines = []
        libdirs = []
        libs = []
        for dep in self.dependencies.values():
            try:
                cpp = dep.cpp_info
            except Exception:
                continue
            for d in getattr(cpp, "includedirs", []) or []:
                incs.append('-I"%s"' % str(d).replace(os.sep, "/"))
            for d in getattr(cpp, "defines", []) or []:
                defines.append("-D%s" % d)
            for d in getattr(cpp, "libdirs", []) or []:
                libdirs.append('-L"%s"' % str(d).replace(os.sep, "/"))
            for lib in getattr(cpp, "libs", []) or []:
                libs.append("-l%s" % lib)
            for lib in getattr(cpp, "system_libs", []) or []:
                libs.append("-l%s" % lib)
        return (" ".join(incs), " ".join(defines), " ".join(libdirs),
                " ".join(libs))

    def _test_link_args(self, libdirs, libs):
        """Prefer static archives and embed rpaths for the test binary.

        Same 127-class fix as the main recipe build() test binary: the
        consumer test links the full transitive closure (which includes
        -lcheck/-lsubunit from the libngf closure) but VirtualRunEnv does
        not put the check libdir on the loader path, so a dynamically
        linked test_ngf dies at startup with
        ``Error loading shared library libcheck.so`` (exit 127). Link
        static archives by full path wherever they exist and embed
        -rpath for any remaining shared libdirs, so the binary starts
        with no environment help. Order is preserved (in-place
        substitution), so static archives keep their trailing -l
        dependencies.
        """
        static_map = {}
        try:
            for dep in self.dependencies.values():
                try:
                    pkg = dep.package_folder
                except Exception:
                    continue
                if not pkg:
                    continue
                ldir = os.path.join(pkg, "lib")
                try:
                    names = os.listdir(ldir)
                except Exception:
                    continue
                for n in names:
                    if n.startswith("lib") and n.endswith(".a"):
                        static_map.setdefault(n[3:-2],
                                              os.path.join(ldir, n))
        except Exception:
            pass
        out = []
        try:
            for tok in libs.split():
                if tok.startswith("-l"):
                    p = static_map.get(tok[2:])
                    if p and os.path.isfile(p):
                        out.append('"%s"' % p.replace(os.sep, "/"))
                        continue
                out.append(tok)
        except Exception:
            out = libs.split()
        rpaths = []
        try:
            seen = set()
            for dep in self.dependencies.values():
                try:
                    cpp = dep.cpp_info
                except Exception:
                    continue
                for d in getattr(cpp, "libdirs", []) or []:
                    ds = str(d).replace(os.sep, "/")
                    if ds not in seen:
                        seen.add(ds)
                        rpaths.append('-Wl,-rpath,"%s"' % ds)
        except Exception:
            pass
        return " ".join(x for x in
                        (libdirs, " ".join(out), " ".join(rpaths), "-lm")
                        if x)

    def build(self):
        src = os.path.join(self.source_folder, "test.c").replace("\\", "/")
        incs, defines, libdirs, libs = self._dep_flags()
        cflags = ("-g -O2 " + " ".join(x for x in (incs, defines) if x))
        link_libs = self._test_link_args(libdirs, libs)
        self.run('"%s" %s "%s" -o test_ngf %s'
                 % (self._cc(), cflags, src, link_libs),
                 cwd=self.build_folder, env="conanbuild")

    def test(self):
        if can_run(self):
            exe = os.path.join(self.build_folder, "test_ngf")
            if not os.path.isfile(exe):
                raise ConanException("test binary missing: %s" % exe)
            # Deterministic single source: run the binary with stdout/stderr
            # captured into a file, then count the "CHECK-OK: <name>" lines
            # from that file. No returncode-based guessing: a zero exit with
            # missing lines (or a failing exit) yields passed < discovered.
            # Expected check names are listed explicitly so a truncated or
            # hand-edited binary cannot pass by printing duplicate lines.
            expected_names = [
                "string-roundtrip",
                "integer-roundtrip",
                "unsigned-roundtrip",
                "boolean-and-types",
                "parsers",
                "foreach",
                "copy",
                "keys",
            ]
            discovered = len(expected_names)
            out_file = os.path.join(self.build_folder,
                                    "test_ngf_output.txt")
            run_env = Environment()
            run_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
            with run_env.vars(self).apply():
                try:
                    self.run('"%s" > "%s" 2>&1' % (exe, out_file),
                             cwd=self.build_folder,
                             env=["conanbuild", "conanrun"])
                    run_ok = True
                except Exception as exc:
                    self.output.error("test_ngf failed: %s" % exc)
                    run_ok = False
            try:
                content = load(self, out_file)
            except Exception as exc:
                raise ConanException(
                    "test output file missing: %s (%s)" % (out_file, exc))
            seen = set()
            for line in content.splitlines():
                if line.startswith("CHECK-OK: "):
                    seen.add(line[len("CHECK-OK: "):].strip())
            passed = len([n for n in expected_names if n in seen])
            all_line = "ALL %d CHECKS PASSED" % discovered in content
            ok = run_ok and all_line and passed == discovered
            if not ok:
                self.output.error(
                    "test_ngf evidence: run_ok=%s all_line=%s "
                    "matched=%d/%d names=%s"
                    % (run_ok, all_line, passed, discovered, sorted(seen)))
            tp_result = {
                "executed": True,
                "passed": ok,
                "command": "./test_ngf",
                "discovered": discovered,
                "passedCount": passed,
            }
            tp_marker = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_result)
            print(tp_marker, flush=True)
            self.output.info(tp_marker)
            try:
                self.output.info("test_ngf captured output:\n%s" % content)
            except Exception:
                pass
            self._reemit_upstream()
            if not ok:
                raise ConanException(
                    "test_ngf failed: %d/%d checks matched"
                    % (passed, discovered))

    def _reemit_upstream(self):
        try:
            emitted = False
            try:
                dep = self.dependencies["libngf"]
                cand = os.path.join(dep.package_folder, "res",
                                    "hmbs_upstream.json")
                if os.path.isfile(cand):
                    up = json.loads(load(self, cand))
                    up_marker = ("HMBS_UPSTREAM_TEST_RESULT="
                                 + json.dumps(up, ensure_ascii=False))
                    print(up_marker, flush=True)
                    self.output.info(up_marker)
                    emitted = True
            except Exception as exc:
                self.output.warning("upstream re-emit lookup failed: %s"
                                    % exc)
            if not emitted:
                self.output.warning(
                    "hmbs_upstream.json absent from package res/; "
                    "upstream marker left to the main build "
                    "(cache-miss rounds)")
        except Exception as exc:
            self.output.warning("upstream re-emit failed: %s" % exc)
