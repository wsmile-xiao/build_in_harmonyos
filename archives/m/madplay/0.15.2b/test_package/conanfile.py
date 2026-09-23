#!/usr/bin/env python3
"""test_package for madplay 0.15.2b — CLI smoke + real decode on-device.

Runs the real madplay binary and checks:
  1. --version prints the three banner lines (mad, libid3tag, madplay)
  2. --help prints usage
  3. -T (tags-only) parse of a generated silent MPEG-1 Layer III fixture
  4. -o wave:FILE real decode → 44-byte header + 25*1152 16-bit mono PCM,
     sample values stay within libmad's dither noise (|x| <= 2)
  5. -o hex:FILE real decode → header line + 25*1152 hex samples, |x| <= 2
  6. negative: nonexistent file exits non-zero (exit 4 on open failure)
  7. negative: garbage input decodes 0 frames → 44-byte header-only wave

The fixture is generated arithmetically by gen_fixture.c (MPEG-1 Layer III
128 kbps mono 44100 Hz frames, all-zero side info and payload) — no binary
blob from unknown provenance. No audio device is involved: -T parses tags
only, wave/hex write to files.
"""
import contextlib
import os
import re
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.layout import basic_layout

from test_madplay import FRAME_LEN, check_hex_dump, check_wave

FRAMES = 25


class MadplayTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv", "CMakeToolchain", "CMakeDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    # ── OHOS SDK linker host runtime (E429; mirrors conanfile.py) ────
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
    # The gen_fixture target is compiled AND linked by this test's
    # CMakeToolchain through the same SDK clang → lld path, so it hits
    # the identical host-loader failure as the main recipe's configure.

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
        # Linker host-runtime gate (E429), identical in behavior to the
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
        # gen_fixture comes from this test's CMake build; madplay comes from
        # the tested package, located via the dependencies API.
        gen_fixture = os.path.join(self.build_folder, "bin", "gen_fixture")
        assert os.path.isfile(gen_fixture), f"gen_fixture missing at {gen_fixture}"
        dep = self.dependencies.get(self.tested_reference_str)
        madplay = os.path.join(dep.package_folder, "bin", "madplay")
        assert os.path.isfile(madplay), f"madplay missing at {madplay}"

        fixture = os.path.join(self.build_folder, "fixture.mp3")
        logdir = os.path.join(self.build_folder, "logs")
        os.makedirs(logdir, exist_ok=True)

        # generate the deterministic silent fixture: FRAMES MPEG frames
        self._run_capture([gen_fixture, fixture, str(FRAMES)], "gen_fixture.txt")
        expected = FRAMES * FRAME_LEN
        assert os.path.getsize(fixture) == expected, \
            f"fixture size {os.path.getsize(fixture)} != {expected}"

        # 1. version banners — ver_version prints "madplay 0.15.2 (beta)":
        # the tarball is 0.15.2b, the banner keeps the historic beta suffix.
        out = self._run_capture([madplay, "--version"], "version.txt")
        assert "MPEG Audio Decoder" in out, "mad banner missing"
        assert "ID3 Tag Library" in out, "libid3tag banner missing"
        assert "madplay 0.15.2" in out, "madplay banner missing"

        # 2. usage
        out = self._run_capture([madplay, "--help"], "help.txt")
        assert "usage" in out.lower(), "usage line missing"

        # 3. tags-only parse — no audio output module involved at all
        self._run_capture([madplay, "-T", fixture], "tags.txt")

        # 4. real decode to RIFF/WAVE (file output, no sound card)
        wave_path = os.path.join(self.build_folder, "out.wav")
        self._run_capture([madplay, "-o", f"wave:{wave_path}", fixture], "wave.txt")
        check_wave(wave_path, FRAMES)

        # 5. real decode to hex dump (text PCM)
        hex_path = os.path.join(self.build_folder, "out.hex")
        self._run_capture([madplay, "-o", f"hex:{hex_path}", fixture], "hex.txt")
        check_hex_dump(hex_path, FRAMES)

        # 6. negative: nonexistent input must fail (exit 4 on open failure)
        missing = os.path.join(self.build_folder, "nonexistent.mp3")
        ret = self._exit_code([madplay, "-T", missing])
        assert ret != 0, "madplay must fail on nonexistent input"

        # 7. negative: garbage input decodes zero frames → header-only wave
        garbage = os.path.join(self.build_folder, "garbage.mp3")
        with open(garbage, "wb") as fh:
            fh.write(bytes(range(256)) * 8)
        gw = os.path.join(self.build_folder, "garbage.wav")
        ret = self._exit_code([madplay, "-o", f"wave:{gw}", garbage])
        assert ret == 0, "garbage decode skips bad frames, exits 0"
        assert os.path.getsize(gw) == 44, \
            f"garbage wave must be header-only (44 bytes), got {os.path.getsize(gw)}"

        self.output.success("madplay test_package passed")

    # ── helpers ────────────────────────────────────────────────────
    def _run_capture(self, cmd, log_name):
        """Run via self.run (conanrun env), capture combined output for asserts."""
        log_path = os.path.join(self.build_folder, "logs", log_name)
        command = " ".join(shlex.quote(c) for c in cmd) + f" > {shlex.quote(log_path + '.all')} 2>&1"
        self.run(command, env="conanrun")
        with open(log_path + ".all") as fh:
            out = fh.read()
        with open(os.path.join(self.build_folder, "logs", log_name), "w") as fh:
            fh.write(out)
        return out

    def _exit_code(self, cmd):
        """Run expecting any exit code; return it (via a rc file, since
        self.run raises on non-zero)."""
        rc_file = os.path.join(self.build_folder, "exitcode.txt")
        command = " ".join(shlex.quote(c) for c in cmd) + \
            f" ; rc=$? ; echo $rc > {shlex.quote(rc_file)} ; true"
        self.run(command, env="conanrun")
        with open(rc_file) as fh:
            return int(fh.read().strip())
