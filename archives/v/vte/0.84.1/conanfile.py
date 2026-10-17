#!/usr/bin/env python3
"""Conan recipe — vte 0.84.1 (meson)

vte is the terminal emulator library (libvte-2.91-gtk4) used by GNOME
Terminal and other terminal applications. This is the version-follow
bump of the archived vte/0.74.2 recipe onto the 0.84 line (task
#14257): same library API soname family (vte-2.91), gtk4 flavour
(0.74.2 was gtk3).

Upstream 0.84.1 dependency delta vs 0.74.2 (meson.build @ 663-705):
  NEW   liblz4 (>= r1.9.4)     — scrollback compression
  NEW   simdutf (>= 6.2.0)     — provided by subprojects/simdutf.wrap
                                 (wrap-git v8.2.0) — OHOS build host
                                 has no network for wrapdb; the conan
                                 package simdutf/6.0.3 does NOT satisfy
                                 the >= 6.2.0 requirement, so the wrap
                                 subproject is vendored from the
                                 release tarball's subprojects/ dir
                                 (already present, no download needed
                                 with wrap_mode=forcefallback... but the
                                 wrap is wrap-git which still wants the
                                 network — see patch 0001: swap the
                                 wrap-git for the bundled tarball copy
                                 shipped in the release archive OR pin
                                 conan simdutf if version suffices).
  NEW   fmt (header-only)      — allow_fallback: false; optional system
                                 dep first, subproject fmt.wrap fallback.
                                 conan fmt/9.1.0 satisfies (fmt_sysdep
                                 found → header-only mode, no subproject
                                 download).
  cairo/glib/gobject/gio/pango/pcre2 — same as 0.74.2.

Options for the OHOS build (0.74.2 precedent):
  gtk4=true  (the point of this bump)
  gtk3=false (superseded line)
  gir/vapi/docs/glade/gnutls/icu/_systemd/a11y/fribidi=false
  app=false  (vte application; the tool binaries are installed via
              commands.json from the library build only if produced)
  terminfo=true (terminfo data ships with the library payload)

The pcre2 alias .pc forwarding (libpcre2-8), glib tool variable
injection, meson native [binaries] pinning and W_EXITCODE musl macro
patch all carry over from the 0.74.2 recipe.
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


class VteConan(ConanFile):
    name = "vte"
    version = "0.84.1"
    description = "Terminal emulator library for GTK4 (libvte-2.91-gtk4)"
    license = ["LGPL-3.0-or-later", "GPL-3.0-or-later"]
    homepage = "https://gitlab.gnome.org/GNOME/vte"
    url = "https://download.gnome.org/sources/vte/0.84/vte-0.84.1.tar.xz"

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
        # gtk4 flavour: match gtk4/4.22.4's dependency tree
        self.requires("gtk4/4.22.4", transitive_headers=True, transitive_libs=True)
        self.requires("cairo/1.18.4", transitive_headers=True, transitive_libs=True)
        self.requires("cairo-gobject/1.18.4", transitive_headers=True, transitive_libs=True)
        self.requires("pango/1.56.4", transitive_headers=True, transitive_libs=True)
        self.requires("glib/2.84.0.1.1", transitive_headers=True, transitive_libs=True, override=True)
        self.requires("pcre2/10.45", transitive_headers=True, transitive_libs=True)
        self.requires("zlib/1.3.1.1", transitive_headers=True, transitive_libs=True)
        self.requires("lz4/1.10.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("fmt/9.1.0", transitive_headers=True, transitive_libs=True)
        # simdutf: the release tarball vendors the FULL simdutf 8.2.0
        # source (subprojects/simdutf/ with its own meson.build, added by
        # the wrap patch_directory) — meson's subproject fallback builds
        # it from the vendored tree with NO network access. The conan
        # registry's simdutf/6.0.3 is below the required >= 6.2.0, so
        # the vendored subproject is the correct dependency source.

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._re_sign_glib_tools()
        self._fix_cairo_pc_alignment()
        self._fix_pcre2_pc()
        self._fix_lz4_pc()
        self._inject_glib_tool_variables()
        self._fix_glib_intl_link()

        tc = MesonToolchain(self)
        # vte's meson.build asserts b_ndebug == 'false'
        tc.b_ndebug = "false"
        # musl libc (OHOS) does not provide W_EXITCODE
        exitcode_def = "W_EXITCODE(stat, sig)=((stat) << 8 | (sig))"
        tc.c_args.append(f"-D{exitcode_def}")
        tc.cpp_args.append(f"-D{exitcode_def}")
        tc.project_options["gtk4"] = "true"
        tc.project_options["gtk3"] = "false"
        tc.project_options["icu"] = "false"
        tc.project_options["_systemd"] = "false"
        tc.project_options["gir"] = "false"
        tc.project_options["vapi"] = "false"
        tc.project_options["docs"] = "false"
        tc.project_options["glade"] = "false"
        tc.project_options["gnutls"] = "false"
        tc.project_options["fribidi"] = "false"
        tc.project_options["a11y"] = "false"
        tc.project_options["app"] = "false"
        tc.project_options["terminfo"] = "true"
        tc.project_options["wrap_mode"] = "nodownload"
        tc.generate()
        self._inject_meson_archiver()
        self._setup_build_ld_library_path()

    # ── the following helpers are carried over verbatim from the
    #    vte/0.74.2 recipe (proven on OHOS CI); see that recipe for
    #    the detailed rationale of each patch-up.

    def _fix_glib_intl_link(self):
        gens = self.generators_folder
        glib_pc = os.path.join(gens, "glib-2.0.pc")
        if not os.path.isfile(glib_pc):
            return
        text = open(glib_pc).read()
        if "-lintl" in text:
            return
        lines = text.splitlines(True)
        for i, line in enumerate(lines):
            if line.startswith("Libs:"):
                lines[i] = line.rstrip("\n") + " -lintl\n"
                break
        with open(glib_pc, "w") as f:
            f.write("".join(lines))

    def _re_sign_glib_tools(self):
        """Re-sign the glib package's ELF bin tools in place.

        R85/R86 fix, carried over from the gtk4/4.22.4 recipe (proven on
        OHOS CI): the registry's glib package ships its build-time bin
        tools (glib-compile-resources / glib-compile-schemas /
        gio-querymodules / gobject-query, …) as OHOS aarch64 ELF
        executables whose linker-time .codesign section is stale — OHOS
        XPM exec rejects them with "Operation not permitted" (ninja
        FAILED [code=126] at src/vteresources*.c/h). Re-sign them in
        place with binary-sign-tool so meson's gnome.compile_resources /
        compile_schemas custom commands can run. (glib-mkenums /
        glib-genmarshal / gdbus-codegen are shebang scripts — left
        alone.) The tools also have no RPATH, so glib's own lib dir goes
        onto LD_LIBRARY_PATH for the exec.
        Verified locally (task #14257 CI reds #65549/#66114/#66132:
        three different workers, same 126):
          before: "operation not permitted"
          after re-sign: glib-compile-resources --version -> 2.84.0
        """
        if not getattr(self, "dependencies", None):
            return
        g = None
        for ref, dep in self.dependencies.items():
            if ref.ref and ref.ref.name == "glib":
                g = dep
                break
        if not g or not getattr(g, "package_folder", None):
            return
        gbin = os.path.join(g.package_folder, "bin")
        glib_lib = os.path.join(g.package_folder, "lib")
        if not os.path.isdir(gbin):
            return
        if os.path.isdir(glib_lib):
            os.environ["LD_LIBRARY_PATH"] = (
                glib_lib + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
            )
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for tool in os.listdir(gbin):
            tp = os.path.join(gbin, tool)
            if not os.path.isfile(tp):
                continue
            with open(tp, "rb") as f:
                magic = f.read(4)
            if magic[:4] != b"\x7fELF":
                continue  # shebang scripts (glib-mkenums, …) — leave alone
            try:
                self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=tp))
                self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1 2>/dev/null || true'.format(sg=signer, f=tp))
                self.output.info("re-signed glib bin tool: %s" % tp)
            except Exception as e:  # pragma: no cover — non-blocking
                self.output.warning("re-sign %s failed: %s" % (tp, e))

    def _setup_build_ld_library_path(self):
        env = Environment()
        for dep in self.dependencies.values():
            for bindir in dep.cpp_info.bindirs:
                env.prepend_path("PATH", bindir)
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
            for component in dep.cpp_info.components.values():
                for bindir in component.bindirs:
                    env.prepend_path("PATH", bindir)
                for libdir in component.libdirs:
                    env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.vars(self, scope="build").save_script("conanbuild_ld_library_path")

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
        (Carried over verbatim from the vte/0.74.2 recipe, proven on OHOS CI.)
        """
        gens = self.generators_folder
        cg_path = os.path.join(gens, "cairo-gobject.pc")
        c_path = os.path.join(gens, "cairo.pc")
        if not (os.path.isfile(cg_path) and os.path.isfile(c_path)):
            return
        cg_text = open(cg_path).read()
        c_text = open(c_path).read()
        cg_prefix = None
        for line in cg_text.splitlines():
            if line.startswith("prefix="):
                cg_prefix = line.split("=", 1)[1].strip()
                break
        if not cg_prefix:
            return
        c_prefix = None
        for line in c_text.splitlines():
            if line.startswith("prefix="):
                c_prefix = line.split("=", 1)[1].strip()
                break
        if c_prefix == cg_prefix:
            return  # Already aligned
        lines = c_text.splitlines(True)
        for i, line in enumerate(lines):
            if line.startswith("prefix="):
                lines[i] = f"prefix={cg_prefix}\n"
                break
        with open(c_path, "w") as f:
            f.write("".join(lines))

    def _fix_pcre2_pc(self):
        gens = self.generators_folder
        src = os.path.join(gens, "pcre2.pc")
        dst = os.path.join(gens, "libpcre2-8.pc")
        if os.path.isfile(src) and not os.path.isfile(dst):
            text = open(src).read()
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

    def _fix_lz4_pc(self):
        # vte's meson.build looks up dependency('liblz4'); conan's lz4 package
        # ships lz4.pc — same pc-name mismatch as libpcre2-8 above.
        gens = self.generators_folder
        src = os.path.join(gens, "lz4.pc")
        dst = os.path.join(gens, "liblz4.pc")
        if os.path.isfile(src) and not os.path.isfile(dst):
            text = open(src).read()
            lines = []
            for line in text.splitlines(True):
                if line.startswith("Name:"):
                    lines.append("Name: liblz4\n")
                elif line.startswith("Description:"):
                    lines.append("Description: LZ4 compression library\n")
                else:
                    lines.append(line)
            with open(dst, "w") as f:
                f.write("".join(lines))

    def _inject_glib_tool_variables(self):
        gens = self.generators_folder
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
            needs_injection = False
            for var_name in tools:
                if f"\n{var_name}=" not in text and f"\n{var_name} =" not in text:
                    needs_injection = True
                    break
            if not needs_injection:
                continue
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
            additions = []
            for var_name, tool_bin in tools.items():
                if f"\n{var_name}=" in text or f"\n{var_name} =" in text:
                    continue
                additions.append(f"{var_name}={bindir}/{tool_bin}")
            if additions:
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
                    new_lines.append("\n")
                    for add in additions:
                        new_lines.append(add + "\n")
                with open(pc_path, "w") as f:
                    f.write("".join(new_lines))

    def _inject_meson_archiver(self):
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
        if ar and "[binaries]" in c and "\nar =" not in c:
            additions.append("ar = '%s'" % ar)
            if rl:
                additions.append("ranlib = '%s'" % rl)
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
        injected_tools = set()
        for bindir in glib_bindirs:
            for tool_name in tool_names:
                # 新版 glib 配方已由 MesonToolchain 自动声明工具；且依赖图里可能存在多个 glib 包目录
                # （host 上下文+build 上下文各一）——两路都会撞键，必须双重去重
                if "\n%s =" % tool_name in c or "\n%s=" % tool_name in c:
                    continue
                if tool_name in injected_tools:
                    continue
                tool_path = os.path.join(bindir, tool_name)
                if os.path.isfile(tool_path):
                    additions.append("%s = '%s'" % (tool_name, tool_path))
                    injected_tools.add(tool_name)
        if not additions or "[binaries]" not in c:
            return
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
            new_lines.append("\n[binaries]\n")
            for add in additions:
                new_lines.append(add + "\n")
        with open(nf, "w", encoding="utf-8") as f:
            f.write("".join(new_lines))

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # Upstream tests (meson test) for cross-built binaries cannot
        # run on the build host through meson; the pure-parser subset
        # is executed directly below (R30: run what the platform can
        # run, report the rest — no PTY environment on the build host).
        self._run_parser_tests()

    def _run_parser_tests(self):
        import shlex
        libdirs = [os.path.join(self.build_folder, "src", ".libs")]
        for _r, _d in self.dependencies.items():
            _base = getattr(_d, "package_folder", None) or ""
            for _p in (_d.cpp_info.libdirs or []):
                if not os.path.isabs(_p) and _base:
                    _p = os.path.join(_base, _p)
                if _p not in libdirs:
                    libdirs.append(_p)
        ldpath = os.pathsep.join(libdirs + ["/system/lib64"])
        tdir = self.build_folder
        runnable = []
        # All no-pty / no-display unit tests (13 with gtk4=true,
        # gtk3=false): verified rc=0 locally on OHOS. test-reaper (needs
        # a pty) and test-minifont-gtk4 (needs a broadway display) are
        # environment-sensitive — verified locally by direct exec, kept
        # out of the CI hard-gate run and documented in notes.md.
        # test-vtetypes/test-minifont-gtk3 are gtk3-only (not built).
        for cand in ("test-parser", "test-modes", "test-tabstops", "test-utf8",
                     "test-refptr", "test-stream", "test-pastify",
                     "test-base16", "test-colors", "test-color-lightness",
                     "test-properties", "test-uuid", "test-unicode-width"):
            exe = os.path.join(tdir, "src", cand)
            if os.path.isfile(exe):
                runnable.append(exe)
        if not runnable:
            # meson 0.84 layout: tests live under builddir/src
            for root, _, files in os.walk(self.build_folder):
                for cand in files:
                    if cand.startswith("test-") and "." not in cand:
                        runnable.append(os.path.join(root, cand))
        for exe in runnable:
            self.run(
                'bash -c \'export LD_LIBRARY_PATH="{ld}"; "{exe}"\''.format(
                    ld=ldpath, exe=shlex.quote(exe)),
                env="conanbuild",
            )

    def package(self):
        Meson(self).install()
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)
        self._sign_binaries()

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
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
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1 2>/dev/null || true'.format(sg=signer, f=f))

    def package_info(self):
        # 0.84 gtk4 flavour: library is libvte-2.91-gtk4.so
        self.cpp_info.libs = ["vte-2.91-gtk4"]
        self.cpp_info.includedirs = ["include/vte-2.91-gtk4"]
        self.cpp_info.set_property("cmake_file_name", "vte-gtk4")
        self.cpp_info.set_property("cmake_target_name", "vte-gtk4::vte-gtk4")
        self.cpp_info.set_property("pkg_config_name", "vte-2.91-gtk4")
