"""OATH Toolkit's liboath and oathtool for HarmonyOS PC."""

import hashlib
import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import copy, get, unzip
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class OathConan(ConanFile):
    name = "oath"
    version = "2.6.14"
    description = "OATH one-time-password library and command-line tool"
    license = "LGPL-2.1-or-later AND GPL-3.0-or-later"
    homepage = "https://oath-toolkit.codeberg.page/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder=".")

    def build_requirements(self):
        # The upstream usersfile test deliberately moves time into 2006.
        # Both tools are published for OHOS; keeping them build-only avoids
        # introducing a runtime dependency on a test fixture.
        self.tool_requires("datefudge/1.27")
        self.tool_requires("coreutils/9.10")

    def source(self):
        local_archive = os.environ.get("OATH_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).resolve(strict=True)
            with archive.open("rb") as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
            expected = self.conan_data["sources"][self.version]["sha256"]
            if actual != expected:
                raise ConanException("OATH_SOURCE_ARCHIVE SHA-256 mismatch")
            unzip(self, str(archive), destination=self.source_folder, strip_root=True)
        else:
            get(self, **self.conan_data["sources"][self.version], strip_root=True)

    @staticmethod
    def _replace_exact(path, old, new):
        text = path.read_text(encoding="utf-8")
        if text.count(old) != 1:
            raise ConanException(f"unexpected Autotools template in {path}: {old[:60]!r}")
        path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")

    def _adapt_autotools(self):
        """Keep config.guess/sub honest about OHOS; never spoof --host/--build."""
        root = Path(self.source_folder)
        for prefix in (Path("."), Path("liboath")):
            aux = root / prefix / "build-aux"
            guess = aux / "config.guess"
            sub = aux / "config.sub"
            self._replace_exact(
                guess,
                "#if defined(__ANDROID__)\n\tLIBC=android\n\t#else",
                "#if defined(__ANDROID__)\n\tLIBC=android\n"
                "#elif defined(__OHOS__)\n\tLIBC=ohos\n\t#else",
            )
            self._replace_exact(
                guess,
                "case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in\n"
                "    *:NetBSD:*:*)",
                "case $UNAME_MACHINE:$UNAME_SYSTEM:$UNAME_RELEASE:$UNAME_VERSION in\n"
                "    *:HarmonyOS:*:*)\n"
                "\tcase \"$UNAME_MACHINE\" in\n"
                "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
                "\t    x86_64|amd64) MACHINE=x86_64 ;;\n"
                "\t    *) MACHINE=\"$UNAME_MACHINE\" ;;\n"
                "\tesac\n"
                "\tGUESS=${MACHINE}-unknown-linux-ohos\n\t;;\n"
                "    *:NetBSD:*:*)",
            )
            self._replace_exact(
                sub,
                "\t\t\tandroid-linux)\n\t\t\t\tbasic_machine=$field1-unknown\n"
                "\t\t\t\tbasic_os=linux-android\n\t\t\t\t;;",
                "\t\t\tandroid-linux)\n\t\t\t\tbasic_machine=$field1-unknown\n"
                "\t\t\t\tbasic_os=linux-android\n\t\t\t\t;;\n"
                "\t\t\tohos-linux)\n\t\t\t\tbasic_machine=$field1-unknown\n"
                "\t\t\t\tbasic_os=linux-ohos\n\t\t\t\t;;",
            )
            self._replace_exact(sub, "gnu* | android* | bsd* |",
                                "gnu* | android* | ohos* | bsd* |")
            self._replace_exact(sub, "linux-relibc*- | linux-uclibc*- )",
                                "linux-ohos*- | linux-relibc*- | linux-uclibc*- )")

        # On HMDFS, config.status cannot write into its own mode-0700 temp
        # directory when the numeric owner changes between mount views.
        for relative in ("configure", "liboath/configure"):
            configure = root / relative
            self._replace_exact(configure, '(umask 077 && mktemp -d "./confXXXXXX")',
                                '(umask 022 && mktemp -d "./confXXXXXX")')
            self._replace_exact(
                configure,
                'tmp=./conf$$-$RANDOM\n  (umask 077 && mkdir "$tmp")',
                'tmp=./conf$$-$RANDOM\n  (umask 022 && mkdir "$tmp")',
            )

        # The OHOS fortify header rejects an unbounded complement, although
        # umask only consumes the low nine POSIX permission bits. Masking to
        # 0777 preserves the intended mode without disabling the API.
        self._replace_exact(
            root / "liboath" / "usersfile.c",
            "umask (~(S_IRUSR | S_IWUSR))",
            "umask (0777 & ~(S_IRUSR | S_IWUSR))",
        )

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--disable-pam",  # HarmonyOS has no Linux-PAM service stack.
            "--disable-pskc",  # libpskc is a separate published package.
            "--disable-gtk-doc",
            "--disable-gcc-warnings",
            "--enable-shared" if self.options.shared else "--disable-shared",
            "--disable-static" if self.options.shared else "--enable-static",
        ])
        if self.settings.os == "OHOS":
            env = tc.environment()
            # The contest worker has Bash, but the currently available PC
            # exposes only /bin/sh. The released configure is POSIX shell.
            env.define("CONFIG_SHELL", "/bin/sh")
            env.define("SHELL", "/bin/sh")
            # Some OHOS installations expose LLVM binutils only under their
            # llvm-* names. Autoconf otherwise guesses the MSVC "link -lib".
            ar = shutil.which("llvm-ar") or shutil.which("ar")
            ranlib = shutil.which("llvm-ranlib") or shutil.which("ranlib")
            if not ar or not ranlib:
                raise ConanException("an archiver and ranlib are required")
            env.define("AR", ar)
            env.define("RANLIB", ranlib)
            for variable, preferred, fallback in (
                ("LD", "ld.lld", "ld"),
                ("NM", "llvm-nm", "nm"),
                ("OBJDUMP", "llvm-objdump", "objdump"),
                ("STRIP", "llvm-strip", "strip"),
            ):
                executable = shutil.which(preferred) or shutil.which(fallback)
                if not executable:
                    raise ConanException(f"{variable} tool is unavailable")
                env.define(variable, executable)
            tc.generate(env=env)
        else:
            tc.generate()

    def build(self):
        if self.settings.os == "OHOS":
            self._adapt_autotools()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        if can_run(self):
            # Both upstream subprojects are retained: liboath has nine tests
            # and oathtool has two shell tests. A failure is never downgraded.
            test_env = Environment()
            for name in ("datefudge", "coreutils"):
                dependency = self.dependencies.build[name]
                executable_dir = os.path.join(dependency.package_folder, "bin")
                if not os.path.isdir(executable_dir):
                    raise ConanException(f"missing {name} test executable directory")
                test_env.prepend_path("PATH", executable_dir)
            with test_env.vars(self).apply():
                autotools.make(target="check", args=["-j1"])

    def package(self):
        Autotools(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        expected = os.path.join(self.package_folder, "include", "liboath", "oath.h")
        if not os.path.isfile(expected):
            raise ConanException(f"missing installed header: {expected}")

    def package_info(self):
        self.cpp_info.libs = ["oath"]
        self.cpp_info.set_property("pkg_config_name", "liboath")
        self.cpp_info.set_property("cmake_file_name", "oath")
        self.cpp_info.set_property("cmake_target_name", "oath::oath")
