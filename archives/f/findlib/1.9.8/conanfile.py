#!/usr/bin/env python3
"""Conan recipe — findlib (ocamlfind) 1.9.8

findlib is OCaml's library manager: it ships `ocamlfind`, which resolves
package META files and drives the OCaml compilers/linkers.

Build chain: configure (custom autoconf-style) -> make all -> make opt -> make install

OHOS platform adaptations (all guarded in patches/0001-configure.patch):
  - OCaml bytecode tools (ocaml toplevel, the built extract_args helper) are
    plain scripts whose shebang points at ocamlrun.  OHOS hmmac refuses to
    exec shebang scripts and the embedded ocamlrun path is stale, so they are
    invoked through an explicit ocamlrun ($OCAMLRUN).  No-op elsewhere.
  - Bytecode linking must locate the OCaml shared stubs (dllunix.so, ...);
    the stublibs dir is published as CAML_LD_LIBRARY_PATH in Makefile.config.
  - OHOS has no GNU install(1); configure falls back to mkdir -p / cp.

The recipe requires ocaml/4.14.1.1.4 as a tool_requires because the CI clean
environment has no system OCaml toolchain (see SKILL §0.3 CI capability matrix).
"""
import os
import shlex

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class FindlibConan(ConanFile):
    name = "findlib"
    version = "1.9.8"
    description = "OCaml library manager (ocamlfind): resolves packages and drives the OCaml compilers"
    license = "MIT"
    homepage = "http://projects.camlcity.org/projects/findlib.html"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # findlib is a build/tool package: the OCaml toolchain is needed at
        # build time only.  It must be a tool_requires so the CI environment
        # (no system OCaml) can build it.
        self.tool_requires("ocaml/4.14.1.1.4")

    def layout(self):
        self.folders.build = "."
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        pass  # findlib ships a custom configure script, not autotools

    def build(self):
        apply_conandata_patches(self)

        ocaml_pkg = self.dependencies.build["ocaml"].package_folder
        ocaml_bin = os.path.join(ocaml_pkg, "bin")
        ocaml_stdlib = os.path.join(ocaml_pkg, "lib", "ocaml")
        ocamlrun = os.path.join(ocaml_bin, "ocamlrun")
        # OCAMLRUN activates the OHOS guards added by patches/0001-configure.patch:
        # bytecode tools are then launched as `"$OCAMLRUN" tool ...`.
        env = (f"OCAMLRUN={shlex.quote(ocamlrun)} "
               f"OCAMLLIB={shlex.quote(ocaml_stdlib)} "
               f"CAML_LD_LIBRARY_PATH={shlex.quote(os.path.join(ocaml_stdlib, 'stublibs'))} "
               f"PATH={shlex.quote(ocaml_bin)}:$PATH")

        # OHOS hmmac refuses to exec shebang scripts, so configure is invoked
        # through an explicit interpreter.  The OCaml tools are found via PATH.
        self.run(
            f"{env} /bin/sh ./configure "
            f"-bindir {shlex.quote(os.path.join(self.package_folder, 'bin'))} "
            f"-mandir {shlex.quote(os.path.join(self.package_folder, 'share', 'man'))} "
            f"-sitelib {shlex.quote(os.path.join(self.package_folder, 'lib', 'ocaml'))} "
            f"-config {shlex.quote(os.path.join(self.package_folder, 'etc', 'ocamlfind.conf'))} "
            f"-no-custom -no-camlp4",
            env="conanrun",
        )
        self.run(f"{env} make -j1 all", env="conanrun")
        self.run(f"{env} make -j1 opt", env="conanrun")

    def package(self):
        # DESTDIR staging: configure used self.package_folder as prefix, so
        # `make install DESTDIR=<dest>` lands files under <dest>/<prefix>/.
        # install() prefers ocamlfind_opt (native ELF) over the bytecode script.
        dest = os.path.join(self.build_folder, "dest_install")
        self.run(f'make install DESTDIR="{dest}"', env="conanrun")
        src_base = os.path.join(dest, self.package_folder.lstrip("/"))
        if not os.path.isdir(src_base):
            src_base = dest
        copy(self, "*", src_base, self.package_folder)
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # findlib ships two kinds of artifacts:
        #   - the `ocamlfind` CLI in bin/
        #   - the findlib OCaml library (findlib.cma/.cmxa/.cmxs) under lib/ocaml/findlib/
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib/ocaml/findlib"]
        self.cpp_info.includedirs = ["lib/ocaml/findlib"]
        # Downstreams that compile OCaml code need the findlib package dir on
        # OCAMLPATH; those running bytecode need the OCaml shared stubs.
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
        self.env_info.OCAMLPATH.append(os.path.join(self.package_folder, "lib", "ocaml"))
