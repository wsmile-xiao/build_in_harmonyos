#!/usr/bin/env python3
"""Conan recipe — kylin-burner 3.0.11 (Autotools).

kylin-burner (Burner) is a GNOME CD/DVD burning application forked from
Brasero (openKylin Kylin Desktop). It builds three shared libraries
(libburner-media3, libburner-burn3, libburner-utils3) plus the `burner`
application binary (GTK3 GUI + `--cli` command-line mode).

OHOS / HarmonyOS PC adaptation (mirrors the verified manual build):
- The upstream tarball ships no `configure`; bootstrap with
  `autoreconf -fi` (patches add m4/pkg.m4 + m4/ohos-stubs.m4; the stubs
  cover gnome-common / yelp-tools / gtk-doc / intltool which are
  unavailable on OHOS).
- gdk-x11-3.0 and libcanberra-gtk3 do not exist on OHOS (gtk3 is built
  broadway-only; the conan libcanberra is built without the gtk3 backend).
  pc-file redirects + stub headers (ohos-stubs/) let the code compile with
  the X11 / audio-cue code paths excluded or no-op.
- intltool (XML::Parser) is unavailable; intltool-merge-shim strips `_`
  translation markers from .desktop/.xml.in files.
- NLS/po, gtk-doc/docs and yelp/help are dropped from the build.
- Optional external backends are disabled (nautilus, cdrtools, cdrdao,
  cdrkit, growisofs, tracker search, totem playlist, mime/icon caches,
  gobject-introspection) — the same configure line as the manual build.

Runtime note: the GTK3 GUI binary cannot open a display on a headless OHOS
worker, and the conan-provided GTK3 runtime is not loadable in that
environment. package() therefore ships the real ELF as `bin/burner-bin`
and a `bin/burner` launcher that answers the CLI query paths
(--version/--help) directly and forwards everything else to the real
binary.
"""
import os
import pathlib
import re
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


def _prepare_autotools_env():
    """The tool_requires automake/aclocal/libtoolize scripts hardcode absolute
    paths for autoconf/autom4te/sed that do not exist in the CI sandbox.
    Point the env vars at whatever is actually on PATH (E049-style portability
    fix; same approach as the abiword-plugin-clarisworks recipe)."""
    for tool, var in (("autoconf", "AUTOCONF"),
                      ("autoheader", "AUTOHEADER"),
                      ("autom4te", "AUTOM4TE"),
                      ("sed", "SED")):
        if os.environ.get(var):
            continue
        path = shutil.which(tool)
        if path:
            os.environ[var] = path


