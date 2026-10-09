#!/usr/bin/env python3
"""Conan recipe — Menhir 20260209

Menhir is an LR(1) parser generator for OCaml, distributed by the Menhir
project (Inria).  It is built with Dune and is self-bootstrapping:

  * driver/stage1 is generated with ocamlyacc and compiled into the stage 1
    executable;
  * driver/stage2 binds the stage 1 executable as "menhir" (see
    driver/stage2/dune) and generates the stage 2 parser and the final
    executable.

External tooling needed: ocaml (ocamlc/ocamlopt/ocamllex/ocamlyacc) and dune,
both declared as Conan tool_requires from the OHOS registry — the OHOS system
image ships no OCaml.

OHOS notes:
  * The packaged ocamlc/ocamlopt keep a build-time absolute stdlib path that
    does not survive Conan cache relocation; OCAMLLIB is therefore derived
    from the tool package location and exported explicitly (same workaround as
    the merged ocaml/dune and pdfsandwich recipes).
  * Both tool packages expose bin/ through the conanbuild environment; PATH is
    additionally patched here for robustness.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class MenhirConan(ConanFile):
    name = "menhir"
    version = "20260209"
    description = ("An LR(1) parser generator for OCaml "
                   "(menhir binary + menhirLib/Sdk/CST/GLR libraries)")
    license = "GPL-2.0-only"
    homepage = "https://gitlab.inria.fr/fpottier/menhir"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Compiler toolchain and build system come from the registry;
        # the OHOS system image provides no OCaml.
        self.tool_requires("ocaml/4.14.1.1.4")
        self.tool_requires("dune/3.17.0")

    def layout(self):
        self.folders.build = "."
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _toolchain_env(self):
        ocaml_dep = self.dependencies.build["ocaml"]
        dune_dep = self.dependencies.build["dune"]
        ocaml_bin = os.path.join(ocaml_dep.package_folder, "bin")
        ocaml_lib = os.path.join(ocaml_dep.package_folder, "lib", "ocaml")
        dune_bin = os.path.join(dune_dep.package_folder, "bin")
        os.environ["PATH"] = os.pathsep.join(
            [dune_bin, ocaml_bin, os.environ.get("PATH", "")])
        os.environ["OCAMLLIB"] = ocaml_lib
        self.output.info("OCAMLLIB=%s" % ocaml_lib)
        self.output.info("tool bins prepended to PATH: %s %s" % (dune_bin, ocaml_bin))

    def build(self):
        self._toolchain_env()
        apply_conandata_patches(self)
        self.run(
            "dune build -p menhirLib,menhirSdk,menhirCST,menhirGLR,menhir "
            "--profile release @install",
            env="conanbuild",
        )

    def package(self):
        # Dune's install tree uses symlinks into _build/default; conan's copy
        # would reproduce them verbatim (broken in the package, as observed
        # for cairo2).  Copy the real files instead (symlinks=False follows
        # links while the build tree still exists).
        install_tree = os.path.join(self.build_folder, "_build", "install", "default")
        shutil.copytree(install_tree, self.package_folder,
                        symlinks=False, dirs_exist_ok=True)

    def package_info(self):
        # menhir is a CLI tool.  The OCaml libraries (menhirLib, menhirSdk,
        # menhirCST, menhirGLR) are installed under lib/ and are consumed by
        # OCaml builds through their filesystem path, not through Conan
        # cpp_info link flags.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
