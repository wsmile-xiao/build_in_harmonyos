#!/usr/bin/env python3
"""Conan recipe — docker-machine v0.16.2

Docker Machine is a tool that lets you install Docker Engine on virtual
computers on your local machine, on cloud providers, and so on.

Build system: Go (module mode with vendored dependencies).
The CI worker does not have Go pre-installed, so this recipe downloads
the Harmonybrew Go bottle and uses it for building.

License: Apache-2.0
"""
import os
import shutil
import tarfile
import urllib.request

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class DockerMachineConan(ConanFile):
    name = "docker-machine"
    version = "v0.16.2"
    description = "Tool to install Docker Engine on virtual or cloud computers"
    license = "Apache-2.0"
    homepage = "https://github.com/docker/machine"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ensure_go(self):
        """Download and set up Go if not available in PATH."""
        # Check if go is already in PATH
        go_bin = shutil.which("go")
        if go_bin:
            return go_bin, None

        # Download Go from Harmonybrew bottle
        go_version = "1.26.5"
        bottle_url = f"https://harmonybrew.atomgit.com/bottles/go-{go_version}.arm64_ohos.bottle.tar.gz"
        # Bottle extracts to go/{version}/ structure
        extract_dir = os.path.join(self.build_folder, "toolchain")
        go_exe = os.path.join(extract_dir, "go", go_version, "bin", "go")
        go_root = os.path.join(extract_dir, "go", go_version, "libexec")

        if os.path.exists(go_exe):
            return go_exe, go_root

        # Download bottle
        tarball_path = os.path.join(self.build_folder, "go-bottle.tar.gz")
        self.output.info(f"Downloading Go {go_version} from Harmonybrew...")
        urllib.request.urlretrieve(bottle_url, tarball_path)

        # Extract bottle
        os.makedirs(extract_dir, exist_ok=True)
        with tarfile.open(tarball_path, "r:gz") as tar:
            tar.extractall(path=extract_dir)

        # Clean up
        os.unlink(tarball_path)

        if not os.path.exists(go_exe):
            raise ConanInvalidConfiguration(
                f"Go binary not found at {go_exe} after extraction"
            )

        self.output.info(f"Go {go_version} installed at {go_exe}")
        return go_exe, go_root

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder

        # Ensure Go is available
        go_exe, go_root = self._ensure_go()

        # Create a minimal go.mod to enable module mode with vendor
        go_mod = os.path.join(src, "go.mod")
        if not os.path.exists(go_mod):
            with open(go_mod, "w") as f:
                f.write("module github.com/docker/machine\n\ngo 1.16\n")

        # Remove broken symlinks that break the build
        for root, dirs, files in os.walk(src):
            for name in files + dirs:
                full = os.path.join(root, name)
                if os.path.islink(full) and not os.path.exists(full):
                    os.unlink(full)

        # Set up environment for Go
        env = {
            "CGO_ENABLED": "1",
            "GOOS": "linux",
            "GOARCH": "arm64",
            "GOFLAGS": "-mod=vendor",
        }
        if go_root:
            env["GOROOT"] = go_root

        # Build the binary
        ldflags = "-s -w -X github.com/docker/machine/version.GitCommit=v0.16.2-ohos"
        out_bin = os.path.join(self.build_folder, "docker-machine")

        # Construct the command with environment variables
        env_str = " ".join(f'{k}="{v}"' for k, v in env.items())
        self.run(
            f'{env_str} "{go_exe}" build -ldflags="{ldflags}" '
            f'-o "{out_bin}" ./cmd/docker-machine',
            cwd=src,
        )

    def package(self):
        copy(self, "docker-machine", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
