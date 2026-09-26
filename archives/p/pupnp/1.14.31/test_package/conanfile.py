#!/usr/bin/env python3
"""Consumer test for pupnp/1.14.31.

Builds test_pupnp.c against the packaged shared libraries (UPNP::Shared)
and runs three real-API scenarios: ixml DOM parse/traverse/serialize,
pre-init server accessors plus error-message lookup, and the full
UpnpInit2/UpnpFinish lifecycle. Emits HMBS_TEST_PACKAGE_RESULT with
scenario counts parsed from the executable's own structured stdout, and
re-emits the upstream CTest result carried in the package res/ so every
round provides evidence.
"""

import json
import os
import re
import shutil

from conan import ConanFile
from conan.tools.build import can_run, cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv


class PupnpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _ensure_writable_tmp(self):
        # Mirror main recipe: redirect temp root away from read-only /tmp.
        candidates = []
        for key in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR",
                    "HMBS_AUTOCONF_MKTEMP_FALLBACK"):
            val = os.getenv(key)
            if val and val not in candidates:
                candidates.append(val)
        cap = os.getenv("HMBS_PLATFORM_CAPABILITIES")
        if cap:
            try:
                tmpdir = json.loads(cap).get("tmpdir")
                if tmpdir and tmpdir not in candidates:
                    candidates.insert(0, tmpdir)
            except Exception:
                pass
        home = os.path.expanduser("~")
        if home and home != "~":
            home_tmp = os.path.join(home, "tmp")
            if home_tmp not in candidates:
                candidates.append(home_tmp)
        try:
            bf = getattr(self, "build_folder", None)
            if bf:
                local_tmp = os.path.join(bf, "hmbs-tmp")
                if local_tmp not in candidates:
                    candidates.append(local_tmp)
        except Exception:
            pass
        for cand in candidates:
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs_write_probe")
                with open(probe, "w") as handle:
                    handle.write("ok")
                os.remove(probe)
                os.environ["TMPDIR"] = cand
                os.environ["TMP"] = cand
                os.environ["TEMP"] = cand
                os.environ["GOTMPDIR"] = cand
                return cand
            except Exception:
                continue
        return None

    def _resolve_compiler(self, configured, names):
        if configured and os.path.exists(configured):
            return configured
        for tool in names:
            found = shutil.which(tool)
            if found:
                return found
        home_bin = os.path.join(os.path.expanduser("~"), "usr", "local",
                                "bin")
        for tool in names:
            cand = os.path.join(home_bin, tool)
            if os.path.exists(cand):
                return cand
        return configured or names[0]

    def _fix_generated_toolchain_compiler(self, configured_map, c_tool,
                                          cxx_tool):
        # Mirror main recipe: cache_variables pin alone may not override
        # a stale profile compiler path (e.g. /data/service/hnp/bin/clang
        # after the true-device clang migration), so patch the generated
        # conan_toolchain.cmake itself -- only when the configured path is
        # missing and the resolved one exists (CI workers untouched).
        if not isinstance(configured_map, dict):
            configured_map = {}
        c_old = configured_map.get("c")
        cxx_old = configured_map.get("cpp")
        pairs = []
        if c_old and c_tool and c_old != c_tool \
                and not os.path.exists(c_old) and os.path.exists(c_tool):
            pairs.append((c_old, c_tool))
        if cxx_old and cxx_tool and cxx_old != cxx_tool \
                and not os.path.exists(cxx_old) \
                and os.path.exists(cxx_tool):
            pairs.append((cxx_old, cxx_tool))
        if not pairs:
            return
        try:
            gen_folder = getattr(self, "generators_folder", None)
            path = os.path.join(gen_folder, "conan_toolchain.cmake") \
                if gen_folder else None
            if path and os.path.isfile(path):
                with open(path, "r", encoding="utf-8",
                          errors="replace") as handle:
                    text = handle.read()
                orig = text
                for old_path, new_path in pairs:
                    text = text.replace(old_path, new_path)
                if text != orig:
                    with open(path, "w", encoding="utf-8") as handle:
                        handle.write(text)
                    self.output.info(
                        "HMBS diag fixed test toolchain %s" % path)
            else:
                self.output.warning(
                    "HMBS diag test toolchain file not found: %s" % path)
        except Exception as exc:
            self.output.warning("HMBS diag test toolchain fix failed: %s"
                                % exc)
        try:
            comp_env = Environment()
            if c_old and c_tool and (c_old, c_tool) in pairs:
                comp_env.define("CC", c_tool)
            if cxx_old and cxx_tool and (cxx_old, cxx_tool) in pairs:
                comp_env.define("CXX", cxx_tool)
            comp_env.vars(self, scope="build").save_sh("hmbs_compiler")
        except Exception as exc:
            self.output.warning(
                "HMBS diag test compiler env export failed: %s" % exc)

    def generate(self):
        tmpdir = self._ensure_writable_tmp()
        if tmpdir:
            env = Environment()
            env.define("TMPDIR", tmpdir)
            env.define("TMP", tmpdir)
            env.define("TEMP", tmpdir)
            env.define("GOTMPDIR", tmpdir)
            env.vars(self, scope="build").save_sh("hmbs_tmpdir")
        tc = CMakeToolchain(self)
        try:
            compilers = self.conf.get("tools.build:compiler_executables",
                                       default=None)
        except Exception:
            compilers = None
        if not isinstance(compilers, dict):
            compilers = {}
        c_tool = self._resolve_compiler(compilers.get("c"),
                                        ("clang", "cc"))
        cxx_tool = self._resolve_compiler(compilers.get("cpp"),
                                          ("clang++", "c++"))
        if c_tool:
            tc.cache_variables["CMAKE_C_COMPILER"] = c_tool
        if cxx_tool:
            tc.cache_variables["CMAKE_CXX_COMPILER"] = cxx_tool
        self.output.info("HMBS diag test compilers c=%s cxx=%s"
                         % (c_tool, cxx_tool))
        tc.generate()
        self._fix_generated_toolchain_compiler(compilers, c_tool, cxx_tool)
        CMakeDeps(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        self._ensure_writable_tmp()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _hmbs_emit(self, line):
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass

    def test(self):
        self._ensure_writable_tmp()
        if cross_building(self) or not can_run(self):
            self.output.info(
                "Cross build: pupnp consumer was built; run it on the "
                "HarmonyOS PC target.")
            return
        # bindirs[0] from cmake_layout is relative ("."); join with the
        # absolute build folder so the run does not depend on run()'s
        # default cwd. Fall back to a recursive search if layout shifts
        # the binary (multi-config subdir, etc.).
        bindir = "."
        try:
            if self.cpp.build.bindirs:
                bindir = self.cpp.build.bindirs[0] or "."
        except Exception:
            pass
        candidate = os.path.normpath(
            os.path.join(self.build_folder, bindir, "test_pupnp"))
        executable = candidate
        if not os.path.isfile(executable):
            for root, _dirs, files in os.walk(self.build_folder):
                if "test_pupnp" in files:
                    executable = os.path.join(root, "test_pupnp")
                    break
                if "test_pupnp.exe" in files:
                    executable = os.path.join(root, "test_pupnp.exe")
                    break
        self.output.info("HMBS diag test bindir=%s candidate=%s "
                         "resolved=%s exists=%s" % (
                             bindir, candidate, executable,
                             os.path.isfile(executable)))
        run_log = os.path.join(self.build_folder,
                               "hmbs_test_package_run.log")
        # Loader diagnostics: file exists (exists=True last round) yet the
        # shell still reports 127, so expose the real loader error instead
        # of masking it. Prepend the installed package lib dir to
        # LD_LIBRARY_PATH (musl loader on the unknown-HarmonyOS CMake
        # platform may ignore build-tree RPATH, same root cause as the
        # upstream ../ixml/libixml.so fix) and dump the run log plus
        # NEEDED entries when the run fails.
        pkg_lib = ""
        try:
            pkg_folder = self.dependencies["pupnp"].package_folder
            cand_lib = os.path.join(pkg_folder, "lib")
            if os.path.isdir(cand_lib):
                pkg_lib = cand_lib
                prev = os.environ.get("LD_LIBRARY_PATH", "")
                os.environ["LD_LIBRARY_PATH"] = pkg_lib + (":" + prev if prev else "")
            listing = sorted(os.listdir(cand_lib)) if cand_lib and os.path.isdir(cand_lib) else []
            self.output.info("HMBS diag test pkg_lib=%s libs=%s LD_LIBRARY_PATH=%s" % (
                pkg_lib, listing[:20], os.environ.get("LD_LIBRARY_PATH", "")))
        except Exception as exc:
            self.output.warning("HMBS diag test pkg lib probe failed: %s" % exc)
        try:
            self.run('"%s" > "%s" 2>&1' % (executable, run_log),
                     cwd=self.build_folder, env=["conanbuild", "conanrun"])
        except Exception:
            if os.path.isfile(run_log):
                try:
                    with open(run_log, "r", encoding="utf-8", errors="replace") as handle:
                        log_text = handle.read()
                    tail = log_text.splitlines()[-20:]
                    for line in tail:
                        self.output.info("consumer-log: %s" % line)
                    if not log_text.strip():
                        self.output.info("consumer-log: <empty run log>")
                except Exception as exc:
                    self.output.warning("HMBS diag read run log failed: %s" % exc)
            else:
                self.output.warning("HMBS diag run log missing: %s" % run_log)
            try:
                import shutil as _shutil
                import subprocess as _sp
                readelf = _shutil.which("readelf") or _shutil.which("llvm-readelf")
                if readelf and os.path.isfile(executable):
                    proc = _sp.run([readelf, "-d", executable], capture_output=True, text=True, timeout=30)
                    diag = (proc.stdout + proc.stderr).splitlines()
                    for line in diag[:30]:
                        self.output.info("consumer-needed: %s" % line)
            except Exception as exc:
                self.output.info("HMBS diag readelf probe skipped: %s" % exc)
            raise
        out = ""
        if os.path.isfile(run_log):
            with open(run_log, "r", encoding="utf-8",
                      errors="replace") as handle:
                out = handle.read()
        for line in out.splitlines()[-10:]:
            self.output.info("consumer: %s" % line)
        scenarios = re.findall(r"^SCENARIO (\S+) PASS\s*$", out,
                               flags=re.MULTILINE)
        discovered = len(scenarios)
        ok = ("PUPNP_CONSUMER_TEST PASS" in out and discovered == 3
              and len(set(scenarios)) == 3)
        self._hmbs_emit("HMBS_TEST_PACKAGE_RESULT=%s" % json.dumps(
            {"executed": True, "passed": bool(ok),
             "command": "./test_pupnp",
             "discovered": discovered,
             "passedCount": discovered if ok else 0},
            separators=(",", ":")))
        if not ok:
            raise RuntimeError(
                "pupnp consumer scenarios failed: %s" % scenarios)
        # Re-emit the real upstream result carried in the package res so
        # cache-hit runs still provide evidence every round.
        try:
            res = os.path.join(
                self.dependencies["pupnp"].package_folder,
                "res", "hmbs_upstream.json")
            with open(res, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if payload.get("status") == "passed" and \
                    int(payload.get("discovered", 0)) > 0 and \
                    int(payload.get("executed", 0)) > 0:
                self._hmbs_emit("HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(
                    payload, separators=(",", ":")))
            else:
                self.output.warning(
                    "HMBS diag upstream res invalid: %s" % payload)
        except Exception as exc:
            self.output.warning(
                "HMBS diag upstream res missing: %s" % exc)
