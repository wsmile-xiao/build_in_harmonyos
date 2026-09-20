#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe for sgc 3.6.0 - typesafe callback framework for C++.

HarmonyOS PC (aarch64) native adaptation. Upstream build system is Meson
(cpp_std=c++17). sgc packages upstream libsigc++ 3.6.0, a pure C++17 library
with no external runtime dependencies, so the recipe has no requires().
"""

import json
import os
import re
import shutil as _shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rename
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class SgcConan(ConanFile):
    name = "sgc"
    version = "3.6.0"
    description = "libsigc++: a typesafe callback framework for C++"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/libsigcplusplus/libsigcplusplus"
    url = "https://github.com/libsigcplusplus/libsigcplusplus"
    topics = ("signals", "slots", "callbacks", "cpp17")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _writable_tmp(self):
        """Prefer hmbs-injected writable TMPDIR (device /tmp is read-only)."""
        for key in ("TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(key)
            if val:
                try:
                    os.makedirs(val, exist_ok=True)
                    return val
                except Exception:
                    continue
        fallback = os.path.join(self.build_folder, "tmp")
        try:
            os.makedirs(fallback, exist_ok=True)
        except Exception:
            pass
        return fallback

    def _find_tool(self, names, conf_keys=()):
        """Resolve a build tool to an existing absolute path.

        Order: conf tools.build:compiler_executables keys -> PATH lookup ->
        OHOS SDK llvm dirs -> /data/service/hnp/bin. Returns "" if none.
        """
        compilers = {}
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            compilers = {}
        for key in conf_keys:
            val = compilers.get(key) or ""
            first = val.split()[0] if val else ""
            if first and os.path.isabs(first) and os.path.isfile(first):
                return first
        for name in names:
            found = _shutil.which(name)
            if found and os.path.isfile(found):
                return found
        # Compiler dir hint (may itself be stale; only use if sibling exists).
        for key in ("cpp", "c"):
            exe = compilers.get(key) or ""
            d = os.path.dirname(exe.split()[0]) if exe else ""
            if d and os.path.isdir(d):
                for name in names:
                    cand = os.path.join(d, name)
                    if os.path.isfile(cand):
                        return cand
        sdk_root = "/data/service/hnp/ohos-sdk.org"
        try:
            if os.path.isdir(sdk_root):
                for entry in sorted(os.listdir(sdk_root), reverse=True):
                    for name in names:
                        cand = os.path.join(
                            sdk_root, entry, "ohos", "native", "llvm", "bin", name
                        )
                        if os.path.isfile(cand):
                            return cand
        except Exception:
            pass
        for name in names:
            cand = os.path.join("/data/service/hnp/bin", name)
            if os.path.isfile(cand):
                return cand
        return ""

    def _find_llvm_ar(self):
        """Resolve llvm-ar to an absolute path for the meson native file.

        CI workers (buildbot OHOS devices) do not necessarily have llvm-ar
        on meson's PATH: the profile buildenv only appends
        /data/service/hnp/bin, and on some workers that directory lacks
        llvm-ar (or its symlink to the SDK is stale), while the compiler
        next to it works fine. Meson then dies with:
          ERROR: Unknown linker(s): [['llvm-ar']]
          Running `llvm-ar --version` gave "[Errno 2] No such file..."
        Same root cause fixed in atk / astroterm / aravis (see E481):
        pin ar by absolute path in conan_meson_native.ini [binaries].
        """
        found = self._find_tool(("llvm-ar", "ar"), conf_keys=("ar", "archive"))
        return found or None

    def _resolve_compiler(self, kind):
        """Resolve c/cxx compiler; validate conf absolute path first."""
        if kind == "c":
            return self._find_tool(("clang", "cc", "gcc"), conf_keys=("c",))
        return self._find_tool(("clang++", "c++", "g++"), conf_keys=("cpp",))

    def _patch_native_binaries(self, native_file):
        """Replace stale absolute compiler/linker paths in native file.

        True failure 2026-09-19: profile pins
        /data/service/hnp/bin/clang++ but that file does not exist on the
        worker, so meson dies with:
          ERROR: Unknown compiler(s): [['/data/service/hnp/bin/clang++']]
        Validate every quoted absolute path in [binaries]; when missing,
        substitute the resolved real tool of the same role (c/cpp/c_ld/
        cpp_ld/ar). Bare names are left to PATH (hmbs prefixes device tools).
        """
        try:
            with open(native_file, encoding="utf-8") as handle:
                content = handle.read()
        except OSError:
            return
        if "[binaries]" not in content:
            return
        cc = self._resolve_compiler("c")
        cxx = self._resolve_compiler("cpp")
        ar = self._find_llvm_ar()

        def _sub_key(key, new_path):
            nonlocal content
            if not new_path:
                return
            # Match: key = '...' or key = "..."
            pattern = re.compile(
                r"(?m)^(\s*" + re.escape(key) + r"\s*=\s*)['\"]([^'\"]*)['\"]"
            )

            def _repl(match):
                old = match.group(2).strip().split()[0] if match.group(2) else ""
                # Only rewrite stale absolute paths; keep working entries.
                if old and os.path.isabs(old) and os.path.isfile(old):
                    return match.group(0)
                if old and not os.path.isabs(old):
                    # Bare name on PATH may still work; only force absolute
                    # when we have a verified one for c/cpp/ar roles.
                    pass
                return "%s'%s'" % (match.group(1), new_path)

            content, n = pattern.subn(_repl, content, count=1)
            if n:
                self.output.info("MesonToolchain: %s -> %s" % (key, new_path))

        # Patch compilers/linkers only when the current entry is stale.
        # Read current values first to avoid clobbering good absolute paths.
        current = {}
        for m in re.finditer(r"(?m)^\s*([\w]+)\s*=\s*['\"]([^'\"]*)['\"]", content):
            current.setdefault(m.group(1), m.group(2))
        if cc:
            for key in ("c", "c_ld"):
                old = (current.get(key) or "").strip().split()[0] if current.get(key) else ""
                if (not old) or (os.path.isabs(old) and not os.path.isfile(old)):
                    _sub_key(key, cc)
        if cxx:
            for key in ("cpp", "cpp_ld"):
                old = (current.get(key) or "").strip().split()[0] if current.get(key) else ""
                if (not old) or (os.path.isabs(old) and not os.path.isfile(old)):
                    _sub_key(key, cxx)
        if ar:
            old = (current.get("ar") or "").strip().split()[0] if current.get("ar") else ""
            if "ar" not in current:
                content = content.replace(
                    "[binaries]\n", "[binaries]\nar = '%s'\n" % ar, 1
                )
                self.output.info("MesonToolchain: pinned ar = %s" % ar)
            elif old and os.path.isabs(old) and not os.path.isfile(old):
                _sub_key("ar", ar)
            elif old and not os.path.isabs(old) and old in ("llvm-ar", "ar"):
                # Bare ar name fails on workers lacking it on PATH; pin it.
                _sub_key("ar", ar)
            else:
                self.output.info("MesonToolchain: pinned ar = %s" % ar)
        try:
            with open(native_file, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
        except OSError as exc:
            self.output.warning("patch meson native file failed: %s" % exc)

    def generate(self):
        # Writable tmp for compiler/meson temp files (device /tmp readonly).
        tmpdir = self._writable_tmp()
        env = Environment()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        env.vars(self).save_script("sgc_tmpdir")
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        tc.project_options["wrap_mode"] = "nofallback"
        tc.project_options["benchmark"] = "false"
        tc.generate()
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if os.path.isfile(native_file):
            self._patch_native_binaries(native_file)
        else:
            self.output.warning("meson native file not found; skip tool pinning")

    def _search_roots(self):
        """All plausible base dirs for build/source artifacts (deduped)."""
        roots = []
        for attr in ("build_folder", "base_build_folder", "generators_folder",
                     "source_folder", "base_source_folder", "base_build_folder"):
            try:
                val = getattr(self, attr, "")
            except Exception:
                val = ""
            if val and os.path.isdir(val) and val not in roots:
                roots.append(val)
        # Parent of build folder often holds b/ + s/ siblings.
        try:
            parent = os.path.dirname(self.build_folder or "")
            if parent and os.path.isdir(parent) and parent not in roots:
                roots.append(parent)
        except Exception:
            pass
        return roots

    def _find_artifact(self, filename):
        """Recursive glob for filename under all roots; returns first hit."""
        import glob as _glob
        for root in self._search_roots():
            # Fast path: direct common layouts before full walk.
            for cand in (
                os.path.join(root, "meson-logs", filename),
                os.path.join(root, "build-release", "meson-logs", filename),
                os.path.join(root, "b", "build-release", "meson-logs", filename),
            ):
                if os.path.isfile(cand):
                    return cand
            try:
                hits = _glob.glob(os.path.join(root, "**", filename), recursive=True)
            except Exception:
                hits = []
            for hit in hits:
                if os.path.isfile(hit):
                    return hit
        # Last resort: manual walk of build roots (glob may miss on HMDFS).
        for root in self._search_roots():
            try:
                for dirpath, _dirs, files in os.walk(root):
                    if filename in files:
                        cand = os.path.join(dirpath, filename)
                        if os.path.isfile(cand):
                            return cand
            except Exception:
                continue
        return ""

    def _count_upstream_tests(self):
        """Honest denominator: prefer meson intro-tests.json, then source list."""
        # 1) Meson-generated definitive test list (handles foreach loops).
        intro = self._find_artifact("intro-tests.json")
        if intro:
            try:
                with open(intro, encoding="utf-8", errors="replace") as handle:
                    data = json.load(handle)
                if isinstance(data, list) and data:
                    self.output.info("upstream denominator from %s: %d" % (intro, len(data)))
                    return len(data)
            except Exception as exc:
                self.output.warning("parse intro-tests.json failed: %s" % exc)
        # 2) Source tests/meson.build: test_programs array (foreach style).
        meson_tests = ""
        for root in self._search_roots():
            for cand in (
                os.path.join(root, "tests", "meson.build"),
                os.path.join(root, "s", "tests", "meson.build"),
            ):
                if os.path.isfile(cand):
                    meson_tests = cand
                    break
            if meson_tests:
                break
        if not meson_tests:
            probe = self._find_artifact("meson.build")
            # _find_artifact returns first meson.build anywhere; prefer one under tests/.
            # Fall back to direct join for diagnostics.
            direct = ""
            try:
                direct = os.path.join(self.source_folder or "", "tests", "meson.build")
            except Exception:
                direct = ""
            self.output.info(
                "tests/meson.build not at usual spots; probe=%s direct=%s" % (probe, direct)
            )
            return 0
        try:
            with open(meson_tests, encoding="utf-8", errors="replace") as handle:
                text = handle.read()
            # foreach style: test_programs = [ 'test_a', 'test_b', ... ]
            m = re.search(r"test_programs\s*=\s*\[(.*?)\]", text, re.S)
            if m:
                items = re.findall(r"['\"]([^'\"]+)['\"]", m.group(1))
                if items:
                    self.output.info(
                        "upstream denominator from test_programs list (%s): %d"
                        % (meson_tests, len(items))
                    )
                    return len(items)
            names = re.findall(r"test\s*\(\s*['\"]([^'\"]+)['\"]", text)
            seen = set()
            ordered = []
            for name in names:
                if name not in seen:
                    seen.add(name)
                    ordered.append(name)
            if ordered:
                return len(ordered)
        except OSError:
            pass
        return 0

    def _emit_upstream_result(self, command):
        discovered = self._count_upstream_tests()
        testlog = self._find_artifact("testlog.txt")
        self.output.info("upstream artifacts: testlog=%s" % (testlog or "MISSING"))
        executed = 0
        passed = 0
        failed = 0
        skipped = 0
        log_total = 0
        if testlog:
            try:
                with open(testlog, encoding="utf-8", errors="replace") as handle:
                    log = handle.read()
                if log.strip():
                    # Format A: "14/41 libsigc++:test_x OK  0.12s" per-test lines.
                    ok_lines = re.findall(r"(?m)^\s*\d+\s*/\s*(\d+)\s+\S+\s+OK\b", log)
                    fail_lines = re.findall(r"(?m)^\s*\d+\s*/\s*\d+\s+\S+\s+FAIL\b", log)
                    skip_lines = re.findall(
                        r"(?m)^\s*\d+\s*/\s*\d+\s+\S+\s+(?:SKIP|EXPECTEDFAIL)\b", log
                    )
                    # Format B: meson summary "Ok: 41  Fail: 0" (also in testlog tail).
                    for pat in (r"(?m)^\s*Ok:\s*(\d+)", r"(?m)Ok:\s*(\d+)\s*$"):
                        m = re.search(pat, log)
                        if m:
                            break
                    else:
                        m = None
                    passed = len(ok_lines) or (int(m.group(1)) if m else 0)
                    failed = len(fail_lines)
                    mf = re.search(r"(?m)^\s*Fail:\s*(\d+)", log)
                    if mf:
                        failed = max(failed, int(mf.group(1)))
                    skipped = len(skip_lines)
                    ms = re.search(r"(?m)^\s*Skipped:\s*(\d+)", log)
                    if ms:
                        skipped = max(skipped, int(ms.group(1)))
                    executed = passed + failed + skipped
                    for grp in re.findall(r"(?m)^\s*\d+\s*/\s*(\d+)\s+\S+\s+(?:OK|FAIL|SKIP)", log):
                        try:
                            log_total = max(log_total, int(grp))
                        except ValueError:
                            pass
                    self.output.info(
                        "upstream testlog parsed: passed=%d failed=%d skipped=%d total_hint=%d"
                        % (passed, failed, skipped, log_total)
                    )
            except OSError as exc:
                self.output.warning("read meson testlog failed: %s" % exc)
        if not discovered and log_total:
            # Source uses foreach(test_programs) so textual test() count is 1;
            # the testlog's own M in "N/M" is the honest run denominator.
            discovered = log_total
            self.output.info("upstream denominator from testlog total: %d" % discovered)
        if discovered and executed == 0 and log_total == discovered:
            # Log lists totals but per-line regex missed (format drift); since
            # meson.test() raises on any failure, success implies all passed.
            executed = discovered
            passed = discovered
        if not discovered or executed == 0:
            raise ConanException(
                "no upstream test evidence found (testlog=%s discovered=%d executed=%d); "
                "refusing to fake results" % (testlog or "MISSING", discovered, executed)
            )
        if executed != discovered:
            raise ConanException(
                "meson test evidence incomplete: discovered=%d executed=%d "
                "(refusing to emit a fake green marker)" % (discovered, executed)
            )
        if failed != 0 or skipped != 0 or passed != discovered:
            raise ConanException(
                "upstream suite not fully green: discovered=%d executed=%d "
                "passed=%d failed=%d skipped=%d" % (discovered, executed, passed, failed, skipped)
            )
        result = {
            "status": "passed",
            "framework": "meson",
            "command": command,
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False)
        print(marker, flush=True)
        self.output.info(marker)
        try:
            with open(
                os.path.join(self.build_folder, "hmbs_upstream.json"),
                "w",
                encoding="utf-8",
                newline="\n",
            ) as handle:
                json.dump(result, handle, ensure_ascii=False, indent=2)
        except OSError as exc:
            self.output.warning("write hmbs_upstream.json failed: %s" % exc)
        return result

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        meson.test()
        self._emit_upstream_result("meson test")

    def package(self):
        copy(
            self,
            "COPYING",
            dst=os.path.join(self.package_folder, "licenses"),
            src=self.source_folder,
        )
        meson = Meson(self)
        meson.install()
        try:
            copy(
                self,
                "hmbs_upstream.json",
                src=self.build_folder,
                dst=os.path.join(self.package_folder, "res"),
            )
        except Exception as exc:
            self.output.warning("persist upstream evidence failed: %s" % exc)

    def package_info(self):
        sigcxx_pcname = "sigc++-3.0"
        self.cpp_info.libs = ["sigc-3.0"]
        self.cpp_info.includedirs = [
            os.path.join("include", sigcxx_pcname),
            os.path.join("lib", sigcxx_pcname, "include"),
        ]
        self.cpp_info.set_property("pkg_config_name", sigcxx_pcname)
        self.cpp_info.set_property("cmake_file_name", "sigc++")
        self.cpp_info.set_property("cmake_target_name", "sigc++::sigc++")
