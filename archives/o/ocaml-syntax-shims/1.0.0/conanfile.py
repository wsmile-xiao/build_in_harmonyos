#!/usr/bin/env python3
"""Conan recipe — ocaml-syntax-shims 1.0.0

Backport new syntax (e.g. let+) to older OCaml versions.
Builds as an executable (OCaml preprocessor) using dune.

Key OHOS adaptations:
  - dune install fails on HMDFS (traverses parent dirs); manual install instead
  - OCaml bin path injected from Conan dependency (R33)
  - dune hardcodes OCaml stdlib path at build time; fix stale path with symlink
  - OCaml bytecode scripts have shebangs pointing to build-time ocamlrun path
"""
import os
import re
import subprocess
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.errors import ConanException


class OcamlSyntaxShimsConan(ConanFile):
    name = "ocaml-syntax-shims"
    version = "1.0.0"
    description = "Backport new syntax to older OCaml versions"
    license = "MIT"
    homepage = "https://github.com/ocaml-ppx/ocaml-syntax-shims"
    url = "https://github.com/ocaml-ppx/ocaml-syntax-shims"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ocaml/4.14.1.1.2")
        self.requires("dune/3.17.0")

    def layout(self):
        self.folders.build = "."
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        pass  # dune uses its own build system, not CMake/Autotools toolchain

    def _fix_ocaml_shebangs(self, ocaml_bin):
        """Fix OCaml bytecode script shebangs that point to build-time paths.

        OCaml bytecode executables (ocaml, ocamlc.byte, etc.) have shebangs like:
          #!/path/to/build-time/ocamlrun
        When the package is installed in a different Conan cache location,
        these shebangs break. We create symlinks so the shebang paths resolve.
        """
        for fname in os.listdir(ocaml_bin):
            fpath = os.path.join(ocaml_bin, fname)
            if not os.path.isfile(fpath):
                continue
            with open(fpath, "rb") as f:
                magic = f.read(2)
            if magic != b"#!":
                continue
            # Read the shebang line
            with open(fpath, "r", errors="ignore") as f:
                shebang = f.readline().strip()
            # Extract the interpreter path (after #! and before any arguments)
            interp = shebang[2:].split()[0] if shebang.startswith("#!") else None
            if not interp or not os.path.isabs(interp):
                continue
            # If the interpreter already exists, no fix needed
            if os.path.isfile(interp):
                continue
            # Find the actual interpreter in the current OCaml bin
            interp_name = os.path.basename(interp)
            actual_interp = os.path.join(ocaml_bin, interp_name)
            if not os.path.isfile(actual_interp):
                continue
            # Create symlink from shebang path to actual interpreter
            interp_dir = os.path.dirname(interp)
            if not os.path.isdir(interp_dir):
                os.makedirs(interp_dir, exist_ok=True)
            if not os.path.exists(interp):
                os.symlink(actual_interp, interp)

    def _fix_stale_ocaml_lib_path(self, dune_bin, ocaml_bin, ocaml_lib):
        """Probe dune to detect stale OCaml lib path, then create symlink fix.

        dune hardcodes the OCaml stdlib directory from its build time.
        When the Conan cache differs, dune fails with:
          Error: <stale_path>/Makefile.config: No such file or directory
        """
        if not os.path.isdir(ocaml_lib):
            return
        env = os.environ.copy()
        env["PATH"] = f"{dune_bin}:{ocaml_bin}:{env.get('PATH', '')}"
        dune_exe = os.path.join(dune_bin, "dune")
        if not os.path.isfile(dune_exe):
            return
        result = subprocess.run(
            [dune_exe, "build", "-p", "ocaml-syntax-shims"],
            capture_output=True, text=True, env=env, cwd=self.build_folder
        )
        if result.returncode == 0:
            return
        # Parse stale OCaml path from dune's output
        output = result.stderr + result.stdout
        m = re.search(r"(/[^\s:]*ocaml[^\s:]*Makefile\.config)", output)
        if not m:
            return
        stale_path = m.group(1)
        stale_dir = os.path.dirname(stale_path)
        # Create symlink: stale_dir -> actual ocaml_lib
        if os.path.islink(stale_dir):
            os.remove(stale_dir)
        elif os.path.isdir(stale_dir) and not os.listdir(stale_dir):
            shutil.rmtree(stale_dir)
        if not os.path.exists(stale_dir):
            os.makedirs(os.path.dirname(stale_dir), exist_ok=True)
            os.symlink(ocaml_lib, stale_dir)

    def build(self):
        apply_conandata_patches(self)

        # Find OCaml binaries from dependency package (R33: no bare shell vars)
        ocaml_pkg = self.dependencies["ocaml/4.14.1.1.2"]
        ocaml_bin = os.path.join(ocaml_pkg.package_folder, "bin")
        ocaml_lib = os.path.join(ocaml_pkg.package_folder, "lib", "ocaml")

        # Find dune binary from dependency package
        dune_pkg = self.dependencies["dune/3.17.0"]
        dune_bin = os.path.join(dune_pkg.package_folder, "bin")

        # Fix 1: OCaml bytecode scripts have shebangs pointing to build-time
        # ocamlrun paths that may not exist in this Conan cache location
        self._fix_ocaml_shebangs(ocaml_bin)

        # Fix 2: dune hardcodes OCaml stdlib path from its build time
        self._fix_stale_ocaml_lib_path(dune_bin, ocaml_bin, ocaml_lib)

        # Clean any dune _build cache from the probe
        dune_cache = os.path.join(self.build_folder, "_build")
        if os.path.isdir(dune_cache):
            shutil.rmtree(dune_cache, ignore_errors=True)

        env_vars = f'PATH="{dune_bin}:{ocaml_bin}:$PATH"'
        self.run(f'{env_vars} dune build -p ocaml-syntax-shims', env="conanrun")

    def package(self):
        # dune install fails on HMDFS; manual install from _build/install/default
        copy(self, "ocaml-syntax-shims",
             src=os.path.join(self.build_folder, "_build", "install", "default", "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        # Make binary executable
        bin_path = os.path.join(self.package_folder, "bin", "ocaml-syntax-shims")
        if os.path.exists(bin_path):
            os.chmod(bin_path, 0o755)

        # Copy library metadata
        copy(self, "*",
             src=os.path.join(self.build_folder, "_build", "install", "default", "lib", "ocaml-syntax-shims"),
             dst=os.path.join(self.package_folder, "lib", "ocaml-syntax-shims"))

        # Copy documentation
        copy(self, "*",
             src=os.path.join(self.build_folder, "_build", "install", "default", "doc", "ocaml-syntax-shims"),
             dst=os.path.join(self.package_folder, "doc", "ocaml-syntax-shims"))

        # Fallback: if _build/install symlinks broken, copy from build dir directly
        if not os.path.exists(bin_path):
            exe = os.path.join(self.build_folder, "_build", "default", "src", "pp.exe")
            if os.path.exists(exe):
                os.makedirs(os.path.dirname(bin_path), exist_ok=True)
                copy(self, "pp.exe",
                     src=os.path.join(self.build_folder, "_build", "default", "src"),
                     dst=os.path.join(self.package_folder, "bin"))
                # Rename pp.exe -> ocaml-syntax-shims
                src = os.path.join(self.package_folder, "bin", "pp.exe")
                if os.path.exists(src) and not os.path.exists(bin_path):
                    os.rename(src, bin_path)
                if os.path.exists(bin_path):
                    os.chmod(bin_path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # This is an application, not a library; clear libs
        self.cpp_info.libs = []
