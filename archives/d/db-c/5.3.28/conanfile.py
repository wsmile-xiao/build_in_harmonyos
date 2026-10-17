#!/usr/bin/env python3
"""Conan recipe for the Berkeley DB 5.3 C API."""

import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    load,
    rm,
    save,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class DbCConan(ConanFile):
    name = "db-c"
    version = "5.3.28"
    description = "Embedded transactional key/value database C API"
    license = "Sleepycat"
    homepage = "https://www.oracle.com/database/technologies/related/berkeleydb.html"
    url = "https://download.oracle.com/berkeley-db/db-5.3.28.tar.gz"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if str(self.settings.os) == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        target_os = str(self.settings.os)
        if target_os not in ("Linux", "OHOS", "Windows"):
            raise ConanInvalidConfiguration(
                f"db-c is validated only for Linux, OHOS, and Windows, not {target_os}"
            )

    def build_requirements(self):
        # Autoconf and make are POSIX commands when Conan runs on Windows.
        settings_build = getattr(self, "settings_build", self.settings)
        if str(settings_build.os) == "Windows":
            self.win_bash = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            filename="db-5.3.28.tar.gz",
            strip_root=True,
        )

    def generate(self):
        target_os = str(self.settings.os)
        settings_build = getattr(self, "settings_build", self.settings)
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--disable-cxx",
                "--disable-java",
                "--disable-jdbc",
                "--disable-tcl",
                "--disable-sql",
                "--disable-sql_compat",
                "--disable-sql_codegen",
                "--disable-stl",
                "--disable-test",
                "--with-cryptography=yes",
                "--enable-shared" if self.options.shared else "--disable-shared",
                "--disable-static" if self.options.shared else "--enable-static",
            ]
        )
        if target_os == "OHOS":
            tc.configure_args.extend(
                ["--host=aarch64-linux-ohos", "--build=x86_64-linux-gnu"]
            )
            # Some workers override generated buildenv files with a shared,
            # non-writable TMPDIR. Bind the recipe process to its build root
            # before configure/package subprocesses are launched.
            os.environ["TMPDIR"] = self._shell_path(self.build_folder)
            self._prepare_mktemp_shim()
            if str(settings_build.os) != "Windows":
                shell = shutil.which("bash") or shutil.which("sh")
                if shell:
                    os.environ["SHELL"] = shell
                    os.environ["CONFIG_SHELL"] = shell
        env = tc.environment()
        # Some OHOS workers expose a shared TMPDIR that is not writable by the
        # package process. Keep Autoconf probes task-local and writable.
        if target_os == "OHOS" and str(settings_build.os) != "Windows":
            env.define("TMPDIR", self._shell_path(self.build_folder))
            env.prepend_path(
                "PATH", self._shell_path(os.path.join(self.build_folder, "bin"))
            )
            shell = shutil.which("bash") or shutil.which("sh")
            if shell:
                env.define("SHELL", shell)
                env.define("CONFIG_SHELL", shell)
        compiler_tools = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        for tool_name, env_name in {
            "ld": "LD",
            "ar": "AR",
            "ranlib": "RANLIB",
            "nm": "NM",
            "strip": "STRIP",
        }.items():
            if tool_name in compiler_tools:
                env.define(env_name, str(compiler_tools[tool_name]).replace("\\", "/"))
        tc.generate(env=env)

    def _prepare_mktemp_shim(self):
        """Create a task-local mktemp shim for ACL-restricted OHOS workers."""
        shim_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(shim_dir, exist_ok=True)
        shim = os.path.join(shim_dir, "mktemp")
        save(
            self,
            shim,
            "#!/bin/sh\n"
            "set -eu\n"
            "if [ \"${1:-}\" = \"-d\" ] && [ $# -ge 2 ]; then\n"
            "  template=\"$2\"\n"
            "  parent=\"${template%/*}\"\n"
            "  base=\"${template##*/}\"\n"
            "  [ \"$parent\" = \"$template\" ] && parent=.\n"
            "  stem=\"${base%XXXXXX}\"\n"
            "  n=0\n"
            "  while :; do\n"
            "    candidate=\"$parent/${stem}$$-$n\"\n"
            "    if (umask 022 && mkdir \"$candidate\") 2>/dev/null; then\n"
            "      chmod 0755 \"$candidate\" 2>/dev/null || true\n"
            "      printf '%s\\n' \"$candidate\"\n"
            "      exit 0\n"
            "    fi\n"
            "    n=$((n + 1))\n"
            "  done\n"
            "fi\n"
            "exec /usr/bin/mktemp \"$@\"\n",
        )
        try:
            os.chmod(shim, 0o755)
        except OSError:
            pass

        # w64devkit does not mount drive letters as /f-style MSYS paths.
        # Conan's generated shell files use those paths, so bind them to the
        # task's native drive paths before the POSIX shell consumes them.

    def _normalize_generated_env(self):
        for filename in (
            "conanbuild.sh",
            "conanautotoolstoolchain.sh",
            "conanbuildenv-release-armv8.sh",
        ):
            path = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(path):
                continue
            content = load(self, path).replace("\\", "/")
            # Conan emits /mnt/f/... on WSL-backed Windows shells.  Match the
            # mount prefix explicitly; a generic /f/... pattern cannot match
            # it because the preceding character is the `t` in /mnt/.
            content = re.sub(
                r"/mnt/([A-Za-z])/",
                lambda match: "%s:/" % match.group(1).upper(),
                content,
            )
            content = re.sub(
                r"(?<![A-Za-z0-9])/(?:([A-Za-z]))/",
                lambda match: "%s:/" % match.group(1).upper(),
                content,
            )
            save(self, path, content)

    @staticmethod
    def _shell_path(path):
        return os.fspath(path).replace("\\", "/")

    @staticmethod
    def _short_windows_path(path):
        """Return a space-free Windows path for tools embedded in Makefiles."""
        normalized = os.path.abspath(os.fspath(path)).replace("\\", "/")
        if os.name != "nt":
            return normalized
        try:
            import ctypes
            from ctypes import wintypes

            get_short_path = ctypes.windll.kernel32.GetShortPathNameW
            get_short_path.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
            get_short_path.restype = wintypes.DWORD
            buffer = ctypes.create_unicode_buffer(32768)
            length = get_short_path(normalized, buffer, len(buffer))
            if length:
                return buffer.value.replace("\\", "/")
        except (AttributeError, OSError):
            pass
        return normalized

    def _run_w64devkit(self, command):
        """Run one Autotools phase through the configured Windows shell."""
        bash = self.conf.get("tools.microsoft.bash:path", check_type=str)
        make = self.conf.get("tools.gnu:make_program", check_type=str)
        # Conan writes the aggregate shell files after generate(); normalize
        # them at the point they are consumed by w64devkit.
        self._normalize_generated_env()
        source_env = self._shell_path(
            os.path.relpath(
                os.path.join(self.generators_folder, "conanbuild.sh"),
                self.build_folder,
            )
        )
        build_root = self._shell_path(self.build_folder)
        shell_script = self._shell_path(
            os.path.join(self.build_folder, "db-c-shell.sh")
        )
        # Keep SHELL/CONFIG_SHELL extensionless and free of spaces.  The
        # task-local wrapper quotes the real w64devkit sh.exe path; exporting
        # the spaced executable directly makes configure invoke config.sub
        # with an unquoted path and return 127.
        compiler_tools = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler_c = compiler_tools.get("c")
        shell_dir = (
            os.path.dirname(os.path.abspath(os.fspath(compiler_c)))
            if compiler_c
            else os.path.dirname(os.path.abspath(os.fspath(make)))
        )
        shell_wrapper = self._shell_path(os.path.join(shell_dir, "sh"))
        bash_bin = self._short_windows_path(
            os.path.dirname(os.path.abspath(os.fspath(bash)))
        )
        toolchain_bin = self._short_windows_path(
            os.path.dirname(os.path.abspath(os.fspath(make)))
        )
        task_bin = self._short_windows_path(
            os.path.join(self.build_folder, "bin")
        )
        shell_exe = self._short_windows_path(os.path.join(toolchain_bin, "sh.exe"))
        make_exe = self._short_windows_path(os.fspath(make))
        helper_exports = []
        for helper in (
            "sed",
            "grep",
            "egrep",
            "fgrep",
            "chmod",
            "cp",
            "install",
            "ln",
            "mkdir",
            "mv",
            "rm",
        ):
            helper_exports.append(
                'export %s="%s"\n'
                % (helper.upper(), self._shell_path(os.path.join(shell_dir, helper)))
            )
        content = (
            "set -e\n"
            "umask 022\n"
            "cd \"%s\"\n" % build_root
            + ". %s\n" % source_env
            + "export PATH=\"%s;%s;%s;$PATH\"\n"
            % (task_bin, toolchain_bin, bash_bin)
            + "export PATH_SEPARATOR=\";\"\n"
            # Autoconf otherwise probes only extensionless tools on Windows.
            + "export ac_executable_extensions=\".exe\"\n"
            + "export MAKE=\"%s\"\n" % make_exe
            + "export SHELL=\"%s\"\n" % shell_exe
            + "export CONFIG_SHELL=\"%s\"\n" % shell_exe
            + "export db_cv_path_sh=\"%s\"\n" % shell_exe
            + "export ac_cv_path_db_cv_path_sh=\"%s\"\n" % shell_exe
            + (
                "export TMPDIR=\"%s\"\n" % self._shell_path(self.build_folder)
                if str(self.settings.os) == "OHOS"
                else ""
            )
            + "".join(helper_exports)
            + command
            + "\n"
        )
        save(self, shell_script, content)
        previous = self.win_bash
        self.win_bash = None
        try:
            return self.run(
                '"%s" "%s"' % (bash, shell_script),
                env=None,
                cwd=self.build_folder,
            )
        finally:
            self.win_bash = previous

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        settings_build = getattr(self, "settings_build", self.settings)
        previous_umask = os.umask(0o022)
        try:
            if str(settings_build.os) == "Windows":
                # Keep Autoconf's srcdir/config_files relative; DOS drive colons
                # are parsed as template separators by config.status.
                configure = self._shell_path(
                    os.path.relpath(
                        os.path.join(self.source_folder, "dist", "configure"),
                        self.build_folder,
                    )
                )
                self._run_w64devkit('"%s" %s' % (configure, autotools._configure_args))
                make = self.conf.get("tools.gnu:make_program", check_type=str)
                self._run_w64devkit(
                    '"%s" library_build -j1' % self._short_windows_path(make)
                )
            elif str(self.settings.os) == "OHOS":
                shell = os.environ.get("CONFIG_SHELL") or shutil.which("bash")
                if not shell:
                    shell = "/bin/sh"
                configure = self._shell_path(
                    os.path.join(self.source_folder, "dist", "configure")
                )
                self.run(
                    'CONFIG_SHELL="%s" SHELL="%s" "%s" "%s" %s'
                    % (shell, shell, shell, configure, autotools._configure_args),
                    cwd=self.build_folder,
                )
                make = self.conf.get(
                    "tools.gnu:make_program", default="make", check_type=str
                )
                self.run(
                    'CONFIG_SHELL="%s" SHELL="%s" "%s" library_build -j1'
                    % (shell, shell, make),
                    cwd=self.build_folder,
                )
            else:
                autotools.configure(build_script_folder=os.path.join(self.source_folder, "dist"))
                autotools.make(target="library_build", args=["-j1"])
        finally:
            os.umask(previous_umask)

    def package(self):
        autotools = Autotools(self)
        settings_build = getattr(self, "settings_build", self.settings)
        previous_umask = os.umask(0o022)
        try:
            if str(settings_build.os) == "Windows":
                make = self.conf.get("tools.gnu:make_program", check_type=str)
                destdir = self._shell_path(self.package_folder)
                self._run_w64devkit(
                    '"%s" library_install -j1 DESTDIR=%s'
                    % (self._short_windows_path(make), destdir)
                )
            elif str(self.settings.os) == "OHOS":
                shell = os.environ.get("CONFIG_SHELL") or shutil.which("bash")
                if not shell:
                    shell = "/bin/sh"
                make = self.conf.get(
                    "tools.gnu:make_program", default="make", check_type=str
                )
                destdir = self._shell_path(self.package_folder)
                self.run(
                    'CONFIG_SHELL="%s" SHELL="%s" "%s" library_install -j1 DESTDIR="%s"'
                    % (shell, shell, make, destdir),
                    cwd=self.build_folder,
                )
            else:
                autotools.install(target="library_install", args=["-j1"])
        finally:
            os.umask(previous_umask)
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        target_os = str(self.settings.os)
        self.cpp_info.set_property("cmake_file_name", "db-c")
        self.cpp_info.set_property("cmake_target_name", "db-c::db-c")
        self.cpp_info.set_property("pkg_config_name", "db-5.3")
        self.cpp_info.libs = ["db-5.3"]
        if target_os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
            if target_os == "Linux":
                self.cpp_info.system_libs.append("dl")
        elif target_os == "Windows":
            self.cpp_info.system_libs = ["advapi32", "ws2_32"]
