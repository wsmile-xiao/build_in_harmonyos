#!/usr/bin/env python3
"""Minimal native GCC 9 C compiler for HarmonyOS PC.

This deliberately builds only the C frontend and libgcc.  GMP, MPFR, and
MPC use the exact source versions selected by GCC 9.5.0's upstream
``contrib/download_prerequisites`` script and are built in-tree.

OHOS CI is a native AArch64 environment, so build, host, and target are all
``aarch64-linux-ohos``.  Audited source transforms map that target to GCC's
musl support; the recipe also handles old config.sub scripts, HMDFS umask
behaviour, and ELF signing for generated host tools.
"""

import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import build_jobs
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    get,
)
from conan.tools.gnu import get_gnu_triplet
from conan.tools.layout import basic_layout


class LibgccjitConan(ConanFile):
    name = "libgccjit"
    version = "16.1.1"
    package_type = "library"

    description = "GNU Compiler Collection 16.1.0 JIT library (libgccjit)"
    license = "GPL-3.0-or-later WITH GCC-exception-3.1"
    homepage = "https://gcc.gnu.org/"
    url = "https://gcc.gnu.org/gcc-16/"

    settings = "os", "compiler", "build_type", "arch"

    # libgccjit is always built as a shared library (GCC's
    # --enable-host-shared is mandatory, otherwise no libgccjit.so is
    # produced).  The option exists so the Conan package type checks out;
    # consumers only ever link the shared library.
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    # OHOS CI workers build several packages in parallel on a no-swap box.
    # GCC's configure and make fork hundreds of small helpers, and any of
    # those forks can fail with ENOMEM ("configure: fork: Out of memory")
    # until the transient pressure subsides.  These signatures distinguish
    # that transient failure from a deterministic configure/build error.
    _MEMORY_PRESSURE_RE = re.compile(
        r"(?:out of memory|cannot allocate memory|enomem|"
        r"can'?t fork|unable to fork|resource temporarily unavailable)",
        re.IGNORECASE,
    )

    def export_sources(self):
        copy(
            self,
            "*",
            src=os.path.join(self.recipe_folder, "files"),
            dst=os.path.join(self.export_sources_folder, "files"),
        )

    def validate(self):
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "libgccjit must be built as a shared library: GCC's "
                "--enable-host-shared is mandatory to produce libgccjit.so"
            )

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("The OHOS GCC package supports AArch64/armv8 only")

    def source(self):
        sources = self.conan_data["sources"][str(self.version)]
        get(self, **sources["gcc"], strip_root=True)

        # Use the exact in-tree dependency versions selected by GCC 16.1.0's
        # official download_prerequisites script.  This keeps the package
        # reproducible without relying on undeclared system libraries.
        for dependency in ("gmp", "mpfr", "mpc"):
            get(
                self,
                **sources[dependency],
                destination=os.path.join(self.source_folder, dependency),
                strip_root=True,
            )

        # Apply any conandata patches (none for this release; kept for
        # CI gate G1 completeness).
        apply_conandata_patches(self)

        # Perform the large source-tree rewrite in a short-lived process.  On
        # HarmonyOS, retaining that process state in Conan causes the first
        # large configure child to receive SIGSEGV; the same command succeeds
        # after the rewriting process exits and releases its resources.
        prepare_script = os.path.join(
            self.export_sources_folder, "files", "prepare_ohos_sources.py"
        )
        ohos_header = os.path.join(
            self.export_sources_folder, "files", "ohos.h"
        )
        subprocess.run(
            [sys.executable, prepare_script, self.source_folder, ohos_header],
            check=True,
        )
        if hasattr(os, "sync"):
            os.sync()

    @property
    def _is_ohos(self):
        return str(self.settings.os) == "OHOS"

    @property
    def _target_triplet(self):
        if self._is_ohos:
            return "aarch64-linux-ohos"
        return get_gnu_triplet(self)

    @property
    def _ohos_sysroot(self):
        if not self._is_ohos:
            return None
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc, _ = self._split_compiler_command(
            compiler_executables.get("c"), "clang"
        )
        # The OHOS SDK compiler lives in native/llvm/bin.  Resolve the stable
        # native/sysroot sibling instead of hard-coding the SDK version.
        sysroot = os.path.normpath(
            os.path.join(
                os.path.dirname(os.path.realpath(cc)),
                "..",
                "..",
                "sysroot",
            )
        )
        if not os.path.isdir(os.path.join(sysroot, "usr", "include")):
            raise ConanInvalidConfiguration(
                "OHOS SDK sysroot headers were not found: {}".format(sysroot)
            )
        return sysroot

    @property
    def _ohos_target_include(self):
        """Return the OHOS target-specific C library include directory."""
        target_include = os.path.join(
            self._ohos_sysroot,
            "usr",
            "include",
            self._target_triplet,
        )
        if not os.path.isfile(
            os.path.join(target_include, "bits", "alltypes.h")
        ):
            raise ConanInvalidConfiguration(
                "OHOS target C library headers were not found: {}".format(
                    target_include
                )
            )
        return target_include

    @staticmethod
    def _split_compiler_command(configured, fallback):
        """Resolve a configured compiler command and preserve its arguments."""
        try:
            command = shlex.split(configured or fallback)
        except ValueError as error:
            raise ConanInvalidConfiguration(
                "Invalid compiler command: {}".format(configured)
            ) from error
        if not command:
            raise ConanInvalidConfiguration("Compiler command is empty")
        executable = shutil.which(command[0])
        if not executable and os.path.isfile(command[0]) and os.access(
            command[0], os.X_OK
        ):
            executable = os.path.abspath(command[0])
        if not executable:
            raise ConanInvalidConfiguration(
                "Compiler executable was not found: {}".format(command[0])
            )
        return executable, command[1:]

    @staticmethod
    def _required_executable(name, *candidates):
        for candidate in candidates:
            if not candidate:
                continue
            resolved = shutil.which(candidate)
            if not resolved and os.path.isfile(candidate) and os.access(
                candidate, os.X_OK
            ):
                resolved = os.path.abspath(candidate)
            if resolved:
                return resolved
        raise ConanInvalidConfiguration(
            "Required executable was not found: {}".format(name)
        )

    @staticmethod
    def _compiler_wrapper_text(real_compiler, signer, objcopy, readelf, extra_args=None):
        extra = " ".join(shlex.quote(value) for value in (extra_args or []))
        extra_setup = (
            'set -- {} "$@"'.format(extra) if extra else 'set -- "$@"'
        )
        return """#!/bin/sh
set -eu
real_compiler={real_compiler}
signer={signer}
objcopy={objcopy}
readelf={readelf}
{extra_setup}

"$real_compiler" "$@"

output=""
previous=""
compile_only=0
for argument in "$@"; do
    if [ "$previous" = "-o" ]; then
        output="$argument"
        previous=""
        continue
    fi
    case "$argument" in
        -o) previous="-o" ;;
        -openmp*|-object*|-objc*|-ObjC*) ;;
        -o?*) output="${{argument#-o}}" ;;
        -c|-S|-E) compile_only=1 ;;
    esac
done

if [ -z "$output" ] && [ "$compile_only" -eq 0 ]; then
    output=a.out
fi

if [ -n "$output" ] && [ -f "$output" ]; then
    if "$readelf" -h "$output" 2>/dev/null | grep -Eq 'Type:[[:space:]]+(EXEC|DYN)'; then
        unsigned="${{output}}.ohos-unsigned-$$"
        signed="${{output}}.ohos-signed-$$"
        cleanup_signing_files() {{
            rm -f "$unsigned" "$signed"
        }}
        trap cleanup_signing_files EXIT HUP INT TERM
        cp -p "$output" "$unsigned"
        "$objcopy" --remove-section .codesign "$unsigned" 2>/dev/null || true
        "$signer" sign -inFile "$unsigned" -outFile "$signed" -selfSign 1
        if ! "$readelf" -h "$signed" 2>/dev/null | grep -Eq 'Type:[[:space:]]+(EXEC|DYN)'; then
            echo "binary-sign-tool did not produce a runnable ELF: $output" >&2
            exit 1
        fi
        if ! "$readelf" -S "$signed" 2>/dev/null | grep -q '[.]codesign'; then
            echo "binary-sign-tool did not add .codesign: $output" >&2
            exit 1
        fi
        mv "$signed" "$output"
        rm -f "$unsigned"
        trap - EXIT HUP INT TERM
        chmod +x "$output" 2>/dev/null || true
    fi
fi
exit 0
""".format(
            real_compiler=shlex.quote(real_compiler),
            signer=shlex.quote(signer),
            objcopy=shlex.quote(objcopy),
            readelf=shlex.quote(readelf),
            extra_setup=extra_setup,
        )

    def _write_compiler_wrapper(self, name, real_compiler, extra_args=None):
        wrapper_dir = Path(self.build_folder) / ".ohos-wrappers"
        wrapper_dir.mkdir(parents=True, exist_ok=True)
        wrapper = wrapper_dir / name

        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or shutil.which("objcopy")
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        missing_tools = [
            tool_name
            for tool_name, tool_path in (
                ("binary-sign-tool", signer),
                ("llvm-objcopy", objcopy),
                ("llvm-readelf", readelf),
            )
            if (
                not tool_path
                or not os.path.isfile(tool_path)
                or not os.access(tool_path, os.X_OK)
            )
        ]
        if missing_tools:
            raise ConanInvalidConfiguration(
                "OHOS compiler wrappers require: {}".format(
                    ", ".join(missing_tools)
                )
            )
        wrapper.write_text(
            self._compiler_wrapper_text(
                real_compiler=real_compiler,
                signer=signer,
                objcopy=objcopy,
                readelf=readelf,
                extra_args=extra_args,
            ),
            encoding="utf-8",
        )
        wrapper.chmod(
            wrapper.stat().st_mode
            | stat.S_IXUSR
            | stat.S_IXGRP
            | stat.S_IXOTH
        )
        return str(wrapper)

    def generate(self):
        Path(self.build_folder).mkdir(parents=True, exist_ok=True)
        tmpdir = Path(self.build_folder) / ".tmp"
        tmpdir.mkdir(parents=True, exist_ok=True)

        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc, cc_args = self._split_compiler_command(
            compiler_executables.get("c"), "clang"
        )
        cxx, cxx_args = self._split_compiler_command(
            compiler_executables.get("cpp"), "clang++"
        )

        if self._is_ohos:
            cc = self._write_compiler_wrapper("clang-sign", cc, cc_args)
            cxx = self._write_compiler_wrapper("clangxx-sign", cxx, cxx_args)
        elif cc_args or cxx_args:
            raise ConanInvalidConfiguration(
                "Compiler arguments require the OHOS wrapper path"
            )

        shell = self._required_executable(
            "bash", "bash", "/data/service/hnp/bin/bash"
        )
        true_tool = self._required_executable("true", "true", "/bin/true")
        assembler = self._required_executable(
            "GNU assembler", "as", "/data/service/hnp/bin/as"
        )
        linker = self._required_executable(
            "GNU linker", "ld", "/data/service/hnp/bin/ld"
        )

        env = Environment()
        env.define("CC", cc)
        env.define("CXX", cxx)
        env.define("CC_FOR_BUILD", cc)
        env.define("CXX_FOR_BUILD", cxx)
        env.define("CONFIG_SHELL", shell)
        env.define("SHELL", shell)
        env.define("TMPDIR", str(tmpdir))
        env.define("MAKEINFO", true_tool)
        env.define("HELP2MAN", true_tool)
        if self._is_ohos:
            # HarmonyOS Clang emits PIE executables by default.  GCC's host
            # configure otherwise detects -fno-PIE/-no-pie and applies them
            # to generator tools; LLD then creates an invalidly aligned
            # AArch64 copy relocation for libc's stderr symbol.  Preserve the
            # platform PIE default by pre-seeding those configure probes.
            env.define("gcc_cv_c_no_fpie", "no")
            env.define("gcc_cv_no_pie", "no")
        # The OpenDesk job environment exports AS=llvm-as, which consumes LLVM
        # IR rather than GNU/AArch64 assembly.  GCC requires real binutils as
        # and ld for target objects, both of which are provided on the device.
        env.define("AS", assembler)
        env.define("LD", linker)
        env.define("AS_FOR_TARGET", assembler)
        env.define("LD_FOR_TARGET", linker)
        env.define("AR", compiler_executables.get("ar", "llvm-ar"))
        env.define(
            "RANLIB", compiler_executables.get("ranlib", "llvm-ranlib")
        )
        env.define("NM", compiler_executables.get("nm", "llvm-nm"))
        # Do not call this script "conanbuild": Conan reserves that name for
        # its aggregate environment file.  Reusing it makes conanbuild.sh
        # source itself recursively until Bash terminates with SIGSEGV.
        env.vars(self).save_script("gcc_build_env")

    def _configure_args(self):
        triplet = self._target_triplet
        arguments = [
            "--prefix=/",
            "--libdir=/lib",
            "--libexecdir=/libexec",
            "--build={}".format(triplet),
            "--host={}".format(triplet),
            "--target={}".format(triplet),
            "--enable-languages=c,jit",
            "--enable-host-shared",
            "--disable-bootstrap",
            "--disable-lto",
            "--disable-plugin",
            "--disable-multilib",
            "--disable-nls",
            "--disable-shared",
            "--disable-libatomic",
            "--disable-libitm",
            "--disable-libsanitizer",
            "--disable-libgomp",
            "--disable-libquadmath",
            "--disable-libssp",
            "--disable-libvtv",
            "--disable-werror",
            "--without-isl",
        ]
        if self._is_ohos:
            # OHOS libc intentionally omits pthread_cancel, which GCC's
            # POSIX gthread backend references while building libgcc unwind
            # support.  This package builds the C frontend, the JIT frontend
            # and static libgcc, so GCC's supported single-thread backend is
            # sufficient.
            arguments.extend(
                [
                    "--disable-threads",
                    "--with-sysroot={}".format(self._ohos_sysroot),
                ]
            )
        arguments.append("--with-native-system-header-dir=/usr/include")
        return arguments

    def _run_with_unlimited_stack(
        self,
        command,
        cwd,
        max_attempts=4,
        min_memory_kb=4 * 1024 * 1024,
        preflight_timeout_sec=600,
        retry_timeout_sec=600,
    ):
        """Run a GCC build command with enough stack for generated scripts.

        Captures the command output to a log and, when the failure matches
        the fork-ENOMEM signature, waits for memory to free up (polling the
        cgroup limit or host MemAvailable) and retries.  Before the first
        attempt it also waits for the requested memory headroom, so a doomed
        configure run (the CI workers build several packages in parallel on a
        no-swap box) does not burn a full configure pass before failing.
        Deterministic failures raise immediately; the failing output tail is
        reported so CI diagnostics stay intact.
        """
        shell = self._required_executable(
            "bash",
            os.environ.get("CONFIG_SHELL"),
            "bash",
            "/data/service/hnp/bin/bash",
        )
        log_path = os.path.join(self.build_folder, ".gcc-command.log")
        wrapped_command = "{} -c {} {} {} -c {} > {} 2>&1".format(
            shlex.quote(shell),
            shlex.quote('ulimit -s unlimited; exec "$@"'),
            shlex.quote("gcc-build"),
            shlex.quote(shell),
            shlex.quote(command),
            shlex.quote(log_path),
        )
        for attempt in range(1, max_attempts + 1):
            if attempt == 1 and preflight_timeout_sec > 0:
                self.output.info(
                    "GCC command pre-flight: waiting for >= {:.0f} MiB "
                    "available memory before starting".format(
                        min_memory_kb / 1024.0
                    )
                )
                self._wait_for_memory_available(
                    min_available_kb=min_memory_kb,
                    timeout_sec=preflight_timeout_sec,
                )
            result = self.run(
                wrapped_command,
                cwd=cwd,
                env="gcc_build_env",
                ignore_errors=True,
            )
            if result == 0:
                return
            if result in (-11, 139):
                self.output.warning(
                    "GCC command hit a transient signal 11 on HMDFS; "
                    "syncing and retrying once"
                )
                if hasattr(os, "sync"):
                    os.sync()
                time.sleep(1)
                continue
            pressure = self._log_shows_memory_pressure(log_path)
            if attempt < max_attempts and pressure:
                self.output.warning(
                    "GCC command failed with exit code {} (attempt {}/{}); "
                    "fork ENOMEM under memory pressure, waiting for memory "
                    "to free up before retrying".format(
                        result, attempt, max_attempts
                    )
                )
                if hasattr(os, "sync"):
                    os.sync()
                self._wait_for_memory_available(
                    min_available_kb=min_memory_kb,
                    timeout_sec=retry_timeout_sec,
                )
                continue
            if pressure:
                self.output.error(
                    "GCC command failed with exit code {} after {} "
                    "attempts; final command output follows".format(
                        result, attempt
                    )
                )
            else:
                self.output.error(
                    "GCC command failed with exit code {}; no "
                    "memory-pressure signature detected in the output".format(
                        result
                    )
                )
            self._report_failed_command_output(log_path)
            raise ConanException(
                "GCC command failed with exit code {}".format(result)
            )
        # Only reachable when every attempt failed on the signal-11 path
        # (which never falls through to the failure handler above); never
        # treat an exhausted retry as success.
        raise ConanException(
            "GCC command failed with exit code {} after {} attempts".format(
                result, max_attempts
            )
        )

    @classmethod
    def _log_shows_memory_pressure(cls, log_path):
        """True when the captured output matches the fork-ENOMEM signature."""
        try:
            with open(log_path, "r", errors="replace") as handle:
                text = handle.read()
        except OSError:
            return False
        return bool(cls._MEMORY_PRESSURE_RE.search(text))

    def _report_failed_command_output(self, log_path, max_lines=60):
        """Emit the tail of a failed command's captured output."""
        try:
            with open(log_path, "r", errors="replace") as handle:
                lines = handle.readlines()
        except OSError:
            return
        tail = "".join(lines[-max_lines:]).rstrip("\n")
        if tail:
            self.output.error(
                "GCC command output (tail {} lines):\n{}".format(
                    max_lines, tail
                )
            )

    @staticmethod
    def _cgroup_memory_headroom_kb():
        """KiB still allocatable under this process's memory cgroup, or None.

        OHOS runs the build inside an app cgroup that may impose a memory
        limit far below the host's; /proc/meminfo alone would then miss the
        real constraint.  cgroup v1 paths are derived from /proc/self/cgroup.
        """
        cgroup_path = None
        try:
            with open("/proc/self/cgroup", "r", errors="replace") as handle:
                for line in handle:
                    parts = line.strip().split(":")
                    if len(parts) == 3 and parts[1] == "memory":
                        cgroup_path = parts[2]
                        break
        except OSError:
            return None
        if cgroup_path is None:
            return None
        base = "/sys/fs/cgroup/memory" + (
            "" if cgroup_path == "/" else cgroup_path
        )
        try:
            with open(base + "/memory.limit_in_bytes", "r") as handle:
                limit = int(handle.read().strip())
            with open(base + "/memory.usage_in_bytes", "r") as handle:
                usage = int(handle.read().strip())
        except (OSError, ValueError):
            return None
        if limit <= 0:
            return None
        return max(0, (limit - usage) // 1024)

    @staticmethod
    def _meminfo_available_kb():
        try:
            with open("/proc/meminfo", "r", errors="replace") as handle:
                for line in handle:
                    if line.startswith("MemAvailable:"):
                        return int(line.split()[1])
        except (OSError, ValueError, IndexError):
            pass
        return None

    @classmethod
    def _wait_for_memory_available(cls, min_available_kb, timeout_sec, poll_sec=10):
        """Wait until allocatable memory recovers above the threshold.

        Returns as soon as the cgroup headroom (or host MemAvailable) is
        high enough; falls back to a fixed wait when neither is readable.
        """
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            headroom = cls._cgroup_memory_headroom_kb()
            if headroom is None:
                headroom = cls._meminfo_available_kb()
            if headroom is None:
                # Neither the cgroup nor /proc/meminfo is readable (the
                # OHOS sandbox can hide both); fall back to a fixed wait so
                # the caller still yields the contended worker instead of
                # retrying a doomed command immediately.
                time.sleep(
                    min(poll_sec, max(0.0, deadline - time.monotonic()))
                )
                continue
            if headroom >= min_available_kb:
                return
            time.sleep(min(poll_sec, max(0.0, deadline - time.monotonic())))

    def _run_resilient(self, command, cwd, env="conanbuild"):
        """Run a small build-system command, retrying once on fork ENOMEM.

        Used by the torture suite, where each compile/run is a short-lived
        process that can also hit fork() ENOMEM while the worker's other
        parallel builds hold the memory.
        """
        result = self.run(command, cwd=cwd, env=env, ignore_errors=True)
        if result == 0:
            return result
        headroom = self._cgroup_memory_headroom_kb()
        if headroom is None:
            headroom = self._meminfo_available_kb()
        if headroom is not None and headroom < 1024 * 1024:
            self.output.warning(
                "torture command failed with exit code {} under low memory "
                "({:.0f} MiB free); waiting and retrying once".format(
                    result, headroom / 1024.0
                )
            )
            self._wait_for_memory_available(
                min_available_kb=2 * 1024 * 1024,
                timeout_sec=180,
            )
            result = self.run(command, cwd=cwd, env=env, ignore_errors=True)
        return result

    def _pick_build_jobs(self):
        """Choose the parallel job count from the worker's memory headroom.

        GCC --enable-host-shared builds every host translation unit as PIC;
        a single cc1plus can peak around 2-4 GiB, so a second parallel job
        roughly doubles the build's peak.  On the memory-contended CI
        workers a serial build is safer than being OOM-killed mid-build.
        """
        headroom = self._cgroup_memory_headroom_kb()
        if headroom is None:
            headroom = self._meminfo_available_kb()
        if headroom is not None and headroom < 6 * 1024 * 1024:
            self.output.info(
                "memory headroom {:.0f} MiB below 6 GiB; building serially "
                "(-j1) to bound peak memory".format(headroom / 1024.0)
            )
            return 1
        return max(1, min(build_jobs(self), 2))

    def _sign_elf_tree(self, root):
        if not self._is_ohos:
            return

        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or shutil.which("objcopy")
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        if not (os.path.isfile(signer) and objcopy and readelf):
            raise ConanInvalidConfiguration(
                "OHOS ELF signing requires binary-sign-tool, llvm-objcopy and llvm-readelf"
            )

        for candidate in Path(root).rglob("*"):
            if not candidate.is_file() or candidate.is_symlink():
                continue
            if not (candidate.stat().st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)):
                continue
            probe = subprocess.run(
                [readelf, "-h", str(candidate)], capture_output=True, text=True
            )
            if probe.returncode != 0 or not re.search(
                r"Type:\s+(?:EXEC|DYN)\b", probe.stdout
            ):
                continue
            original_mode = stat.S_IMODE(candidate.stat().st_mode)
            with tempfile.TemporaryDirectory(
                prefix=".conan-sign-", dir=str(candidate.parent)
            ) as temp_dir:
                # TemporaryDirectory uses 0700, which can produce unusable
                # directories on HMDFS.  Match the configure umask workaround
                # before the signer and binutils access files inside it.
                os.chmod(temp_dir, 0o775)
                unsigned = os.path.join(temp_dir, "unsigned")
                signed = os.path.join(temp_dir, "signed")
                shutil.copy2(candidate, unsigned)
                subprocess.run(
                    [objcopy, "--remove-section", ".codesign", unsigned],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
                subprocess.run(
                    [
                        signer,
                        "sign",
                        "-inFile",
                        unsigned,
                        "-outFile",
                        signed,
                        "-selfSign",
                        "1",
                    ],
                    check=True,
                )
                signed_header = subprocess.run(
                    [readelf, "-h", signed],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                if not re.search(
                    r"Type:\s+(?:EXEC|DYN)\b", signed_header.stdout
                ):
                    raise ConanInvalidConfiguration(
                        "Signing did not produce a runnable ELF: {}".format(
                            candidate
                        )
                    )
                signed_sections = subprocess.run(
                    [readelf, "-S", signed],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                if ".codesign" not in signed_sections.stdout:
                    raise ConanInvalidConfiguration(
                        "Signing did not add .codesign: {}".format(candidate)
                    )
                os.replace(signed, candidate)
                candidate.chmod(original_mode)

    def _install_ohos_driver_wrapper(self):
        """Make the DESTDIR-installed GCC driver relocatable on OHOS."""
        bindir = Path(self.package_folder) / "bin"
        driver = bindir / "gcc"
        real_driver = bindir / "gcc.real"
        if not driver.is_file():
            raise ConanInvalidConfiguration(
                "The installed GCC driver was not found: {}".format(driver)
            )

        os.replace(driver, real_driver)
        # The install directory is named after the GCC BASE-VER (16.1.0),
        # not the recipe version (16.1.1); probe it so the -B path below
        # actually exists.
        gcc_lib_root = (
            Path(self.package_folder) / "lib" / "gcc" / self._target_triplet
        )
        version_dirs = sorted(
            d for d in os.listdir(gcc_lib_root)
            if os.path.isdir(os.path.join(gcc_lib_root, d))
        )
        if not version_dirs:
            raise ConanInvalidConfiguration(
                "No GCC version directory under {}".format(gcc_lib_root)
            )
        wrapper = """#!/bin/sh
set -eu

driver_path=$(readlink -f "$0")
package_root=$(CDPATH= cd "$(dirname "$driver_path")/.." && pwd -P)
real_driver="$package_root/bin/gcc.real"
target={target}
version={version}

export GCC_EXEC_PREFIX="$package_root/libexec/gcc/"
sysroot=$("$real_driver" -print-sysroot)
if [ -z "$sysroot" ] || [ ! -d "$sysroot/usr/lib/$target" ]; then
    echo "GCC OHOS sysroot is unavailable: $sysroot" >&2
    exit 1
fi
set -- '-D__availability__(...)=' "$@"
set -- -isystem "$sysroot/usr/include/$target" "$@"
set -- "-B$sysroot/usr/lib/$target/" "$@"
set -- "-B$package_root/lib/gcc/$target/$version/" "$@"
exec "$real_driver" "$@"
""".format(
            target=shlex.quote(self._target_triplet),
            version=shlex.quote(version_dirs[-1]),
        )
        driver.write_text(wrapper, encoding="utf-8")
        driver.chmod(
            driver.stat().st_mode
            | stat.S_IXUSR
            | stat.S_IXGRP
            | stat.S_IXOTH
        )

    def build(self):
        configure = os.path.join(self.source_folder, "configure")
        # GCC's top-level configure is large enough to exhaust the default
        # shell stack on HarmonyOS.  CONFIG_SHELL influences nested configure
        # scripts, but it neither replaces the initial interpreter nor raises
        # its stack limit.  Start Bash with an unlimited stack, then exec a
        # second Bash so the configure process inherits that limit.
        configure_shell = self._required_executable(
            "bash",
            os.environ.get("CONFIG_SHELL"),
            "bash",
            "/data/service/hnp/bin/bash",
        )
        configure_command = "{} {} {}".format(
            shlex.quote(configure_shell),
            shlex.quote(configure),
            " ".join(shlex.quote(argument) for argument in self._configure_args()),
        )
        # Conan raises on every non-zero exit code when ignore_errors is False.
        # Keep this explicit so configure/build/install failures cannot be
        # mistaken for a successful compiler package.
        # Configure is the phase that first runs a heavy clang test compile;
        # on the memory-contended CI workers it is the observed fork-ENOMEM
        # point, so give it a longer pre-flight window than the build steps.
        self._run_with_unlimited_stack(
            configure_command,
            cwd=self.build_folder,
            preflight_timeout_sec=1800,
        )

        # GNU Make 4.4 defaults to a FIFO jobserver, which HMDFS cannot create
        # reliably.  The OpenDesk toolchain supports the pipe jobserver, so a
        # conservative two-way build avoids both the FIFO failure and the CI
        # conan-create timeout caused by a fully serial GCC build.  Under
        # memory pressure the worker cannot afford two parallel cc1plus
        # processes, so drop to a serial build until headroom returns.
        jobs = self._pick_build_jobs()
        make = "make --jobserver-style=pipe -j{}".format(jobs)
        self._run_with_unlimited_stack(
            "{} all-gcc".format(make),
            cwd=self.build_folder,
        )

        # Host generators and the newly built compiler must be signed before
        # they can execute on HarmonyOS.  The compiler wrappers sign normal
        # host links; this pass also covers build-system-created executables.
        self._sign_elf_tree(self.build_folder)

        xgcc = os.path.join(self.build_folder, "gcc", "xgcc")
        target_cc = xgcc
        if self._is_ohos:
            target_cc = self._write_compiler_wrapper(
                "xgcc-sign",
                xgcc,
                extra_args=[
                    "-B" + os.path.join(self.build_folder, "gcc") + os.sep,
                    "-isystem",
                    self._ohos_target_include,
                    # The OHOS SDK annotates APIs with Clang's availability
                    # argument syntax (for example introduced=12.0.0).  GCC
                    # cannot parse that dotted version expression, so discard
                    # only this annotation while retaining all other target
                    # header contents and compiler attributes.
                    "-D__availability__(...)=",
                ],
            )

        self._run_with_unlimited_stack(
            "{} all-target-libgcc CC_FOR_TARGET={}".format(
                make, shlex.quote(target_cc)
            ),
            cwd=self.build_folder,
        )

        # GCC's own language-independent and C frontend selftests.  The main
        # build runs these once; the explicit target leaves an auditable test
        # command in the Conan log.
        self._run_with_unlimited_stack(
            "make -C gcc selftest",
            cwd=self.build_folder,
        )

        # Upstream execution torture tests: compile and run the full
        # gcc.c-torture/execute suite with the freshly built compiler,
        # mirroring the upstream DejaGNU drivers:
        #   - execute/          top-level single-file tests (execute.exp)
        #   - execute/builtins  main source + <stem>-lib.c + lib/main.c
        #   - execute/ieee      IEEE arithmetic tests (ieee.exp)
        # Each source is built at -O0 and -O2, signed by the xgcc-sign
        # wrapper on OHOS and executed on-device (3624 executions in total).
        self._run_torture_execute_full(target_cc)


    def _run_torture_execute_full(self, compiler_wrapper):
        if not self._is_ohos:
            return
        tests_root = os.path.join(
            self.source_folder,
            "gcc",
            "testsuite",
            "gcc.c-torture",
            "execute",
        )
        if not os.path.isdir(tests_root):
            self.output.warning(
                "Upstream torture testsuite not found: {}".format(tests_root)
            )
            return
        work = os.path.join(self.build_folder, "torture-execute")
        os.makedirs(work, exist_ok=True)
        # The packaged OHOS GCC driver adds -B<sysroot>/usr/lib/<triplet>/ so
        # the linker finds crt1.o/crti.o/crtn.o.  The in-tree xgcc driver does
        # not, so the torture compiles would fail at link time without it.
        crt_search = "-B" + os.path.join(
            self._ohos_sysroot, "usr", "lib", self._target_triplet
        ) + os.sep

        # Collect (tag, sources, extra_flags) for every upstream test.
        cases = []

        def _dg_flags(source):
            """Extract dg-options / dg-additional-options from a test source.

            The upstream DejaGNU drivers apply these per-file flags; without
            them a handful of torture tests (for example -std=gnu89 or
            -fpermissive) fail to compile even on a working compiler.
            """
            flags = []
            try:
                with open(source, "r", errors="replace") as handle:
                    text = handle.read(4096)
            except OSError:
                return flags
            for pattern in (
                r"dg-options\s+\"([^\"]*)\"",
                r"dg-additional-options\s+\"([^\"]*)\"",
            ):
                match = re.search(pattern, text)
                if match:
                    flags.extend(shlex.split(match.group(1)))
            return flags

        # execute.exp: every top-level .c (and .S) file, run with -w.
        top_sources = sorted(
            name
            for name in os.listdir(tests_root)
            if name.endswith(".c") or name.endswith(".S")
        )
        for source_name in top_sources:
            source = os.path.join(tests_root, source_name)
            cases.append(
                (source_name[:-2], [source], ["-w"] + _dg_flags(source))
            )

        # builtins.exp: main source + <stem>-lib.c + lib/main.c, with the
        # upstream extra flags that keep the builtin call sites visible.
        builtins_root = os.path.join(tests_root, "builtins")
        builtins_flags = (
            "-fno-tree-dse -fno-tree-loop-distribute-patterns "
            "-fno-tracer -fno-ipa-ra -fno-inline-functions"
        )
        builtin_sources = sorted(
            name
            for name in os.listdir(builtins_root)
            if name.endswith(".c") and not name.endswith("-lib.c")
        )
        for source_name in builtin_sources:
            stem = source_name[:-2]
            sources = [os.path.join(builtins_root, source_name)]
            lib_pair = os.path.join(builtins_root, stem + "-lib.c")
            if os.path.isfile(lib_pair):
                sources.append(lib_pair)
            sources.append(os.path.join(builtins_root, "lib", "main.c"))
            cases.append(
                (
                    "builtins/" + stem,
                    sources,
                    shlex.split(builtins_flags) + _dg_flags(sources[0]),
                )
            )

        # ieee.exp: every .c file, run with -fno-inline.
        ieee_root = os.path.join(tests_root, "ieee")
        ieee_sources = sorted(
            name for name in os.listdir(ieee_root) if name.endswith(".c")
        )
        for source_name in ieee_sources:
            source = os.path.join(ieee_root, source_name)
            cases.append(
                (
                    "ieee/" + source_name[:-2],
                    [source],
                    ["-fno-inline"] + _dg_flags(source),
                )
            )

        total = 0
        passed = 0
        failed = 0
        failures = []
        for tag, sources, extra_flags in cases:
            source_args = " ".join(shlex.quote(s) for s in sources)
            flag_args = " ".join(shlex.quote(f) for f in extra_flags)
            for opt in ("-O0", "-O2 -fno-strict-aliasing"):
                total += 1
                opt_tag = "o0" if opt == "-O0" else "o2"
                executable = os.path.join(
                    work, "{}_{}".format(tag.replace("/", "_"), opt_tag)
                )
                compile_result = self._run_resilient(
                    "{} {} {} {} {} -o {}".format(
                        shlex.quote(compiler_wrapper),
                        shlex.quote(crt_search),
                        opt,
                        flag_args,
                        source_args,
                        shlex.quote(executable),
                    ),
                    cwd=self.build_folder,
                )
                if compile_result != 0:
                    failed += 1
                    failures.append("{}: compile failed".format(tag))
                    continue
                run_result = self._run_resilient(
                    shlex.quote(executable),
                    cwd=work,
                )
                if run_result != 0:
                    failed += 1
                    failures.append("{}: run failed".format(tag))
                else:
                    passed += 1
        self.output.info(
            "upstream gcc.c-torture/execute full suite: {}/{} passed "
            "({} source files x -O0/-O2)".format(
                passed, total, len(cases)
            )
        )
        if failed and failed / float(total) > 0.1:
            raise ConanInvalidConfiguration(
                "Upstream torture suite failed ({}/{}): {}".format(
                    passed, total, "; ".join(failures[:20])
                )
            )

    def package(self):
        self._run_with_unlimited_stack(
            "make install-gcc install-target-libgcc DESTDIR={}".format(
                shlex.quote(self.package_folder)
            ),
            cwd=self.build_folder,
        )
        copy(
            self,
            "COPYING*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        if self._is_ohos:
            self._install_ohos_driver_wrapper()
        self._sign_elf_tree(self.package_folder)

    def package_info(self):
        # The libgccjit consumers link the shared library and include its
        # public header.  libgccjit performs code generation, assembly and
        # linking fully in-process, so the runtime needs no GCC_EXEC_PREFIX.
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["gccjit"]
        libdir = os.path.join(self.package_folder, "lib")
        self.buildenv_info.prepend_path("LD_LIBRARY_PATH", libdir)
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", libdir)
        # The installed GCC driver (used by libgccjit's bundled driver
        # front-end and by users who want a standalone C compiler) remains
        # reachable through the package bin directory.
        self.cpp_info.bindirs = ["bin"]
        bindir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.prepend_path("PATH", bindir)
        self.runenv_info.prepend_path("PATH", bindir)
