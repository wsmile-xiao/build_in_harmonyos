#!/usr/bin/env python3
"""Conan test_package — topkg 1.1.1 (consumer view).

Recreates the OHOS OCaml shims (as / ocamlc / ocamlopt, see the recipe
docstring) and compiles a consumer program against the PACKAGED topkg
archives, both natively and in bytecode, then runs a real device file-I/O
e2e case through the Topkg API (Topkg.String / Topkg.R / Topkg.Fpath /
Topkg.OS.File).
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException


class TopkgTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("ocaml/4.14.1.1.4")

    def layout(self):
        self.folders.build = "."
        self.folders.source = "."

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

    def _make_shims(self):
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

        env = {
            "OCAMLLIB": ocaml_lib,
            "CAML_LD_LIBRARY_PATH": os.path.join(ocaml_lib, "stublibs"),
            "PATH": shim + os.pathsep + ocaml_bin + os.pathsep
                    + os.environ.get("PATH", ""),
        }
        return shim, ocaml_lib, ocaml_bin, cc, env

    def test(self):
        pkg = self.dependencies[self.tested_reference_str]
        shim, ocaml_lib, ocaml_bin, cc, env = self._make_shims()
        test_sh = os.path.join(self.source_folder, "test.sh")
        if not os.path.isfile(test_sh):
            raise ConanException("test_package/test.sh missing")
        args = [test_sh, pkg.package_folder, ocaml_lib, ocaml_bin, cc, shim]
        self.run('sh "%s"' % '" "'.join(args),
                 env=["%s=%s" % (k, v) for k, v in env.items()])
        self.output.info("topkg test_package: ALL PASS")
