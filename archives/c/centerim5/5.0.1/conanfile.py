#!/usr/bin/env python3
"""Conan recipe for centerim5 5.0.1 on HarmonyOS PC (aarch64).

centerim5 is the IRC/ICQ/Jabber/... instant-messaging client (fork of
CenterIM) with a curses UI built on cppconsui + libtermkey, and protocol
support via libpurple.

Build: upstream tarball ships configure.ac (no pre-generated configure), so
the recipe runs the upstream `bootstrap` script (autopoint/libtoolize/
aclocal/autoheader/autoconf/automake) before configure. Dependencies come
from the ohpcd registry: pidgin (libpurple), libsigc++, glib, ncursesw,
libtermkey, unibilium, gettext, libiconv.

Notes:
  - tests/colorpicker.cpp & tests/window.cpp use `&(std::ostringstream() << x)`
    which is invalid in C++11+ (operator<< rvalue overload) — patched to
    std::to_string() (patch 0001).
  - tests/termex.py spawns the test binary with a hardcoded env and drops
    LD_LIBRARY_PATH, so the test child cannot locate libsigc/libc++_shared —
    patched to inherit LD_LIBRARY_PATH (patch 0001).
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class Centerim5Conan(ConanFile):
    name = "centerim5"
    version = "5.0.1"
    description = "Curses-based instant messaging client (IRC/Jabber/ICQ, libpurple backend)"
    license = "GPL-2.0"
    homepage = "https://github.com/petrpavlu/centerim5"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
        # E521: this toolchain's libtoolize is broken (func_error: sources
        # missing) so `./bootstrap` cannot generate config/ltmain.sh.
        # Ship a pristine ltmain.sh (libtool 2.4.7 build-aux) plus the gettext
        # m4 macros and po templates needed by autopoint-less bootstrap.
        # NOTE: conan's copy() has path-semantics issues under export_sources
        # (CI observed an empty es/), so use shutil.copytree directly
        # (same approach as abiword-plugin-docbook).
        _src_aux = os.path.join(self.recipe_folder, "build-aux")
        _dst_aux = os.path.join(self.export_sources_folder, "build-aux")
        if os.path.isdir(_src_aux) and not os.path.exists(_dst_aux):
            shutil.copytree(_src_aux, _dst_aux)
            self.output.info(f"  [ok] exported build-aux to {_dst_aux}")

    def requirements(self):
        # configure.ac PKG_CHECK_MODULES:
        #   purple >= 2.7.0, glib-2.0 >= 2.32.0, sigc++-2.0 >= 2.2.0,
        #   ncursesw >= 5.8 (+ iconv/gettext via glib)
        # cppconsui bundles libtermkey sources (needs libtermkey/unibilium API
        # compatibility) and links libpurple for protocol support.
        self.requires("pidgin/2.14.14")
        self.requires("libsigc/2.10.8")
        self.requires("glib/2.84.0")
        self.requires("ncurses/6.4")
        self.requires("libtermkey/0.22")
        self.requires("unibilium/2.1.2")
        self.requires("gettext/0.22.5")
        self.requires("libiconv/1.17")

    def build_requirements(self):
        # tarball ships configure.ac (no configure), so build() must run
        # aclocal/autoheader/autoconf/automake to bootstrap. The CI worker
        # (USER=100 sandbox) cannot see the locally hand-installed
        # automake/libtool under $HOME/usr/local/bin, and /data/service/hnp/bin
        # only has the autoconf family — aclocal/automake would be "not found".
        # Pull them as tool_requires (registry has 1.18/2.5.4) and let
        # VirtualBuildEnv inject their bin dirs into the conanbuild PATH
        # (same approach as the merged abiword-plugin-docbook recipe).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R31/R33: pkg-config deps via conan generators
        deps = PkgConfigDeps(self)
        deps.generate()
        # centerim5 configure.ac does PKG_CHECK_MODULES([PURPLE], [purple >= 2.7.0])
        # but pidgin's recipe sets pkg_config_name="libpurple", so PkgConfigDeps
        # emits libpurple.pc (not purple.pc) -> configure fails with
        # "No package 'purple' found". Provide a purple.pc alias so pkg-config
        # resolves the same metadata under the name the project looks up.
        _gen = self.generators_folder
        _src_pc = os.path.join(_gen, "libpurple.pc")
        _dst_pc = os.path.join(_gen, "purple.pc")
        if os.path.exists(_src_pc) and not os.path.exists(_dst_pc):
            # centerim5 sources use `#include <libpurple/purple.h>` (include ROOT
            # path), but pidgin's cpp_info.includedirs=["include/libpurple"]
            # makes PkgConfigDeps emit includedir=<pkg>/include/libpurple with
            # Cflags -I<that>. So purple.pc must expose the include root and
            # also keep libpurple/ for the pidgin-relative includes.
            _content = open(_src_pc, encoding="utf-8").read()
            _content = _content.replace(
                "includedir=${prefix}/include/libpurple",
                "includedir=${prefix}/include",
            )
            _content = _content.replace(
                'Cflags: -I"${includedir}"',
                'Cflags: -I"${includedir}" -I"${includedir}/libpurple"',
            )
            open(_dst_pc, "w", encoding="utf-8").write(_content)
            self.output.info(f"  [ok] alias purple.pc -> libpurple.pc (include root + libpurple/)")

        # ohpcd's glib-2.0.pc embeds `-l:ld-musl-aarch64.so.1` (musl loader)
        # which does not exist in this sysroot; via Requires it leaks into
        # PURPLE_LIBS / the link line and makes ld.lld fail. Strip it (and the
        # bare -L/lib it sits next to) from every generated .pc.
        for f in os.listdir(_gen):
            if not f.endswith(".pc"):
                continue
            pc = os.path.join(_gen, f)
            content = open(pc, encoding="utf-8").read()
            fixed = re.sub(r"-l:ld-musl[^ ]*", "", content)
            fixed = re.sub(r"-L/lib ", "", fixed)
            # ohpcd glib-2.0.pc wrongly puts `-I${includedir} -I${includedir1}`
            # into Libs (no Cflags line), so `pkg-config --cflags glib-2.0`
            # returns empty and glib.h is not found. Move -I flags into Cflags.
            libs_line = re.search(r"^Libs:(.*)$", fixed, re.M)
            if libs_line and re.search(r"-I[^\s]", libs_line.group(1)):
                inc_flags = re.findall(r"-I(?:[^\s]+|\"\${includedir[^}]*}\")", libs_line.group(1))
                stripped = re.sub(r"\s+-I(?:[^\s]+|\"\${includedir[^}]*}\")", "", libs_line.group(1))
                fixed = fixed[:libs_line.start()] + f"Libs:{stripped}\n" + fixed[libs_line.end():]
                cflags_line = re.search(r"^Cflags:(.*)$", fixed, re.M)
                if cflags_line:
                    fixed = fixed[:cflags_line.start()] + f"Cflags:{cflags_line.group(1)} {' '.join(inc_flags)}" + fixed[cflags_line.end():]
                else:
                    fixed += f"Cflags: {' '.join(inc_flags)}\n"
            if fixed != content:
                open(pc, "w", encoding="utf-8").write(fixed)
                self.output.info(f"  [ok] sanitized {f}")
            # glib's static archive references gettext (ggettext.c) but the
            # generated glib-2.0.pc has no -lintl -> link fails with undefined
            # bindtextdomain/dgettext/gettext. Append libintl from gettext.
            if f == "glib-2.0.pc":
                try:
                    intl_lib = os.path.join(self.dependencies["gettext"].package_folder, "lib")
                except Exception:
                    intl_lib = None
                if intl_lib and os.path.isdir(intl_lib) and "-lintl" not in fixed:
                    fixed = fixed.replace(
                        "Libs:", f"Libs: -L\"{intl_lib}\" -lintl ", 1
                    )
                    open(pc, "w", encoding="utf-8").write(fixed)
                    self.output.info("  [ok] appended -lintl to glib-2.0.pc")
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.configure_args.append("--prefix=/usr")
        # OHOS is not recognized by config.guess (uname -s = HarmonyOS, plus CI
        # sandbox tmp is unwritable so the guess probe fails with Permission
        # denied). Explicitly give --build/--host to skip the guess, matching
        # the merged abiword-plugin-docbook recipe.
        tc.configure_args.append("--build=aarch64-linux")
        tc.configure_args.append("--host=aarch64-linux")
        # CI worker (USER=100) cannot see $HOME/.local hand-installed aclocal
        # macros; ship our gettext/pkg/libtool macros via ACLOCAL_PATH, then
        # VirtualBuildEnv injects tool_requires(automake/libtool) bin dirs into
        # the conanbuild PATH so `aclocal`/`automake` resolve (E540; mirrors
        # merged abiword-plugin-docbook recipe).
        _m4_dir = os.path.join(self.export_sources_folder, "build-aux", "m4")
        if os.path.isdir(_m4_dir):
            self.buildenv_info.append_path("ACLOCAL_PATH", _m4_dir)
        VirtualBuildEnv(self).generate()
        tc.generate()

    def build(self):
        # CI worker's conan process has a minimal PATH (no usr/local/bin, no
        # hnp), so aclocal/autoheader/autoconf/automake are "not found".
        # Prepend the toolchain dirs the same way the local env does; the
        # actual autotools calls below run inside env="conanbuild" (see
        # build_requirements/generate) which resolves tool_requires
        # (automake/libtool) + hnp autoconf family via PATH.
        _tool_paths = [
            "/data/service/hnp/bin",
            "/storage/Users/currentUser/usr/local/bin",
            "/storage/Users/currentUser/.local/bin",
        ]
        _cur = os.environ.get("PATH", "")
        os.environ["PATH"] = ":".join(_tool_paths + ([_cur] if _cur else []))
        # aclocal invokes autom4te internally; point it at the hnp binary so
        # the bootstrap works even where autom4te is not on the default PATH.
        os.environ["AUTOM4TE"] = "/data/service/hnp/bin/autom4te"

        apply_conandata_patches(self)
        src = self.source_folder
        aux = os.path.join(self.export_sources_folder, "build-aux")

        # E521: this toolchain's libtoolize is broken so `./bootstrap` cannot
        # produce config/ltmain.sh. Replicate the upstream bootstrap sequence
        # manually with shipped artifacts (verified on the local AI build):
        #   1) seed config/ltmain.sh (from libtool 2.4.7 build-aux)
        #   2) seed gettext m4 macros + pkg.m4 into m4/ (aclocal needs them to
        #      expand PKG_CHECK_MODULES / AM_GNU_GETTEXT)
        #   3) seed po templates (autopoint output) into po/
        #   4) run aclocal/autoheader/autoconf/automake by hand
        cfg_dir = os.path.join(src, "config")
        os.makedirs(cfg_dir, exist_ok=True)
        shutil.copy(os.path.join(aux, "ltmain.sh"), os.path.join(cfg_dir, "ltmain.sh"))
        # gettext/autopoint would normally install config.rpath + ABOUT-NLS
        # (required by AM_GNU_GETTEXT); ship them from the gettext dist.
        shutil.copy(os.path.join(aux, "config.rpath"), os.path.join(cfg_dir, "config.rpath"))
        shutil.copy(os.path.join(aux, "ABOUT-NLS"), os.path.join(src, "ABOUT-NLS"))

        m4_dir = os.path.join(src, "m4")
        os.makedirs(m4_dir, exist_ok=True)
        for f in os.listdir(os.path.join(aux, "m4")):
            shutil.copy(os.path.join(aux, "m4", f), os.path.join(m4_dir, f))

        po_dir = os.path.join(src, "po")
        os.makedirs(po_dir, exist_ok=True)
        for f in os.listdir(os.path.join(aux, "po")):
            shutil.copy(os.path.join(aux, "po", f), os.path.join(po_dir, f))

        # manual bootstrap (skip broken libtoolize/autopoint); run inside the
        # conanbuild env so tool_requires(automake/libtool) + hnp autoconf
        # family resolve via PATH (CI worker cannot see $HOME/.local tools).
        self.run("aclocal -I m4", cwd=src, env="conanbuild")
        self.run("autoheader", cwd=src, env="conanbuild")
        self.run("autoconf", cwd=src, env="conanbuild")
        self.run("automake --add-missing --copy", cwd=src, env="conanbuild")

        # autoconf 2.72 emits `umask 077 && mktemp -d "./confXXXXXX"` which
        # creates a 2700 (setgid) temp dir; on hmdfs the build process cannot
        # write into it (config.status: subs1.awk: Permission denied).
        # Relax to the default umask so the temp dir is group-writable.
        _cfg = os.path.join(src, "configure")
        if os.path.isfile(_cfg):
            _data = open(_cfg, encoding="utf-8").read()
            _orig = _data
            _data = _data.replace('(umask 077 && mktemp -d "./confXXXXXX")',
                                  '(mktemp -d "./confXXXXXX")')
            _data = _data.replace('(umask 077 && mkdir "$tmp")',
                                  '(mkdir "$tmp")')
            if _data != _orig:
                open(_cfg, "w", encoding="utf-8").write(_data)
                self.output.info("  [ok] relaxed config.status temp-dir umask 077 -> default")

        autotools = Autotools(self)
        autotools.configure()
        # centerim5 ships its own src/request.h (Request class) which shadows
        # libpurple's request.h: purple.h does `#include <request.h>` and the
        # automake DEFAULT_INCLUDES (-I. -I$(srcdir)) precede PURPLE_CFLAGS,
        # so it picks centerim5's header and libpurple types are undefined.
        # Prepend pidgin's include dirs to DEFAULT_INCLUDES in the generated
        # Makefiles: purple.h's angle-bracket refs then resolve to libpurple,
        # while centerim5's own quoted "Request.h" refs still hit src/ first.
        self._fix_purple_include_priority()
        # pidgin's installed libpurple.la records absolute dep paths (libffi /
        # pcre2) from the revision that built the binary; those hashed dirs are
        # gone after conan cache rebuilds, so libtool fails resolving the .la
        # graph when linking plugins. Rewrite stale refs to the actually
        # resolved deps in the current graph (self-healing, mirrors the manual
        # AI-build workaround).
        self._fix_purple_la_refs()
        autotools.make(args=["-j1"])

    def _fix_purple_include_priority(self):
        """Prepend pidgin include dirs to DEFAULT_INCLUDES in generated Makefiles."""
        try:
            purple_inc = os.path.join(
                self.dependencies["pidgin"].package_folder, "include"
            )
        except Exception:
            return
        if not os.path.isdir(purple_inc):
            return
        inc_libpurple = os.path.join(purple_inc, "libpurple")
        prefix = f"-I{inc_libpurple} -I{purple_inc}"
        for root, _dirs, files in os.walk(self.build_folder):
            if "Makefile" not in files:
                continue
            mk = os.path.join(root, "Makefile")
            data = open(mk, encoding="utf-8").read()
            orig = data
            # DEFAULT_INCLUDES = -I. -I$(srcdir) -I$(top_builddir)
            data = re.sub(
                r"^(DEFAULT_INCLUDES\s*=)(.*)$",
                lambda m: f"{m.group(1)} {prefix}{m.group(2)}",
                data,
                count=1,
                flags=re.M,
            )
            if data != orig:
                open(mk, "w", encoding="utf-8").write(data)
                self.output.info(f"  [ok] prepended pidgin includes to {mk}")

    def _fix_purple_la_refs(self):
        """Self-heal libpurple.la and dep .la stale paths.

        Two problems hit on this machine (not on a fresh CI registry pull):
          1. pidgin's libpurple.la records absolute -L dirs into old
             libffi/pcre2 hashed dirs that conan cache rebuilds removed.
          2. pcre2-posix.la (and similar) carry a bare `//lib/libpcre2-8.la`
             ref from the OHOS sysroot build; libtool recursively resolves it
             and fails ("//lib/libpcre2-8.la is not a valid libtool archive").
        Rewrite: stale `-L` -> live dep dir, stale `<dir>/libX.la` -> `-lX`,
        and strip `//lib/` prefix from remaining .la refs.
        """
        la_files = []
        try:
            purple = self.dependencies["pidgin"].package_folder
        except Exception:
            return
        la_files.append(os.path.join(purple, "lib", "libpurple.la"))
        # Dep .la files that may carry OHOS `//lib/` sysroot refs.
        for dep_name in ("pcre2", "libffi", "glib", "libxml2"):
            try:
                libdir = os.path.join(self.dependencies[dep_name].package_folder, "lib")
                la_files += [
                    os.path.join(libdir, f)
                    for f in os.listdir(libdir)
                    if f.endswith(".la")
                ]
            except Exception:
                continue

        stale = {
            "/storage/Users/currentUser/.conan2/p/libff686a8eee3007f/p/lib": "libffi",
            "/storage/Users/currentUser/.conan2/p/pcre297338922b93dd/p/lib": "pcre2",
        }
        for la in la_files:
            if not os.path.isfile(la):
                continue
            data = open(la, encoding="utf-8").read()
            orig = data
            # 1) stale <dir>/lib*.la refs -> -l<name>
            for s, name in stale.items():
                data = re.sub(
                    re.escape(s) + r"/(lib[^ ]+\.la)",
                    lambda m: "-l" + m.group(1)[3:-3],
                    data,
                )
            # 2) strip OHOS `//lib/` sysroot prefix; then convert BARE `.la`
            #    dep refs (e.g. `libpcre2-8.la` left over from the sysroot
            #    prefix, or `//lib/libpcre2-8.la`) into `-l<name>` so libtool
            #    stops trying to open a file that does not exist.  Only touch
            #    refs that start at a token boundary (space / quote / start),
            #    not `-L/some/dir/libX.la` absolute paths already validated.
            data = re.sub(
                r"//lib/(lib[^ ]+\.la)",
                lambda m: "-l" + m.group(1)[3:-3],
                data,
            )
            data = re.sub(
                r"(?<=[\s'])(lib[^ ]+\.la)(?=[\s']|$)",
                lambda m: "-l" + m.group(1)[3:-3],
                data,
            )
            data = data.replace("-L//lib", "")
            # 4) drop musl loader refs (-l:ld-musl-aarch64.so.1) recorded by
            #    pidgin's build; the library does not exist in this sysroot and
            #    static linking handles the loader via the toolchain itself.
            data = re.sub(r"-l:ld-musl[^ ]*", "", data)
            # 3) stale -L dirs -> live dep dirs
            for s, name in stale.items():
                try:
                    live = os.path.join(self.dependencies[name].package_folder, "lib")
                    data = data.replace(f"-L{s}", f"-L{live}")
                except Exception:
                    pass
            if data != orig:
                open(la, "w", encoding="utf-8").write(data)
                self.output.info(f"  [ok] self-healed stale refs in {la}")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # --prefix=/usr installs the binary under <pkg>/usr/bin; conan's
        # VirtualRunEnv only adds <pkg>/bin to PATH for test_package, so
        # relocate usr/bin/* -> bin/ (and drop the now-empty usr/ tree).
        src_bin = os.path.join(self.package_folder, "usr", "bin")
        dst_bin = os.path.join(self.package_folder, "bin")
        if os.path.isdir(src_bin) and not os.path.isdir(dst_bin):
            os.makedirs(dst_bin, exist_ok=True)
            for f in os.listdir(src_bin):
                shutil.move(os.path.join(src_bin, f), os.path.join(dst_bin, f))
                self.output.info(f"  [ok] relocated usr/bin/{f} -> bin/{f}")
            shutil.rmtree(os.path.join(self.package_folder, "usr"))
        # clean install() artifacts that confuse packaging audits
        for junk in ("usr", "lib/pkgconfig", "share"):
            p = os.path.join(self.package_folder, junk)
            if os.path.isdir(p) and not os.listdir(p):
                try:
                    shutil.rmtree(p)
                except OSError:
                    pass

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
