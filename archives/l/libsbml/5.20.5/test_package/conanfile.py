#!/usr/bin/env python3
"""Conan test_package for libsbml 5.20.5 — Conan L1 official test."""

import contextlib
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv


class LibsbmlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "test_libsbml.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # Match main recipe: CMake >= 4.0 needs POLICY_VERSION_MINIMUM
        # for upstream 'cmake_minimum_required(VERSION 3.1...3.19)'.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        if str(self.settings.os) == "OHOS":
            # Match main recipe: vanilla CMake has no Platform/HarmonyOS
            # module, so force Linux/aarch64 to pass compiler
            # identification. Single channel only (cache_variables),
            # like the merged oystr/0.2.0 recipe.
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Miss-only compiler fallback (mirrors main recipe): the profile
        # compiler path may be stale on the preflight host.
        try:
            _cc, _cxx, _over = self._resolve_compilers()
            if _over:
                if _cc and os.path.isfile(_cc):
                    tc.cache_variables["CMAKE_C_COMPILER"] = _cc
                if _cxx and os.path.isfile(_cxx):
                    tc.cache_variables["CMAKE_CXX_COMPILER"] = _cxx
                self.output.info(
                    "compiler fallback: profile-missing, using c={} cpp={}".format(_cc, _cxx))
        except Exception as _exc:
            self.output.warning("compiler fallback skipped (non-fatal): {}".format(_exc))
        tc.generate()
        VirtualRunEnv(self).generate()

    # -- OHOS SDK linker host runtime (E557; mirrors conanfile.py) --
    # A test_package is an independent consumer recipe: the scoped
    # Environment of the main recipe does NOT propagate here, so the
    # same discovery/probe/scoped-retry sequence runs before
    # cmake.configure(). Only a host dynamic-library failure is
    # recoverable via LD_LIBRARY_PATH; anything else fails closed
    # with the real probe output (never a skipped compiler check).

    _MISSING_LIB_PATTERNS = (
        re.compile(r"error loading shared library ([^\s:]+)", re.IGNORECASE),
        re.compile(
            r"error while loading shared libraries: ([^\s:]+)", re.IGNORECASE
        ),
        re.compile(r"([^\s:]+): cannot open shared object file", re.IGNORECASE),
    )
    _HOST_LOADER_MARKERS = (
        "error loading shared library",
        "error while loading shared libraries",
        "cannot open shared object file",
        "error relocating",
        "symbol not found",
    )

    def _get_cc(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c")
        if not cc:
            return shutil.which("clang") or "clang"
        if os.path.isfile(cc):
            return cc
        return shutil.which(os.path.basename(cc)) or cc

    def _resolve_compilers(self):
        # Mirror of the main recipe: profile path
        # (/data/service/hnp/bin/clang{,++}) may be stale on the
        # preflight host while PATH carries the migrated toolchain.
        # Only override on miss; never fabricate.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc_prof = compilers.get("c", "")
        cxx_prof = compilers.get("cpp", "")

        def _pick(prof, names):
            if prof and os.path.isfile(prof):
                return prof, False
            cands = []
            if prof:
                cands.append(os.path.basename(prof))
            cands += names
            for name in cands:
                found = shutil.which(name)
                if found and os.path.isfile(found):
                    return found, True
            return prof or names[0], False

        cc, cc_over = _pick(cc_prof, ["clang"])
        cxx, cxx_over = _pick(cxx_prof, ["clang++"])
        if cc and os.path.isfile(cc) and (not cxx or not os.path.isfile(cxx)):
            sibling = os.path.join(os.path.dirname(cc), "clang++")
            if os.path.isfile(sibling):
                cxx, cxx_over = sibling, True
        return cc, cxx, (cc_over or cxx_over)

    def _repair_stale_toolchain_compilers(self):
        # Build-time repair (mirrors main recipe): the generate() env
        # may not see the migrated compiler on PATH, so rewrite a
        # missing CMAKE_C/CXX_COMPILER in the generated toolchain file
        # just before cmake.configure(). Miss-only, PATH-derived.
        try:
            base = getattr(self, "build_folder", "") or "."
            tc_paths = []
            try:
                for root, _dirs, files in os.walk(base):
                    if "conan_toolchain.cmake" in files:
                        tc_paths.append(os.path.join(root, "conan_toolchain.cmake"))
            except OSError:
                pass
            if not tc_paths:
                return
            try:
                cc_new, cxx_new, _over = self._resolve_compilers()
            except Exception:
                return
            if not _over:
                return
            for tc_path in tc_paths:
                try:
                    with open(tc_path, "r", encoding="utf-8", errors="replace") as fh:
                        content = fh.read()
                except OSError:
                    continue
                orig = content
                for key, new_val in (("CMAKE_C_COMPILER", cc_new),
                                     ("CMAKE_CXX_COMPILER", cxx_new)):
                    if not new_val or not os.path.isfile(new_val):
                        continue
                    pattern = re.compile(r'set\(' + key + r'\s+"([^"]+)"')
                    match = pattern.search(content)
                    if not match:
                        continue
                    old_val = match.group(1)
                    if old_val and not os.path.isfile(old_val):
                        content = pattern.sub(
                            'set(' + key + ' "' + new_val + '"', content, count=1)
                        self.output.info(
                            "toolchain compiler repair: {} {} -> {}".format(
                                key, old_val, new_val))
                if content != orig:
                    try:
                        with open(tc_path, "w", encoding="utf-8") as fh:
                            fh.write(content)
                    except OSError as exc:
                        self.output.warning(
                            "toolchain compiler repair: cannot write {}: {}".format(
                                tc_path, exc))
        except Exception as exc:
            self.output.warning(
                "toolchain compiler repair skipped (non-fatal): {}".format(exc))

    def _resolve_lld(self, cc):
        candidates = []
        try:
            proc = subprocess.run(
                [cc, "-print-prog-name=ld.lld"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, timeout=60, check=False,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                candidates.append(proc.stdout.strip())
        except (OSError, subprocess.SubprocessError):
            pass
        bin_dir = os.path.dirname(os.path.realpath(cc))
        candidates += [os.path.join(bin_dir, "ld.lld"),
                       os.path.join(bin_dir, "lld")]
        for candidate in candidates:
            if os.path.isfile(candidate):
                return os.path.realpath(candidate)
            resolved = shutil.which(candidate)
            if resolved:
                return os.path.realpath(resolved)
        return ""

    def _missing_host_libs(self, log):
        libs = []
        for pattern in self._MISSING_LIB_PATTERNS:
            libs += pattern.findall(log or "")
        return [lib for lib in dict.fromkeys(libs) if ".so" in lib]

    def _is_host_loader_failure(self, log):
        lowered = (log or "").lower()
        return any(marker in lowered for marker in self._HOST_LOADER_MARKERS)

    def _host_runtime_libdirs(self, cc, lld, missing_libs):
        candidates = []
        for tool in (cc, lld):
            if tool and os.path.sep in tool:
                llvm_root = os.path.dirname(
                    os.path.dirname(os.path.realpath(tool))
                )
                candidates.append(os.path.join(llvm_root, "lib"))
        try:
            proc = subprocess.run(
                [cc, "-print-resource-dir"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                text=True, timeout=60, check=False,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                candidates.append(
                    os.path.dirname(os.path.dirname(proc.stdout.strip()))
                )
        except (OSError, subprocess.SubprocessError):
            pass
        candidates += [
            p for p in (os.environ.get("PATH") or "").split(os.pathsep) if p
        ]
        candidates += [
            p for p in (os.environ.get("LD_LIBRARY_PATH") or "").split(os.pathsep)
            if p
        ]
        for tool in (lld, cc):
            if not tool or os.path.sep not in tool:
                continue
            node = os.path.dirname(os.path.realpath(tool))
            for _ in range(4):
                node = os.path.dirname(node)
                if node in ("", os.path.sep):
                    break
                candidates.append(os.path.join(node, "lib"))
                candidates.append(os.path.join(node, "llvm", "lib"))
        found = []
        for candidate in dict.fromkeys(candidates):
            if not os.path.isdir(candidate):
                continue
            if missing_libs:
                if any(
                    os.path.isfile(os.path.join(candidate, lib))
                    for lib in missing_libs
                ):
                    found.append(candidate)
                continue
            try:
                entries = os.listdir(candidate)
            except OSError:
                continue
            if any(".so" in entry for entry in entries):
                found.append(candidate)
        return found

    def _cc_link_probe(self, cc, extra_ld_library_path=None):
        probe_dir = os.path.join(self.build_folder, "linker-probe")
        os.makedirs(probe_dir, exist_ok=True)
        source = os.path.join(probe_dir, "probe.c")
        binary = os.path.join(probe_dir, "probe")
        with open(source, "w") as fh:
            fh.write("int main(void) { return 0; }\n")
        env = os.environ.copy()
        if extra_ld_library_path:
            current = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                p for p in (extra_ld_library_path, current) if p
            )
        try:
            proc = subprocess.run(
                [cc, source, "-o", binary],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, env=env, timeout=180, check=False,
            )
        except (OSError, subprocess.SubprocessError) as error:
            return 127, str(error)
        finally:
            if os.path.exists(binary):
                try:
                    os.unlink(binary)
                except OSError:
                    pass
        return proc.returncode, (proc.stdout or "").strip()

    def _linker_runtime_environment(self):
        if str(self.settings.os) != "OHOS":
            return None
        cc = self._get_cc()
        lld = self._resolve_lld(cc)
        self.output.info("OHOS linker probe: clang={}".format(cc))
        self.output.info("OHOS linker probe: lld={}".format(lld or "(unresolved)"))
        rc, log = self._cc_link_probe(cc)
        if rc == 0:
            self.output.info(
                "OHOS linker probe: minimal C compile+link OK "
                "(ambient environment)"
            )
            return None
        missing_libs = self._missing_host_libs(log)
        if not self._is_host_loader_failure(log):
            raise ConanException(
                "OHOS linker probe: the configured C compiler "
                "'{}' cannot compile+link a minimal program in the "
                "test_package context and the failure is not a host "
                "dynamic-library issue (lld={}). "
                "Probe output:\n{}".format(cc, lld or "unresolved", log or "(empty)")
            )
        missing = ", ".join(missing_libs) or "unidentified library"
        self.output.warning(
            "OHOS linker probe: minimal C compile+link FAILED in the "
            "ambient environment (rc={}); locating the SDK host "
            "runtime ({}) ...".format(rc, missing)
        )
        if log:
            self.output.info("OHOS linker probe output:\n{}".format(log))
        candidates = self._host_runtime_libdirs(cc, lld, missing_libs)
        if not candidates:
            raise ConanException(
                "OHOS linker probe: the configured C compiler "
                "'{}' cannot compile+link a minimal program and no "
                "directory containing {} could be derived from "
                "the active toolchain (lld={}). "
                "Probe output:\n{}".format(
                    cc, missing, lld or "unresolved", log or "(empty)")
            )
        for libdir in candidates:
            rc, log = self._cc_link_probe(cc, extra_ld_library_path=libdir)
            if rc == 0:
                self.output.info(
                    "OHOS linker probe: minimal C compile+link OK with "
                    "{} prepended to LD_LIBRARY_PATH".format(libdir)
                )
                env = Environment()
                env.prepend_path("LD_LIBRARY_PATH", libdir)
                return env
        raise ConanException(
            "OHOS linker probe: the configured C compiler "
            "'{}' cannot compile+link a minimal program even with "
            "the discovered host runtime. Missing library: {}; "
            "lld={}; candidates tried: {}. "
            "Last probe output:\n{}".format(
                cc, missing, lld or "unresolved",
                ", ".join(candidates), log or "(empty)")
        )

    def build(self):
        self._repair_stale_toolchain_compilers()
        link_env = self._linker_runtime_environment()
        cmake = CMake(self)
        with (link_env.vars(self).apply() if link_env else contextlib.nullcontext()):
            cmake.configure()
            cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException("libsbml test consumer is not runnable on this configuration")
        executable = os.path.join(self.cpp.build.bindir, "test_libsbml")
        if str(self.settings.os) == "OHOS":
            # Prefer the HMBS-injected SHELL (/bin/sh) and CONFIG_SHELL when
            # present; the SDK bash path may be absent when the toolchain
            # mount is unhealthy (preflight 2026-09-20: /data/service/hnp/bin
            # missing). Pick the first existing shell, fall back to /bin/sh.
            candidates = [
                os.environ.get("CONFIG_SHELL", ""),
                os.environ.get("SHELL", ""),
                "/bin/sh",
                "/data/service/hnp/bin/bash",
            ]
            shell = ""
            for cand in candidates:
                if cand and os.path.isfile(cand):
                    shell = cand
                    break
            if not shell:
                shell = "/bin/sh"
            self.run("{} -c '\"{}\" '".format(shell, executable), env="conanrun")
        else:
            self.run("\"{}\"".format(executable), env="conanrun")
