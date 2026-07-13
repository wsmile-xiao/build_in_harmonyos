#!/usr/bin/env python3
"""Conan recipe — Scala 2.12.21 (JVM precompiled distribution).

This is NOT a C/C++ source project. The source archive contains prebuilt
shell scripts (bin/) and JAR files (lib/) that run on any JVM.

Build steps: download → extract → copy to staging → verify
No configure, no make.
"""
import os
import subprocess
import hashlib

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import copy, apply_conandata_patches, export_conandata_patches


class ScalaConan(ConanFile):
    name = "scala"
    version = "2.12.21"
    description = "Scala 2.12.21 — JVM programming language and runtime"
    license = "Apache-2.0"
    homepage = "https://www.scala-lang.org/"
    url = "https://github.com/scala/scala"

    # Settings required for package compatibility metadata.
    # Scala is JVM-based (architecture-independent), but Conan requires
    # these to match the consumer profile.
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def system_requirements(self):
        # Scala requires a JVM (bishengjdk 17+) installed on the system.
        # bishengjdk is provided via cmd-pkgs, not as a Conan package.
        import shutil
        if not shutil.which("java"):
            self.output.warning(
                "Java (JVM) is required but not found in PATH. "
                "Install bishengjdk 17.0.13 via: "
                "curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/"
                "releases/download/pkgs/install-jdk.sh | sh -s -- 17.0.13"
            )

    def layout(self):
        # Use basic layout — source folder is the extracted distribution.
        from conan.tools.layout import basic_layout
        basic_layout(self)

    def source(self):
        # Download and extract the precompiled distribution.
        # Use wget/curl instead of Conan's get() — Python's ssl module may not
        # be available on OHOS CI workers, but wget/curl have their own SSL.
        import shutil

        url = self.conan_data["sources"]["url"]
        expected_sha256 = self.conan_data["sources"]["sha256"]
        filename = url.split("/")[-1]
        archive = os.path.join(self.source_folder, filename)

        env = os.environ.copy()
        ssl_cert = "/storage/Users/currentUser/usr/local/ssl/cert.pem"
        if os.path.exists(ssl_cert):
            env["SSL_CERT_FILE"] = ssl_cert

        wget_path = shutil.which("wget")
        curl_path = shutil.which("curl")

        if wget_path:
            subprocess.check_call(
                [wget_path, "-O", archive, url], env=env, timeout=120,
            )
        elif curl_path:
            subprocess.check_call(
                [curl_path, "-L", "--connect-timeout", "30", "-o", archive, url],
                env=env, timeout=120,
            )
        else:
            raise ConanException(
                "Neither wget nor curl found in PATH. "
                "Install one to download source archives."
            )

        # Verify SHA256 checksum
        h = hashlib.sha256()
        with open(archive, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        actual_sha256 = h.hexdigest()
        if actual_sha256 != expected_sha256:
            os.remove(archive)
            raise ConanException(
                f"SHA256 mismatch: expected {expected_sha256}, got {actual_sha256}"
            )

        # Extract (strip_root: remove top-level scala-2.12.21/ directory)
        subprocess.check_call(
            ["tar", "xfz", archive, "--strip-components=1"],
            cwd=self.source_folder, env=env,
        )
        os.remove(archive)

    def build(self):
        # Apply patches if any (no patches for this precompiled distribution)
        apply_conandata_patches(self)
        # Precompiled distribution — no compilation needed.
        # The source archive contains prebuilt bin/ (shell scripts) and
        # lib/ (JAR files) that are ready to use on any JVM.
        #
        # R32: Platform compatibility check.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Scala precompiled distribution supports Linux/OHOS, "
                f"got {self.settings.os}"
            )
        self.output.info("Scala is a JVM precompiled distribution — no build step needed.")

    def package(self):
        # Copy precompiled bin/ and lib/ to the package folder.
        copy(self, "*", src=os.path.join(self.source_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "*", src=os.path.join(self.source_folder, "lib"),
             dst=os.path.join(self.package_folder, "lib"))
        # Copy man pages
        copy(self, "*", src=os.path.join(self.source_folder, "man"),
             dst=os.path.join(self.package_folder, "man"))
        # Copy documentation
        copy(self, "*", src=os.path.join(self.source_folder, "doc"),
             dst=os.path.join(self.package_folder, "doc"))
        # Copy license files
        copy(self, "LICENSE", src=self.source_folder, dst=self.package_folder)
        copy(self, "NOTICE", src=self.source_folder, dst=self.package_folder)

    def package_info(self):
        # Scala is a JVM toolset — expose via environment variables,
        # not as C/C++ libraries.
        bin_path = os.path.join(self.package_folder, "bin")
        lib_path = os.path.join(self.package_folder, "lib")

        # Set PATH so scala, scalac, etc. are available
        self.env_info.PATH.append(bin_path)
        # Set SCALA_HOME for tools that reference it
        self.env_info.SCALA_HOME = self.package_folder
        # Classpath includes the Scala JARs
        self.env_info.CLASSPATH = (
            lib_path + "/scala-library.jar:"
            + lib_path + "/scala-compiler.jar:"
            + lib_path + "/scala-reflect.jar"
        )

        self.user_info.scala_home = self.package_folder
        self.user_info.bin_dir = bin_path
        self.user_info.lib_dir = lib_path

        self.cpp_info.libs = []  # No native libraries
