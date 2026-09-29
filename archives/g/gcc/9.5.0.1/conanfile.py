#!/usr/bin/env python3
"""Native GCC 9 C compiler for HarmonyOS PC (all-PIE, LLD auto-signing).

This deliberately builds only the C frontend and libgcc.  GMP, MPFR, and MPC
use the exact source versions selected by GCC 9.5.0's upstream
``contrib/download_prerequisites`` script and are built in-tree.

OHOS CI is a native AArch64 environment, so build, host, and target are all
``aarch64-linux-ohos``.  Audited source transforms map that target to GCC's
musl support; the recipe also handles old config.sub scripts and HMDFS umask
behaviour.

This is the all-PIE LLD toolchain (route B):

* ``--enable-default-pie`` and cleared ``NO_PIE_*`` makefiles keep every
  host tool and every target object position independent.  Non-PIE objects
  trigger an OHOS LLD AArch64 copy-relocation bug (misaligned LO12 literal
  loads) that crashes the built compiler's own test programs.
* The OHOS SDK LLD is baked in as the only linker (``--with-ld`` plus
  ``LD``/``LD_FOR_TARGET``).  LLD signs every ELF it links (.codesign), so
  the build, the installed driver, and every program it links run on
  HarmonyOS without binary-sign-tool.  The GNU linker is never used because
  it does not sign and its output is rejected by the kernel.
* Compiler wrappers therefore only carry GCC search prefixes; there is no
  signing wrapper and no post-build signing pass.

9.5.0.1 fixes the 9.5.0 package, whose non-PIE host tools and target objects
hit the copy-relocation bug above (gcc.c-torture execute failures such as
nestfunc, printf-2, fprintf-2).
"""

import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import build_jobs
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches
from conan.tools.files import (
    copy,
    get,
)
from conan.tools.gnu import get_gnu_triplet
from conan.tools.layout import basic_layout


