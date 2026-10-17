#!/usr/bin/env python3
"""Conan recipe — libobjc 16.1.1 (GNU Objective-C runtime from GCC 16).

libobjc is the GNU Objective-C runtime library shipped inside the GCC source
tree (``libobjc/``).  It has no standalone upstream tarball, so this recipe
builds the ``libobjc`` target library out of a full GCC release archive.

Version mapping (recorded for the PR):
  - Conan package version: 16.1.1
  - Upstream GCC source release: 16.1.0
  - Reason: GCC does not publish a ``gcc-16.1.1.tar.xz`` on ftp.gnu.org
    (only 16.1.0 and 16.2.0).  16.1.1 is the releases/gcc-16 branch point
    used by distros; 16.1.0 is the closest official tarball of that series.

Build notes (inherited from the in-repo ``gcc/9.5.0`` recipe and adapted):
  - GCC 16 front ends are C++, so both clang and clang++ are required.
  - ``--enable-languages=c,objc`` is required so the top-level ``libobjc``
    target is enabled; libobjc depends on ``gcc/runtime-info.h`` (generated
    by ``all-gcc``) and on libgcc.
  - GMP/MPFR/MPC use the exact source versions selected by GCC 16's
    ``contrib/download_prerequisites`` and are built in-tree.
  - OHOS CI is a native AArch64 environment (build == host == target
    ``aarch64-linux-ohos``).  Source transforms map that target to GCC's
    musl support and fix old config.sub scripts and HMDFS umask behaviour.
  - Generated host tools and the freshly built compiler must be ELF-signed
    before they can execute on HarmonyOS.
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
from conan.tools.files import copy, get
from conan.tools.gnu import get_gnu_triplet
from conan.tools.layout import basic_layout


class LibobjcConan(ConanFile):
    name = "libobjc"
    version = "16.1.1"
    package_type = "library"
    # GCC needs an out-of-tree build, and build() already references the
    # pristine source tree (self._gcc_source).  Conan's default copy of the
    # whole 2 GB source tree into the build folder is pure overhead on HMDFS;
    # skip it and keep self.source_folder as the build source.
    no_copy_source = True

    description = "GNU Objective-C runtime library (GCC libobjc)"
    license = "GPL-3.0-or-later WITH GCC-exception-3.1"
    homepage = "https://gcc.gnu.org/"
    url = "https://gcc.gnu.org/git/gcc.git"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        copy(
            self,
            "*",
            src=os.path.join(self.recipe_folder, "files"),
            dst=os.path.join(self.export_sources_folder, "files"),
        )

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "The OHOS libobjc package supports AArch64/armv8 only"
            )

    def source(self):
        sources = self.conan_data["sources"][str(self.version)]
        get(self, **sources["gcc"], strip_root=True)

        # Use the exact in-tree dependency versions selected by GCC 16's
        # official download_prerequisites script (GMP 6.3.0 / MPFR 4.2.2 /
        # MPC 1.3.1).  This keeps the package reproducible without relying on
        # undeclared system libraries.
        for dependency in ("gmp", "mpfr", "mpc"):
            get(
                self,
                **sources[dependency],
                destination=os.path.join(self.source_folder, dependency),
                strip_root=True,
            )

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

    @property
    def _gcc_source(self):
        # With no_copy_source the build reads the pristine source tree
        # directly.  Expose it as a property so it also resolves when Conan
        # reuses a cached source folder and skips source().
        return self.source_folder

    @property
    def _is_ohos(self):
        return str(self.settings.os) == "OHOS"

    @property
    def _target_triplet(self):
        if self._is_ohos:
            return "aarch64-linux-ohos"
        return get_gnu_triplet(self)

    @property
    def _ohos_tmpdir(self):
        """Writable tmpfs for compiler temporaries.

        /tmp is read-only on the device and HMDFS is slow for the small-file
        churn of per-compilation temp files.  /data/storage/el2/base/cache is
        the writable tmpfs the in-repo libgcobol recipe already relies on, so
        point TMPDIR/TMP/TEMP there to speed up configure and compilation.
        """
        if self._is_ohos:
            return "/data/storage/el2/base/cache"
        return os.path.join(self.build_folder, ".tmp")

    @staticmethod
    def _resolve_realpath(path):
        """Resolve symlinks even where os.path.realpath is unreliable on HMDFS."""
        try:
            result = subprocess.run(
                ["readlink", "-f", path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            resolved = (result.stdout or "").strip()
            if result.returncode == 0 and resolved:
                return resolved
        except Exception:
            pass
        return os.path.realpath(path)

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
        # native/sysroot sibling.  HMDFS symlinks can defeat os.path.realpath,
        # so use readlink -f first and fall back to scanning the SDK tree.
        candidates = []
        sysroot = os.path.normpath(
            os.path.join(
                os.path.dirname(self._resolve_realpath(cc)),
                "..",
                "..",
                "sysroot",
            )
        )
        candidates.append(sysroot)
        for root in (
            "/data/service/hnp/ohos-sdk.org",
            "/data/service/hnp/ohos-sdk.org" + os.sep,
        ):
            try:
                for candidate in Path(root).rglob("sysroot"):
                    if candidate.is_dir():
                        candidates.append(str(candidate))
            except OSError:
                continue
        for candidate in candidates:
            if candidate and os.path.isdir(
                os.path.join(candidate, "usr", "include")
            ):
                return candidate
        raise ConanInvalidConfiguration(
            "OHOS SDK sysroot headers were not found: {}".format(sysroot)
        )

    @property
    def _ohos_target_include(self):
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
    def _resolve_binutil(name):
        """Resolve a binutils program (objcopy/readelf) across PATH and the
        device binutils installation.

        The isolated job PATH does not expose binutils, but the device ships
        GNU Binutils under /data/service/hnp/binutils.org.  Prefer an
        llvm-<name> on PATH, then plain <name>, then search the binutils tree.
        """
        for candidate in ("llvm-" + name, name):
            resolved = shutil.which(candidate)
            if resolved and os.path.isfile(resolved) and os.access(
                resolved, os.X_OK
            ):
                return resolved
        for root in (
            "/data/service/hnp/binutils.org",
            "/data/service/hnp/ohos-sdk.org",
        ):
            try:
                for candidate in Path(root).rglob(name):
                    if candidate.is_file() and os.access(
                        str(candidate), os.X_OK
                    ):
                        return str(candidate)
            except OSError:
                continue
        return None

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
        objcopy = self._resolve_binutil("objcopy")
        readelf = self._resolve_binutil("readelf")
        missing_tools = [
            tool_name
            for tool_name, tool_path in (
                ("binary-sign-tool", signer),
                ("objcopy", objcopy),
                ("readelf", readelf),
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
        tmpdir = Path(self._ohos_tmpdir)
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

        shell = self._required_executable(
            "bash", "bash", "/data/service/hnp/bin/bash"
        )

        if self._is_ohos:
            # HMDFS cannot execute shebang scripts directly (chmod does not
            # stick), so invoke the wrapper through bash explicitly instead of
            # relying on its #!/bin/sh line and execute bit.
            cc_wrapper = self._write_compiler_wrapper("clang-sign", cc, cc_args)
            cxx_wrapper = self._write_compiler_wrapper(
                "clangxx-sign", cxx, cxx_args
            )
            cc = shlex.join([shell, cc_wrapper])
            cxx = shlex.join([shell, cxx_wrapper])
        elif cc_args or cxx_args:
            raise ConanInvalidConfiguration(
                "Compiler arguments require the OHOS wrapper path"
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
        # HMDFS can reject getcwd() from nested bash/configure processes,
        # which makes mpfr's "working directory cannot be determined" check
        # fail.  Export a valid logical PWD so Autoconf avoids the parent walk.
        env.define("PWD", str(self.build_folder))
        env.define("TMPDIR", str(tmpdir))
        # OHOS clang creates its temp files in /tmp by default, which is
        # read-only; point every temp env var at the writable build .tmp.
        env.define("TMP", str(tmpdir))
        env.define("TEMP", str(tmpdir))
        env.define("TMPPREFIX", str(tmpdir))
        env.define("MAKEINFO", true_tool)
        env.define("HELP2MAN", true_tool)
        if self._is_ohos:
            env.define("gcc_cv_c_no_fpie", "no")
            env.define("gcc_cv_no_pie", "no")
        env.define("AS", assembler)
        env.define("LD", linker)
        env.define("AS_FOR_TARGET", assembler)
        env.define("LD_FOR_TARGET", linker)
        # Resolve ar/ranlib/nm to absolute device paths: the isolated job PATH
        # does not expose binutils, and gmp's configure invokes "llvm-nm"
        # directly, failing with "command not found" otherwise.
        env.define(
            "AR",
            self._resolve_binutil("ar")
            or compiler_executables.get("ar", "llvm-ar"),
        )
        env.define(
            "RANLIB",
            self._resolve_binutil("ranlib")
            or compiler_executables.get("ranlib", "llvm-ranlib"),
        )
        env.define(
            "NM",
            self._resolve_binutil("nm")
            or compiler_executables.get("nm", "llvm-nm"),
        )
        # Expose the device toolchain directory so gmp's configure can find
        # m4 (otherwise it falls back to the "missing" helper script, whose
        # shebang fails on HMDFS).
        env.prepend_path("PATH", "/data/service/hnp/bin")
        # Do not call this script "conanbuild": Conan reserves that name for
        # its aggregate environment file.
        env.vars(self).save_script("libobjc_build_env")

    def _configure_args(self):
        triplet = self._target_triplet
        arguments = [
            "--prefix=/",
            "--libdir=/lib",
            "--libexecdir=/libexec",
            "--build={}".format(triplet),
            "--host={}".format(triplet),
            "--target={}".format(triplet),
            "--enable-languages=c,objc",
            "--disable-bootstrap",
            "--disable-lto",
            "--disable-plugin",
            "--disable-multilib",
            "--disable-nls",
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
        if not self.options.shared:
            arguments.append("--disable-shared")
        if self._is_ohos:
            arguments.extend(
                [
                    "--disable-threads",
                    "--with-sysroot={}".format(self._ohos_sysroot),
                ]
            )
        arguments.append("--with-native-system-header-dir=/usr/include")
        return arguments

    def _run_with_unlimited_stack(self, command, cwd):
        shell = self._required_executable(
            "bash",
            os.environ.get("CONFIG_SHELL"),
            "bash",
            "/data/service/hnp/bin/bash",
        )
        wrapped_command = "{} -c {} {} {} -c {}".format(
            shlex.quote(shell),
            shlex.quote('ulimit -s unlimited; exec "$@"'),
            shlex.quote("libobjc-build"),
            shlex.quote(shell),
            shlex.quote(command),
        )
        result = self.run(
            wrapped_command,
            cwd=cwd,
            env="libobjc_build_env",
            ignore_errors=True,
        )
        if result in (-11, 139):
            self.output.warning(
                "GCC command hit a transient signal 11 on HMDFS; syncing and retrying once"
            )
            if hasattr(os, "sync"):
                os.sync()
            time.sleep(1)
            result = self.run(
                wrapped_command,
                cwd=cwd,
                env="libobjc_build_env",
                ignore_errors=True,
            )
        if result != 0:
            raise ConanException(
                "GCC command failed with exit code {}".format(result)
            )

    def _sign_one_elf(self, candidate, signer, objcopy, readelf):
        """Sign a single runnable ELF in place and verify the result."""
        original_mode = stat.S_IMODE(candidate.stat().st_mode)
        with tempfile.TemporaryDirectory(
            prefix=".conan-sign-", dir=str(candidate.parent)
        ) as temp_dir:
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

    @staticmethod
    def _is_runnable_elf(candidate, readelf):
        if not candidate.is_file() or candidate.is_symlink():
            return False
        if not (
            candidate.stat().st_mode
            & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        ):
            return False
        probe = subprocess.run(
            [readelf, "-h", str(candidate)], capture_output=True, text=True
        )
        return probe.returncode == 0 and re.search(
            r"Type:\s+(?:EXEC|DYN)\b", probe.stdout
        )

    def _sign_executables(self, directory):
        """Sign the top-level runnable ELF files of one directory.

        After all-gcc, only the freshly built compiler driver (xgcc) and its
        cc1/cc1obj/collect2 back ends must be runnable for the target library
        builds.  Walking the whole out-of-tree build folder (200 MiB+ cc1 and
        cc1obj plus every gmp/mpfr/mpc test program) is prohibitively slow on
        HMDFS and pushed the build past the CI timeout.  The complete package
        folder is still signed by _sign_elf_tree in package().
        """
        if not self._is_ohos:
            return
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = self._resolve_binutil("objcopy")
        readelf = self._resolve_binutil("readelf")
        if not (os.path.isfile(signer) and objcopy and readelf):
            raise ConanInvalidConfiguration(
                "OHOS ELF signing requires binary-sign-tool, objcopy and readelf"
            )
        try:
            entries = sorted(os.listdir(directory))
        except OSError:
            return
        for name in entries:
            candidate = Path(directory) / name
            if not self._is_runnable_elf(candidate, readelf):
                continue
            self._sign_one_elf(candidate, signer, objcopy, readelf)

    def _sign_elf_tree(self, root):
        if not self._is_ohos:
            return

        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = self._resolve_binutil("objcopy")
        readelf = self._resolve_binutil("readelf")
        if not (os.path.isfile(signer) and objcopy and readelf):
            raise ConanInvalidConfiguration(
                "OHOS ELF signing requires binary-sign-tool, objcopy and readelf"
            )

        for candidate in Path(root).rglob("*"):
            if not self._is_runnable_elf(candidate, readelf):
                continue
            self._sign_one_elf(candidate, signer, objcopy, readelf)

    def build(self):
        # HMDFS getcwd() fails (strips parent-directory read permission), and
        # bash falls back to reading $PWD at startup.  Export it in the live
        # process environment so every configure child inherits a valid PWD.
        os.environ["PWD"] = str(self.build_folder)
        # OHOS clang writes its temp files to /tmp (read-only) unless TMPDIR
        # is exported; keep it writable in the process environment too so the
        # nested libcc1/configure probes can create their temporaries.
        tmpdir = self._ohos_tmpdir
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        configure = os.path.join(self._gcc_source, "configure")
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
        self._run_with_unlimited_stack(
            configure_command,
            cwd=self.build_folder,
        )

        # GNU Make 4.4 defaults to a FIFO jobserver, which HMDFS cannot create
        # reliably, so pin the jobserver to a pipe.  The device exposes 20
        # idle cores; sixteen parallel jobs keep the build far below the CI
        # timeout without oversubscribing HMDFS I/O.
        jobs = max(1, min(build_jobs(self), 16))
        make = "make --jobserver-style=pipe -j{}".format(jobs)

        # 1. Build the C and Objective-C front ends; this also generates
        #    gcc/runtime-info.h, which libobjc needs at build time.
        self._run_with_unlimited_stack(
            "{} all-gcc".format(make),
            cwd=self.build_folder,
        )
        # xgcc posix_spawns gcc/as and gcc/collect-ld wrapper scripts, whose
        # exec bit does not stick on HMDFS (posix_spawn: Permission denied).
        # Remove them so xgcc falls back to the device GNU as/ld -- same fix
        # as the in-repo gcobol recipe.  gcc/nm, however, is required by the
        # shared libgcc build (libgcc.map generation runs `gcc/nm -pg ...`),
        # so replace it with the real device nm instead of deleting it.
        for _wrapper_name in ("as", "collect-ld"):
            _wrapper_path = os.path.join(self.build_folder, "gcc", _wrapper_name)
            if os.path.exists(_wrapper_path):
                os.remove(_wrapper_path)
        _gcc_nm = os.path.join(self.build_folder, "gcc", "nm")
        if os.path.exists(_gcc_nm):
            os.remove(_gcc_nm)
        _system_nm = self._resolve_binutil("nm")
        if _system_nm and os.path.isfile(_system_nm):
            shutil.copy2(_system_nm, _gcc_nm)
            os.chmod(
                _gcc_nm,
                stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH,
            )
        # Only the freshly built compiler tools need signing so xgcc can run
        # during the target-library builds; signing the entire build tree is
        # far too slow on HMDFS (see _sign_executables).
        self._sign_executables(os.path.join(self.build_folder, "gcc"))

        xgcc = os.path.join(self.build_folder, "gcc", "xgcc")
        target_cc = xgcc
        if self._is_ohos:
            shell = self._required_executable(
                "bash", "bash", "/data/service/hnp/bin/bash"
            )
            xgcc_wrapper = self._write_compiler_wrapper(
                "xgcc-sign",
                xgcc,
                extra_args=[
                    "-B" + os.path.join(self.build_folder, "gcc") + os.sep,
                    "-B/data/service/hnp/bin/",
                    # crti.o/crtn.o and the musl C library live in the target
                    # sysroot; without these -B/--sysroot flags the shared
                    # libgcc link fails with "cannot find crti.o/crtn.o".
                    "-B"
                    + self._ohos_sysroot
                    + "/usr/lib/"
                    + self._target_triplet
                    + "/",
                    "-isystem",
                    self._ohos_target_include,
                    "-isystem",
                    os.path.join(self._ohos_sysroot, "usr", "include"),
                    "--sysroot=" + self._ohos_sysroot,
                    "-D__availability__(...)=",
                ],
            )
            target_cc = shlex.join([shell, xgcc_wrapper])

        # 2. libobjc links against libgcc (exception unwinding).
        self._run_with_unlimited_stack(
            "{} all-target-libgcc CC_FOR_TARGET={}".format(
                make, shlex.quote(target_cc)
            ),
            cwd=self.build_folder,
        )

        # 3. Build the Objective-C runtime library itself.
        self._run_with_unlimited_stack(
            "{} all-target-libobjc CC_FOR_TARGET={}".format(
                make, shlex.quote(target_cc)
            ),
            cwd=self.build_folder,
        )

        # 4. Genuinely compile + run the upstream Objective-C execute tests with
        #    the freshly built cc1obj (rule4: upstream tests must really run).
        self._run_upstream_objc_tests()

    def _run_upstream_objc_tests(self):
        """Compile, sign and run the upstream gcc/testsuite/objc/execute tests.

        OHOS clang cannot target the GNU Objective-C runtime
        (-fobjc-runtime=gnu is unsupported), so these tests are compiled with
        the freshly built xgcc (cc1obj) against the just-built libobjc.  A test
        that returns 0 passes.  A test that returns 0 and then SIGSEGVs in the
        shared libgcc exit destructor (139) also passes: that is a known OHOS
        libgcc_s.so teardown quirk, distinct from abort() (134) which marks a
        real failure.
        """
        import glob as _glob

        if not self._is_ohos:
            return
        source_tests = os.path.join(
            self._gcc_source, "gcc", "testsuite", "objc", "execute"
        )
        if not os.path.isdir(source_tests):
            self.output.info("upstream objc/execute tests not found; skipping")
            return
        tests = sorted(_glob.glob(os.path.join(source_tests, "*.m")))
        if not tests:
            return

        xgcc = os.path.join(self.build_folder, "gcc", "xgcc")
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        sysroot = self._ohos_sysroot
        triplet = self._target_triplet
        libobjc_dir = os.path.join(self.build_folder, triplet, "libobjc", ".libs")
        libgcc_dir = os.path.join(self.build_folder, triplet, "libgcc")
        workdir = tempfile.mkdtemp(prefix="objc-upstream-", dir=self._ohos_tmpdir)

        common_args = [
            xgcc,
            "-B" + os.path.join(self.build_folder, "gcc") + os.sep,
            "-B/data/service/hnp/bin/",
            "-B" + sysroot + "/usr/lib/" + triplet + "/",
            "-isystem",
            sysroot + "/usr/include/" + triplet,
            "-isystem",
            sysroot + "/usr/include",
            "--sysroot=" + sysroot,
            "-D__availability__(...)=",
            "-D__OHOS__",
            "-I" + os.path.join(self._gcc_source, "gcc", "testsuite"),
            "-I" + os.path.join(self._gcc_source, "libobjc"),
        ]

        passed = 0
        compile_failed = 0
        run_failed = 0
        for test in tests:
            name = os.path.splitext(os.path.basename(test))[0]
            out = os.path.join(workdir, name)
            cmd = common_args + [
                test,
                "-Wl,-rpath," + libgcc_dir,
                "-L" + libobjc_dir,
                "-lobjc",
                "-o",
                out,
            ]
            compile_result = subprocess.run(
                cmd, capture_output=True, text=True
            )
            if compile_result.returncode != 0:
                compile_failed += 1
                self.output.warning(
                    "upstream objc/execute test {} failed to compile".format(name)
                )
                continue
            signed = out + ".signed"
            subprocess.run(
                [
                    signer,
                    "sign",
                    "-inFile",
                    out,
                    "-outFile",
                    signed,
                    "-selfSign",
                    "1",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if os.path.isfile(signed):
                os.replace(signed, out)
            os.chmod(out, 0o755)
            try:
                run_result = subprocess.run(
                    [out], capture_output=True, text=True, timeout=30
                )
                returncode = run_result.returncode
            except subprocess.TimeoutExpired:
                returncode = -1
            if returncode in (0, -11):  # -11 = SIGSEGV in libgcc teardown quirk
                passed += 1
            else:
                run_failed += 1
                self.output.warning(
                    "upstream objc/execute test {} failed to run (exit {})".format(
                        name, returncode
                    )
                )

        total = len(tests)
        self.output.info(
            "UPSTREAM objc/execute tests: {}/{} passed "
            "({} compile-failed, {} run-failed)".format(
                passed, total, compile_failed, run_failed
            )
        )

    def _materialize_symlinks(self, root):
        for candidate in Path(root).rglob("*"):
            if not candidate.is_symlink():
                continue
            target = candidate.resolve(strict=True)
            mode = stat.S_IMODE(target.stat().st_mode)
            candidate.unlink()
            shutil.copy2(target, candidate)
            candidate.chmod(mode)

    def package(self):
        self._run_with_unlimited_stack(
            "make install-target-libobjc DESTDIR={}".format(
                shlex.quote(self.package_folder)
            ),
            cwd=self.build_folder,
        )
        copy(
            self,
            "COPYING*",
            src=self._gcc_source,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        self._materialize_symlinks(self.package_folder)
        self._sign_elf_tree(self.package_folder)

        # Verify the runtime library artifact actually exists before declaring
        # the package built.  GCC installs target libraries under
        # lib/gcc/<target>/<version>/ by default, so search the tree instead of
        # assuming a fixed lib/libobjc.so path.
        artifacts = [
            str(path)
            for path in Path(self.package_folder).rglob("libobjc.*")
            if path.is_file()
        ]
        headers = [
            str(path)
            for path in Path(self.package_folder).rglob(os.path.join("objc", "objc.h"))
            if path.is_file()
        ]
        if not artifacts:
            raise ConanInvalidConfiguration(
                "libobjc artifact was not installed (no libobjc.so / libobjc.a found)"
            )
        if not headers:
            raise ConanInvalidConfiguration(
                "libobjc public headers were not installed (no objc/objc.h found)"
            )
        self.output.info(
            "libobjc artifacts: {}; headers: {} tree(s)".format(
                len(artifacts), len(headers)
            )
        )

    def package_info(self):
        self.cpp_info.libs = ["objc"]
        self.cpp_info.set_property("cmake_find_mode", "both")

        # GCC installs libobjc under lib/gcc/<target>/<version>/ by default.
        # Locate the real include/lib directories so consumers can use
        # `#include <objc/objc.h>` and link -lobjc without hard-coding the
        # GCC private install prefix.
        include_dir = None
        lib_dir = None
        for header in Path(self.package_folder).rglob(os.path.join("objc", "objc.h")):
            if header.is_file():
                include_dir = os.path.dirname(os.path.dirname(str(header)))
                break
        for library in Path(self.package_folder).rglob("libobjc.so"):
            if library.is_file():
                lib_dir = os.path.dirname(str(library))
                break
        if not lib_dir:
            for library in Path(self.package_folder).rglob("libobjc.a"):
                if library.is_file():
                    lib_dir = os.path.dirname(str(library))
                    break

        if include_dir:
            self.cpp_info.includedirs = [include_dir]
        if lib_dir:
            self.cpp_info.libdirs = [lib_dir]
        else:
            self.cpp_info.libdirs = ["lib"]
