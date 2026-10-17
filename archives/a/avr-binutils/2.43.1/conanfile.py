#!/usr/bin/env python3
"""GNU Binutils hosted on OHOS and targeting AVR."""

import os
import re
import shlex
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import build_jobs
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.gnu import get_gnu_triplet
from conan.tools.layout import basic_layout


class AvrBinutilsConan(ConanFile):
    name = "avr-binutils"
    version = "2.43.1"
    package_type = "application"

    description = "GNU Binutils hosted on HarmonyOS and targeting AVR"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/binutils/"
    url = "https://sourceware.org/git/binutils-gdb.git"

    settings = "os", "arch", "compiler", "build_type"

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
            return "aarch64-unknown-linux-ohos"
        return get_gnu_triplet(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "avr-binutils supports Linux and OHOS hosts"
            )
        if self._is_ohos and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration(
                "The OHOS package supports AArch64/armv8 only"
            )

    def source(self):
        get(
            self,
            **self.conan_data["sources"][str(self.version)],
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
prebuilt=${input%.texi}.info
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
        shell = self._required_executable("sh", "sh", "/bin/sh")
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
        env.define("TMPDIR", str(tmpdir))
        env.define("TMPPREFIX", str(tmpdir / "zsh"))
        env.vars(self).save_script("avr_binutils_build_env")

    def _configure_args(self):
        return [
            "--prefix=/",
            "--build={}".format(self._host_triplet),
            "--host={}".format(self._host_triplet),
            "--target=avr",
            "--disable-nls",
            "--disable-werror",
            "--disable-gdb",
            "--disable-gdbserver",
            "--disable-gprofng",
            "--disable-gold",
            "--disable-sim",
            "--disable-plugins",
            "--disable-shared",
            "--enable-static",
            "--without-debuginfod",
            "--without-guile",
            "--without-zstd",
        ]

    @property
    def _make(self):
        return self._required_executable(
            "GNU make", "make", "/data/service/hnp/bin/make"
        )

    def build(self):
        configure = os.path.join(self.source_folder, "configure")
        shell = self._required_executable("sh", "sh", "/bin/sh")
        command = "{} {} {}".format(
            shlex.quote(shell),
            shlex.quote(configure),
            " ".join(
                shlex.quote(argument)
                for argument in self._configure_args()
            ),
        )
        self.run(
            command,
            cwd=self.build_folder,
            env="avr_binutils_build_env",
        )

        jobs = max(1, min(build_jobs(self), 2))
        make = "{} --jobserver-style=pipe -j{}".format(
            shlex.quote(self._make), jobs
        )
        self.run(
            make,
            cwd=self.build_folder,
            env="avr_binutils_build_env",
        )
        self._sign_elf_tree(self.build_folder)

        self.run(
            "{} -C libiberty check".format(shlex.quote(self._make)),
            cwd=self.build_folder,
            env="avr_binutils_build_env",
        )
        if shutil.which("runtest"):
            self.run(
                "{} check-binutils check-gas check-ld".format(
                    shlex.quote(self._make)
                ),
                cwd=self.build_folder,
                env="avr_binutils_build_env",
            )
        else:
            self.output.warning(
                "DejaGNU is unavailable; target testsuites are skipped"
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
        self.run(
            "{} install DESTDIR={}".format(
                shlex.quote(self._make),
                shlex.quote(self.package_folder),
            ),
            cwd=self.build_folder,
            env="avr_binutils_build_env",
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
            "avr-ar",
            "avr-as",
            "avr-ld",
            "avr-nm",
            "avr-objcopy",
            "avr-objdump",
            "avr-ranlib",
            "avr-readelf",
            "avr-size",
            "avr-strings",
            "avr-strip",
        )
        missing = [
            name
            for name in required
            if not os.path.isfile(
                os.path.join(self.package_folder, "bin", name)
            )
        ]
        if missing:
            raise ConanInvalidConfiguration(
                "Missing packaged AVR tools: {}".format(", ".join(missing))
            )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        bindir = os.path.join(self.package_folder, "bin")
        self.buildenv_info.prepend_path("PATH", bindir)
        self.buildenv_info.define_path(
            "AVR_BINUTILS_ROOT", self.package_folder
        )
        self.runenv_info.prepend_path("PATH", bindir)
        self.runenv_info.define_path(
            "AVR_BINUTILS_ROOT", self.package_folder
        )
