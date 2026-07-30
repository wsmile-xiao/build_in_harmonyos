#!/usr/bin/env python3
"""Conan recipe for perl 5.42.2."""

import os
import shutil
import subprocess
from shlex import quote

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.layout import basic_layout


class PerlConan(ConanFile):
    name = "perl"
    version = "5.42.2"
    description = "Perl 5 interpreter and core modules"
    license = "Artistic-1.0-Perl OR GPL-1.0-or-later"
    homepage = "https://www.perl.org/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # Perl's Configure/Makefile flow is in-source.
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("perl recipe currently supports Linux and OHOS native builds only")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _compiler(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        candidates = [
            compilers.get("c"),
            os.environ.get("CC"),
            shutil.which("clang"),
            *self._home_tools("clang"),
            "/data/service/hnp/bin/clang",
            shutil.which("cc"),
            "clang",
            "cc",
        ]
        for candidate in candidates:
            if self._command_exists(candidate):
                return self._shell_wrapped(candidate)
        return self._shell_wrapped(candidates[-1])

    def _config_shell(self):
        candidates = [
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            shutil.which("bash"),
            *self._home_tools("bash"),
            "/data/service/hnp/bin/bash",
            shutil.which("sh"),
            "/system/bin/sh",
            "/bin/sh",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return "sh"

    def _home_tools(self, name):
        homes = [os.path.expanduser("~"), os.environ.get("HOME"), "/storage/Users/currentUser"]
        paths = []
        for home in homes:
            if not home:
                continue
            path = os.path.join(home, "usr", "local", "bin", name)
            if path not in paths:
                paths.append(path)
        return paths

    def _tool(self, *names):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        candidates = []
        for name in names:
            candidates.extend([
                compilers.get(name),
                os.environ.get(name.upper().replace("-", "_")),
                shutil.which(name),
                *self._home_tools(name),
                os.path.join("/data/service/hnp/bin", name),
                name,
            ])
        for candidate in candidates:
            if self._command_exists(candidate):
                return self._shell_wrapped(candidate)
        return names[-1]

    def _link_tool(self):
        if self.settings.os == "OHOS":
            return self._ohos_copy_link_tool()
        return self._tool("ln")

    def _ohos_copy_link_tool(self):
        wrapper = os.path.join(self.build_folder, "ohos-ln-copy.sh")
        content = """#!/system/bin/sh
set -eu

cp_cmd="${CP:-/system/bin/cp}"
if [ ! -x "$cp_cmd" ]; then
    cp_cmd=cp
fi

if [ "$#" -eq 2 ]; then
    src=$1
    dst=$2
    case "$dst" in
        */*) dst_dir=${dst%/*} ;;
        *) dst_dir=. ;;
    esac
    case "$src" in
        /*) ;;
        *)
            if [ "$dst_dir" != "." ]; then
                alt="$dst_dir/$src"
                if [ -e "$alt" ]; then
                    src=$alt
                fi
            fi
            ;;
    esac
    rm -f "$dst"
    exec "$cp_cmd" "$src" "$dst"
fi

exec "$cp_cmd" "$@"
"""
        save(self, wrapper, content)
        os.chmod(wrapper, 0o755)
        return f"{self._config_shell()} {wrapper}"

    def _command_exists(self, candidate):
        if not candidate:
            return False
        if os.path.isabs(candidate):
            return os.path.isfile(candidate)
        return bool(shutil.which(candidate))

    def _shell_wrapped(self, candidate):
        if not (candidate and os.path.isfile(candidate)):
            return candidate
        try:
            with open(candidate, "rb") as handle:
                first_line = handle.readline(256)
        except OSError:
            return candidate
        if first_line.startswith(b"#!") and b"/bin/sh" in first_line:
            return f"{self._config_shell()} {candidate}"
        return candidate

    def _configure_args(self):
        no_extensions = ["GDBM_File", "NDBM_File", "ODBM_File", "DB_File"]
        if self.settings.os == "OHOS":
            no_extensions.append("IPC/SysV")

        args = [
            "-des",
            "-Dprefix=/",
            "-Dsiteprefix=/",
            "-Dvendorprefix=/",
            f"-Dcc={self._compiler()}",
            f"-Dnm={self._tool('llvm-nm', 'nm')}",
            f"-Dar={self._tool('llvm-ar', 'ar')}",
            f"-Dranlib={self._tool('llvm-ranlib', 'ranlib')}",
            "-Dusenm=false",
            "-Uuseshrplib",
            "-Dusethreads",
            "-Dusemymalloc=n",
            "-Uinstallusrbinperl",
            "-Dman1dir=none",
            "-Dman3dir=none",
            "-Dinstallman1dir=none",
            "-Dinstallman3dir=none",
            "-Dlibswanted=pthread dl m c",
            f"-Dnoextensions={' '.join(no_extensions)}",
            "-Dcf_by=conan",
        ]
        if self.settings.os == "OHOS":
            link_tool = self._link_tool()
            args.extend([
                "-Dosname=linux",
                "-Darchname=aarch64-linux",
                "-Dmyhostname=ohos",
                "-Dmydomain=.local",
                f"-Dlns={link_tool}",
                "-Ui_langinfo",
                "-Ud_nl_langinfo",
                "-Ud_nl_langinfo_l",
                "-Ud_prctl_set_name",
            ])
        return args

    def build(self):
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)

        shell = self._config_shell()
        os.environ["SHELL"] = shell
        os.environ["CONFIG_SHELL"] = shell
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMPPREFIX"] = os.path.join(tmpdir, "perl")

        configure = os.path.join(self.source_folder, "Configure")
        args = " ".join(quote(arg) for arg in self._configure_args())
        cc = self._compiler()
        nm = self._tool("llvm-nm", "nm")
        ar = self._tool("llvm-ar", "ar")
        ranlib = self._tool("llvm-ranlib", "ranlib")
        lns = self._link_tool()
        env = (
            f"SHELL={quote(shell)} CONFIG_SHELL={quote(shell)} "
            f"CC={quote(cc)} NM={quote(nm)} AR={quote(ar)} RANLIB={quote(ranlib)} LNS={quote(lns)} "
            f"TMPDIR={quote(tmpdir)} TMPPREFIX={quote(os.environ['TMPPREFIX'])}"
        )
        self.run(f"{env} {quote(shell)} {quote(configure)} {args}", cwd=self.source_folder, env="conanbuild")
        self.run(
            f"make -j1 SHELL={quote(shell)} CONFIG_SHELL={quote(shell)} "
            f"CC={quote(cc)} NM={quote(nm)} AR={quote(ar)} "
            f"RANLIB={quote(ranlib)} LNS={quote(lns)}",
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package(self):
        shell = self._config_shell()
        os.environ["SHELL"] = shell
        os.environ["CONFIG_SHELL"] = shell
        self.run(
            f"make install.perl DESTDIR={quote(self.package_folder)} "
            f"SHELL={quote(shell)} CONFIG_SHELL={quote(shell)} "
            f"CC={quote(self._compiler())} NM={quote(self._tool('llvm-nm', 'nm'))} "
            f"AR={quote(self._tool('llvm-ar', 'ar'))} "
            f"RANLIB={quote(self._tool('llvm-ranlib', 'ranlib'))} "
            f"LNS={quote(self._link_tool())}",
            cwd=self.source_folder,
            env="conanbuild",
        )

        copy(self, "Artistic", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "Copying", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

        for exe in ("perl", f"perl{self.version}"):
            path = os.path.join(self.package_folder, "bin", exe)
            if os.path.exists(path):
                os.chmod(path, 0o755)
        self._sign_elf_artifacts()

    def _sign_elf_artifacts(self):
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.exists(sign_tool) and os.path.exists(objcopy)):
            return

        failures = []
        for root, _, files in os.walk(self.package_folder):
            for filename in files:
                path = os.path.join(root, filename)
                try:
                    with open(path, "rb") as handle:
                        if handle.read(4) != b"\x7fELF":
                            continue
                except OSError:
                    continue
                tmp_signed = path + ".signed"
                try:
                    if os.path.exists(tmp_signed):
                        os.remove(tmp_signed)
                    remove_result = subprocess.run(
                        [objcopy, "--remove-section", ".codesign", path],
                        check=False,
                        capture_output=True,
                        text=True,
                    )
                    remove_output = "\n".join(
                        part for part in (remove_result.stdout, remove_result.stderr) if part
                    ).strip()
                    missing_codesign = (
                        ".codesign" in remove_output and "not found" in remove_output.lower()
                    )
                    if remove_result.returncode != 0 and not missing_codesign:
                        detail = remove_output or f"exit code {remove_result.returncode}"
                        failures.append(f"{path}: objcopy failed: {detail}")
                        continue

                    sign_result = subprocess.run(
                        [sign_tool, "sign", "-inFile", path, "-outFile", tmp_signed, "-selfSign", "1"],
                        check=False,
                        capture_output=True,
                        text=True,
                    )
                    if sign_result.returncode != 0 or not os.path.exists(tmp_signed):
                        sign_output = "\n".join(
                            part for part in (sign_result.stdout, sign_result.stderr) if part
                        ).strip()
                        detail = sign_output or f"exit code {sign_result.returncode}"
                        failures.append(f"{path}: signing failed: {detail}")
                        continue

                    os.replace(tmp_signed, path)
                    os.chmod(path, 0o755)
                finally:
                    if os.path.exists(tmp_signed):
                        os.remove(tmp_signed)

        if failures:
            raise RuntimeError("ELF signing failed:\n" + "\n".join(failures))

    def _perl5lib_dirs(self):
        root = os.path.join(self.package_folder, "lib", "perl5")
        bases = [
            os.path.join(root, self.version),
            os.path.join(root, "site_perl", self.version),
            os.path.join(root, "vendor_perl", self.version),
        ]
        arch_names = [
            self._perl_archname(),
            self._perl_archname(threaded=False),
            "aarch64-linux-thread-multi",
            "aarch64-linux",
        ]
        paths = []
        for base in bases:
            for arch_name in arch_names:
                paths.append(os.path.join(base, arch_name))
            paths.append(base)
            if os.path.isdir(base):
                for name in sorted(os.listdir(base)):
                    path = os.path.join(base, name)
                    if os.path.isdir(path):
                        paths.append(path)

        unique = []
        for path in paths:
            if path not in unique:
                unique.append(path)
        return unique

    def _perl_archname(self, threaded=True):
        arch = str(self.settings.arch)
        arch_map = {
            "armv8": "aarch64",
            "armv8.3": "aarch64",
            "x86_64": "x86_64",
            "x86": "i686",
        }
        machine = arch_map.get(arch, arch)
        osname = "linux" if self.settings.os in ("OHOS", "Linux") else str(self.settings.os).lower()
        suffix = "-thread-multi" if threaded else ""
        return f"{machine}-{osname}{suffix}"

    def package_info(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        perl = os.path.join(bin_dir, "perl")

        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]

        self.buildenv_info.prepend_path("PATH", bin_dir)
        self.runenv_info.prepend_path("PATH", bin_dir)
        self.buildenv_info.define("PERL", perl)
        self.runenv_info.define("PERL", perl)
        for path in reversed(self._perl5lib_dirs()):
            self.buildenv_info.prepend_path("PERL5LIB", path)
            self.runenv_info.prepend_path("PERL5LIB", path)
