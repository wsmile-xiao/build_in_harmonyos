#!/usr/bin/env python3
"""GNU Modula-2 runtime libraries for HarmonyOS PC (aarch64).

Builds the GCC 16 snapshot Modula-2 frontend (cc1gm2) and the five runtime
libraries (libm2cor / libm2iso / libm2log / libm2min / libm2pim), then
packages only the runtime libraries and their Modula-2 definition-module
headers.  The gm2 compiler itself is intentionally NOT packaged.

OHOS CI is a native AArch64 environment, so build, host and target are all
``aarch64-linux-ohos``.  Audited source transforms (files/prepare_ohos_sources.py)
map that target to GCC's musl support and apply the Modula-2 frontend fixes
(build-triplet injection, mc bootstrap /tmp paths, umask 022).  Generated
host executables are code-signed with the OHOS SDK binary-sign-tool, and the
gm2 driver's specs file adds --eh-frame-hdr plus a post-link signing step so
compiled programs actually execute on HarmonyOS.
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
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.gnu import get_gnu_triplet
from conan.tools.layout import basic_layout


class Libgm2Conan(ConanFile):
    name = "libgm2"
    version = "16.1.1"
    package_type = "library"

    description = (
        "GNU Modula-2 runtime libraries (libm2cor/libm2iso/libm2log/"
        "libm2min/libm2pim) for HarmonyOS PC"
    )
    license = "GPL-3.0-or-later WITH GCC-exception-3.1"
    homepage = "https://gcc.gnu.org/"
    url = "https://gcc.gnu.org/pub/gcc/snapshots/16-20260502/"

    settings = "os", "compiler", "build_type", "arch"

    # Conan requires a 'shared' option for package_type "library".  The
    # libgm2 package ships both static (.a) and shared (.so) artifacts, so
    # the option is declared for conformance and does not change packaging.
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    build_requires = "dejagnu/1.6.3.1", "expect/5.45.4", "tcl/8.6.16"

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
                "The OHOS libgm2 package supports AArch64/armv8 only"
            )

    def source(self):
        sources = self.conan_data["sources"]
        get(self, **sources["gcc"], strip_root=True)

        # In-tree GMP/MPFR/MPC, exactly the versions GCC 16's official
        # contrib/download_prerequisites selects.  Keeps the package
        # reproducible without undeclared system libraries.
        for dependency in ("gmp", "mpfr", "mpc"):
            get(
                self,
                **sources[dependency],
                destination=os.path.join(self.source_folder, dependency),
                strip_root=True,
            )

        # Empty patches: {} by default; kept for G1 recipe-completeness and
        # for any future upstream patch carried in conandata.yml.
        apply_conandata_patches(self)

        # Run the large source-tree transform in a short-lived process.  On
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
    def _sdk_cxx_libdir(self):
        """Directory holding the SDK static C++ runtime archives."""
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc, _ = self._split_compiler_command(
            compiler_executables.get("c"), "clang"
        )
        libdir = os.path.normpath(
            os.path.join(
                os.path.dirname(os.path.realpath(cc)),
                "..",
                "lib",
                self._target_triplet,
            )
        )
        for name in ("libc++_static.a", "libunwind.a"):
            if not os.path.isfile(os.path.join(libdir, name)):
                raise ConanInvalidConfiguration(
                    "OHOS SDK C++ runtime archive not found: {}/{}".format(
                        libdir, name
                    )
                )
        return libdir

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

    # ------------------------------------------------------------------
    # Compiler / signer wrapper helpers
    # ------------------------------------------------------------------

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

    def _signer_tools(self):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or shutil.which("objcopy")
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        for name, path in (
            ("binary-sign-tool", signer),
            ("llvm-objcopy", objcopy),
            ("llvm-readelf", readelf),
        ):
            if (
                not path
                or not os.path.isfile(path)
                or not os.access(path, os.X_OK)
            ):
                raise ConanInvalidConfiguration(
                    "OHOS tooling requires: {}".format(name)
                )
        return signer, objcopy, readelf

    def _wrapper_dir(self):
        wrapper_dir = Path(self.build_folder) / ".ohos-wrappers"
        wrapper_dir.mkdir(parents=True, exist_ok=True)
        return wrapper_dir

    def _write_compiler_wrapper(self, name, real_compiler, extra_args=None):
        wrapper_dir = self._wrapper_dir()
        signer, objcopy, readelf = self._signer_tools()
        wrapper = wrapper_dir / name
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

    def _write_cxx_target_wrapper(self):
        """SDK clang++ targeting aarch64-linux-ohos (used for the libgm2
        runtime's C++ translation units), then code-signing any output."""
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx, cxx_args = self._split_compiler_command(
            compiler_executables.get("cpp"), "clang++"
        )
        # The configured compiler arguments must come before the
        # target/sysroot pair so --target/--sysroot win over any conflicting
        # flags the profile may have set.
        target_args = cxx_args + [
            "--target=" + self._target_triplet,
            "--sysroot=" + self._ohos_sysroot,
        ]
        return self._write_compiler_wrapper(
            "clangxx-target", cxx, extra_args=target_args
        )

    def _write_sign_output_script(self):
        """post_link spec helper: sign a linked executable in place."""
        signer, objcopy, readelf = self._signer_tools()
        codesign_log = os.path.join(self.build_folder, ".tmp", "codesign.log")
        Path(codesign_log).parent.mkdir(parents=True, exist_ok=True)
        gcc_dir = Path(self.build_folder) / "gcc"
        gcc_dir.mkdir(parents=True, exist_ok=True)
        script = gcc_dir / "sign-output.sh"
        script.write_text(
            """#!/bin/sh
# Sign an OHOS executable/shared library in place (idempotent).
set -eu
out="$1"
[ -n "$out" ] || exit 0
[ -f "$out" ] || exit 0
if {readelf} -h "$out" 2>/dev/null | grep -Eq 'Type:[[:space:]]+(EXEC|DYN)'; then
    unsigned="$out.ohos-unsigned-$$"
    signed="$out.ohos-signed-$$"
    trap 'rm -f "$unsigned" "$signed"' EXIT HUP INT TERM
    cp -p "$out" "$unsigned"
    {objcopy} --remove-section .codesign "$unsigned" 2>/dev/null || true
    # Route the sign tool's INFO chatter away from captured output.
    {signer} sign -inFile "$unsigned" -outFile "$signed" -selfSign 1 >>"{log}" 2>&1
    mv "$signed" "$out"
    rm -f "$unsigned"
    trap - EXIT HUP INT TERM
    chmod +x "$out" 2>/dev/null || true
fi
exit 0
""".format(
                signer=shlex.quote(signer),
                objcopy=shlex.quote(objcopy),
                readelf=shlex.quote(readelf),
                log=codesign_log,
            ),
            encoding="utf-8",
        )
        script.chmod(
            script.stat().st_mode
            | stat.S_IXUSR
            | stat.S_IXGRP
            | stat.S_IXOTH
        )
        return str(script)

    def _write_gm2_specs(self, sign_output):
        """Install the gm2 driver specs file in the -B gcc directory.

        Contains three OHOS-specific overrides on top of the builtin specs:
          *cpp:     discard the Clang-only __availability__ attribute used by
                    the OHOS SDK headers (GCC cannot parse "introduced=..."),
          *post_link: sign every linked program (OHOS refuses unsigned ELF),
          *link:    force --eh-frame-hdr so the exception runtime works.
        """
        template = os.path.join(
            self.export_sources_folder, "files", "gm2-specs.template"
        )
        specs = Path(template).read_text(encoding="utf-8")
        specs = specs.replace("@SIGN_OUTPUT@", shlex.quote(sign_output))
        gcc_dir = Path(self.build_folder) / "gcc"
        gcc_dir.mkdir(parents=True, exist_ok=True)
        (gcc_dir / "specs").write_text(specs, encoding="utf-8")

    def _make_merged_libstdcxx(self):
        """Merge the SDK libc++_static.a + libunwind.a into libstdc++.a.

        gm2spec.cc always adds -lstdc++, and libm2pim (RTExceptions.o /
        RTExceptions.so) references __cxa_throw, __cxa_allocate_exception and
        _ZTIi.  The in-tree libstdc++-v3 is intentionally not built, so a
        merged SDK archive placed in the -B gcc directory satisfies the link.
        """
        sdk_lib = self._sdk_cxx_libdir
        gcc_dir = Path(self.build_folder) / "gcc"
        gcc_dir.mkdir(parents=True, exist_ok=True)
        work = Path(self.build_folder) / ".tmp" / "libstdcxx-merge"
        shutil.rmtree(work, ignore_errors=True)
        work.mkdir(parents=True, exist_ok=True)
        ar = self._required_executable("ar", "llvm-ar", "ar")
        subprocess.run(
            [ar, "x", os.path.join(sdk_lib, "libc++_static.a")],
            cwd=str(work),
            check=True,
        )
        subprocess.run(
            [ar, "x", os.path.join(sdk_lib, "libunwind.a")],
            cwd=str(work),
            check=True,
        )
        members = sorted(str(path) for path in work.iterdir() if path.is_file())
        if not members:
            raise ConanInvalidConfiguration(
                "libc++_static.a/libunwind.a extraction produced no members"
            )
        target = gcc_dir / "libstdc++.a"
        subprocess.run(
            [ar, "rcs", str(target)] + members,
            check=True,
        )
        if not os.path.isfile(target):
            raise ConanInvalidConfiguration(
                "Merged libstdc++.a was not created: {}".format(target)
            )
        return str(target)

    # ------------------------------------------------------------------
    # Environment / build
    # ------------------------------------------------------------------

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
        ar = self._required_executable("ar", "llvm-ar", "ar")
        ranlib = self._required_executable("ranlib", "llvm-ranlib", "ranlib")
        nm = self._required_executable("nm", "llvm-nm", "nm")

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
            # AArch64 copy relocation for libc's stderr symbol.
            env.define("gcc_cv_c_no_fpie", "no")
            env.define("gcc_cv_no_pie", "no")
        env.define("AS", assembler)
        env.define("LD", linker)
        env.define("AS_FOR_TARGET", assembler)
        env.define("LD_FOR_TARGET", linker)
        env.define("AR", ar)
        env.define("RANLIB", ranlib)
        env.define("NM", nm)
        if self._is_ohos:
            env.define(
                "C_INCLUDE_PATH",
                os.path.join(
                    self._ohos_sysroot, "usr", "include", self._target_triplet
                ),
            )
            env.define(
                "CPLUS_INCLUDE_PATH",
                os.path.join(
                    self._ohos_sysroot, "usr", "include", self._target_triplet
                ),
            )
            env.define(
                "LIBRARY_PATH",
                os.path.join(
                    self._ohos_sysroot, "usr", "lib", self._target_triplet
                ),
            )
        # Do not call this script "conanbuild": Conan reserves that name for
        # its aggregate environment file.
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
            "--enable-languages=c,c++,m2",
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
            "--disable-threads",
        ]
        if self._is_ohos:
            arguments.append("--with-sysroot={}".format(self._ohos_sysroot))
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
        signer, objcopy, readelf = self._signer_tools()

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

    def _patch_generated_makefiles(self):
        """Post-configure build-tree edits needed by the OHOS target build.

        All edits target generated build files (Makefile / config.status),
        never the pristine source tree, so a clean re-configure reproduces
        them exactly.
        """
        top_makefile = Path(self.build_folder) / "Makefile"
        content = top_makefile.read_text(encoding="utf-8")
        # The Modula-2 runtime needs only libgcc + libgm2 target dirs.  The
        # in-tree libstdc++-v3 cannot be built (its cross-check needs to
        # execute unsigned xgcc output on-device and the musl ctype_base
        # lacks the _IS* macros), and the gm2 runtime does not need it: the
        # C++ translation units are compiled with the OHOS SDK clang++.
        if "TARGET_CONFIGDIRS =  @target_configdirs@" in content:
            content = content.replace(
                "TARGET_CONFIGDIRS =  @target_configdirs@",
                "TARGET_CONFIGDIRS =  libgcc libgm2",
            )
        # Break the baked-in dependency edge
        # configure-target-libgm2: maybe-all-target-libstdc++-v3 so the huge
        # (and unbuildable) libstdc++-v3 is never configured/built.
        content = content.replace(
            "maybe-all-target-libstdc++-v3: all-target-libstdc++-v3",
            "maybe-all-target-libstdc++-v3:",
        )
        top_makefile.write_text(content, encoding="utf-8")

        # --disable-threads makes libgcc pick the single-threaded
        # gthr-single.h, which lacks __gthread_cond_t; RTco.cc then fails to
        # compile.  OHOS musl provides pthread_cond_t, so use gthr-posix.h.
        for name in ("Makefile", "config.status"):
            path = (
                Path(self.build_folder)
                / "aarch64-linux-ohos"
                / "libgcc"
                / name
            )
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="surrogateescape")
            updated = text.replace("gthr-single.h", "gthr-posix.h")
            if updated != text:
                path.write_text(
                    updated, encoding="utf-8", errors="surrogateescape"
                )

        # The OHOS gm2 driver specs (written into gcc/specs after
        # configure-target-libgcc) must survive the rest of the build.  The
        # stock gcc/Makefile rule re-dumps specs whenever xgcc is newer than
        # gcc/specs -- which happens again during all-target-libgcc
        # (libgcc.mvars depends on `specs xgcc`) -- and that would clobber the
        # __availability__ / --eh-frame-hdr / post-link overrides, breaking
        # libgcc2.c against the OHOS SDK headers.  Neutralise the rule so a
        # later make only touches the file we already wrote.
        gcc_makefile = Path(self.build_folder) / "gcc" / "Makefile"
        if gcc_makefile.is_file():
            gcc_text = gcc_makefile.read_text(
                encoding="utf-8", errors="surrogateescape"
            )
            specs_rule = (
                "$(SPECS): xgcc$(exeext)\n"
                "\t$(GCC_FOR_TARGET) -dumpspecs > tmp-specs\n"
                "\tmv tmp-specs $(SPECS)\n"
            )
            specs_rule_kept = (
                "$(SPECS): xgcc$(exeext)\n"
                "\t@touch $(SPECS)\n"
            )
            if specs_rule in gcc_text:
                gcc_text = gcc_text.replace(
                    specs_rule, specs_rule_kept, 1
                )
                gcc_makefile.write_text(
                    gcc_text, encoding="utf-8", errors="surrogateescape"
                )

    def _is_configured(self):
        return os.path.isfile(
            os.path.join(self.build_folder, "Makefile")
        ) and os.path.isfile(os.path.join(self.build_folder, "config.status"))

    def build(self):
        make = "make --jobserver-style=pipe -j{}".format(
            max(1, min(build_jobs(self), 2))
        )

        if self._is_configured():
            self.output.info("Build tree already configured; skipping configure")
        else:
            configure = os.path.join(self.source_folder, "configure")
            shell = self._required_executable(
                "bash",
                os.environ.get("CONFIG_SHELL"),
                "bash",
                "/data/service/hnp/bin/bash",
            )
            configure_command = "{} {} {}".format(
                shlex.quote(shell),
                shlex.quote(configure),
                " ".join(
                    shlex.quote(argument)
                    for argument in self._configure_args()
                ),
            )
            self._run_with_unlimited_stack(
                configure_command,
                cwd=self.build_folder,
            )

        self._patch_generated_makefiles()

        # cc1gm2 (the Modula-2 compiler) and the gm2 driver.
        self._run_with_unlimited_stack(
            "{} all-gcc".format(make),
            cwd=self.build_folder,
        )
        self._sign_elf_tree(self.build_folder)

        # Prepare the link environment (signer + merged libstdc++.a) before
        # any program is compiled and executed.  The specs file is written
        # AFTER configure-target-libgcc: that configure step re-runs
        # `xgcc -dumpspecs > specs`, which would clobber a template written
        # here and drop the __availability__ / --eh-frame-hdr / post-link
        # overrides that libgcc2.c needs to compile against OHOS headers.
        sign_output = self._write_sign_output_script()
        self._make_merged_libstdcxx()

        # Target libraries: first configure libgcc so the thread_header edit
        # lands before its compilation, then build libgcc and the gm2 runtime.
        self._run_with_unlimited_stack(
            "{} configure-target-libgcc".format(make),
            cwd=self.build_folder,
        )
        self._patch_generated_makefiles()
        self._write_gm2_specs(sign_output)
        self._run_with_unlimited_stack(
            "{} all-target-libgcc".format(make),
            cwd=self.build_folder,
        )
        cxx_target = self._write_cxx_target_wrapper()
        self._run_with_unlimited_stack(
            "{} all-target-libgm2 CXX_FOR_TARGET={}".format(
                make, shlex.quote(cxx_target)
            ),
            cwd=self.build_folder,
        )

        self._run_gm2_smoke_test()

    def _runtime_dir(self):
        return os.path.join(
            self.build_folder,
            "aarch64-linux-ohos",
            "libgm2",
        )

    def _run_gm2_smoke_test(self):
        """Compile and execute an upstream Modula-2 hello program with the
        freshly built gm2 driver.  Exercises cc1gm2, the driver, the OHOS
        specs (__availability__ / --eh-frame-hdr / post-link signing), the
        merged libstdc++.a and the five runtime libraries end to end."""
        if not self._is_ohos:
            return
        build = Path(self.build_folder)
        gcc_dir = build / "gcc"
        gm2 = gcc_dir / "gm2"
        if not os.path.isfile(gm2):
            raise ConanInvalidConfiguration(
                "The built gm2 driver was not found: {}".format(gm2)
            )
        src_root = Path(self.source_folder) / "gcc" / "m2"
        work = build / ".tmp" / "gm2-smoke"
        shutil.rmtree(work, ignore_errors=True)
        work.mkdir(parents=True, exist_ok=True)
        hello = src_root / ".." / "testsuite" / "gm2" / "examples" / "hello" / "pass" / "hello.mod"
        if not os.path.isfile(hello):
            raise ConanInvalidConfiguration(
                "Upstream hello.mod not found: {}".format(hello)
            )
        rt = self._runtime_dir()
        # -fm2-pathname maps a pathname (as written by IMPORT FROM ... hints
        # in the .mod sources) to a search directory; repeating a pathname
        # appends another directory to it.  "m2pim" resolves against the
        # packaged runtime .def headers first, then the source-tree
        # gm2-libs; "m2iso" likewise, with gm2-libs-iso as a plain -I.
        flags = [
            "-B" + str(gcc_dir),
            "-fm2-pathname=m2pim", "-I" + os.path.join(rt, "libm2pim"),
            "-fm2-pathname=m2pim", "-I" + os.path.join(src_root, "gm2-libs"),
            "-fm2-pathname=m2iso", "-I" + os.path.join(rt, "libm2iso"),
            "-I" + os.path.join(src_root, "gm2-libs-iso"),
        ]
        for lib in ("libm2pim", "libm2iso", "libm2cor", "libm2log", "libm2min"):
            flags.append("-L" + os.path.join(rt, lib, ".libs"))
        flags += ["-fpim", "-o", "hello", str(hello)]
        command = "{} {}".format(
            shlex.quote(str(gm2)), " ".join(shlex.quote(f) for f in flags)
        )
        self._run_with_unlimited_stack(command, cwd=str(work))
        executable = work / "hello"
        if not os.path.isfile(executable):
            raise ConanInvalidConfiguration(
                "gm2 smoke test did not produce an executable"
            )
        ld_path = ":".join(
            os.path.join(rt, lib, ".libs")
            for lib in ("libm2pim", "libm2iso", "libm2cor", "libm2log", "libm2min")
        )
        result = self.run(
            "LD_LIBRARY_PATH={} ./hello".format(shlex.quote(ld_path)),
            cwd=str(work),
            env="gcc_build_env",
            ignore_errors=True,
        )
        if result != 0:
            raise ConanInvalidConfiguration(
                "gm2 smoke test failed to run (rc={}); the runtime or the "
                "compiled executable is broken".format(result)
            )
        self.output.info("gm2 smoke test passed: hello world from libgm2")

    # ------------------------------------------------------------------
    # Packaging
    # ------------------------------------------------------------------

    def package(self):
        rt = self._runtime_dir()
        for lib in ("libm2cor", "libm2iso", "libm2log", "libm2min", "libm2pim"):
            libs_dir = os.path.join(rt, lib, ".libs")
            for name in (
                "lib{}.a".format(lib[3:]),
                "lib{}.so".format(lib[3:]),
                "lib{}.so.21".format(lib[3:]),
                "lib{}.so.21.0.0".format(lib[3:]),
            ):
                source = os.path.join(libs_dir, name)
                if not os.path.isfile(source):
                    raise ConanInvalidConfiguration(
                        "Runtime library artifact missing: {}".format(source)
                    )
                copy(
                    self,
                    name,
                    src=libs_dir,
                    dst=os.path.join(self.package_folder, "lib"),
                )
            # Modula-2 definition-module headers for this library.
            for name in sorted(
                entry for entry in os.listdir(os.path.join(rt, lib))
                if entry.endswith(".def")
            ):
                copy(
                    self,
                    name,
                    src=os.path.join(rt, lib),
                    dst=os.path.join(
                        self.package_folder, "include", "libgm2", lib[3:]
                    ),
                )
        # The merged C++ runtime stub (see _make_merged_libstdcxx).  Kept in
        # lib/ so -lstdc++ resolves for static consumers of libm2pim.
        copy(
            self,
            "libstdc++.a",
            src=os.path.join(self.build_folder, "gcc"),
            dst=os.path.join(self.package_folder, "lib"),
        )
        copy(
            self,
            "COPYING3",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "COPYING.RUNTIME",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        # Re-sign the packaged shared libraries so the package is runnable
        # even if it was assembled from an interrupted cache build.
        self._sign_elf_tree(self.package_folder)

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include", "include/libgm2"]
        # libm2pim.so.21 and the static archives reference the C++ exception
        # runtime; the packaged libstdc++.a (merged libc++_static + libunwind)
        # satisfies it for both shared and static consumers.
        self.cpp_info.libs = [
            "m2iso",
            "m2pim",
            "m2cor",
            "m2log",
            "m2min",
            "stdc++",
        ]
        self.cpp_info.system_libs = ["m"]
