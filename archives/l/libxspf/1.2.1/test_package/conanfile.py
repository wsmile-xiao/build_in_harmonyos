#!/usr/bin/env python3
"""Conan test_package for libxspf 1.2.1 — exercises the real public API.

Compiles test_xspf.cpp against the installed package (14 CHECK assertions:
parse/validate/round-trip of XSPF playlists) with explicit -I/-L/-l flags
taken from the dependency graph, self-signs the binary on HarmonyOS, runs
it and emits the HMBS_TEST_PACKAGE_RESULT marker. Any failing CHECK makes
the binary exit non-zero, which flips the marker to passed=false.
"""
import json
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout

# CHECK() assertions in test_xspf.cpp; update together with that file.
TEST_ASSERTIONS = 14


class LibxspfTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "test_xspf.cpp"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    @staticmethod
    def _is_writable_dir(path):
        """Real write probe: isdir alone cannot prove HMDFS writability."""
        try:
            if not os.path.isdir(path):
                return False
            probe = os.path.join(path, ".hmbs-write-probe")
            with open(probe, "w", encoding="utf-8") as handle:
                handle.write("ok")
            os.remove(probe)
            return True
        except OSError:
            return False

    def _writable_tmpdir(self):
        """Prefer the HMBS-injected task TMPDIR, verified by write probe.

        Falls back to build_folder/.tmp (conan guarantees it is writable).
        Keeps clang/test temp files off the read-only /tmp ([readonly_tmp]).
        Only replaces the temp root; no test is skipped or deleted.
        """
        for key in ("TMPDIR", "TMP", "TEMP"):
            candidate = os.environ.get(key)
            if candidate and self._is_writable_dir(candidate):
                return candidate
        for key in ("TMPDIR", "TMP", "TEMP"):
            candidate = os.environ.get(key)
            if candidate:
                try:
                    os.makedirs(candidate, exist_ok=True)
                except OSError:
                    continue
                if self._is_writable_dir(candidate):
                    return candidate
        fallback = os.path.join(self.build_folder, ".tmp")
        os.makedirs(fallback, exist_ok=True)
        return fallback

    def _tmp_prefix(self):
        tmpdir = self._writable_tmpdir()
        return 'TMPDIR="{}" TMP="{}" TEMP="{}" '.format(
            tmpdir, tmpdir, tmpdir)

    def _compiler(self):
        # tools.build:compiler_executables is a dict {"c": ..., "cpp": ...},
        # not a ":cpp"-suffixed key (that key raises "[conf] ... does not
        # exist" on Conan 2.30). Mirror the main recipe's
        # _discover_vendor_compiler("cxx"): prefer the profile path only
        # when it exists as a file, else $CXX, else PATH lookup.
        try:
            executables = self.conf.get(
                "tools.build:compiler_executables", default=None)
        except Exception:
            executables = None
        if isinstance(executables, dict):
            candidate = executables.get("cpp") or ""
            if candidate and os.path.isfile(candidate.split()[0]):
                return candidate
        for env_key in ("CXX", "CC_FOR_BUILD"):
            candidate = (os.environ.get(env_key) or "").strip()
            if candidate and os.path.isfile(candidate.split()[0]):
                return candidate
        for name in ("clang++", "aarch64-unknown-linux-ohos-clang++",
                     "aarch64-linux-ohos-clang++", "c++", "g++"):
            resolved = shutil.which(name)
            if resolved:
                return resolved
        return "c++"

    def build(self):
        include_dirs = []
        lib_dirs = []
        libs = []

        def push_unique(items, value):
            if value and value not in items:
                items.append(value)

        # The tested package first so -l order resolves dependents first.
        # NOTE: self.tested_reference_str is a plain string
        # ("libxspf/1.2.1") on Conan 2.x, not an object with .ref.
        tested_ref = self.tested_reference_str
        tested_name = tested_ref.split("/")[0]
        try:
            tested_dep = self.dependencies[tested_ref]
        except KeyError:
            tested_dep = self.dependencies[tested_name]
        ordered = [tested_dep]
        for dep in self.dependencies.host.values():
            if dep.ref.name != tested_name:
                ordered.append(dep)
        for dep in ordered:
            for inc in dep.cpp_info.includedirs:
                path = inc if os.path.isabs(inc) else os.path.join(
                    dep.package_folder, inc)
                push_unique(include_dirs, path)
            for libdir in dep.cpp_info.libdirs:
                path = libdir if os.path.isabs(libdir) else os.path.join(
                    dep.package_folder, libdir)
                push_unique(lib_dirs, path)
            for lib in dep.cpp_info.libs:
                push_unique(libs, lib)
            for syslib in dep.cpp_info.system_libs:
                push_unique(libs, syslib)

        src = os.path.join(self.source_folder, "test_xspf.cpp")
        out = os.path.join(self.build_folder, "test_xspf")
        cmd = (
            "{cxx} -std=c++11 -O1 {incs} \"{src}\" -o \"{out}\""
            " {libdirs} {libs}"
        ).format(
            cxx=shlex.quote(self._compiler()),
            incs=" ".join("-I{}".format(shlex.quote(d))
                          for d in include_dirs),
            src=src,
            out=out,
            libdirs=" ".join("-L{}".format(shlex.quote(d))
                             for d in lib_dirs),
            libs=" ".join("-l{}".format(shlex.quote(l)) for l in libs),
        )
        self.run(self._tmp_prefix() + cmd, env="conanbuild")

    def _sign_ohos_elf(self, path):
        if str(self.settings.os) != "OHOS":
            return
        signer = shutil.which("binary-sign-tool") or (
            "/data/service/hnp/bin/binary-sign-tool"
        )
        objcopy = shutil.which("llvm-objcopy") or (
            "/data/service/hnp/bin/llvm-objcopy"
        )
        if not os.path.isfile(signer) or not os.path.isfile(objcopy):
            raise ConanException("required OHOS signing tools are missing")
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", path],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=120,
        )
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", path,
             "-selfSign", "1"],
            check=True,
            timeout=180,
        )
        os.chmod(path, 0o755)

    def test(self):
        if not can_run(self):
            raise ConanException("libxspf test binary is not runnable here")
        result = {
            "executed": True,
            "passed": True,
            "command": "./test_xspf",
            "discovered": TEST_ASSERTIONS,
            "passedCount": TEST_ASSERTIONS,
        }
        binary = os.path.join(self.build_folder, "test_xspf")
        if not os.path.isfile(binary):
            raise ConanException("test binary was not built: " + binary)
        # OHOS cannot execute unsigned ELF binaries.
        self._sign_ohos_elf(binary)
        try:
            self.run(
                self._tmp_prefix() + "\"{}\"".format(binary),
                env="conanrun",
            )
        except Exception as exc:
            result["passed"] = False
            result["passedCount"] = 0
            print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result),
                  flush=True)
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result)
            )
            raise ConanException(
                "test_xspf consumer test failed: {}".format(exc)
            )
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result), flush=True)
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result))
        # Re-emit the upstream evidence persisted in package/res/ so every
        # round carries HMBS_UPSTREAM_TEST_RESULT even when the Conan cache
        # skips build() (boost1.84-coroutine precedent). Dual channel.
        # No fallback fabrication: a missing file means the package
        # predates the persistence change and must be rebuilt.
        reemitted = False
        for dep in self.dependencies.host.values():
            try:
                cand = os.path.join(
                    dep.package_folder, "res", "upstream_test_result.json")
            except Exception:
                continue
            if not os.path.isfile(cand):
                continue
            try:
                with open(cand, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
            except (OSError, ValueError) as exc:
                raise ConanException(
                    "persisted upstream result unreadable ({}): {}".format(
                        cand, exc))
            print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(data),
                  flush=True)
            self.output.info(
                "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(data))
            reemitted = True
            break
        if not reemitted:
            raise ConanException(
                "persisted upstream_test_result.json not found in the "
                "tested package (res/); rebuild the package so build() "
                "persists the real `make check` evidence")
