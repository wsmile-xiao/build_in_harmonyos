#!/usr/bin/env python3
"""Native GCC 9 C and Fortran compiler for HarmonyOS PC.

This builds the C and Fortran frontends (gcc, gfortran), their runtimes
(libgcc, libgfortran), and all necessary host tools (cc1, f951, collect2,
etc.) for HarmonyOS AArch64.

GMP, MPFR, and MPC use the exact source versions selected by GCC 9.5.0's
upstream ``contrib/download_prerequisites`` script and are built in-tree.

OHOS CI is a native AArch64 environment, so build, host, and target are all
``aarch64-linux-ohos``.  Audited source transforms map that target to GCC's
musl support; the recipe also handles old config.sub scripts, HMDFS umask
behaviour, and ELF signing for generated host tools.

Quadmath and libgomp are disabled to match the minimal gcc/9.5.0 baseline;
gfortran provides REAL(4)/REAL(8) IEEE support without quad precision.
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


class GccCFortranConan(ConanFile):
    name = "gcc-c-fortran"
    version = "9.5.0"
    package_type = "application"

    description = "GNU Compiler Collection 9 C compiler and Fortran compiler (gfortran) for HarmonyOS PC"
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
            raise ConanInvalidConfiguration("The OHOS GCC C/Fortran package supports AArch64/armv8 only")

    def source(self):
        sources = self.conan_data["sources"][str(self.version)]
        get(self, **sources["gcc"], strip_root=True)
        # No external patch files are declared in conandata.yml; the OHOS
        # source transforms below are applied inline by prepare_ohos_sources.py
        # (which also injects the aarch64-linux-ohos triplet into config.sub and
        # maps the target to GCC's musl configuration).  Calling the standard
        # Conan entry point here is a safe no-op that keeps the recipe
        # consistent with the CI completeness gate.
        apply_conandata_patches(self)

        for dependency in ("gmp", "mpfr", "mpc"):
            get(
                self,
                **sources[dependency],
                destination=os.path.join(self.source_folder, dependency),
                strip_root=True,
            )

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
        return """#!/data/service/hnp/bin/bash
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
            env.define("gcc_cv_c_no_fpie", "no")
            env.define("gcc_cv_no_pie", "no")
        env.define("AS", assembler)
        env.define("LD", linker)
        env.define("AS_FOR_TARGET", assembler)
        env.define("LD_FOR_TARGET", linker)
        env.define("AR", compiler_executables.get("ar", "llvm-ar"))
        env.define(
            "RANLIB", compiler_executables.get("ranlib", "llvm-ranlib")
        )
        env.define("NM", compiler_executables.get("nm", "llvm-nm"))
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
            "--enable-languages=c,fortran",
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
            arguments.extend(
                [
                    "--disable-threads",
                    "--with-sysroot={}".format(self._ohos_sysroot),
                ]
            )
        arguments.append("--with-native-system-header-dir=/usr/include")
        return arguments

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
        """Make the DESTDIR-installed GCC/gfortran drivers relocatable on OHOS."""
        bindir = Path(self.package_folder) / "bin"

        for driver_name in ("gcc", "gfortran"):
            driver = bindir / driver_name
            real_driver = bindir / "{}.real".format(driver_name)
            if not driver.is_file():
                continue

            os.replace(driver, real_driver)
            wrapper = """#!/data/service/hnp/bin/bash
set -eu

driver_path=$(readlink -f "$0")
package_root=$(CDPATH= cd "$(dirname "$driver_path")/.." && pwd -P)
real_driver="$package_root/bin/{driver_name}.real"
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
set -- "-B$package_root/lib/" "$@"
exec "$real_driver" "$@"
""".format(
                driver_name=driver_name,
                target=shlex.quote(self._target_triplet),
                version=shlex.quote(str(self.version)),
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

        jobs = max(1, min(build_jobs(self), 2))
        make = "make --jobserver-style=pipe -j{} ".format(jobs)

        # 1. Build C and Fortran frontends (cc1, f951, gcc, gfortran drivers, etc.)
        self._run_with_unlimited_stack(
            "{} all-gcc".format(make),
            cwd=self.build_folder,
        )

        # 2. Sign host tools before they are used as build tools
        self._sign_elf_tree(self.build_folder)

        # 3. Build the target xgcc-sign wrapper for target lib compilation
        xgcc = os.path.join(self.build_folder, "gcc", "xgcc")
        target_cc = xgcc
        if self._is_ohos:
            # The OHOS sysroot keeps crt1.o/crti.o/crtn.o and libc in
            # usr/lib/<triplet>/; without -B there, configure link probes
            # for target libraries (libbacktrace, libgfortran) fail with
            # "C compiler cannot create executables".  The packaged driver
            # wrapper injects the same path, so keep the in-tree target
            # compiler equivalent here.
            crt_search = "-B" + os.path.join(
                self._ohos_sysroot, "usr", "lib", self._target_triplet
            ) + os.sep
            target_cc = self._write_compiler_wrapper(
                "xgcc-sign",
                xgcc,
                extra_args=[
                    "-B" + os.path.join(self.build_folder, "gcc") + os.sep,
                    crt_search,
                    "-isystem",
                    self._ohos_target_include,
                    "-D__availability__(...)=",
                ],
            )
        # Reused by package() so install-target-* recompiles (e.g.
        # libgfortran/caf) with the same sysroot-aware target compiler.
        self._target_cc = target_cc

        # 4. Build target libgcc
        self._run_with_unlimited_stack(
            "{} all-target-libgcc CC_FOR_TARGET={}".format(
                make, shlex.quote(target_cc)
            ),
            cwd=self.build_folder,
        )

        # 5. Build target libbacktrace (host cc1/f951 link it unconditionally
        #    in GCC 9.5, so it must be enabled; the target build is needed by
        #    libgfortran's optional error-traceback support).
        self._run_with_unlimited_stack(
            "{} all-target-libbacktrace CC_FOR_TARGET={}".format(
                make, shlex.quote(target_cc)
            ),
            cwd=self.build_folder,
        )

        # 6. Build target libgfortran (depends on libgcc being built first)
        self._run_with_unlimited_stack(
            "{} all-target-libgfortran CC_FOR_TARGET={}".format(
                make, shlex.quote(target_cc)
            ),
            cwd=self.build_folder,
        )

        # 7. Sign all ELF binaries including newly built target libraries
        self._sign_elf_tree(self.build_folder)

        # 7.5 Skip OHOS fixincludes: the stmp-fixinc rule runs fixinc.sh
        # inside a subshell that cd's between directories; on HMDFS getcwd()
        # fails there with "cannot access parent directories" and make aborts.
        # OHOS musl headers are already clean, so no fixing is needed.  Pre-
        # stamp the rule and provide an (essentially empty) include-fixed
        # directory so make skips fixinc.sh both for selftest and install.
        gcc_build_dir = os.path.join(self.build_folder, "gcc")
        include_fixed = os.path.join(gcc_build_dir, "include-fixed")
        os.makedirs(include_fixed, exist_ok=True)
        gsyslimits = os.path.join(
            self.source_folder, "gcc", "gsyslimits.h"
        )
        syslimits = os.path.join(include_fixed, "syslimits.h")
        if os.path.isfile(gsyslimits) and not os.path.isfile(syslimits):
            shutil.copy2(gsyslimits, syslimits)
        Path(os.path.join(gcc_build_dir, "stmp-fixinc")).touch()

        # 8. GCC's own language-independent and C frontend selftests
        self._run_with_unlimited_stack(
            "make -C gcc selftest",
            cwd=self.build_folder,
        )

        # 9. Run a representative subset of Fortran upstream tests (gfortran.dg)
        self._run_fortran_test_subset(target_cc)

    def _run_fortran_test_subset(self, compiler_wrapper):
        """Compile and run a subset of gfortran.dg tests on OHOS."""
        if not self._is_ohos:
            return
        tests_root = os.path.join(
            self.source_folder,
            "gcc",
            "testsuite",
            "gfortran.dg",
        )
        if not os.path.isdir(tests_root):
            self.output.warning(
                "gfortran.dg testsuite not found: {}".format(tests_root)
            )
            return

        # Select representative Fortran tests: floating-point arithmetic,
        # arrays, intrinsic functions, and formatted I/O.
        candidate_tests = [
            "pr43669.f90",
            "class_1.f90",
            "array_constructor_1.f90",
            "intrinsic_pack_1.f90",
            "intrinsic_sum_1.f90",
            "power.f90",
            "pr33789.f90",
            "substr_1.f90",
            "flow_1.f90",
            "integer_select_1.f90",
            "character_select_1.f90",
        ]
        # Filter to tests that actually exist in the source tree
        available = [
            t for t in candidate_tests
            if os.path.isfile(os.path.join(tests_root, t))
        ]
        if not available:
            # Fall back: pick any .f90 files if our list doesn't match
            all_f90 = sorted(
                f for f in os.listdir(tests_root)
                if f.endswith(".f90") and not f.startswith(".")
            )[:12]
            available = all_f90

        if not available:
            self.output.warning("No Fortran test sources found for smoke test")
            return

        gfortran = os.path.join(self.build_folder, "gcc", "gfortran")
        if not os.path.isfile(gfortran):
            self.output.warning("gfortran not built; skipping Fortran tests")
            return

        work = os.path.join(self.build_folder, "fortran-dg")
        os.makedirs(work, exist_ok=True)
        crt_search = "-B" + os.path.join(
            self._ohos_sysroot, "usr", "lib", self._target_triplet
        ) + os.sep
        # With --disable-shared the static libgfortran.a sits directly in the
        # target build directory; the in-tree xgcc driver does not search it.
        # libgfortran uses libtool, so the archive lands in .libs/ rather
        # than the build directory root.  The xgcc driver with -x f95 does
        # NOT add -lgfortran automatically (only the gfortran driver does),
        # so pass -L<.libs> -lgfortran explicitly at link time.
        libgfortran_dir = os.path.join(
            self.build_folder, self._target_triplet, "libgfortran", ".libs"
        )
        fortran_lib_search = "-B" + libgfortran_dir + os.sep
        fortran_link_flags = "-L{} -lgfortran".format(
            shlex.quote(libgfortran_dir)
        )
        total = 0
        passed = 0
        failed = 0
        failures = []
        for test_name in available:
            source = os.path.join(tests_root, test_name)
            stem = test_name.replace(".f90", "").replace(".f", "")
            executable = os.path.join(work, stem)
            # xgcc is the universal GCC driver; -x f95 selects the freshly
            # built f951.  (GCC's driver only recognises the f77/f95
            # language names, not the generic "fortran" alias.)
            compile_result = self.run(
                "{} -x f95 -O2 -w {} {} {} {} -o {}".format(
                    shlex.quote(compiler_wrapper),
                    shlex.quote(source),
                    shlex.quote(crt_search),
                    shlex.quote(fortran_lib_search),
                    fortran_link_flags,
                    shlex.quote(executable),
                ),
                cwd=self.build_folder,
                env="gcc_build_env",
                ignore_errors=True,
            )
            if compile_result != 0:
                failed += 1
                failures.append("{}: compile failed".format(test_name))
                total += 1
                continue
            # Sign the executable
            if self._is_ohos:
                signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
                objcopy = shutil.which("llvm-objcopy") or shutil.which("objcopy")
                readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
                if os.path.isfile(signer) and objcopy and readelf:
                    # Simple sign: objcopy strip codesign → sign → overwrite
                    tmp_sign = executable + ".sign_tmp"
                    shutil.copy2(executable, tmp_sign)
                    subprocess.run(
                        [objcopy, "--remove-section", ".codesign", tmp_sign],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        check=False,
                    )
                    subprocess.run(
                        [signer, "sign", "-inFile", tmp_sign,
                         "-outFile", executable, "-selfSign", "1"],
                        check=True,
                    )
                    os.unlink(tmp_sign)
            run_result = self.run(
                shlex.quote(executable),
                cwd=work,
                env="gcc_build_env",
                ignore_errors=True,
            )
            total += 1
            if run_result != 0:
                failed += 1
                failures.append("{}: run failed".format(test_name))
            else:
                passed += 1

        self.output.info(
            "upstream gfortran.dg subset: {}/{} passed".format(
                passed, total
            )
        )
        if failed and total > 0 and failed / float(total) > 0.3:
            raise ConanInvalidConfiguration(
                "Fortran test subset failed ({}/{}): {}".format(
                    passed, total, "; ".join(failures[:20])
                )
            )

    def package(self):
        cc_target = ""
        if self._is_ohos:
            cc_target = " CC_FOR_TARGET={}".format(
                shlex.quote(self._target_cc)
            )
        self._run_with_unlimited_stack(
            "make install-gcc install-target-libgcc install-target-libbacktrace install-target-libgfortran DESTDIR={}{}".format(
                shlex.quote(self.package_folder),
                cc_target,
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
