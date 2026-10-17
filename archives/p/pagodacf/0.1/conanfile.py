#!/usr/bin/env python3
"""Conan recipe — pagodacf 0.1 (OCaml NAE Core Foundation, Makefile)

pagodacf is the OCaml NAE Core Foundation (Cf) library by James H. Woodyatt,
originally distributed as cf-0.10.tar.gz and repackaged by Debian as
pagodacf_0.10.orig.tar.gz. The recipe name "pagodacf" follows the Debian
source package; the recipe version "0.1" is the cf library version line
announced on the Caml mailing list.

The upstream Makefile drives an ocamlfind/ocamlmklib build. Key OHOS
adaptations:
  - toolchain provided by the ocaml/4.14.1 requirement (ocamlc, ocamlopt,
    ocamlmklib, ocamldep). The ocaml recipe ships the compiler but NOT the
    findlib front-end (`ocamlfind`), so patch 0002 rewrites the Makefile to
    call ocamlc/ocamlopt/ocamlmktop/ocamlldoc directly with an explicit
    `-I +unix` include (the exact substitution findlib's `-package unix`
    performs), and replaces `ocamlfind install/remove cf` with a manual
    `cp`/`rm` into `$(DESTDIR)/cf`.
  - TMPDIR exported for any auxiliary tools that write to /tmp
  - `make -j1` (parallel ocamlc invocations are not race-free here)
  - install via `make install DESTDIR=<stage>` into a staged cf/ tree, then
    copy to package
  - upstream self-tests (t/t_cf.ml, TAP style) run via `make test`
"""
import os
import re

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class PagodacfConan(ConanFile):
    name = "pagodacf"
    version = "0.1"
    description = "OCaml NAE Core Foundation (Cf) library — functional data structures, parsers, sockets"
    license = "BSD-2-Clause"
    homepage = "https://tracker.debian.org/pkg/pagodacf"
    url = ""

    settings = "os", "compiler", "build_type", "arch"
    package_type = "library"
    # ocamlmklib builds static OCaml archives (cf.cma bytecode + cf.cmxa/cf.a
    # native); there is no shared build mode. Conan 2 requires a `shared`
    # option for `package_type="library"`, so declare it static-only.
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ocaml/4.14.1")

    def layout(self):
        self.folders.build = "."
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # The ocaml/4.14.1 recipe installs its compiler binaries
        # (ocamlc/ocamlopt/ocamlmklib/ocamldep/ocamllex/ocamlyacc/ocamlrun)
        # into `<package>/bin/` but does NOT inject that directory into
        # PATH via its own `package_info()` (no env_info.PATH, no
        # cpp_info.bindirs). As a pure OCaml downstream that drives the
        # Makefile with bare `ocamlc ...` (patch 0002 removed the
        # `ocamlfind` front-end), we must prepend ocaml's bin to PATH
        # ourselves so `make` can locate the toolchain. This mirrors the
        # pattern ocaml's own test_package uses:
        #   bin_dir = os.path.join(self.dependencies["ocaml"].package_folder, "bin")
        # Conan 2's `self.dependencies[...]` is available from generate() onward.
        # Conan 2 self.run(env=...) takes a **list of env-file names**, not a
        # dict — passing a dict raises AssertionError "env argument should be a
        # list". So we materialise an env file via Environment() and reference
        # it by name ("pagodacf_ocaml_env") in every self.run() call.
        ocaml_pkg = self.dependencies["ocaml"].package_folder
        ocaml_bin = os.path.join(ocaml_pkg, "bin")
        env = Environment()
        env.prepend_path("PATH", ocaml_bin)
        # OCaml's bytecode loader needs CAML_LD_LIBRARY_PATH to find
        # dllcf.so at runtime (t.cf / t_pagodacf execution).
        env.append_path("CAML_LD_LIBRARY_PATH", ocaml_bin)
        # The upstream Makefile drives the C compiler via `ocamlc -ccopt <flags>`,
        # and cf_*_p.c includes <caml/alloc.h> from OCaml's C runtime. ocaml/4.14.1's
        # package_info() declares `cpp_info.includedirs = ["lib/ocaml/caml"]`, but that
        # only feeds Conan's C/C++ generators (CMake/Autotools) — a bare `make` driving
        # `ocamlc -ccopt -MM` gets no `-I` injection, so clang cannot find caml/alloc.h
        # (真机日志: `fatal error: 'caml/alloc.h' file not found`).
        #
        # clang/GCC both read `C_INCLUDE_PATH`/`CPLUS_INCLUDE_PATH` as additional
        # header search roots. The OCaml 4.14.1 install layout is:
        #   <prefix>/lib/ocaml/caml/alloc.h   (caml/ is a leaf dir, no nested caml/)
        # so `#include <caml/alloc.h>` needs the **parent** `<prefix>/lib/ocaml` as
        # the search root (resolves to <prefix>/lib/ocaml/caml/alloc.h). The previous
        # attempt pointed at `.../lib/ocaml/caml` itself, where clang looks for
        # `caml/alloc.h` and finds no `caml/` subdir — hence the same failure.
        #
        # We add BOTH levels: the parent (for <caml/alloc.h>) and the caml dir itself
        # (for any direct `#include "alloc.h"` style reference in upstream headers).
        ocaml_lib = os.path.join(ocaml_pkg, "lib", "ocaml")
        caml_dir = os.path.join(ocaml_lib, "caml")
        env.append_path("C_INCLUDE_PATH", ocaml_lib)
        env.append_path("C_INCLUDE_PATH", caml_dir)
        env.append_path("CPLUS_INCLUDE_PATH", ocaml_lib)
        env.append_path("CPLUS_INCLUDE_PATH", caml_dir)
        # OCaml 4.14's `ocamlc` locates the standard library directory by:
        #   1. OCAMLLIB env var
        #   2. CAMLLIB env var (legacy)
        #   3. standard_library_default compiled into the binary (= configure --prefix + "/lib/ocaml")
        # The ocaml/4.14.1 recipe's package_info() does NOT set env_info.OCAMLLIB,
        # so we must set it ourselves to point at <ocaml_pkg>/lib/ocaml — the
        # directory that actually contains stdlib.cmi. Without this, `ocamlc`
        # falls back to the compiled-in prefix (which is the Conan cache path
        # and *should* match), but if that lookup fails for any reason (e.g.
        # the binary was built in a different Conan cache layout, or the
        # compiled-in path is relative and CWD differs), the compiler aborts
        # with `File "command line", line 1: Error: Unbound module Stdlib`
        # because it cannot open Stdlib's .cmi to start type-checking.
        # Setting OCAMLLIB explicitly is the OCaml-recommended way to relocate
        # a compiler installation, and is the same mechanism opam switches use.
        env.define("OCAMLLIB", ocaml_lib)
        # Some ocamlmklib variants invoke ldconfig; ignore on cross hosts.
        env.define("OCAMLFIND_LDCONFIG", "ignore")
        env.vars(self).save_script("pagodacf_ocaml_env")

    def build(self):
        apply_conandata_patches(self)
        # The upstream tarball ships a pre-generated `.depend` whose
        # `cf_*_p.o` prerequisites hard-code absolute OCaml runtime
        # header paths (e.g. /usr/local/lib/ocaml/caml/alloc.h) that do
        # not exist on OHOS.  We delete the stale file and let the
        # Makefile's `$(DEPEND_FILE) ::` rule regenerate it from the
        # host's real OCaml prefix via `ocamlc -ccopt -MM`.
        stale_depend = os.path.join(self.source_folder, ".depend")
        if os.path.isfile(stale_depend):
            os.remove(stale_depend)
        # Regenerate `.depend` with the host's real include paths.  The
        # `fix-depend-include` patch changes `include $(DEPEND_FILE)`
        # to `-include $(DEPEND_FILE)` so a temporarily-missing file
        # does not abort the makefile read.
        self.run("make -j1 depend", env=["conanrun", "pagodacf_ocaml_env"])
        # Build bytecode archive (cf.cma) + native archive (cf.cmxa).
        # `make default` builds cf.cma and links the test programs;
        # `make opt` builds cf.cmxa and native test programs.
        self.run("make -j1 default opt", env=["conanrun", "pagodacf_ocaml_env"])
        # Build the upstream TAP test binaries (t.cf bytecode + t-opt.cf native)
        # WITHOUT running them.  Upstream's `test`/`test.opt` targets execute
        # `./t.cf` via a broken `#!<bindir>/ocamlrun` shebang (Config.bindir is
        # hardcoded at OCaml build time and does not match this Conan cache
        # layout), so we build the binaries here and defer execution to
        # test_package, where the proper `ocamlrun`/`LD_PRELOAD` environment is
        # already wired (R19-R22).  test_package also runs every `conan create`
        # regardless of cache hits, so moving the upstream suite there fixes the
        # R26 regression where `build()` was skipped on a cached package and
        # `HMBS_UPSTREAM_TEST_RESULT` never got emitted (discovered=0
        # executed=0).
        self.run("make -j1 t.cf t-opt.cf", env=["conanrun", "pagodacf_ocaml_env"])

    def package(self):
        # Stage install into a temporary prefix using the Makefile's manual
        # cp-based `install` target (patch 0002 dropped `ocamlfind install`).
        # `make install` writes to `$(DESTDIR)/cf/`; stage there, then copy to
        # the Conan package's lib/cf.
        stage = os.path.join(self.build_folder, "stage")
        os.makedirs(stage, exist_ok=True)
        # DESTDIR is a one-off staging path specific to this package() call;
        # inject it via a transient Environment() script rather than mutating
        # the reusable pagodacf_ocaml_env.
        stage_env = Environment()
        stage_env.define("DESTDIR", stage)
        stage_env.vars(self).save_script("pagodacf_stage_env")
        self.run("make install", env=["conanrun", "pagodacf_ocaml_env", "pagodacf_stage_env"])
        # Copy staged cf/ tree into the Conan package's lib/cf
        cf_src = os.path.join(stage, "cf")
        cf_dst = os.path.join(self.package_folder, "lib", "cf")
        if os.path.isdir(cf_src):
            copy(self, "*", cf_src, cf_dst)
        # Package the upstream TAP test binaries + source so test_package can
        # run the upstream suite.  `build()` constructs `t.cf` (bytecode) and
        # `t-opt.cf` (native) in the build folder; we stage them under
        # lib/cf/tests/ alongside t/t_cf.ml.  test_package runs both binaries
        # with the proper `ocamlrun`/`LD_PRELOAD` environment (R19-R22) and
        # emits HMBS_UPSTREAM_TEST_RESULT.  This is necessary because
        # `conan create` skips `build()` on a cached package (R26 regression:
        # discovered=0 executed=0), while test_package always runs.
        tests_dst = os.path.join(self.package_folder, "lib", "cf", "tests")
        os.makedirs(tests_dst, exist_ok=True)
        for name in ("t.cf", "t-opt.cf"):
            src = os.path.join(self.build_folder, name)
            if os.path.isfile(src):
                copy(self, name, self.build_folder, tests_dst)
        t_src = os.path.join(self.source_folder, "t", "t_cf.ml")
        if os.path.isfile(t_src):
            copy(self, "t_cf.ml", os.path.join(self.source_folder, "t"), tests_dst)
        # License
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["cf"]
        self.cpp_info.libdirs = ["lib/cf"]
        self.cpp_info.includedirs = []
        self.env_info.CF_LIBDIR = os.path.join(self.package_folder, "lib", "cf")
