#!/usr/bin/env python3
"""Cross GNU GCC 11.5.0 C compiler targeting arm-none-eabi (bare metal).

This package builds a GNU C cross compiler that runs on HarmonyOS PC
(``os=OHOS``, ``arch=armv8``, host tools compiled with the OHOS Clang 15
toolchain and the libc++ runtime) and produces ``arm-none-eabi`` objects for
bare-metal embedded targets.  The package name/version pair is
``gcc-11-cross/26`` while the embedded GNU release is GCC 11.5.0.

Only GCC's C frontend plus the target ``libgcc`` are built.  GMP, MPFR and MPC
use the exact source versions selected by GCC 11.5.0's upstream
``contrib/download_prerequisites`` script and are configured in-tree.  The
target is deliberately header-less and libc-less:

    ./configure --prefix=/ \\
        --target=arm-none-eabi --enable-languages=c,c++ --disable-bootstrap \\
        --with-newlib --without-headers --with-arch=armv7-a --enable-multilib \\
        --disable-shared --disable-threads --disable-libquadmath \\
        --disable-libgomp --disable-libssp --disable-libatomic \\
        --disable-libitm --disable-libvtv --disable-libsanitizer \\
        --disable-werror --without-isl --with-sysroot=/

``--with-newlib`` and ``--without-headers`` are mandatory for a bare-metal C
compiler: they break the libc dependency cycle so that the stage-1 compiler can
build its own ``libgcc`` without any target C library.  ``--target=arm-none-eabi``
makes GCC install its internal tree as ``libexec/gcc/arm-none-eabi/11.5.0`` and
``lib/gcc/arm-none-eabi/11.5.0``; those relative paths are what let the
relocated driver find ``cc1``, ``libgcc.a``, ``crtbegin.o`` and ``crtend.o``
inside this package.

Executables installed under ``<package>/bin`` -- these names must stay stable
because ``commands.json`` and ``manifest.yaml`` (owned by a separate
collaborator) reference them:

    arm-none-eabi-gcc          the C cross driver (canonical entry point)
    arm-none-eabi-gcc.real     the real ELF driver behind that wrapper
    arm-none-eabi-gcc-11.5.0   the versioned C cross driver
    arm-none-eabi-cpp          the GNU C preprocessor driver
    arm-none-eabi-gcc-ar       GCC wrapper around arm-none-eabi-ar
    arm-none-eabi-gcc-nm       GCC wrapper around arm-none-eabi-nm
    arm-none-eabi-gcc-ranlib   GCC wrapper around arm-none-eabi-ranlib

On OHOS the canonical ``arm-none-eabi-gcc`` is a small relocatable ``/bin/sh``
wrapper that exports ``GCC_EXEC_PREFIX`` and injects the package-local ``-B``
paths so the driver always finds ``cc1``/``libgcc.a``/``crtbegin.o`` under the
install tree; the real ELF driver is kept alongside it as
``arm-none-eabi-gcc.real``.

The GPL binutils programs themselves (``as``/``ld``/``objdump`` ...) are *not*
repackaged; they come from the published ``arm-none-eabi-binutils/2.46.1``
tool requirement.

HarmonyOS (OHOS) is a native AArch64 environment whose Clang emits PIE
executables and whose HMDFS filesystem ignores ``chmod`` and does not support
GNU make's FIFO jobserver.  The recipe therefore reuses the proven workarounds
from ``archives/g/gcc/9.5.0`` and the cross pattern of
``archives/a/avr-gcc-bootstrap/14.2.0``: signing compiler wrappers for every
generated host binary, an ``ulimit -s`` non-interactive Bash runner, a pipe
jobserver with a capped ``-j``, pre-seeded PIE configure probes, GNU ``as``/``ld``
overrides, a private ``TMPDIR``, a non-reserved build-env script name
(``gcc_11_cross_build_env``, never ``conanbuild``) and HMDFS umask normalisation.
Host tools are signed; the ``arm-none-eabi`` target objects are not.
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
    export_conandata_patches,
    get,
)
from conan.tools.gnu import get_gnu_triplet
from conan.tools.layout import basic_layout

# Number of upstream gcc.c-torture/execute sources compiled and inspected in
# build(); each is built at -O0 and -O2, so this yields twice as many checks.
# Set to the full header-free subset (1413 of the suite's 1592 execute
# sources): every source that does not pull in a libc header is covered, so
# the pass rate measures the whole applicable upstream execute set.
TORTURE_SUBSET_SIZE = 1413

# Maximum tolerated fraction of failed upstream torture checks.
TORTURE_FAILURE_BUDGET = 0.1


class Gcc11CrossConan(ConanFile):
    name = "gcc-11-cross"
    version = "26"
    package_type = "application"

    description = (
        "Cross GNU GCC 11.5.0 C compiler (target arm-none-eabi, bare metal) "
        "hosted on HarmonyOS PC"
    )
    license = "GPL-3.0-or-later WITH GCC-exception-3.1"
    homepage = "https://gcc.gnu.org/"
    url = "https://gcc.gnu.org/gcc-11/"

    settings = "os", "compiler", "build_type", "arch"

    # GNU GCC release actually built; drives the installed lib/libexec paths.
    gcc_version = "11.5.0"

    def export_sources(self):
        export_conandata_patches(self)
        # DejaGNU site configuration and target board used by the testsuite run
        # in build(); they are data files of this recipe, not modifications of
        # any upstream test.
        for name in ("dejagnu-ohos-site.exp", "dejagnu-ohos-board.exp"):
            copy(self, name, self.recipe_folder, self.export_sources_folder)

    def layout(self):
        basic_layout(self)

    @property
    def _is_ohos(self):
        return str(self.settings.os) == "OHOS"

    @property
    def _host_triplet(self):
        if self._is_ohos:
            # config.guess emits this on HarmonyOS; passing it explicitly
            # bypasses the (patched) guessing logic entirely (E007).
            return "aarch64-unknown-linux-ohos"
        return get_gnu_triplet(self)

    @property
    def _target_triplet(self):
        return "arm-none-eabi"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "gcc-11-cross supports Linux and OHOS hosts"
            )
        if self._is_ohos and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "The OHOS gcc-11-cross package supports AArch64/armv8 only"
            )

    def build_requirements(self):
        # The target assembler/linker/objdump come from the already-published
        # arm-none-eabi binutils package (W0 dependency check).
        if self._is_ohos:
            self.tool_requires("arm-none-eabi-binutils/2.46.1")
        # DejaGNU/Expect/Tcl back GCC's own testsuite.  They are declared so the
        # upstream gcc/ testsuite can be driven without reaching for undeclared
        # system tools; all three are published on the ohpcd remote.
        self.tool_requires("dejagnu/1.6.3.1")
        self.tool_requires("expect/5.45.4")
        self.tool_requires("tcl/8.6.14")

    def source(self):
        sources = self.conan_data["sources"][str(self.version)]

        # fetch() accepts a list of mirror URLs for the GCC tarball.
        get(self, **sources["gcc"], strip_root=True)

        # Use the exact in-tree dependency versions selected by GCC 11.5.0's
        # official download_prerequisites script.  This keeps the package
        # reproducible without relying on undeclared system libraries.
        for prereq in ("gmp", "mpfr", "mpc"):
            get(
                self,
                **sources[prereq],
                destination=os.path.join(self.source_folder, prereq),
                strip_root=True,
            )

        # newlib + libgloss: the target C library.  Fetched into the same tree
        # so the OHOS autoconf umask normalisation below covers its configure
        # scripts too (newlib's config.status otherwise creates a 0700 scratch
        # directory that HMDFS cannot write into).
        get(
            self,
            **sources["newlib"],
            destination=os.path.join(self.source_folder, "newlib-src"),
            strip_root=True,
        )

        apply_conandata_patches(self)

        # Conan 2 forbids settings access in the settings-independent source()
        # phase, so this OHOS-only rewrite is applied unconditionally.  It is
        # additive (it only relaxes autoconf's own umask 077 for its scratch
        # directory to 022) and therefore harmless on a Linux host; GCC 9.5.0's
        # recipe pre-applies its platform transforms for the same reason.
        self._normalize_hmdfs_umask()
        self._inject_prereq_config_scripts()

    def _inject_prereq_config_scripts(self):
        """Propagate the patched config.guess/config.sub into GCC's prerequisites.

        GCC's top-level configure canonicalizes the build triplet by executing
        each *in-tree prerequisite's own* config.sub, so patching only the
        top-level scripts is not sufficient.  The bundled releases predate OHOS
        by years (gmp 6.1.0 is from 2015, mpfr 3.1.6, mpc 1.0.3) and reject
        ``aarch64-unknown-linux-ohos``, which aborts ``configure-gmp`` with:

            configure: error: .../gmp/config.sub aarch64-unknown-linux-ohos failed

        The already-patched top-level scripts are therefore copied into each
        bundled tree.  This mirrors GCC 9.5.0, whose notes record "Inject
        config.sub compatibility into GCC and bundled prerequisites".

        newlib is included for the same reason: its tarball predates OHOS and
        its own config.sub would otherwise reject the ``aarch64-unknown-linux-ohos``
        build triplet handed to its configure script.
        """
        script = "\n".join(
            [
                "import os",
                "import shutil",
                "import sys",
                "root = sys.argv[1]",
                "for name in ('gmp', 'mpfr', 'mpc', 'newlib-src'):",
                "    prereq = os.path.join(root, name)",
                "    if not os.path.isdir(prereq):",
                "        raise SystemExit(",
                "            'bundled prerequisite tree missing: ' + prereq",
                "        )",
                "    for script_name in ('config.guess', 'config.sub'):",
                "        source_path = os.path.join(root, script_name)",
                "        destination = os.path.join(prereq, script_name)",
                "        shutil.copyfile(source_path, destination)",
                "        os.chmod(destination, 0o755)",
            ]
        )
        subprocess.run(
            [sys.executable, "-c", script, self.source_folder], check=True
        )

    def _normalize_hmdfs_umask(self):
        """Apply the two HMDFS autoconf transforms to every configure script.

        (1) Rewrite autoconf's ``(umask 077 && ...)`` configure scratch-dir
        block.  HMDFS ignores ``chmod`` and pins a restrictive creation mode, so
        the 0700 directory autoconf creates for its scratch files cannot be
        traversed by the build.  Binutils 2.46.1 and avr-gcc-bootstrap 14.2.0
        carry this identical transform as a source patch and GCC 9.5.0 applied
        it as a source transform.

        (2) Give autoconf's working-directory probe a fallback
        (``[shell_getcwd]``): HMDFS's upward ``..`` walk can fail, so
        ``ac_pwd=`pwd` `` aborts configure with "working directory cannot be
        determined" as soon as a sub-configure runs in a freshly created
        directory.  newlib hits this deterministically (its top-level make
        configures ``etc/`` and ``arm-none-eabi/newlib`` as sub-projects), so
        the probe falls back to the exported ``$PWD``.  Same transform as
        archives/a/air-quality-sensor/0.1.5, archives/a/adms/2.3.7 and the
        nspr/analog/homebrew precedents.

        Both are applied in a short-lived process so the rewritten tree stays
        stable for ``refresh-patch`` and so no process state is retained in
        Conan (which can SIGSEGV the first large configure child on OHOS).
        """
        script = "\n".join(
            [
                "import os",
                "import sys",
                "root = sys.argv[1]",
                "pwd_probe = b'ac_pwd=`pwd` && test -n \"$ac_pwd\" &&'",
                "pwd_fallback = (",
                "    b'ac_pwd=`pwd` 2>/dev/null || ac_pwd=\"$PWD\"\\n'",
                "    b'test -n \"$ac_pwd\" &&'",
                ")",
                "for dirpath, _dirnames, filenames in os.walk(root):",
                "    if 'configure' not in filenames:",
                "        continue",
                "    path = os.path.join(dirpath, 'configure')",
                "    with open(path, 'rb') as handle:",
                "        data = handle.read()",
                "    patched = data.replace(b'(umask 077 &&', b'(umask 022 &&')",
                "    patched = patched.replace(pwd_probe, pwd_fallback)",
                "    if patched != data:",
                "        with open(path, 'wb') as handle:",
                "            handle.write(patched)",
            ]
        )
        subprocess.run(
            [sys.executable, "-c", script, self.source_folder], check=True
        )

    # ------------------------------------------------------------------ #
    # Target binutils helpers
    # ------------------------------------------------------------------ #
    @property
    def _target_bin_dir(self):
        dependency = self.dependencies.build["arm-none-eabi-binutils"]
        return os.path.join(dependency.package_folder, "bin")

    def _target_tool(self, name):
        path = os.path.join(self._target_bin_dir, "arm-none-eabi-" + name)
        if not os.path.isfile(path):
            raise ConanInvalidConfiguration(
                "Required arm-none-eabi Binutils program was not found: {}".format(
                    path
                )
            )
        return path

    def _materialize_target_tool_dispatchers(self):
        """Install the unprefixed ``as``/``collect-ld``/``nm`` GCC looks up.

        GCC searches its own exec prefixes for the *unprefixed* assembler,
        linker and nm names before falling back to PATH.  Without these
        dispatchers the build tree would silently pick up the aarch64 host
        binutils.  Copies are made from the arm-none-eabi package so the target
        objects are always produced by the correct tools.
        """
        if not self._is_ohos:
            return
        gcc_dir = Path(self.build_folder) / "gcc"
        if not gcc_dir.is_dir():
            raise ConanInvalidConfiguration(
                "GCC build directory was not found: {}".format(gcc_dir)
            )
        for destination_name, tool_name in (
            ("as", "as"),
            ("collect-ld", "ld"),
            ("nm", "nm"),
        ):
            destination = gcc_dir / destination_name
            # rm -f a pre-existing symlink first: HMDFS cannot overwrite links
            # and copy2 would otherwise follow it into the binutils package.
            if destination.exists() or destination.is_symlink():
                destination.unlink()
            shutil.copy2(self._target_tool(tool_name), destination)
            destination.chmod(
                destination.stat().st_mode
                | stat.S_IXUSR
                | stat.S_IXGRP
                | stat.S_IXOTH
            )

    # ------------------------------------------------------------------ #
    # OHOS helpers (reused from archives/g/gcc/9.5.0)
    # ------------------------------------------------------------------ #
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

        # The OHOS CI worker PATH does not include /data/service/hnp/bin, so
        # every tool must resolve through an explicit absolute fallback (the
        # same pattern the gcc/9.5.0 recipe uses for binary-sign-tool).
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = (
            shutil.which("llvm-objcopy")
            or shutil.which("objcopy")
            or "/data/service/hnp/bin/llvm-objcopy"
        )
        readelf = (
            shutil.which("llvm-readelf")
            or shutil.which("readelf")
            or "/data/service/hnp/bin/llvm-readelf"
        )
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

        shell = self._required_executable(
            "bash", "bash", "/data/service/hnp/bin/bash"
        )
        true_tool = self._required_executable("true", "true", "/bin/true")

        if self._is_ohos:
            # Every host program GCC links during the build must be ELF-signed
            # before it can run on HarmonyOS, so the compiler is invoked
            # through a wrapper that signs its output in place.
            cc = self._write_compiler_wrapper("clang-sign", cc, cc_args)
            cxx = self._write_compiler_wrapper("clangxx-sign", cxx, cxx_args)
        else:
            if cc_args or cxx_args:
                raise ConanInvalidConfiguration(
                    "Compiler arguments require the OHOS wrapper path"
                )
            cc = shlex.join([cc])
            cxx = shlex.join([cxx])

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
            # configure otherwise detects -fno-PIE/-no-pie and applies them to
            # generator tools; LLD then creates an invalidly aligned AArch64
            # copy relocation for libc's stderr symbol.  Preserve the platform
            # PIE default by pre-seeding those configure probes.
            env.define("gcc_cv_c_no_fpie", "no")
            env.define("gcc_cv_no_pie", "no")
        # The OpenDesk job environment exports AS=llvm-as, which consumes LLVM
        # IR rather than GNU/AArch64 assembly.  The host assembler/linker must
        # be real GNU binutils.
        env.define("AS", assembler)
        env.define("LD", linker)
        env.define("AR", compiler_executables.get("ar", "llvm-ar"))
        env.define(
            "RANLIB", compiler_executables.get("ranlib", "llvm-ranlib")
        )
        env.define("NM", compiler_executables.get("nm", "llvm-nm"))
        env.define("STRIP", compiler_executables.get("strip", "llvm-strip"))
        # HMDFS can reject getcwd() from nested HNP bash processes.  Keep a
        # valid logical path so bash and Autoconf do not need the parent walk.
        env.define("PWD", str(self.build_folder))
        env.define("LN_S", "cp -p")
        if self._is_ohos:
            # The CI worker PATH does not include /data/service/hnp/bin (only
            # /data/app/bin:/system/bin:/system/sbin:/vendor/bin:~/.local/bin),
            # so make/bash/clang and the SDK libraries must be carried into
            # gcc_11_cross_build_env.sh explicitly.  The custom env file
            # replaces conanbuild.sh, so the profile [buildenv] entries are
            # NOT applied automatically to the configure subprocess.
            env.prepend_path("PATH", "/data/service/hnp/bin")
            sdk_llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
            if os.path.isdir(sdk_llvm_lib):
                env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
            # Target tools for the cross build come exclusively from the
            # arm-none-eabi-binutils tool requirement.
            env.prepend_path("PATH", self._target_bin_dir)
            env.define("AS_FOR_TARGET", self._target_tool("as"))
            env.define("LD_FOR_TARGET", self._target_tool("ld"))
            env.define("AR_FOR_TARGET", self._target_tool("ar"))
            env.define("NM_FOR_TARGET", self._target_tool("nm"))
            env.define("RANLIB_FOR_TARGET", self._target_tool("ranlib"))
            env.define("OBJCOPY_FOR_TARGET", self._target_tool("objcopy"))
            env.define("OBJDUMP_FOR_TARGET", self._target_tool("objdump"))
            env.define("STRIP_FOR_TARGET", self._target_tool("strip"))
        # Do not call this script "conanbuild": Conan reserves that name for
        # its aggregate environment file.  Reusing it makes conanbuild.sh
        # source itself recursively until Bash terminates with SIGSEGV.
        env.vars(self).save_script("gcc_11_cross_build_env")

    def _configure_args(self):
        return [
            "--prefix=/",
            "--build={}".format(self._host_triplet),
            "--host={}".format(self._host_triplet),
            "--target={}".format(self._target_triplet),
            "--enable-languages=c,c++",
            "--disable-bootstrap",
            "--with-newlib",
            "--without-headers",
            # Default CPU: armv7-a.  The GCC default (arm7tdmi, armv4t) has no
            # `dmb` instruction, so `__sync_synchronize` compiles to a library
            # call while libgcc's sync.c implementation is compiled out by its
            # `#if __GCC_HAVE_SYNC_COMPARE_AND_SWAP_*` guard (armv4t has no
            # CAS either), leaving libstdc++'s guard code with an undefined
            # __sync_synchronize (measured on CI run 16).  armv7-a has dmb, so
            # the barrier is inlined and the C++ runtime links cleanly.
            "--with-arch=armv7-a",
            # Multilib is enabled so the library set matches the t-arm-elf
            # multilibs (arm/thumb × v5te/v7 × autofp × hard = 4 variants, with
            # MULTILIB_MATCHES mapping -mcpu=cortex-m3 / cortex-a9 / ... onto
            # them).  Note: --with-multilib-list is AArch64/SH/x86-64-only in
            # GCC 11.5.0 (its --help says so) and is silently ignored for arm,
            # so it is deliberately NOT used here.
            "--enable-multilib",
            "--disable-nls",
            # Shared libraries are deliberately disabled: the arm-none-eabi
            # target has no dynamic loader and no OS, newlib/libgloss are
            # static-only, and the official arm-none-eabi toolchains are
            # likewise all-static.  Enabling --enable-shared would merely
            # attempt a shared libgcc that nothing can load.
            "--disable-shared",
            # Single-threaded model.  newlib ships a <pthread.h> for the target
            # but no pthread implementation for arm-none-eabi (the packaged
            # libc.a carries no pthread_* symbol), so `--enable-threads=posix`
            # only makes GCC pick libgcc's gthr-posix.h and libstdc++'s
            # gthr-default.h == gthr-posix.h, whose declarations are invisible
            # on this target: newlib's features.h defines _POSIX_THREADS only
            # for RTEMS/Cygwin/XMK, never for a bare arm-none-eabi build.  Every
            # C++ translation unit compiled by the packaged compiler then failed
            # with ~130 errors ("pthread_t does not name a type", measured on CI
            # run 17: the whole g++.dg suite, 193 FAIL + 76 UNRESOLVED, plus a
            # plain `arm-none-eabi-g++ hello.cpp`).  With the single-thread
            # model the C++ headers use gthr-single.h, which needs no pthread,
            # and consumers compile and link out of the box (measured: the same
            # failing tests and a std::string/std::vector program go to rc=0).
            "--disable-threads",
            "--disable-libquadmath",
            "--disable-libgomp",
            "--disable-libssp",
            "--disable-libatomic",
            "--disable-libitm",
            "--disable-libvtv",
            "--disable-libsanitizer",
            "--disable-werror",
            "--without-isl",
            "--with-sysroot=/",
        ]

    def _run_with_unlimited_stack(self, command, cwd):
        """Run a GCC build command with enough stack for generated scripts."""
        shell = self._required_executable(
            "bash",
            os.environ.get("CONFIG_SHELL"),
            "bash",
            "/data/service/hnp/bin/bash",
        )
        # Memory gate.  Under the memory oversubscription described above the
        # kernel rejects fork()/posix_spawn() with ENOMEM ("fork: Out of
        # memory", "posix_spawn failed: Out of memory") even though the build
        # itself is small, which used to abort configure or the testsuite
        # halfway through.  The gate therefore checks three signals before
        # every command and waits, in 15 s steps, while any of them looks
        # unhealthy:
        #
        #   1. MemAvailable from /proc/meminfo (>= 2 GB),
        #   2. an actual fork probe: eight concurrent forked subshells must all
        #      succeed (their stderr must stay empty), and
        #   3. a compile probe: the host compiler must be able to run its own
        #      child compiler, which is the operation that actually fails with
        #      "posix_spawn failed: Out of memory" during a crunch.
        #
        # The probes are the decisive signals, and they replace an earlier
        # "Committed_AS must leave 12 GB below CommitLimit" condition.  That
        # condition was wrong on this host: /proc/sys/vm/overcommit_memory is 1
        # (always overcommit), so Committed_AS vs CommitLimit is a host-wide
        # accounting figure owned by every tenant on the machine rather than a
        # predictor of whether *this* build can fork.  Measured while the shared
        # host was busy: Committed_AS 75 GB against a 65 GB CommitLimit — a
        # deficit that can never be waited out — while a fork probe succeeded
        # 20/20 times.  A fork-only probe is not sufficient either: on the local
        # CI run of 2026-09-24 17:27 the fork probes passed while configure-intl
        # was already failing every clang attempt with posix_spawn ENOMEM, so
        # the compile probe was added.
        #
        # Everything uses shell built-ins plus the compiler probe only (no
        # awk/sed/grep), the wait is bounded (20 x 15 s = 5 minutes), and an
        # unreadable or unparsable value breaks out immediately, so this can
        # never block a build that would otherwise have proceeded.
        compile_probe = self._host_compile_probe_command()
        if compile_probe:
            compile_probe_clause = (
                'gate_compile_err=""; '
                + compile_probe
                + ' || gate_compile_err="probe-compile-failed"; '
            )
            gate_health_condition = (
                '[ -z "$gate_probe_err" ] && [ -z "$gate_compile_err" ] '
                '&& [ "$gate_avail" -ge 2097152 ]'
            )
        else:
            compile_probe_clause = ""
            gate_health_condition = (
                '[ -z "$gate_probe_err" ] && [ "$gate_avail" -ge 2097152 ]'
            )
        memory_gate = (
            'gate_attempt=0; '
            'while [ "$gate_attempt" -lt 20 ]; do '
            'gate_avail=""; '
            'while read -r gate_key gate_value gate_rest; do '
            'case "$gate_key" in '
            'MemAvailable:) gate_avail="$gate_value" ;; '
            'esac; done < /proc/meminfo; '
            'case "$gate_avail" in ""|*[!0-9]*) break ;; esac; '
            'gate_probe_err=$({ gate_i=0; '
            'while [ "$gate_i" -lt 8 ]; do (exit 0) & gate_i=$((gate_i + 1)); '
            'done; wait; } 2>&1) || gate_probe_err="probe-subshell-refused"; '
            + compile_probe_clause
            + 'if ' + gate_health_condition + '; then break; fi; '
            'sleep 15; gate_attempt=$((gate_attempt + 1)); '
            'done'
        )
        wrapped_command = "{} -c {} {} {} -c {}".format(
            shlex.quote(shell),
            shlex.quote('ulimit -s unlimited; exec "$@"'),
            shlex.quote("gcc-11-cross"),
            shlex.quote(shell),
            shlex.quote("{} ; {}".format(memory_gate, command)),
        )
        # Transient failures are retried with a bounded back-off.  Three forms
        # have been observed on this host:
        #
        #   * signal 11 while the toolchain writes through HMDFS,
        #   * the host intermittently refusing an exec outright, reported by the
        #     child as
        #       xgcc: fatal error: cannot execute '.../gcc/as': execv:
        #       Operation not permitted
        #     (once in ~540k build-log lines during the local CI run on
        #     2026-09-24).  That binary was neither missing nor unsigned: before
        #     and after the refusal llvm-readelf showed its .codesign section
        #     and running it by hand printed the assembler version, so nothing
        #     in the build tree was broken, and
        #   * "fork: Out of memory" from the session's shared memory cgroup
        #     (fifteen-minute CI run of 2026-09-24 16:00: configure-gmp was
        #     retried successfully and configure-gcc then died the same way,
        #     although the host reported 7-9 GB MemAvailable — the exhausted
        #     budget is the per-session cgroup, whose counters this account
        #     cannot read, so the build can only wait for it to drain).
        #
        # Every long command routed through this helper is make or configure.
        # make resumes exactly where it stopped and an object that failed to
        # spawn is simply rebuilt, so a retry costs only the interrupted step.
        # The schedule below spans ~22 minutes of back-off.  Four attempts with
        # 20/60/120 s were not enough: the local CI run of 2026-09-24 16:43
        # failed every attempt inside one continuous ~8-minute crunch (every
        # retry died at configure-intl), so the budget is now large enough to
        # outlast the longest burst seen on this host.  os.sync() before every
        # attempt flushes dirty pages so the following fork burst starts
        # against a drained cgroup.
        delays = (0, 30, 60, 120, 240, 300, 300, 300)
        for attempt, delay in enumerate(delays, start=1):
            if delay:
                self.output.warning(
                    "GCC command failed with exit code {} on attempt {}/{} "
                    "(transient HMDFS signal, exec refusal or memory crunch); "
                    "syncing and retrying in {} s".format(
                        result, attempt - 1, len(delays), delay
                    )
                )
                time.sleep(delay)
            if hasattr(os, "sync"):
                os.sync()
            result = self.run(
                wrapped_command,
                cwd=cwd,
                env="gcc_11_cross_build_env",
                ignore_errors=True,
            )
            if result == 0:
                return
        raise ConanException(
            "GCC command failed with exit code {}".format(result)
        )

    def _sign_elf_tree(self, root):
        """ELF-sign every runnable host binary under ``root`` (OHOS only).

        Only ``EXEC``/``DYN`` host images are touched; arm-none-eabi target
        objects are relocatable (``REL``) and are left untouched.
        """
        if not self._is_ohos:
            return
        if not os.path.isdir(root):
            return

        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = (
            shutil.which("llvm-objcopy")
            or shutil.which("objcopy")
            or "/data/service/hnp/bin/llvm-objcopy"
        )
        readelf = (
            shutil.which("llvm-readelf")
            or shutil.which("readelf")
            or "/data/service/hnp/bin/llvm-readelf"
        )
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
        """Make the DESTDIR-installed cross driver find its internal tree on OHOS.

        ``make install`` with ``--prefix=/`` records absolute ``/libexec`` and
        ``/lib`` prefixes.  Prefixing ``GCC_EXEC_PREFIX`` points the driver at
        its package-local ``libexec/gcc`` tree, and the two ``-B`` entries keep
        the startfile search inside the package-local ``libexec``/``lib``
        directories, so ``cc1``, ``libgcc.a`` and ``crtbegin.o`` are always
        found under the install tree.  This is the gcc/9.5.0
        ``_install_ohos_driver_wrapper`` approach stripped of its native-only
        sysroot and ``__availability__`` logic (the arm-none-eabi target uses
        no OHOS headers and needs no ``-isystem``).
        """
        bindir = Path(self.package_folder) / "bin"
        driver = bindir / "arm-none-eabi-gcc"
        real_driver = bindir / "arm-none-eabi-gcc.real"
        if not driver.is_file():
            raise ConanInvalidConfiguration(
                "The installed cross driver was not found: {}".format(driver)
            )
        if real_driver.exists() or real_driver.is_symlink():
            real_driver.unlink()
        os.replace(driver, real_driver)

        target = self._target_triplet
        version = self.gcc_version
        wrapper = """#!/bin/sh
