#!/usr/bin/env python3
"""Conan recipe — vte 0.74.2 (meson)

vte is a terminal emulator library (libvte-2.91) used by GNOME Terminal.
The upstream source tarball does NOT include a tests/ directory; tests are
inline in src/meson.build (test-modes, test-parser, test-pastify, test-reaper,
test-refptr, test-stream, test-tabstops, test-utf8, test-vtetypes).  These are
run via `meson test` during the conan build's test phase.

Options disabled for OHOS:
  - gtk4: no gtk4 package published to ohpcd
  - icu:  not published to ohpcd (legacy charset support, non-essential)
  - _systemd: libsystemd not published to ohpcd
  - gir:  gobject-introspection not needed
  - vapi: vala bindings not needed
  - glade: glade catalogue not needed
  - gnutls: optional TLS support, disabled to simplify dependency chain
  - fribidi: optional bidirectional text support, disabled
  - a11y: accessibility support, disabled (requires at-spi2)
"""
from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.env import Environment

import os
import glob


class VteConan(ConanFile):
    name = "vte"
    version = "0.74.2"
    description = "Terminal emulator library for GTK+ (libvte-2.91)"
    license = ["LGPL-3.0-or-later", "GPL-3.0-or-later"]
    homepage = "https://gitlab.gnome.org/GNOME/vte"
    url = "https://download.gnome.org/sources/vte/0.74/vte-0.74.2.tar.xz"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Core dependencies (all published to ohpcd)
        # Version pins must match gtk/3.24.43's dependency tree to avoid conflicts
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        self.requires("cairo/1.18.4", transitive_headers=True, transitive_libs=True)
        self.requires("pango/1.50.14.1.1", transitive_headers=True, transitive_libs=True)
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("pcre2/10.45", transitive_headers=True, transitive_libs=True)
        self.requires("zlib/1.3.1.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._fix_pcre2_pc()
        self._inject_glib_tool_variables()
        self._fix_cairo_pc_alignment()
        self._fix_glib_intl_link()
        tc = MesonToolchain(self)
        # vte's meson.build asserts b_ndebug == 'false' (assertions must not be disabled).
        # MesonToolchain defaults b_ndebug to "true" for non-debug builds; override it.
        tc.b_ndebug = "false"
        # musl libc (OHOS) does not provide W_EXITCODE macro used in src/widget.cc:766
        exitcode_def = "W_EXITCODE(stat, sig)=((stat) << 8 | (sig))"
        tc.c_args.append(f"-D{exitcode_def}")
        tc.cpp_args.append(f"-D{exitcode_def}")
        # Disable optional features whose deps are not in ohpcd
        tc.project_options["gtk4"] = "false"
        tc.project_options["icu"] = "false"
        tc.project_options["_systemd"] = "false"
        tc.project_options["gir"] = "false"
        tc.project_options["vapi"] = "false"
        tc.project_options["glade"] = "false"
        tc.project_options["gnutls"] = "false"
        tc.project_options["fribidi"] = "false"
        tc.project_options["a11y"] = "false"
        # Prevent meson from downloading wrap sub-projects
        tc.project_options["wrap_mode"] = "nodownload"
        tc.generate()
        self._inject_meson_archiver()
        self._setup_build_ld_library_path()

    def _fix_cairo_pc_alignment(self):
        """Ensure cairo.pc and cairo-gobject.pc point to the same cairo package.

        Conan may resolve cairo and cairo-gobject to different cairo package
        instances (one built with glib/gobject support, one without). When
        this happens, cairo-gobject.pc points to the package with
        CAIRO_HAS_GOBJECT_FUNCTIONS, but cairo.pc points to a different
        package without that define. The compiler then finds the wrong
        cairo-features.h and fails with:
          error: Cairo was not compiled with support for GObject

        Fix: rewrite cairo.pc to use the same prefix as cairo-gobject.pc.
        """
        gens = self.generators_folder
        cg_path = os.path.join(gens, "cairo-gobject.pc")
        c_path = os.path.join(gens, "cairo.pc")
        if not (os.path.isfile(cg_path) and os.path.isfile(c_path)):
            return
        cg_text = open(cg_path).read()
        c_text = open(c_path).read()
        # Extract prefix from cairo-gobject.pc
        cg_prefix = None
        for line in cg_text.splitlines():
            if line.startswith("prefix="):
                cg_prefix = line.split("=", 1)[1].strip()
                break
        if not cg_prefix:
            return
        # Check if cairo.pc already uses the same prefix
        c_prefix = None
        for line in c_text.splitlines():
            if line.startswith("prefix="):
                c_prefix = line.split("=", 1)[1].strip()
                break
        if c_prefix == cg_prefix:
            return  # Already aligned
        # Rewrite cairo.pc to use the same prefix as cairo-gobject.pc
        new_text = c_text
        # Replace all path references that use ${prefix} — they'll auto-update
        # Just replace the prefix= line
        lines = new_text.splitlines(True)
        for i, line in enumerate(lines):
            if line.startswith("prefix="):
                lines[i] = f"prefix={cg_prefix}\n"
                break
        with open(c_path, "w") as f:
            f.write("".join(lines))

    def _fix_glib_intl_link(self):
        """Add -lintl to glib-2.0.pc Libs to fix undefined symbol errors.

        glib's libglib-2.0.so references g_libintl_bindtextdomain and other
        g_libintl_* symbols from libintl.so (gettext). Conan's PkgConfigDeps
        does not include -lintl in glib-2.0.pc's Libs line, causing linker
        errors:
          ld.lld: error: undefined symbol: g_libintl_bindtextdomain

        This patches glib-2.0.pc to add -lintl to the Libs line, pointing
        at the glib package's lib directory where libintl.so resides.
        """
        gens = self.generators_folder
        glib_pc = os.path.join(gens, "glib-2.0.pc")
        if not os.path.isfile(glib_pc):
            return
        text = open(glib_pc).read()
        if "-lintl" in text:
            return  # Already has -lintl
        # Add -lintl to the Libs line
        lines = text.splitlines(True)
        for i, line in enumerate(lines):
            if line.startswith("Libs:"):
                lines[i] = line.rstrip("\n") + " -lintl\n"
                break
        with open(glib_pc, "w") as f:
            f.write("".join(lines))

    def _setup_build_ld_library_path(self):
        """Set LD_LIBRARY_PATH and PATH for the build scope.

        Meson's GNOME module runs glib-compile-resources, glib-genmarshal,
        glib-mkenums, etc. as custom commands during `ninja`. These binaries
        dynamically link against libgio-2.0.so.0, libglib-2.0.so.0, etc.
        Conan's conanbuildenv only sets PATH to /data/service/hnp/bin (which
        has broken symlinks to system glib tools) and does NOT set
        LD_LIBRARY_PATH. This causes:

          1. glib-compile-resources: "Error loading shared library
             libgio-2.0.so.0" — dynamic linker can't find glib libs
          2. glib-mkenums: "/data/service/hnp/bin/glib-mkenums: No such file
             or directory" — broken symlink on PATH

        Fix: prepend all dependency bindirs (for tool binaries) and libdirs
        (for shared libraries) to PATH and LD_LIBRARY_PATH respectively.
        """
        env = Environment()
        for dep in self.dependencies.values():
            # Prepend bindirs so glib-mkenums, glib-compile-resources, etc.
            # from the Conan glib package are found before broken system
            # symlinks in /data/service/hnp/bin
            for bindir in dep.cpp_info.bindirs:
                env.prepend_path("PATH", bindir)
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
            # Also check component-level dirs
            for component in dep.cpp_info.components.values():
                for bindir in component.bindirs:
                    env.prepend_path("PATH", bindir)
                for libdir in component.libdirs:
                    env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("conanbuild_ld_library_path")

    def _fix_pcre2_pc(self):
        """Create libpcre2-8.pc alias for pcre2.pc.

        Conan's PkgConfigDeps generates pcre2.pc for the top-level cpp_info,
        but vte's meson.build looks for `libpcre2-8` (pkg-config name).
        This creates a forwarding .pc file.
        """
        gens = self.generators_folder
        src = os.path.join(gens, "pcre2.pc")
        dst = os.path.join(gens, "libpcre2-8.pc")
        if os.path.isfile(src) and not os.path.isfile(dst):
            text = open(src).read()
            # Replace the Name: line to match what meson expects
            lines = []
            for line in text.splitlines(True):
                if line.startswith("Name:"):
                    lines.append("Name: libpcre2-8\n")
                elif line.startswith("Description:"):
                    lines.append("Description: PCRE2 8-bit library\n")
                else:
                    lines.append(line)
            with open(dst, "w") as f:
                f.write("".join(lines))

    def _inject_glib_tool_variables(self):
        """Inject missing tool variables into gio-2.0.pc and glib-2.0.pc.

        Meson's GNOME module (_find_tool) queries pkg-config variables to
        locate glib tool binaries:
          - gio-2.0.pc: glib_compile_resources, glib_compile_schemas,
                        gio_querymodules, gdbus_codegen
          - glib-2.0.pc: glib_mkenums, glib_genmarshal

        Conan's PkgConfigDeps does NOT emit these variables, causing:
          ERROR: Could not get pkg-config variable ... for gio-2.0

        This method reads the glib package's bindir from the .pc file's
        prefix/bindir, then appends the tool variables pointing to the
        actual binaries in the glib Conan package.
        """
        gens = self.generators_folder

        # Map: pc_filename -> { variable_name: tool_binary_name }
        tool_map = {
            "gio-2.0.pc": {
                "glib_compile_resources": "glib-compile-resources",
                "glib_compile_schemas": "glib-compile-schemas",
                "gio_querymodules": "gio-querymodules",
                "gdbus_codegen": "gdbus-codegen",
            },
            "glib-2.0.pc": {
                "glib_mkenums": "glib-mkenums",
                "glib_genmarshal": "glib-genmarshal",
            },
        }

        for pc_name, tools in tool_map.items():
            pc_path = os.path.join(gens, pc_name)
            if not os.path.isfile(pc_path):
                continue
            text = open(pc_path).read()
            # Only inject if not already present
            needs_injection = False
            for var_name in tools:
                if f"\n{var_name}=" not in text and f"\n{var_name} =" not in text:
                    needs_injection = True
                    break
            if not needs_injection:
                continue

            # Extract prefix from the .pc file
            prefix = None
            bindir = None
            for line in text.splitlines():
                if line.startswith("prefix="):
                    prefix = line.split("=", 1)[1].strip()
                if line.startswith("bindir="):
                    bindir = line.split("=", 1)[1].strip()
            if not prefix:
                continue
            if not bindir:
                bindir = "${prefix}/bin"

            # Append tool variables
            additions = []
            for var_name, tool_bin in tools.items():
                # Check if variable already exists
                if f"\n{var_name}=" in text or f"\n{var_name} =" in text:
                    continue
                tool_path = f"{bindir}/{tool_bin}"
                additions.append(f"{var_name}={tool_path}")

            if additions:
                # Append before the Name: line (standard .pc layout)
                lines = text.splitlines(True)
                new_lines = []
                injected = False
                for line in lines:
                    if not injected and line.startswith("Name:"):
                        for add in additions:
                            new_lines.append(add + "\n")
                        new_lines.append("\n")
                        injected = True
                    new_lines.append(line)
                if not injected:
                    # Fallback: append at end
                    new_lines.append("\n")
                    for add in additions:
                        new_lines.append(add + "\n")
                with open(pc_path, "w") as f:
                    f.write("".join(new_lines))

    def _inject_meson_archiver(self):
        """Inject ar/ranlib and glib tool paths into meson native file.

        Conan's MesonToolchain doesn't always write ar/ranlib into
        conan_meson_native.ini. Meson then probes for 'llvm-ar' by bare name,
        which may not be on PATH. This injects the full path.

        Additionally, vte's src/vte/meson.build uses find_program('glib-mkenums')
        which searches PATH. On OHOS, /data/service/hnp/bin/glib-mkenums is a
        broken symlink that gets found first. We inject the real glib tool
        paths into the [binaries] section of the meson native file so meson
        finds the correct binaries.
        """
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar, rl = ce.get("ar"), ce.get("ranlib")
        if not ar:
            cc = ce.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                cand = os.path.join(bindir, "llvm-ar")
                if os.path.isfile(cand):
                    ar = cand
                    rlc = os.path.join(bindir, "llvm-ranlib")
                    if os.path.isfile(rlc):
                        rl = rlc
        nf = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(nf):
            return
        with open(nf, encoding="utf-8") as f:
            c = f.read()

        additions = []

        # Inject ar/ranlib if missing
        if ar and "[binaries]" in c and "\nar =" not in c:
            additions.append("ar = '%s'" % ar)
            if rl:
                additions.append("ranlib = '%s'" % rl)

        # Inject glib tool paths to avoid broken symlinks in /data/service/hnp/bin
        glib_bindirs = set()
        for dep in self.dependencies.values():
            for bindir in getattr(dep.cpp_info, "bindirs", []) or []:
                glib_bindirs.add(bindir)
            for component in dep.cpp_info.components.values():
                for bindir in getattr(component, "bindirs", []) or []:
                    glib_bindirs.add(bindir)

        tool_names = [
            "glib-mkenums", "glib-genmarshal", "gdbus-codegen",
            "glib-compile-resources", "glib-compile-schemas",
            "gio-querymodules",
        ]
        for bindir in glib_bindirs:
            for tool_name in tool_names:
                tool_path = os.path.join(bindir, tool_name)
                if os.path.isfile(tool_path):
                    additions.append("%s = '%s'" % (tool_name, tool_path))

        if not additions or "[binaries]" not in c:
            return

        # Insert after [binaries] line
        lines = c.splitlines(True)
        new_lines = []
        inserted = False
        for line in lines:
            new_lines.append(line)
            if not inserted and line.strip() == "[binaries]":
                for add in additions:
                    new_lines.append(add + "\n")
                inserted = True
        if not inserted:
            # No [binaries] section, create one
            new_lines.append("\n[binaries]\n")
            for add in additions:
                new_lines.append(add + "\n")
        with open(nf, "w", encoding="utf-8") as f:
            f.write("".join(new_lines))

    def _sign_glib_tools(self):
        """Sign glib package's ELF tool binaries for HarmonyOS.

        OHOS requires host ELF binaries to carry a valid ``.codesign``
        section before the kernel will exec them (E077/E486).  The glib
        Conan package ships unsigned build-time tools
        (``glib-compile-resources``, ``glib-mkenums``, ``gdbus-codegen``,
        ``glib-genmarshal`` …) in its ``bin/`` directory.  When meson
        invokes these tools during ``vte``'s build the exec fails with::

            /bin/sh: glib-compile-resources: Operation not permitted
            FAILED: [code=126]

        Fix (knowledge E077 four-step, E486 link-interception): for every
        ELF file under the glib package ``bin/`` directory — remove any
        stale ``.codesign`` section, self-sign in place, then restore the
        executable bit (signing zeroes the mode).  Done in ``build()``
        before the first tool invocation, not in ``package()``.
        """
        if self.settings.os != "OHOS":
            return
        try:
            glib_pkg = self.dependencies["glib"]
        except KeyError:
            return
        glib_bin = os.path.join(glib_pkg.package_folder, "bin")
        if not os.path.isdir(glib_bin):
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for name in os.listdir(glib_bin):
            binpath = os.path.join(glib_bin, name)
            if not os.path.isfile(binpath) or os.path.islink(binpath):
                continue
            if not self._is_elf(binpath):
                continue
            # E077 step 1: remove stale .codesign (ignore errors if absent)
            self.run(f'{objcopy} --remove-section .codesign "{binpath}" 2>/dev/null || true')
            # E077 step 3: re-sign in place (self-signed)
            self.run(f'{signer} sign -inFile "{binpath}" -outFile "{binpath}" -selfSign 1 2>/dev/null || true')
            # E077 step 4: signing zeroes permissions — restore +x
            self.run(f'chmod a+x "{binpath}" 2>/dev/null || true')

    def build(self):
        apply_conandata_patches(self)
        self._sign_glib_tools()
        meson = Meson(self)
        meson.configure()
        meson.build()
        # Run upstream tests (meson test) — must pass 100%
        meson.test()

    def package(self):
        Meson(self).install()
        # Remove libtool .la files (they contain hardcoded paths)
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)
        self._sign_binaries()

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        """Sign ELF binaries for HarmonyOS XPM."""
        if self.settings.os != "OHOS":
            return
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for f in targets:
            if os.path.islink(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        self.cpp_info.libs = ["vte-2.91"]
        # vte installs headers to include/vte-2.91/vte/vte.h
        # set includedirs so consumers can #include <vte/vte.h>
        self.cpp_info.includedirs = ["include/vte-2.91"]
        self.cpp_info.set_property("cmake_file_name", "vte")
        self.cpp_info.set_property("cmake_target_name", "vte::vte")
        self.cpp_info.set_property("pkg_config_name", "vte-2.91")
