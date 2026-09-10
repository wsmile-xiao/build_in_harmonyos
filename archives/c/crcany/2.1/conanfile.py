#!/usr/bin/env python3
"""Conan recipe — crcany 2.1 (Makefile)

crcany is Mark Adler's suite of programs that generalize CRC calculations and
generate C code to compute and combine CRCs efficiently. Upstream builds with a
plain GNU Makefile (no configure, no install target): `make` compiles the
crcany/crctest/crcall/crcadd/mincrc executables plus generated sources, and
`make test` runs the official verification over all catalogued CRC models in
allcrcs-abbrev.txt. This recipe publishes the callable routines
(model/crc/crcdbl/crcgen) as a static library; the CLI tools are built for the
upstream test but intentionally not packaged, so this stays a pure library
package (no commands.json required).
"""

import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class CrcanyConan(ConanFile):
    name = "crcany"
    version = "2.1"
    description = "Compute any CRC and generate C code for efficient CRC calculation and combination."
    license = "Zlib"
    homepage = "https://github.com/madler/crcany"
    url = ""
    topics = "crc", "checksum", "code-generation"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "crcany 2.1 upstream Makefile builds static objects only; shared is not supported"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _resolve_tool(self, conf_value, *fallbacks):
        # HMBS injects tools.build:compiler_executables, but the absolute
        # path inside can be stale on a given worker (e.g. previous preflight
        # saw /data/service/hnp/bin/clang missing -> make Error 127).
        # Prefer a value that actually exists; otherwise fall back to a
        # PATH-resolvable name (HMBS prepends tool dirs to buildenv PATH).
        candidates = [conf_value] + list(fallbacks)
        for cand in candidates:
            if not cand:
                continue
            if os.path.isabs(cand):
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    return cand
            else:
                found = shutil.which(cand)
                if found:
                    return found
                # Bare name with no which() hit (buildenv PATH not visible
                # at recipe-import time): still usable via self.run(env=...).
                return cand
        return conf_value or (fallbacks[0] if fallbacks else "")

    def _compiler_from_conf(self):
        # R33: compiler path comes from Conan conf (HMBS injects
        # tools.build:compiler_executables), never from shell $CC.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        # NOTE: tools.build:compiler_executables is a dict conf; there is no
        # 'tools.build:compiler_executables:ar' sub-conf (conan raises
        # "[conf] ... does not exist in configuration list"). Read 'ar' from
        # the same dict with a PATH-resolvable fallback.
        cc = self._resolve_tool(compilers.get("c"), "clang", "cc", "/data/service/hnp/bin/clang")
        ar = self._resolve_tool(compilers.get("ar"), "llvm-ar", "ar", "/data/service/hnp/bin/llvm-ar")
        self.output.info("resolved CC=%s AR=%s (conf=%s)" % (cc, ar, compilers))
        return cc, ar

    def _write_upstream_result(self, data):
        try:
            os.makedirs(self.build_folder, exist_ok=True)
            path = os.path.join(self.build_folder, "upstream_test_result.json")
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                json.dump(data, f, ensure_ascii=False)
        except OSError as e:
            self.output.warning("write upstream_test_result.json failed: %s" % e)

    def _run_upstream_tests(self, cc):
        # Upstream test entry is `make test`: it feeds every model in
        # allcrcs-abbrev.txt to ./crctest (bit/residue/byte/word/combine
        # verification per model) and then runs the generated-code check
        # src/test_src. It needs no network (the networked `getcrcs`
        # comparison only runs under the separate `checklists` target).
        abbrev = os.path.join(self.source_folder, "allcrcs-abbrev.txt")
        try:
            size = os.path.getsize(abbrev)
        except OSError:
            size = 0
        self.output.info("allcrcs-abbrev.txt size %d" % size)
        if size <= 0:
            raise RuntimeError("allcrcs-abbrev.txt is empty or missing; upstream fixture did not unpack")

        cmd = ["make", "test", "CC=%s" % cc]
        self.output.info("Running upstream tests: %s (cwd=source_folder)" % " ".join(cmd))
        env = os.environ.copy()
        for key in ("TMPDIR", "TMP", "TEMP"):
            value = os.environ.get(key)
            if value:
                env[key] = value
        proc = subprocess.run(
            cmd,
            cwd=self.source_folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=1200,
            env=env,
        )
        out = proc.stdout or ""
        # Keep the full evidence in the log (tail at minimum) so CI L1c can
        # see the real `make test` trace instead of a bare exit code.
        self.output.info("make test returncode=%d" % proc.returncode)
        self.output.info("make test output tail:\n%s" % out[-4000:])
        if not out.strip():
            raise RuntimeError("make test produced no output; harness did not really run")

        # Falsification guard: upstream crctest.c returns 0 even when it
        # prints "** verification failed", so exit code alone proves nothing.
        # Require the explicit "-- all good" verdict plus consistent counters.
        if proc.returncode != 0:
            raise RuntimeError("make test failed with returncode %d" % proc.returncode)
        if "-- all good" not in out:
            raise RuntimeError("make test missing '-- all good' verdict; output tail: %s" % out[-1000:])

        def _pair(pattern, text):
            match = re.search(pattern, text)
            if not match:
                return None
            return int(match.group(1)), int(match.group(2))

        bit = _pair(r"(\d+)\s+models?\s+verified\s+bit-wise\s+out\s+of\s+(\d+)\s+usable", out)
        residue = _pair(r"(\d+)\s+model\s+residues\s+verified\s+out\s+of\s+(\d+)\s+usable", out)
        bytewise = _pair(r"(\d+)\s+models?\s+verified\s+byte-wise\s+out\s+of\s+(\d+)\s+usable", out)
        wordwise = _pair(r"(\d+)\s+models?\s+verified\s+word-wise\s+out\s+of\s+(\d+)\s+usable", out)
        combine = _pair(r"(\d+)\s+models?\s+verified\s+combine\s+out\s+of\s+(\d+)\s+usable", out)
        groups = [bit, residue, bytewise, wordwise, combine]
        if any(g is None for g in groups):
            raise RuntimeError("could not parse all five crctest counters from make test output")
        for good, num in groups:
            if good != num or num <= 0:
                raise RuntimeError("upstream counter not fully passing: %s" % (groups,))
        discovered = bit[1]
        upstream = {
            "status": "passed",
            "framework": "make-test",
            "command": "make test",
            "discovered": discovered,
            "executed": discovered,
            "passed": discovered,
            "failed": 0,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
        self._write_upstream_result(upstream)

    def build(self):
        apply_conandata_patches(self)
        cc, ar = self._compiler_from_conf()
        # R33: CC comes from the conf-derived `cc` python variable, not from
        # a shell environment expansion (L0h scans self.run strings).
        # Single job per OHOS platform constraint.
        self.run("make -j1 CC=%s" % cc, env="conanbuild", cwd=self.source_folder)
        # Layer 1: official upstream suite, parsed (not just exit code).
        self._run_upstream_tests(cc)
        # Archive the callable routines as a static library. The executables
        # (crcany/crcall/crcadd/crctest/mincrc) stay in the build tree only.
        lib = os.path.join(self.build_folder, "libcrcany.a")
        self.run(
            '"%s" rcs "%s" model.o crc.o crcdbl.o crcgen.o' % (ar, lib),
            env="conanbuild",
            cwd=self.source_folder,
        )

    def package(self):
        copy(self, "libcrcany.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
        for header in ("model.h", "crc.h", "crcdbl.h", "crcgen.h"):
            copy(self, header, src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        try:
            copy(
                self,
                "upstream_test_result.json",
                src=self.build_folder,
                dst=os.path.join(self.package_folder, "res"),
            )
        except Exception:
            pass

    def package_info(self):
        self.cpp_info.libs = ["crcany"]
        self.cpp_info.set_property("cmake_file_name", "crcany")
        self.cpp_info.set_property("cmake_target_name", "crcany::crcany")
        self.cpp_info.set_property("pkg_config_name", "crcany")
