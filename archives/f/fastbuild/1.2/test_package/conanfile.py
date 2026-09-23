#!/usr/bin/env python3
"""Conan test_package for fastbuild 1.2.

Consumer tests (each a real execution of the packaged fbuild binary):
  T1 version   — `fbuild -version` must print upstream "v1.02".
  T2 hello build — drive fbuild on a minimal BFF (Compiler/ObjectList)
    using the OHOS clang from Conan conf; the produced object file must
    exist and be non-empty (empty-output guard: a silent no-op build
    must not count as pass).

Also re-emits the upstream suite result persisted by the main recipe in
res/upstream_test_result.json, then emits HMBS_TEST_PACKAGE_RESULT.
Both markers are printed on every run so evidence survives cache hits.
"""
import json
import os
import shlex
import subprocess

from conan import ConanFile
from conan.tools.build import can_run


def _q(value):
    return shlex.quote(str(value))


class FastbuildTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        dep = self.dependencies["fastbuild"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        fbuild = os.path.join(bin_dir, "fbuild")
        if not os.path.isfile(fbuild):
            raise RuntimeError("packaged fbuild binary missing: %s" % fbuild)
        self.output.info("fbuild binary: %s" % fbuild)

        discovered = 2
        passed_count = 0

        # T1: version (L0d gate: real self.run execution).
        self.run("%s -version" % _q(fbuild), env="conanrun")
        proc = subprocess.run([fbuild, "-version"], capture_output=True,
                              text=True, timeout=120)
        version_out = (proc.stdout or "") + (proc.stderr or "")
        self.output.info("fbuild -version: %s" % version_out.strip())
        if proc.returncode == 0 and "v1.02" in version_out:
            passed_count += 1
        else:
            self.output.error("T1 version check failed (rc=%d): %s"
                              % (proc.returncode, version_out.strip()))

        # T2: functional build driven by fbuild (Compiler + ObjectList).
        # R33: dict-form conf (dotted ":c" subkey does not exist on OHOS conan).
        try:
            _compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict)
        except Exception:
            _compilers = {}
        cc = _compilers.get("c", "clang") if isinstance(_compilers, dict) else "clang"
        work = os.path.join(self.build_folder, "fbtest")
        os.makedirs(work, exist_ok=True)
        hello_c = os.path.join(work, "hello.c")
        with open(os.path.join(str(self.source_folder), "hello.c"),
                  "r", encoding="utf-8") as src:
            hello_src = src.read()
        with open(hello_c, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(hello_src)
        if os.path.getsize(hello_c) < 50:
            raise RuntimeError("hello.c test source suspiciously small")

        bff = os.path.join(work, "hello.bff")
        with open(bff, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("// Minimal consumer build: compile hello.c with the OHOS clang.\n")
            fh.write("Compiler( 'OHOS-Clang' )\n{\n")
            fh.write("    .Executable = '%s'\n" % cc.replace("'", ""))
            fh.write("    .CompilerFamily = 'clang'\n")
            fh.write("}\n")
            fh.write("ObjectList( 'HelloObj' )\n{\n")
            fh.write("    .Compiler = 'OHOS-Clang'\n")
            fh.write('    .CompilerOptions = \'-c "%1" -o "%2"\'\n')
            fh.write("    .CompilerInputFiles = '%s'\n" % hello_c.replace("\\", "/").replace("'", ""))
            fh.write("    .CompilerOutputPath = '%s'\n" % (work.replace("\\", "/") + "/out/"))
            fh.write("}\n")
            fh.write("Alias( 'all' )\n{\n")
            fh.write("    .Targets = 'HelloObj'\n")
            fh.write("}\n")
        self.run("%s -config %s HelloObj" % (_q(fbuild), _q(bff)), env="conanrun", cwd=work)
        hello_o = os.path.join(work, "out", "hello.o")
        if not os.path.isfile(hello_o):
            # FASTBuild may name the object after the full input path; search.
            found = ""
            for root, _, files in os.walk(os.path.join(work, "out")):
                for entry in files:
                    if entry.endswith(".o"):
                        found = os.path.join(root, entry)
                        break
            hello_o = found
        if hello_o and os.path.isfile(hello_o) and os.path.getsize(hello_o) > 100:
            self.output.info("T2 hello build produced %s (%d bytes)"
                             % (hello_o, os.path.getsize(hello_o)))
            passed_count += 1
        else:
            self.output.error("T2 hello build produced no non-empty object")

        # Re-emit upstream suite result persisted by the main recipe.
        res_json = os.path.join(dep.package_folder, "res", "upstream_test_result.json")
        if not os.path.isfile(res_json):
            raise RuntimeError("upstream_test_result.json missing from package res/")
        with open(res_json, "r", encoding="utf-8") as fh:
            upstream = json.load(fh)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream))
        if (upstream.get("status") != "passed"
                or int(upstream.get("discovered", 0)) <= 0
                or int(upstream.get("executed", 0)) != int(upstream.get("discovered", 0))
                or int(upstream.get("passed", 0)) != int(upstream.get("discovered", 0))):
            raise RuntimeError("upstream result invalid: %s" % upstream)

        marker = {
            "executed": True,
            "passed": passed_count == discovered,
            "command": "fbuild -version + fbuild -config hello.bff HelloObj (hello.c object build)",
            "discovered": discovered,
            "passedCount": passed_count,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
        if passed_count != discovered:
            raise RuntimeError("test_package failed: %d/%d" % (passed_count, discovered))
