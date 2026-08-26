#!/usr/bin/env python3
"""Bootstrap AVR GCC hosted on OHOS."""

import os
import re
import shlex
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import build_jobs
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.gnu import get_gnu_triplet
from conan.tools.layout import basic_layout


class AvrGccBootstrapConan(ConanFile):
    name = "avr-gcc-bootstrap"
    version = "14.2.0"
    package_type = "application"
    no_copy_source = True

    description = "Bootstrap AVR C compiler hosted on HarmonyOS"
    license = "GPL-3.0-or-later WITH GCC-exception-3.1"
    homepage = "https://gcc.gnu.org/"
    url = "https://gcc.gnu.org/git/gcc.git"

    settings = "os", "arch", "compiler", "build_type"

    def build_requirements(self):
        self.tool_requires("avr-binutils/2.43.1")

    def export_sources(self):
        copy(
            self,
            "*",
            src=os.path.join(self.recipe_folder, "patches"),
            dst=os.path.join(self.export_sources_folder, "patches"),
        )

    def layout(self):
        basic_layout(self)

    @property
    def _is_ohos(self):
        return str(self.settings.os) == "OHOS"

    @property
    def _host_triplet(self):
        if self._is_ohos:
            return "aarch64-unknown-linux-musl"
        return get_gnu_triplet(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "avr-gcc-bootstrap supports Linux and OHOS hosts"
            )
        if self._is_ohos and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "The OHOS package supports AArch64/armv8 only"
            )

    def source(self):
        sources = self.conan_data["sources"][str(self.version)]
        get(self, **sources["gcc"], strip_root=True)
        for dependency in ("gmp", "mpfr", "mpc"):
            get(
                self,
                **sources[dependency],
                destination=os.path.join(
                    self.source_folder, dependency
                ),
                strip_root=True,
            )
        apply_conandata_patches(self)

    @staticmethod
    def _split_command(configured, fallback):
        command = shlex.split(configured or fallback)
        if not command:
            raise ConanInvalidConfiguration("Compiler command is empty")
        executable = shutil.which(command[0])
        if not executable and os.path.isfile(command[0]):
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
            if not resolved and os.path.isfile(candidate):
                resolved = os.path.abspath(candidate)
            if resolved and os.access(resolved, os.X_OK):
                return resolved
        raise ConanInvalidConfiguration(
            "Required executable was not found: {}".format(name)
        )

    def _avr_tool(self, name):
        dependency = self.dependencies.build["avr-binutils"]
        path = os.path.join(dependency.package_folder, "bin", name)
        if not os.path.isfile(path):
            raise ConanInvalidConfiguration(
                "Required AVR Binutils program was not found: {}".format(path)
            )
        return path

    @property
    def _avr_bin_dir(self):
        return os.path.join(
            self.dependencies.build["avr-binutils"].package_folder,
            "bin",
        )

    def _materialize_target_tool_dispatchers(self):
        if not self._is_ohos:
            return

        gcc_dir = Path(self.build_folder) / "gcc"
        dispatchers = {
            "as": "avr-as",
            "collect-ld": "avr-ld",
            "nm": "avr-nm",
        }
        for destination_name, source_name in dispatchers.items():
            destination = gcc_dir / destination_name
            if not destination.is_file():
                raise ConanInvalidConfiguration(
                    "GCC target tool dispatcher was not found: {}".format(
                        destination
                    )
                )
            shutil.copy2(self._avr_tool(source_name), destination)
            destination.chmod(destination.stat().st_mode | stat.S_IXUSR)

    @staticmethod
    def _compiler_wrapper_text(
        real_compiler, signer, objcopy, readelf, extra_args=None
    ):
        extra = " ".join(shlex.quote(value) for value in (extra_args or []))
        setup = 'set -- {} "$@"'.format(extra) if extra else 'set -- "$@"'
        return """#!/bin/sh
set -eu
real_compiler={real_compiler}
signer={signer}
objcopy={objcopy}
readelf={readelf}
{setup}

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
        -o?*) output=$(printf '%s' "$argument" | cut -c3-) ;;
        -c|-S|-E) compile_only=1 ;;
    esac
done

if [ -z "$output" ] && [ "$compile_only" -eq 0 ]; then
    output=a.out
fi

if [ -n "$output" ] && [ -f "$output" ]; then
    if "$readelf" -h "$output" 2>/dev/null | grep -Eq 'Type:[[:space:]]+(EXEC|DYN)'; then
        unsigned="$output.ohos-unsigned-$$"
        signed="$output.ohos-signed-$$"
        trap 'rm -f "$unsigned" "$signed"' EXIT HUP INT TERM
        cp -p "$output" "$unsigned"
        "$objcopy" --remove-section .codesign "$unsigned" 2>/dev/null || true
        "$signer" sign -inFile "$unsigned" -outFile "$signed" -selfSign 1
        "$readelf" -S "$signed" | grep -q '[.]codesign'
        mv "$signed" "$output"
        rm -f "$unsigned"
        trap - EXIT HUP INT TERM
        chmod +x "$output" 2>/dev/null || true
    fi
fi
""".format(
            real_compiler=shlex.quote(real_compiler),
            signer=shlex.quote(signer),
            objcopy=shlex.quote(objcopy),
            readelf=shlex.quote(readelf),
            setup=setup,
        )

    def _write_compiler_wrapper(
        self, name, real_compiler, extra_args=None
    ):
        wrapper_dir = Path(self.build_folder) / ".ohos-wrappers"
        wrapper_dir.mkdir(parents=True, exist_ok=True)
        wrapper = wrapper_dir / name
        signer = (
            shutil.which("binary-sign-tool")
            or "/data/service/hnp/bin/binary-sign-tool"
        )
        objcopy = shutil.which("llvm-objcopy") or shutil.which("objcopy")
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        if not (os.path.isfile(signer) and objcopy and readelf):
            raise ConanInvalidConfiguration(
                "OHOS compiler wrappers require binary-sign-tool, "
                "llvm-objcopy and llvm-readelf"
            )
        wrapper.write_text(
            self._compiler_wrapper_text(
                real_compiler,
                signer,
                objcopy,
                readelf,
                extra_args,
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

    def _write_makeinfo_wrapper(self, shell):
        wrapper_dir = Path(self.build_folder) / ".ohos-wrappers"
        wrapper_dir.mkdir(parents=True, exist_ok=True)
        wrapper = wrapper_dir / "makeinfo-fallback"
        wrapper.write_text(
            """#!/bin/sh
set -eu

if [ "${1:-}" = "--version" ]; then
    echo "texi2any (GNU texinfo) 7.0"
    exit 0
fi

output=""
input=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        -o)
            shift
            [ "$#" -gt 0 ] || exit 2
            output=$1
            ;;
        -o?*) output=${1#-o} ;;
        *.texi) input=$1 ;;
    esac
    shift
done

if [ -z "$output" ] || [ -z "$input" ]; then
    echo "makeinfo fallback requires -o OUTPUT INPUT.texi" >&2
    exit 2
fi
prebuilt="$(dirname "$input")/$(basename "$output")"
if [ ! -f "$prebuilt" ]; then
    prebuilt=${input%.texi}.info
fi
if [ ! -f "$prebuilt" ]; then
    echo "prebuilt info file was not found: $prebuilt" >&2
    exit 2
fi
mkdir -p "$(dirname "$output")"
cp -p "$prebuilt" "$output"
""",
            encoding="utf-8",
        )
        return shlex.join([shell, str(wrapper)])

    def generate(self):
        Path(self.build_folder).mkdir(parents=True, exist_ok=True)
        tmpdir = Path(self.build_folder) / ".tmp"
        tmpdir.mkdir(parents=True, exist_ok=True)
        (tmpdir / "zsh").mkdir(parents=True, exist_ok=True)

        configured = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        cc, cc_args = self._split_command(configured.get("c"), "clang")
        cxx, cxx_args = self._split_command(
            configured.get("cpp"), "clang++"
        )
        shell = self._required_executable(
            "bash", "bash", "/data/service/hnp/bin/bash"
        )
        if self._is_ohos:
            cc_wrapper = self._write_compiler_wrapper("clang-sign", cc, cc_args)
            cxx_wrapper = self._write_compiler_wrapper(
                "clangxx-sign", cxx, cxx_args
            )
            cc = shlex.join([shell, cc_wrapper])
            cxx = shlex.join([shell, cxx_wrapper])
        else:
            cc = shlex.join([cc] + cc_args)
            cxx = shlex.join([cxx] + cxx_args)

        makeinfo = self._write_makeinfo_wrapper(shell)

        assembler = self._required_executable(
            "GNU assembler", "as", "/data/service/hnp/bin/as"
        )
        linker = self._required_executable(
            "GNU linker", "ld", "/data/service/hnp/bin/ld"
        )
        true_tool = self._required_executable("true", "true", "/bin/true")

        env = Environment()
        env.define("CC", cc)
        env.define("CXX", cxx)
        env.define("CC_FOR_BUILD", cc)
        env.define("CXX_FOR_BUILD", cxx)
        env.define("AS", assembler)
        env.define("LD", linker)
        env.define("AR", configured.get("ar", "llvm-ar"))
        env.define("RANLIB", configured.get("ranlib", "llvm-ranlib"))
        env.define("NM", configured.get("nm", "llvm-nm"))
        env.define("STRIP", configured.get("strip", "llvm-strip"))
        env.define("CONFIG_SHELL", shell)
        env.define("SHELL", shell)
        env.define("MAKEINFO", makeinfo)
        env.define("HELP2MAN", true_tool)
        env.define("LN_S", "cp -p")
        # HMDFS can reject getcwd() from nested HNP bash processes. Keep a
        # valid logical path so bash and Autoconf do not need the parent walk.
        env.define("PWD", str(self.build_folder))
        env.define("TMPDIR", str(tmpdir))
        env.define("TMPPREFIX", str(tmpdir / "zsh"))
        env.prepend_path("PATH", self._avr_bin_dir)
        env.define("AS_FOR_TARGET", self._avr_tool("avr-as"))
        env.define("LD_FOR_TARGET", self._avr_tool("avr-ld"))
        env.define("AR_FOR_TARGET", self._avr_tool("avr-ar"))
        env.define("NM_FOR_TARGET", self._avr_tool("avr-nm"))
        env.define("RANLIB_FOR_TARGET", self._avr_tool("avr-ranlib"))
        env.define("OBJCOPY_FOR_TARGET", self._avr_tool("avr-objcopy"))
        env.define("OBJDUMP_FOR_TARGET", self._avr_tool("avr-objdump"))
        env.define("STRIP_FOR_TARGET", self._avr_tool("avr-strip"))
        env.vars(self).save_script("avr_gcc_bootstrap_build_env")

    def _configure_args(self):
        return [
            "--prefix=/",
            "--build={}".format(self._host_triplet),
            "--host={}".format(self._host_triplet),
            "--target=avr",
            "--enable-languages=c",
            "--with-multilib-list=avr5",
            "--with-double=32",
            "--with-long-double=32",
            "--enable-checking=release",
            "--enable-host-pie",
            "--disable-bootstrap",
            "--disable-nls",
            "--disable-shared",
            "--disable-threads",
            "--disable-libatomic",
            "--disable-libcc1",
            "--disable-libgomp",
            "--disable-libitm",
            "--disable-libquadmath",
            "--disable-fixed-point",
            "--with-libf7=no",
            "--disable-libsanitizer",
            "--disable-libssp",
            "--disable-libvtv",
            "--disable-lto",
            "--disable-plugin",
            "--with-newlib",
            "--without-headers",
            "--without-isl",
            "--with-dwarf2",
            "--with-gnu-as",
            "--with-gnu-ld",
        ]

    @property
    def _make(self):
        return self._required_executable(
            "GNU make", "make", "/data/service/hnp/bin/make"
        )

    def _run_unlimited(self, command, cwd):
        shell = self._required_executable(
            "bash", "bash", "/data/service/hnp/bin/bash"
        )
        wrapped = "{} -c {} {} {} -c {}".format(
            shlex.quote(shell),
            shlex.quote('ulimit -s unlimited; exec "$@"'),
            shlex.quote("avr-gcc-bootstrap"),
            shlex.quote(shell),
            shlex.quote(command),
        )
        result = self.run(
            wrapped,
            cwd=cwd,
            env="avr_gcc_bootstrap_build_env",
            ignore_errors=True,
        )
        if result != 0:
            raise ConanException(
                "GCC bootstrap command failed with exit code {}".format(
                    result
                )
            )

    def build(self):
        os.chdir(self.build_folder)
        shell = self._required_executable(
            "bash", "bash", "/data/service/hnp/bin/bash"
        )
        configure = os.path.join(self.source_folder, "configure")
        configure_command = "{} {} {}".format(
            shlex.quote(shell),
            shlex.quote(configure),
            " ".join(
                shlex.quote(argument)
                for argument in self._configure_args()
            ),
        )
        self._run_unlimited(configure_command, self.build_folder)

        jobs = max(1, min(build_jobs(self), 2))
        make = "{} --jobserver-style=pipe -j{}".format(
            shlex.quote(self._make), jobs
        )
        self._run_unlimited(
            "{} all-gcc".format(make), self.build_folder
        )
        self._sign_elf_tree(self.build_folder)
        self._materialize_target_tool_dispatchers()

        self._run_unlimited(
            "{} all-target-libgcc".format(make), self.build_folder
        )
        self._sign_elf_tree(self.build_folder)

        self._run_unlimited(
            "cd gcc && {} selftest".format(shlex.quote(self._make)),
            self.build_folder,
        )
        self._compile_torture_subset()

    def _compile_torture_subset(self):
        tests = (
            "20000113-1.c",
            "20000121-1.c",
            "20000217-1.c",
            "20000223-1.c",
            "20000224-1.c",
            "20000225-1.c",
            "20000313-1.c",
            "20000314-1.c",
        )
        xgcc = os.path.join(self.build_folder, "gcc", "xgcc")
        if not os.path.isfile(xgcc):
            raise ConanInvalidConfiguration(
                "Freshly built xgcc was not found: {}".format(xgcc)
            )
        output_dir = Path(self.build_folder) / "torture-compile"
        output_dir.mkdir(parents=True, exist_ok=True)
        source_dir = Path(self.source_folder) / "gcc" / "testsuite"
        source_dir = source_dir / "gcc.c-torture" / "execute"
        for optimization in ("-O0", "-O2"):
            for source_name in tests:
                source = source_dir / source_name
                output = output_dir / (
                    "{}-{}.o".format(
                        source.stem,
                        optimization[1:],
                    )
                )
                command = [
                    xgcc,
                    "-B" + os.path.join(self.build_folder, "gcc") + os.sep,
                    "-B" + self._avr_bin_dir + os.sep,
                    "-mmcu=atmega328p",
                    optimization,
                    "-c",
                    str(source),
                    "-o",
                    str(output),
                ]
                self.run(
                    " ".join(shlex.quote(value) for value in command),
                    cwd=self.build_folder,
                    env="avr_gcc_bootstrap_build_env",
                )

    def _sign_elf_tree(self, root):
        if not self._is_ohos:
            return
        signer = (
            shutil.which("binary-sign-tool")
            or "/data/service/hnp/bin/binary-sign-tool"
        )
        objcopy = shutil.which("llvm-objcopy") or shutil.which("objcopy")
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        if not (os.path.isfile(signer) and objcopy and readelf):
            raise ConanInvalidConfiguration(
                "OHOS ELF signing requires binary-sign-tool, "
                "llvm-objcopy and llvm-readelf"
            )

        for candidate in Path(root).rglob("*"):
            if (
                not candidate.is_file()
                or candidate.is_symlink()
                or not candidate.stat().st_mode
                & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            ):
                continue
            probe = subprocess.run(
                [readelf, "-h", str(candidate)],
                capture_output=True,
                text=True,
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
                sections = subprocess.run(
                    [readelf, "-S", signed],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                if ".codesign" not in sections.stdout:
                    raise ConanInvalidConfiguration(
                        "Signing did not add .codesign: {}".format(
                            candidate
                        )
                    )
                os.replace(signed, candidate)
                candidate.chmod(original_mode)

    @staticmethod
    def _materialize_symlinks(root):
        for candidate in Path(root).rglob("*"):
            if not candidate.is_symlink():
                continue
            target = candidate.resolve(strict=True)
            mode = stat.S_IMODE(target.stat().st_mode)
            candidate.unlink()
            shutil.copy2(target, candidate)
            candidate.chmod(mode)

    def package(self):
        make = shlex.quote(self._make)
        self._run_unlimited(
            "{} install-gcc install-target-libgcc DESTDIR={}".format(
                make,
                shlex.quote(self.package_folder),
            ),
            self.build_folder,
        )
        copy(
            self,
            "COPYING*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        self._materialize_symlinks(self.package_folder)
        self._sign_elf_tree(self.package_folder)

        required = (
            os.path.join("bin", "avr-gcc"),
            os.path.join(
                "libexec", "gcc", "avr", str(self.version), "cc1"
            ),
            os.path.join(
                "lib", "gcc", "avr", str(self.version), "libgcc.a"
            ),
        )
        missing = [
            path
            for path in required
            if not os.path.isfile(
                os.path.join(self.package_folder, path)
            )
        ]
        if missing:
            raise ConanInvalidConfiguration(
                "Missing bootstrap compiler artifacts: {}".format(
                    ", ".join(missing)
                )
            )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        bindir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.prepend_path("PATH", bindir)
        self.buildenv_info.define_path(
            "AVR_GCC_BOOTSTRAP_ROOT", self.package_folder
        )
        self.runenv_info.prepend_path("PATH", bindir)
        self.runenv_info.define_path(
            "AVR_GCC_BOOTSTRAP_ROOT", self.package_folder
        )
