#!/usr/bin/env python3
"""Conan recipe for libmarpa 11.0.13 — the Marpa low-level parsing library.

libmarpa is a literate-programming project: the released C sources are
generated from CWEB (.w) files by ctangle, assembled into an Autotools
"stage" tree by etc/copier.pl, and turned into a proper ac_dist tarball by
autoreconf + `make dist`.  This recipe reproduces that upstream chain inside
build() instead of shipping pre-generated sources:

  1. top-level Makefile rules create libmarpa_version.sh + work/etc/LIB_VERSION
  2. dev/*.texi are spliced from their .premenu sources (the sed part of the
     upstream rule; the emacs menu-rewrite part is cosmetic for these inputs)
  3. placeholder doc payloads are created for the stage copier list because
     the OHOS build host has no pdftex/makeinfo/texi2any/texi2html (docs only)
  4. ctangle (tool_requires cweb/4.12.2) runs per work/ subdirectory to
     generate the C sources (dev/, ami/, tavl/, public/, ac/)
  5. perl etc/copier.pl < work/ac/copier.list assembles work/stage/, which
     gets its own git snapshot (upstream's dist-hook runs `git log`), then
     autoreconf + configure + `make dist` produce the ac_dist tarball
  6. the tarball is unpacked and built with the regular Autotools flow,
     including the full upstream `make check` suite

No source patches: upstream's bundled config.sub/config.guess
(2023-09-19) already accept aarch64-linux-ohos.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibmarpaConan(ConanFile):
    name = "libmarpa"
    version = "11.0.13"
    description = "The Marpa low-level parsing library (Earley/Leo algorithm, BNF grammars)"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/jeffreykegler/libmarpa"
    url = ""
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        # No patches: the upstream chain runs unmodified.
        pass

    def build_requirements(self):
        # Host-side generators required by the upstream source/dist chain.
        # Resolved with the build profile; pass -pr:b alongside -pr:h.
        self.tool_requires("cweb/4.12.2")
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libmarpa is only supported on Linux/OHOS, not "
                + str(self.settings.os))
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            # config.sub (2023-09-19) accepts aarch64-linux-ohos natively;
            # pass the triplet explicitly so no host probe runs.
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-ohos",
                "--host=aarch64-unknown-linux-ohos",
            ])
        # Install into the package folder directly (DESTDIR mode is
        # deprecated per R20).  Drop AutotoolsToolchain's literal
        # "${prefix}/lib"-style dir args — the manual configure invocation
        # below does not eval-expand them, so they must not be passed at
        # all; --prefix alone gives the standard layout.
        tc.configure_args = [
            a for a in tc.configure_args
            if not a.startswith(("--prefix=", "--bindir=", "--sbindir=",
                                 "--libdir=", "--includedir=",
                                 "--oldincludedir="))
        ]
        tc.configure_args.append("--prefix=%s" % self.package_folder)
        tc.generate()
        # Remember the toolchain args for the manual ac_dist build (the
        # Autotools helper runs in conanfile folders; the ac_dist tree lives
        # in its own subfolder).
        self._configure_args = list(tc.configure_args)

    def _run(self, command, cwd):
        self.run(command, cwd=cwd, env="conanbuild")

    def _patch_autoconf_hmdfs_umask(self, configure_path):
        """E114: relax the temp-dir umask of a generated Autoconf configure.

        Autoconf's AS_TMPDIR creates the confXXXXXX scratch directory that
        backs `ac_tmp` — the temp machinery config.status writes its scripts
        into — under a restrictive umask (`umask 077` or `umask 000`,
        depending on the Autoconf/m4sh build: plain upstream 2.72 and the
        repository autoconf/2.72 AS_TMPDIR patch emit 077).  On a HarmonyOS
        PC HMDFS build tree (setgid forced on every directory) `umask 077`
        yields drwx--S---, and config.status then fails with "could not
        setup config files machinery" when writing ./confXXXXXX/subs1.awk.
        022 yields drwxr-s--x, which is known good.

        Only the empirically verified AS_TMPDIR layouts are rewritten, each
        with the exact occurrence count its generator emits, and only inside
        the tmp-dir creation block itself; any other layout (or a leftover
        077/000 form) fails closed so the build stops instead of silently
        missing the fix.  A configure already carrying one of the known
        relaxed 022 layouts (e.g. a previous run of this helper) is accepted
        unchanged, so the patch is idempotent.
        """
        with open(configure_path, "r", encoding="utf-8") as f:
            data = f.read()
        original = data

        # Known AS_TMPDIR layouts (name -> {emitted line: expected count})
        # from the Autoconf builds this toolchain uses.
        # Form A: repository autoconf/2.72 with the linux-ohos AS_TMPDIR
        # patch — case block, 3x umask 077 (ohos mkdir, mktemp, mkdir
        # fallback).
        # Form B: plain m4sh — 2x umask 000 (mktemp, mkdir fallback).
        # Form C: plain upstream 2.72 m4sh — 2x umask 077 (mktemp, mkdir
        # fallback); what a stock autoreconf 2.72 emits (the CI worker).
        layouts = (
            ("A: repository autoconf/2.72 AS_TMPDIR patch, 3x umask 077", {
                '(umask 077 && mkdir "$tmp")': 2,
                '(umask 077 && mktemp -d "./confXXXXXX")': 1,
            }),
            ("B: plain m4sh, 2x umask 000", {
                '(umask 000 && mkdir "$tmp")': 1,
                '(umask 000 && mktemp -d "./confXXXXXX")': 1,
            }),
            ("C: plain upstream 2.72 m4sh, 2x umask 077", {
                '(umask 077 && mkdir "$tmp")': 1,
                '(umask 077 && mktemp -d "./confXXXXXX")': 1,
            }),
            # Already-relaxed 022 layouts — what a previous run of this
            # helper leaves behind (or a future Autoconf that emits 022
            # itself); accepted unchanged, making the patch idempotent.
            ("A': already 022 (mkdir x2 + mktemp x1)", {
                '(umask 022 && mkdir "$tmp")': 2,
                '(umask 022 && mktemp -d "./confXXXXXX")': 1,
            }),
            ("B'/C': already 022 (mkdir x1 + mktemp x1)", {
                '(umask 022 && mkdir "$tmp")': 1,
                '(umask 022 && mktemp -d "./confXXXXXX")': 1,
            }),
        )
        total_077 = data.count("umask 077")
        total_000 = data.count("umask 000")

        # Every umask 077/000 must belong to the AS_TMPDIR tmp-dir creation
        # block itself: between the "Create a (secure) tmp directory" marker
        # and the `ac_tmp=$tmp` handoff into config.status's temp machinery.
        # A umask anywhere else is an unknown construct and fails closed —
        # no global replace.
        block_start = data.find("# Create a (secure) tmp directory")
        block_end = (data.find("ac_tmp=$tmp", block_start)
                     if block_start != -1 else -1)
        if block_end <= block_start:
            raise ConanInvalidConfiguration(
                "E114: AS_TMPDIR tmp-dir block not found in generated "
                "configure %s; refusing to run it unpatched on HMDFS"
                % configure_path)
        for needle in ("umask 077", "umask 000"):
            pos = data.find(needle)
            while pos != -1:
                if not block_start < pos < block_end:
                    raise ConanInvalidConfiguration(
                        "E114: %r outside the AS_TMPDIR tmp-dir block in "
                        "%s; refusing to run it unpatched on HMDFS"
                        % (needle, configure_path))
                pos = data.find(needle, pos + 1)
        # Exactly one known layout must be present, with every one of its
        # umask lines matched at the expected count; no match, a partial
        # layout, or several layouts at once fails closed.
        matched = [name for name, expected in layouts
                   if all(data.count(line) == count
                          for line, count in expected.items())]
        if not matched:
            expected_forms = "; ".join(
                "%s (077: %d, 000: %d)" % (
                    name,
                    sum(c for l, c in expected.items() if "077" in l),
                    sum(c for l, c in expected.items() if "000" in l))
                for name, expected in layouts)
            raise ConanInvalidConfiguration(
                "E114: unexpected umask 077/000 occurrence counts in %s "
                "(077: %d, 000: %d); expected one of: %s; refusing to run "
                "it unpatched on HMDFS"
                % (configure_path, total_077, total_000, expected_forms))
        if len(matched) > 1:
            raise ConanInvalidConfiguration(
                "E114: multiple AS_TMPDIR umask layouts matched in %s (%s); "
                "refusing to run it unpatched on HMDFS"
                % (configure_path, ", ".join(matched)))
        # The matched layout must also account for every 077/000 occurrence
        # in the file — a stray extra one is an unknown construct.
        layout = dict(layouts)[matched[0]]
        layout_077 = sum(c for l, c in layout.items() if "077" in l)
        layout_000 = sum(c for l, c in layout.items() if "000" in l)
        if total_077 != layout_077 or total_000 != layout_000:
            raise ConanInvalidConfiguration(
                "E114: stray umask 077/000 beyond the matched layout in %s "
                "(077: %d, 000: %d); refusing to run it unpatched on HMDFS"
                % (configure_path, total_077, total_000))
        for line in layout:
            data = data.replace(line,
                                line.replace("umask 077", "umask 022")
                                    .replace("umask 000", "umask 022"))
        if "umask 077" in data or "umask 000" in data:
            raise ConanInvalidConfiguration(
                "E114: residual umask 077/000 left in %s after rewrite"
                % configure_path)
        if data != original:  # already-022 layouts leave the file untouched
            with open(configure_path, "w", encoding="utf-8") as f:
                f.write(data)

    def _make_texi_from_premenu(self, premenu, texi, premenu_name):
        """Reproduce work/<dir>/Makefile's ``<x>.texi: <x>.premenu`` rule.

        The upstream rule is: sed to splice in a "DO NOT EDIT" header, then
        ``emacs -batch -eval '(texinfo-master-menu 1)'``.  The emacs call only
        rewrites @menu blocks for human reading; the generated-code consumers
        (public/texi2err.pl, texi2event.pl, texi2step.pl, bin/texi2proto.pl)
        read exclusively @deftypevr/@deftypefun/@deftypefn/@strong lines.
        emacs is not available on the OHOS build host, so the recipe runs the
        sed part of the rule byte-for-byte and skips the menu rewrite.
        """
        with open(premenu, "r", encoding="utf-8") as f:
            content = f.read()
        # sed -ne '1,/^@copying/p' | sed -e '$d'  (up to, not including, @copying)
        head = content.split("@copying", 1)[0]
        # sed -ne '/^@copying/,$p'  (from @copying to EOF)
        tail = "@copying" + content.split("@copying", 1)[1]
        with open(texi, "w", encoding="utf-8") as f:
            f.write(head)
            f.write("@c DO NOT EDIT -- This file was created from %s using make\n" % premenu_name)
            f.write("@c The next full make will overwrite any changes made to this file\n")
            f.write("\n")
            f.write(tail)

    def _generate_sources(self):
        """Reproduce the upstream generation chain (top-level ac_dist flow)."""
        src = self.source_folder

        # Step 1: libmarpa_version.sh + work/etc/LIB_VERSION (upstream Makefile
        # rules; pure shell, embeds 11.0.13 from MAJOR/MINOR/MICRO).
        self._run("make libmarpa_version.sh", cwd=src)
        copy(self, "libmarpa_version.sh", src, os.path.join(src, "work", "etc"))
        self._run("sh libmarpa_version.sh version > work/etc/LIB_VERSION", cwd=src)

        # Step 2: dev/api.texi + dev/internal.texi from their .premenu files
        # (make-rule sed part; see _make_texi_from_premenu) — needed by
        # public/ generation (texi2err/texi2event/texi2step read these).
        # NOTE: work/ami/ has its OWN api.texi/internal.texi checked into
        # upstream git (with the friend-API @deftypefun declarations that
        # marpa_ami.h.p50 is built from); they must NOT be overwritten.
        self._make_texi_from_premenu(
            os.path.join(src, "work", "dev", "api.premenu"),
            os.path.join(src, "work", "dev", "api.texi"),
            "api.premenu")
        self._make_texi_from_premenu(
            os.path.join(src, "work", "dev", "internal.premenu"),
            os.path.join(src, "work", "dev", "internal.texi"),
            "internal.premenu")

        # Step 3: doc placeholders, BEFORE make sources.  The build host has
        # no pdftex/makeinfo/texi2any/texi2html, and work/<dir>/Makefile's
        # default `all` target drags in the PDF/texi doc rules.  The stage
        # copier list only needs these payloads to exist; they are
        # documentation-only outputs, never compiled or shipped as code.
        # Content: pointer to the upstream documentation website.
        placeholder = (b"Placeholder for documentation. "
                       b"See https://jeffreykegler.github.io/Marpa-web-site/\n")
        for rel in ("work/dev/marpa.pdf", "work/ami/marpa_ami.pdf",
                    "work/doc1/api.pdf", "work/doc1/api.info"):
            path = os.path.join(src, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(placeholder)

        # Step 4: ctangle the CWEB sources into C.  The upstream
        # work/Makefile `sources` target loops over ac/ami/dev/tavl/public
        # running each subdir's default `all`, but dev/all and ami/all also
        # drag in PDF rules that need cweave+pdftex (unavailable here; their
        # GNU-make for-loop also masks subdir failures).  The C-source
        # generation itself is exactly each subdir's `sources` target (or
        # `all` where it is code-only), so run the subdirs directly.
        for subdir, target in (("dev", "sources"), ("ami", "sources"),
                               ("tavl", "all"), ("public", "all"),
                               ("ac", "all")):
            self._run("(cd %s && make %s)" % (subdir, target),
                      cwd=os.path.join(src, "work"))

        # Step 5: doc outputs of the ac_doc/ac_doc1 copier lists.  The stage
        # copier copies doc/api_html.tar and doc1/api.html verbatim; build
        # them as placeholder payloads (same reason as Step 3).
        api_html_dir = os.path.join(src, "work", "doc", "api.html")
        os.makedirs(api_html_dir, exist_ok=True)
        api_html = ("<html><head><title>libmarpa API</title></head><body>"
                    "<p>Placeholder. Documentation at "
                    "https://jeffreykegler.github.io/Marpa-web-site/</p>"
                    "</body></html>\n")
        with open(os.path.join(api_html_dir, "index.html"), "w",
                  encoding="utf-8") as f:
            f.write(api_html)
        self._run("tar cf doc/api_html.tar -C doc/api.html .",
                  cwd=os.path.join(src, "work"))
        with open(os.path.join(src, "work", "doc1", "api.html"), "w",
                  encoding="utf-8") as f:
            f.write(api_html)

        # Step 6: assemble work/stage per the upstream copier list.
        # (Upstream rule: `perl ../etc/copier.pl --verbose < ac/copier.list`
        # run from work/; etc/ lives at the repo top level.)
        stage = os.path.join(src, "work", "stage")
        os.makedirs(os.path.join(stage, "m4"), exist_ok=True)
        self._run("perl ../etc/copier.pl --verbose < ac/copier.list",
                  cwd=os.path.join(src, "work"))

        # Step 7: autoreconf + configure + `make dist` → the ac_dist tarball.
        # The upstream Makefile.am dist-hook runs `git log -n 5 >> GIT_LOG.txt`
        # inside the stage tree.  Upstream runs this from a git checkout; the
        # Conan build dir is not one, so give the stage tree its own local
        # repo holding exactly the staged snapshot (the appended GIT_LOG.txt
        # then truthfully records the dist snapshot, and no foreign history
        # leaks in).
        self._run("git init -q", cwd=stage)
        self._run("git -c user.name=libmarpa -c user.email=libmarpa@example.org "
                  "add -A -f", cwd=stage)
        self._run("git -c user.name=libmarpa -c user.email=libmarpa@example.org "
                  "commit -q -m 'libmarpa 11.0.13 stage snapshot'", cwd=stage)
        self._run("autoreconf -iv", cwd=stage)
        # E114: the just-generated stage configure creates its confXXXXXX
        # temp dir under `umask 077` (or `umask 000` for the plain upstream
        # m4sh form).  On the HMDFS setgid build tree either form can yield a
        # directory config.status cannot write into.  Relax both to 022 —
        # the only known-good mode on HMDFS — before running it.
        self._patch_autoconf_hmdfs_umask(os.path.join(stage, "configure"))
        # The generated stage configure must not rely on config.guess on
        # HarmonyOS.  Reuse the explicit build/host triplets prepared by
        # AutotoolsToolchain while keeping dist-generation-specific options
        # independent from the final package configure.
        stage_triplets = [
            arg for arg in self._configure_args
            if arg.startswith(("--build=", "--host="))
        ]
        stage_configure = "sh configure"
        if stage_triplets:
            stage_configure += " " + " ".join(stage_triplets)
        self._run(stage_configure, cwd=stage)
        # Automake's ustar probe does not recognize the HarmonyOS host tar
        # implementation, even though normal tar archive creation works.
        # Let Automake construct the canonical dist directory, including the
        # upstream dist-hook, then archive that directory explicitly.
        self._run("make distdir", cwd=stage)

        dist_name = "libmarpa-11.0.13"
        dist_tar = os.path.join(stage, dist_name + ".tar")
        dist_tarball = dist_tar + ".gz"

        self._run(
            'tar cf "%s" "%s"' % (dist_tar, dist_name),
            cwd=stage,
        )
        self._run(
            'gzip -9 -c "%s" > "%s"' % (dist_tar, dist_tarball),
            cwd=stage,
        )
        os.remove(dist_tar)
        return dist_tarball

    def build(self):
        src = self.source_folder
        build = self.build_folder

        dist_tarball = self._generate_sources()

        # Step 8: unpack the ac_dist tarball and run the regular Autotools
        # flow on it, exactly like an upstream release build.
        ac_dir = os.path.join(build, "libmarpa-11.0.13")
        if os.path.isdir(ac_dir):
            shutil.rmtree(ac_dir)
        self.run("tar xzf %s -C %s" % (dist_tarball, build),
                 env="conanbuild")

        # make -j1: E074 (HMDFS jobserver fifo EPERM).
        # The Autotools helper runs in the conanfile build folder, but the
        # ac_dist tree is a subfolder of its own, so drive configure/make
        # manually with the AutotoolsToolchain args (CC/CFLAGS/LD etc. come
        # from the conanbuild env script).
        cfg_args = " ".join(self._configure_args)
        self._run("sh configure %s" % cfg_args, cwd=ac_dir)
        self._run("make -j1", cwd=ac_dir)
        # The full upstream regression suite is part of the build contract:
        # 8 programs / 896 assertions via the C TAP harness.
        self._run("make -j1 check", cwd=ac_dir)

    def package(self):
        ac_dir = os.path.join(self.build_folder, "libmarpa-11.0.13")
        self._run("make install", cwd=ac_dir)

        # Conan 2 copy() has no delete=; remove libtool *.la wrappers manually.
        for _la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)

    def package_info(self):
        self.cpp_info.libs = ["marpa"]
        self.cpp_info.includedirs = ["include"]
        # libmarpa uses -release 11.0.13, so the shared object is
        # lib/libmarpa-11.0.13.so (SONAME) with a libmarpa.so symlink.
        # Upstream does not install a usable pkg-config file.
