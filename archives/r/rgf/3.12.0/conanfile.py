#!/usr/bin/env python3
"""Conan recipe — rgf 3.12.0 (CMake, application).

Regularized Greedy Forest: tree-ensemble machine-learning CLI from
RGF-team/rgf. This recipe builds the original RGF implementation only
(the RGF/ subdirectory, same scope as the Homebrew formula): a single
C++ executable `rgf` with zero third-party dependencies (C++ stdlib
only). FastRGF (the optional OpenMP multicore variant) and the
python-package/R wrappers are out of scope for this base adaptation.

Upstream layout: the tag tarball root contains RGF/, FastRGF/,
python-package/, R-package/. The RGF core has its own CMakeLists at
RGF/CMakeLists.txt (`add_executable(rgf ...)` + `install(TARGETS rgf
DESTINATION bin)`), no enable_testing/ctest registration and no
make-check target, so build() does not call cmake.test(); the no-test
audit lives in test_package/MANIFEST.yml (R51).

OHOS notes:
  - R32: validate() uses `in ("Linux", "OHOS")`.
  - R33: no bare ${CC}/${CFLAGS} anywhere; the compiler comes from the
    CMakeToolchain generated from the ohos-aarch64 profile.
  - generate() only sets CMAKE_POLICY_VERSION_MINIMUM=3.5
    (RGF/CMakeLists.txt declares no cmake_minimum_required at all;
    E103/E187; toolchain entry plus configure-time -D like oatpp/1.3.1)
    and aliases CMAKE_SYSTEM_NAME=Linux + CMAKE_SYSTEM_PROCESSOR=aarch64
    (E092: cmake 4.4.3 ships no Platform/HarmonyOS.cmake; precedent
    lzo/2.10, zxc/0.9.1; upstream has no Linux-only branches).
  - build() runs an OHOS linker host-runtime gate ported from
    ls-hpack/2.3.5 (E557): a real compile+link probe; when lld cannot
    start (missing libxml2.so.16 host dep) the SDK runtime dir derived
    from the active toolchain is scoped via LD_LIBRARY_PATH. No CMake
    compiler-check bypass.
  - One portability patch removes the hardcoded
    set(CMAKE_INSTALL_PREFIX <source>) so cmake.install() lands in the
    package folder (Homebrew works around the same line by hand-copying
    bin/rgf instead of running cmake --install).
  - HMBS injects tools.build:jobs=1, so the single-job rule holds
    without extra flags.
"""

