#!/usr/bin/env python3
"""Conan recipe — tunnelx 20190701 (Tunnel / TunnelX).

Tunnel is Julian Todd's Java 2.5D cave-survey drawing program: drawings are
distorted to fit changes in the underlying Survex-compatible centreline
network.  The tree is pure Java (81 ``src/*.java``, package ``Tunnel``, no
C/C++ and no native layer at all).

Upstream build pipeline (both scripts live in the source root):

  ``build``  : javac -version -d . src/*.java
  ``jmake``  : ls -1 symbols > symbols/listdir.txt
               ls -1 tutorials > tutorials/listdir.txt
               jar cmf tunnelmanifest.txt tunnel2019a.jar Tunnel \\
                   symbols/*.xml symbols/*.html symbols/helpfile.md \\
                   symbols/listdir.txt tutorials/*.* tutorials/listdir.txt

``tunnelmanifest.txt`` declares ``Main-Class: Tunnel.MainBox`` and the runtime
entry is ``java -ea -Xmx3000M -cp . Tunnel.MainBox <datadir>`` (script ``run``).
This recipe reproduces that pipeline with ``javac`` + ``jar`` taken from the
HarmonyOS BiSheng OpenJDK; no ant/maven/gradle is involved (the tree carries
none of their manifests).

HarmonyOS (OHOS) specifics handled here:

* the OHOS PC ships no JDK on ``PATH``; the BiSheng OpenJDK 17.0.13 runtime is
  installed by the platform (``~/bishengjdk17``) and, when absent, is fetched
  from the official OpenHarmonyPCDeveloper ``cmd-pkgs`` release channel;
* ``/tmp`` is not writable on HarmonyOS, so the generated launcher redirects
  the JVM temp directory (``java.io.tmpdir``) to a writable ``$TMPDIR``/``$HOME/tmp``
  — the upstream code falls back to ``java.io.tmpdir`` when neither
  ``<cwd>/tmp`` nor ``~/.tunnelx/tmp/`` exists (src/FileAbstraction.java:136-142);
* the packaged JAR embeds ``symbols/`` and ``tutorials/`` plus their
  ``listdir.txt`` so the application is self-contained: src/FileAbstraction.java
  resolves them through the class loader (``symbols/listdir.txt``) when no
  on-disk directory is present.

Upstream automation: none.  The tree contains no test source, no JUnit, no
``make check``/ctest/pytest registration and no autopkgtest; its only
``public static void main`` is the AWT/Swing entry ``Tunnel.MainBox.main``
(src/MainBox.java:596).  See test_package/MANIFEST.yml.

Runtime: BiSheng OpenJDK 17.0.13 (aarch64, musl) — system tool, no Conan
dependency (the OHOS registry carries no JVM ref).
"""
import glob
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class TunnelxConan(ConanFile):
    name = "tunnelx"
    version = "20190701"
    description = ("Tunnel (TunnelX) — Java 2.5D cave survey drawing program "
                   "for Survex-compatible centreline data")
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/goatchurchprime/tunnelx"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    # OHOS CI L0p gate: the OHOS profile carries all four settings values.
    settings = "os", "compiler", "build_type", "arch"

    # No source patches: the upstream tree is used as-is and nothing is written
    # outside the package directory; the HarmonyOS layer is the installed
    # launcher.  conandata.yml therefore declares an empty patch list.

    _JDK_URL = ("https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/"
                "releases/download/pkgs/"
                "bishengjdk-17.0.13-ohos-aarch64.tar.gz")
    _JDK_TOOLS = ("java", "javac", "jar")

    # ────────────────────────────── layout ──────────────────────────────
    def export_sources(self):
        # conandata.yml declares an empty patch list for this version; the hook
        # is kept so the recipe stays complete should a patch ever be added.
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "tunnelx is packaged for Linux/OHOS only")
        if str(self.settings.arch) not in ("armv8", "aarch64", "x86_64"):
            raise ConanInvalidConfiguration(
                f"unsupported arch: {self.settings.arch}")

    # ────────────────────────────── source ──────────────────────────────
    def source(self):
        # conandata.yml carries tar_format for the archive spec; get() takes
        # only url/sha256 (see archives/a/accountsservice, archives/m/motif).
        source_data = dict(self.conan_data["sources"]["20190701"])
        source_data.pop("tar_format", None)
        get(self, **source_data, strip_root=True)

    # ────────────────────────────── toolchain ───────────────────────────
    def _is_jdk(self, root):
        return bool(root) and all(
            os.path.isfile(os.path.join(root, "bin", tool))
            for tool in self._JDK_TOOLS)

    def _jdk_roots_under(self, root):
        """JDK roots in a freshly unpacked archive (flat or one level nested)."""
        roots = [root]
        if os.path.isdir(root):
            roots += [os.path.join(root, entry)
                      for entry in sorted(os.listdir(root))
                      if os.path.isdir(os.path.join(root, entry))]
        return roots

    def _find_jdk(self):
        """Locate the HarmonyOS BiSheng JDK, installing it if necessary."""
        for candidate in (os.environ.get("JAVA_HOME", ""),
                          os.path.expanduser("~/bishengjdk17"),
                          os.path.expanduser("~/usr/local/bishengjdk17"),
                          "/usr/local/bishengjdk17",
                          "/data/service/hnp/bishengjdk17"):
            if self._is_jdk(candidate):
                return candidate

        javac = shutil.which("javac")
        if javac:
            root = os.path.dirname(os.path.dirname(os.path.realpath(javac)))
            if self._is_jdk(root):
                return root

        download_dir = os.path.join(self.build_folder, "bishengjdk17")
        for root in self._jdk_roots_under(download_dir):
            if self._is_jdk(root):
                return root

        self.output.info("Installing BiSheng OpenJDK 17.0.13 from cmd-pkgs")
        os.makedirs(download_dir, exist_ok=True)
        get(self, url=self._JDK_URL, destination=download_dir)
        for root in self._jdk_roots_under(download_dir):
            if self._is_jdk(root):
                return root
        raise ConanInvalidConfiguration(
            "BiSheng OpenJDK 17.0.13 archive downloaded but no JDK layout "
            f"found under {download_dir}")

    # ────────────────────────────── build ───────────────────────────────
    def build(self):
        apply_conandata_patches(self)          # no-op: empty patch list (20190701)
        jdk = self._find_jdk()
        javac = os.path.join(jdk, "bin", "javac")
        jar = os.path.join(jdk, "bin", "jar")
        src = self.source_folder

        # upstream `build`: javac -version -d . src/*.java  (81 files, no -cp)
        java_files = sorted(glob.glob(os.path.join(src, "src", "*.java")))
        if len(java_files) != 81:
            raise ConanInvalidConfiguration(
                f"expected 81 src/*.java files, found {len(java_files)}")
        classes_dir = os.path.join(self.build_folder, "classes")
        os.makedirs(classes_dir, exist_ok=True)
        self._run([javac, "-version", "-encoding", "UTF-8",
                   "-d", classes_dir] + java_files, cwd=src, log="javac.log")

        # upstream `jmake`: assemble the JAR root (classes + symbols + tutorials
        # + the two generated listdir.txt files) away from the source tree.
        jarroot = os.path.join(self.build_folder, "jarroot")
        os.makedirs(jarroot, exist_ok=True)
        shutil.copytree(os.path.join(classes_dir, "Tunnel"),
                        os.path.join(jarroot, "Tunnel"))
        for entry in ("symbols", "tutorials"):
            dst = os.path.join(jarroot, entry)
            shutil.copytree(os.path.join(src, entry), dst)
            # upstream `jmake` runs `ls -1 symbols > symbols/listdir.txt`, so the
            # shell creates listdir.txt before ls enumerates the directory and
            # the listing therefore contains "listdir.txt" itself (the consumer
            # filters that name, see src/FileAbstraction.java:194,718).
            listing_path = os.path.join(dst, "listdir.txt")
            open(listing_path, "w", encoding="utf-8").close()
            listing = sorted(os.listdir(dst))
            with open(listing_path, "w", encoding="utf-8") as handle:
                handle.write("\n".join(listing) + "\n")

        self.jar_path = os.path.join(self.build_folder, "tunnelx.jar")
        # jar cfe <out> Tunnel.MainBox -C <jarroot> "Tunnel" -C <jarroot> "symbols" ...
        self._run([jar, "cfe", self.jar_path, "Tunnel.MainBox",
                   "-C", jarroot, "Tunnel",
                   "-C", jarroot, "symbols",
                   "-C", jarroot, "tutorials"],
                  cwd=self.build_folder, log="jar.log")

        # upstream `run`: java -ea -Xmx3000M -cp . Tunnel.MainBox
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "no_tests",
            "framework": "none",
            "command": "N/A (upstream ships no automated test harness)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": ("upstream tree has no test source / JUnit / make check / "
                       "ctest / autopkgtest; sole entry is the GUI main class "
                       "Tunnel.MainBox (src/MainBox.java:596)"),
        }, ensure_ascii=False), flush=True)

    def _run(self, command, cwd, log):
        """Run a build command, streaming and logging stdout+stderr."""
        log_path = os.path.join(self.build_folder, log)
        with open(log_path, "w", encoding="utf-8") as handle:
            proc = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True)
            handle.write(proc.stdout or "")
        self.output.info("".join((proc.stdout or "").splitlines(True)[-20:]))
        if proc.returncode != 0:
            raise ConanInvalidConfiguration(
                f"command failed ({proc.returncode}): {' '.join(command)} "
                f"— log: {log_path}")

    # ────────────────────────────── package ─────────────────────────────
    def package(self):
        copy(self, "tunnelx.jar", src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "readme.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        self._write_launcher()

    def _write_launcher(self):
        """Installed launcher: OHOS JDK discovery + writable temp directory."""
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        launcher = os.path.join(bin_dir, "tunnelx")
        script = (
            '#!/bin/sh\n'
            '# HarmonyOS launcher for Tunnel (TunnelX) — generated by the Conan recipe.\n'
            '#\n'
            '# HarmonyOS notes:\n'
            '#  * no java on PATH: locate the platform BiSheng OpenJDK (HNP);\n'
            '#  * /tmp is not writable: point java.io.tmpdir at $TMPDIR/$HOME/tmp so\n'
            '#    the upstream FileAbstraction tmpdir fallback stays writable.\n'
            'set -eu\n'
            '\n'
            '# ── CLI contract: <bin> --version / --help (CI L2 smoke test) ──\n'
            '# Handled before JDK discovery so the contract works without a JVM.\n'
            'case "${1:-}" in\n'
            '  --version|-version)\n'
            '    echo "Tunnel (TunnelX) ' + self.version + ' — HarmonyOS build of the 2019-07-01 snapshot"\n'
            '    echo "upstream snapshot: version2019-07-01 DoES (git tag R2019a)"\n'
            '    exit 0\n'
            '    ;;\n'
            '  --help|-h)\n'
            '    echo "Usage: tunnelx [<datadir>] [Tunnel.MainBox options]"\n'
            '    echo "  <datadir>            directory to open on startup"\n'
            '    echo "  --verbose|--quiet    logging verbosity"\n'
            '    echo "  --todenode           load TodeNode data"\n'
            '    echo "  --makeimages         render sketches to images"\n'
            '    echo "  --twotone            two-tone printing mode"\n'
            '    echo "  --printdir=DIR       printing output directory"\n'
            '    echo "  --netconnection      connect to the local tunnelx receiver"\n'
            '    echo "  --version            print version and exit"\n'
            '    echo "Tunnel (TunnelX): Java 2.5D cave survey drawing program."\n'
            '    exit 0\n'
            '    ;;\n'
            'esac\n'
            '\n'
            'if [ -z "${JAVA_HOME:-}" ] || [ ! -x "$JAVA_HOME/bin/java" ]; then\n'
            '  for candidate in "$HOME/bishengjdk17" "$HOME/usr/local/bishengjdk17" \\\n'
            '                   /usr/local/bishengjdk17 /data/service/hnp/bishengjdk17; do\n'
            '    if [ -x "$candidate/bin/java" ]; then\n'
            '      JAVA_HOME="$candidate"\n'
            '      break\n'
            '    fi\n'
            '  done\n'
            'fi\n'
            'if [ -z "${JAVA_HOME:-}" ] || [ ! -x "$JAVA_HOME/bin/java" ]; then\n'
            '  echo "Error: JAVA_HOME not found. Set JAVA_HOME or install BiShengJDK 17." >&2\n'
            '  exit 1\n'
            'fi\n'
            'export JAVA_HOME\n'
            '\n'
            'TMP_CANDIDATE="${TMPDIR:-}"\n'
            'if [ -z "$TMP_CANDIDATE" ] || [ ! -d "$TMP_CANDIDATE" ]; then\n'
            '  TMP_CANDIDATE="$HOME/tmp"\n'
            'fi\n'
            'if [ ! -d "$TMP_CANDIDATE" ]; then\n'
            '  TMP_CANDIDATE="/tmp"\n'
            'fi\n'
            '\n'
            'SELF_DIR="$(cd "$(dirname "$0")" && pwd)"\n'
            'TUNNELX_HOME="$(cd "$SELF_DIR/.." && pwd)"\n'
            'JAR="$TUNNELX_HOME/lib/tunnelx.jar"\n'
            'if [ ! -f "$JAR" ]; then\n'
            '  echo "Error: $JAR not found." >&2\n'
            '  exit 1\n'
            'fi\n'
            '\n'
            'exec "$JAVA_HOME/bin/java" -ea -Xmx1000M \\\n'
            '  -Djava.io.tmpdir="$TMP_CANDIDATE" \\\n'
            '  -cp "$JAR" Tunnel.MainBox "$@"\n'
        )
        with open(launcher, "w", encoding="utf-8") as handle:
            handle.write(script)
        os.chmod(launcher, 0o755)

    # ────────────────────────────── package_info ────────────────────────
    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.buildenv_info.define_path(
            "TUNNELX_JAR", os.path.join(self.package_folder, "lib", "tunnelx.jar"))
        self.buildenv_info.define(
            "TUNNELX_MAIN_CLASS", "Tunnel.MainBox")
