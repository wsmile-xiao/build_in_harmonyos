#!/usr/bin/env python3
"""Conan recipe for GNU make 4.4.1.

Notes:
- Source URL and SHA256 are kept inline in this recipe (no conandata.yml) so
  the package does not enter the CI pre-download branch that references an
  uninitialized BUILD_DIR.
- The two patches under patches/ are whole-file replacements of
  build-aux/config.guess and build-aux/config.sub (HarmonyOS triplet support),
  copied over the upstream files during build(). They are not unified diffs,
  so apply_conandata_patches() is not used.
- OHOS build mirrors the r9 device findings recorded in notes.md:
  ld.bfd instead of lld (missing libxml2 dependency) and a fixed TMPDIR
  (HMDFS mktemp permission issue).
"""

import os
import shlex
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

_source_url = "https://ftp.gnu.org/gnu/make/make-4.4.1.tar.gz"
_source_sha256 = "dd16fb1d67bfab79a72f5e8390735c49e3e8e70b4945a15ab1f81ddb78658fb3"

# patch file name -> file replaced in the source tree
_config_patch_files = {
    "0001-config.guess-harmonyos.patch": "build-aux/config.guess",
    "0002-config.sub-harmonyos.patch": "build-aux/config.sub",
}


class MakeConan(ConanFile):
    name = "make"
    version = "4.4.1"
    description = "GNU Make - a tool for building programs"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/make/"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports = "patches/*"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("make is adapted for Linux and OHOS only")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, url=_source_url, sha256=_source_sha256, strip_root=True)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(self._recipe_configure_args())
        if self._is_ohos():
            toolchain.configure_args.extend(self._triplet_configure_args())
            env = toolchain.environment()
            shell = self._select_shell()
            env.define("CONFIG_SHELL", shell)
            env.define("SHELL", shell)
            # HarmonyOS refuses execve on newly created files; route CC
            # through a wrapper that signs every produced ELF so configure
            # conftest probes and the final binary can actually run (r9).
            env.define("CC", self._write_compiler_wrapper())
            for variable, candidates in {
                "AR": ["llvm-ar", "ar"],
                "RANLIB": ["llvm-ranlib", "ranlib"],
                "NM": ["llvm-nm", "nm"],
            }.items():
                command = self._select_tool_command(candidates)
                if command:
                    env.define(variable, command)
            toolchain.generate(env=env)
        else:
            toolchain.generate()

    def build(self):
        self._apply_config_patches()
        self._prepare_build_environment()
        if self._is_ohos():
            self._relax_configure_tempdirs()
            self._run_configure()
            self._run_make(args=["-j1"])
        else:
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])
        self._run_smoke_test()

    def package(self):
        self._prepare_build_environment()
        if self._is_ohos():
            self._run_make(
                target="install",
                args=[f"DESTDIR={self.package_folder}", "MAKEINFO=true"],
            )
        else:
            autotools = Autotools(self)
            autotools.install()
        # The upstream install ships only the binary plus docs/info pages that
        # live under the redirected datarootdir; nothing else needs pruning.

    def package_info(self):
        bindir = os.path.join(self.package_folder, "bin")
        make = os.path.join(bindir, "make")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.buildenv_info.append_path("PATH", bindir)
        self.runenv_info.append_path("PATH", bindir)
        self.buildenv_info.define_path("MAKE", make)
        self.runenv_info.define_path("MAKE", make)

    # ------------------------------------------------------------------
    # helpers

    def _is_ohos(self):
        return str(self.settings.os) == "OHOS"

    def _apply_config_patches(self):
        patches = os.path.join(self.recipe_folder, "patches")
        for patch_name, target in _config_patch_files.items():
            src = os.path.join(patches, patch_name)
            dst = os.path.join(self.source_folder, target)
            copy(self, pattern=patch_name, src=patches, dst=os.path.dirname(dst))
            os.replace(os.path.join(os.path.dirname(dst), patch_name), dst)
            os.chmod(dst, os.stat(dst).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def _write_compiler_wrapper(self):
        """Return a 'sh <wrapper>' CC value that compiles then signs ELFs.

        The device denies execve on every file created at runtime, so:
        - the wrapper itself is invoked as `sh <script>` (no execve on it);
        - after clang runs, every `-o` output is signed with
          binary-sign-tool and made executable, allowing configure's
          conftest probes and the final make binary to run (r9 finding).
        """
        clang = shutil.which("aarch64-unknown-linux-ohos-clang") or (
            "/data/service/hnp/bin/aarch64-unknown-linux-ohos-clang"
        )
        sign_tool = shutil.which("binary-sign-tool") or (
            "/data/service/hnp/bin/binary-sign-tool"
        )
        objcopy = shutil.which("llvm-objcopy") or (
            "/data/service/hnp/bin/llvm-objcopy"
        )
        wrapper = os.path.join(self.build_folder, "clang-sign-wrapper.sh")
        save(
            self,
            wrapper,
            "#!/bin/sh\n"
            "# HarmonyOS: sign every compiler output; ELFs need a signature\n"
            "# before the system allows execve (generated by conan recipe).\n"
            f'CC_REAL="{clang}"\n'
            f'SIGN_TOOL="{sign_tool}"\n'
            f'OBJCOPY="{objcopy}"\n'
            '"$CC_REAL" "$@"\n'
            "rc=$?\n"
            "prev=\"\"\n"
            'for a in "$@"; do\n'
            '  if [ "$prev" = "-o" ] && [ -f "$a" ]; then\n'
            "    # ld.bfd embeds an invalid placeholder .codesign section on\n"
            "    # ohos targets; the signer refuses files that already carry\n"
            "    # one, so strip it before signing.\n"
            '    "$OBJCOPY" --remove-section .codesign "$a" >/dev/null 2>&1\n'
            '    "$SIGN_TOOL" sign -selfSign 1 -inFile "$a" -outFile "$a.sig" \\\n'
            "      -signAlg SHA256withECDSA >/dev/null 2>&1 && {\n"
            '      chmod 755 "$a"\n'
            '      cat "$a.sig" > "$a"\n'
            '      rm -f "$a.sig"\n'
            "    }\n"
            "  fi\n"
            '  prev="$a"\n'
            "done\n"
            "exit $rc\n",
        )
        return f"sh {wrapper}"

    def _prepare_build_environment(self):
        if not self._is_ohos():
            return
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        shell = self._select_shell()
        os.environ["CONFIG_SHELL"] = shell
        os.environ["SHELL"] = shell

    def _select_shell(self):
        for shell in (
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            "/data/service/hnp/bin/bash",
            "/bin/sh",
            "/system/bin/sh",
        ):
            if not shell:
                continue
            if os.path.isabs(shell):
                if os.path.isfile(shell) and os.access(shell, os.X_OK):
                    return shell
            elif shutil.which(shell):
                return shell
        return "sh"

    def _select_compiler_command(self, compiler):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        command = compilers.get(compiler)
        if not command:
            return None
        try:
            parts = shlex.split(command)
        except ValueError:
            return command
        if not parts:
            return None
        if self._is_executable(parts[0]):
            return command
        for index, part in enumerate(parts[1:], start=1):
            if self._is_executable(part):
                return shlex.join(parts[index:])
        return command

    def _select_tool_command(self, candidates):
        for candidate in candidates:
            command = shutil.which(candidate)
            if command:
                return command
        return candidates[0] if candidates else None

    def _is_executable(self, command):
        if os.path.isabs(command):
            return os.path.isfile(command) and os.access(command, os.X_OK)
        return shutil.which(command) is not None

    def _relax_configure_tempdirs(self):
        """r9 finding 5: on HMDFS, `mktemp -d` yields a mode-2700+SUID dir
        whose children cannot write (umask cannot widen it back), while
        plain `mkdir` works. Force the mktemp branch of configure to fail
        so it falls through to the `mkdir ./conf$$-$RANDOM` branch, and
        relax that branch's umask (same approach as m4's 0003 patch)."""
        configure = os.path.join(self.source_folder, "configure")
        with open(configure, encoding="utf-8", errors="surrogateescape") as f:
            text = f.read()
        replaced = text.replace(
            '(umask 077 && mktemp -d "./confXXXXXX")',
            "(umask 077 && false)",
        ).replace(
            '(umask 077 && mkdir "$tmp")',
            '(umask 022 && mkdir "$tmp")',
        )
        if replaced != text:
            with open(configure, "w", encoding="utf-8", errors="surrogateescape") as f:
                f.write(replaced)

    def _run_configure(self):
        configure = os.path.join(self.source_folder, "configure")
        # "sh configure" instead of direct execve: the device denies the
        # execute bit on files created at runtime (exit 126).
        command = ["sh", configure] + self._ohos_configure_args()
        self._run_command(shlex.join(command), "OHOS configure")

    def _run_make(self, target=None, args=None):
        command = ["make"]
        if target:
            command.append(target)
        command.extend(args or [])
        self._run_command(shlex.join(command), f"OHOS make {target or 'all'}")

    def _run_smoke_test(self):
        smoke_mk = os.path.join(self.build_folder, "conan-smoke.mk")
        save(
            self,
            smoke_mk,
            "all: out.txt\n\t@cat out.txt\n"
            "out.txt:\n\t@echo hello-from-gnu-make > $@\n"
            "clean:\n\t@rm -f out.txt\n",
        )
        make = shlex.quote(os.path.join(self.build_folder, "make"))
        self._run_command(f"{make} --version", "make --version")
        self._run_command(
            f"{make} -f {shlex.quote(smoke_mk)} clean all",
            "make smoke build",
        )

    def _run_command(self, command, description):
        ret = self.run(command, env="conanbuild", ignore_errors=True)
        if ret != 0:
            raise ConanException(f"{description} failed with exit code {ret}")

    def _ohos_configure_args(self):
        return (
            self._autotools_install_configure_args()
            + self._recipe_configure_args()
            + self._triplet_configure_args()
            + [
                # r9 device finding: lld fails with a missing libxml2
                # dependency; link with GNU ld.bfd instead.
                "LDFLAGS=-fuse-ld=bfd",
            ]
        )

    @staticmethod
    def _recipe_configure_args():
        return [
            "--disable-dependency-tracking",
            "--disable-silent-rules",
            "--disable-nls",
        ]

    @staticmethod
    def _autotools_install_configure_args():
        return [
            "--prefix=/",
            "--bindir=${prefix}/bin",
            "--sbindir=${prefix}/bin",
            "--libdir=${prefix}/lib",
            "--includedir=${prefix}/include",
            "--oldincludedir=${prefix}/include",
            "--datarootdir=${prefix}/res",
        ]

    def _triplet_configure_args(self):
        arch = str(self.settings.arch)
        cpu = {
            "armv8": "aarch64",
            "armv8.3": "aarch64",
            "armv8_32": "arm",
            "armv7": "arm",
            "x86_64": "x86_64",
        }.get(arch, arch)
        triplet = f"{cpu}-unknown-linux-ohos"
        return [
            f"--build={triplet}",
            f"--host={triplet}",
        ]
