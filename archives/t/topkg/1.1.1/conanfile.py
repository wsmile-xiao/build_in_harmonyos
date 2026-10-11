#!/usr/bin/env python3
"""Conan recipe — topkg 1.1.1

topkg is the OCaml software packager library ("The transitory OCaml software
packager"). Upstream builds itself with `ocaml pkg/pkg.ml build`, a bootstrap
that `#use "topfind"`s and then drives ocamlbuild. The registry does not yet
carry ocamlbuild (its own adaptation is submitted as a separate dependency
task), so this recipe compiles the unmodified upstream sources directly with
the registry OCaml toolchain, replicating the installed layout of
`Pkg.mllib ~api:["Topkg"] "src/topkg.mllib"`:
  src/*.ml/.mli -> topkg.cma / topkg.cmxa / topkg.a / topkg.cmxs + cmi + API mli
and runs the upstream Pkg.test program (test/test.ml).

OHOS/aarch64 adaptations (same family as the xmlm/ocamlbuild recipes):
  - `as` shim -> OHOS clang -c (registry ocaml package's baked assembler is a
    bare `as`; OHOS has no GNU as);
  - `ocamlc`/`ocamlopt` shims add `-cc <OHOS clang>` (baked C compiler is the
    dead CI path /data/service/hnp/bin/clang) and `-use-runtime <real
    ocamlrun>` (dangling bytecode shebangs); `-ccopt -shared` restores the
    cmxs `-shared` flag lost when `-cc` is used; freshly linked executables
    are re-signed with the SDK `binary-sign-tool` because OHOS refuses some
    lld-generated `.codesign` sections (EPERM).
No upstream source file is modified.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (get, copy, apply_conandata_patches,
                               export_conandata_patches)


class TopkgConan(ConanFile):
    name = "topkg"
    version = "1.1.1"
    description = "The transitory OCaml software packager"
    license = "ISC"
    homepage = "https://erratique.ch/software/topkg"
    url = "https://erratique.ch/software/topkg"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    # OCaml artifacts are static by nature; option kept for interface parity.
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # topkg's runtime library has no OCaml-level dependencies; the
        # upstream *build* deps (ocamlfind, ocamlbuild) are replaced by the
        # direct ocamlc/ocamlopt build (see module docstring).
        self.requires("ocaml/4.14.1.1.4")

    def layout(self):
        self.folders.build = "."
        self.folders.source = "."

    def source(self):
        get(self, filename="topkg-1.1.1.tar.bz2", strip_root=True,
            **self.conan_data["sources"][self.version])

    def generate(self):
        pass

    @staticmethod
    def _find_tool(candidates):
        for c in candidates:
            if c and os.path.isfile(c) and os.access(c, os.X_OK):
                return c
        for c in candidates:
            if c:
                w = shutil.which(c)
                if w:
                    return w
        return ""

    def _toolchain(self):
        ocaml_pkg = self.dependencies["ocaml/4.14.1.1.4"]
        ocaml_bin = os.path.join(ocaml_pkg.package_folder, "bin")
        ocaml_lib = os.path.join(ocaml_pkg.package_folder, "lib", "ocaml")
        cc = (self.conf.get("tools.build:compiler_executables", default={},
                            check_type=dict).get("c")
              or os.environ.get("CC") or "clang")
        cc_dir = os.path.dirname(cc)
        objcopy = self._find_tool([os.path.join(cc_dir, "llvm-objcopy"),
                                   "llvm-objcopy", "objcopy"])
        readelf = self._find_tool([os.path.join(cc_dir, "llvm-readelf"),
                                   "llvm-readelf", "readelf"])
        sign = self._find_tool([
            os.path.join(cc_dir, "..", "..", "..", "bin", "binary-sign-tool"),
            "/data/service/hnp/bin/binary-sign-tool",
            "binary-sign-tool",
        ])

        shim = os.path.join(self.build_folder, ".ohc-toolchain")
        os.makedirs(shim, exist_ok=True)

        def write(name, content):
            p = os.path.join(shim, name)
            with open(p, "w") as f:
                f.write(content)
            os.chmod(p, 0o755)

        write("as", "#!/bin/sh\nexec %s -c \"$@\"\n" % shlex.quote(cc))
        for tool in ("ocamlc", "ocamlc.opt"):
            write(tool, "#!/bin/sh\nexec %s -use-runtime %s -cc %s \"$@\"\n" % (
                shlex.quote(os.path.join(ocaml_bin, tool)),
                shlex.quote(os.path.join(ocaml_bin, "ocamlrun")),
                shlex.quote(cc)))
        write("sign-elf", (
            "#!/bin/sh\n"
            "f=\"$1\"\n"
            "[ -f \"$f\" ] || exit 0\n"
            "case \"$f\" in *.cmxs|*.so|*.o|*.a|*.cma|*.cmxa|*.cmo|*.cmx) exit 0 ;; esac\n"
            "head -c4 \"$f\" | grep -q ELF || exit 0\n"
            "%s -l \"$f\" 2>/dev/null | grep -q INTERP || exit 0\n"
            "%s --remove-section .codesign \"$f\" 2>/dev/null\n"
            "if %s sign -inFile \"$f\" -outFile \"$f.signed.tmp\" -selfSign 1 >/dev/null 2>&1; then\n"
            "  mv \"$f.signed.tmp\" \"$f\" && chmod 755 \"$f\"\n"
            "else\n"
            "  rm -f \"$f.signed.tmp\"\n"
            "fi\n"
            "exit 0\n") % (shlex.quote(readelf), shlex.quote(objcopy),
                           shlex.quote(sign or "binary-sign-tool")))
        opt_body = (
            "#!/bin/sh\n"
            "EXTRA=\"\"\n"
            "case \" $* \" in *\" -shared \"*) EXTRA=\"-ccopt -shared\" ;; esac\n"
            "%s -cc %s $EXTRA \"$@\"\n"
            "rc=$?\n"
            "if [ $rc -eq 0 ]; then\n"
            "  out=\"\"; prev=\"\"\n"
            "  for a in \"$@\"; do [ \"$prev\" = \"-o\" ] && out=\"$a\"; prev=\"$a\"; done\n"
            "  [ -n \"$out\" ] && %s \"$out\"\n"
            "fi\n"
            "exit $rc\n") % (shlex.quote(os.path.join(ocaml_bin, "%s")),
                             shlex.quote(cc),
                             shlex.quote(os.path.join(shim, "sign-elf")))
        for tool in ("ocamlopt", "ocamlopt.opt"):
            write(tool, opt_body % tool)

        env_prefix = (
            "OCAMLLIB=%s CAML_LD_LIBRARY_PATH=%s PATH=%s:%s:$PATH " % (
                shlex.quote(ocaml_lib),
                shlex.quote(os.path.join(ocaml_lib, "stublibs")),
                shlex.quote(shim), shlex.quote(ocaml_bin)))
        return cc, env_prefix

    def build(self):
        apply_conandata_patches(self)  # no-op: upstream builds unmodified
        cc, env_prefix = self._toolchain()
        qcc = shlex.quote(cc)

        # 1) dependency-ordered module compilation (ocamldep -sort)
        self.run(
            "%socamldep -sort src/*.ml src/*.mli "
            "| tr ' ' '\\n' | sed '/^$/d' > order.txt" % env_prefix,
            env="conanbuild")
        order = open(os.path.join(self.source_folder, "order.txt")).read().split()
        if not order:
            raise ConanException("ocamldep -sort produced no output; cannot "
                                 "determine the build order")
        for rel in order:
            name = os.path.basename(rel)
            if name.endswith(".mli"):
                self.run("cd src && %socamlc -c -I . %s" % (env_prefix, name),
                         env="conanbuild")
            elif name.endswith(".ml"):
                self.run("cd src && %socamlc -c -I . %s" % (env_prefix, name),
                         env="conanbuild")
                self.run("cd src && %socamlopt -c -I . %s" % (env_prefix, name),
                         env="conanbuild")

        # 2) archives in dependency order (ocamldep -sort output; dependencies
        #    must precede dependents for single-pass archive linking). The
        #    upstream mllib order (API module first) cannot be used directly
        #    here: OCaml resolves archive units in one pass.
        modules = []
        for rel in order:
            name = os.path.basename(rel)
            if name.endswith(".ml"):
                mod = name[:-3]
                if mod not in modules:
                    modules.append(mod)
        cmos = " ".join(m + ".cmo" for m in modules)
        cmxs = " ".join(m + ".cmx" for m in modules)
        self.run("cd src && %socamlc -a -o topkg.cma %s" % (env_prefix, cmos),
                 env="conanbuild")
        self.run("cd src && %socamlopt -a -o topkg.cmxa %s" % (env_prefix, cmxs),
                 env="conanbuild")
        self.run("cd src && %socamlopt -cc %s -shared -ccopt -shared "
                 "-o topkg.cmxs topkg.cmxa" % (env_prefix, qcc),
                 env="conanbuild")

        # 3) upstream test (R51): Pkg.test "test/test"
        self.run("cd test && %socamlopt -I ../src ../src/topkg.cmxa "
                 "test.ml -o test.exe" % env_prefix, env="conanbuild")
        self.run("cd test && ./test.exe alpha beta", env="conanbuild")

    def package(self):
        src = os.path.join(self.source_folder, "src")
        lib_dir = os.path.join(self.package_folder, "lib", "ocaml", "topkg")
        os.makedirs(lib_dir, exist_ok=True)

        for fname in ("topkg.cma", "topkg.cmxa", "topkg.cmxs", "topkg.a",
                      "topkg.mli"):
            src_file = os.path.join(src, fname)
            if not os.path.isfile(src_file):
                raise ConanException("mandatory build artifact missing: %s"
                                     % src_file)
            copy(self, fname, src, lib_dir)
        for fname in os.listdir(src):
            if fname.endswith(".cmi"):
                copy(self, fname, src, lib_dir)
        copy(self, "META", os.path.join(self.source_folder, "pkg"), lib_dir)
        copy(self, "topkg.opam", self.source_folder, lib_dir)
        copy(self, "LICENSE.md", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

        for fname in os.listdir(lib_dir):
            p = os.path.join(lib_dir, fname)
            if os.path.islink(p) or not os.path.isfile(p):
                raise ConanException("package artifact is not a real file: %s" % p)
            if os.path.getsize(p) == 0:
                raise ConanException("package artifact is empty: %s" % p)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib/ocaml/topkg"]
        self.cpp_info.includedirs = ["lib/ocaml/topkg"]
        self.buildenv_info.append_path(
            "OCAMLPATH", os.path.join(self.package_folder, "lib", "ocaml"))
