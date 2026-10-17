#!/usr/bin/env python3
"""Conan recipe for Hamlib 4.7.2."""

import glob
import ctypes
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import (
    apply_conandata_patches,
    check_sha256,
    copy,
    download,
    load,
    save,
    unzip,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class HamlibConan(ConanFile):
    # Conan runs Autotools through the configured POSIX subsystem when the
    # build profile is Windows-hosted.  Without this declaration, a Windows
    # host invokes the POSIX configure script through cmd.exe and fails before
    # any source compilation starts.
    win_bash = True
    name = "hamlib"
    version = "4.7.2"
    description = "Library and command-line tools for controlling amateur radio equipment"
    license = "LGPL-2.1-or-later"
    homepage = "https://hamlib.github.io/"
    url = "https://github.com/Hamlib/Hamlib"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("Hamlib supports Linux and OHOS only")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS Hamlib builds require armv8/aarch64")
        if self.settings.os == "OHOS" and self.options.shared:
            raise ConanInvalidConfiguration("OHOS Hamlib builds are static to avoid system library collisions")

    def layout(self):
        basic_layout(self)

    def source(self):
        source = self.conan_data["sources"]
        archive = os.path.join(self.source_folder, "hamlib-4.7.2.tar.gz")
        configured_archive = self.conf.get("user.hamlib:source_archive", default=None)
        if configured_archive:
            configured_archive = os.path.abspath(os.fspath(configured_archive))
            if not os.path.isfile(configured_archive):
                raise ConanInvalidConfiguration(
                    "user.hamlib:source_archive does not name a regular file"
                )
            check_sha256(self, configured_archive, source["sha256"])
            if os.path.normcase(configured_archive) != os.path.normcase(os.path.abspath(archive)):
                shutil.copy2(configured_archive, archive)
            check_sha256(self, archive, source["sha256"])
        else:
            download(self, source["url"], archive, sha256=source["sha256"])
        unzip(self, archive, destination=self.source_folder, strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--without-libusb",
            "--without-readline",
            "--disable-html-matrix",
            "--disable-winradio",
            "--disable-parallel",
        ])
        if self.settings.os == "OHOS" and not str(self.settings_build.os).startswith("Windows"):
            # HMDFS may reject config.guess's temporary probe executable.
            # The target triplet is already fixed by the Conan OHOS profile.
            tc.configure_args.append("--build=aarch64-linux-ohos")
        if str(self.settings_build.os).startswith("Windows"):
            # The Windows LLVM driver prints a space-containing native linker
            # path during libtool's optional global-symbol probe.  This probe
            # is irrelevant for the static-only OHOS package and fails before
            # compilation under w64devkit, so seed its cache variables.
            tc.configure_args.extend([
                "lt_cv_nm_interface=BSD",
                "lt_cv_sys_global_symbol_pipe=cat",
                "lt_cv_sys_global_symbol_to_cdecl=cat",
            ])
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
        else:
            tc.configure_args.append("--disable-shared")
        env = None
        if str(self.settings_build.os).startswith("Windows"):
            compiler_executables = self.conf.get(
                "tools.build:compiler_executables", default={}
            ) or {}
            compiler = compiler_executables.get("c")
            if compiler:
                tool_dir = os.path.dirname(os.path.abspath(os.fspath(compiler)))
                env = tc.environment()
                for variable, wrapper in (
                    ("LD", "ld.sh"),
                    ("AR", "ar.sh"),
                    ("RANLIB", "ranlib.sh"),
                    ("NM", "nm.sh"),
                    ("STRIP", "strip.sh"),
                ):
                    candidate = os.path.join(tool_dir, wrapper)
                    if os.path.isfile(candidate):
                        env.define(variable, candidate.replace("\\", "/"))
        tc.generate(env=env)
        # Conan's Windows/MSYS generator writes the generators directory with
        # native backslashes into conanautotoolstoolchain.sh.  Bash cannot
        # source that path, so normalize only this generated script's own
        # directory references after generation.
        if str(self.settings_build.os).startswith("Windows"):
            toolchain_env = os.path.join(
                self.generators_folder, "conanautotoolstoolchain.sh"
            )
            if os.path.isfile(toolchain_env):
                content = load(self, toolchain_env)
                content = content.replace(
                    self.generators_folder,
                    self.generators_folder.replace("\\", "/"),
                )
                content = content.replace(
                    self.generators_folder.replace("\\", "/"),
                    "/" + self.generators_folder[0].lower()
                    + self.generators_folder[2:].replace("\\", "/"),
                )
                content = content.replace('"$script_folder\\', '"$script_folder/')
                content = re.sub(
                    r'"/([A-Za-z])/',
                    lambda match: f'"{match.group(1).upper()}:/',
                    content,
                )
                save(self, toolchain_env, content)

    def _run_w64devkit(self, command):
        """Run one build command under the task's w64devkit Bash wrapper."""
        bash = self.conf.get("tools.microsoft.bash:path", check_type=str)
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}
        ) or {}
        compiler = compiler_executables.get("c")
        compiler_dir = (
            os.path.dirname(os.path.abspath(os.fspath(compiler)))
            if compiler
            else ""
        )
        make = self.conf.get("tools.gnu:make_program", check_type=str)
        make_dir = os.path.dirname(os.path.abspath(os.fspath(make)))
        bash_dir = os.path.dirname(os.path.abspath(os.fspath(bash)))
        path_dirs = []
        for directory in (compiler_dir, make_dir, bash_dir):
            normalized = directory.replace("\\", "/")
            if normalized and normalized not in path_dirs:
                path_dirs.append(normalized)
        shell_wrapper = os.path.join(self.build_folder, "hamlib-shell.sh")
        bash_path = bash.replace("\\", "/")
        save(
            self,
            shell_wrapper,
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            f'exec "{bash_path}" "$@"\n',
        )
        shell_path = os.path.abspath(shell_wrapper)
        if os.name == "nt":
            try:
                buffer = ctypes.create_unicode_buffer(32768)
                length = ctypes.windll.kernel32.GetShortPathNameW(
                    shell_path, buffer, len(buffer)
                )
                if length:
                    shell_path = buffer.value
            except (AttributeError, OSError):
                pass
        shell_path = shell_path.replace("\\", "/")
        exports = [
            f'export PATH="{";".join(path_dirs)}"',
            f'export MAKE="{make.replace(chr(92), "/")}"',
            f'export SHELL="{shell_path}"',
            f'export CONFIG_SHELL="{shell_path}"',
        ]
        for variable, executable in (
            ("SED", "sed"),
            ("GREP", "grep"),
            ("EGREP", "egrep"),
            ("FGREP", "fgrep"),
        ):
            candidate = (
                os.path.join(compiler_dir, executable)
                if compiler_dir
                else ""
            )
            if not os.path.isfile(candidate):
                candidate = shutil.which(executable) or ""
            if candidate:
                exports.append(
                    f'export {variable}="{candidate.replace(chr(92), "/")}"'
                )
        env_script = os.path.join(
            self.generators_folder, "conanautotoolstoolchain.sh"
        ).replace("\\", "/")
        command_script = os.path.join(
            self.build_folder, "hamlib-w64devkit-command.sh"
        )
        script = (
            f'cd "{self.source_folder.replace(chr(92), "/")}"\n'
            f'. "{env_script}"\n'
            + "".join(f"{line}\n" for line in exports)
            + f'{command}\n'
        )
        save(self, command_script, script)
        command_script = command_script.replace("\\", "/")
        previous = self.win_bash
        self.win_bash = None
        try:
            return self.run(
                f'"{bash}" "{command_script}"',
                env=None,
                cwd=self.source_folder,
            )
        finally:
            self.win_bash = previous

    def _normalize_generated_make_shell(self):
        """Keep recursive Automake rules on Bash in the Windows host build."""
        for current, _, files in os.walk(self.source_folder):
            if "Makefile" not in files:
                continue
            makefile = os.path.join(current, "Makefile")
            content = load(self, makefile)
            lines = content.splitlines(keepends=True)
            updated = []
            changed = False
            for line in lines:
                if line.startswith("SHELL = "):
                    shell_wrapper = os.path.join(
                        self.build_folder, "hamlib-shell.sh"
                    ).replace("\\", "/")
                    updated.append(f"SHELL = {shell_wrapper}\n")
                    changed = True
                else:
                    updated.append(line)
            if changed:
                save(self, makefile, "".join(updated))

    def _fix_hmdfs_configure_tmpdir(self):
        """Keep config.status temporary files writable on native OHOS HMDFS."""
        if self.settings.os != "OHOS" or str(self.settings_build.os).startswith("Windows"):
            return
        configure = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure):
            raise ConanInvalidConfiguration("Hamlib configure script is missing")
        content = load(self, configure)
        replacements = (
            (
                'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
                'tmp=`(umask 022 && mktemp -d "${TMPDIR:-.}/confXXXXXX") 2>/dev/null`',
            ),
            (
                'tmp=./conf$$-$RANDOM\n  (umask 077 && mkdir "$tmp")',
                'tmp="${TMPDIR:-.}/conf$$-$RANDOM"\n  (umask 022 && mkdir "$tmp")',
            ),
        )
        for old, new in replacements:
            if content.count(old) != 1:
                raise ConanInvalidConfiguration(
                    "Hamlib configure HMDFS temporary-directory anchor drifted"
                )
            content = content.replace(old, new)
        save(self, configure, content)

    def _regenerate_autotools(self):
        """Regenerate configure/config.h.in after the capability checks patch."""
        if not os.path.isfile(os.path.join(self.source_folder, "configure.ac")):
            return

        config_sub = os.path.join(self.source_folder, "build-aux", "config.sub")
        if not os.path.isfile(config_sub):
            raise ConanInvalidConfiguration("Hamlib build-aux/config.sub is missing")
        config_sub_backup = os.path.join(self.build_folder, "hamlib-config.sub.saved")
        shutil.copy2(config_sub, config_sub_backup)
        try:
            autoreconf = shutil.which("autoreconf")
            aclocal = shutil.which("aclocal")
            autoconf = shutil.which("autoconf")
            autoheader = shutil.which("autoheader")
            if autoreconf and aclocal:
                result = subprocess.run(
                    [autoreconf, "-fi"], cwd=self.source_folder, check=False
                )
                if result.returncode != 0:
                    raise ConanInvalidConfiguration(
                        f"autoreconf failed with exit code {result.returncode}"
                    )
                return

            if autoconf and autoheader:
                for tool in (autoconf, autoheader):
                    result = subprocess.run(
                        [tool, "-f"], cwd=self.source_folder, check=False
                    )
                    if result.returncode != 0:
                        raise ConanInvalidConfiguration(
                            f"{os.path.basename(tool)} failed with exit code "
                            f"{result.returncode}"
                        )
                return

            if not str(self.settings_build.os).startswith("Windows"):
                raise ConanInvalidConfiguration(
                    "Hamlib capability checks require autoreconf in the build environment"
                )

            wsl = shutil.which("wsl.exe") or shutil.which("wsl")
            if not wsl:
                raise ConanInvalidConfiguration(
                    "Hamlib capability checks require autoreconf or WSL on Windows"
                )

            source_path = os.path.abspath(self.source_folder).replace("\\", "/")
            source_posix = "/mnt/" + source_path[0].lower() + source_path[2:]
            autoreconf_script = os.path.join(
                self.build_folder, "hamlib-autoreconf.sh"
            )
            save(
                self,
                autoreconf_script,
                "#!/bin/sh\n"
                f"cd '{source_posix}'\n"
                "exec autoreconf -fi\n",
            )
            script_path = os.path.abspath(autoreconf_script).replace("\\", "/")
            script_posix = "/mnt/" + script_path[0].lower() + script_path[2:]
            previous = self.win_bash
            self.win_bash = None
            try:
                result = subprocess.run(
                    [wsl, "bash", script_posix], cwd=self.source_folder, check=False
                )
            finally:
                self.win_bash = previous
            if result.returncode != 0:
                raise ConanInvalidConfiguration(
                    f"WSL autoreconf failed with exit code {result.returncode}"
                )
        finally:
            shutil.copy2(config_sub_backup, config_sub)

    def build(self):
        apply_conandata_patches(self)
        self._regenerate_autotools()
        self._fix_hmdfs_configure_tmpdir()
        autotools = Autotools(self)
        if str(self.settings_build.os).startswith("Windows"):
            configure = os.path.join(self.source_folder, "configure").replace("\\", "/")
            make = self.conf.get("tools.gnu:make_program", check_type=str)
            configure_args = autotools._configure_args.replace(
                "--build=x86_64-unknown-windows", "--build=x86_64-pc-linux"
            )
            self._run_w64devkit(f'"{configure}" {configure_args}')
            self._normalize_generated_make_shell()
            self._run_w64devkit(
                f'"{make}" -j1'
            )
        else:
            autotools.configure()
            autotools.make(
                args=["-j1", "ACLOCAL=true", "AUTOMAKE=true", "AUTOHEADER=true"]
            )
        if can_run(self):
            autotools.make(
                target="check",
                args=["-j1", "ACLOCAL=true", "AUTOMAKE=true", "AUTOHEADER=true"],
            )
        else:
            self.output.info("Hamlib upstream make check deferred to target-side validation while cross-building")

    def package(self):
        autotools = Autotools(self)
        if str(self.settings_build.os).startswith("Windows"):
            make = self.conf.get("tools.gnu:make_program", check_type=str)
            self._run_w64devkit(
                f'"{make}" install INSTALL=install '
                f'DESTDIR="{self.package_folder.replace(chr(92), "/")}"'
            )
        else:
            autotools.install(
                args=[
                    "INSTALL=install",
                    "ACLOCAL=true",
                    "AUTOMAKE=true",
                    "AUTOHEADER=true",
                ]
            )
        copy(self, "COPYING*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "include", "hamlib"),
            dst=os.path.join(self.package_folder, "include", "hamlib"),
        )
        for executable in (
            "rigctl",
            "rigctld",
            "rigmem",
            "rigsmtr",
            "rigswr",
            "rotctl",
            "rotctld",
            "rigctlcom",
            "rigctltcp",
            "rigctlsync",
            "ampctl",
            "ampctld",
            "rigtestmcast",
            "rigtestmcastrx",
        ):
            copy(
                self,
                executable,
                src=os.path.join(self.source_folder, "tests"),
                dst=os.path.join(self.package_folder, "bin"),
                keep_path=False,
            )
        for path in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(path)

    def package_info(self):
        self.cpp_info.libs = ["hamlib", "hamlib++"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("pkg_config_name", "hamlib")
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
