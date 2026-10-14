from conan.tools.files import replace_in_file
from conan.tools.env import Environment
"""DSSI 1.1.1 plugin API, sample modules, and upstream test."""

import hashlib
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class DssiConan(ConanFile):
    name = "dssi"
    version = "1.1.1"
    package_type = "header-library"
    description = "Disposable Soft Synth Interface and example plugins"
    homepage = "https://dssi.sourceforge.net/"
    license = "LGPL-2.1-or-later AND GPL-2.0-or-later"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    def requirements(self):
        self.requires("alsa-lib/1.2.16.1")
        self.requires("ladspa-sdk/1.17")

    def build_requirements(self):
        self.tool_requires("bash/5.3")

    def layout(self):
        basic_layout(self)

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local_archive = os.environ.get("DSSI_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).resolve(strict=True)
            if not archive.is_file():
                raise ConanInvalidConfiguration("local DSSI source archive is not a file")
            source["url"] = archive.as_uri()
            source["filename"] = archive.name
        get(self, **source, strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        AutotoolsDeps(self).generate()
        AutotoolsToolchain(self).generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    @staticmethod
    def _sign_elf(path):
        signer = shutil.which("binary-sign-tool")
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        if not signer or not readelf:
            raise ConanInvalidConfiguration("OHOS ELF signer/readelf missing")
        original = Path(path)
        if not original.is_file() or original.is_symlink():
            raise ConanException("missing real ELF for signing: " + str(original))
        signed = original.with_name(original.name + ".signed")
        if signed.exists():
            raise ConanInvalidConfiguration("stale signed ELF sibling")
        try:
            subprocess.run([signer, "sign", "-inFile", str(original),
                            "-outFile", str(signed), "-selfSign", "1"],
                           check=True, capture_output=True, text=True, timeout=40)
            sections = subprocess.run([readelf, "-S", str(signed)], check=True,
                                      capture_output=True, text=True, timeout=20)
            if ".codesign" not in sections.stdout:
                raise ConanException("signed DSSI ELF lacks .codesign section")
            os.chmod(signed, original.stat().st_mode)
            os.replace(signed, original)
        finally:
            if signed.exists():
                signed.unlink()

    def build(self):
        environment = Environment()
        if str(self.settings.os) == "OHOS":
            # mktemp -d fixes mode 0700 independently of the caller's umask.
            # Use exclusive creation in task-private TMPDIR, not chmod on
            # shared filesystem paths, and preserve config.status cleanup.
            configure = os.path.join(self.source_folder, "configure")
            replacements = (
                ('tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
                 'tmp="${TMPDIR:-.}/conf$$-$RANDOM"; (umask 007 && mkdir "$tmp") &&'),
                ('tmp=./conf$$-$RANDOM', 'tmp="${TMPDIR:-.}/conf$$-$RANDOM"'),
                ('(umask 077 && mkdir "$tmp")', '(umask 007 && mkdir "$tmp")'),
            )
            for original, replacement in replacements:
                replace_in_file(self, configure, original, replacement, strict=True)
            scratch = Path(self.build_folder, ".autoconf-tmp")
            previous_umask = os.umask(0o007)
            try:
                scratch.mkdir(mode=0o770, exist_ok=False)
            finally:
                os.umask(previous_umask)
            environment.define("TMPDIR", str(scratch))
        with environment.vars(self).apply():
            self._build_with_autoconf_tmpdir()

    def _build_with_autoconf_tmpdir(self):
        if str(self.settings.os) == "OHOS":
            self._native_config_helpers()
        autotools = Autotools(self)
        libdirs = []
        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                path = Path(libdir)
                if not path.is_absolute():
                    path = Path(dependency.package_folder, libdir)
                if path.is_dir() and str(path) not in libdirs:
                    libdirs.append(str(path))
        if not libdirs:
            raise ConanException("missing Conan dependency runtime library directories")
        loader = ("LD_LIBRARY_PATH=" + shlex.quote(":".join(libdirs)) +
                  "${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}")
        configure = shlex.quote(str(Path(self.source_folder, "configure")))
        shell = Path(self.dependencies.build["bash"].package_folder, "bin", "bash")
        if not shell.is_file():
            raise ConanException("declared Bash configure interpreter is missing")
        quoted_shell = shlex.quote(str(shell))
        # Detect AS_ECHO with the same interpreter that later executes
        # config.status/Libtool. mksh's print builtin is unavailable in Bash.
        self.run(f"{loader} CONFIG_SHELL={quoted_shell} SHELL={quoted_shell} "
                 f"{quoted_shell} {configure} {autotools._configure_args} "
                 "--disable-static --enable-shared",
                 cwd=self.build_folder, env=["conanbuild", "conanrun"])
        autotools.make(args=["-j1", "SHELL=" + quoted_shell])
        # The target clang injects linker-only --code-sign into compile probes;
        # keep upstream -Werror for source warnings, but demote that one flag warning.
        self.run('make -C tests -j1 CFLAGS="$CFLAGS -Wno-error=unused-command-line-argument" controller',
                 cwd=self.build_folder, env="conanbuild")
        if str(self.settings.os) == "OHOS":
            self._sign_elf(Path(self.build_folder, "tests", "controller"))
        self.run(f"{loader} make -j1 check", cwd=self.build_folder,
                 env=["conanbuild", "conanrun"])
        self.output.info("DSSI_UPSTREAM_1_OF_1_PASS")

    def _native_config_helpers(self):
        # Preserve the release's generated build files; extend only its old
        # canonicalizer instead of requiring a developer-machine Automake.
        auxdir = Path(self.source_folder)
        expected_aux = {
            "config.guess": "8486189f55971e6bde5ace26d97a2a51470fe49222160647d258be15d1e693b2",
            "config.sub": "4b046cb76957a1a683f30014263c0672b02d8425086a721e6ef25aede80ff861",
        }
        backup = Path(self.build_folder, ".autoconf-aux-backup")
        backup.mkdir(mode=0o770, exist_ok=False)
        for name, expected in expected_aux.items():
            source = auxdir / name
            if not source.is_file() or source.is_symlink():
                raise ConanInvalidConfiguration("invalid bundled config helper: " + name)
            if hashlib.sha256(source.read_bytes()).hexdigest() != expected:
                raise ConanInvalidConfiguration("unverified bundled config helper: " + name)
            shutil.copy2(source, backup / name)
            if hashlib.sha256((backup / name).read_bytes()).hexdigest() != expected:
                raise ConanException("config helper backup mismatch: " + name)
        sub = auxdir / "config.sub"
        contents = sub.read_text(encoding="utf-8")
        replacements = (
            ("nto-qnx* | linux-gnu*", "nto-qnx* | linux-ohos* | linux-gnu*"),
            ("| a29k \\", "| aarch64 | a29k \\"),
            ("| a29k-* \\", "| aarch64-* | a29k-* \\"),
            ("| -mingw32* | -linux-gnu*", "| -mingw32* | -linux-ohos* | -linux-gnu*"),
        )
        for old, new in replacements:
            if contents.count(old) != 1:
                raise ConanInvalidConfiguration("bundled config.sub anchor drift: " + old)
            contents = contents.replace(old, new, 1)
        sub.write_text(contents, encoding="utf-8")
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        compiler = compilers.get("c") or "clang"
        target = subprocess.run(shlex.split(compiler) + ["-dumpmachine"], check=True,
                                capture_output=True, text=True, timeout=20).stdout.strip()
        if not re.fullmatch(r"aarch64(?:-[A-Za-z0-9_.]+)?-linux-ohos", target):
            raise ConanInvalidConfiguration("unexpected native OHOS compiler tuple: " + target)
        canonical = subprocess.run(["/bin/sh", str(sub), target], check=True,
                                   capture_output=True, text=True, timeout=20).stdout.strip()
        if not re.fullmatch(r"aarch64-[A-Za-z0-9_.]+-linux-ohos", canonical):
            raise ConanInvalidConfiguration("invalid canonical OHOS tuple: " + canonical)
        guess = auxdir / "config.guess"
        guess.write_text("#!/bin/sh\nprintf '%s\\n' " + shlex.quote(canonical) + "\n", encoding="utf-8")
        proved = subprocess.run(["/bin/sh", str(guess)], check=True,
                                capture_output=True, text=True, timeout=20).stdout.strip()
        if proved != canonical:
            raise ConanException("task-local config.guess did not reproduce compiler tuple")
        self.output.info("DSSI_NATIVE_CONFIG_TUPLE=" + proved)

    def package(self):
        Autotools(self).install()
        if str(self.settings.os) == "OHOS":
            for name in ("dssi_analyse_plugin", "dssi_list_plugins"):
                self._sign_elf(Path(self.package_folder, "bin", name))
            plugins = sorted(Path(self.package_folder, "lib", "dssi").glob("*.so"))
            if len(plugins) != 3:
                raise ConanException("expected 3 installed DSSI sample plugins")
            for plugin in plugins:
                self._sign_elf(plugin)
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.requires = ["alsa-lib::asound", "ladspa-sdk::ladspa-sdk"]
        self.cpp_info.set_property("cmake_file_name", "dssi")
        self.cpp_info.set_property("cmake_target_name", "dssi::dssi")
        self.cpp_info.set_property("pkg_config_name", "dssi")
        self.cpp_info.libdirs = []
        self.runenv_info.prepend_path("DSSI_PATH", os.path.join(self.package_folder, "lib", "dssi"))
