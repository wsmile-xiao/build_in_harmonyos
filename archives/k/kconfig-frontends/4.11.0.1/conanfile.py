#!/usr/bin/env python3
"""Conan recipe for the kconfig parser and text frontends."""

import glob
import hashlib
import os
import shlex
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.scm import Git


class KconfigFrontendsConan(ConanFile):
    name = "kconfig-frontends"
    version = "4.11.0.1"
    description = "Standalone Kconfig parser with conf, mconf and nconf text frontends"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.com/ymorin/kconfig-frontends"
    url = "https://gitlab.com/ymorin/kconfig-frontends"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True, "ncurses/*:shared": False}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"kconfig-frontends supports Linux and OHOS, not {self.settings.os}"
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "kconfig-frontends currently supports only OHOS arm64"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # ncurses is deliberately static: a package-local shared copy can
        # shadow HarmonyOS's system curses library (repository rule R4).
        self.requires("ncurses/6.6", options={"shared": False})

    def build_requirements(self):
        # The upstream Git tree does not carry generated configure/Makefile.in.
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")
        self.tool_requires("m4/1.4.19")
        self.tool_requires("bison/3.8.2")
        self.tool_requires("flex/2.6.4.2")
        self.tool_requires("gperf/3.3")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        source = self.conan_data["sources"][self.version]
        git = Git(self, self.source_folder)
        git.clone(url=source["url"], target=".")
        git.checkout(commit=source["commit"])

        # The official source is pinned as a Git commit. Verify a canonical
        # Git archive of that tree against conandata.yml so the source has a
        # SHA256 integrity check as well as an immutable commit identifier.
        archive = os.path.join(self.source_folder, ".kconfig-frontends-source.tar")
        try:
            subprocess.run(
                ["git", "archive", "--format=tar", "--output", archive, source["commit"]],
                cwd=self.source_folder,
                check=True,
            )
            with open(archive, "rb") as source_file:
                digest = hashlib.file_digest(source_file, "sha256").hexdigest()
        finally:
            if os.path.exists(archive):
                os.remove(archive)
        if digest != source["sha256"]:
            raise ConanInvalidConfiguration(
                "Pinned upstream source tree SHA256 mismatch: "
                f"expected {source['sha256']}, got {digest}"
            )

    def _configure_options(self):
        options = [
            "--enable-frontends=conf,mconf,nconf",
            "--disable-kconfig",
            "--disable-utils",
            "--disable-L10n",
        ]
        if self.settings.os == "OHOS":
            # HarmonyOS's native build and target share this supported GNU
            # triplet; config.guess below is also taught to emit it.
            options.extend(
                [
                    "--build=aarch64-unknown-linux-ohos",
                    "--host=aarch64-unknown-linux-ohos",
                ]
            )
        return options

    def _patch_config_guess(self, shell):
        if self.settings.os != "OHOS":
            return
        config_guess = os.path.join(
            self.source_folder, "scripts", ".autostuff", "scripts", "config.guess"
        )
        if not os.path.isfile(config_guess):
            raise ConanInvalidConfiguration(
                f"Autoreconf did not generate config.guess: {config_guess}"
            )

        with open(config_guess, "r", encoding="utf-8") as config_file:
            text = config_file.read()
        marker = "case $UNAME_SYSTEM in\nLinux|GNU|GNU/*)\n"
        harmony_case = (
            "case $UNAME_SYSTEM in\n"
            "HarmonyOS)\n"
            "\tcase $UNAME_MACHINE in\n"
            "\t\taarch64|arm64) GUESS=aarch64-unknown-linux-ohos ;;\n"
            "\t\t*) echo \"config.guess: unsupported HarmonyOS machine: $UNAME_MACHINE\" >&2; exit 1 ;;\n"
            "\tesac\n"
            "\t;;\n"
            "Linux|GNU|GNU/*)\n"
        )
        if harmony_case not in text:
            if text.count(marker) != 1:
                raise ConanInvalidConfiguration(
                    "Generated config.guess has an unexpected platform dispatch"
                )
            text = text.replace(marker, harmony_case, 1)
            with open(config_guess, "w", encoding="utf-8", newline="\n") as config_file:
                config_file.write(text)

        probe = subprocess.run(
            [shell, config_guess],
            cwd=self.source_folder,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if probe.returncode != 0 or probe.stdout.strip() != "aarch64-unknown-linux-ohos":
            raise ConanInvalidConfiguration(
                "Patched config.guess did not detect HarmonyOS: "
                f"exit={probe.returncode}, stdout={probe.stdout.strip()!r}, "
                f"stderr={probe.stderr.strip()!r}"
            )

    def _restore_autotools_helper_modes(self):
        if self.settings.os != "OHOS":
            return

        helper_names = {
            "configure",
            "config.guess",
            "config.sub",
            "install-sh",
            "missing",
            "compile",
            "depcomp",
            "ylwrap",
            "ar-lib",
            "ltmain.sh",
        }
        restored = 0
        for root in (self.recipe_folder, self.source_folder, self.build_folder):
            for directory, _, filenames in os.walk(root):
                for filename in filenames:
                    if filename not in helper_names:
                        continue
                    path = os.path.join(directory, filename)
                    try:
                        mode = os.lstat(path).st_mode
                        if not stat.S_ISREG(mode) or mode & 0o111 == 0o111:
                            continue
                        os.chmod(path, mode | 0o111)
                    except OSError as error:
                        raise ConanInvalidConfiguration(
                            f"Could not restore execute bits on Autotools helper {path}: {error}"
                        ) from error
                    restored += 1

        self.output.info(
            f"Restored execute bits on {restored} known Autotools helper script(s)"
        )

    def generate(self):
        # configure.ac probes curses headers and symbols directly, so expose
        # ncurses' Conan include/library paths to configure and the link steps.
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(self._configure_options())
        tc.parallel = False
        tc.generate()
        VirtualBuildEnv(self).generate()

    def _shell(self):
        candidates = [
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            "/bin/sh",
            shutil.which("bash"),
            shutil.which("sh"),
        ]
        seen = set()
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            try:
                probe = subprocess.run(
                    [candidate, "-c", "pwd >/dev/null"],
                    cwd=self.build_folder,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False,
                )
            except OSError:
                continue
            if probe.returncode == 0 and not probe.stdout and not probe.stderr:
                return candidate.replace("\\", "/")
        raise ConanInvalidConfiguration(
            "No shell can run pwd without diagnostics from the Conan build folder"
        )

    def _configure_args(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(self._configure_options())
        return shlex.join(tc.configure_args)

    def _prepare_build_environment(self, shell):
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        os.environ["CONFIG_SHELL"] = shell
        os.environ["SHELL"] = shell
        os.environ["TERM"] = "xterm"
        return tmpdir

    def build(self):
        apply_conandata_patches(self)
        bash = self._shell()
        self._prepare_build_environment(bash)

        # The official Git source contains configure.ac but not generated
        # Autotools files. Conan tool requirements provide this bootstrap.
        autoreconf = "autoreconf"
        bootstrap_env = (
            f"CONFIG_SHELL={shlex.quote(bash)} SHELL={shlex.quote(bash)} "
        )
        if self.settings.os == "OHOS":
            # HarmonyOS's HNP Automake scripts can carry a shebang for the
            # system Perl while Conan exports PERL5LIB for its own Perl build
            # requirement. Run those Perl entry points with Conan's matching
            # interpreter instead of mixing the two runtimes.
            autoconf_package = self.dependencies.build["autoconf"].package_folder
            automake_package = self.dependencies.build["automake"].package_folder
            perl_package = self.dependencies.build["perl"].package_folder
            automake_libdirs = glob.glob(
                os.path.join(automake_package, "share", "automake-*")
            )
            if len(automake_libdirs) != 1:
                raise ConanInvalidConfiguration(
                    "Expected one Automake Perl library directory in the OHOS build requirement"
                )

            automake_libdir = automake_libdirs[0]
            automake_acdir = os.path.join(automake_package, "share", "aclocal-1.18")
            automake_system_acdir = os.path.join(automake_package, "share", "aclocal")
            perl = os.path.join(perl_package, "bin", "perl")
            tool_wrappers = os.path.join(self.build_folder, "tmp", "autotools-perl")
            os.makedirs(tool_wrappers, exist_ok=True)

            wrapper_specs = {
                "aclocal": (
                    os.path.join(automake_package, "bin", ".aclocal-real"),
                    [
                        f"--automake-acdir={automake_acdir}",
                        f"--system-acdir={automake_system_acdir}",
                    ],
                ),
                "automake": (
                    os.path.join(automake_package, "bin", ".automake-real"),
                    [f"--libdir={automake_libdir}"],
                ),
            }
            for name, (script, args) in wrapper_specs.items():
                if not os.path.isfile(script):
                    raise ConanInvalidConfiguration(
                        f"The OHOS Automake package is missing its {name} Perl entry point"
                    )
                wrapper = os.path.join(tool_wrappers, name)
                wrapper_command = " ".join(
                    [shlex.quote(perl), shlex.quote(script)]
                    + [shlex.quote(arg) for arg in args]
                    + ['"$@"']
                )
                with open(wrapper, "w", encoding="utf-8") as wrapper_file:
                    wrapper_file.write(f"#!/bin/sh\nexec {wrapper_command}\n")
                os.chmod(wrapper, 0o755)
                bootstrap_env += f"{name.upper()}={shlex.quote(wrapper)} "

            autoreconf = os.path.join(autoconf_package, "bin", "autoreconf")
            if not os.path.isfile(autoreconf):
                raise ConanInvalidConfiguration(
                    "The OHOS Autoconf build requirement is missing autoreconf"
                )
            autoreconf = shlex.quote(autoreconf)

        bootstrap = f"{shlex.quote(bash)} -c {shlex.quote(f'umask 022 && {bootstrap_env}{autoreconf} -fi')}"
        self.run(bootstrap, cwd=self.source_folder, env="conanbuild")
        self._restore_autotools_helper_modes()
        self._patch_config_guess(bash)

        configure = os.path.join(self.source_folder, "configure").replace("\\", "/")
        configure_command = (
            f"SHELL={shlex.quote(bash)} CONFIG_SHELL={shlex.quote(bash)} "
            f"{shlex.quote(bash)} "
            f"{shlex.quote(configure)} {self._configure_args()}"
        )
        command = f"{shlex.quote(bash)} -c {shlex.quote('umask 022 && ' + configure_command)}"
        self.run(command, cwd=self.build_folder, env="conanbuild")

        autotools = Autotools(self)
        autotools.make(args=["-j1", f"SHELL={bash}"])
        if can_run(self):
            # The upstream tree has no registered tests; keep the conventional
            # target as a build-system regression check. Functional coverage is
            # supplied by test_package and documented in notes.md.
            autotools.make(target="check", args=["-j1", f"SHELL={bash}"])
        else:
            self.output.warning("cross-build: upstream make check skipped")

    def package(self):
        bash = self._shell()
        Autotools(self).install(args=[f"SHELL={bash}"])
        for path in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(path)
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["kconfig-parser"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.defines = ["KBUILD_NO_NLS"]
        self.cpp_info.set_property("pkg_config_name", "kconfig-parser")
        self.cpp_info.set_property("cmake_file_name", "kconfig-parser")
        self.cpp_info.set_property("cmake_target_name", "kconfig-parser::kconfig-parser")
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
