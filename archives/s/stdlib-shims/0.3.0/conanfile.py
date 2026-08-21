#!/usr/bin/env python3
"""Conan recipe — stdlib-shims 0.3.0 (OCaml compatibility shims)

stdlib-shims backports the Stdlib module to older OCaml compilers (< 4.08).

OHOS adaptations:
  - OCaml Conan package's standard_library path points to build dir (p/b/)
    instead of package dir (p/); fix via symlink before dune invocation
  - dune install fails on HMDFS; copy from _build/install/default/ instead
  - Source and build in same directory (dune builds relative to workspace root)
  - Fix bytecode scripts' shebang (ocamlrun path baked at build time differs
    from install-time cache location; patch with actual ocamlrun path)
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class StdlibshimsConan(ConanFile):
    name = "stdlib-shims"
    version = "0.3.0"
    description = "Backport some of the new stdlib features to older compiler (Stdlib module)"
    license = "typeof OCaml system"
    homepage = "https://github.com/ocaml/stdlib-shims"
    url = ""

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # Source and build in the same directory — dune needs sources alongside _build/
    folders = {"source": ".", "build": "."}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ocaml/4.14.1.1.2")

    def build_requirements(self):
        self.tool_requires("dune/3.17.0")

    def layout(self):
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        ocaml_pkg = self.dependencies["ocaml"].package_folder
        ocaml_bin = os.path.join(ocaml_pkg, "bin")
        ocaml_lib = os.path.join(ocaml_pkg, "lib", "ocaml")

        from conan.tools.env import Environment
        env = Environment()
        env.prepend_path("PATH", ocaml_bin)
        env.append_path("CAML_LD_LIBRARY_PATH",
                         os.path.join(ocaml_pkg, "lib", "ocaml", "stublibs"))
        env.define("OCAMLLIB", ocaml_lib)
        env.define("OCAMLFIND_LDCONFIG", "ignore")
        tmpdir = os.environ.get("TMPDIR", os.path.expanduser("~/tmp"))
        env.define("TMPDIR", tmpdir)
        env.vars(self).save_script("stdlib_shims_ocaml_env")

    def build(self):
        apply_conandata_patches(self)
        # Fix OCaml standard_library path
        ocaml_pkg = self.dependencies["ocaml"].package_folder
        ocaml_bin = os.path.join(ocaml_pkg, "bin")
        ocamlrun = os.path.join(ocaml_bin, "ocamlrun")

        # Fix bytecode scripts' shebang: ocaml package hardcodes the
        # build-time ocamlrun path in #! lines (e.g. #!/.conan2/p/ocaml.../bin/ocamlrun).
        # On CI the cache dir differs (.cache/conan2/ vs .conan2/), so execve fails.
        # Patch all bytecode scripts to use the actual ocamlrun location.
        if os.path.isfile(ocamlrun):
            for fname in os.listdir(ocaml_bin):
                fpath = os.path.join(ocaml_bin, fname)
                if not os.path.isfile(fpath):
                    continue
                try:
                    with open(fpath, "rb") as f:
                        header = f.readline()
                    if header.startswith(b"#!") and b"ocamlrun" in header:
                        old_shebang = header.decode("ascii", errors="replace").strip()
                        new_shebang = "#!" + ocamlrun
                        with open(fpath, "r+b") as f:
                            content = f.read()
                        content = content.replace(
                            old_shebang.encode("ascii", errors="replace"),
                            new_shebang.encode("ascii"), 1)
                        with open(fpath, "wb") as f:
                            f.write(content)
                except (OSError, PermissionError):
                    pass

        result = subprocess.run(
            [os.path.join(ocaml_bin, "ocamlc.opt"), "-config"],
            capture_output=True, text=True, env={
                **os.environ, "PATH": ocaml_bin + os.pathsep + os.environ.get("PATH", "")
            })
        stdlib_path = None
        for line in result.stdout.splitlines():
            if line.startswith("standard_library:"):
                stdlib_path = line.split(":", 1)[1].strip()
                break
        if stdlib_path and os.path.isdir(os.path.dirname(stdlib_path)):
            if not os.path.exists(os.path.join(stdlib_path, "Makefile.config")):
                actual_lib = os.path.join(ocaml_pkg, "lib", "ocaml")
                if os.path.isdir(actual_lib) and not os.path.exists(stdlib_path):
                    os.makedirs(os.path.dirname(stdlib_path), exist_ok=True)
                    os.symlink(actual_lib, stdlib_path)
        # dune build @install populates _build/install/default/
        self.run("dune build @install --root .", env=["conanbuild", "stdlib_shims_ocaml_env"])
        # Run upstream test suite
        self.run("dune runtest --root .", env=["conanbuild", "stdlib_shims_ocaml_env"])

    def package(self):
        # Copy from _build/install/default/ (dune build @install output)
        # Dereference symlinks created by dune
        src = os.path.join(self.build_folder, "_build", "install", "default")
        for subdir in ["lib/stdlib-shims", "doc/stdlib-shims"]:
            src_dir = os.path.join(src, subdir)
            dst_dir = os.path.join(self.package_folder, subdir)
            os.makedirs(dst_dir, exist_ok=True)
            if os.path.isdir(src_dir):
                for f in os.listdir(src_dir):
                    src_file = os.path.join(src_dir, f)
                    dst_file = os.path.join(dst_dir, f)
                    if os.path.islink(src_file):
                        target = os.path.realpath(src_file)
                        if os.path.isfile(target):
                            shutil.copy2(target, dst_file)
                    elif os.path.isfile(src_file):
                        shutil.copy2(src_file, dst_file)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib/stdlib-shims"]
        self.cpp_info.includedirs = []
        self.env_info.CAML_LD_LIBRARY_PATH.append(
            os.path.join(self.package_folder, "lib", "stdlib-shims"))
