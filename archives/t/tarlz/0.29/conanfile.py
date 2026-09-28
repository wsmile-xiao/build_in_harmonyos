#!/usr/bin/env python3
"""Conan recipe for tarlz 0.29 — parallel tar + lzip archiver.

tarlz (Antonio Diaz) is a massively parallel (multithreaded) combined
implementation of the tar archiver and the lzip compressor.  C++ with a
generated configure script shipped in the upstream tarball — no
autoreconf bootstrap needed.  One external library dependency: lzlib
(hard configure probe), already published in the ohpcd registry
(lzlib/1.15, the in-fleet consensus version) and referenced directly.

Source-packaging quirk: upstream ships only `.tar.lz`.  Conan 2.32's
`unzip_and_get` does not handle `.tar.lz`, so source() only downloads
and verifies the file; the unpack (lzip -d + tar -xf) happens in
_build_ohos via `tool_requires("lzip/1.25")` (published) under the
conanbuild environment.

OHOS machinery (same proven set as this archive's tardy/zvbi ports):

* **Compilers pinned from the profile** (R33: conanautotoolstoolchain.sh is
  sourced only by conan's own Autotools() helper, never by a raw
  subprocess).
* **Shell**: `/data/service/hnp/bin/bash` (generated configure contains
  `exec 7<&0`, rejected by toybox sh).
* **umask 077 -> 022** in the generated configure (hmdfs traversal, same
  device-verified workaround as tardy/ncrack/libcaca/libabw/zvbi).
* **In-tree build**: source unpacked into the build folder before
  configuring.
* **Install only the binary** (`make install-bin`): `install-doc` needs
  GROFF+ps2pdf (PDF manuals), unavailable on the device/CI fleet.
  Documented as降级边界 in notes.md.
"""

import hashlib
import os
import shlex
import ssl
import subprocess
import time
import urllib.request
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

OHOS_SHELL_CANDIDATES = ("/data/service/hnp/bin/bash", "/usr/bin/zsh", "bash")


