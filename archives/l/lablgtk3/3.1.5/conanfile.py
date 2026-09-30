#!/usr/bin/env python3
"""Conan recipe — lablgtk3 3.1.5 (OCaml bindings for GTK3)

Pure dune build (dune-project lang 1.8, opam build field:
`dune build -p lablgtk3`).  The release tarball ships pregenerated
varcc.ml/propcc.ml, so camlp5 is NOT needed.  OCaml-side dependencies are
vendored into this package and built first with the same dune toolchain
(the single-library gate forbids introducing new archives/ directories):

  - camlp-streams 5.0.1  (pure OCaml; used by the varcc/propcc build tools)
  - cairo2 0.6.4         (OCaml cairo bindings; src/dune has (libraries
                          threads cairo2), C stubs link libcairo via
                          pkg-config)

Both are installed into a build-time findlib root exposed through an
explicit ocamlfind configuration (OCAMLFIND_CONF) and OCAMLPATH.

C side: src/dune runs `dune_config -pkg gtk+-3.0 -version 3.18`
(dune.configurator) at build time; PKG_CONFIG_PATH points at the
PkgConfigDeps-generated .pc files of the gtk/3.24.43 dependency graph
(gtk+-3.0 >= 3.18 satisfied by 3.24.43).

OHOS platform facts (knowledge E253/E463/E471; archives/o/ocaml notes):
  - hmmac refuses to exec shebang scripts; the ocaml/4.14.1.1.4 package
    installs native ELF ocamlc/ocamlopt (upstream `ln -sf *.opt` replaced
    by `cp -f`), so plain compiler names work.
  - /tmp is read-only: TMPDIR/TMP/TEMP are redirected into the build dir.
  - No native display backend (E463/E471): build-only test semantics, the
    upstream opam run-test (`dune build -p name examples/buttons.exe`)
    is a compile-only smoke target and is executed here as such.

Install layout (findlib): lib/lablgtk3/** (META, .cma/.cmxa, headers),
lib/stublibs/dll*.so, plus vendored lib/camlp-streams/** and lib/cairo/**.
"""
import os
import shlex
import shutil
import time

from conan import ConanFile
from conan.tools.files import get, copy, save, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps


def _wait_file(path, attempts=20, delay=1.0):
    """Wait until `path` can actually be opened and read.

    The OHOS shared-storage filesystem (HMDFS) intermittently reports freshly
    written/extracted files in readdir() while open() still fails with
    ENOENT for a while (observed on-device; cf. E253/E463 HMDFS entries).
    Builds that scan a just-extracted/copyied tree race against that lag, so
    verify a sentinel file is genuinely readable before proceeding.
    """
    last = None
    for _ in range(attempts):
        try:
            with open(path, "rb") as f:
                f.read(1)
            return
        except OSError as e:
            last = e
            time.sleep(delay)
    raise RuntimeError("file never became readable: %s (%s)" % (path, last))


def _copy2_retry(src, dst, *, follow_symlinks=True):
    """shutil.copy2 with retries (HMDFS freshly-created-dir ENOENT lag)."""
    last = None
    for _ in range(20):
        try:
            return shutil.copy2(src, dst, follow_symlinks=follow_symlinks)
        except OSError as e:
            last = e
            time.sleep(1.0)
    raise RuntimeError("copy failed: %s -> %s (%s)" % (src, dst, last))


def _copy_tree_real(src, dst):
    """Copy a dune install tree dereferencing symlinks.

    dune's `-p` install layout emits META (and friends) as RELATIVE SYMLINKS
    into _build/default/<pkg>.META...  Copying them as links (conan copy /
    plain cp) yields dangling links; symlinks=False materializes the real
    file contents (targets exist inside _build at copy time).
    """
    last = None
    for _ in range(20):
        try:
            os.makedirs(dst, exist_ok=True)
            break
        except OSError as e:
            last = e
            time.sleep(1.0)
    if last is not None and not os.path.isdir(dst):
        raise RuntimeError("mkdir failed: %s (%s)" % (dst, last))
    shutil.copytree(src, dst, dirs_exist_ok=True, symlinks=False,
                    copy_function=_copy2_retry)