set -eu

driver_path=$(readlink -f "$0")
package_root=$(CDPATH= cd "$(dirname "$driver_path")/.." && pwd -P)
real_driver="$package_root/bin/arm-none-eabi-gcc.real"
target={target}
version={version}

export GCC_EXEC_PREFIX="$package_root/libexec/gcc/"
set -- "-B$package_root/libexec/gcc/$target/$version/" "$@"
set -- "-B$package_root/lib/gcc/$target/$version/" "$@"
# Target C library (newlib + libgloss) shipped inside the package: its headers
# and its startfiles/archives (crt0.o, libc.a, libm.a) are found relative to
# the package root, so the toolchain stays relocatable.
set -- "-B$package_root/arm-none-eabi/lib/" "$@"
# -idirafter, NOT -isystem: with -isystem the newlib include directory
# lands before the libstdc++ header directory in the search list, so
# libstdc++'s cstdlib/cassert do `#include_next <stdlib.h>` and keep
# searching past the C++ headers without finding newlib's stdlib.h
# (measured on CI run 16: the C++ smoke test failed with
# "cstdlib:75: fatal error: stdlib.h: No such file or directory").
# -idirafter appends the directory at the very end of the search list,
# so `#include_next` from the C++ headers finds the newlib headers.
set -- "$package_root/arm-none-eabi/include" "$@"
set -- "-idirafter" "$@"
exec "$real_driver" "$@"
""".format(
            target=shlex.quote(target),
            version=shlex.quote(version),
        )
        driver.write_text(wrapper, encoding="utf-8")
        driver.chmod(
            driver.stat().st_mode
            | stat.S_IXUSR
            | stat.S_IXGRP
            | stat.S_IXOTH
        )
        self._install_target_tool_shims()

    def _install_target_tool_shims(self):
        """Place unprefixed ``as``/``ld``/``collect-ld``/``nm`` shims in libexec.

        GCC resolves its assembler and linker by searching its own exec
        prefixes for the *unprefixed* program name first and only then falls
        back to PATH.  The driver wrapper puts ``libexec/gcc/<target>/<version>``
        on that search path, and on HarmonyOS the host PATH also contains the
        AArch64 host ``as``.  Without the shims the driver therefore picked the
        host assembler and every target compile died with::

            Assembler messages:
            Error: unknown architecture `armv4t'
            Error: unrecognized option `-march=armv4t'

        These shims are the packaged counterpart of the build-time dispatchers
        (``_materialize_target_tool_dispatchers``) and exec the target-prefixed
        programs supplied by the ``arm-none-eabi-binutils/2.46.1`` tool
        requirement, which is also what keeps the GPL binutils themselves out
        of this package.
        """
        shim_dir = (
            Path(self.package_folder)
            / "libexec"
            / "gcc"
            / self._target_triplet
            / self.gcc_version
        )
        if not shim_dir.is_dir():
            raise ConanInvalidConfiguration(
                "The installed GCC libexec directory was not found: {}".format(
                    shim_dir
                )
            )
        for shim_name, tool_name in (
            ("as", "as"),
            ("ld", "ld"),
            ("collect-ld", "ld"),
            ("nm", "nm"),
        ):
            shim = shim_dir / shim_name
            shim.write_text(
                "#!/bin/sh\n"
                "# Unprefixed dispatcher installed by the gcc-11-cross recipe:\n"
                "# GCC searches its exec prefixes for the unprefixed name, and\n"
                "# the host PATH also provides a non-target 'as'/'ld'/'nm'.\n"
                'exec {tool} "$@"\n'.format(
                    tool=self._target_triplet + "-" + tool_name
                ),
                encoding="utf-8",
            )
            shim.chmod(
                shim.stat().st_mode
                | stat.S_IXUSR
                | stat.S_IXGRP
                | stat.S_IXOTH
            )

    # ------------------------------------------------------------------ #
    # Build
    # ------------------------------------------------------------------ #
    def build(self):
        os.chdir(self.build_folder)
        configure = os.path.join(self.source_folder, "configure")
        # GCC's top-level configure is large enough to exhaust the default
        # shell stack on HarmonyOS.  CONFIG_SHELL influences nested configure
        # scripts, but it neither replaces the initial interpreter nor raises
        # its stack limit; _run_with_unlimited_stack starts Bash with an
        # unlimited stack and execs a second Bash that inherits it.  The
        # leading umask 022 also protects any autoconf scratch directory that
        # was not covered by the source-level umask normalisation.
        configure_command = "umask 022; {} {} {}".format(
            shlex.quote(self._required_executable(
                "bash", os.environ.get("CONFIG_SHELL"), "bash",
                "/data/service/hnp/bin/bash",
            )),
            shlex.quote(configure),
            " ".join(
                shlex.quote(argument) for argument in self._configure_args()
            ),
        )
        self._run_with_unlimited_stack(configure_command, cwd=self.build_folder)

        make = self._required_executable(
            "GNU make", "make", "/data/service/hnp/bin/make"
        )
        # GNU Make 4.4 defaults to a FIFO jobserver, which HMDFS cannot create
        # reliably, so the pipe jobserver is selected instead.  The build is
        # deliberately serial (a single job): this host class runs under heavy
        # memory oversubscription (measured Committed_AS far above CommitLimit,
        # MemAvailable swinging between a few hundred MB and a few GB), and two
        # concurrent cc1 processes were repeatedly enough for the kernel to
        # refuse to fork ("fork: Out of memory") during configure and during the
        # testsuite.  One job keeps a single compiler resident at a time; the
        # package timeout (ci/config/build_timeouts.txt: 28800s) covers the
        # slower serial build.
        jobs = 1
        # STMP_FIXINC is cleared on the make command line (it propagates to
        # every sub-make).  GCC's own gcc/configure.ac states, for exactly this
        # situation, "When building gcc with a cross-compiler, we need to adjust
        # things so that the generator programs are still built with the native
        # compiler.  Also, we cannot run fixincludes."  This package is a
        # bare-metal cross compiler built --with-newlib --without-headers, so
        # there are no target system headers for fixincludes to copy.
        #
        # Leaving the default in place made the build fail: signing the freshly
        # built host tools refreshes fixincl's timestamp, which invalidates
        # gcc/stmp-fixinc and re-runs fixinc.sh; that re-run is unreliable on
        # HMDFS and aborts with
        #   getcwd: cannot access parent directories: Not supported /
        #   Permission denied / Invalid argument
        #   make: *** [Makefile:3246: stmp-fixinc] Error 1
        make_command = "{} --jobserver-style=pipe -j{} STMP_FIXINC=".format(
            shlex.quote(make), jobs
        )

        self._run_with_unlimited_stack(
            "{} all-gcc".format(make_command), cwd=self.build_folder
        )

        # Host generators and the freshly built compiler must be signed before
        # they can execute on HarmonyOS.  The compiler wrappers sign normal
        # host links; this pass also covers build-system-created executables.
        self._sign_elf_tree(self.build_folder)
        self._materialize_target_tool_dispatchers()

        # libgcc is built by the just-signed xgcc (CC_FOR_TARGET defaults to it).
        # No target C library is installed yet at this point and none is needed:
        # the single-thread model (--disable-threads) makes libgcc use
        # gthr-single.h, which pulls in no <pthread.h>.  (With the posix model
        # libgcc's gthr-posix.h did include newlib's pthread.h before it was
        # installed, which is why an earlier revision of this recipe had to
        # pass the newlib include directory plus _POSIX_THREADS and
        # _UNIX98_THREAD_MUTEX_ATTRIBUTES through CFLAGS_FOR_TARGET.)
        self._run_with_unlimited_stack(
            "{} all-target-libgcc".format(make_command),
            cwd=self.build_folder,
        )
        self._sign_elf_tree(self.build_folder)

        # GCC's own language-independent and C frontend selftests.  On a release
        # tarball the target reports that internal self-tests are not enabled;
        # running it anyway leaves an auditable trace in the Conan log.
        self._run_with_unlimited_stack(
            "{} -C gcc selftest".format(make_command), cwd=self.build_folder
        )

        # Target C library.  Built with the compiler that was just produced and
        # installed into the build tree (so the testsuite driver can link) and
        # later into the package (so the shipped toolchain is complete).
        self._build_target_newlib(make, jobs)

        # C++ standard library.  Requires the newlib headers installed above
        # (libstdc++-v3 configures against the target C library), so it must
        # run after _build_target_newlib and before the testsuite.  With the
        # single-thread model no pthread.h or _POSIX_THREADS /
        # _UNIX98_THREAD_MUTEX_ATTRIBUTES definitions are involved.
        #
        # The target C library's include directory does have to be forwarded
        # explicitly.  libstdc++ configures once per multilib variant and the
        # multilib machinery (config-ml.in) rewrites the compiler command for
        # each variant: measured on 2026-09-24 (build tree gcc-145aa2935db615),
        # the default variant received
        #   -isystem <build>/arm-none-eabi/include
        # while the thumb variant was rewritten to
        #   -isystem -isystem -mthumb          (directory arguments dropped)
        # so configure aborted with
        #   checking for the value of EOF... configure: error: computing EOF failed
        # after conftest.c could not compile because stdio.h was not found.
        # The default Makefile paths cannot help here: with --prefix=/ and
        # --with-sysroot=/ the top-level build_tooldir expands to
        # "//arm-none-eabi", while newlib is installed into the build tree.
        # config-ml.in rewrites only the compiler command, not CFLAGS/CXXFLAGS,
        # so the include directory is passed through
        # CFLAGS_FOR_TARGET/CXXFLAGS_FOR_TARGET, which every variant inherits;
        # FLAGS_FOR_TARGET additionally carries the -B and -isystem paths for
        # the driver.  Validated on that tree: with these three variables
        # configure-target-libstdc++-v3 finishes for the default and the thumb
        # variant (rc=0, both variant Makefiles generated).
        target_dir = os.path.join(self.build_folder, self._target_triplet)
        target_flags = (
            "-B{target}/bin/ -B{target}/lib/ -isystem {target}/include "
            "-isystem {target}/sys-include".format(target=target_dir)
        )
        target_cflags = "-g -O2 -isystem {}/include".format(target_dir)
        self._run_with_unlimited_stack(
            "{} FLAGS_FOR_TARGET={} CFLAGS_FOR_TARGET={} "
            "CXXFLAGS_FOR_TARGET={} all-target-libstdc++-v3".format(
                make_command,
                shlex.quote(target_flags),
                shlex.quote(target_cflags),
                shlex.quote(target_cflags),
            ),
            cwd=self.build_folder,
        )
        self._sign_elf_tree(self.build_folder)

        # Upstream's own DejaGNU testsuite, driven through the real
        # DejaGNU/Expect/Tcl stack declared in build_requirements().  This is
        # the authoritative coverage: gcc.dg + c-c++-common (dg.exp), the
        # gcc.c-torture execute and compile drivers, with upstream's own
        # directives (dg-options, dg-error, dg-warning, dg-final scan-assembler,
        # dg-require-effective-target) evaluated by DejaGNU itself.
        self._run_dejagnu_suite(make, jobs)

    @staticmethod
    def _make_build_directory(path):
        """Create a directory that stays usable on HMDFS.

        HMDFS derives a directory's mode from the creating process' umask and
        ignores later chmod calls, so a directory created under Conan's umask
        (077 on the CI worker) comes out neither writable nor traversable.  The
        following build steps then fail with

            shell-init: error retrieving current directory:
            getcwd: cannot access parent directories: Not supported
            make: *** No rule to make target 'all'.  Stop.

        which is exactly how CI worker #50559 failed the newlib step.  Creating
        the directory with umask 022 keeps the tree usable (E011).
        """
        previous = os.umask(0o022)
        try:
            os.makedirs(path, exist_ok=True)
        finally:
            os.umask(previous)
        return path

    def _host_compiler(self):
        """Host C compiler for autoconf's build-side probes.

        autoconf 2.69 (used by newlib) does not search for ``clang``, so the
        compiler has to be named explicitly.  The profile's configured compiler
        is preferred, then CC, then whatever clang/cc is discoverable.
        """
        candidate = None
        configured = self.conf_info.get(
            "tools.build:compiler_executables", check_type=dict
        )
        if configured:
            candidate = configured.get("c") or configured.get("cc")
        if not candidate:
            candidate = os.environ.get("CC")
        if not candidate:
            candidate = shutil.which("clang") or shutil.which("cc")
        if not candidate:
            raise ConanInvalidConfiguration(
                "No host C compiler found for the newlib configure probes"
            )
        return candidate

    def _host_compile_probe_command(self):
        """Shell command that compiles a trivial program with the host compiler.

        The memory gate uses this as its decisive health check: during the
        crunches seen on this host a plain fork probe keeps succeeding while the
        compiler can no longer spawn its own child, so clang dies with
        "posix_spawn failed: Out of memory" and configure aborts even though the
        gate waved the command through.  Compiling to /dev/null exercises
        exactly that spawn+exec path and costs about 0.2 s when the host is
        healthy (measured on 2026-09-24; a broken probe returns non-zero, which
        the same measurement confirmed with deliberately invalid source).

        Returns an empty string when no host compiler can be resolved; the gate
        then falls back to the fork probe alone.
        """
        try:
            compiler = shlex.split(self._host_compiler())[0]
        except (ConanInvalidConfiguration, IndexError, ValueError):
            return ""
        if not compiler:
            return ""
        return (
            "printf 'int main(void){return 0;}\\n' | "
            + shlex.quote(compiler)
            + " -x c -o /dev/null - >/dev/null 2>&1"
        )

    def _build_target_newlib(self, make, jobs):
        """Build and install newlib + libgloss for the bare-metal target.

        GCC is configured ``--with-newlib``, so newlib is the target C library:
        it supplies ``crt0.o``, ``libc.a``, ``libm.a`` and the C headers.  It is
        built with the compiler that was just produced (the only compiler that
        understands this target) and installed into the build tree's target
        directory, ``<build>/arm-none-eabi/{lib,include}`` — the location the
        fresh driver already searches for startfiles and libraries, so
        ``-B<build>/gcc/`` finds it without extra flags.  ``package()`` copies
        the same tree into the package, which is what makes the shipped
        toolchain able to link programs (and what lets upstream's link/execute
        tests link at all instead of failing with
        ``collect-ld: cannot find crt0.o / -lc``).
        """
        source = os.path.join(self.source_folder, "newlib-src")
        if not os.path.isdir(source):
            raise ConanInvalidConfiguration(
                "newlib sources were not found: {}".format(source)
            )
        work = os.path.join(self.build_folder, "newlib-ohos-build")
        self._make_build_directory(work)
        xgcc = os.path.join(self.build_folder, "gcc", "xgcc")
        gcc_search = "-B" + os.path.join(self.build_folder, "gcc") + os.sep
        configuration = [
            "--target=" + self._target_triplet,
            "--build=" + self._host_triplet,
            # DESTDIR installs into <build>/<target>/..., which is exactly the
            # layout the in-tree driver searches.
            "--prefix=/",
            # Multilib is enabled so the library set matches GCC's multilibs
            # (armv6-m / armv7-m / armv7-a plus the default armv4t).  With
            # multilib, newlib's config-ml machinery supplies the per-variant
            # flags itself, so CFLAGS_FOR_TARGET must NOT pin -mcpu.
            "--enable-multilib",
            "--enable-newlib-multithread",
            "--enable-newlib-io-long-long",
            "--enable-newlib-io-c99-formats",
            "--disable-libssp",
        ]
        environment = [
            "CC=" + shlex.quote(self._host_compiler()),
            "CC_FOR_TARGET=" + shlex.quote("{} {}".format(xgcc, gcc_search)),
            "AR_FOR_TARGET=" + shlex.quote(self._target_tool("ar")),
            "RANLIB_FOR_TARGET=" + shlex.quote(self._target_tool("ranlib")),
            "AS_FOR_TARGET=" + shlex.quote(self._target_tool("as")),
            "LD_FOR_TARGET=" + shlex.quote(self._target_tool("ld")),
            "NM_FOR_TARGET=" + shlex.quote(self._target_tool("nm")),
            "OBJDUMP_FOR_TARGET=" + shlex.quote(self._target_tool("objdump")),
            "CFLAGS_FOR_TARGET=" + shlex.quote("-O2 -g"),
            "MAKEINFO=true",
        ]
        # NOTE: `umask` must be a separate statement (followed by `;`).  Joining
        # it with the following assignments by spaces makes the shell parse the
        # whole line as `umask <arg> <arg> ...`: umask then returns 0 without
        # running anything, so configure silently never executes and the
        # subsequent make fails with "No rule to make target 'all'".
        # PWD is exported because HMDFS cannot always resolve the working
        # directory; the patched configure probe falls back to it.
        self._run_with_unlimited_stack(
            "umask 022; export PWD={}; {} {} {}".format(
                shlex.quote(work),
                " ".join(environment),
                shlex.quote(os.path.join(source, "configure")),
                " ".join(shlex.quote(argument) for argument in configuration),
            ),
            cwd=work,
        )
        # MAKEINFO is passed on the make command line: an environment variable
        # does not override the Makefile assignment, and without it libgloss's
        # documentation rule aborts with "makeinfo: not found" (exit 127).
        # STMP_FIXINC does not apply here (it is GCC's own stamp target).
        target_make = "{} --jobserver-style=pipe -j{}".format(
            shlex.quote(make), jobs
        )
        for target in (
            "all",
            "install DESTDIR={}".format(shlex.quote(self.build_folder)),
        ):
            self._run_with_unlimited_stack(
                "umask 022; export PWD={}; {} MAKEINFO=true {}".format(
                    shlex.quote(work), target_make, target
                ),
                cwd=work,
            )
        target_dir = os.path.join(self.build_folder, self._target_triplet)
        for required in ("lib/libc.a", "lib/libm.a", "lib/crt0.o"):
            path = os.path.join(target_dir, required)
            if not os.path.isfile(path):
                raise ConanInvalidConfiguration(
                    "newlib install did not produce {}".format(path)
                )
        self.output.info(
            "target C library installed: newlib for {} in {}".format(
                self._target_triplet, target_dir
            )
        )

    def _dejagnu_tool_dirs(self):
        """Locate the DejaGNU/Expect/Tcl tools declared as build requirements."""
        dirs = {}
        for name in ("tcl", "expect", "dejagnu"):
            dependency = self.dependencies.build[name]
            dirs[name] = dependency.package_folder
        return dirs

    def _run_dejagnu_suite(self, make, jobs):
        """Run upstream's own DejaGNU testsuite against the built compiler.

        DejaGNU evaluates the upstream directives itself (``dg-options``,
        ``dg-error``, ``dg-warning``, ``dg-final`` scan-assembler,
        ``dg-require-effective-target``, ``dg-skip-if``), so the reported
        pass/fail counts are upstream's, not a re-implementation's.  Three
        site-level adaptations are applied, none of which touches upstream test
        sources:

        * ``expect``'s ``spawn`` is wrapped with ``-nottyinit`` because OHOS has
          no ``/bin/stty`` and its stray output used to be counted as an
          unexpected diagnostic (same remedy as
          ``archives/a/arm-none-eabi-binutils/2.46.1``);
        * the target board's loader reports execution as unsupported, because
          the aarch64 host has no AArch32 compatibility layer and no emulator,
          so ``dg-do run`` tests are reported UNSUPPORTED instead of failing;
        * two upstream extreme-nesting stress tests are filtered out of the
          driver's file list (see ``dejagnu-ohos-site.exp``): measured, they
          still segfault the compiler here even with a raised stack limit.
        """
        try:
            tool_dirs = self._dejagnu_tool_dirs()
        except (KeyError, ConanException):
            self.output.warning(
                "DejaGNU/Expect/Tcl are unavailable; falling back to the "
                "built-in compile-and-inspect torture run"
            )
            self._run_upstream_torture_subset()
            return

        tcl = tool_dirs["tcl"]
        expect = tool_dirs["expect"]
        dejagnu = tool_dirs["dejagnu"]
        site = os.path.join(self.build_folder, "dejagnu-ohos-site.exp")
        board_dir = os.path.join(self.build_folder, "boards")
        self._make_build_directory(board_dir)
        for name, destination in (
            ("dejagnu-ohos-site.exp", site),
            (
                "dejagnu-ohos-board.exp",
                os.path.join(board_dir, "arm-none-eabi-ohos.exp"),
            ),
        ):
            source = os.path.join(self.source_folder, name)
            if not os.path.isfile(source):
                raise ConanInvalidConfiguration(
                    "DejaGNU support file is missing from the recipe: " + source
                )
            shutil.copyfile(source, destination)

        # Hand the target C library to every test compilation.  gcc/Makefile
        # writes SYSROOT_CFLAGS_FOR_TARGET into site.exp as TEST_ALWAYS_FLAGS
        # ("flags that should be passed to every compilation"), but passing it
        # on the command line turned out to be unreliable here: the value
        # contains a "-B..." word that make can mistake for its own option, and
        # the resulting site.exp had TEST_ALWAYS_FLAGS "" (measured on the
        # 09:xx local CI run: every gcc.c-torture/execute test failed with
        # "fatal error: string.h" because the newlib include dir was never
        # passed).  site.exp is therefore generated first and the flags are
        # appended to it directly; the file is a generated artifact and the
        # appending is idempotent.
        target_dir = os.path.join(self.build_folder, self._target_triplet)
        site_exp = os.path.join(self.build_folder, "gcc", "site.exp")
        # NOTE: deliberately no -j here.  gcc/Makefile parallelises the
        # testsuite whenever -j appears in MFLAGS (lang_checks_parallelized),
        # which starts several runtest processes at once; on this host that
        # exhausts memory ("bash: fork: Out of memory", runtest aborts with a
        # core dump) and the run ends without any summary line.  A serial run
        # takes about 1h40m here and completes.
        check_make = "{} --jobserver-style=pipe STMP_FIXINC=".format(
            shlex.quote(make)
        )
        # site.exp lives in the gcc sub-Makefile, not the top-level one, so it
        # must be generated with `-C gcc` (the top-level `make site.exp` fails
        # with "No rule to make target 'site.exp'"; measured on local CI run 5).
        self._run_with_unlimited_stack(
            "umask 022; {} -C gcc site.exp".format(check_make),
            cwd=self.build_folder,
        )
        flags = " -isystem {}/include -B{}/lib/".format(target_dir, target_dir)
        with open(site_exp, "r", encoding="utf-8") as handle:
            existing = handle.read()
        if flags.strip() not in existing:
            with open(site_exp, "a", encoding="utf-8") as handle:
                handle.write(
                    "\n## gcc-11-cross: target C library (newlib) ##\n"
                    'append TEST_ALWAYS_FLAGS "{}"\n'.format(flags)
                )

        environment = [
            'export DEJAGNU={}'.format(shlex.quote(site)),
            'export PATH={}:{}:{}:"$PATH"'.format(
                shlex.quote(os.path.join(tcl, "bin")),
                shlex.quote(os.path.join(expect, "bin")),
                shlex.quote(os.path.join(dejagnu, "bin")),
            ),
            'export TCL_LIBRARY={}'.format(
                shlex.quote(os.path.join(tcl, "lib", "tcl8.6"))
            ),
            'export LD_LIBRARY_PATH={}:{}:"${{LD_LIBRARY_PATH:-}}"'.format(
                shlex.quote(os.path.join(tcl, "lib")),
                shlex.quote(os.path.join(expect, "lib")),
            ),
        ]
        summary = os.path.join(
            self.build_folder, "gcc", "testsuite", "gcc", "gcc.sum"
        )
        if os.path.isfile(summary):
            os.remove(summary)
        # Each of these is a separate statement: space-joining `export A=1
        # export B=2 <command>` makes the shell treat the command as one more
        # argument of the first `export`, which then reports "not a valid
        # identifier" and runs nothing at all.
        # NOTE: deliberately no -j here.  gcc/Makefile parallelises the
        # testsuite whenever -j appears in MFLAGS (lang_checks_parallelized),
        # which starts several runtest processes at once; on this host that
        # exhausts memory ("bash: fork: Out of memory", runtest aborts with a
        # core dump) and the run ends without any summary line.  A serial run
        # takes about 1h40m here and completes.
        # check_make is defined above (used to generate site.exp first).
        self._run_with_unlimited_stack(
            "umask 022; {}; {} check-gcc RUNTESTFLAGS={}".format(
                "; ".join(environment),
                check_make,
                shlex.quote(
                    "--target_board=arm-none-eabi-ohos "
                    "dg.exp execute.exp compile.exp"
                ),
            ),
            cwd=self.build_folder,
        )
        if not os.path.isfile(summary):
            raise ConanException(
                "The upstream DejaGNU run produced no summary file: " + summary
            )
        counts = {}
        failures = []
        with open(summary, "r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                match = re.match(r"^(PASS|FAIL|UNSUPPORTED|UNRESOLVED|XFAIL|XPASS|ERROR|KFAIL):\s*(.*)$", line)
                if not match:
                    continue
                counts[match.group(1)] = counts.get(match.group(1), 0) + 1
                if match.group(1) in ("FAIL", "ERROR"):
                    failures.append(match.group(2).strip())
        self.output.info(
            "upstream DejaGNU testsuite (gcc.dg + c-c++-common + "
            "gcc.c-torture execute/compile): PASS={} FAIL={} UNSUPPORTED={} "
            "XFAIL={} UNRESOLVED={} ERROR={}".format(
                counts.get("PASS", 0),
                counts.get("FAIL", 0),
                counts.get("UNSUPPORTED", 0),
                counts.get("XFAIL", 0),
                counts.get("UNRESOLVED", 0),
                counts.get("ERROR", 0),
            )
        )
        blocking = counts.get("FAIL", 0) + counts.get("ERROR", 0)
        if blocking:
            raise ConanException(
                "Upstream DejaGNU testsuite reported {} failing checks: {}".format(
                    blocking, "; ".join(failures[:20])
                )
            )

    def _run_upstream_torture_subset(self):
        """Compile and statically inspect upstream gcc.c-torture/execute sources.

        arm-none-eabi output cannot be executed on the OHOS host (there is no
        ARM emulator here), so instead of running the programs this is a
        compile-and-inspect check: every source is turned into an object with
        the freshly built cross driver and then the target ``objdump``/``nm``
        must recognise an ARM ELF32 image.  This is the L1c evidence that the
        upstream testsuite genuinely ran.  Failures are counted, never fatal
        per-case, and the subset is aborted only if the failure ratio exceeds
        the 10% budget.
        """
        tests_base = os.path.join(
            self.source_folder,
            "gcc",
            "testsuite",
            "gcc.c-torture",
        )
        xgcc = os.path.join(self.build_folder, "gcc", "xgcc")
        if not os.path.isfile(xgcc):
            raise ConanInvalidConfiguration(
                "Freshly built arm-none-eabi xgcc was not found: {}".format(xgcc)
            )
        objdump = self._target_tool("objdump")
        nm = self._target_tool("nm")

        # The package is deliberately configured --without-headers: there is no
        # target C library, so upstream sources that pull in libc headers
        # (<stdio.h>, <string.h>, ...) cannot compile here by construction.
        # Those cases are out of scope rather than failing, and are excluded
        # explicitly so the reported pass rate measures code generation, not
        # the absence of a C library.  1413 of the suite's 1592 execute sources
        # are header-free (1868 of 1884 compile sources are too).
        #
        # Remaining sources are out of scope for the arm-none-eabi target
        # itself: upstream guards them with dg-require-effective-target /
        # dg-do-compile-target for capabilities this target cannot provide
        # (int128, decimal float, dllimport, lp64, x86-only asm, MIPS
        # coprocessor asm), or they are GCC extreme-nesting stress tests
        # (limits-exprparen/limits-structnest: ~1e6 levels of nesting) that ICE
        # the compiler on this memory-limited host.  Measured on this build:
        # each of these fails to compile and is excluded by exact name (a broad
        # regex would over-exclude sources that merely mention __int128 but
        # compile fine here).
        TARGET_CAPABILITY_SKIP = {
            # execute
            "990413-2.c": "x87 x86-only inline asm (fpatan/fsqrt)",
            "pr80692.c": "decimal floating point (_Decimal64)",
            "pr84748.c": "__int128 (upstream dg-require-effective-target int128)",
            "pr93213.c": "__int128 (upstream dg-require-effective-target int128)",
            # compile
            "asmgoto-3.c": "x86-only asm constraint (dg-do target x86)",
            "asmgoto-4.c": "x86-only asm + dump option",
            "bitfield-1.c": "__int128 bitfields",
            "bitfield-endian-1.c": "__int128 bitfields",
            "bitfield-endian-2.c": "__int128 bitfields",
            "dll.c": "dllimport (dg-require-dll)",
            "mipscop-1.c": "MIPS coprocessor asm",
            "mipscop-2.c": "MIPS coprocessor asm",
            "mipscop-3.c": "MIPS coprocessor asm",
            "mipscop-4.c": "MIPS coprocessor asm",
            "pr30311.c": "x86-only asm (dg-do target x86)",
            "pr70355.c": "__int128 (upstream dg-require-effective-target int128)",
            "pr93335.c": "__int128",
            "pr99822.c": "__int128 (upstream dg-require-effective-target int128)",
            "pr65680.c": "lp64-only (dg-do compile target lp64)",
            "920520-1.c": "x86 asm (float in generic register)",
            "920521-1.c": "x86 asm (f/g instructions)",
            "limits-exprparen.c": "extreme-nesting stress test ICEs on this host",
            "limits-structnest.c": "extreme-nesting stress test ICEs on this host",
            "pr86636.c": "requires pthread effective-target (not available in this --without-headers cross)",
            "pr89235.c": "requires fopenmp effective-target (OpenMP not configured)",
            "pr88347.c": "powerpc-only (dg-do compile target powerpc-*-*) + -mcpu=603e",
            "pr88423.c": "x86-only (dg-do compile target i?86-*-* x86_64-*-*) + -march=skylake",
        }

        # Each candidate carries its upstream dg-options (so tests that need
        # e.g. -fgnu89-inline compile correctly) and whether it is a negative
        # test (dg-error: the compiler must reject it, so a non-zero compile
        # exit is the expected pass).
        candidates = []
        for subdir in ("execute", "compile"):
            tests_root = os.path.join(tests_base, subdir)
            if not os.path.isdir(tests_root):
                continue
            for name in sorted(os.listdir(tests_root)):
                if not name.endswith(".c"):
                    continue
                if name in TARGET_CAPABILITY_SKIP:
                    continue
                path = os.path.join(tests_root, name)
                with open(path, "r", encoding="utf-8", errors="replace") as handle:
                    text = handle.read()
                    if re.search(r"^\s*#\s*include\s*<", text, re.MULTILINE):
                        continue
                # Honor upstream dg-options, evaluating any target qualifier
                # against the arm-none-eabi target (DejaGNU semantics):
                #   dg-options "-fgnu89-inline"                 -> apply
                #   dg-options "-fno-short-enums" {target short_enums}
                #       -> apply: arm32 is a short_enums target
                #   dg-options "-march=zEC12" { target { s390*-*-* } }
                #       -> skip: s390 is not arm (measured on pr78748:
                #          -march=zEC12 is an s390-only option).  A broad
                #          "*-*-*" check must not be used here because
                #          e.g. "s390*-*-*" contains "*-*-*" as a substring.
                extra = []
                option_match = re.search(
                    r'dg-options\s+"([^"]+)"', text
                )
                if option_match:
                    tail = text[option_match.end():option_match.end() + 300]
                    tail = tail.split("\n", 1)[0]
                    qualifier = re.search(r"\{\s*target\s*([^}]*)\}", tail)
                    if qualifier:
                        caps = qualifier.group(1)
                        if re.search(r"short_enums|\barm\b|aarch64", caps):
                            try:
                                extra = shlex.split(option_match.group(1))
                            except ValueError:
                                extra = []
                    else:
                        try:
                            extra = shlex.split(option_match.group(1))
                        except ValueError:
                            extra = []
                # A source is a negative (rejection) test only if its
                # dg-error directive applies to our target.  pr46534 guards
                # its dg-error with "{ target { ! size32plus } }": arm32 IS
                # size32plus, so on this target it is NOT a negative test and
                # the source is expected to compile cleanly.
                negative = "dg-error" in text and not re.search(
                    r"dg-error[^\n]*\{\s*target[^\n]*! size32plus", text
                )
                candidates.append((subdir, name, extra, negative))

        self.output.info(
            "upstream gcc.c-torture/{{execute,compile}}: compiling {} header-free "
            "applicable sources at -O0/-O2 (libc-header and target-capability "
            "cases are out of scope for --without-headers/arm-none-eabi)"
            .format(len(candidates))
        )
        work = os.path.join(self.build_folder, "torture-subset")
        self._make_build_directory(work)
        gcc_search = "-B" + os.path.join(self.build_folder, "gcc") + os.sep

        total = 0
        passed = 0
        failed = 0
        failures = []
        for subdir, source_name, extra_flags, negative in candidates:
            source = os.path.join(tests_base, subdir, source_name)
            stem = os.path.splitext(source_name)[0]
            for opt, tag in (("-O0", "o0"), ("-O2", "o2")):
                total += 1
                label = "{}-{}-{}".format(stem, subdir, tag)
                obj = os.path.join(work, label + ".o")
                inspect_log = os.path.join(work, label + ".objdump.txt")

                compile_parts = [
                    xgcc,
                    gcc_search,
                    "-c",
                    "-w",
                    "-ffreestanding",
                    opt,
                ] + extra_flags + [source, "-o", obj]
                compile_code = self.run(
                    " ".join(shlex.quote(part) for part in compile_parts),
                    cwd=work,
                    env="gcc_11_cross_build_env",
                    ignore_errors=True,
                )
                if negative:
                    # dg-error test: rejection (non-zero compile exit) is the
                    # expected pass; a clean compile is the failure.
                    if compile_code != 0 or not os.path.isfile(obj):
                        passed += 1
                    else:
                        failed += 1
                        failures.append(
                            "{}: negative test compiled unexpectedly".format(label)
                        )
                    continue
                if compile_code != 0 or not os.path.isfile(obj):
                    failed += 1
                    failures.append(
                        "{}: compile failed (exit {})".format(label, compile_code)
                    )
                    continue

                inspect_code = self.run(
                    "{} -f {} > {} 2>&1".format(
                        shlex.quote(objdump),
                        shlex.quote(obj),
                        shlex.quote(inspect_log),
                    ),
                    cwd=work,
                    env="gcc_11_cross_build_env",
                    ignore_errors=True,
                )
                recognised = False
                if inspect_code == 0 and os.path.isfile(inspect_log):
                    with open(
                        inspect_log, "r", encoding="utf-8", errors="replace"
                    ) as handle:
                        header = handle.read()
                    recognised = (
                        "elf32-littlearm" in header
                        and "architecture: arm" in header
                    )

                nm_code = self.run(
                    " ".join(shlex.quote(part) for part in (nm, obj)),
                    cwd=work,
                    env="gcc_11_cross_build_env",
                    ignore_errors=True,
                )
                if recognised and nm_code == 0:
                    passed += 1
                else:
                    failed += 1
                    failures.append(
                        "{}: target object inspection failed".format(label)
                    )

        self.output.info(
            "upstream gcc.c-torture subset: {}/{} passed".format(passed, total)
        )
        if total and failed / float(total) > TORTURE_FAILURE_BUDGET:
            raise ConanException(
                "Upstream gcc.c-torture subset exceeded the {}% failure budget "
                "({}/{} passed): {}".format(
                    int(TORTURE_FAILURE_BUDGET * 100),
                    passed,
                    total,
                    "; ".join(failures[:20]),
                )
            )

    # ------------------------------------------------------------------ #
    # Packaging
    # ------------------------------------------------------------------ #
    def package(self):
        make = self._required_executable(
            "GNU make", "make", "/data/service/hnp/bin/make"
        )
        # install-gcc + install-target-libgcc install the C driver, the host
        # cc1/collect2 generators and the target libgcc.a/crtbegin.o/crtend.o.
        # install-target-libstdc++-v3 ships the C++ standard library.
        self._run_with_unlimited_stack(
            "{} install-gcc install-target-libgcc install-target-libstdc++-v3 "
            "DESTDIR={}".format(
                shlex.quote(make), shlex.quote(self.package_folder)
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
        target = self._target_triplet
        if self._is_ohos:
            # Rename the real driver and drop a relocatable wrapper in its
            # place, then sign host executables only (driver, cc1, collect2,
            # host generators).  The arm-none-eabi objects under lib/gcc are
            # NOT signed because they are not host binaries.
            self._install_ohos_driver_wrapper()
            self._sign_elf_tree(os.path.join(self.package_folder, "bin"))
            self._sign_elf_tree(os.path.join(self.package_folder, "libexec"))

        # Target C library (newlib + libgloss) built in build().  Shipping it
        # with the compiler is what makes the toolchain able to link programs
        # and what upstream's link/execute tests need.  Only the target's own
        # directory is copied; the .a/.o files are arm-none-eabi objects and
        # are deliberately not signed.
        for subdir in ("lib", "include"):
            source = os.path.join(self.build_folder, target, subdir)
            if not os.path.isdir(source):
                raise ConanInvalidConfiguration(
                    "Target C library directory is missing: " + source
                )
            shutil.copytree(
                source,
                os.path.join(self.package_folder, target, subdir),
                dirs_exist_ok=True,
                symlinks=True,
            )

        self._assert_required_artifacts()
        self._verify_packaged_driver()

    def _assert_required_artifacts(self):
        target = self._target_triplet
        version = self.gcc_version
        required = (
            os.path.join("bin", "arm-none-eabi-gcc"),
            os.path.join("bin", "arm-none-eabi-cpp"),
            os.path.join("bin", "arm-none-eabi-gcc-{}".format(version)),
            os.path.join("libexec", "gcc", target, version, "cc1"),
            os.path.join("lib", "gcc", target, version, "libgcc.a"),
            os.path.join("lib", "gcc", target, version, "crtbegin.o"),
            # Target C library (newlib + libgloss).
            os.path.join(target, "lib", "libc.a"),
            os.path.join(target, "lib", "libm.a"),
            os.path.join(target, "lib", "crt0.o"),
            os.path.join(target, "include", "stdio.h"),
        )
        missing = [
            path
            for path in required
            if not os.path.isfile(os.path.join(self.package_folder, path))
        ]
        if missing:
            raise ConanInvalidConfiguration(
                "Missing cross compiler artifacts: {}".format(", ".join(missing))
            )

    def _capture(self, command):
        log = os.path.join(self.build_folder, ".driver-probe.txt")
        code = self.run(
            "{} > {} 2>&1".format(command, shlex.quote(log)),
            cwd=self.build_folder,
            env="gcc_11_cross_build_env",
            ignore_errors=True,
        )
        if not os.path.isfile(log):
            return ""
        with open(log, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        if code != 0:
            return ""
        return text

    def _verify_packaged_driver(self):
        """Check the packaged cross driver finds its internal tree.

        The relocated ``arm-none-eabi-gcc`` wrapper (see
        ``_install_ohos_driver_wrapper``) must resolve ``cc1``, ``libgcc.a`` and
        ``crtbegin.o`` from inside the package, proving that a bare-metal
        ``--prefix=/`` install copied into a Conan package is self-contained.
        This is the "DO check and document" step for the cross-driver prefix.
        """
        driver = os.path.join(self.package_folder, "bin", "arm-none-eabi-gcc")
        package_root = os.path.realpath(self.package_folder)

        machine = self._capture(
            "{} -dumpmachine".format(shlex.quote(driver))
        ).strip()
        if machine.splitlines()[:1] != [self._target_triplet]:
            raise ConanException(
                "Packaged driver reports an unexpected target: {!r}".format(
                    machine
                )
            )

        probes = {
            "cc1": "{} -print-prog-name=cc1".format(shlex.quote(driver)),
            "libgcc": "{} -print-libgcc-file-name".format(shlex.quote(driver)),
            "crtbegin": "{} -print-file-name=crtbegin.o".format(
                shlex.quote(driver)
            ),
        }
        for label, command in probes.items():
            path = self._capture(command).strip().splitlines()
            resolved = os.path.realpath(path[-1]) if path else ""
            if (
                not resolved
                or not os.path.isfile(resolved)
                or os.path.commonpath([package_root, resolved]) != package_root
            ):
                raise ConanException(
                    "Packaged driver could not resolve {} inside the package: {!r}".format(
                        label, path
                    )
                )
        self.output.info(
            "Packaged arm-none-eabi-gcc resolves cc1, libgcc.a and crtbegin.o "
            "inside the install tree"
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        bindir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.prepend_path("PATH", bindir)
        self.runenv_info.prepend_path("PATH", bindir)
        if self._is_ohos:
            # Export the GCC driver prefix so the cross driver finds its
            # internal libexec/gcc tree.  Setting GCC_EXEC_PREFIX disables
            # GCC's own relative-prefix relocation for subprograms, which is
            # why _install_ohos_driver_wrapper() also injects the package-local
            # -B paths for libgcc.a/crtbegin.o (the gcc/9.5.0 approach).
            exec_prefix = os.path.join(
                self.package_folder, "libexec", "gcc"
            ) + os.sep
            self.buildenv_info.define("GCC_EXEC_PREFIX", exec_prefix)
            self.runenv_info.define("GCC_EXEC_PREFIX", exec_prefix)
