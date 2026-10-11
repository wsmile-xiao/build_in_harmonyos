#!/usr/bin/env python3
"""Conan recipe — xmlm 1.4.0

xmlm is a streaming XML codec for OCaml (single module + a small `xmltrip`
inspection tool). Upstream builds with topkg (ocaml pkg/pkg.ml build), which
drives ocamlbuild; neither topkg nor ocamlbuild exists in the OHOS registry,
so this recipe compiles the unmodified upstream sources directly with the
registry OCaml toolchain (ocaml/4.14.1.1.4), replicating exactly what the
topkg/ocamlbuild pipeline produces:
  src/xmlm.ml/.mli -> xmlm.cma / xmlm.cmxa / xmlm.cmxs / xmlm.a / xmlm.cmi
  test/xhtml.ml + test/xmltrip.ml -> bin/xmltrip
and runs the four upstream Pkg.test programs (test/test.ml, test/test_tree.ml,
test/xhtml.ml, test/examples.ml) built against the produced library.

OHOS/aarch64 adaptations (all verified on the physical device):
  - OCaml requires an assembler named `as`; the repo's registry ocaml package
    was configured against the CI-worker toolchain, so its baked `asm` value
    is a bare `as` that does not exist on the PC device. build() installs a
    tiny `as` shim that forwards to the OHOS clang from conan conf
    (tools.build:compiler_executables) with `-c`.
  - The baked native/bytecode C compiler points at the dead CI path
    /data/service/hnp/bin/clang, so every ocamlopt invocation passes
    `-cc <OHOS clang>`; with `-cc` set, OCaml drops the `-shared` flag for
    cmxs links, so `-ccopt -shared` restores it.
  - Conan's unzip() does not recognise the upstream `.tbz` extension, so
    source() downloads with an explicit `filename="xmlm-1.4.0.tar.bz2"`.
  - The dune/topkg `@install` layout is emulated by copying real artifacts
    (never symlinks); META ships verbatim from pkg/META.
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (get, copy, load, apply_conandata_patches,
                               export_conandata_patches)


class XmlmConan(ConanFile):
    name = "xmlm"
    version = "1.4.0"
    description = "Streaming XML codec for OCaml"
    license = "ISC"
    homepage = "https://erratique.ch/software/xmlm"
    url = ""  # CI fills this
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    # OCaml artifacts are static by nature (cma/cmxa/cmxs/a are produced
    # together regardless of this option); declared for interface convention.
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Registry-provided OCaml toolchain (R36); xmlm has no other deps.
        self.requires("ocaml/4.14.1.1.4")

    def layout(self):
        # In-source build (topkg writes artifacts next to the sources).
        self.folders.build = "."
        self.folders.source = "."

    def source(self):
        # Official single upstream URL. filename= is required because this
        # Conan version's unzip() does not map the `.tbz` extension to tar.bz2.
        get(self, filename="xmlm-1.4.0.tar.bz2", strip_root=True,
            **self.conan_data["sources"][self.version])

    def generate(self):
        pass  # no autotools/cmake; OCaml's own toolchain is used

    def _toolchain(self):
        """(cc, env_prefix) for the OCaml invocations."""
        ocaml_pkg = self.dependencies["ocaml/4.14.1.1.4"]
        ocaml_bin = os.path.join(ocaml_pkg.package_folder, "bin")
        ocaml_lib = os.path.join(ocaml_pkg.package_folder, "lib", "ocaml")
        cc = (self.conf.get("tools.build:compiler_executables", default={},
                            check_type=dict).get("c")
              or os.environ.get("CC") or "clang")

        # `as` shim -> OHOS clang -c (see module docstring). Kept inside the
        # build folder so it never leaks into the package.
        shim_dir = os.path.join(self.build_folder, ".ohc-toolchain")
        os.makedirs(shim_dir, exist_ok=True)
        as_shim = os.path.join(shim_dir, "as")
        with open(as_shim, "w") as f:
            f.write("#!/bin/sh\nexec %s -c \"$@\"\n" % shlex.quote(cc))
        os.chmod(as_shim, 0o755)

        env_prefix = (
            "OCAMLLIB=%s CAML_LD_LIBRARY_PATH=%s PATH=%s:%s:$PATH " % (
                shlex.quote(ocaml_lib),
                shlex.quote(os.path.join(ocaml_lib, "stublibs")),
                shlex.quote(shim_dir),
                shlex.quote(ocaml_bin),
            )
        )
        return cc, env_prefix

    def build(self):
        apply_conandata_patches(self)  # no-op: xmlm 1.4.0 needs no patches
        cc, env_prefix = self._toolchain()
        qcc = shlex.quote(cc)

        # --- library (byte + native + plugin), all in src/ ---
        self.run("cd src && %socamlc -c xmlm.mli" % env_prefix,
                 env="conanbuild")
        self.run("cd src && %socamlc -c xmlm.ml" % env_prefix,
                 env="conanbuild")
        self.run("cd src && %socamlc -a -o xmlm.cma xmlm.cmo" % env_prefix,
                 env="conanbuild")
        self.run("cd src && %socamlopt -c xmlm.ml" % env_prefix,
                 env="conanbuild")
        self.run("cd src && %socamlopt -a -o xmlm.cmxa xmlm.cmx" % env_prefix,
                 env="conanbuild")
        self.run("cd src && %socamlopt -cc %s -shared -ccopt -shared "
                 "-o xmlm.cmxs xmlm.cmx" % (env_prefix, qcc),
                 env="conanbuild")

        # --- upstream test programs (R51): the four Pkg.test entries of
        # pkg/pkg.ml are compiled against the produced library and executed.
        for t in ("test", "test_tree", "xhtml", "examples"):
            self.run("cd test && %socamlopt -I ../src -cc %s "
                     "../src/xmlm.cmxa %s.ml -o %s.exe" % (env_prefix, qcc, t, t),
                     env="conanbuild")
            self.run("cd test && ./%s.exe" % t, env="conanbuild")

        # --- xmltrip tool (Pkg.bin) + parse smoke test ---
        self.run("cd test && %socamlopt -I ../src -cc %s "
                 "../src/xmlm.cmxa xhtml.ml xmltrip.ml -o xmltrip"
                 % (env_prefix, qcc), env="conanbuild")
        sample = os.path.join(self.build_folder, "xmlm_smoke.xml")
        with open(sample, "w") as f:
            f.write('<root a="1"><child>text</child></root>\n')
        self.run("./test/xmltrip -p %s" % shlex.quote(sample),
                 env="conanbuild")

    def package(self):
        src = os.path.join(self.source_folder, "src")
        test = os.path.join(self.source_folder, "test")
        lib_dir = os.path.join(self.package_folder, "lib", "ocaml", "xmlm")
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(lib_dir, exist_ok=True)
        os.makedirs(bin_dir, exist_ok=True)

        for fname in ("xmlm.cma", "xmlm.cmxa", "xmlm.cmxs", "xmlm.a",
                      "xmlm.cmi", "xmlm.ml", "xmlm.mli"):
            src_file = os.path.join(src, fname)
            if not os.path.isfile(src_file):
                raise ConanException("mandatory build artifact missing: %s"
                                     % src_file)
            copy(self, fname, src, lib_dir)

        # META ships verbatim from the upstream pkg/META.
        meta_src = os.path.join(self.source_folder, "pkg", "META")
        meta = load(self, meta_src)
        if "xmlm" not in meta:
            raise ConanException("unexpected upstream pkg/META content")
        with open(os.path.join(lib_dir, "META"), "w") as f:
            f.write(meta)

        copy(self, "xmltrip", test, bin_dir)
        os.chmod(os.path.join(bin_dir, "xmltrip"), 0o755)

        # Reject dangling symlinks / empty files (HMDFS symptom guard).
        for d in (lib_dir, bin_dir):
            for fname in os.listdir(d):
                fpath = os.path.join(d, fname)
                if os.path.islink(fpath) or not os.path.isfile(fpath):
                    raise ConanException("package artifact is not a real file: %s"
                                         % fpath)
                if os.path.getsize(fpath) == 0:
                    raise ConanException("package artifact is empty: %s" % fpath)

    def package_info(self):
        # OCaml artifacts are consumed via OCAMLPATH, not via a C toolchain.
        # Conan 2 environment exports (self.env_info is a deprecated no-op
        # under Conan 2.x; buildenv_info/runenv_info are the supported way).
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib/ocaml/xmlm"]
        self.cpp_info.includedirs = ["lib/ocaml/xmlm"]
        self.cpp_info.bindirs = ["bin"]
        self.buildenv_info.append_path(
            "OCAMLPATH", os.path.join(self.package_folder, "lib", "ocaml"))
        self.buildenv_info.append_path(
            "PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.append_path(
            "PATH", os.path.join(self.package_folder, "bin"))
