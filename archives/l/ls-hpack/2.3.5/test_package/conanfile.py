#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# test_package for ls-hpack 2.3.5 — verifies the public C API of the
# final Conan package on HarmonyOS PC (aarch64, musl, clang15).
#
# Covered (per task requirements):
#   1. HPACK header encoding (literal + indexed, RFC 7541 Appendix C
#      vectors — the upstream official test vectors)
#   2. Decoding of those exact vectors, byte-for-byte comparison
#   3. Multiple headers (full header sets)
#   4. Round-trip: encode N headers -> decode -> name/value byte-exact
#   5. Known/static table behavior: decoding an indexed header field
#      (0x82 = ":method: GET" static-table row 2) must yield the exact
#      name/value, proving the static table is embedded correctly
#   6. Error/truncated input: decode must fail (rc < 0 or no progress)
#      instead of crashing or looping
#
# OHOS linker host runtime (E557): a Conan test_package is a SEPARATE
# consumer recipe — the scoped Environment the main recipe applies
# around its own build() does NOT propagate into this recipe's CMake
# configure/compiler check. This recipe therefore runs the SAME
# discovery/probe/scoped-retry sequence as the main conanfile.py
# before cmake.configure(): a REAL minimal compile+link probe in the
# ambient environment first; only when that fails with a host-loader
# error (e.g. lld cannot load its libxml2.so.16 host dependency) are
# toolchain-derived candidate dirs that actually contain the missing
# library retried with LD_LIBRARY_PATH prepended, and only the winning
# dir is applied — via a Conan Environment scoped to
# cmake.configure()/cmake.build() (never os.environ, never a skipped
# or forced CMake compiler check). If every candidate fails the real
# probe, the recipe fails closed with full diagnostics.

