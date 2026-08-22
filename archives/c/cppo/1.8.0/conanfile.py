#!/usr/bin/env python3
"""Conan recipe — cppo 1.8.0

cppo is an OCaml equivalent of the C preprocessor. It is a build-time
dependency of yojson.

Key OHOS adaptations:
  - Fix OCaml shebangs (Conan build-time paths don't exist after install)
  - Set OCAMLLIB to actual installed path
  - Replace native ocaml binary with ocamlrun wrapper (OHOS PT_INTERP incompatible)
  - Use --root=. for dune commands to avoid HMDFS parent dir traversal
"""
import os
import glob
import shlex

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches


class CppoConan(ConanFile):
    name = "cppo"
    version = "1.8.0"
    description = "OCaml C-style preprocessor"
    license = "BSD-3-Clause"
    homepage = "https://github.com/ocaml-community/cppo"
    url = ""
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
        pass

    def build(self):
        apply_conandata_patches(self)
        ocaml_pkg = self.dependencies["ocaml/4.14.1.1.2"]
        ocaml_bin = os.path.join(ocaml_pkg.package_folder, "bin")
        ocaml_lib = os.path.join(ocaml_pkg.package_folder, "lib", "ocaml")
        dune_pkg = self.dependencies["dune/3.17.0"]
        dune_bin = os.path.join(dune_pkg.package_folder, "bin")

        # Fix OCaml bytecode shebangs.
        # Match any conan cache base path (e.g. .conan2 or .cache/conan2).
        for fname in os.listdir(ocaml_bin):
            fpath = os.path.join(ocaml_bin, fname)
            if os.path.isfile(fpath):
                try:
                    with open(fpath, "rb") as f:
                        data = f.read()
                    if data.startswith(b"#!") and b"/p/b/" in data[:200]:
                        nl = data.index(b"\n")
                        old_line = data[:nl].decode(errors="replace")
                        old_bin = old_line.rstrip().split("/")[-1]
                        new_shebang = f"#!{ocaml_bin}/{old_bin}".encode()
                        data = new_shebang + data[nl:]
                        with open(fpath, "wb") as f:
                            f.write(data)
                        self.output.info(f"Fixed shebang: {fname} -> {new_shebang.decode()}")
                except Exception as e:
                    self.output.warning(f"Could not fix shebang for {fname}: {e}")
        # Verify ocaml works after shebang fix
        ocaml_exe = os.path.join(ocaml_bin, "ocaml")
        ocamlrun = os.path.join(ocaml_bin, "ocamlrun")
        rc = self.run(f'"{ocaml_exe}" -version', env="conanrun", ignore_errors=True)
        if rc != 0:
            self.output.warning("ocaml still not executable after shebang fix, trying wrapper")
            # Fallback for native ELF binary with broken PT_INTERP
            try:
                with open(ocaml_exe, "rb") as f:
                    magic = f.read(4)
                if magic == b"\x7fELF" and os.path.isfile(ocamlrun):
                    ocaml_toplevel = os.path.join(ocaml_lib, "ocaml")
                    if os.path.isfile(ocaml_toplevel):
                        self.output.info("Replacing native ocaml with ocamlrun wrapper")
                        os.remove(ocaml_exe)
                        with open(ocaml_exe, "w") as f:
                            f.write(f"#!/bin/sh\nexec \"{ocamlrun}\" \"{ocaml_toplevel}\" \"$@\"\n")
                        os.chmod(ocaml_exe, 0o755)
                    else:
                        self.output.warning("No bytecode toplevel found, ocaml may not work")
            except Exception as e:
                self.output.warning(f"Wrapper fallback failed: {e}")

        env_prefix = (
            f"OCAMLLIB={shlex.quote(ocaml_lib)} "
            f"CAML_LD_LIBRARY_PATH={shlex.quote(os.path.join(ocaml_lib, 'stublibs'))} "
            f"PATH={shlex.quote(ocaml_bin)}:{shlex.quote(dune_bin)}:$PATH "
        )

        self.run(f"{env_prefix} dune build -p cppo", env="conanrun")

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        lib_dir = os.path.join(self.package_folder, "lib", "ocaml", "cppo")
        os.makedirs(bin_dir, exist_ok=True)
        os.makedirs(lib_dir, exist_ok=True)

        # Copy cppo binary from _build
        build_dir = os.path.join(self.source_folder, "_build", "default")
        for root, _, files in os.walk(build_dir):
            for f in files:
                if f == "cppo.exe" or (f.startswith("cppo") and f.endswith(".exe")):
                    src = os.path.join(root, f)
                    copy(self, f, os.path.dirname(src), bin_dir)
                    dst = os.path.join(bin_dir, f.replace(".exe", ""))
                    src_path = os.path.join(bin_dir, f)
                    if src_path != dst and not os.path.exists(dst):
                        try:
                            os.rename(src_path, dst)
                        except OSError:
                            pass

        # Copy library files
        for root, _, files in os.walk(build_dir):
            for f in files:
                if f.startswith("cppo") and any(f.endswith(e) for e in
                    (".cma", ".cmxa", ".a", ".cmi", ".cmx", ".cmxs",
                     ".ml", ".mli", ".cmt", ".cmti")):
                    copy(self, f, root, lib_dir)

        # Generate META
        meta = 'version = "1.8.0"\ndescription = "C preprocessor for OCaml"\narchive(byte) = "cppo.cma"\narchive(native) = "cppo.cmxa"\n'
        with open(os.path.join(lib_dir, "META"), "w") as f:
            f.write(meta)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib/ocaml/cppo"]
        self.cpp_info.includedirs = ["lib/ocaml/cppo"]
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
        self.env_info.OCAMLPATH.append(os.path.join(self.package_folder, "lib", "ocaml"))
