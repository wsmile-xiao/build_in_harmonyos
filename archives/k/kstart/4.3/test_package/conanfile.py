#!/usr/bin/env python3
"""Test package — kstart 4.3 (application).

Consumes the package ONLY from the final package folder (never the build
tree): the consumer model is running the installed bin/k5start and
bin/krenew.  The smoke checks are the two things this recipe actually
ships — the two commands — plus the man pages, and the OHOS-specific
binary attributes (AArch64 ELF, musl interpreter, RUNPATH to the Conan
krb5 libdir, .codesign section on OHOS).
"""
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException


class KstartTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # locate tools in the worker's PATH (readelf lives outside default)
        tool_dirs = (
            "/data/service/hnp/bin",
        )
        def find_tool(name):
            found = shutil.which(name)
            if found:
                return found
            for d in tool_dirs:
                p = os.path.join(d, name)
                if os.path.isfile(p):
                    return p
            return None

        # consume the installed package only (never the build tree):
        # resolve package_folder through the explicit requirement
        kstart = self.dependencies[self.tested_reference_str]
        bin_dir = os.path.join(kstart.package_folder, "bin")
        k5start = os.path.join(bin_dir, "k5start")
        krenew = os.path.join(bin_dir, "krenew")
        for exe in (k5start, krenew):
            if not os.path.isfile(exe):
                raise ConanException("missing installed binary: " + exe)
            if not os.access(exe, os.X_OK):
                raise ConanException("not executable: " + exe)

        # runenv from the package (LD_LIBRARY_PATH to Conan krb5 lib);
        # fall back to krb5 dependency's libdir resolved the same way
        runenv = dict(os.environ)
        try:
            runenv.update(self.runenv_info.vars(self))
        except Exception:
            pass
        krb5 = self.dependencies.get("krb5")
        krb5_lib_dir = None
        if krb5 is not None:
            libdirs = krb5.cpp_info.libdirs or ["lib"]
            lib_dir = libdirs[0]
            if not os.path.isabs(lib_dir):
                lib_dir = os.path.join(krb5.package_folder, lib_dir)
            krb5_lib_dir = os.path.normpath(lib_dir)
            runenv["LD_LIBRARY_PATH"] = (
                lib_dir + os.pathsep + runenv.get("LD_LIBRARY_PATH", ""))
        checks = []

        smoke_path = os.path.join(self.source_folder, "test_smoke.py")
        if not os.path.isfile(smoke_path):
            raise ConanException("missing test source: " + smoke_path)

        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "kstart_test_smoke", smoke_path)
        smoke = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(smoke)

        checks.extend(
            smoke.run_smoke_checks(k5start, krenew, runenv)
        )

        # ── OHOS-specific binary checks (TestQualitySpec) ──────────
        ohos = str(self.settings.os) == "OHOS"
        readelf = find_tool("readelf")
        if readelf is None:
            raise ConanException("readelf not found in worker PATH")
        for exe, name in ((k5start, "k5start"), (krenew, "krenew")):
            ok, detail = self._check_elf(
                readelf, exe, ohos, krb5_lib_dir)
            checks.append((f"{name} OHOS ELF checks", ok))
            if not ok:
                self.output.error(detail)

        passed = sum(1 for _n, ok in checks if ok)
        for name, ok in checks:
            self.output.info(f"SMOKE {'PASS' if ok else 'FAIL'}: {name}")
        self.output.info(f"SMOKE_SUMMARY total={len(checks)} passed={passed} failed={len(checks) - passed}")
        if passed != len(checks):
            raise ConanException(
                f"smoke checks failed: {[n for n, ok in checks if not ok]}")

    # ── helpers ───────────────────────────────────────────────────

    @staticmethod
    def _run(cmd, env, timeout):
        proc = subprocess.run(
            cmd, env=env, timeout=timeout,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, text=True)
        return proc.stdout or ""

    @staticmethod
    def _run_rc(cmd, env, timeout):
        proc = subprocess.run(
            cmd, env=env, timeout=timeout,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL)
        return proc.returncode

    def _check_elf(self, readelf, exe, ohos, krb5_lib_dir):
        try:
            dyn = subprocess.run(
                [readelf, "-d", exe], capture_output=True, text=True,
                timeout=30).stdout
            hdr = subprocess.run(
                [readelf, "-h", exe], capture_output=True, text=True,
                timeout=30).stdout
            prog = subprocess.run(
                [readelf, "-l", exe], capture_output=True, text=True,
                timeout=30).stdout
            if ohos:
                sections = subprocess.run(
                    [readelf, "-S", exe], capture_output=True, text=True,
                    timeout=30).stdout
        except subprocess.TimeoutExpired:
            return False, f"readelf timeout on {exe}"
        problems = []
        # arch: AArch64 ELF
        if not re.search(r"Class:\s+ELF64", hdr) or \
           "AArch64" not in hdr:
            problems.append("not an AArch64 ELF64 binary")
        # interpreter: musl (OHOS) — PT_INTERP /lib/ld-musl-aarch64.so.1
        if ohos and "ld-musl-aarch64" not in prog:
            problems.append("missing musl ld-musl-aarch64 PT_INTERP")
        # RUNPATH pointing at the Conan krb5 libdir (not /usr/lib).
        # readelf prints: "(RUNPATH)   Library runpath: [/path]" — allow
        # arbitrary text between the tag and the bracketed value.
        m = re.search(r"(?:RPATH|RUNPATH)\)[^[]*\[([^\]]*)\]", dyn)
        if not m:
            problems.append("no RPATH/RUNPATH entry")
        else:
            runpath = m.group(1)
            runpath_entries = [
                os.path.normpath(entry)
                for entry in runpath.split(os.pathsep)
                if entry
            ]
            if "/usr/lib" in runpath or "/usr/local/lib" in runpath:
                problems.append(f"host libdir leaked into RUNPATH: {runpath}")
            if krb5_lib_dir is None:
                problems.append("Conan krb5 libdir unavailable")
            elif os.path.normpath(krb5_lib_dir) not in runpath_entries:
                problems.append(
                    f"RUNPATH does not contain Conan krb5 libdir "
                    f"{krb5_lib_dir}: {runpath}")
        # NEEDED must be present and not host libs
        needed = re.findall(r"NEEDED\)[^[]*\[([^\]]*)\]", dyn)
        if not needed:
            problems.append("no NEEDED entries")
        if ohos:
            if ".codesign" in sections or ".codesign" in dyn:
                self.output.info(f"{os.path.basename(exe)}: .codesign section present")
            else:
                problems.append("missing .codesign section (OHOS signing)")
        return (not problems), "; ".join(problems)