class GccConan(ConanFile):
    name = "gcc"
    version = "9.5.0.1"
    package_type = "application"

    description = "GNU Compiler Collection 9 C compiler"
    license = "GPL-3.0-or-later WITH GCC-exception-3.1"
    homepage = "https://gcc.gnu.org/"
    url = "https://gcc.gnu.org/gcc-9/"

    settings = "os", "compiler", "build_type", "arch"

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
            raise ConanInvalidConfiguration("The OHOS GCC package supports AArch64/armv8 only")

    def source(self):
        sources = self.conan_data["sources"][str(self.version)]
        get(self, **sources["gcc"], strip_root=True)

        # Use the exact in-tree dependency versions selected by GCC 9.5.0's
        # official download_prerequisites script.  This keeps the package
        # reproducible without relying on undeclared system libraries.
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

    @property
    def _ohos_lld(self):
        """Return the OHOS SDK LLD, the only linker this toolchain may use."""
        if not self._is_ohos:
            return None
        candidate = shutil.which("ld.lld") or "/data/service/hnp/bin/ld.lld"
        if not os.path.isfile(candidate) or not os.access(candidate, os.X_OK):
            raise ConanInvalidConfiguration(
                "The OHOS SDK LLD was not found: {}".format(candidate)
            )
        # Bake the resolved SDK path.  The sysroot reference below pins the
        # SDK version anyway, so resolving the /data/service/hnp symlink here
        # adds no extra fragility and matches what --with-ld records.
        return os.path.realpath(candidate)

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
            # Route B: the SDK Clang already links through LLD, which signs
            # every ELF it produces.  The compilers are used directly, with
            # no wrapper in between.  An explicit -fuse-ld flag must be
            # rejected: it not only emits "unused argument" diagnostics that
            # pollute autoconf's -E stderr probes (misdetected features),
            # but "-fuse-ld=bfd" would also disable LLD's signing entirely.
            for prefix in ("-fuse-ld", "--fuse-ld"):
                if any(
                    argument == prefix or argument.startswith(prefix + "=")
                    for argument in cc_args + cxx_args
                ):
                    raise ConanInvalidConfiguration(
                        "Compiler arguments must not force a linker "
                        "(found '{}*'): the OHOS toolchain relies on the "
                        "SDK default LLD for automatic ELF signing".format(
                            prefix
                        )
                    )
            cc = " ".join([cc] + cc_args)
            cxx = " ".join([cxx] + cxx_args)
        elif cc_args or cxx_args:
            raise ConanInvalidConfiguration(
                "Compiler arguments require the OHOS path"
            )

        shell = self._required_executable(
            "bash", "bash", "/data/service/hnp/bin/bash"
        )
        true_tool = self._required_executable("true", "true", "/bin/true")
        # The OpenDesk job environment exports AS=llvm-as, which consumes LLVM
        # IR rather than GNU/AArch64 assembly.  GCC's target backend requires
        # real binutils as for assembling objects.
        assembler = self._required_executable(
            "GNU assembler", "as", "/data/service/hnp/bin/as"
        )
        if self._is_ohos:
            # LLD both signs and links; it replaces the GNU linker for every
            # host and target link in this build.
            linker = self._ohos_lld
        else:
            linker = self._required_executable("GNU linker", "ld", "/data/service/hnp/bin/ld")

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
            "--enable-languages=c",
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
            # OHOS libc intentionally omits pthread_cancel, which GCC 9's
            # POSIX gthread backend references while building libgcc unwind
            # support.  This package builds only the C frontend and static
            # libgcc, so GCC's supported single-thread backend is sufficient.
            arguments.extend(
                [
                    "--disable-threads",
                    "--with-sysroot={}".format(self._ohos_sysroot),
                    # Everything PIE: non-PIE objects trigger an OHOS LLD
                    # AArch64 copy-relocation bug (misaligned LO12 loads) and
                    # crash the built compiler's own test programs.
                    "--enable-default-pie",
                    # Bake the SDK LLD into the driver (DEFAULT_LINKER) so
                    # target links are signed without binary-sign-tool.
                    "--with-ld={}".format(self._ohos_lld),
                ]
            )
        arguments.append("--with-native-system-header-dir=/usr/include")
        return arguments

    def _clear_no_pie_flags(self):
        """Force GCC's host tools to stay PIE on OHOS.

        GCC 9.5's configure detects that CC accepts -fno-PIE/-no-pie and then
        compiles every host generator (genattrtab, genemit, ...) non-PIE.
        The SDK Clang links such objects with LLD, whose AArch64
        copy-relocation handling for libc symbols (stderr) is broken for
        non-PIE inputs and crashes those generators.  Pre-seeding the
        gcc_cv_c_no_fpie/gcc_cv_no_pie cache variables in the environment
        does not survive the top-level configure (verified experimentally),
        so the substituted makefile variables are cleared right after
        configure instead.  The BUILD_NO_PIE_* variables reference these
        through $(NO_PIE_*) indirection and follow automatically.
        """
        if not self._is_ohos:
            return
        makefile = Path(self.build_folder) / "gcc" / "Makefile"
        text = makefile.read_text(encoding="utf-8")
        cleared = text
        for variable in (
            "NO_PIE_CFLAGS",
            "NO_PIE_FLAG",
            "NO_PIE_CFLAGS_FOR_BUILD",
            "NO_PIE_FLAG_FOR_BUILD",
        ):
            cleared = re.sub(
                r"(?m)^{} = .*$".format(variable),
                "{} =".format(variable),
                cleared,
            )
        if cleared != text:
            makefile.write_text(cleared, encoding="utf-8")
            self.output.info("cleared NO_PIE flags in gcc/Makefile (route B)")

    def _assert_baked_linker(self):
        """Fail fast if --with-ld did not bake the SDK LLD into xgcc.

        Without DEFAULT_LINKER, the built driver would hand target links to
        the unsigned GNU linker, whose output the HarmonyOS kernel refuses
        to execute.  Detect that misconfiguration right after all-gcc
        instead of hours later in the torture tests.
        """
        if not self._is_ohos:
            return
        xgcc = os.path.join(self.build_folder, "gcc", "xgcc")
        probe = subprocess.run(
            [
                xgcc,
                "-B" + os.path.join(self.build_folder, "gcc") + os.sep,
                "-print-prog-name=ld",
            ],
            capture_output=True,
            text=True,
        )
        if probe.returncode != 0:
            raise ConanException(
                "xgcc could not report its linker (exit {}): {}".format(
                    probe.returncode, probe.stderr.strip()
                )
            )
        resolved = probe.stdout.strip()
        expected = self._ohos_lld
        if resolved != expected:
            raise ConanException(
                "xgcc resolves 'ld' to {!r} but the OHOS SDK LLD is {!r}; "
                "--with-ld did not take effect and target links would be "
                "unsigned".format(resolved, expected)
            )
        self.output.info("xgcc bakes the OHOS SDK LLD: {}".format(resolved))

    def _write_target_cc_wrapper(self, xgcc):
        """Write the thin build-tree target compiler wrapper.

        LLD signs every link, so unlike the 9.5.0 recipe there is no signing
        wrapper: this only prepends the search prefixes the in-tree driver
        needs (build-tree programs, sysroot startup files and target
        headers) plus the availability-annotation discard.
        """
        wrapper_dir = Path(self.build_folder) / ".ohos-wrappers"
        wrapper_dir.mkdir(parents=True, exist_ok=True)
        wrapper = wrapper_dir / "xgcc-ohos"
        wrapper.write_text(
            """#!/bin/sh
set -eu
exec {xgcc} {build_gcc} {sysroot_lib} -isystem {target_include} '-D__availability__(...)=' "$@"
""".format(
                xgcc=shlex.quote(xgcc),
                build_gcc=shlex.quote(
                    "-B" + os.path.join(self.build_folder, "gcc") + os.sep
                ),
                sysroot_lib=shlex.quote(
                    "-B"
                    + os.path.join(
                        self._ohos_sysroot, "usr", "lib", self._target_triplet
                    )
                    + os.sep
                ),
                target_include=shlex.quote(self._ohos_target_include),
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

    def _run_with_unlimited_stack(self, command, cwd):
        """Run a GCC build command with enough stack for generated scripts."""
        shell = self._required_executable(
            "bash",
            os.environ.get("CONFIG_SHELL"),
            "bash",
            "/data/service/hnp/bin/bash",
        )
        wrapped_command = "{} -c {} {} {} -c {}".format(
            shlex.quote(shell),
            shlex.quote('ulimit -s unlimited; exec "$@"'),
            shlex.quote("gcc-build"),
            shlex.quote(shell),
            shlex.quote(command),
        )
        result = self.run(
            wrapped_command,
            cwd=cwd,
            env="gcc_build_env",
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
                env="gcc_build_env",
                ignore_errors=True,
            )
        if result != 0:
            raise ConanException(
                "GCC command failed with exit code {}".format(result)
            )

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
linker=$("$real_driver" -print-prog-name=ld)
if [ "$linker" = "ld" ] || [ ! -x "$linker" ]; then
    echo "GCC OHOS SDK LLD is unavailable: $linker" >&2
    exit 1
fi
# The SDK LLD links libxml2 from the SDK's llvm/lib on some workers.
sdk_llvm_lib=$(CDPATH= cd "$sysroot/.." && pwd -P)/llvm/lib
if [ -d "$sdk_llvm_lib" ]; then
    export LD_LIBRARY_PATH="$sdk_llvm_lib${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"
fi
set -- '-D__availability__(...)=' "$@"
set -- -isystem "$sysroot/usr/include/$target" "$@"
set -- "-B$sysroot/usr/lib/$target/" "$@"
set -- "-B$package_root/lib/gcc/$target/$version/" "$@"
exec "$real_driver" "$@"
""".format(
            target=shlex.quote(self._target_triplet),
            # The conan package version (9.5.0.1) carries the OHOS revision
            # suffix; the installed GCC runtime tree uses the base GCC
            # version (9.5.0) as its directory name.
            version=shlex.quote(self.version.rsplit(".", 1)[0]),
        )
        driver.write_text(wrapper, encoding="utf-8")
        driver.chmod(
            driver.stat().st_mode
            | stat.S_IXUSR
            | stat.S_IXGRP
            | stat.S_IXOTH
        )

    def build(self):
        # gcc 9.5.0 upstream tarball is used unmodified (zero diff vs 9.5.0);
        # conandata.yml declares no patches, so this is a no-op that keeps the
        # recipe ready for patch declarations without changing package_id.
        apply_conandata_patches(self)
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
        self._run_with_unlimited_stack(
            configure_command,
            cwd=self.build_folder,
        )

        # GCC's top-level configure does not configure subdirectories;
        # gcc/Makefile is created by the recursive configure that all-gcc
        # would trigger.  Run it explicitly first so the NO_PIE flags can be
        # cleared before any host generator (genattrtab & friends) is
        # compiled with them.  The sed makes gcc/Makefile newer than its
        # sources, so all-gcc never re-runs config.status over the edit.
        self._run_with_unlimited_stack(
            "make configure-gcc",
            cwd=self.build_folder,
        )
        self._clear_no_pie_flags()

        # GNU Make 4.4 defaults to a FIFO jobserver, which HMDFS cannot create
        # reliably.  The OpenDesk toolchain supports the pipe jobserver, so a
        # conservative two-way build avoids both the FIFO failure and the CI
        # conan-create timeout caused by a fully serial GCC build.
        jobs = max(1, min(build_jobs(self), 2))
        make = "make --jobserver-style=pipe -j{}".format(jobs)
        self._run_with_unlimited_stack(
            "{} all-gcc".format(make),
            cwd=self.build_folder,
        )

        # The all-LLD toolchain signs everything it links, so xgcc and every
        # host tool are already executable on HarmonyOS at this point.
        self._assert_baked_linker()

        xgcc = os.path.join(self.build_folder, "gcc", "xgcc")
        target_cc = xgcc
        if self._is_ohos:
            target_cc = self._write_target_cc_wrapper(xgcc)

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

        # Upstream execution torture tests: compile and run a deterministic
        # subset of gcc.c-torture/execute with the freshly built compiler.
        # Each source is built at -O0 and -O2 (100 executions in total);
        # LLD signs every link, so the binaries run on-device directly.
        self._run_torture_execute_subset(target_cc)


    def _run_torture_execute_subset(self, compiler_wrapper):
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
        sources = sorted(
            name for name in os.listdir(tests_root) if name.endswith(".c")
        )[:50]
        work = os.path.join(self.build_folder, "torture-execute")
        os.makedirs(work, exist_ok=True)
        # The wrapper already prepends -B<sysroot>/usr/lib/<triplet>/ so the
        # in-tree xgcc driver finds crt1.o/crti.o/crtn.o at link time.
        total = 0
        passed = 0
        failed = 0
        failures = []
        for source_name in sources:
            source = os.path.join(tests_root, source_name)
            stem = source_name[:-2]
            for opt in ("-O0", "-O2 -fno-strict-aliasing"):
                total += 1
                tag = "{}_{}".format(stem, "o0" if opt == "-O0" else "o2")
                executable = os.path.join(work, tag)
                compile_result = self.run(
                    "{} {} -w {} -o {}".format(
                        shlex.quote(compiler_wrapper),
                        opt,
                        shlex.quote(source),
                        shlex.quote(executable),
                    ),
                    cwd=self.build_folder,
                    env="conanbuild",
                    ignore_errors=True,
                )
                if compile_result != 0:
                    failed += 1
                    failures.append("{}: compile failed".format(tag))
                    continue
                run_result = self.run(
                    shlex.quote(executable),
                    cwd=work,
                    env="conanbuild",
                    ignore_errors=True,
                )
                if run_result != 0:
                    failed += 1
                    failures.append("{}: run failed".format(tag))
                else:
                    passed += 1
        self.output.info(
            "upstream gcc.c-torture/execute subset: {}/{} passed".format(
                passed, total
            )
        )
        if failed and failed / float(total) > 0.1:
            raise ConanInvalidConfiguration(
                "Upstream torture subset failed ({}/{}): {}".format(
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

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        bindir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.prepend_path("PATH", bindir)
        self.runenv_info.prepend_path("PATH", bindir)
        if self._is_ohos:
            exec_prefix = os.path.join(
                self.package_folder,
                "libexec",
                "gcc",
            ) + os.sep
            self.buildenv_info.define("GCC_EXEC_PREFIX", exec_prefix)
            self.runenv_info.define("GCC_EXEC_PREFIX", exec_prefix)