class TarlzConan(ConanFile):
    name = "tarlz"
    version = "0.29"
    description = "Parallel tar archiver with lzip compression (multithreaded)"
    license = "GPL-2.0-or-later"
    homepage = "https://www.nongnu.org/lzip/tarlz.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # Hard configure requirement (lzlib probe fails without it).
        # Already published in the ohpcd registry — direct reference,
        # no import needed (§3.7 "依赖已发布" row).
        self.requires("lzlib/1.15")

    def build_requirements(self):
        # Unpacks the upstream .tar.lz (conan's unzipper cannot).
        self.tool_requires("lzip/1.25")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"tarlz is adapted for Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        """Fetch and verify the official Savannah release file.

        Unpacking is deferred to build(): it needs the lzip binary from
        build_requirements, which is only guaranteed on PATH under the
        conanbuild environment.  The CA trust store is resolved from
        conan's own certifi or $CONAN_HOME/cacert.pem with a hard
        failure when neither exists.
        """
        source = dict(self.conan_data["sources"])
        archive = Path(self.source_folder, "tarlz-source.tar.lz")
        self._fetch(source["url"], archive, source["sha256"])

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(self._configure_args())
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            self._build_ohos()
        else:
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["install-bin"])

    def package(self):
        if str(self.settings.os) == "OHOS":
            self._package_ohos()
        else:
            Autotools(self).install(args=["install-bin"])
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

    # ── configure arguments ─────────────────────────────────────────────

    def _configure_args(self):
        return [
            # Same triplet convention as the merged tardy/zvbi recipes:
            # the shipped config.sub is not guaranteed to know "ohos";
            # aarch64-unknown-linux-gnu is accepted.
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
            "--prefix=/",
            "--disable-dependency-tracking",
        ]

    # ── OHOS build machinery ────────────────────────────────────────────

    def _build_ohos(self):
        shell = self._resolve_shell()
        self._unpack_upstream(shell)
        self._restore_script_modes()
        self._relax_umask_in_configure()
        with self._build_environment().vars(self).apply():
            self._run_ohos(
                f"{shlex.quote(shell)} ./configure "
                f"{' '.join(shlex.quote(a) for a in self._configure_args())}"
            )
            self._run_ohos("make -j1")

    def _unpack_upstream(self, shell):
        """lzip -d + tar -xf the verified .tar.lz into the build folder."""
        archive = next(Path(self.source_folder).glob("tarlz-source.tar.lz"),
                       None)
        if archive is None:
            raise ConanException("verified upstream archive missing "
                                 "from the source folder")
        with self._build_environment().vars(self).apply():
            self._run_ohos(
                f"lzip -d -k -f {shlex.quote(str(archive))} "
                f"-o {shlex.quote(str(Path(self.build_folder, 'tarlz-source.tar')))}"
            )
            self._run_ohos(
                f"{shlex.quote(shell)} -c "
                f"\"tar -xf tarlz-source.tar --strip-components=1\""
            )

    def _restore_script_modes(self):
        """Make the autotools helper scripts executable again (E490)."""
        candidates = [
            "configure", "config.guess", "config.sub", "install-sh",
            "missing", "depcomp", "compile", "ltmain.sh", "config.status",
            "ar-lib", "mkinstalldirs", "test-driver",
        ]
        for relative in candidates:
            path = Path(self.build_folder, relative)
            if path.is_file():
                path.chmod(path.stat().st_mode | 0o111)
        for helper in Path(self.build_folder, "build-aux").glob("*"):
            if helper.is_file():
                helper.chmod(helper.stat().st_mode | 0o111)

    def _relax_umask_in_configure(self):
        """Rewrite `umask 077` -> `umask 022` in the generated configure.

        Device-verified (tardy, ncrack, libcaca, libabw, zvbi): the
        scratch dir is created with `umask 077` giving mode 2700, and hmdfs
        decides traversal on the group bits where `chmod` is a no-op, so
        the directory is untraversable (EACCES on everything inside it).
        022 yields `drwxr-s--x`.
        """
        path = Path(self.build_folder, "configure")
        if not path.is_file():
            raise ConanException(f"configure script is missing: {path}")
        content = path.read_text(encoding="utf-8")
        count = content.count("umask 077")
        self.output.info(f"umask 077 occurrences in configure: {count}")
        if count == 0:
            raise ConanException(
                "umask contract changed in configure: no 'umask 077' found, "
                "hmdfs workaround has nothing to rewrite"
            )
        path.write_text(content.replace("umask 077", "umask 022"),
                        encoding="utf-8", newline="\n")

    def _package_ohos(self):
        shell = self._resolve_shell()
        with self._build_environment().vars(self).apply():
            destination = shlex.quote(self.package_folder)
            # install-bin only: install-doc needs GROFF+ps2pdf
            # (PDF manuals), unavailable on the device/CI fleet.
            self._run_ohos(f"make -j1 install-bin DESTDIR={destination}")

    def _build_environment(self):
        temporary = Path(self.build_folder, ".tmp")
        temporary.mkdir(parents=True, exist_ok=True)
        environment = Environment()
        environment.define_path("TMPDIR", str(temporary))
        # tool_requires binaries (lzip for the .tar.lz unpack) are not on
        # a raw subprocess PATH — expose them explicitly (R33: declared
        # build requirement, not ambient PATH).
        for dep in self.dependencies.build.values():
            for bindir in dep.cpp_info.bindirs:
                environment.prepend_path("PATH", bindir)
        # Raw subprocess never sees conan's dependency flags, so expose
        # the direct host dependencies' headers/libraries explicitly
        # (configure probes -llz itself; it only needs -I/-L to find it).
        cppflags, ldflags = [], []
        for dep in self.dependencies.values():
            info = dep.cpp_info
            cppflags.extend(f"-I{d}" for d in info.includedirs)
            ldflags.extend(f"-L{d}" for d in info.libdirs)
        if cppflags:
            environment.append("CPPFLAGS", " ".join(cppflags))
        if ldflags:
            environment.append("LDFLAGS", " ".join(ldflags))
        # No LD_LIBRARY_PATH here, on purpose (see tardy recipe: the SDK's
        # lld resolves libraries from LD_LIBRARY_PATH before its own rpath
        # and this recipe's consumers run under conan's conanrun env).
        for name, value in self._compiler_environment_items().items():
            environment.define(name, value)
        return environment

    def _compiler_environment_items(self):
        """CC/CXX from the profile's tools.build:compiler_executables.

        The toolchain script holding them is sourced only by conan's own
        Autotools() helper, so a raw subprocess must be given them directly
        (R33: the toolchain comes from a declared source, not from PATH).
        """
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default=None)
        if not compilers:
            return {}
        if isinstance(compilers, str):
            import json
            try:
                compilers = json.loads(compilers)
            except ValueError:
                return {}
        mapping = {"c": "CC", "cpp": "CXX"}
        return {variable: compilers[key]
                for key, variable in mapping.items() if compilers.get(key)}

    def _resolve_shell(self):
        for candidate in OHOS_SHELL_CANDIDATES:
            if os.path.sep in candidate:
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    return candidate
                continue
            for directory in os.environ.get("PATH", "").split(os.pathsep):
                path = os.path.join(directory, candidate)
                if os.path.isfile(path) and os.access(path, os.X_OK):
                    return path
        raise ConanInvalidConfiguration(
            "no suitable shell found on OHOS (need the hnp bash or zsh; "
            "zsh cannot run automake's recursive make)"
        )

    def _run_ohos(self, command, cwd=None):
        shell = self._resolve_shell()
        environment = dict(os.environ)
        environment["SHELL"] = shell
        environment["CONFIG_SHELL"] = shell
        completed = subprocess.run(
            command + " < /dev/null", shell=True, env=environment,
            cwd=cwd or self.build_folder, stdin=subprocess.DEVNULL,
        )
        if completed.returncode != 0:
            self._dump_failure_diagnostics(cwd or self.build_folder,
                                           environment)
            raise ConanException(
                f"OHOS build step failed (rc={completed.returncode}): {command}"
            )

    def _dump_failure_diagnostics(self, directory, environment):
        """Evidence for a failed step, printed into the captured build log.

        A CI worker's log is the only observation point this recipe gets on
        that fleet and it is truncated to the last 4000 characters, so the
        output stays deliberately compact (OP-8).
        """
        self.output.info("---- ohos diagnostics: environment ----")
        for name in ("CC", "CXX", "CPPFLAGS", "LDFLAGS", "LIBS", "CFLAGS",
                     "TMPDIR"):
            if name in environment:
                self.output.info(f"{name}={environment[name]}")
        config_log = Path(directory, "config.log")
        if not config_log.is_file():
            self.output.info("no config.log in the failing directory")
            return
        text = config_log.read_text(errors="replace")
        marker = "checking whether the C compiler works"
        start = text.rfind(marker)
        window = text[start:] if start != -1 else text[-2000:]
        self.output.info("---- config.log: last compiler-test block ----")
        for line in window.splitlines()[:14]:
            self.output.info(line)

    # ── download helpers ────────────────────────────────────────────────

    def _ca_bundle(self):
        candidates = []
        try:
            import certifi
            candidates.append(certifi.where())
        except ImportError:
            pass
        conan_home = os.getenv("CONAN_HOME") or os.path.join(
            os.path.expanduser("~"), ".conan2")
        candidates.append(os.path.join(conan_home, "cacert.pem"))
        candidates.append(os.getenv("SSL_CERT_FILE") or "")
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        raise ConanException(
            "no CA bundle found for the source download: looked for certifi's "
            "cacert, $CONAN_HOME/cacert.pem and $SSL_CERT_FILE"
        )

    def _fetch(self, url, destination, sha256, attempts=3):
        destination = Path(destination)
        staging = destination.with_name(destination.name + ".part")
        if url.startswith("file:"):
            from urllib.parse import urlparse
            from urllib.request import url2pathname
            import shutil
            shutil.copyfile(url2pathname(urlparse(url).path), staging)
        else:
            context = ssl.create_default_context(cafile=self._ca_bundle())
            last = None
            for attempt in range(1, attempts + 1):
                try:
                    request = urllib.request.Request(
                        url, headers={"User-Agent": "conan"})
                    with urllib.request.urlopen(request, timeout=120,
                                                context=context) as response:
                        payload = response.read()
                        status = response.status
                    staging.write_bytes(payload)
                    self.output.info(
                        f"downloaded {len(payload)} bytes (HTTP {status}) "
                        f"from {url}")
                    break
                except Exception as error:  # noqa: BLE001 - reported verbatim
                    last = error
                    self.output.warning(
                        f"download attempt {attempt}/{attempts} failed for "
                        f"{url}: {type(error).__name__}: {error}")
                    if staging.exists():
                        staging.unlink()
                    if attempt < attempts:
                        time.sleep(5)
            else:
                raise ConanException(f"could not download {url}: {last}")

        digest = hashlib.sha256(staging.read_bytes()).hexdigest()
        if digest != sha256:
            staging.unlink()
            raise ConanException(
                f"sha256 mismatch for {url}: expected {sha256}, got {digest}")
        os.replace(staging, destination)
