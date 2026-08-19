#!/usr/bin/env python3
"""Conan recipe — seq 0.3.1

seq provides a compatibility Seq module for OCaml < 4.07.
It is a runtime dependency of yojson when using OCaml 4.14.

Key OHOS adaptations:
  - Fix OCaml shebangs (Conan build-time paths don't exist after install)
  - Set OCAMLLIB to actual installed path
  - Use --root=. for dune commands to avoid HMDFS parent dir traversal
"""
import os
import glob
import shlex

from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches


class SeqConan(ConanFile):
    name = "seq"
    version = "0.3.1"
    description = "Compatibility Seq module for OCaml"
    license = "GPL-3.0"
    homepage = "https://github.com/c-cube/seq"
    url = ""
    package_type = "library"

    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

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

        # Fix OCaml shebangs
        old_shebang = b"#!/storage/Users/currentUser/.conan2/p/b/"
        new_shebang = f"#!{ocaml_bin}/".encode()
        for fname in os.listdir(ocaml_bin):
            fpath = os.path.join(ocaml_bin, fname)
            if os.path.isfile(fpath):
                try:
                    with open(fpath, "rb") as f:
                        data = f.read()
                    if data.startswith(old_shebang):
                        data = new_shebang + data[len(old_shebang):]
                        with open(fpath, "wb") as f:
                            f.write(data)
                except Exception:
                    pass

        env_prefix = (
            f"OCAMLLIB={shlex.quote(ocaml_lib)} "
            f"CAML_LD_LIBRARY_PATH={shlex.quote(os.path.join(ocaml_lib, 'stublibs'))} "
            f"PATH={shlex.quote(ocaml_bin)}:{shlex.quote(dune_bin)}:$PATH "
        )

        self.run(f"{env_prefix} dune build -p seq", env="conanrun")

    def package(self):
        lib_dir = os.path.join(self.package_folder, "lib", "ocaml", "seq")
        os.makedirs(lib_dir, exist_ok=True)

        build_dir = os.path.join(self.source_folder, "_build", "default")

        # Copy compiled library files
        for root, _, files in os.walk(build_dir):
            for f in files:
                if (f.startswith("seq") and any(f.endswith(e) for e in
                    (".a", ".cma", ".cmxa", ".cmxs", ".cmi", ".cmx",
                     ".ml", ".mli", ".cmt", ".cmti"))):
                    copy(self, f, root, lib_dir)

        # Generate META
        meta = (
            'version = "0.3.1"\n'
            'description = "Compatibility Seq module"\n'
            'archive(byte) = "seq.cma"\n'
            'archive(native) = "seq.cmxa"\n'
            'plugin(byte) = "seq.cma"\n'
            'plugin(native) = "seq.cmxs"\n'
        )
        with open(os.path.join(lib_dir, "META"), "w") as f:
            f.write(meta)

    def package_info(self):
        self.cpp_info.libs = ["seq"]
        self.cpp_info.libdirs = ["lib/ocaml/seq"]
        self.cpp_info.includedirs = ["lib/ocaml/seq"]
        self.env_info.OCAMLPATH.append(os.path.join(self.package_folder, "lib", "ocaml"))