# Static sexp replacement for camlp-streams' root `dune` file.
# Upstream ships that file as a Jbuild_plugin.V1 OCaml-syntax dune file,
# which dune evaluates by exec'ing the `ocaml` toplevel.  The
# ocaml/4.14.1.1.4 package ships bin/ocaml as a bytecode shebang script
# whose interpreter path is stale (build-time conan cache path) and which
# OHOS hmmac refuses anyway (E253).  The content below is EXACTLY what the
# plugin generates for OCaml >= 4.08 and < 5.0 (toolchain here is
# ocaml/4.14.1.1.4): Stream/Genlex are re-exported from the stdlib via
# generated stub modules; the enabled_if guards are kept verbatim so the
# file stays faithful to upstream semantics.
CAMLP_STREAMS_STATIC_DUNE = """\
(rule
  (target stream.mli)
  (action (copy src/%{target} %{target}))
  (enabled_if (>= %{ocaml_version} 5.0)))

(rule
  (target stream.ml)
  (action (copy src/%{target} %{target}))
  (enabled_if (>= %{ocaml_version} 5.0)))

(rule
  (target stream.mli)
  (action (with-stdout-to stream.mli
    (echo "include module type of struct include Stream end")))
  (enabled_if (< %{ocaml_version} 5.0)))

(rule
  (target stream.ml)
  (action (with-stdout-to stream.ml
    (echo "include Stream")))
  (enabled_if (< %{ocaml_version} 5.0)))

(rule
  (target genlex.mli)
  (action (copy src/%{target} %{target}))
  (enabled_if (>= %{ocaml_version} 5.0)))

(rule
  (target genlex.ml)
  (action (copy src/%{target} %{target}))
  (enabled_if (>= %{ocaml_version} 5.0)))

(rule
  (target genlex.mli)
  (action (with-stdout-to genlex.mli
    (echo "include module type of struct include Genlex end")))
  (enabled_if (< %{ocaml_version} 5.0)))

(rule
  (target genlex.ml)
  (action (with-stdout-to genlex.ml
    (echo "include Genlex")))
  (enabled_if (< %{ocaml_version} 5.0)))

(rule
  (action (with-stdout-to flags.sexp (echo "(-w -9)")))
  (enabled_if (>= %{ocaml_version} 5.0)))
(rule
  (action (with-stdout-to flags.sexp (echo "(-w -3)")))
  (enabled_if (and (>= %{ocaml_version} 4.14) (< %{ocaml_version} 5.0))))
(rule
  (action (with-stdout-to flags.sexp (echo "()")))
  (enabled_if (< %{ocaml_version} 4.14)))

(library
  (name camlp_streams)
  (public_name camlp-streams)
  (modules :standard)
  (wrapped false)
  (flags :standard (:include flags.sexp)))
"""


# Standalone build of the dune-configurator library (see build() step 5).
CONFIGURATOR_DUNE = """\
(ocamllex extract_obj)

(library
 (name configurator)
 (public_name dune-configurator)
 (private_modules import dune_lang ocaml_config extract_obj)
 (libraries unix csexp)
 (flags (:standard -safe-string)))
"""

CONFIGURATOR_DUNE_PROJECT = """\
(lang dune 3.0)
"""

CONFIGURATOR_OPAM = """\
opam-version: "2.0"
synopsis: "dune-configurator vendored for the lablgtk3 build"
maintainer: "OpenHarmony conan recipe (lablgtk3/3.1.5)"
authors: ["Jane Street Group, LLC"]
depends: [
  "ocaml"
  "dune"
  "csexp"
]
"""