import contextlib
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class LsHpackTestPackage(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    # ── OHOS SDK linker host runtime (E557; mirrors conanfile.py) ────
    #
    # Same behavior as the main recipe (kept deliberately in sync —
    # Conan exports test_package as an independent recipe, so the
    # helpers cannot be imported from the parent conanfile.py):
    #   * compiler from tools.build:compiler_executables (authoritative
    #     OHOS profile conf; basename+PATH fallback only), never a
    #     hardcoded toolchain path;
    #   * linker derived from the toolchain itself
    #     (-print-prog-name=ld.lld, realpath-resolved);
    #   * candidate host-runtime dirs derived ONLY from the active
    #     toolchain and current environment;
    #   * a REAL compile+link probe decides, not a --version check;
    #   * the fix is a Conan Environment scoped to the build methods.

    # Loader signatures that name the missing host library.
    _MISSING_LIB_PATTERNS = (
        # musl: "Error loading shared library libxml2.so.16: (needed by ...)"
        re.compile(r"error loading shared library ([^\s:]+)", re.IGNORECASE),
        # glibc: "...: error while loading shared libraries: libxml2.so.16"
        re.compile(
            r"error while loading shared libraries: ([^\s:]+)", re.IGNORECASE
        ),
        # glibc: "libxml2.so.16: cannot open shared object file: ..."
        re.compile(r"([^\s:]+): cannot open shared object file", re.IGNORECASE),
    )
    # Host-loader failure markers (recoverable via LD_LIBRARY_PATH).
    _HOST_LOADER_MARKERS = (
        "error loading shared library",
        "error while loading shared libraries",
        "cannot open shared object file",
        "error relocating",
        "symbol not found",
    )

    def _get_cc(self):
        # Compiler comes from the Conan conf first (the authoritative
        # source the OHOS profile sets to the SDK clang); if that path
        # does not exist, fall back to basename + PATH resolution only.
        # Never a hardcoded toolchain path.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c")
        if not cc:
            return shutil.which("clang") or "clang"
        if os.path.isfile(cc):
            return cc
        return shutil.which(os.path.basename(cc)) or cc

    def _resolve_lld(self, cc):
        # The linker the clang driver actually invokes at the final link
        # step, derived from the toolchain itself: ask the driver
        # (-print-prog-name=ld.lld) first, then the compiler's real bin
        # dir, then PATH.
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
        # Missing host library name(s) extracted from the probe log
        # (e.g. libxml2.so.16) — what the candidate dirs must contain.
        libs = []
        for pattern in self._MISSING_LIB_PATTERNS:
            libs += pattern.findall(log or "")
        return [lib for lib in dict.fromkeys(libs) if ".so" in lib]

    def _is_host_loader_failure(self, log):
        lowered = (log or "").lower()
        return any(marker in lowered for marker in self._HOST_LOADER_MARKERS)

    def _host_runtime_libdirs(self, cc, lld, missing_libs):
        """Candidate host-runtime dirs derived ONLY from the active
        toolchain and the current environment, in the same priority
        order as the main recipe (no CI-worker paths):
          1. the configured compiler's real LLVM tree
          2. the resolved lld's real LLVM tree
          3. the compiler resource-dir tree (clang -print-resource-dir)
          4. tool-related dirs in the current PATH
          5. the current LD_LIBRARY_PATH
          6. a bounded upward walk from the toolchain binaries
        Returns only dirs that actually contain the missing library
        (or, when the log names no library, toolchain-derived dirs that
        hold shared libraries at all).
        """
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
                # <prefix>/lib/clang/<ver> → <prefix>/lib
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
        # Bounded upward walk from the toolchain binaries (covers SDK
        # layouts reached through symlinked wrapper dirs).
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
            # No library named in the log (e.g. a pure "symbol not
            # found" relocation failure): accept toolchain-derived dirs
            # that actually hold shared libraries.
            try:
                entries = os.listdir(candidate)
            except OSError:
                continue
            if any(".so" in entry for entry in entries):
                found.append(candidate)
        return found

    def _cc_link_probe(self, cc, extra_ld_library_path=None):
        """REAL compile+link probe: build `int main(void) { return 0; }`
        with the configured OHOS clang. A bare `clang --version` is not
        enough — CMake's compiler check compiles testCCompiler.c AND
        links it, and the link step is exactly where lld dies when its
        libxml2.so.16 host dependency cannot be loaded.
        Returns (returncode, combined_output).
        """
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
        """Linker host-runtime gate before cmake.configure() — the same
        sequence as the main recipe (a test_package is an independent
        consumer recipe; the main recipe's scoped Environment does not
        propagate here).

        1. REAL compile+link probe in the ambient environment.
        2. When that fails with a host-loader error, derive candidate
           host-runtime dirs from the active toolchain, keep those that
           actually contain the missing library, and retry the probe
           with each prepended to LD_LIBRARY_PATH.
        3. Return the winning dir as a Conan Environment to apply ONLY
           around cmake.configure()/cmake.build(); the ambient
           environment is never modified globally. Every other outcome
           fails closed with full diagnostics (compiler, linker,
           missing library, candidates, probe output).
        """
        if str(self.settings.os) != "OHOS":
            return None

        cc = self._get_cc()
        lld = self._resolve_lld(cc)
        self.output.info(f"OHOS linker probe: clang={cc}")
        self.output.info(f"OHOS linker probe: lld={lld or '(unresolved)'}")

        # 1) Ambient environment: can the configured clang compile+link?
        rc, log = self._cc_link_probe(cc)
        if rc == 0:
            self.output.info(
                "OHOS linker probe: minimal C compile+link OK "
                "(ambient environment)"
            )
            return None

        # 2) The link failed. Only a host dynamic-library failure is
        #    recoverable by prepending LD_LIBRARY_PATH; any other
        #    failure fails closed immediately.
        missing_libs = self._missing_host_libs(log)
        if not self._is_host_loader_failure(log):
            raise ConanException(
                "OHOS linker probe: the configured C compiler "
                f"'{cc}' cannot compile+link a minimal program in the "
                "test_package context and the failure is not a host "
                f"dynamic-library issue (lld={lld or 'unresolved'}). "
                f"Probe output:\n{log or '(empty)'}"
            )

        missing = ", ".join(missing_libs) or "unidentified library"
        self.output.warning(
            f"OHOS linker probe: minimal C compile+link FAILED in the "
            f"ambient environment (rc={rc}); locating the SDK host "
            f"runtime ({missing}) ..."
        )
        if log:
            self.output.info(f"OHOS linker probe output:\n{log}")
        candidates = self._host_runtime_libdirs(cc, lld, missing_libs)
        if not candidates:
            raise ConanException(
                "OHOS linker probe: the configured C compiler "
                f"'{cc}' cannot compile+link a minimal program and no "
                f"directory containing {missing} could be derived from "
                f"the active toolchain (lld={lld or 'unresolved'}). "
                f"Probe output:\n{log or '(empty)'}"
            )
        for libdir in candidates:
            rc, log = self._cc_link_probe(cc, extra_ld_library_path=libdir)
            if rc == 0:
                self.output.info(
                    "OHOS linker probe: minimal C compile+link OK with "
                    f"{libdir} prepended to LD_LIBRARY_PATH"
                )
                env = Environment()
                env.prepend_path("LD_LIBRARY_PATH", libdir)
                return env
        raise ConanException(
            "OHOS linker probe: the configured C compiler "
            f"'{cc}' cannot compile+link a minimal program even with "
            f"the discovered host runtime. Missing library: {missing}; "
            f"lld={lld or 'unresolved'}; candidates tried: "
            f"{', '.join(candidates)}. "
            f"Last probe output:\n{log or '(empty)'}"
        )

    def build(self):
        # Linker host-runtime gate (E557), identical in behavior to the
        # main recipe: verify the configured OHOS clang can compile+link
        # a minimal C program BEFORE configure; when the ambient env is
        # broken (lld cannot load its host dependency), discover the SDK
        # host runtime and scope it via LD_LIBRARY_PATH to configure and
        # build only. No CMake compiler-check bypass — the real CMake
        # probe must pass on its own or the build stops with full
        # diagnostics.
        link_env = self._linker_runtime_environment()
        cmake = CMake(self)
        with (link_env.vars(self).apply() if link_env else contextlib.nullcontext()):
            cmake.configure()
            cmake.build()

    def test(self):
        # Actual execution on the OHOS target (HarmonyOS PC aarch64).
        # cmake.test() runs ctest, which invokes the test binary; for
        # the L0d gate (and explicitness) the direct run is preferred.
        self.run(f"ctest --test-dir {self.build_folder} --output-on-failure", env="conanrun")
