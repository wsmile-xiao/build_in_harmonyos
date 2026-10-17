#!/usr/bin/env python3
"""Conan recipe — camlp-streams 5.0.1

camlp-streams provides the Stream and Genlex OCaml libraries (split out of
the OCaml standard library; they will be removed from stdlib in a future
OCaml release and maintained here).

Key OHOS adaptations (pattern proven by csexp 1.5.2 in this registry):
  - Registry-provided OCaml 4.14.1 + dune 3.17.0 toolchain (W0b CI matrix:
    OCaml is CI-able via the registry toolchain, PR6097/csexp precedent).
  - OCAMLLIB / CAML_LD_LIBRARY_PATH / PATH injected from the dependency
    package folders (ocamlc -where returns a stale path after conan cache
    relocation).
  - Defensive shebang fix for the ocaml package launcher scripts: the
    absolute interpreter path baked in at ocaml-package build time may not
    exist on a relocated cache (csexp precedent, generalized: rewrite any
    shebang whose target is missing but exists in the current ocaml bin).
  - The dune @install tree is all relative symlinks into _build/ (dangling
    after a plain copy, problematic on HMDFS) — package() copies the REAL
    artifacts from _build/default and writes META ourselves (csexp precedent).
  - R51: the upstream test suite (test/equality.exe + test/linking.exe,
    2 executables + 2 diff assertions) runs via
    `dune runtest -p camlp-streams` inside build(). The diff assertions
    reference equality.expected / issue4.expected, which are NOT shipped in
    the v5.0.1 tarball (verified against the upstream git tree), so those
    2/4 checks cannot execute; the 2 executables build and run cleanly
    (they are type-level/link-level tests with empty expected output).
    No source modification was needed.
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches


class CamlpStreamsConan(ConanFile):
    name = "camlp-streams"
    version = "5.0.1"
    description = "OCaml Stream and Genlex libraries (Camlp4/Camlp5 support)"
    license = "LGPL-2.1"
    homepage = "https://github.com/ocaml/camlp-streams"
    url = ""  # CI fills this
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    # OCaml artifacts (cma/cmxa/a/cmxs) are static by nature; shared=False is
    # the only meaningful value and does not change the build.
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def requirements(self):
        # OCaml toolchain + dune build system (registry-provided, R36).
        # Declared as requires (not tool_requires) following the csexp 1.5.2
        # precedent so consumers automatically get the toolchain.
        self.requires("ocaml/4.14.1.1.4")
        self.requires("dune/3.17.0")

    def layout(self):
        self.folders.build = "."
        self.folders.source = "."

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        pass

    def build(self):
        # No patches for this version (upstream builds unmodified); the
        # call is kept so future patches flow through the standard pipeline.
        apply_conandata_patches(self)
        ocaml_pkg = self.dependencies["ocaml/4.14.1.1.4"]
        ocaml_bin = os.path.join(ocaml_pkg.package_folder, "bin")
        ocaml_lib = os.path.join(ocaml_pkg.package_folder, "lib", "ocaml")
        dune_pkg = self.dependencies["dune/3.17.0"]
        dune_bin = os.path.join(dune_pkg.package_folder, "bin")

        # Fix OCaml toolchain launcher shebangs: scripts such as `ocaml`
        # carry an absolute interpreter path baked in at the ocaml package's
        # build time; if the conan cache was relocated, the shebang dangles
        # and the script breaks. Rewrite to the current package bin when the
        # interpreter exists there (csexp precedent, generalized).
        for fname in os.listdir(ocaml_bin):
            fpath = os.path.join(ocaml_bin, fname)
            if not os.path.isfile(fpath):
                continue
            try:
                with open(fpath, "rb") as f:
                    data = f.read()
                if not data.startswith(b"#!"):
                    continue
                nl = data.index(b"\n")
                parts = data[:nl].decode(errors="replace")[2:].strip().split()
                if not parts:
                    continue
                if os.path.exists(parts[0]):
                    continue  # shebang valid on this machine
                candidate = os.path.join(ocaml_bin, os.path.basename(parts[0]))
                if os.path.exists(candidate):
                    data = ("#!" + candidate).encode() + data[nl:]
                    with open(fpath, "wb") as f:
                        f.write(data)
                    self.output.info(f"Fixed shebang: {fname} -> {candidate}")
            except Exception as e:
                self.output.warning(f"Could not fix shebang for {fname}: {e}")

        env_prefix = (
            f"OCAMLLIB={shlex.quote(ocaml_lib)} "
            f"CAML_LD_LIBRARY_PATH={shlex.quote(os.path.join(ocaml_lib, 'stublibs'))} "
            f"PATH={shlex.quote(ocaml_bin)}:{shlex.quote(dune_bin)}:$PATH "
        )

        # No --root flag: dune 3.17 rejects `dune --root=. <cmd>` (option
        # before subcommand is not parsed as a global flag). Root detection
        # works from the build folder; the HMDFS "Unable to read
        # /storage/Users" warning is benign (verified: build still succeeds).
        self.run(f"{env_prefix} dune build -p camlp-streams", env="conanbuild")
        # R51: upstream test suite — see module docstring for the
        # missing-.expected caveat.
        self.run(f"{env_prefix} dune runtest -p camlp-streams", env="conanbuild")

    def package(self):
        # On HMDFS the dune @install tree is full of relative symlinks into
        # _build/ (e.g. camlp_streams.cma -> ../../../../default/...).
        # Copying those into the package leaves dangling links, so instead
        # copy the REAL artifacts from _build/default and generate the META
        # ourselves (content verified against the dune-generated one).
        lib_dir = os.path.join(self.package_folder, "lib", "ocaml", "camlp-streams")
        os.makedirs(lib_dir, exist_ok=True)
        build_root = os.path.join(self.source_folder, "_build", "default")
        objs = os.path.join(build_root, ".camlp_streams.objs", "byte")

        # Mandatory build artifacts (real files, verified present after
        # `dune build -p camlp-streams`).
        for fname in ("camlp_streams.cma", "camlp_streams.cmxa",
                      "camlp_streams.cmxs", "camlp_streams.a"):
            src = os.path.join(build_root, fname)
            if not os.path.isfile(src):
                raise ConanException(f"mandatory build artifact missing: {src}")
            copy(self, fname, build_root, lib_dir)

        # Module interfaces (dune stores them under .camlp_streams.objs/byte).
        for fname in ("stream.cmi", "genlex.cmi"):
            src = os.path.join(objs, fname)
            if not os.path.isfile(src):
                raise ConanException(f"interface file missing: {src}")
            copy(self, fname, objs, lib_dir)

        # Implementation sources + dune consumer metadata (dune installs both).
        for fname in ("stream.ml", "stream.mli", "genlex.ml", "genlex.mli"):
            src = os.path.join(build_root, fname)
            if os.path.isfile(src):
                copy(self, fname, build_root, lib_dir)
            else:
                self.output.warning(f"optional source missing: {fname}")
        dp = os.path.join(build_root, "camlp-streams.dune-package")
        if not os.path.isfile(dp):
            raise ConanException(f"dune-package missing: {dp}")
        copy(self, "camlp-streams.dune-package", build_root, lib_dir)

        # Sanity: every file in the package must be a real regular file,
        # never a dangling symlink (root cause of the earlier G2 failure in
        # the csexp recipe).
        for fname in os.listdir(lib_dir):
            fpath = os.path.join(lib_dir, fname)
            if os.path.islink(fpath) or not os.path.isfile(fpath):
                raise ConanException(f"package artifact is not a real file: {fpath}")
            if os.path.getsize(fpath) == 0:
                raise ConanException(f"package artifact is empty: {fpath}")

        # META: the dune-generated one has no version field; write a complete
        # one referencing the real archive names.
        meta = (
            'version = "5.0.1"\n'
            'description = "OCaml Stream and Genlex libraries"\n'
            'requires = ""\n'
            'archive(byte) = "camlp_streams.cma"\n'
            'archive(native) = "camlp_streams.cmxa"\n'
            'plugin(byte) = "camlp_streams.cma"\n'
            'plugin(native) = "camlp_streams.cmxs"\n'
        )
        with open(os.path.join(lib_dir, "META"), "w") as f:
            f.write(meta)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = ["lib/ocaml/camlp-streams"]
        self.cpp_info.includedirs = ["lib/ocaml/camlp-streams"]
        # OCaml consumers (dune/ocamlc) locate the library via OCAMLPATH.
        self.env_info.OCAMLPATH.append(
            os.path.join(self.package_folder, "lib", "ocaml"))