class Lablgtk3Conan(ConanFile):
    name = "lablgtk3"
    version = "3.1.5"
    description = "OCaml bindings for GTK3 (lablgtk3 findlib package)"
    # Upstream lablgtk3.opam license field.  Vendored build deps carry their
    # own licenses (camlp-streams: LGPL-2.1-only WITH OCaml-LGPL-linking-
    # exception; cairo2: LGPL-3.0) — see manifest.yaml / notes.md.
    license = "LGPL-2.1-or-later WITH OCaml-LGPL-linking-exception"
    homepage = "https://github.com/garrigue/lablgtk"
    url = ""  # CI fills this

    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # gtk+-3.0 >= 3.18 dev files; the gtk package carries the whole C
        # closure (glib/pango/cairo/cairo-gobject/gdk-pixbuf/atk/fribidi/
        # libepoxy) and publishes the gtk+-3.0 pkg-config name.
        self.requires("gtk/3.24.43")
        # OCaml toolchain, all published on the artifact registry
        self.tool_requires("ocaml/4.14.1.1.4")
        self.tool_requires("dune/3.17.0")
        self.tool_requires("findlib/1.9.8")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # conan 2.29 unzip() dispatch: .tbz is NOT a known tar suffix and is
        # handed to zipfile (BadZipFile) — build-chain-pitfalls entry.
        # Pin a .tar.bz2 filename to route into untargz (content untouched,
        # sha256 still verified against the official .tbz checksum).
        get(self, **self.conan_data["sources"][self.version],
            filename="lablgtk3-3.1.5.tar.bz2", strip_root=True)

    def generate(self):
        # Forwarding .pc files for the gtk dependency graph; dune_config
        # resolves gtk+-3.0 through pkg-config at build time (E527/E348).
        PkgConfigDeps(self).generate()
        gen = self.generators_folder
        # Fail fast with an explicit list instead of a late pkg-config error.
        missing = [pc for pc in ("gtk+-3.0.pc", "cairo.pc", "glib-2.0.pc")
                   if not os.path.isfile(os.path.join(gen, pc))]
        if missing:
            raise FileNotFoundError(
                "PkgConfigDeps output missing: %s (generators dir: %s)"
                % (", ".join(missing), gen))
        # Explicit link closure for lld executable links (build-chain-pitfalls
        # "shared library link closure" / libgee case): pkg-config's compiled-in
        # system dirs (/storage/Users/currentUser/usr/local/lib) shadow conan
        # packages with static brew archives (libgio-2.0.a, libglib-2.0.a)
        # whose g_libintl_* symbols are unresolved, and libgio needs the
        # private lib/libintl.so.8.  Prepend every conan dependency libdir to
        # the gtk+-3.0.pc Libs so conan shared libraries always win.
        lib_dirs = []
        for dep in self.dependencies.host.values():
            lib_dir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(lib_dir) and lib_dir not in lib_dirs:
                lib_dirs.append(lib_dir)
        glib_lib = os.path.join(self.dependencies["glib"].package_folder, "lib")
        if not os.path.isfile(os.path.join(glib_lib, "libintl.so")):
            raise FileNotFoundError("glib libintl.so missing: %s" % glib_lib)
        if glib_lib not in lib_dirs:
            lib_dirs.append(glib_lib)
        # Round-02 finding: -L ordering alone is NOT enough — ocamlopt itself
        # prepends -L/usr/local/lib to every link (baked into the toolchain)
        # and lld resolves lib<name>.so then lib<name>.a WITHIN each directory
        # before moving on, so the static-only libgobject-2.0.a/libglib-2.0.a
        # in that first directory beat the conan shared libs in later -L dirs
        # (undefined ffi_*/pcre2_* pulled from gclosure.o/regex.o of those
        # archives).  Fix per build-chain-pitfalls: list the supplying .so
        # files as EXPLICIT link inputs (isfile-guarded, ahead of every -l
        # flag) so they define the symbols first and the shadow archives have
        # nothing left to satisfy.
        explicit_inputs = []
        for name in ("gio-2.0", "girepository-2.0", "glib-2.0",
                     "gmodule-2.0", "gobject-2.0", "gthread-2.0", "intl"):
            so_path = os.path.join(glib_lib, "lib%s.so" % name)
            if os.path.isfile(so_path):
                explicit_inputs.append(so_path)
        closure = " ".join(explicit_inputs + ["-L%s" % d for d in lib_dirs])
        gtk_pc = os.path.join(gen, "gtk+-3.0.pc")
        with open(gtk_pc, encoding="utf-8") as f:
            pc_text = f.read()
        if "Libs:" in pc_text:
            pc_text = pc_text.replace("Libs:", "Libs: %s " % closure, 1)
        else:
            pc_text += "Libs: %s\n" % closure
        with open(gtk_pc, "w", newline="\n") as f:
            f.write(pc_text)

    def _ocaml_env(self, ocaml_bin, ocaml_stdlib, dune_bin, findlib_bin,
                   conf, ldconf, path_dirs, stubdirs, gen, tmp):
        """Explicit, self-contained OCaml/pkg-config environment prefix.

        No reliance on ambient device state (implement-policy §5): stdlib,
        findlib config, search paths, pkg-config path and TMPDIR are all
        pinned to conan cache / build-dir locations.
        """
        q = shlex.quote
        return (
            f'OCAMLLIB={q(ocaml_stdlib)} '
            f'OCAMLRUN={q(os.path.join(ocaml_bin, "ocamlrun"))} '
            f'OCAMLPATH={q(":".join(path_dirs))} '
            f'OCAMLFIND_CONF={q(conf)} '
            f'OCAMLFIND_LDCONF={q(ldconf)} '
            f'CAML_LD_LIBRARY_PATH={q(":".join(stubdirs))} '
            f'PATH={q(ocaml_bin)}:{q(dune_bin)}:{q(findlib_bin)}:$PATH '
            f'PKG_CONFIG_PATH={q(gen)} '
            f'TMPDIR={q(tmp)} TMP={q(tmp)} TEMP={q(tmp)}'
        )

    def build(self):
        apply_conandata_patches(self)
        b = self.build_folder
        src = self.source_folder
        gen = self.generators_folder

        tmp = os.path.join(b, ".tmp")
        os.makedirs(tmp, exist_ok=True)

        # ── 1. Vendor OCaml libraries (official archives, sha256 pinned) ──
        vendor = self.conan_data["vendor_sources"]
        cs_dir = os.path.join(b, ".vendor", "camlp-streams")
        cairo_dir = os.path.join(b, ".vendor", "cairo2")
        dune_src = os.path.join(b, ".vendor", "dune")
        csexp_dir = os.path.join(b, ".vendor", "csexp")
        get(self, **vendor["camlp-streams"], destination=cs_dir, strip_root=True)
        get(self, **vendor["cairo2"], destination=cairo_dir, strip_root=True,
            filename="cairo2-0.6.4.tar.bz2")
        get(self, **vendor["dune"], destination=dune_src, strip_root=True)
        get(self, **vendor["csexp"], destination=csexp_dir, strip_root=True,
            filename="csexp-1.5.2.tar.bz2")
        # HMDFS visibility lag: verify each freshly extracted project is
        # genuinely readable before dune scans it (see _wait_file).
        for proj in (cs_dir, cairo_dir, dune_src, csexp_dir):
            _wait_file(os.path.join(proj, "dune-project"))

        # Replace the Jbuild_plugin OCaml-syntax root dune file (see comment
        # on CAMLP_STREAMS_STATIC_DUNE; dune cannot exec the `ocaml` toplevel
        # on OHOS to evaluate it).
        save(self, os.path.join(cs_dir, "dune"), CAMLP_STREAMS_STATIC_DUNE)

        # ── 2. Locate toolchain pieces ──
        ocaml_pkg = self.dependencies.build["ocaml"].package_folder
        ocaml_bin = os.path.join(ocaml_pkg, "bin")
        ocaml_stdlib = os.path.join(ocaml_pkg, "lib", "ocaml")
        dune_pkg = self.dependencies.build["dune"].package_folder
        dune_bin = os.path.join(dune_pkg, "bin")
        dune_lib = os.path.join(dune_pkg, "lib")
        findlib_pkg = self.dependencies.build["findlib"].package_folder
        findlib_bin = os.path.join(findlib_pkg, "bin")
        findlib_sitelib = os.path.join(findlib_pkg, "lib", "ocaml")

        for d in (ocaml_bin, ocaml_stdlib, dune_bin, findlib_bin):
            if not os.path.isdir(d):
                raise FileNotFoundError(
                    "toolchain component missing: %s" % d)

        # ── 3. Explicit findlib root for the vendored libraries ──
        # NOTE: ocamlroot sits BEFORE the dune package lib in the findlib
        # path: the published dune package ships lib/dune as an EMPTY
        # findlib package (META only), while the vendored -p build emits a
        # real one — first match in path order wins, so the real one must
        # come first.
        ocamlroot = os.path.join(b, ".ocamlroot", "lib")
        ocaml_stublibs = os.path.join(ocamlroot, "stublibs")
        os.makedirs(ocaml_stublibs, exist_ok=True)

        ldconf = os.path.join(b, "ld.conf")
        with open(ldconf, "w", newline="\n") as f:
            f.write(os.path.join(ocaml_stdlib, "stublibs") + "\n")
            f.write(ocaml_stublibs + "\n")
        path_dirs = [ocaml_stdlib, ocamlroot, dune_lib, findlib_sitelib]
        conf = os.path.join(b, "ocamlfind.conf")
        with open(conf, "w", newline="\n") as f:
            # findlib.conf: path is a colon-separated directory list
            # (newline-separated entries break findlib's directory scan)
            f.write('destdir = "%s"\n' % ocamlroot)
            f.write('path = "%s"\n' % ":".join(path_dirs))
            f.write('ldconf = "%s"\n' % ldconf)

        stubdirs = [os.path.join(ocaml_stdlib, "stublibs"), ocaml_stublibs]
        def dune(cmd, cwd_arg):
            """Run a dune build with retries.

            The OHOS shared-storage filesystem intermittently fails directory
            scans on freshly written trees (E253 HMDFS notes + on-device
            observation); dune is incremental, so a retry resumes cleanly.
            """
            last_err = None
            for attempt in range(3):
                try:
                    self.run(f"{env} {cmd}", cwd=cwd_arg, env="conanbuild")
                    return
                except Exception as e:
                    last_err = e
                    time.sleep(10)
            raise last_err

        env = self._ocaml_env(ocaml_bin, ocaml_stdlib, dune_bin, findlib_bin,
                              conf, ldconf, path_dirs, stubdirs, gen, tmp)

        def install_lib(builtir, pkg_name):
            """Copy a dune -p install tree into the findlib root."""
            inst_lib = os.path.join(builtir, "_build", "install", "default", "lib")
            _copy_tree_real(os.path.join(inst_lib, pkg_name),
                            os.path.join(ocamlroot, pkg_name))
            stubs = os.path.join(inst_lib, "stublibs")
            if os.path.isdir(stubs):
                _copy_tree_real(stubs, os.path.join(ocamlroot, "stublibs"))
            # HMDFS visibility lag (see _wait_file): make sure the freshly
            # copied META is genuinely readable before the next dune run
            # scans the findlib root.
            _wait_file(os.path.join(ocamlroot, pkg_name, "META"))

        # ── 4. camlp-streams (pure OCaml, no pkg-config needed) ──
        dune("dune build -j 4 -p camlp-streams", cs_dir)
        install_lib(cs_dir, "camlp-streams")

        # ── 5. csexp + dune-configurator (needed by cairo2 and lablgtk3
        #       builds; absent from the published dune package, see the
        #       conandata.yml note) ──
        dune("dune build -j 4 -p csexp", csexp_dir)
        install_lib(csexp_dir, "csexp")

        # dune-configurator: the dune source workspace itself cannot build it
        # here — its (vendored_dirs *) setup hides the ambient OCAMLPATH, so
        # the external csexp we just installed is invisible to it.  The
        # configurator library is self-contained (private import/dune_lang/
        # ocaml_config modules + unix + csexp only), so build it as a
        # standalone project against the installed csexp.
        cfg_dir = os.path.join(b, ".vendor", "dune-configurator")
        os.makedirs(cfg_dir, exist_ok=True)
        src_lib = os.path.join(dune_src, "otherlibs", "configurator", "src")
        for f in ("configurator.ml", "dune_lang.ml", "dune_lang.mli",
                  "extract_obj.mli", "import.ml", "ocaml_config.ml",
                  "ocaml_config.mli", "v1.ml", "v1.mli", "extract_obj.mll"):
            shutil.copy2(os.path.join(src_lib, f), os.path.join(cfg_dir, f))
        save(self, os.path.join(cfg_dir, "dune"), CONFIGURATOR_DUNE)
        save(self, os.path.join(cfg_dir, "dune-project"), CONFIGURATOR_DUNE_PROJECT)
        save(self, os.path.join(cfg_dir, "dune-configurator.opam"), CONFIGURATOR_OPAM)
        _wait_file(os.path.join(cfg_dir, "dune-project"))
        dune("dune build -j 4 -p dune-configurator", cfg_dir)
        install_lib(cfg_dir, "dune-configurator")

        # ── 6. cairo2 (dune-configurator probes pkg-config cairo) ──
        dune("dune build -j 2 -p cairo2", cairo_dir)
        # install dir follows the PUBLIC name (cairo2), not the lib name
        install_lib(cairo_dir, "cairo2")

        # ── 7. lablgtk3 itself (opam build semantics: dune build -p name) ──
        _wait_file(os.path.join(src, "dune-project"))
        dune("dune build -j 2 -p lablgtk3", src)
        # ── 8. Upstream run-test parity (opam run-test field), build-only ──
        # `dune build -p lablgtk3 -j jobs examples/buttons.exe` compiles the
        # example as a link-level smoke target; running it needs a display
        # server (E471: no native display backend on OHOS).
        dune("dune build -j 2 -p lablgtk3 examples/buttons.exe", src)

    def package(self):
        b = self.build_folder
        src = self.source_folder
        lib = os.path.join(self.package_folder, "lib")
        inst_lib = os.path.join(src, "_build", "install", "default", "lib")
        # main findlib package + stubs plugins (dereference dune's META links)
        _copy_tree_real(os.path.join(inst_lib, "lablgtk3"),
                        os.path.join(lib, "lablgtk3"))
        stubs = os.path.join(inst_lib, "stublibs")
        if os.path.isdir(stubs):
            _copy_tree_real(stubs, os.path.join(lib, "stublibs"))
        # vendored OCaml libraries (camlp-streams, csexp, dune-configurator,
        # cairo) — already dereferenced in build()
        _copy_tree_real(os.path.join(b, ".ocamlroot", "lib"), lib)
        # licenses
        licenses = os.path.join(self.package_folder, "licenses")
        copy(self, "LICENSE", src, licenses)
        copy(self, "LGPL", src, licenses)

    def package_info(self):
        # OCaml findlib package: consumed through OCAMLPATH / ocamlfind, not
        # as a C/C++ link library.  The stubs .so are dlopen plugins for
        # bytecode consumers; native consumers link them statically.
        self.cpp_info.libs = []
        self.cpp_info.libdirs = ["lib/stublibs"]
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = ["lib/lablgtk3"]
        libd = os.path.join(self.package_folder, "lib")
        # Downstream OCaml consumers (dune/ocamlfind) resolve the packages
        # through these env entries (findlib/1.9.8 recipe pattern).
        self.env_info.OCAMLPATH.append(libd)
        stublibs = os.path.join(libd, "stublibs")
        if os.path.isdir(stublibs):
            self.env_info.CAML_LD_LIBRARY_PATH.append(stublibs)
