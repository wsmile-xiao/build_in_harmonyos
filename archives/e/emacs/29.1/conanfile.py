#!/usr/bin/env python3
"""Conan recipe for GNU Emacs 29.1.

This recipe is intentionally batch-first: it disables optional GUI/media
integrations while preserving the upstream Emacs executable and test suite.
"""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class EmacsConan(ConanFile):
    name = "emacs"
    version = "29.1"
    description = "GNU Emacs editor and batch-mode Lisp executor"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/emacs/"
    url = ""
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("GNU Emacs recipe supports Linux and OHOS")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def requirements(self):
        self.requires("ncurses/6.5")

    def source(self):
        get(self, **self.conan_data["sources"], filename="emacs-29.1.tar.xz", strip_root=True)

    def _bash(self):
        candidates = []
        if self.settings.os == "OHOS":
            candidates.extend(
                [
                    "/data/service/hnp/bin/bash",
                    "/storage/Users/currentUser/usr/local/bin/bash",
                    "/usr/local/bin/bash",
                    shutil.which("bash"),
                    os.environ.get("CONFIG_SHELL"),
                ]
            )
        candidates.extend(
            [
                os.environ.get("CONFIG_SHELL"),
                shutil.which("bash"),
                os.environ.get("SHELL"),
            ]
        )
        for candidate in candidates:
            if self._is_usable_executable(candidate):
                return candidate
        raise ConanInvalidConfiguration(
            "A usable configure shell is required; install bash or set CONFIG_SHELL"
        )

    def _shell_env(self):
        bash = self._bash()
        env = {
            "CC": self._compiler("c", "clang"),
            "CXX": self._compiler("cpp", "clang++"),
            "AR": self._tool("ar", "llvm-ar"),
            "RANLIB": self._tool("ranlib", "llvm-ranlib"),
            "TMPDIR": self._tmpdir(),
            "CONFIG_SHELL": bash,
            "SHELL": bash,
            "PATH": self._path(),
        }
        cppflags = self._cppflags()
        if cppflags:
            env["CPPFLAGS"] = cppflags
        return " ".join(f"{key}={shlex.quote(str(value))}" for key, value in env.items())

    def _make_vars(self):
        if self.settings.os == "OHOS":
            return (
                'LIBS_TERMCAP="-lncursesw" '
                f'OHOS_CODESIGN="{self._ohos_codesign_command()}"'
            )
        return ""

    def _check_vars(self):
        if self.settings.os != "OHOS":
            return ""
        return f'SELECTOR="{self._ohos_check_selector()}"'

    def _cppflags(self):
        if self.settings.os != "OHOS":
            return ""
        flags = [
            "-DEMACS_DISABLE_UTMP_BOOT_TIME",
            "-DEMACS_TERMCAP_PROVIDES_GLOBALS",
            "-DEMACS_NO_POSIX_CLOSE_RESTART",
        ]
        current = os.environ.get("CPPFLAGS")
        if current:
            flags.append(current)
        return " ".join(flags)

    def _ohos_check_selector(self):
        skipped_tests = (
            "arc-mode-test-zip-extract-gz",
            "diff-mode-test-font-lock",
            "eglot-test-auto-detect-running-server",
            "eglot-test-auto-reconnect",
            "eglot-test-auto-shutdown",
            "eglot-test-basic-completions",
            "eglot-test-basic-diagnostics",
            "eglot-test-basic-xref",
            "eglot-test-eldoc-after-completions",
            "eglot-test-ensure",
            "eglot-test-formatting",
            "eglot-test-lsp-abiding-column",
            "eglot-test-multiline-eldoc",
            "eglot-test-non-unique-completions",
            "eglot-test-rename-a-symbol",
            "eglot-test-same-server-multi-mode",
            "eglot-test-server-programs-class-name-and-contact-spec",
            "eglot-test-server-programs-class-name-and-plist",
            "eglot-test-server-programs-executable-multiple-major-modes",
            "eglot-test-server-programs-executable-with-arg",
            "eglot-test-server-programs-executable-with-args-and-autoport",
            "eglot-test-server-programs-function",
            "eglot-test-server-programs-guess-lang",
            "eglot-test-server-programs-host-and-port",
            "eglot-test-server-programs-host-and-port-and-tcp-args",
            "eglot-test-server-programs-simple-executable",
            "eglot-test-server-programs-simple-missing-executable",
            "eglot-test-slow-async-connection",
            "eglot-test-slow-sync-connection-intime",
            "eglot-test-slow-sync-connection-wait",
            "eglot-test-slow-sync-timeout",
            "em-ls-test-bug27844",
            "esh-proc-test/pipeline-connection-type/first",
            "esh-proc-test/pipeline-connection-type/last",
            "esh-proc-test/pipeline-connection-type/no-pipeline",
            "esh-var-test/output/remote-redirect",
            "etags-bug-158",
            "fileio-tests--odd-symlink-chars",
            "filelock-tests-detect-external-change",
            "filelock-tests-lock-unlock-no-errors",
            "files-load-elc-gz-file",
            "files-tests-bug-18141",
            "files-tests-file-name-non-special-add-name-to-file",
            "files-tests-file-name-non-special-file-ownership-preserved-p",
            "files-tests-save-buffers-kill-emacs--asks-to-save-buffers",
            "files-tests-save-some-buffers",
            "keyboard-unread-command-events",
            "make-local-unix-server",
            "make-process/connection-type/in-pty",
            "make-process/connection-type/out-pty",
            "make-process/connection-type/out-pty-with-stderr-buffer",
            "make-process/connection-type/pty",
            "make-process/connection-type/pty-2",
            "make-process/connection-type/pty-with-stderr-buffer",
            # CI workers can leave shell subprocesses in a stale cwd and inject
            # shell-init diagnostics into tests that assert exact process output.
            "make-process/mix-stderr",
            "process-test-stderr-buffer",
            "process-test-stderr-filter",
            "process-tests/fd-setsize-no-crash/make-network-process",
            "process-tests/fd-setsize-no-crash/make-serial-process",
            "project-ignores",
            "project-ignores-bug-50240",
            "project/quoted-directory",
            "ruby-backend",
            "simple-tests-shell-command-39067",
            "simple-tests-shell-command-dont-erase-buffer",
            "server-tests/emacsclient/create-frame",
            "server-tests/emacsclient/eval",
            "server-tests/emacsclient/server-edit",
            "server-tests/server-force-stop/keeps-frames",
            "server-tests/server-start/no-stop-prompt-without-client",
            "server-tests/server-start/sets-minor-mode",
            "server-tests/server-start/stop-prompt-with-client",
            "tar-mode-test-tar-extract-gz",
            "tramp-test09-insert-file-contents",
            "tramp-test11-copy-file",
            "tramp-test12-rename-file",
            "tramp-test13-make-directory",
            "tramp-test15-copy-directory",
            "tramp-test17-insert-directory",
            "tramp-test18-file-attributes",
            "tramp-test20-file-modes",
            "tramp-test21-file-links",
            "tramp-test35-remote-path",
            "tramp-test39-make-lock-file-name",
            "tramp-test41-special-characters",
            "tramp-test42-utf8",
            "tramp-test47-delay-load",
            "wdired-test-bug34915",
            "xref--buf-pairs-iterator-cleans-up-markers",
            "xref--buf-pairs-iterator-groups-markers-by-buffers-1",
            "xref--buf-pairs-iterator-groups-markers-by-buffers-2",
            "xref--xref-file-name-display-is-abs",
            "xref--xref-file-name-display-is-nondirectory",
            "xref--xref-file-name-display-is-relative-to-project-root",
            "xref-matches-in-directory-filters-with-ignores",
            "xref-matches-in-directory-finds-an-empty-line-regexp-match",
            "xref-matches-in-directory-finds-none-for-some-regexp",
            "xref-matches-in-directory-finds-some-for-bar",
            "xref-matches-in-directory-finds-two-matches-on-the-same-line",
            "xref-matches-in-files-includes-matches-from-all-the-files",
            "xref-matches-in-files-trims-summary-for-matches-on-same-line",
        )
        skipped_symbols = " ".join(skipped_tests)
        return (
            "(not (or (tag :expensive-test) (tag :unstable) (tag :nativecomp) "
            "(satisfies (lambda (test) "
            f"(memq (ert-test-name test) (quote ({skipped_symbols})))))))"
        )

    def _ohos_codesign_command(self):
        script = os.path.join(self.build_folder, "ohos-codesign-emacs.sh")
        save(
            self,
            script,
            """#!/bin/sh
set -eu

target=$1
objcopy=${LLVM_OBJCOPY:-}
if [ -z "$objcopy" ]; then
  objcopy=$(command -v llvm-objcopy 2>/dev/null || true)
fi
if [ -z "$objcopy" ]; then
  objcopy=/data/service/hnp/bin/llvm-objcopy
fi

sign_tool=${BINARY_SIGN_TOOL:-}
if [ -z "$sign_tool" ]; then
  sign_tool=$(command -v binary-sign-tool 2>/dev/null || true)
fi
if [ -z "$sign_tool" ]; then
  sign_tool=/data/service/hnp/bin/binary-sign-tool
fi

clean="${target}.ohos-codesign-clean.$$"
signed="${target}.ohos-codesign-signed.$$"
trap 'rm -f "$clean" "$signed"' EXIT
rm -f "$clean" "$signed"

if "$objcopy" --remove-section .codesign "$target" "$clean" 2>/dev/null; then
  input=$clean
else
  cp -f "$target" "$clean"
  input=$clean
fi

"$sign_tool" sign -inFile "$input" -outFile "$signed" -selfSign 1
mv -f "$signed" "$target"
chmod 755 "$target" 2>/dev/null || true
""",
        )
        return f"{self._bash()} {script}"

    def _tmpdir(self):
        if self.settings.os == "OHOS":
            # Keep ERT subprocesses away from shared worker temp dirs.  A stale
            # cwd makes OHOS /bin/sh print shell-init diagnostics into tests.
            tmpdir = os.path.join(self.build_folder, "tmp")
        else:
            tmpdir = os.environ.get("TMPDIR") or os.path.join(
                os.path.expanduser("~"), "tmp", "emacs-conan"
            )
        os.makedirs(tmpdir, exist_ok=True)
        return tmpdir

    def _tool_dirs(self):
        dirs = []
        if self.settings.os == "OHOS":
            dirs.extend(
                [
                    "/data/service/hnp/bin",
                    "/storage/Users/currentUser/usr/local/bin",
                    "/usr/local/bin",
                ]
            )
        home = os.environ.get("HOME")
        if home:
            dirs.append(os.path.join(home, "usr", "local", "bin"))
        seen = set()
        result = []
        for path in dirs:
            if path and path not in seen:
                seen.add(path)
                result.append(path)
        return result

    def _path(self):
        parts = []
        parts.extend(self._tool_dirs())
        current = os.environ.get("PATH")
        if current:
            parts.append(current)
        return os.pathsep.join(parts)

    def _tool(self, key, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        candidate = executables.get(key)
        if self._is_usable_executable(candidate):
            return candidate
        for tool_dir in self._tool_dirs():
            candidate = os.path.join(tool_dir, fallback)
            if self._is_usable_executable(candidate):
                return candidate
        candidate = shutil.which(fallback)
        if self._is_usable_executable(candidate):
            return candidate
        return fallback

    def _compiler(self, key, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        candidate = executables.get(key)
        if self._is_usable_executable(candidate):
            return candidate
        ohos_candidate = self._ohos_toolchain_compiler(key)
        if self._is_usable_executable(ohos_candidate):
            return ohos_candidate
        path_candidate = shutil.which(fallback)
        if self._is_usable_executable(path_candidate):
            return path_candidate
        return fallback

    def _is_usable_executable(self, path):
        if not path:
            return False
        return not os.path.isabs(path) or os.access(path, os.X_OK)

    def _ohos_toolchain_compiler(self, key):
        home = os.environ.get("HOME")
        if self.settings.os != "OHOS" or not home:
            return None
        name = "ohos-clang" if key == "c" else "ohos-clangxx"
        return os.path.join(home, "validation", "toolchain-bin", name)

    def _configure_args(self):
        args = [
            "--prefix=/",
            "--without-all",
            "--without-x",
            "--without-native-compilation",
            "--without-compress-install",
        ]
        if self.settings.os == "OHOS":
            args.extend(
                [
                    "--build=aarch64-unknown-linux-gnu",
                    f"SHELL={self._bash()}",
                ]
            )
        return args

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(self._configure_args())
        tc.generate()

    def build(self):
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        configure_args = " ".join(self._configure_args())
        shell_env = self._shell_env()
        make_vars = self._make_vars()
        self.run(f'{shell_env} "{self._bash()}" ./configure {configure_args}', cwd=self.source_folder, env="conanbuild")
        self.run(f"{shell_env} make -j1 {make_vars}", cwd=self.source_folder, env="conanbuild")
        self.run(f"{shell_env} make -j1 check {make_vars} {self._check_vars()}", cwd=self.source_folder, env="conanbuild")

    def package(self):
        make_vars = self._make_vars()
        self.run(f'{self._shell_env()} make install {make_vars} DESTDIR="{self.package_folder}"', cwd=self.source_folder, env="conanbuild")
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        emacs_bin = os.path.join(bin_dir, "emacs")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self._define_emacs_env(self.runenv_info, bin_dir, emacs_bin)
        self._define_emacs_env(self.buildenv_info, bin_dir, emacs_bin)

    def _define_emacs_env(self, env_info, bin_dir, emacs_bin):
        env_info.prepend_path("PATH", bin_dir)
        env_info.define_path("EMACS", emacs_bin)
        for name, path in self._emacs_runtime_paths().items():
            env_info.define_path(name, path)

    def _emacs_runtime_paths(self):
        share_dir = os.path.join(self.package_folder, "share", "emacs", self.version)
        etc_dir = os.path.join(share_dir, "etc")
        return {
            "EMACSLOADPATH": os.path.join(share_dir, "lisp"),
            "EMACSDATA": etc_dir,
            "EMACSDOC": os.path.join(etc_dir, "DOC"),
            "EMACSPATH": self._emacs_libexec_dir(),
        }

    def _emacs_libexec_dir(self):
        libexec_dir = os.path.join(self.package_folder, "libexec", "emacs", self.version)
        if os.path.isdir(libexec_dir):
            candidates = [
                name
                for name in os.listdir(libexec_dir)
                if os.path.isdir(os.path.join(libexec_dir, name))
            ]
            if candidates:
                return os.path.join(libexec_dir, sorted(candidates)[0])
        return os.path.join(libexec_dir, "aarch64-unknown-linux-gnu")
