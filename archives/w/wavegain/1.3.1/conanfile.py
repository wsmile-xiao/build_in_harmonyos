#!/usr/bin/env python3
"""Conan recipe for wavegain 1.3.1 — ReplayGain for PCM WAV files.

WaveGain applies ReplayGain album/track gain to standard PCM wave
files.  Pure C, zero external dependencies (FreeBSD port declares
0 dependencies), upstream ships sources only (no configure, no
Makefile — Windows .sln/.vcproj are the only project files), so the
build is a direct `$CC *.c -o wavegain` with the profile compiler.

Upstream ships no test harness (no testsuite/, no `make check`) —
declared as such (R51, libexplain precedent): consumers verify through
test_package/, which synthesizes a minimal PCM WAV fixture in shell,
runs the gain pass, and asserts a changed payload with exit 0.

OHOS notes: bundled getopt.c/getopt1.c cover platforms without
getopt_long; no autotools, hence no umask/configure workarounds apply.
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
                               export_conandata_patches, unzip)
from conan.tools.layout import basic_layout

OHOS_SHELL_CANDIDATES = ("/data/service/hnp/bin/bash", "/usr/bin/zsh", "bash")

# Upstream 1.3.1 file set (C sources only; Windows project files excluded
# from the build but kept in the source tree untouched).
SOURCES = [
    "audio.c", "dither.c", "gain_analysis.c", "getopt.c", "getopt1.c",
    "main.c", "misc.c", "recurse.c", "wavegain.c",
]


class WavegainConan(ConanFile):
    name = "wavegain"
    version = "1.3.1"
    description = "ReplayGain volume normalization for PCM WAV files"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/MestreLion/wavegain"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"wavegain is adapted for Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        """Fetch and unpack the official 1.3.1 tag tarball.

        CA trust from conan's own certifi or $CONAN_HOME/cacert.pem,
        hard failure when neither exists; sha256 verified (R39).
        """
        source = dict(self.conan_data["sources"])
        archive = Path(self.source_folder, "wavegain-source.tar.gz")
        self._fetch(source["url"], archive, source["sha256"])
        unzip(self, str(archive), destination=self.source_folder,
              strip_root=True)
        archive.unlink()

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            self._build_ohos()
        else:
            self._compile(subprocess, self.source_folder, self.build_folder,
                          self._host_cc())

    def package(self):
        binary = "wavegain"
        copy(self, binary, src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

    # ── OHOS build ──────────────────────────────────────────────────────

    def _build_ohos(self):
        compilers = self._compiler_environment_items()
        cc = compilers.get("CC", "cc")
        self._compile_sh(cc, self.source_folder, self.build_folder)

    def _compile_sh(self, cc, src_dir, build_dir):
        """Direct $CC compile of the nine C sources (no build system)."""
        shell = self._resolve_shell()
        objects = " ".join(SOURCES)
        with self._build_environment().vars(self).apply():
            # -fcommon: tentative definitions in headers need common linkage (clang15 defaults -fno-common); -DHAVE_CONFIG_H: upstream only pulls config.h (LITTLE/BIG,
            # machine_endianness) under this macro (Windows builds define
            # it in-project). -lm: gain_analysis/dither use libm.
            self._run_ohos(
                f"{shlex.quote(cc)} -O2 -fcommon -DHAVE_CONFIG_H -o "
                f"{shlex.quote(str(Path(build_dir, 'wavegain')))} "
                f"{objects} -lm",
                cwd=src_dir, shell=shell,
            )

    def _host_cc(self):
        return os.environ.get("CC", "cc")

    def _compile(self, subprocess_mod, src_dir, build_dir, cc):
        cmd = ([cc, "-O2", "-fcommon", "-DHAVE_CONFIG_H", "-o",
                str(Path(build_dir, "wavegain"))]
               + SOURCES + ["-lm"])
        completed = subprocess_mod.run(cmd, cwd=src_dir)
        if completed.returncode != 0:
            raise ConanException(
                f"host build step failed (rc={completed.returncode}): "
                f"{' '.join(cmd)}")

    def _build_environment(self):
        temporary = Path(self.build_folder, ".tmp")
        temporary.mkdir(parents=True, exist_ok=True)
        environment = Environment()
        environment.define_path("TMPDIR", str(temporary))
        for name, value in self._compiler_environment_items().items():
            environment.define(name, value)
        return environment

    def _compiler_environment_items(self):
        """CC from the profile's tools.build:compiler_executables (R33)."""
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
        return {"CC": compilers["c"]} if compilers.get("c") else {}

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
            "no suitable shell found on OHOS (need the hnp bash or zsh)"
        )

    def _run_ohos(self, command, cwd=None, shell=None):
        shell = shell or self._resolve_shell()
        environment = dict(os.environ)
        environment["SHELL"] = shell
        environment["CONFIG_SHELL"] = shell
        completed = subprocess.run(
            command + " < /dev/null", shell=True, env=environment,
            cwd=cwd or self.build_folder, stdin=subprocess.DEVNULL,
        )
        if completed.returncode != 0:
            raise ConanException(
                f"OHOS build step failed (rc={completed.returncode}): {command}"
            )

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
