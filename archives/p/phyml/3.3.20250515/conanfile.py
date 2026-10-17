"""PhyML 3.3.20250515 phylogenetic inference tool for HarmonyOS PC."""

import hashlib
import os
import re
import shlex
import shutil
import stat
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, get, unzip
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PhymlConan(ConanFile):
    name = "phyml"
    version = "3.3.20250515"
    description = "Maximum-likelihood phylogenetic tree inference"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/stephaneguindon/phyml"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def build_requirements(self):
        self.tool_requires("autoconf/2.72")
        self.tool_requires("automake/1.18")
        self.tool_requires("perl/5.42.2")
        self.tool_requires("m4/1.4.19")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        local_archive = os.environ.get("PHYML_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).resolve(strict=True)
            with archive.open("rb") as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
            expected = self.conan_data["sources"][self.version]["sha256"]
            if actual != expected:
                raise ConanException("PHYML_SOURCE_ARCHIVE SHA-256 mismatch")
            unzip(self, str(archive), destination=self.source_folder, strip_root=True)
        else:
            get(self, **self.conan_data["sources"][self.version], strip_root=True)

    @staticmethod
    def _replace_count(path, old, new, count):
        text = path.read_text(encoding="utf-8")
        if text.count(old) != count:
            raise ConanException(f"unexpected PhyML Autoconf template: {old}")
        path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")

    def _preserve_toolchain_flags(self):
        configure_ac = Path(self.source_folder) / "configure.ac"
        self._replace_count(configure_ac, 'LDFLAGS="${ARGC_flag}"',
                            'LDFLAGS="${LDFLAGS} ${ARGC_flag}"', 1)
        self._replace_count(configure_ac, 'CFLAGS="${DEFAULT_C_FLAG}"',
                            'CFLAGS="${CFLAGS} ${DEFAULT_C_FLAG}"', 3)

    def _remove_upstream_configured_outputs(self):
        # The official source snapshot unexpectedly contains outputs from an
        # earlier machine. Leaving config.status makes Automake reject a fresh
        # configure, and leaving Makefiles risks using its old compiler flags.
        root = Path(self.source_folder)
        for relative in (
            "Makefile", "config.h", "config.log", "config.status",
            "doc/Makefile", "src/Makefile", "stamp-h1",
        ):
            generated = root / relative
            if not generated.is_file() or generated.is_symlink():
                raise ConanException(f"expected ordinary generated file: {generated}")
            generated.unlink()

    def _bind_native_ohos_tuple(self):
        executables = self.conf.get("tools.build:compiler_executables", default={})
        compiler = executables.get("c") or shutil.which("clang")
        if not compiler:
            raise ConanException("OHOS C compiler is unavailable")
        target = subprocess.run([compiler, "-dumpmachine"], capture_output=True,
                                text=True, check=True, timeout=15).stdout.strip()
        if not re.fullmatch(r"aarch64-[A-Za-z0-9_.-]*linux-ohos", target):
            raise ConanException(f"compiler did not prove an OHOS/aarch64 tuple: {target}")
        guess = Path(self.source_folder) / "config.guess"
        if not guess.is_file() or guess.is_symlink():
            raise ConanException("config.guess is not an ordinary file")
        sub = Path(self.source_folder) / "config.sub"
        shell = shutil.which("sh") or "/bin/sh"
        if not Path(shell).is_file():
            raise ConanException("a POSIX shell is required for config.sub")
        check = subprocess.run([shell, str(sub), target], capture_output=True,
                               text=True, check=True, timeout=15)
        if check.stdout.strip() != target:
            raise ConanException("generated config.sub changed the compiler tuple")
        mode = guess.stat().st_mode
        guess.write_text("#!/bin/sh\nprintf '%s\\n' '" + target + "'\n",
                         encoding="utf-8", newline="\n")
        guess.chmod(mode | stat.S_IXUSR)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(["--enable-phyml", "--disable-native"])
        tc.generate()
        VirtualBuildEnv(self).generate()

    def _autotools_entrypoints(self):
        # Conan Automake carries raw Perl programs behind wrappers whose
        # shebangs can point at the package producer's machine. Use the actual
        # build-host interpreter and the relocated pure-Perl module paths.
        perl = shutil.which("perl")
        if not perl:
            raise ConanException("build-host Perl is required for Autotools")
        perl = Path(perl).resolve()
        cached_perl = Path(self.dependencies.build["perl"].package_folder, "bin", "perl").resolve()
        if self.settings_build.os == "OHOS" and perl == cached_perl:
            raise ConanException("Autotools must not load Perl XS modules from the OHOS cache")
        automake = Path(self.dependencies.build["automake"].package_folder)
        autoconf = Path(self.dependencies.build["autoconf"].package_folder)
        overlay = Path(self.build_folder, ".phyml-autotools")
        overlay.mkdir(mode=0o770, exist_ok=False)
        result = {"perl": perl, "autoreconf": autoconf / "bin" / "autoreconf"}
        for name, arguments in (
            ("aclocal", ["--automake-acdir=" + str(automake / "share" / "aclocal-1.18"),
                         "--system-acdir=" + str(automake / "share" / "aclocal")]),
            ("automake", ["--libdir=" + str(automake / "share" / "automake-1.18")]),
        ):
            raw = automake / "bin" / ("." + name + "-real")
            if not raw.is_file():
                raise ConanException("Automake raw tool is unavailable: " + str(raw))
            wrapper = overlay / name
            command = " ".join(shlex.quote(str(part)) for part in (perl, raw, *arguments))
            descriptor = os.open(wrapper, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o770)
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                stream.write("#!/bin/sh\nexec " + command + ' "$@"\n')
            result[name] = wrapper
        if not result["autoreconf"].is_file():
            raise ConanException("Autoconf autoreconf tool is unavailable")
        result["perl5lib"] = ":".join((str(automake / "share" / "automake-1.18"),
                                      str(autoconf / "share" / "autoconf")))
        return result

    def build(self):
        self._remove_upstream_configured_outputs()
        self._preserve_toolchain_flags()
        tools = self._autotools_entrypoints()
        command = ("ACLOCAL=" + shlex.quote(str(tools["aclocal"])) +
                   " AUTOMAKE=" + shlex.quote(str(tools["automake"])) +
                   " PERL=" + shlex.quote(str(tools["perl"])) +
                   " PERL5LIB=" + shlex.quote(tools["perl5lib"]) +
                   " " + shlex.quote(str(tools["autoreconf"])) + " --force --install")
        self.run(command, cwd=self.source_folder, env="conanbuild")
        if self.settings.os == "OHOS":
            self._bind_native_ohos_tuple()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        if can_run(self):
            autotools.make(target="check", args=["-j1"])
            self.output.info("PHYML_UPSTREAM_0_OF_0_MAKE_CHECK_PASS")

    def package(self):
        Autotools(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        binary = Path(self.package_folder) / "bin" / "phyml"
        if not binary.is_file():
            raise ConanException(f"installed PhyML executable missing: {binary}")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
