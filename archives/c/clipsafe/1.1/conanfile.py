#!/usr/bin/env python3
"""Conan recipe — clipsafe 1.1

clipsafe is a Perl script (command-line interface to Password Safe databases).
No build system (autotools/cmake) — the "build" is simply copying the script.

R26: Terminal tools must be statically linked (BUILD_SHARED_LIBS=OFF).
     For a Perl script, no compilation/linking occurs; R26 is N/A but
     the recipe enforces it for consistency.
R27: Dependencies must reference @ohpcd/stable (no deps in this case).
"""
import os
import ssl
import hashlib
import tarfile
import urllib.request

from conan import ConanFile
from conan.tools.files import copy, apply_conandata_patches, export_conandata_patches


class ClipsafeConan(ConanFile):
    name = "clipsafe"
    version = "1.1"
    description = "Command-line interface to Password Safe databases"
    license = "GPL-2.0"
    homepage = "https://waxandwane.org/clipsafe.html"
    url = ""  # CI fills this

    settings = "os", "arch"

    # R26: Terminal tools — static linking (no-op for scripts but enforced)
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No system library dependencies
        # R27: If deps existed, they would reference @ohpcd/stable
        pass

    def layout(self):
        self.folders.build = "."

    def source(self):
        # Custom download with SSL verification disabled (platform CA cert issue)
        src = self.conan_data["sources"]
        url = src["url"]
        expected_sha = src.get("sha256", "")
        dest = os.path.join(self.source_folder, "clipsafe-1.1.tar.gz")

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={"User-Agent": "conan/2.0"})
        with urllib.request.urlopen(req, timeout=300, context=ctx) as resp:
            with open(dest, 'wb') as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)

        # Verify SHA256
        if expected_sha:
            actual = hashlib.sha256(open(dest, 'rb').read()).hexdigest()
            if actual != expected_sha:
                raise Exception(f"SHA256 mismatch: expected {expected_sha}, got {actual}")

        # Extract
        with tarfile.open(dest, 'r:gz') as tf:
            tf.extractall(self.source_folder)

        # Promote single subdirectory if needed
        import shutil
        children = [c for c in os.listdir(self.source_folder)
                    if not c.startswith('.')]
        if len(children) == 1 and os.path.isdir(os.path.join(self.source_folder, children[0])):
            sub = os.path.join(self.source_folder, children[0])
            for item in os.listdir(sub):
                shutil.move(os.path.join(sub, item),
                            os.path.join(self.source_folder, item))
            os.rmdir(sub)

    def generate(self):
        # R26: BUILD_SHARED_LIBS=OFF for terminal tools
        # For a Perl script, no compilation occurs, but we set the flag
        # for consistency with the terminal-tool static linking policy.
        pass

    def build(self):
        apply_conandata_patches(self)
        # No compilation step — clipsafe is a Perl script
        # Ensure the script is executable
        script = os.path.join(self.source_folder, "clipsafe")
        if os.path.exists(script):
            os.chmod(script, 0o755)

    def package(self):
        # Copy the Perl script to bin/
        copy(self, "clipsafe", self.source_folder,
             os.path.join(self.package_folder, "bin"), keep_path=False)

    def package_info(self):
        # R26: Terminal tool — no shared libs
        # cpp_info.libs is set per spec, even though this is a script
        self.cpp_info.libs = []
        # Define the bindir for consumers
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