import contextlib
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class RgfConan(ConanFile):
    name = "rgf"
    version = "3.12.0"
    description = (
        "Regularized Greedy Forest: decision-forest machine learning "
        "command line tool (train / predict / train_predict)"
    )
    license = "MIT"
    homepage = "https://github.com/RGF-team/rgf"
    url = "https://github.com/RGF-team/rgf"
    topics = ("machine-learning", "decision-forest", "cli")
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Zero third-party dependencies: RGF core links the C++ stdlib only.
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "rgf/3.12.0 is validated for Linux and OHOS, not {0}".format(
                    self.settings.os
                )
            )
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "rgf/3.12.0 OHOS support is validated for armv8/AArch64 only"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # RGF/CMakeLists.txt declares no cmake_minimum_required at all;
        # CMake 4.x removed compatibility with < 3.5 (E103/E187), so
        # configure would stop at `project(rgf)`. Belt and suspenders
        # like oatpp/1.3.1: toolchain entry plus configure-time -D (the
        # toolchain value alone is read too late for the version check).
        # E092 (cmake 4.4.3 has no Platform/HarmonyOS.cmake): alias the
        # target to Linux + aarch64 (precedent: lzo/2.10, zxc/0.9.1,
        # ayatana-ido/0.10.4-v2). Upstream RGF/CMakeLists.txt has no
        # Linux-only branches (only MINGW/MSVC special cases, verified
        # against tag 3.12.0), so the alias is behavior-preserving; the
        # Linux platform module supplies the flags the HarmonyOS name
        # lacks. Round 1 (Linux alias alone) still failed on the E557
        # lld host-runtime fault; round 2 (lld gate alone) still failed
        # on the unknown-platform compiler sanity check. Both are needed.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Compiler-usability guard (naga/ayatana-ido precedent, NEW this
        # round): the ohos-aarch64 profile pins an absolute SDK path
        # (/data/service/hnp/bin/clang{,++}). When that file is absent or
        # not executable on the worker, CMakeToolchain still embeds the
        # dangling path and project() fails with "compiler identification
        # is unknown" for BOTH C and CXX — while the recipe's own bare
        # probe (which falls back to PATH) can still succeed, hiding the
        # divergence. Mirror the probe fallback inside the toolchain:
        # only override when the conf path is unusable; otherwise leave
        # the profile default untouched.
        try:
            _exes = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
        except Exception:
            _exes = {}
        _conf_c = (_exes or {}).get("c")
        _conf_cxx = (_exes or {}).get("cpp") or (_exes or {}).get("cxx")
        for _key, _conf_val, _bare in (
            ("CMAKE_C_COMPILER", _conf_c, "clang"),
            ("CMAKE_CXX_COMPILER", _conf_cxx, "clang++"),
        ):
            _usable = False
            try:
                _usable = bool(
                    _conf_val
                    and os.path.isfile(str(_conf_val))
                    and os.access(str(_conf_val), os.X_OK)
                )
            except Exception:
                _usable = False
            if not _conf_val or not _usable:
                _which = shutil.which(_bare)
                if _which:
                    self.output.warning(
                        "conf compiler '{0}' unusable; "
                        "overriding {1} with PATH-resolved '{2}'".format(
                            _conf_val, _key, _which
                        )
                    )
                    tc.variables[_key] = _which
                elif _conf_val:
                    self.output.warning(
                        "conf compiler '{0}' unusable and no '{1}' on "
                        "PATH; leaving {2} for CMake diagnostics".format(
                            _conf_val, _bare, _key
                        )
                    )
        tc.generate()

    # ── OHOS SDK linker host runtime (lld / libxml2.so.16) ───────────
    #
    # Preflight root cause (round 2): with or without the Linux system-name
    # mapping, CMake stops at `project()` with
    #   -- The C compiler identification is unknown
    #   The CMAKE_C_COMPILER: /data/service/hnp/bin/clang ...
    # i.e. the driver cannot even compile+link CMake's probe program.
    # This is the repo-proven ls-hpack/2.3.5 (CI PR #7487, E557) host-runtime
    # failure, not an rgf source error: the OHOS clang driver spawns `lld`
    # for the final link step; lld is a dynamically linked HOST ELF whose
    # NEEDED list includes libxml2.so.16 (normally resolved via its RUNPATH
    # $ORIGIN/../lib -> SDK llvm/lib, which the worker host loader does not
    # expand), so lld fails to start and CMake reports the compiler probe as
    # broken. Fix ported from archives/l/ls-hpack/2.3.5/conanfile.py: run a
    # REAL compile+link probe before cmake.configure(); when the ambient
    # environment fails, dynamically locate the libxml2.so.16 host-runtime
    # dir derived from the active toolchain and scope the build under an
    # LD_LIBRARY_PATH prepend. No CMake bypass (no CMAKE_C_COMPILER_WORKS /
    # skipped compiler check) — the real CMake probe must succeed on its own.

    def _get_cc(self):
        # Compiler comes from the Conan conf first (the authoritative
        # source the OHOS profile sets to the SDK clang); the entry must
        # be an existing EXECUTABLE file, otherwise fall back to basename
        # + PATH resolution only. Never a hardcoded toolchain path.
        # NOTE: this must mirror the generate() usability guard (isfile +
        # X_OK); a present-but-non-executable file is unusable and must
        # not be returned, or the probe and CMake diverge on compilers.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = (compilers or {}).get("c")
        if not cc:
            return shutil.which("clang") or "clang"
        try:
            if os.path.isfile(cc) and os.access(cc, os.X_OK):
                return cc
        except Exception:
            pass
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

    def _libxml2_host_libdirs(self, cc, lld):
        """Candidate host-runtime dirs holding the libxml2.so.16 lld needs.

        Derived ONLY from the active toolchain and the current environment,
        in priority order (no worker-specific paths):
          1. the configured compiler's real LLVM tree
          2. the resolved lld's real LLVM tree
          3. the compiler resource-dir tree (clang -print-resource-dir)
          4. tool-related dirs in the current PATH
          5. the current LD_LIBRARY_PATH
          6. a bounded upward walk from the toolchain binaries
        Returns only dirs that actually contain libxml2.so.16.
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
                # <prefix>/lib/clang/<ver> -> <prefix>/lib
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
            if os.path.isfile(os.path.join(candidate, "libxml2.so.16")):
                found.append(candidate)
        return found

    def _cc_link_probe(self, cc, extra_ld_library_path=None):
        """REAL compile+link probe: build `int main(void) { return 0; }`
        with the configured OHOS clang. A bare `clang --version` is not
        enough — CMake's compiler check compiles AND links its probe, and
        the link step is exactly where lld dies when its libxml2.so.16
        host dependency cannot be loaded.
        Returns (returncode, combined_output).
        """
        probe_dir = os.path.join(self.build_folder, "linker-probe")
        os.makedirs(probe_dir, exist_ok=True)
        source = os.path.join(probe_dir, "probe.c")
        binary = os.path.join(probe_dir, "probe")
        with open(source, "w", encoding="utf-8") as fh:
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
        """Linker host-runtime gate (ported from ls-hpack/2.3.5, CI PR #7487).

        Verifies the configured OHOS clang can compile+link a minimal C
        program BEFORE cmake.configure(). When the ambient environment
        fails (lld cannot load its libxml2.so.16 host dependency),
        dynamically discovers a usable host-runtime dir and returns a
        build-scoped Environment prepending it to LD_LIBRARY_PATH; the
        user environment is never modified globally. Raises
        ConanException with full diagnostics when the linker cannot be
        made to work — the error is never hidden and CMake is never
        bypassed.
        """
        if str(self.settings.os) != "OHOS":
            return None

        cc = self._get_cc()
        lld = self._resolve_lld(cc)
        self.output.info("OHOS linker probe: clang={0}".format(cc))
        self.output.info("OHOS linker probe: lld={0}".format(lld or "(unresolved)"))

        # 1) Ambient environment: can the configured clang compile+link?
        rc, log = self._cc_link_probe(cc)
        if rc == 0:
            self.output.info(
                "OHOS linker probe: minimal C compile+link OK "
                "(ambient environment)"
            )
            return None

        # 2) Link failed — find a libxml2.so.16 host-runtime dir derived
        #    from the active toolchain and retry the probe with it
        #    prepended to LD_LIBRARY_PATH.
        self.output.warning(
            "OHOS linker probe: minimal C compile+link FAILED in the "
            "ambient environment (rc={0}); locating the SDK host "
            "runtime (libxml2.so.16) ...".format(rc)
        )
        if log:
            self.output.info("OHOS linker probe output:\n{0}".format(log))
        candidates = self._libxml2_host_libdirs(cc, lld)
        if not candidates:
            raise ConanException(
                "OHOS linker probe: the configured C compiler "
                "'{0}' cannot compile+link a minimal program and no "
                "directory containing libxml2.so.16 could be derived "
                "from the active toolchain (lld={1}). "
                "Probe output:\n{2}".format(cc, lld or "unresolved", log or "(empty)")
            )
        for libdir in candidates:
            rc, log = self._cc_link_probe(cc, extra_ld_library_path=libdir)
            if rc == 0:
                self.output.info(
                    "OHOS linker probe: minimal C compile+link OK with "
                    "{0} prepended to LD_LIBRARY_PATH".format(libdir)
                )
                env = Environment()
                env.prepend_path("LD_LIBRARY_PATH", libdir)
                return env
        raise ConanException(
            "OHOS linker probe: the configured C compiler "
            "'{0}' cannot compile+link a minimal program even with "
            "the discovered libxml2.so.16 host runtime. Candidates "
            "tried: {1}; lld={2}. "
            "Last probe output:\n{3}".format(
                cc, ", ".join(candidates), lld or "unresolved", log or "(empty)")
        )

    def _dump_cmake_diagnostics(self, max_lines=60):
        # Surface the hidden compiler error text: HMBS preflight summaries
        # truncate the lines after "The CMAKE_C_COMPILER: ..." which hold
        # the real cause. On configure failure, print the tails of
        # CMakeError.log / CMakeOutput.log so the next round diagnoses
        # from evidence instead of guessing.
        candidates = []
        for root, _dirs, files in os.walk(self.build_folder):
            for name in files:
                if name in ("CMakeError.log", "CMakeOutput.log"):
                    candidates.append(os.path.join(root, name))
        for path in sorted(set(candidates)):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    lines = fh.read().splitlines()
            except OSError:
                continue
            tail = lines[-max_lines:] if len(lines) > max_lines else lines
            self.output.info(
                "CMAKE_DIAG {0} ({1} lines, last {2}):\n{3}".format(
                    path, len(lines), len(tail), "\n".join(tail)
                )
            )
        if not candidates:
            self.output.info(
                "CMAKE_DIAG no CMakeError.log/CMakeOutput.log found under "
                "{0}".format(self.build_folder)
            )

    def build(self):
        apply_conandata_patches(self)
        # Linker host-runtime gate (ls-hpack pattern): verify the OHOS
        # clang can compile+link BEFORE configure; scope a discovered SDK
        # host runtime via LD_LIBRARY_PATH when the ambient env is broken.
        link_env = self._linker_runtime_environment()
        cmake = CMake(self)
        with (link_env.vars(self).apply() if link_env else contextlib.nullcontext()):
            try:
                cmake.configure(
                    build_script_folder=os.path.join(self.source_folder, "RGF"),
                    variables={
                        "CMAKE_POLICY_VERSION_MINIMUM": "3.5",
                        "CMAKE_SYSTEM_NAME": "Linux",
                        "CMAKE_SYSTEM_PROCESSOR": "aarch64",
                    },
                )
            except Exception:
                self._dump_cmake_diagnostics()
                raise
            cmake.build()
        # No cmake.test(): upstream RGF core registers zero ctest cases
        # (no enable_testing/add_test in RGF/CMakeLists.txt). Running an
        # empty `ctest` as "evidence" would fake coverage, so the
        # no-tests audit in test_package/MANIFEST.yml stands instead.

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "COPYING",
            src=os.path.join(self.source_folder, "RGF"),
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "RGF", "examples", "sample"),
            dst=os.path.join(self.package_folder, "share", "rgf", "examples", "sample"),
            keep_path=True,
        )

    def package_info(self):
        # Command line tool, no libraries or headers.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
