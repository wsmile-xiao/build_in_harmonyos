#!/usr/bin/env python3
"""Conan recipe — madplay 0.15.2b — MPEG audio decoder and player.

madplay is the reference command-line player built on libmad, with ID3 tag
support via libid3tag. Source: https://sourceforge.net/projects/mad/
"""
import contextlib
import glob
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class MadplayConan(ConanFile):
    name = "madplay"
    version = "0.15.2b"
    description = "MAD (MPEG Audio Decoder) player and tag tools"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/mad/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("madplay is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        # configure.ac: mad.h + AC_CHECK_LIB(mad) are unconditional hard deps
        self.requires("mad/0.16.4")
        # configure.ac: id3tag.h + AC_CHECK_LIB(id3tag, ..., [-lz]) hard dep
        self.requires("libid3tag/0.16.3")
        # configure.ac links id3tag against zlib (-lz)
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Pass the cross triplet explicitly: `uname -s` reports "HarmonyOS",
        # which the 2001-era config.guess/config.sub do not know. With the
        # patch in place config.sub accepts aarch64-unknown-linux-ohos.
        # No --with-<audio> switches: configure probes OSS via <soundcard.h>
        # (present in the OHOS sysroot — on-device this selects audio=oss);
        # regardless of the probed default, every file output module
        # (wave/raw/snd/aiff/cdda/hex/null) compiles unconditionally, so no
        # audio device is ever needed for decode-to-file operation.
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-ohos",
        ])
        tc.generate()
        # AutotoolsDeps supplies CPPFLAGS/LDFLAGS/LIBS (-lmad -lid3tag -lz)
        AutotoolsDeps(self).generate()

    # ── OHOS SDK linker host runtime (E429; mirrors ls-hpack 2.3.5) ──
    #
    # Online CI root cause (same as ls-hpack E429): the OHOS clang driver
    # spawns `lld` for the final link step. lld is a dynamically linked
    # HOST ELF whose NEEDED list includes host libraries such as
    # libxml2.so.16 (normally resolved via its RUNPATH $ORIGIN/../lib →
    # the SDK llvm/lib, which the CI host musl loader does not expand),
    # so on CI workers lld fails to even start:
    #     Error loading shared library libxml2.so.16:
    #     needed by .../llvm/bin/lld
    #     configure: error: C compiler cannot create executables
    # This is a host-runtime problem of the SDK linker itself, not a
    # madplay source error. Fix (verified ls-hpack 2.3.5 pattern): before
    # autotools.configure() run a REAL compile+link probe with the
    # configured clang; only when the ambient environment fails, derive
    # candidate host-runtime dirs from the active toolchain
    # (realpath / -print-prog-name / -print-resource-dir), keep only dirs
    # that actually contain the missing library, re-verify with the SAME
    # probe, and scope the build under an LD_LIBRARY_PATH prepend. No
    # configure-check bypass (no cache vars, no skipped compiler test) and
    # no global environment mutation.

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
        toolchain and the current environment, in priority order (no
        CI-worker paths):
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
        enough — configure's "checking for C compiler default output file
        name" compiles conftest.c AND links it, and the link step is
        exactly where lld dies when its host dependency (libxml2.so.16)
        cannot be loaded.
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
        """Linker host-runtime gate, executed BEFORE autotools.configure().

        1. REAL compile+link probe in the ambient environment.
        2. When that fails with a host-loader error, derive candidate
           host-runtime dirs from the active toolchain, keep those that
           actually contain the missing library, and retry the probe
           with each prepended to LD_LIBRARY_PATH (same probe).
        3. Return the winning dir as a Conan Environment to apply ONLY
           around configure/make; the ambient environment is never
           modified globally. Every other outcome fails closed with full
           diagnostics (compiler, linker, missing library, candidates,
           probe stderr) — configure is never allowed to be skipped.
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
                f"'{cc}' cannot compile+link a minimal program and the "
                "failure is not a host dynamic-library issue "
                f"(lld={lld or 'unresolved'}). "
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
                # Remember it for package(): `make install` may relink
                # via the same broken lld within the same conan create.
                self._ohos_host_runtime_libdir = libdir
                return env
        raise ConanException(
            "OHOS linker probe: the configured C compiler "
            f"'{cc}' cannot compile+link a minimal program even with "
            f"the discovered host runtime. Missing library: {missing}; "
            f"lld={lld or 'unresolved'}; candidates tried: "
            f"{', '.join(candidates)}. "
            f"Last probe output:\n{log or '(empty)'}"
        )

    def _dump_config_log_tail(self, max_lines=80):
        """On configure failure, surface the tail of config.log — the
        real link error behind configure's generic "C compiler cannot
        create executables" summary."""
        for folder in (self.build_folder, self.source_folder):
            path = os.path.join(folder, "config.log")
            if not os.path.isfile(path):
                continue
            try:
                with open(path, errors="replace") as fh:
                    lines = fh.readlines()
            except OSError:
                continue
            tail = "".join(lines[-max_lines:]).rstrip()
            self.output.error(f"configure failed — tail of {path}:\n{tail}")
            return
        self.output.error(
            "configure failed and no config.log was found in "
            f"{self.build_folder} or {self.source_folder}"
        )

    def build(self):
        apply_conandata_patches(self)
        # Linker host-runtime gate (E429): verify the configured OHOS
        # clang can compile+link a minimal C program BEFORE configure; if
        # the ambient env is broken (lld cannot load its host dependency),
        # dynamically discover the SDK host runtime and scope it to the
        # build via LD_LIBRARY_PATH. No configure compiler-check bypass —
        # the real configure probe must pass on its own or the build
        # stops with full diagnostics.
        link_env = self._linker_runtime_environment()
        autotools = Autotools(self)
        with (link_env.vars(self).apply() if link_env else contextlib.nullcontext()):
            try:
                autotools.configure()
            except ConanException:
                # configure's own summary hides the real link error —
                # print the config.log tail before re-raising.
                self._dump_config_log_tail()
                raise
            # -j1: 2004-era libtool does not cope with parallel make on this toolchain
            autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        # `make install` can relink through the same broken host lld
        # (libtool relink on install), so reuse the discovered host
        # runtime dir when the build needed one. Scoped to install()
        # only — the ambient environment is never modified.
        libdir = getattr(self, "_ohos_host_runtime_libdir", None)
        with (Environment().prepend_path("LD_LIBRARY_PATH", libdir).vars(self).apply()
              if libdir else contextlib.nullcontext()):
            autotools.install()
        # bin_SCRIPTS abxtest (shell helper for ABX listening tests) is kept;
        # libtool *.la wrappers are not meaningful in a Conan package.
        for _la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
