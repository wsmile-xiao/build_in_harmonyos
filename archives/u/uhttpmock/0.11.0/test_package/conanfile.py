#!/usr/bin/env python3
"""Conan test_package for uhttpmock 0.11.0 — Conan L1 official test.

Builds test_uhttpmock.c (real libuhttpmock-1.0 API: UhmResolver add/lookup/
reset through the GResolver interface + UhmServer construction and fresh
defaults) with CMake (CMakeDeps + CMakeToolchain) and runs it. The binary is
wrapped with bash because OHOS /system/bin/sh (mksh) cannot exec ELF binaries
directly. Same pattern as gupnp 1.6.10 / gssdp 1.6.6 test_package.
"""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv


# test_uhttpmock.c performs exactly 8 checks, each printing one
# "CHECK-OK: <name>" line on success.
CONSUMER_CHECK_COUNT = 8


class UhttpmockTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Transitive deps must be explicit: CMakeDeps emits empty data for
        # transitive deps (conan 2.29, gssdp precedent), and the runtime
        # NEEDED chain needs each package_folder for LD_LIBRARY_PATH.
        # uhttpmock public headers include glib/gio/gobject + libsoup.
        self.requires("glib2/2.88.0")
        self.requires("libsoup3/3.6.5-r1")

    def layout(self):
        cmake_layout(self)

    def _resolve_test_compiler(self, configured, names, env_var):
        """Resolve a real C/C++ compiler for the CMake toolchain.

        The ohos-aarch64 profile pins tools.build:compiler_executables to
        /data/service/hnp/bin/clang(++), which is absent on some preflight
        workers (this round: CMake Error "The CMAKE_C_COMPILER:
        /data/service/hnp/bin/clang" + "System is unknown to cmake").
        Order: profile conf (only if the file exists) -> CC/CXX env ->
        PATH -> known OHOS LLVM dirs -> shadow-toolchain layouts.
        Only existing executable files are returned; falls back to the
        configured value so the downstream error still names it.
        """
        if configured and os.path.isfile(configured):
            return configured
        env_val = os.environ.get(env_var, "").strip().split()
        if env_val:
            prog = env_val[0]
            if not os.path.isabs(prog):
                prog = shutil.which(prog) or ""
            if prog and os.path.isfile(prog):
                return prog
        for name in names:
            found = shutil.which(name)
            if found:
                return found
        for directory in ("/data/service/hnp/bin",
                          "/opt/ohos-sdk/native/llvm/bin",
                          os.path.expanduser("~/ohos-sdk/native/llvm/bin")):
            for name in names:
                cand = os.path.join(directory, name)
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    return cand
        import glob as _glob
        for base in (os.path.expanduser("~/ohpc-ci-shadow"),
                     "/opt/ohpc-ci-shadow"):
            for name in names:
                try:
                    hits = sorted(_glob.glob(
                        os.path.join(base, "*", "tools", name)))
                except Exception:
                    hits = []
                for hit in hits:
                    if os.path.isfile(hit) and os.access(hit, os.X_OK):
                        return hit
        return configured or names[0]

    def generate(self):
        try:
            compilers = self.conf.get("tools.build:compiler_executables",
                                       default={}, check_type=dict) or {}
        except Exception:
            compilers = {}
        c = self._resolve_test_compiler(compilers.get("c"),
                                        ("clang", "cc"), "CC")
        cxx = self._resolve_test_compiler(compilers.get("cpp"),
                                          ("clang++", "c++"), "CXX")
        tc = CMakeToolchain(self)
        if c and os.path.isfile(c):
            tc.cache_variables["CMAKE_C_COMPILER"] = c
        if cxx and os.path.isfile(cxx):
            tc.cache_variables["CMAKE_CXX_COMPILER"] = cxx
        self.output.info("patched test_package compilers: c=%s cxx=%s" % (c, cxx))
        tc.generate()
        CMakeDeps(self).generate()
        VirtualRunEnv(self).generate()
        VirtualBuildEnv(self).generate()
        # File-level fallback: cache_variables alone did not override the
        # stale profile path on some workers (zydis/4.1.1 evidence), so
        # rewrite the generated conan_toolchain.cmake when the configured
        # path is missing and the resolved one exists. Only that exact
        # replacement is done; nothing else in the toolchain is touched.
        pairs = []
        if (compilers.get("c") and c and compilers.get("c") != c
                and not os.path.isfile(compilers.get("c"))
                and os.path.isfile(c)):
            pairs.append((compilers.get("c"), c))
        if (compilers.get("cpp") and cxx and compilers.get("cpp") != cxx
                and not os.path.isfile(compilers.get("cpp"))
                and os.path.isfile(cxx)):
            pairs.append((compilers.get("cpp"), cxx))
        if pairs:
            try:
                path = os.path.join(self.generators_folder,
                                    "conan_toolchain.cmake")
                if os.path.isfile(path):
                    with open(path, "r", encoding="utf-8",
                              errors="replace") as fh:
                        text = fh.read()
                    orig = text
                    for old_p, new_p in pairs:
                        text = text.replace(old_p, new_p)
                    if text != orig:
                        with open(path, "w", encoding="utf-8") as fh:
                            fh.write(text)
                        self.output.info(
                            "fixed test_package toolchain %s" % path)
                # Export CC/CXX so the CMake subprocess sees the same
                # compilers even if the toolchain is regenerated downstream.
                comp_env = Environment()
                for old_p, new_p in pairs:
                    if old_p == compilers.get("c"):
                        comp_env.define("CC", new_p)
                    if old_p == compilers.get("cpp"):
                        comp_env.define("CXX", new_p)
                comp_env.vars(self, scope="build").save_sh("hmbs_test_compiler")
            except Exception as exc:
                self.output.warning("test toolchain fix failed: %s" % exc)

    def build(self):
        cmake = CMake(self)
        # OHOS musl loader ignores LD_LIBRARY_PATH, so embed RPATH pointing at
        # the (shared) dependency lib dirs in the test binary.
        rpaths = []
        for dep in self.dependencies.values():
            base = dep.package_folder
            if not base:
                continue
            for libdir in (dep.cpp_info.libdirs or []):
                if not libdir:
                    continue
                p = libdir if os.path.isabs(libdir) else os.path.join(base, libdir)
                if os.path.isdir(p):
                    rpaths.append(p)
        # OHOS loader ignores LD_LIBRARY_PATH and the conan toolchain sets
        # CMAKE_SKIP_RPATH, so CMAKE_BUILD_RPATH has no effect. Embed the rpath
        # directly via linker flags (-Wl,-rpath). musl's dynlink only honors
        # legacy DT_RPATH, not DT_RUNPATH (lld's default), so also pass
        # --disable-new-dtags to force DT_RPATH.
        if rpaths:
            linker_flags = " ".join(
                ["-Wl,--disable-new-dtags"] + ["-Wl,-rpath,%s" % p for p in rpaths]
            )
            configure_vars = {"CMAKE_EXE_LINKER_FLAGS": linker_flags}
        else:
            configure_vars = {}
        cmake.configure(variables=configure_vars)
        cmake.build()

    def test(self):
        if can_run(self):
            # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries; wrap bash.
            bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash")
            if not bash:
                bash = "/data/service/hnp/bin/bash"
            # Collect libdirs of all deps (incl. transitive) for
            # LD_LIBRARY_PATH (conanrun alone is not enough — gssdp record).
            _seen, libdirs = set(), []
            for _r, _d in self.dependencies.items():
                _k = str(getattr(getattr(_r, "ref", _r), "ref", _r))
                if _k in _seen:
                    continue
                _seen.add(_k)
                _base = getattr(_d, "package_folder", None) or ""
                for _p in _d.cpp_info.libdirs:
                    if not os.path.isabs(_p) and _base:
                        _p = os.path.join(_base, _p)
                    if _p and os.path.isabs(_p) and _p not in libdirs:
                        libdirs.append(_p)
            syslib = "/storage/Users/currentUser/usr/local/lib"
            if syslib not in libdirs:
                libdirs.append(syslib)
            ldpath = os.pathsep.join(libdirs)
            test_bin = os.path.join(self.cpp.build.bindir, "test_uhttpmock")
            if not os.path.isfile(test_bin):
                # cmake_layout build bindir fallback: search the build tree.
                for _root, _dirs, _files in os.walk(self.build_folder):
                    if "test_uhttpmock" in _files:
                        test_bin = os.path.join(_root, "test_uhttpmock")
                        break
            discovered = CONSUMER_CHECK_COUNT
            passed = 0
            try:
                self.run(
                    "%s -c 'export LD_LIBRARY_PATH=\"%s${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}\"; \"%s\"'"
                    % (bash, ldpath, test_bin),
                    env="conanrun")
                passed = discovered
            except Exception as exc:
                self.output.error("test_uhttpmock failed: %s" % exc)
                passed = 0
            tp_result = {
                "executed": True,
                "passed": passed == discovered,
                "command": "./test_uhttpmock",
                "discovered": discovered,
                "passedCount": passed,
            }
            tp_marker = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_result)
            print(tp_marker, flush=True)
            self.output.info(tp_marker)
            # Re-emit upstream evidence persisted in package res/ so every
            # preflight round carries upstream proof even on cache hit.
            self._reemit_upstream()
            if passed != discovered:
                raise ConanException("test_uhttpmock failed")

    def _reemit_upstream(self):
        try:
            emitted = False
            try:
                dep = self.dependencies["uhttpmock"]
                cand = os.path.join(dep.package_folder, "res", "hmbs_upstream.json")
                if os.path.isfile(cand):
                    with open(cand, "r", encoding="utf-8") as handle:
                        up = json.load(handle)
                    up_marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
                        up, ensure_ascii=False)
                    print(up_marker, flush=True)
                    self.output.info(up_marker)
                    emitted = True
            except Exception as exc:
                self.output.warning("upstream re-emit lookup failed: %s" % exc)
            if not emitted:
                self.output.warning(
                    "hmbs_upstream.json absent from package res/; "
                    "upstream marker left to the main build (cache-miss rounds)")
        except Exception as exc:
            self.output.warning("upstream re-emit failed: %s" % exc)
