#!/usr/bin/env python3
"""Conan recipe - merecat 2.31-git20260330

merecat is the thttpd-derived HTTP/HTTPS server maintained by troglobit.
The pinned source is the official upstream git snapshot that Debian packaged as
2.31+git20260330+ds-1 (commit 57a2ce7c0cca, 2026-03-15); the GitHub archive used
here was verified file-by-file (130 files, SHA256) against that Debian orig
tarball.

HarmonyOS PC (os=OHOS, aarch64) adaptation - path A:

* The git snapshot ships no generated `configure`/`Makefile.in`, so build()
  bootstraps them from `autogen.sh` with the `automake` tool chain published in
  the OHOS registry (the worker has autoconf/make but no system automake, so
  automake is a tool_requires instead of a PATH assumption).
* Upstream `config.guess`/`config.sub` do not know HarmonyOS, so the generated
  pair is extended in place (knowledge E007).  This is a POSIX-compatible
  change and keeps configure on its native, non-cross-compiling path - passing
  --build/--host would make autoconf skip every run-time probe.
* HMDFS creates mktemp(1) directories as 2700+setgid and masks file permission
  bits, therefore:
    - configure's AS_TMPDIR is pinned to a pre-created writable directory
      (E114) and the generated helper scripts get their execute bit restored
      (E490);
    - files never carry the POSIX "other" permission bits that upstream uses to
      decide whether a file may be served, so those checks learn to fall back to
      access(2) (patches/0002, POSIX-compatible per iron rule R8);
* `/tmp` is read-only on HarmonyOS PC, so the bundled tmpfile() replacement
  honours `$TMPDIR` (patches/0001).
* an in-tree build with an explicit working directory is used because HMDFS
  rejects the ephemeral Conan build folder as a process working directory.

With these patches the complete upstream test suite passes inside build():
`make check` reports 13 PASS / 0 FAIL / 1 SKIP (php-cgi is not installed, the
test itself exits 77).
"""
import os
import re
import shlex
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cmd_args_to_string, load_toolchain_args
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class MerecatConan(ConanFile):
    name = "merecat"
    version = "2.31-git20260330"
    description = "merecat - small and made-easy HTTP/HTTPS server based on thttpd"
    license = "BSD-2-Clause"
    homepage = "https://github.com/troglobit/merecat"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    # HarmonyOS config.guess case block; same intent as the shared
    # patch-autotools-ohos helper but expressed without platform macros (R8).
    _HARMONYOS_CASE = (
        "\t*:HarmonyOS:*:*)\n"
        "\tcase \"$UNAME_MACHINE\" in\n"
        "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
        "\t    armv7*|armv8*) MACHINE=arm ;;\n"
        "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
        "\t    i?86)         MACHINE=i686 ;;\n"
        "\t    *)            MACHINE=\"$UNAME_MACHINE\" ;;\n"
        "\tesac\n"
        "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
        "\t;;\n\n"
    )

    _CONFIGURE_EXTRA = (
        "--enable-builtin-icons",
        "--enable-htaccess",
        "--enable-htpasswd",
        # Do not install the generic httpd/in.httpd symlinks.
        "--without-symlinks",
    )

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} is not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libconfuse/3.3")     # /etc/merecat.conf parser
        self.requires("openssl/3.5.6.1")    # HTTPS support
        self.requires("zlib/1.3.1")         # mod_deflate (gzip)

    def build_requirements(self):
        # The git snapshot has no generated configure; the worker provides
        # autoconf, make and clang but no automake, so take it from the registry.
        self.tool_requires("automake/1.18")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # HMDFS cannot write to the read-only /tmp, so configure and the test
        # suite share a private, pre-created temporary directory (E114).
        tmpdir = os.path.join(self._writable_tmp_root(), "merecat-ac-tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        self.buildenv_info.define_path("TMPDIR", tmpdir)

        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()
        # The project specific flags are appended in _configure_args(); keeping
        # them out of the tool chain file avoids passing every option twice.
        AutotoolsToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        self._bootstrap()
        self._patch_config_guess()
        self._patch_config_sub()
        self._fix_helper_modes()
        self._pin_configure_tmpdir()
        # Build in-tree with an explicit working directory: the ephemeral Conan
        # build folder is not usable as a process cwd on HMDFS ("getcwd: cannot
        # access parent directories"), while the source folder is.
        src = self.source_folder
        # E386: the tool chain bash cannot always getcwd() inside the Conan
        # cache on HMDFS, which makes Autoconf's CONFIG_SHELL re-exec fail.
        # Probe the candidates in the real build directory and pin the one that
        # demonstrably keeps the working directory.
        shell = self._working_shell()
        self.output.info(f"configure shell: {shell}")
        self.run(f'CONFIG_SHELL="{shell}" SHELL="{shell}" '
                 f'"{os.path.join(src, "configure")}" {self._configure_args()}',
                 cwd=src, env="conanbuild")
        self.run("make -j1", cwd=src, env="conanbuild")
        # Upstream test suite is part of the build gate (R51).
        self.run("make check", cwd=src, env="conanbuild")

    def package(self):
        self.run(f'make install DESTDIR="{self.package_folder}"',
                 cwd=self.source_folder, env="conanbuild")
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["sbin", "bin"]

    # ----------------------------------------------------------------- helpers
    _SHELL_CANDIDATES = ("/bin/sh", "/usr/bin/sh", "/data/service/hnp/bin/bash")

    def _working_shell(self):
        """Return the first shell that keeps the working directory (E386).

        A shell that cannot resolve the current directory still exits zero for
        some commands while printing a getcwd diagnostic, so require a clean
        `pwd` in the real build tree instead of trusting the exit status alone.
        """
        for candidate in self._SHELL_CANDIDATES:
            if not os.path.exists(candidate):
                continue
            try:
                probe = subprocess.run([candidate, "-c", "pwd"], cwd=self.source_folder,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       universal_newlines=True, timeout=60)
            except (OSError, subprocess.SubprocessError):
                continue
            if probe.returncode == 0 and not probe.stderr.strip() \
                    and probe.stdout.strip():
                return candidate
        raise ConanException("no shell can resolve the working directory")

    def _configure_args(self):
        """Conan's configure_args are an already quoted string (conanbuild.conf)."""
        base = load_toolchain_args(self.generators_folder).get("configure_args") or ""
        if not isinstance(base, str):
            base = cmd_args_to_string(list(base))
        # PkgConfigDeps writes the .pc files into the generators folder; make
        # the generated configure see them (same pattern as the abiword recipes).
        extra = cmd_args_to_string(list(self._CONFIGURE_EXTRA) +
                                   [f"PKG_CONFIG_PATH={self.generators_folder}"])
        return f"{base} {extra}".strip()

    def _writable_tmp_root(self):
        candidates = [
            os.environ.get("TMPDIR"),
            os.path.join(os.path.expanduser("~"), "tmp"),
            tempfile.gettempdir(),
        ]
        for cand in candidates:
            if not cand:
                continue
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".merecat-writable-probe")
                with open(probe, "w", encoding="utf-8") as handle:
                    handle.write("ok")
                os.unlink(probe)
                return cand
            except OSError:
                continue
        raise ConanException("no writable temporary directory found")

    def _aux_dir(self):
        aux = os.path.join(self.source_folder, "aux")
        return aux if os.path.isdir(aux) else self.source_folder

    def _materialise(self, path):
        """Replace an automake-installed symlink with a private copy.

        `automake --add-missing` links config.guess/config.sub into the automake
        package; editing the link in place would mutate the shared tool chain
        inside the Conan cache, so take a private copy first.
        """
        if os.path.islink(path):
            with open(os.path.realpath(path), "rb") as handle:
                data = handle.read()
            os.unlink(path)
            with open(path, "wb") as handle:
                handle.write(data)
        return path

    def _read(self, path):
        with open(path, "r", encoding="utf-8", errors="surrogateescape") as handle:
            return handle.read()

    def _write(self, path, text):
        with open(path, "w", encoding="utf-8", errors="surrogateescape") as handle:
            handle.write(text)

    def _bootstrap(self):
        if os.path.exists(os.path.join(self.source_folder, "configure")):
            return
        self.run("sh ./autogen.sh", cwd=self.source_folder, env="conanbuild")
        if not os.path.exists(os.path.join(self.source_folder, "configure")):
            raise ConanException("autogen.sh did not produce configure")

    def _patch_config_guess(self):
        path = os.path.join(self._aux_dir(), "config.guess")
        if not os.path.exists(path):
            return
        text = self._read(path)
        if "HarmonyOS" in text:
            return
        match = re.search(r"^[ \t]+\*:NetBSD:\*:\*\)[ \t]*$", text, re.M)
        if not match:
            raise ConanException("config.guess: NetBSD anchor not found")
        text = text[:match.start()] + self._HARMONYOS_CASE + text[match.start():]
        self._write(self._materialise(path), text)
        self.output.info("config.guess: added HarmonyOS platform detection")

    def _patch_config_sub(self):
        path = os.path.join(self._aux_dir(), "config.sub")
        if not os.path.exists(path):
            return
        text = self._read(path)
        if "ohos-linux" in text:
            return
        lines = text.splitlines(keepends=True)
        for idx, line in enumerate(lines):
            if line.strip() == "android-linux)":
                end = idx
                while end < len(lines) and ";;" not in lines[end]:
                    end += 1
                block = lines[idx:end + 1]
                extra = [item.replace("android-linux", "ohos-linux")
                               .replace("linux-android", "linux-ohos")
                         for item in block]
                lines[idx:end + 1] = block + extra
                break
        text = "".join(lines)
        text = re.sub(r"(gnu\*\s*\|\s*android\*)", r"\1 | ohos*", text, count=1)
        text = re.sub(r"(linux-uclibc\*[/-]?\s*)\)", r"\1| linux-ohos*)", text, count=1)
        self._write(self._materialise(path), text)
        self.output.info("config.sub: added ohos-linux triplet")

    def _fix_helper_modes(self):
        """E490: HMDFS can drop the execute bit of generated helper scripts."""
        aux = self._aux_dir()
        helpers = ["configure", os.path.join(aux, "config.guess"),
                   os.path.join(aux, "config.sub"), os.path.join(aux, "install-sh"),
                   os.path.join(aux, "missing"), os.path.join(aux, "depcomp"),
                   os.path.join(aux, "compile"), os.path.join(aux, "test-driver")]
        for helper in helpers:
            # Never chmod through a symlink into the shared tool chain.
            if os.path.isfile(helper) and not os.path.islink(helper):
                os.chmod(helper, os.stat(helper).st_mode | stat.S_IXUSR)

    def _pin_configure_tmpdir(self):
        """E114: mktemp -d directories on HMDFS are not writable."""
        fixed = os.environ.get("TMPDIR", tempfile.gettempdir())
        os.makedirs(fixed, exist_ok=True)
        path = os.path.join(self.source_folder, "configure")
        if not os.path.exists(path):
            raise ConanException("configure not found")
        text = self._read(path)
        if "ac_tmp=$tmp" in text:
            # E114: $TMPDIR (or the platform default) may contain spaces or
            # shell metacharacters, so quote it before it lands in a script.
            text = text.replace("ac_tmp=$tmp", f"ac_tmp={shlex.quote(fixed)}")
            text = text.replace(
                '{ test ! -d "$ac_tmp" || rm -fr "$ac_tmp"; } && exit $exit_status',
                "exit $exit_status")
            self._write(path, text)
            self.output.info(f"configure: AS_TMPDIR pinned to {fixed}")
