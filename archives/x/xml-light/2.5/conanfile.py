#!/usr/bin/env python3
"""Conan recipe — xml-light 2.5

Xml-Light is a minimal XML parser & printer for OCaml (pure OCaml, no C
library), with DTD parsing, checking and proving. Upstream 2.5 builds with
dune (upstream opam build: `dune build -p xml-light`); the library stanza
has `wrapped false`, so the public modules keep their top-level names
(Xml, Dtd, XmlParser, plus the ocamllex/ocamlyacc generated internals).

Toolchain: registry-provided ocaml/4.14.1.1.4 + dune/3.17.0 (W0b CI
matrix: OCaml is CI-able via the registry toolchain; csexp /
camlp-streams 5.0.1 / menhir precedents).

Key OHOS adaptations (pattern proven by camlp-streams 5.0.1 in this
registry):
  - OCAMLLIB / CAML_LD_LIBRARY_PATH / PATH injected from the dependency
    package folders (ocamlc -where returns a stale path after conan cache
    relocation).
  - Defensive shebang fix for the ocaml package launcher scripts: the
    absolute interpreter path baked in at ocaml-package build time may not
    exist on a relocated cache; rewrite any shebang whose target is
    missing but exists in the current ocaml bin.
  - The dune @install tree is all relative symlinks into _build/ (dangling
    after a plain copy, problematic on HMDFS) — package() copies the REAL
    files (shutil.copytree symlinks=False) into lib/ocaml/xml-light
    (findlib-style layout, camlp-streams/xmlm precedent).
  - Conan's unzip() does not recognise the upstream `.tbz` extension, so
    source() downloads with an explicit `filename="xml-light-2.5.tar.bz2"`
    (xmlm 1.4.0 precedent). The tarball is the official release asset
    pinned by the opam repository (sha256 verified).
  - R51: the upstream test suite (tests/dune registers two `runtest`
    actions: test.exe fed tests/simple.xml via pipe-stdout, and
    check_dtd.exe validating tests/topic.xml against tests/topic-like.dtd)
    runs via `dune runtest -p xml-light` inside build(). No source
    modification was needed.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, export_conandata_patches, apply_conandata_patches


class XmlLightConan(ConanFile):
    name = "xml-light"
    version = "2.5"
    description = "Minimal XML parser & printer for OCaml (with DTD support)"
    license = "LGPL-2.1-or-later WITH OCaml-LGPL-linking-exception"
    homepage = "https://github.com/ncannasse/xml-light"
    url = ""  # CI fills this
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    # OCaml artifacts (cma/cmxa/a/cmxs) are static by nature; shared=False is
    # the only meaningful value and does not change the build.
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def requirements(self):
        # OCaml toolchain + dune build system (registry-provided, R36).
        # Declared as requires (not tool_requires) following the
        # camlp-streams 5.0.1 precedent so OCaml consumers automatically
        # get the toolchain.
        self.requires("ocaml/4.14.1.1.4")
        self.requires("dune/3.17.0")

    def layout(self):
        self.folders.build = "."
        self.folders.source = "."

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # Official release tarball (.tbz = bzip2). filename= is required
        # because this Conan version's unzip() does not map the `.tbz`
        # extension to tar.bz2 (xmlm 1.4.0 precedent).
        get(self, filename="xml-light-2.5.tar.bz2", strip_root=True,
            **self.conan_data["sources"][self.version])

    def generate(self):
        pass  # no autotools/cmake; OCaml's own toolchain is used

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
        # interpreter exists there (camlp-streams precedent, generalized).
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
        # /storage/Users" warning is benign (camlp-streams precedent).
        self.run(f"{env_prefix} dune build -p xml-light @install",
                 env="conanbuild")
        # R51: upstream test suite — see module docstring.
        self.run(f"{env_prefix} dune runtest -p xml-light", env="conanbuild")

    def package(self):
        # The dune @install tree (_build/install/default/lib/xml-light) is
        # all relative symlinks into _build/default; copying those verbatim
        # leaves dangling links (HMDFS-hostile). Copy the REAL files
        # (symlinks=False follows the links while _build still exists —
        # menhir 20260209 precedent) into the findlib-style layout.
        install_lib = os.path.join(self.build_folder, "_build", "install",
                                   "default", "lib", "xml-light")
        if not os.path.isdir(install_lib):
            raise ConanException(f"dune install tree missing: {install_lib}")
        lib_dir = os.path.join(self.package_folder, "lib", "ocaml", "xml-light")
        shutil.copytree(install_lib, lib_dir, symlinks=False, dirs_exist_ok=True)

        # Mandatory build artifacts (real files, verified present after
        # `dune build -p xml-light @install`).
        for fname in ("xml_light.cma", "xml_light.cmxa", "xml_light.cmxs",
                      "xml_light.a", "xml.cmi", "dtd.cmi", "xmlParser.cmi",
                      "META"):
            fpath = os.path.join(lib_dir, fname)
            if not os.path.isfile(fpath):
                raise ConanException(f"mandatory artifact missing: {fpath}")

        # Sanity: every file in the package must be a real regular file,
        # never a dangling symlink / empty file (HMDFS symptom guard,
        # camlp-streams precedent).
        for root, _, files in os.walk(lib_dir):
            for fname in files:
                fpath = os.path.join(root, fname)
                if os.path.islink(fpath) or not os.path.isfile(fpath):
                    raise ConanException(
                        f"package artifact is not a real file: {fpath}")
                if os.path.getsize(fpath) == 0:
                    raise ConanException(f"package artifact is empty: {fpath}")

    def package_info(self):
        # OCaml artifacts are consumed via OCAMLPATH, not via a C toolchain
        # (xmlm 1.4.0 precedent: Conan 2 buildenv_info/runenv_info are the
        # supported way to export the environment).
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = ["lib/ocaml/xml-light"]
        self.cpp_info.includedirs = ["lib/ocaml/xml-light"]
        self.buildenv_info.append_path(
            "OCAMLPATH", os.path.join(self.package_folder, "lib", "ocaml"))