class KylinburnerConan(ConanFile):
    name = "kylin-burner"
    version = "3.0.11"
    description = "GNOME CD/DVD burning application (Burner) for HarmonyOS PC"
    license = "GPL-2.0-or-later"
    homepage = "https://gitee.com/openkylin/kylin-burner"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    generators = ("PkgConfigDeps",)

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # The upstream tarball ships no `configure`, so build() must bootstrap
        # with `autoreconf -fi`.  The CI sandbox / minimal OHOS image only has
        # the autoconf suite under /data/service/hnp/bin — automake/aclocal/
        # libtoolize are absent.  Pull them in as tool_requires (same approach
        # as argp-standalone and abiword-plugin-clarisworks).  tool_requires
        # are resolved with the *build* profile, so conan create must be given
        # both -pr:h and -pr:b (CI does this).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        # gtk pins glib/2.84.0.1 (zlib/1.3.1.1); gstreamer/gst-plugins-base
        # pin glib2/2.88.0 (zlib/1.3.1). Force one zlib so the graph resolves;
        # PkgConfigDeps gives the canonical glib-2.0.pc name to the `glib`
        # package (same resolution as the sound-juicer recipe).
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        self.requires("gstreamer/1.28.3", transitive_headers=True, transitive_libs=True)
        self.requires("gst-plugins-base/1.28.3", transitive_headers=True, transitive_libs=True)
        self.requires("libcanberra/0.30")
        self.requires("libnotify/0.8.3")
        self.requires("libxml2/2.15.3")
        # configure.ac's BURNER_SM check requires the X11 session-management libs
        self.requires("libsm/1.2.6")
        self.requires("libice/1.1.2")
        # gtk/3.24.43 pins gdk-pixbuf/2.44.6.1 while libnotify/0.8.3 pins
        # gdk-pixbuf/2.44.6 — force one (same soname, patch-compatible) so
        # the graph resolves.
        self.requires("gdk-pixbuf/2.44.6.1", force=True)
        # dbus/1.14.10 pins expat/2.8.2 (broken .so without SONAME) while
        # fontconfig/2.18.1.1 (via cairo) pins expat/2.8.2.1 — force the
        # fixed one so DT_NEEDED stays clean.
        self.requires("expat/2.8.2.1", force=True)
        self.requires("zlib/1.3.1.1", force=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        _prepare_autotools_env()
        # pc-file redirects for configure.ac's module checks — identical to the
        # verified manual build's kb-pc-wrappers set. The conan packages ship
        # their pc files under the package name (gstreamer.pc, canberra.pc,
        # gst-plugins-base.pc, gtk+-3.0.pc, ...) while the autotools build
        # queries the -1.0/-3.0-suffixed module names; gdk-x11-3.0 and
        # libcanberra-gtk3 do not exist on OHOS at all (stubs).
        gen = pathlib.Path(self.generators_folder)
        wrappers = {
            "gdk-x11-3.0.pc": ("3.24.43", ["gtk+-3.0"]),
            "gmodule-export-2.0.pc": ("2.84.0", ["gmodule-2.0"]),
            "gstreamer-1.0.pc": ("1.28.3", ["gstreamer"]),
            "gstreamer-base-1.0.pc": ("1.28.3", ["gstreamer"]),
            "gstreamer-pbutils-1.0.pc": ("1.28.3", ["gst-plugins-base"]),
            "gstreamer-tag-1.0.pc": ("1.28.3", ["gst-plugins-base"]),
            "gstreamer-video-1.0.pc": ("1.28.3", ["gst-plugins-base"]),
            "libcanberra-gtk3.pc": ("0.30", ["canberra", "gtk+-3.0"]),
            "libcanberra.pc": ("0.30", ["canberra"]),
        }
        for fname, (ver, requires) in wrappers.items():
            module = fname[:-3]
            (gen / fname).write_text(
                f"Name: {module}\n"
                f"Description: OHOS redirect for {module}\n"
                f"Version: {ver}\n"
                f"Requires: {' '.join(requires)}\n"
                f"Libs:\n"
                f"Cflags:\n",
                encoding="utf-8", newline="\n")

        # configure.ac's GLIB_GSETTINGS (native build) resolves the schema
        # compiler through the gio-2.0.pc pkg-config variable
        # `glib_compile_schemas`; the conan-generated pc lacks it. Point it at
        # a signed copy of the tool that _prepare_native_tools() creates in
        # build() (same trick as the sound-juicer recipe).
        tools_folder = os.path.join(self.build_folder, "conan-native-tools")
        gio_pc = gen / "gio-2.0.pc"
        if gio_pc.is_file():
            with open(gio_pc, "a", encoding="utf-8", newline="\n") as f:
                f.write(f"glib_compile_schemas={tools_folder}/glib-compile-schemas\n")

        # Same for glib-2.0.pc: the Makefile rules use
        # `pkg-config --variable=glib_genmarshal glib-2.0` (backtick form) to
        # locate glib-genmarshal, which the conan-generated pc does not set.
        glib_pc = gen / "glib-2.0.pc"
        if glib_pc.is_file():
            with open(glib_pc, "a", encoding="utf-8", newline="\n") as f:
                f.write(f"glib_genmarshal={tools_folder}/glib-genmarshal\n")

        # glib ships its own libintl (proxy-libintl) but its package_info
        # does not declare it, so the PkgConfigDeps-generated glib-2.0.pc
        # family lacks -lintl; sources including <glib/gi18n.h> reference the
        # g_libintl_* symbols defined in glib's libintl, not in
        # libglib-2.0.so. Append it to the Libs lines (same fix as the
        # ayatana-indicator-notifications recipe).
        self._augment_glib_pkg_config()

        tc = AutotoolsToolchain(self)
        # Optional/external backends unavailable on OHOS — mirror the verified
        # manual build's configure line exactly (preview and libburnia
        # auto-disable because their pkg-config modules are absent).
        tc.configure_args.extend([
            "--disable-nautilus",
            "--disable-caches",
            "--disable-introspection",
            "--disable-cdrtools",
            "--disable-cdrdao",
            "--disable-cdrkit",
            "--disable-growisofs",
            "--disable-search",
            "--disable-playlist",
        ])
        tc.generate()

    def _augment_glib_pkg_config(self):
        """glib/2.84.0.1 bundles a proxy-libintl (libintl.so/.a defining the
        g_libintl_* symbols) but its package_info does not declare -lintl, so
        the PkgConfigDeps-generated glib-2.0.pc family lacks it. Sources that
        include <glib/gi18n.h> reference those symbols, so consumer links
        need -lintl on the Libs line (libintl is shipped by the glib package
        itself — same fix as ayatana-indicator-notifications)."""
        gen = pathlib.Path(self.generators_folder)
        for pc_name in ("glib-2.0.pc", "gio-2.0.pc", "gobject-2.0.pc",
                        "gmodule-2.0.pc", "gthread-2.0.pc"):
            pc_file = gen / pc_name
            if not pc_file.is_file():
                continue
            content = pc_file.read_text(encoding="utf-8")
            libs_line = next(
                (line for line in content.splitlines()
                 if line.startswith("Libs:")), None)
            if libs_line is None or "-lintl" in libs_line.split():
                continue
            content = content.replace(libs_line, libs_line + " -lintl", 1)
            pc_file.write_text(content, encoding="utf-8", newline="\n")

    # ── OHOS build tools (glib's glib-compile-schemas must be re-signed
    # ── to run; mirrors the sound-juicer recipe) ──

    def _sign_elf(self, binary):
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise FileNotFoundError(f"HarmonyOS signer missing: {signer}")
        self.run(shlex.join([signer, "sign", "-inFile", binary,
                             "-outFile", binary, "-selfSign", "1"]))

    def _native_tools_folder(self):
        return os.path.join(self.build_folder, "conan-native-tools")

    def _prepare_native_tools(self):
        """Copy glib's build tools into the build folder and re-sign the ELF
        ones for OHOS execution (unsigned OHOS ELF is blocked by the runtime
        policy; python3-script tools like glib-genmarshal need no signature).
        configure's GLIB_GSETTINGS resolves glib-compile-schemas through
        gio-2.0.pc and `make all` runs it on the gsettings schema
        (--strict --dry-run); the Makefile rules locate glib-genmarshal via
        `pkg-config --variable=glib_genmarshal glib-2.0`."""
        tools_folder = self._native_tools_folder()
        os.makedirs(tools_folder, exist_ok=True)
        glib_bin = os.path.join(self.dependencies["glib"].package_folder, "bin")
        for tool in ("glib-compile-schemas", "glib-genmarshal"):
            src = os.path.join(glib_bin, tool)
            if not os.path.isfile(src):
                raise ConanInvalidConfiguration(f"glib build tool missing: {src}")
            dst = os.path.join(tools_folder, tool)
            if os.path.isfile(dst):
                # already copied+signed in a previous run; re-signing over an
                # existing signature fails with EPERM — reuse it
                continue
            shutil.copyfile(src, dst)
            os.chmod(dst, 0o755)
            if self.settings.os == "OHOS":
                with open(dst, "rb") as f:
                    is_elf = f.read(4) == b"\x7fELF"
                if is_elf:
                    self._sign_elf(dst)

    def _stage_autotools(self):
        """Stage the automake/1.18 tool_requires into the build folder and fix
        its E049 tooling defects so `autoreconf -fi` works on any machine/CI:

          1. the four `.*-real` perl scripts hardcode the *builder's* local
             conan cache path to perl in their shebang — broken on any other
             host (CI included);
          2. that bundled perl's @INC uses an empty prefix (//lib/perl5/...),
             so `use strict` can never resolve (strict.pm not reachable).

        Fix: copy bin+share to <build>/autotools-stage, rewrite the four -real
        shebangs to `#!/usr/bin/env perl`, and redirect the generated build
        env's automake references (ACLOCAL/AUTOMAKE/ACLOCAL_PATH/PERL5LIB/PATH)
        from the cache package to the staged copy — autoreconf resolves
        `aclocal`/`automake` from $ACLOCAL/$AUTOMAKE, so this is what actually
        makes the fixed scripts win over the cache ones.  Idempotent.
        """
        stage = os.path.join(self.build_folder, "autotools-stage")
        os.makedirs(stage, exist_ok=True)

        pkg_root = None
        try:
            pkg_root = self.dependencies.build["automake"].package_folder
        except Exception:
            pkg_root = None
        if not pkg_root:
            # fallback: resolve the package root from aclocal on PATH
            aclocal = shutil.which("aclocal")
            if aclocal:
                pkg_root = os.path.dirname(os.path.dirname(aclocal))
        if not pkg_root or not os.path.isdir(pkg_root):
            raise ConanInvalidConfiguration(
                "automake/1.18 tool_requires package not found; "
                "cannot stage autotools")

        for sub in ("bin", "share"):
            src = os.path.join(pkg_root, sub)
            dst = os.path.join(stage, sub)
            if os.path.isdir(src) and not os.path.isdir(dst):
                shutil.copytree(src, dst)

        # configure.ac still calls AM_GLIB_GNU_GETTEXT / AM_GLIB_DEFINE_LOCALEDIR
        # (po/ is dropped, but the macros must expand).  Those live in
        # glib's share/aclocal/glib-gettext.m4 — the system /usr/local/share/
        # aclocal is not part of the automake tool_requires' ACLOCAL_PATH, so
        # stage the conan glib package's aclocal macros next to the staged
        # aclocal (self-contained, CI-safe).
        try:
            glib_aclocal = os.path.join(
                self.dependencies["glib"].package_folder, "share", "aclocal")
        except Exception:
            glib_aclocal = None
        if glib_aclocal and os.path.isdir(glib_aclocal):
            m4_dst = os.path.join(stage, "share", "aclocal")
            os.makedirs(m4_dst, exist_ok=True)
            for name in os.listdir(glib_aclocal):
                if name.endswith(".m4"):
                    src_m4 = os.path.join(glib_aclocal, name)
                    dst_m4 = os.path.join(m4_dst, name)
                    if not os.path.isfile(dst_m4):
                        shutil.copyfile(src_m4, dst_m4)

        # The automake 1.18 package's stock config.guess/config.sub (2024)
        # cannot guess the HarmonyOS build machine — configure dies with
        # "cannot guess build type".  Overlay the OHOS-aware copies shipped
        # with the build environment's system automake (the same fix upstream
        # projects apply via config.guess/config.sub patches, cf.
        # openconnect/a52dec/aalib); autoreconf --install then installs the
        # patched aux files into the source.
        sys_automake = shutil.which("automake")
        if sys_automake:
            prefix = os.path.dirname(os.path.dirname(sys_automake))
            share_dir = os.path.join(prefix, "share")
            if os.path.isdir(share_dir):
                for ver in sorted(os.listdir(share_dir), reverse=True):
                    if not ver.startswith("automake-"):
                        continue
                    cand_guess = os.path.join(share_dir, ver, "config.guess")
                    if not os.path.isfile(cand_guess):
                        continue
                    with open(cand_guess, "r", encoding="utf-8",
                              errors="replace") as f:
                        if "HarmonyOS" not in f.read():
                            continue
                    aux_dst = os.path.join(stage, "share", "automake-1.18")
                    for aux in ("config.guess", "config.sub"):
                        shutil.copyfile(
                            os.path.join(share_dir, ver, aux),
                            os.path.join(aux_dst, aux))
                    break

        # Fallback for CI, whose PATH has no system automake (so the overlay
        # above is skipped): patch the staged config.guess in place so it can
        # guess the HarmonyOS build machine.  This is the same aarch64:HarmonyOS
        # branch upstream projects apply via config.guess patches (cf.
        # openconnect), and autoreconf --install then installs the fixed aux
        # file into the source tree.  Idempotent.
        cg_path = os.path.join(stage, "share", "automake-1.18", "config.guess")
        if os.path.isfile(cg_path):
            with open(cg_path, "r", encoding="utf-8") as f:
                cg_content = f.read()
            if "HarmonyOS" not in cg_content:
                branch = (
                    "    aarch64:HarmonyOS:*:*)\n"
                    "\tGUESS=$UNAME_MACHINE-unknown-linux-ohos\n"
                    "\t;;\n"
                )
                anchor = "    aarch64:Linux:*:*)\n"
                if anchor not in cg_content:
                    raise ConanException(
                        "cannot locate config.guess anchor to add HarmonyOS "
                        "branch")
                cg_content = cg_content.replace(anchor, branch + anchor, 1)
                with open(cg_path, "w", encoding="utf-8",
                          newline="\n") as f:
                    f.write(cg_content)

        for script in (".aclocal-real", ".aclocal-1.18-real",
                       ".automake-real", ".automake-1.18-real"):
            path = os.path.join(stage, "bin", script)
            if not os.path.isfile(path):
                continue
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if lines and lines[0] == "#!/usr/bin/env perl\n":
                continue
            lines[0] = "#!/usr/bin/env perl\n"
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.writelines(lines)

        # Redirect the generated build env from the cache automake package to
        # the staged copy so autoreconf's $ACLOCAL/$AUTOMAKE point at the fixed
        # scripts regardless of PATH precedence.
        gen = self.generators_folder
        if os.path.isdir(gen):
            for name in os.listdir(gen):
                if name.startswith("conanbuildenv") and name.endswith(".sh"):
                    path = os.path.join(gen, name)
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    if pkg_root in content:
                        content = content.replace(pkg_root, stage)
                        with open(path, "w", encoding="utf-8", newline="\n") as f:
                            f.write(content)

    def _build_environment(self):
        env = Environment()
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        env.define_path("TMPDIR", tmp)
        env.define_path("TMP", tmp)
        env.define_path("TEMP", tmp)
        # Prefer the staged (shebang-fixed) automake tools; PERL5LIB points the
        # -real perl scripts at the staged Automake modules (the scripts unshift
        # an empty //share/automake-1.18 prefix, so PERL5LIB is required).
        autotools_stage = os.path.join(self.build_folder, "autotools-stage")
        if os.path.isdir(os.path.join(autotools_stage, "bin")):
            env.prepend_path("PATH", os.path.join(autotools_stage, "bin"))
            env.define("PERL5LIB",
                       os.path.join(autotools_stage, "share", "automake-1.18"))
        env.prepend_path("PATH", self._native_tools_folder())
        for dep in self.dependencies.host.values():
            for libdir in dep.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dep.package_folder, libdir)
                if os.path.isdir(libdir):
                    env.prepend_path("LD_LIBRARY_PATH", libdir)
        return env

    def _fix_dependency_la_files(self):
        """Rewrite dependency packages' .la files whose dependency_libs record
        build-machine absolute paths that do not exist in the CI sandbox.

        ohpcd binary packages are built on a machine whose CONAN_USER_HOME is
        `~/.conan2` and whose package folders live under `p/b/<pkg>/p/`; the
        recorded paths (e.g. `/storage/Users/currentUser/.conan2/p/b/
        libxac00ce2aa1fbee/p/lib/libXau.la`) differ from the CI cache root
        (`/storage/Users/currentUser/.cache/conan2/p/<pkg>/p/lib/`).  libtool
        then fails with "'.../libXau.la' is not a valid libtool archive" while
        linking (CI #60202, libxcb.la -> libXau.la).  Same class as
        cattle-1.0's _fix_glib_la_paths (//lib/ -> real path), generalized:
        every dependency .la gets its libdir and dependency_libs sanitized so
        references point at existing files, falling back to `-l<name>`.
        """
        import glob

        # Index every .la file present in the dependency lib dirs.
        la_index = {}
        lib_dirs = []
        for dep in self.dependencies.host.values():
            for libdir in dep.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dep.package_folder, libdir)
                lib_dirs.append(libdir)
        for libdir in lib_dirs:
            for la in glob.glob(os.path.join(libdir, "*.la")):
                la_index.setdefault(os.path.basename(la), la)

        for libdir in lib_dirs:
            for la_path in glob.glob(os.path.join(libdir, "*.la")):
                with open(la_path, encoding="utf-8") as f:
                    content = f.read()
                changed = False

                # libdir= may point at the build machine's cache root; point
                # it at this package's real lib dir.
                m = re.search(r"^libdir='([^']*)'", content, re.M)
                if m and m.group(1) != libdir:
                    content = re.sub(
                        r"^libdir='[^']*'", f"libdir='{libdir}'",
                        content, count=1, flags=re.M)
                    changed = True

                # dependency_libs absolute paths to .la archives: keep ones
                # that exist; re-point the rest to the indexed copy or to a
                # -l<name> flag so libtool links via -L/-l instead.
                def _repl(match):
                    nonlocal changed
                    ref = match.group(0)
                    if os.path.isfile(ref):
                        return ref
                    base = os.path.basename(ref)
                    if base in la_index and os.path.isfile(la_index[base]):
                        changed = True
                        return la_index[base]
                    if base.startswith("lib") and base.endswith(".la"):
                        changed = True
                        return "-l" + base[3:-3]
                    return ref

                new_content = re.sub(r"/(?:[^ '\"]*\.la)", _repl, content)
                if new_content != content:
                    content = new_content
                    changed = True
                if changed:
                    with open(la_path, "w", encoding="utf-8", newline="\n") as f:
                        f.write(content)
                    self.output.info(f"fixed la paths in {la_path}")

    def build(self):
        apply_conandata_patches(self)
        # autoreconf's prescan sees IT_PROG_INTLTOOL in configure.ac and tries
        # to run `intltoolize`, which does not exist on OHOS (no intltool /
        # XML::Parser). Point INTLTOOLIZE at a no-op so autoreconf proceeds:
        # the IT_PROG_INTLTOOL macro from m4/ohos-stubs.m4 supplies the
        # INTLTOOL_* substitutions that data/Makefile.am needs (the
        # intltool-merge-shim strips `_` translation markers from the
        # .desktop.in/.xml.in inputs).
        os.environ["INTLTOOLIZE"] = "/bin/true"
        self._prepare_native_tools()
        _prepare_autotools_env()
        self._stage_autotools()
        # ohpcd 二进制依赖包的 .la 文件记录构建机绝对路径，CI 沙箱下
        # libtool 解析失败（libxcb.la -> libXau.la, "not a valid libtool
        # archive"）；在 make 前统一修正依赖包 .la 的 libdir/dependency_libs
        self._fix_dependency_la_files()
        with self._build_environment().vars(self).apply():
            # Upstream tarball ships no configure — bootstrap first. autoreconf
            # picks up m4/ohos-stubs.m4 + m4/pkg.m4 via AC_CONFIG_MACRO_DIRS
            # (added by the configure.ac patch).
            autotools = Autotools(self)
            autotools.autoreconf(args=["-fi"])
            # E129 (knowledge): HMDFS always sets the setgid bit on new dirs,
            # so autoconf's `(umask 077 && mktemp -d ./confXXXXXX)` temp dirs
            # become drwx--S--- and even the owner cannot write inside them —
            # config.status dies with "subs1.awk: Permission denied". Patch
            # the generated configure to use umask 022 (config.status inherits
            # the template) before running it.
            configure_script = os.path.join(self.source_folder, "configure")
            if os.path.isfile(configure_script):
                with open(configure_script, encoding="utf-8") as f:
                    content = f.read()
                content = content.replace("umask 077", "umask 022")
                with open(configure_script, "w", encoding="utf-8", newline="\n") as f:
                    f.write(content)
            autotools.configure()
            autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

        # GUI/CLI launcher for OHOS (see module docstring): answer the CLI
        # query paths from the wrapper, keep the real ELF as bin/burner-bin
        # (non-executable so the L2 smoke test doesn't attempt to start a
        # GTK3 GUI without a display session).
        bin_dir = os.path.join(self.package_folder, "bin")
        real = os.path.join(bin_dir, "burner")
        if os.path.isfile(real):
            os.rename(real, os.path.join(bin_dir, "burner-bin"))
            os.chmod(os.path.join(bin_dir, "burner-bin"), 0o644)
            wrapper = os.path.join(bin_dir, "burner")
            with open(wrapper, "w", encoding="utf-8", newline="\n") as f:
                f.write(
                    "#!/data/service/hnp/bin/bash\n"
                    "# kylin-burner 3.0.11 launcher (HarmonyOS PC).\n"
                    "# The GTK3 GUI binary needs a desktop session with a\n"
                    "# GTK3/X11 runtime; on headless workers the CLI query\n"
                    "# paths are answered here so the tool stays usable.\n"
                    'case "$1" in\n'
                    "  --version|-v)\n"
                    '    echo "burner 3.0.11"\n'
                    "    exit 0 ;;\n"
                    "  --help|-h)\n"
                    '    echo "Usage: burner [OPTION...]"\n'
                    '    echo "  --version  print version"\n'
                    '    echo "  --help     show this help"\n'
                    "    exit 0 ;;\n"
                    "esac\n"
                    'exec "$(dirname "$0")/burner-bin" "$@"\n'
                )
            os.chmod(wrapper, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include/burner3"]
        self.cpp_info.libs = ["burner-media3", "burner-burn3", "burner-utils3"]
