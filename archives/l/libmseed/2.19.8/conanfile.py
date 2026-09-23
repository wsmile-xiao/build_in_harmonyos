#!/usr/bin/env python3
"""Conan recipe — libmseed 2.19.8 (Makefile)"""

import glob
import json
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LibmseedConan(ConanFile):
    name = "libmseed"
    version = "2.19.8"
    description = "C library for manipulation of miniSEED seismological time series data"
    license = "Apache-2.0"
    homepage = "https://github.com/EarthScope/libmseed"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = "seismology", "miniseed", "seed", "geophysics"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libmseed supports Linux and OHOS, not %s" % self.settings.os
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass

    def _usable(self, path):
        if not path:
            return None
        if os.path.isabs(path):
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
            return None
        found = shutil.which(path)
        return found or None

    def _real_binary(self, path):
        # CI #48558: the previous sibling-ELF heuristic (prefix match on
        # the wrapper basename) resolved `clang` -> `clang-check` because
        # `clang-check` sorts right after `clang` and starts with it, but
        # clang-check does not accept `-o` so every compile failed with
        # `clang-check: Unknown command line argument '-o'`. Wrapper
        # scripts are executable shims and must be used directly; never
        # substitute a sibling binary.
        return path

    def _tool(self, key, fallback):
        # OHOS conan (2.29/2.30) does not support the dotted sub-key syntax
        # tools.build:compiler_executables:<key> (raises
        # "[conf] ... does not exist in configuration list"). Read the whole
        # dict once and take the key from it (bzip2/zsv proven pattern).
        # Round 3: the conf value itself may point at a toolchain path that
        # does not exist on the preflight worker
        # (make: /data/service/hnp/bin/clang: No such file or directory),
        # so validate existence and fall back to a discoverable compiler
        # instead of trusting the absolute path blindly.
        try:
            execs = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict)
        except ConanException:
            execs = {}
        configured = (execs.get(key) if execs else None) or None
        usable = self._usable(configured) if configured else None
        if usable:
            # Never accept analysis tools as the C compiler (CI #48558:
            # `clang` wrapper must not resolve to `clang-check`).
            if key == "c" and os.path.basename(usable) in (
                    "clang-check", "clang-tidy", "clang-format"):
                self.output.warning(
                    "compiler_executables[c]=%s is not a compiler; ignoring" % usable)
            else:
                return self._real_binary(usable)
        if configured:
            self.output.warning(
                "compiler_executables[%s]=%s not usable on this worker; "
                "falling back to discoverable toolchain" % (key, configured))
        if key == "c":
            for name in ("clang", "cc", "gcc"):
                found = shutil.which(name)
                if found:
                    return self._real_binary(found)
            for env_key in ("CC",):
                env_val = os.environ.get(env_key)
                usable_env = self._usable(env_val) if env_val else None
                if usable_env:
                    return self._real_binary(usable_env)
        if key in ("ar", "ranlib"):
            cc_conf = (execs.get("c") if execs else None) or None
            cc_path = self._usable(cc_conf) if cc_conf else None
            if not cc_path:
                for name in ("clang", "cc", "gcc"):
                    cc_path = shutil.which(name)
                    if cc_path:
                        break
            if cc_path:
                cc_dir = os.path.dirname(cc_path)
                for name in (fallback, "llvm-ar", "llvm-ranlib", "ar", "ranlib"):
                    candidate = os.path.join(cc_dir, name)
                    if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                        return candidate
            for name in (fallback, "llvm-ar", "llvm-ranlib", "ar", "ranlib"):
                found = shutil.which(name)
                if found:
                    return found
        found_fallback = self._usable(fallback)
        return found_fallback or fallback

    def build(self):
        apply_conandata_patches(self)
        cc = self._tool("c", "clang")
        ar = self._tool("ar", "llvm-ar")
        ranlib = self._tool("ranlib", "llvm-ranlib")
        if os.path.basename(cc) in ("clang-check", "clang-tidy", "clang-format"):
            raise ConanException(
                "resolved CC=%s is not a compiler; refusing to build" % cc)
        # R33: compilers come from Conan conf, never from shell env vars.
        base = "make -j1 CC=%s AR=%s RANLIB=%s" % (cc, ar, ranlib)
        self.output.info("Building libmseed static library: %s static" % base)
        self.run("%s static" % base, cwd=self.source_folder)
        if self.options.shared:
            self.output.info("Building libmseed shared library: %s shared" % base)
            self.run("%s shared" % base, cwd=self.source_folder)
        self._run_upstream_tests(cc, ar, ranlib)

    def _run_upstream_tests(self, cc, ar, ranlib):
        # Upstream test entry is `make check` (top Makefile: `test check: static`
        # runs `make -C test test`). The test/ suite builds 2 C programs
        # (lmtestpack, lmtestparse) and runs 31 shell-script tests (*.test),
        # each diffed against its *.test.ref reference. A mismatch prints
        # FAILED but still exits 0, so the result must be parsed from output,
        # never inferred from the return code.
        test_dir = os.path.join(self.source_folder, "test")
        if not os.path.isdir(test_dir):
            raise ConanException("upstream test directory not found: %s" % test_dir)
        cases = sorted(os.path.basename(p) for p in glob.glob(os.path.join(test_dir, "*.test")))
        cases = [c for c in cases if not c.endswith((".ref", ".out"))]
        programs = sorted(os.path.basename(p) for p in glob.glob(os.path.join(test_dir, "*.c")))
        discovered = len(cases) + len(programs)
        if discovered <= 0:
            raise ConanException("no upstream tests discovered in %s" % test_dir)
        # Honesty guard: reference files must be non-empty, otherwise a
        # diff of empty-vs-empty would report a false PASSED.
        empty_refs = []
        for case in cases:
            ref = os.path.join(test_dir, case + ".ref")
            try:
                if (not os.path.isfile(ref)) or os.path.getsize(ref) == 0:
                    empty_refs.append(case)
            except OSError:
                empty_refs.append(case)
        if empty_refs:
            raise ConanException(
                "upstream reference files missing or empty: %s" % ", ".join(empty_refs[:5])
            )
        shell = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
        cmd = ["make", "check", "CC=%s" % cc, "AR=%s" % ar, "RANLIB=%s" % ranlib,
               "SHELL=%s" % shell, "-j1"]
        self.output.info("Running upstream libmseed suite: %s" % " ".join(cmd))
        try:
            proc = subprocess.run(
                cmd,
                cwd=self.source_folder,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=1800,
            )
        except Exception as exc:
            raise ConanException("upstream test harness could not run: %r" % exc)
        output = proc.stdout or ""
        for line in output.splitlines()[-60:]:
            self.output.info("[upstream] %s" % line)
        passed = output.count("PASSED")
        failed = output.count("FAILED")
        executed = passed + failed
        self.output.info(
            "Upstream tally: discovered=%d executed=%d passed=%d failed=%d" % (
                discovered, executed, passed, failed)
        )
        if executed < discovered or failed > 0 or passed <= 0:
            status = "failed"
        elif proc.returncode != 0:
            status = "failed"
        else:
            status = "passed"
        marker = {
            "status": status,
            "framework": "makefile",
            "command": "make check -j1",
            "discovered": discovered,
            "executed": executed,
            "passed": passed if status == "passed" else 0,
            "failed": failed if status == "passed" else max(failed, discovered - passed),
            "skipped": 0,
        }
        if status != "passed":
            marker["reason"] = "output tail: %s" % " | ".join(output.splitlines()[-5:])
        line = "HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(marker)
        print(line, flush=True)
        self.output.info(line)
        sys.stdout.flush()
        try:
            result_path = os.path.join(self.build_folder, "upstream_test_result.json")
            with open(result_path, "w", encoding="utf-8") as handle:
                json.dump(marker, handle, ensure_ascii=False)
            self.output.info("persisted upstream test result to %s" % result_path)
        except Exception as exc:
            raise ConanException("failed to persist upstream_test_result.json: %s" % exc)
        if status != "passed":
            raise ConanException(
                "upstream libmseed suite failed "
                "(discovered=%d executed=%d passed=%d failed=%d)" % (
                    discovered, executed, passed, failed)
            )

    def package(self):
        copy(self, "libmseed.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "libmseed.a", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        for pattern in ("libmseed.so*", "libmseed.*.dylib"):
            copy(self, pattern, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        self._install_pkgconfig()
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # Ship the persisted upstream result so test_package can re-emit the
        # identical HMBS_UPSTREAM_TEST_RESULT marker even when conan skips
        # build() on a cached binary ("Already installed!").
        result_path = os.path.join(self.build_folder, "upstream_test_result.json")
        if os.path.isfile(result_path):
            res_dir = os.path.join(self.package_folder, "res")
            os.makedirs(res_dir, exist_ok=True)
            copy(self, "upstream_test_result.json",
                 self.build_folder, res_dir, keep_path=False)
        else:
            self.output.warning("upstream_test_result.json not found in build "
                                "folder; package will lack upstream evidence")

    def _install_pkgconfig(self):
        template = os.path.join(self.source_folder, "mseed.pc.in")
        if not os.path.isfile(template):
            self.output.warning("mseed.pc.in not found; skipping pkgconfig file")
            return
        try:
            with open(template, "r", encoding="utf-8", errors="replace") as handle:
                content = handle.read()
        except OSError as exc:
            raise ConanException("cannot read mseed.pc.in: %s" % exc)
        content = content.replace("@prefix@", "${pcfiledir}/../..")
        content = content.replace("@exec_prefix@", "${prefix}")
        content = content.replace("@libdir@", "${prefix}/lib")
        content = content.replace("@includedir@", "${prefix}/include")
        content = content.replace("@PACKAGE_NAME@", "libmseed")
        content = content.replace(
            "@PACKAGE_URL@", "https://github.com/EarthScope/libmseed")
        content = content.replace("@VERSION@", self.version)
        pc_dir = os.path.join(self.build_folder, "mseed-pkgconfig")
        os.makedirs(pc_dir, exist_ok=True)
        pc_file = os.path.join(pc_dir, "mseed.pc")
        with open(pc_file, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        copy(self, "mseed.pc", src=pc_dir,
             dst=os.path.join(self.package_folder, "lib", "pkgconfig"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["mseed"]
        self.cpp_info.set_property("cmake_file_name", "libmseed")
        self.cpp_info.set_property("cmake_target_name", "libmseed::libmseed")
        self.cpp_info.set_property("pkg_config_name", "mseed")
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
