#!/usr/bin/env python3
"""Conan recipe — cairo2 0.6.5

cairo2 is the OCaml binding to the Cairo 2D vector graphics library
(upstream: https://github.com/Chris00/ocaml-cairo).

Toolchain strategy (same pattern as pdfsandwich 0.1.7):
  - OCaml compiler and dune are build-time tool_requires (registry packages
    ocaml/4.14.1.1.4 and dune/3.17.0 target aarch64 OHOS natively).
  - The registry dune package ships only the dune binary without the
    dune-configurator library, so the upstream `config/discover` probe is
    removed by patch; this recipe generates src/c_flags.sexp,
    src/c_library_flags.sexp and src/cairo_ocaml.h directly from the Conan
    dependency graph (no pkg-config, no baked shell env, R33 compliant).
  - OCAMLLIB is derived from the ocamlc binary location in PATH because
    `ocamlc -where` returns a stale path after conan cache relocation.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class Cairo2Conan(ConanFile):
    name = "cairo2"
    version = "0.6.5"
    description = "OCaml bindings to Cairo, a 2D Vector Graphics Library"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/Chris00/ocaml-cairo"
    url = ""  # CI fills this
    package_type = "static-library"  # OCaml archive (cmxa/.a) package; stubs ship as-is
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # C libraries needed to compile/link the C stubs (cairo-ft usage)
        self.requires("cairo/1.18.4.2")
        self.requires("freetype/2.14.3")
        self.requires("fontconfig/2.18.1.1")

    def build_requirements(self):
        # OCaml toolchain + dune build system (build-time only)
        self.tool_requires("ocaml/4.14.1.1.4")
        self.tool_requires("dune/3.17.0")

    def layout(self):
        self.folders.build = "."
        self.folders.source = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _dep_dirs(self, dep):
        """Absolute include/lib dirs of a host dependency."""
        inc = [os.path.join(dep.package_folder, d) for d in dep.cpp_info.includedirs]
        lib = [os.path.join(dep.package_folder, d) for d in dep.cpp_info.libdirs]
        return inc, lib

    def _write_probe_outputs(self):
        """Generate the files normally produced by upstream config/discover."""
        src = os.path.join(self.source_folder, "src")
        cairo = self.dependencies["cairo"]
        ft = self.dependencies["freetype"]
        fc = self.dependencies["fontconfig"]

        c_inc, _ = self._dep_dirs(cairo)
        ft_inc, _ = self._dep_dirs(ft)
        fc_inc, _ = self._dep_dirs(fc)
        _, cairo_lib = self._dep_dirs(cairo)
        _, ft_lib = self._dep_dirs(ft)
        _, fc_lib = self._dep_dirs(fc)

        # include/freetype2/freetype needed for direct "ftmodapi.h" includes
        incs = c_inc + ft_inc + [os.path.join(d, "freetype") for d in ft_inc
                                 if os.path.isdir(os.path.join(d, "freetype"))] + fc_inc
        libs = cairo_lib + ft_lib + fc_lib

        cflags = " ".join(f"-I{d}" for d in incs)
        clibs = " ".join([f"-L{d}" for d in libs] + ["-lcairo", "-lfontconfig", "-lfreetype"])

        # Enable the OCaml FT font API (cairo-ft available through cairo)
        with open(os.path.join(src, "cairo_ocaml.h.p"), "r") as f:
            hdr = f.read()
        marker = "/* #define OCAML_CAIRO_HAS_FT 1 */"
        if marker in hdr:
            hdr = hdr.replace(marker, "#define OCAML_CAIRO_HAS_FT 1")
        with open(os.path.join(src, "cairo_ocaml.h"), "w") as f:
            f.write(hdr)
        with open(os.path.join(src, "c_flags.sexp"), "w") as f:
            f.write(f"({cflags})\n")
        with open(os.path.join(src, "c_library_flags.sexp"), "w") as f:
            f.write(f"({clibs})\n")

    @staticmethod
    def _ocamllib_expr():
        # pdfsandwich lesson: ocamlc -where returns a stale path after conan
        # cache relocation; derive OCAMLLIB from the ocamlc binary location.
        return ('OCAMLLIB="$(d=$(dirname "$(realpath "$(which ocamlc)")"); '
                'echo "$(dirname "$d")/lib/ocaml")"')

    def _host_ld_path(self):
        parts = []
        for name in ("cairo", "freetype", "fontconfig", "pixman", "expat",
                     "libpng", "zlib", "brotli", "bzip2"):
            try:
                dep = self.dependencies[name]
            except KeyError:
                continue
            if dep.package_folder is None:
                continue
            for d in (dep.cpp_info.libdirs or []):
                parts.append(os.path.join(dep.package_folder, d))
        seen, out = set(), []
        for p in parts:
            if p not in seen:
                seen.add(p)
                out.append(p)
        return ":".join(out)

    def build(self):
        apply_conandata_patches(self)
        self._write_probe_outputs()
        self.run(f"{self._ocamllib_expr()} dune build -p cairo2 -j2", env="conanbuild")
        # Upstream test suite (tests/dune): 7 executables, all must pass
        ld = self._host_ld_path()
        self.run(f"export LD_LIBRARY_PATH={ld}:$LD_LIBRARY_PATH; "
                 f"{self._ocamllib_expr()} dune runtest", env="conanbuild")

    def package(self):
        # dune's install tree uses symlinks into _build; conan.tools.files.copy
        # copies links verbatim (broken in the package). Copy real files instead.
        import shutil
        build_lib = os.path.join(self.source_folder, "_build", "install", "default", "lib")
        for sub in ("cairo2", "stublibs"):
            src_dir = os.path.join(build_lib, sub)
            dst_dir = os.path.join(self.package_folder, "lib", sub)
            os.makedirs(dst_dir, exist_ok=True)
            for entry in sorted(os.listdir(src_dir)):
                src = os.path.join(src_dir, entry)
                real = os.path.realpath(src)
                if os.path.isfile(real):
                    shutil.copy2(real, os.path.join(dst_dir, entry))

    def package_info(self):
        self.cpp_info.includedirs = ["lib/cairo2"]
        self.cpp_info.libdirs = ["lib/cairo2", "lib/stublibs"]
        self.cpp_info.libs = ["cairo_stubs"]
        self.cpp_info.system_libs = ["cairo", "fontconfig", "freetype"]
