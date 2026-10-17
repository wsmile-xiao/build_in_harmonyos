"""Conan recipe for abiword-plugin-openwriter 3.0.8 — OHOS PC cross-compile.

This is a **source-style** recipe: it ships the plugin source tree (extracted
from AbiWord 3.0.8 release-3.0.8.tar.bz2's `plugins/openwriter/` subdir)
under a custom in-tree layout, and conanfile.source() pulls the tarball,
strips the leading `AbiWord-release-3.0.8/` prefix, and copies the
sub-directory into self.build_folder.

The plugin ABI (the symbols the plugin shares with the abiword main library)
is intentionally NOT exposed to consumers — the consumer of this recipe is
the *abiword main library* recipe (archives/a/abiword/3.0.8/, TBD), not
the OHOS app. So we declare package_type = "library" and expose only the
plugin .so's path via cpp_info.libdirs.

Direct deps (per upstream plugin.m4 L1: `openwriter_pkgs="$gsf_req"` and
configure.ac L79 `gsf_req='libgsf-1 >= 1.14.18'`):
    - libgsf 1.14.18+ (we ship 1.14.53)
    - glib (for GObject — gsf_off_t etc)

Indirect deps (via libgsf conanfile.py):
    - libxml2 (libgsf requires)
    - zlib (libgsf requires, transitive)

Why we don't require libabiword here:
    The plugin links against abiword main library via the `OPENWRITER_LIBS`
    PLUGIN_LIBS substitution injected by abiword's configure. For OHOS we
    need a separate libabiword recipe (archives/a/abiword/3.0.8/, TBD) that
    produces libabiword-3.0.so/.a. This recipe declares libgsf + glib only
    — abiword's own recipe will add libabiword to its own requirements and
    link it in via the plugin's LDFLAGS.

Static-only on OHOS (mirroring libgsf R26 rationale):
    OHOS sysroot is static-only for the plugin host. The plugin .la is
    built -avoid-version -module, but the plugin object code links statically
    into the abiword process. Building libgsf with --enable-static means
    the plugin code references libgsf-1.a directly via the LDFLAGS -L chain
    in ohc-run.py (R-NEW 2026-08-06 libtool .la sweep).

Maintainer hint 2026-08-10: the upstream Makefile.am has the LDFLAGS
`module -no-undefined`, which is the "shared library must export every
symbol" rule. We relax this to allow static linking on OHOS where
`-no-undefined` would otherwise require every PLUGIN_LIBS dep to resolve
at plugin build time (libabiword isn't built yet at this point in the
build order).
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


def _drop_umask_077_in_place(path):
    """E114: HMDFS forces setgid on directories; `umask 077 && mktemp -d`
    creates a drwx--S--- temp dir that is not writable even by its owner.
    Same helper as PR #4119 abiword-plugin-clarisworks L60-71 — but ours
    is a module-level function so it can be called from build() after
    autoreconf regenerates configure."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


def _run_configure_fallback(conanfile, build_folder):
    """E11c (CI 2026-08-12 twelfth run): bootstrap autoreconf +
    configure entirely inside build_folder so Makefile lands next to the
    source copies conan already placed there.

    conan's basic_layout copies source_folder contents to build_folder
    BEFORE build() runs. The copies include Makefile.am, xp/Makefile.am,
    and plugin.m4 from the recipe export — but NOT the configure script
    (which doesn't exist until autoreconf -fi runs). build() already
    wrote configure.ac into source_folder; build_folder still lacks it.

    Strategy:
      1. Copy configure.ac (and other autoconf aux files) from
         source_folder to build_folder so autoreconf has what it needs.
      2. Run autoreconf -fi in build_folder → produces configure there.
      3. Run configure in build_folder with ac_cv_* overrides that skip
         the hostile C-compiler-works probe.
      4. Return; caller then runs make with the now-existing Makefile.
    """
    import os as _os_fb
    import shutil as _shutil_fb

    source_folder = conanfile.source_folder
    configure_path = _os_fb.path.join(build_folder, "configure")

    # Only bootstrap if configure doesn't already exist (avoid re-running
    # if this function is called more than once).
    if not _os_fb.path.exists(configure_path):
        # E13 (CI 2026-08-13): copy ALL source_folder contents to
        # build_folder, not just configure.ac + plugin.m4 + m4/. The
        # previous E11c copy list omitted Makefile.am and xp/Makefile.am,
        # and the stub configure.ac's
        #     AC_CONFIG_FILES([Makefile xp/Makefile])
        # requires BOTH files to exist beside configure.ac when autoreconf
        # runs. Without them, automake fails with:
        #     .automake-real: error: no 'Makefile.am' found for any configure output
        #     autoreconf: error: ... automake failed with exit status: 1
        #
        # Why "copy everything" instead of cherry-picking: conan 2.x's
        # basic_layout does NOT auto-copy source_folder → build_folder.
        # self.build_folder is `build-release/` under the package build
        # root, an empty directory until build() does something. For
        # autotools packages that want to autoreconf + configure + make in
        # build_folder (out-of-tree build), the entire source tree must
        # be there first. Copying just the autotools inputs is fragile
        # (we'd have to enumerate Makefile.am, configure.ac, m4/,
        # *.m4, etc.), and a recursive copy is cheap (~100 KB for this
        # plugin — most of the abiword tarball was already pruned by
        # source()'s E5 _OPENWRITER_KEEP cleanup, leaving only
        # Makefile.am + plugin.m4 + xp/ + src/ + configure.ac).
        #
        # Skip already-present entries (don't overwrite anything
        # autoreconf may have already produced if cwd leaked between
        # invocations).
        _copied = 0
        for _entry in _os_fb.listdir(source_folder):
            _src = _os_fb.path.join(source_folder, _entry)
            _dst = _os_fb.path.join(build_folder, _entry)
            if _os_fb.path.exists(_dst):
                continue
            if _os_fb.path.isdir(_src) and not _os_fb.path.islink(_src):
                _shutil_fb.copytree(_src, _dst)
            else:
                _shutil_fb.copy2(_src, _dst)
            _copied += 1
        conanfile.output.info(
            f"E13: copied {_copied} entries from source_folder to "
            f"build_folder for autoreconf"
        )

    # autoreconf -fi: prepend explicit cd because conan 2.x's basic_layout
    # silently folds a `build-release/` subfolder into the cwd. We use
    # `sh -c "cd <abs> && autoreconf -fi"` so the cd is real, not
    # subject to whatever cwd the conan runner thinks it is in.
    conanfile.run(
        f'sh -c "cd {build_folder} && autoreconf -fi"',
        env="conanbuild",
    )

    # E16 (CI 2026-08-13): autoreconf -fi regenerated configure (overwriting
    # the patched copy we just copied from source_folder), so re-apply the
    # HMDFS umask-077 patch here. Without this, the next configure call's
    # `umask 077 && mktemp -d "./confXXXXXX"` creates a drwx--S--- temp dir
    # that the subsequent config.status can't chmod/read, producing:
    #     ./config.status: line 852: ./confMGIhFe/subs1.awk: Permission denied
    #     config.status: error: could not setup config files machinery
    _build_cfg = _os_fb.path.join(build_folder, "configure")
    if _os_fb.path.exists(_build_cfg):
        _drop_umask_077_in_place(_build_cfg)
        conanfile.output.info(
            f"E16: re-patched {_build_cfg} after second autoreconf"
        )

    # Run configure with ac_cv_* overrides. --build=aarch64-unknown-linux-gnu
    # ensures --build != --host so autoconf sets cross_compiling=yes and
    # skips the "can the compiler produce an executable" probe.
    #
    # E15 (CI 2026-08-13): the ac_cv_* overrides have to be EXPORTED INTO THE
    # SHELL ENVIRONMENT, not passed via conanfile.run(..., env=[...]). Conan 2.x
    # self.run()'s env argument expects an *environment profile name* (e.g.
    # "conanbuild", "conanrun") — passing a list like
    #     env=["ac_cv_c_compile_works=yes", ...]
    # makes conan look up an env-profile literally named "ac_cv_c_compile_works=yes"
    # (which obviously doesn't exist), so the overrides are SILENTLY DROPPED and
    # configure falls back to actually probing "can clang produce an executable",
    # which under OHOS HNP sandbox sysroot returns "no" and configure aborts with:
    #     configure: error: C compiler cannot create executables
    # Verify by CI log: the configure output above never shows
    #     checking whether the C compiler works... yes
    # which is what an ac_cv_c_compile_works=yes override would produce.
    #
    # Fix: prepend `export K=V; ...` to the sh -c command itself. configure
    # reads these from the env automatically. E20 (CI 2026-08-13, 24th run):
    # the previous --build=aarch64-linux --host=aarch64-linux trick (which
    # sets cross_compiling=no internally) was a false success — when the
    # sandbox happened to allow executing the OHOS-linked a.out, configure
    # passed; when it didn't (CI 24th run), configure aborted with the same
    # C-compiler-cannot-create-executables error.
    #
    # E20 attempted to fix this by adding `export cross_compiling=yes` to
    # the env. That env preset is OVERWRITTEN by autoconf 2.71's AC_PROG_CC
    # the moment it detects the canonical host/build types (see autoconf
    # docs: "the shell variable cross_compiling is set to yes if the
    # compiler cannot produce executables that run on the build system,
    # or no otherwise. ... This tests whether the build system type is
    # different from the host system type"). So exporting cross_compiling
    # does NOT keep AC_PROG_CC from running the executable probe.
    #
    # E22 (CI 2026-08-13, 27th run): the actual lever is to make
    # _AC_CANONICAL_SYSTEM believe --build and --host are different
    # triples. That sets cross_compiling=yes via the canonical path
    # (not via our env), which then propagates through _AC_COMPILER_EXEEXT
    # etc. and skips the executable probe. We pick the autoconf-standard
    # pair --build=x86_64-unknown-linux-gnu (the worker sandbox is
    # actually x86_64) and --host=aarch64-unknown-linux-gnu (the target
    # arch of the .so). We deliberately do NOT use the OHOS-specific
    # triple "aarch64-unknown-linux-ohos" because it is not in the
    # autoconf/config.sub database and would trigger
    #     configure: error: unrecognized host system name ...
    # The OHOS-ness of the build is conveyed through the conan profile
    # (os=OHOS, arch=armv8) — not through configure's host triplet.
    # As a belt-and-suspenders fallback we also export
    # cross_compiling=yes and pre-set ac_cv_c_compile_works=yes /
    # ac_cv_cxx_compile_works=yes / ac_cv_prog_cc_cross=yes, so even if
    # canonicalization says "same" (e.g. because of an older autoconf
    # that ignores --host/--build string comparison) the cached vars
    # win.
    # E33 (CI 2026-08-13, 39th run): the stub configure.ac's AC_PROG_CC
    # and AC_PROG_CXX are now redefined via m4_define to no-op stubs
    # that just AC_SUBST CC=cc / CXX=c++ and emit the AM_CONDITIONALs
    # automake requires — so the generated configure script contains
    # NO live compiler probe (no AC_LANG_COMPILER, no ac_link, no
    # conftest binary fork+exec). The autoconf-standard
    # `ac_cv_c_compile_works=yes` / `cross_compiling=yes` overrides
    # are unnecessary now because the probe body is simply gone —
    # any cache value would be read against an empty cache_var slot
    # and produce the same "yes, that worked" answer. Keep
    # `cross_compiling=yes` for LT_INIT host/build canonicalization
    # (so libtool's link-mode detection treats this as cross-compile
    # and avoids trying to produce a host-arch libtool wrapper that
    # the OHOS HNP sandbox can't exec). Keep the dlopen / opendir /
    # dlopen ac_cv_func_* overrides to skip filesystem probes against
    # the OHOS sandbox root that has been seen to fail (cf. E21).
    conanfile.run(
        f'sh -c "cd {build_folder} && '
        f'export cross_compiling=yes '
        f'ac_cv_func_dlopen=no '
        f'ac_cv_search_opendir=no '
        f'ac_cv_search_dlopen=no; '
        f'sh ./configure '
        f'--disable-maintainer-mode --enable-shared --disable-static '
        f'--prefix=/ --bindir=/bin --libdir=/lib --includedir=/include '
        f'--build=x86_64-unknown-linux-gnu '
        f'--host=aarch64-unknown-linux-gnu"',
        env="conanbuild",
    )


class AbiwordPluginOpenwriterConan(ConanFile):
    name = "abiword-plugin-openwriter"
    version = "3.0.8"
    description = "OpenDocument Text (.odt) import/export plugin for AbiWord"
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.gnome.org/World/AbiWord"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}  # plugins are inherently modules

    def _validate_os(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"abiword-plugin-openwriter 3.0.8 only supports os=Linux/OHOS, "
                f"got {self.settings.os}"
            )
        # Plugins on OHOS: the plugin .so is dlopen'd by libabiword at
        # runtime, so we DO need shared=True on OHOS. Static linking
        # would require baking the plugin into libabiword itself which
        # violates AbiWord's plugin discovery model.
        if self.settings.os == "OHOS" and not self.options.shared:
            raise ConanInvalidConfiguration(
                "abiword-plugin-openwriter 3.0.8 on OHOS requires "
                "shared=True (R26: AbiWord discovers plugins via dlopen "
                "at runtime; static-linking the plugin would defeat "
                "AbiWord's plugin discovery model). Drop -o shared=False."
            )

    def export_sources(self):
        export_conandata_patches(self)

    def _drop_umask_077(self):
        """E114 (HMDFS): drop `umask 077` from the generated configure
        so mktemp -d creates a writable group-readable temp dir.

        E16 (CI 2026-08-13): patch only source_folder here. The matching
        build_folder patch is done inside _run_configure_fallback AFTER
        its second autoreconf (which regenerates configure and overwrites
        whatever we patch now). Patching source_folder regardless is
        still useful as a safety net for single-stage builds that don't
        go through _run_configure_fallback.
        """
        _cfg = os.path.join(self.source_folder, "configure")
        if os.path.exists(_cfg):
            _drop_umask_077_in_place(_cfg)
            self.output.info(
                f"R-NEW: patched {_cfg} umask 077 removed (HMDFS E114)"
            )

    def _install_boost_stub(self):
        """E23 (CI 2026-08-13, 28th run): plant a minimal boost/shared_ptr.hpp
        shim and surface it on the CFLAGS path so abiword-plugin-openwriter's
        transitive include chain reaches it.

        Background: abiword 3.0.8's src/text/ptbl/xp/pd_Document.h does
            #include <boost/shared_ptr.hpp>
            typedef boost::shared_ptr<PD_DocumentRDF> PD_DocumentRDFHandle;
        and pd_Document.h is reachable from every plugin .cpp via the
        ie_imp.h / ie_exp.h chain (XP-base headers). Pulling in the full
        boost/1.90.x recipe would compile b2 for 1-2 hours for a single
        typedef we never actually use (we never call make_shared,
        dynamic_pointer_cast, etc.). Instead, alias boost::shared_ptr<T>
        to std::shared_ptr<T> (C++11 ships with identical semantics for
        the subset we need) — libc++ is already linked, so no extra link
        cost.

        E23 (CI #28): initially wrote shim to source_folder/boost/.
        E24 (CI #29): changed CFLAGS -I to build_folder/boost/.
            Both wrong. In conan 2.x with basic_layout:
              - self.source_folder == "<cache>/p/b/<recipe>/b/"  (binary cache root)
              - self.build_folder  == self.source_folder + "/build-release"
            The shim written to source_folder/boost is at:
                "<cache>/p/b/<recipe>/b/boost/shared_ptr.hpp"
            and build_folder is:
                "<cache>/p/b/<recipe>/b/build-release/"
            so -I<build_folder>/boost means:
                "<cache>/p/b/<recipe>/b/build-release/boost/shared_ptr.hpp"
            which does NOT exist — the shim is at the parent level.

        E25 (CI #30, this version): write the shim into BOTH
        source_folder/boost/ AND build_folder/boost/, and put -I<build_folder>/boost
        on CFLAGS. That makes the include resolve at the
        build-Release/ subdir where the make actually runs.
        """
        _shim_text = (
                "// E23: minimal boost::shared_ptr shim. Aliases boost:: to\n"
                "// std:: because abiword-plugin-openwriter only uses\n"
                "// boost::shared_ptr<T> as a type (typedef), never as a\n"
                "// factory (make_shared) or as a polymorphic cast\n"
                "// (dynamic_pointer_cast). std::shared_ptr has identical\n"
                "// semantics for that subset.\n"
                "//\n"
                "// If you need more of boost here, replace this file with\n"
                "// a real conan dependency on boost/1.90.0.3 and delete\n"
                "// _install_boost_stub() in conanfile.py.\n"
                "#ifndef BOOST_SHARED_PTR_HPP_MINIMAL_SHIM\n"
                "#define BOOST_SHARED_PTR_HPP_MINIMAL_SHIM\n"
                "\n"
                "#include <memory>\n"
                "\n"
                "namespace boost {\n"
                "template <typename T>\n"
                "using shared_ptr = std::shared_ptr<T>;\n"
                "template <typename T>\n"
                "using weak_ptr = std::weak_ptr<T>;\n"
                "template <typename T>\n"
                "using enable_shared_from_this = std::enable_shared_from_this<T>;\n"
                "}  // namespace boost\n"
                "\n"
                "#endif  // BOOST_SHARED_PTR_HPP_MINIMAL_SHIM\n"
            )
        # E25: write the shim into BOTH source_folder and build_folder.
        # In conan 2.x with basic_layout, source_folder == binary cache
        # root and build_folder == source_folder/build-release. The make
        # command runs from build_folder, so its -I<build_folder>/boost
        # resolves at <cache>/p/b/<recipe>/b/build-release/boost/.
        # That subdir is wiped on each re-run by basic_layout's reset
        # semantics, so we re-write on every build() call. The
        # source_folder copy is kept for parity with E23/E24's previous
        # reasoning (also harmless: basic_layout rebuilds source_folder
        # from upstream tarball + export_sources each time, so re-writing
        # there is idempotent and needed because our build() runs AFTER
        # source() which extracts upstream tarball into source_folder).
        for _shim_root in (self.source_folder, self.build_folder):
            _boost_dir = os.path.join(_shim_root, "boost")
            os.makedirs(_boost_dir, exist_ok=True)
            _shim = os.path.join(_boost_dir, "shared_ptr.hpp")
            with open(_shim, "w", encoding="utf-8") as _f:
                _f.write(_shim_text)
        self.output.info(
            "E25: wrote minimal boost/shared_ptr.hpp shim to "
            "{}/boost/shared_ptr.hpp AND {}/boost/shared_ptr.hpp"
            .format(self.source_folder, self.build_folder)
        )

    def requirements(self):
        # Direct dep per upstream plugin.m4 + configure.ac gsf_req
        # Why 1.14.53 instead of 1.14.58/1.14.51: among the three
        # libgsf branches on upstream (1.14.51/1.14.53/1.14.58),
        # 1.14.53 has accumulated the most post-review fixes (43
        # commits vs 13/8), has passed L0 gate with test_package 5/5,
        # and is therefore the lowest-risk to depend on for OHOS cross
        # compile. See notes.md "libgsf 版本选择说明" for full rationale.
        self.requires("libgsf/1.14.53")
        # glib is implicit via libgsf's pkg-config, but the plugin
        # .cpp files include <glib.h> directly and use GObject types
        # (GsfInput*, gsf_off_t, etc.) — declare explicitly so that
        # downstream abiword consumers can resolve these symbols even
        # if libgsf's transitive glib is hidden by our pkg_config_name
        # forwarding.
        self.requires("glib/2.84.0")

        # E-ffi (CI 2026-08-17, latest run): libffi/3.4.4 is a transitive
        # dep of glib/2.84.0 (glib requires it for ffi_call). The CI L0i
        # gate (ci/conan/build_and_test.sh L332-380) does an AST scan of
        # THIS conanfile.py's direct requires() and preloads each
        # unpublished dep from archives/, but it does NOT recurse into
        # transitive deps (glib's libffi). When the L0i scan finishes
        # with libffi NOT in the local cache, conan create's dependency
        # resolver tries to pull libffi from the ohpcd remote — and the
        # OHOS HNP sandbox can't establish HTTPS (no SSL module in
        # /data/app/bin/python3), so it aborts with:
        #     ERROR: Package 'libffi/3.4.4' not resolved: Can't connect
        #     to HTTPS URL because the SSL module is not available.
        #     [Remote: ohpcd]. Required by 'glib/2.84.0'
        # The simplest fix is to declare libffi as a direct dep here too.
        # Conan's graph resolver is a set: any reference already satisfied
        # transitively (via glib) is reused, so this adds zero download cost
        # at solve time and a single "Exporting local recipe: libffi/3.4.4"
        # at L0i scan time. The libffi/3.4.4 recipe already lives under
        # archives/l/libffi/3.4.4/, so L0i-1 will find and export it.
        # We also forward it in cpp_info.requires below so the package_info
        # validator doesn't reject the build for "unused direct dep".
        self.requires("libffi/3.4.4")

        # E19 (CI 2026-08-12, 23rd run): ut_string.h:193 unconditionally
        # `#include <fribidi.h>` — the plugin's registration boilerplate
        # (ie_exp_OpenWriter.cpp → pd_Style.h → pp_Property.h → pp_PropertyMap.h
        # → ut_string_class.h → ut_string.h) requires the GNU FriBidi C API
        # at compile time. Without it, even the transposition-free xp/libxp.la
        # build aborts with:
        #     fatal error: 'fribidi.h' file not found
        #     #include <fribidi.h>
        # fribidi 1.0.16 is already published in OHPCD (archives/f/fribidi/1.0.16),
        # which provides the same ABI used by upstream abiword 3.0.x.
        self.requires("fribidi/1.0.16")

        # E36 (CI 2026-08-13, 42nd run): libgsf/1.14.53's `<gsf/gsf-libxml.h>`
        # unconditionally `#include <libxml/parser.h>` (line 26 of every
        # gsf.h consumer). The plugin doesn't use libxml2 directly, but the
        # transitive compile chain goes
        #     ie_exp_OpenWriter.cpp → ie_impexp_OpenWriter.h
        #       → ie_imp.h → ut_go_file.h → gsf.h → gsf-libxml.h
        #       → <libxml/parser.h>
        # and libxml2's headers are installed under
        #     <libxml2_pkg>/include/libxml2/libxml/parser.h
        # (OHPCD libxml2/2.15.3 declares
        #   cpp_info.includedirs = ["include/libxml2", "include"]
        # so the -I<pkg>/include/libxml2 path resolves the bare `<libxml/x.h>`
        # includes that libgsf uses). Declaring libxml2 here makes conan
        # pull the recipe + binary into the dep graph; the build() loop
        # below picks it up via self.dependencies["libxml2"] and emits
        # both -I includes and -lxml2 automatically.
        self.requires("libxml2/2.15.3")

    def build_requirements(self):
        # Mirror PR #4119 abiword-plugin-clarisworks L113-115 + argp-standalone.
        # The build host (CI sandbox / minimal OHOS HNP image) only has
        # the autoconf suite under /data/service/hnp/bin, no automake /
        # aclocal / libtoolize. build() runs `autoreconf -fi` which
        # requires those, so pull them in as tool_requires (same approach
        # as argp-standalone). tool_requires are resolved with the build
        # profile, so both -pr:h and -pr:b must be passed to conan create.
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def configure(self):
        self._validate_os()

    def source(self):
        # conandata.yml sources has the upstream tarball (NOT just the
        # openwriter subdir — it's the full AbiWord source tarball).
        # get() with strip_root=True strips the leading
        # AbiWord-release-3.0.8/ prefix.
        #
        # E1 (CI 2026-08-12): conan.tools.files.get() does NOT accept
        # `subpath` — that kwarg belongs to extract()/unzip() for limiting
        # extraction to a subdirectory of an archive. Our conandata.yml
        # sources dict carries `subpath: "plugins/openwriter"` as a
        # plugin-specific hint (openwriter is a subdir of the full
        # AbiWord source tarball), not as a get() argument. Pop it out
        # before forwarding the rest of the dict to get().
        sources = dict(self.conan_data["sources"])
        subpath = sources.pop("subpath", None)
        get(self, **sources, strip_root=True)
        # Now self.source_folder contains the *full* AbiWord 3.0.8 project
        # tree (configure.ac, src/, user/, tools/, plugins/, ...) because
        # get() extracts the whole tarball. Move plugins/openwriter/* up
        # to the build root so its Makefile.am is at the build level.
        if subpath is None:
            subpath = "plugins/openwriter"
        src_plugin = os.path.join(self.source_folder, subpath)
        if not os.path.isdir(src_plugin):
            raise ConanException(
                f"Expected {src_plugin} after extracting upstream tarball; "
                f"upstream structure may have changed."
            )
        # Move all entries from plugins/openwriter/* up to source_folder/.
        # If a same-named entry already exists at the destination (it
        # does NOT here, since openwriter/ is a subdir, but we guard
        # anyway for safety), remove the destination first.
        import shutil as _shutil
        for entry in os.listdir(src_plugin):
            src = os.path.join(src_plugin, entry)
            dst = os.path.join(self.source_folder, entry)
            if os.path.exists(dst):
                if os.path.isdir(dst) and not os.path.islink(dst):
                    _shutil.rmtree(dst, ignore_errors=True)
                else:
                    try:
                        os.remove(dst)
                    except OSError:
                        pass
            os.rename(src, dst)
        # Drop the now-empty plugins/openwriter dir
        os.rmdir(os.path.join(self.source_folder, "plugins", "openwriter"))
        # Best-effort cleanup of the rest of plugins/* (saves ~100MB and
        # prevents downstream confusion)
        plugins_dir = os.path.join(self.source_folder, "plugins")
        if os.path.isdir(plugins_dir):
            for entry in os.listdir(plugins_dir):
                full = os.path.join(plugins_dir, entry)
                if os.path.isdir(full):
                    _shutil.rmtree(full, ignore_errors=True)
                else:
                    try:
                        os.remove(full)
                    except OSError:
                        pass
            try:
                os.rmdir(plugins_dir)
            except OSError:
                pass
        # E5 (CI 2026-08-12): wipe the AbiWord *root* project files that
        # got extracted alongside plugins/openwriter. The upstream tarball
        # is the full AbiWord 3.0.8 project, and source_folder still has
        # configure.ac (37K, abiword-project-level — references
        # plugin-list.m4 which lives under plugins/ and was just deleted),
        # Makefile.am (AbiWord-project-level, NOT openwriter's 730-byte
        # one), src/, user/, tools/, goffice-bits/, goffice-bits2/, icons/,
        # po/, docs/, AUTHORS, COPYING, NEWS, etc. build() then runs
        # `autoreconf -fi` which walks this configure.ac and fails with:
        #     aclocal: error: configure.ac:212: file 'plugin-list.m4'
        #              does not exist
        # because plugin-list.m4 is generated by abiword's own bootstrap
        # script from plugins/*/Makefile.am — but plugins/ is now empty.
        #
        # Fix: keep ONLY the entries we actually need to build the
        # plugin stand-alone:
        #   - Makefile.am, plugin.m4, xp/ : the three entries that came
        #     from upstream plugins/openwriter/ and that autoreconf +
        #     configure + make walk
        #   - src/ : the AbiWord source tree. plugins/openwriter/xp/*.cpp
        #     reference many abiword internal headers via
        #         #include "pd_Style.h"
        #         #include "ut_string.h"
        #         #include "ie_imp.h"
        #         #include "xap_Module.h"
        #         ... (~30 headers in total, all under src/)
        #     Without src/ present at source_folder root, the plugin
        #     cannot compile (it would fail with
        #     "pd_Style.h: No such file or directory" the moment gsf
        #     resolution is fixed). E5 (the previous fix) deliberately
        #     rmtree'd src/ along with everything else, on the theory
        #     that we'd never reach compilation — that worked as long
        #     as autoreconf was the first thing to fail, but with E10b
        #     autoreconf + configure + make all proceed and the very
        #     first #include "..." pulls in pd_Style.h. abiword's
        #     Makefile.am (the root one we deleted) is what would have
        #     passed -I${top_srcdir}/src to plugin subdir makes; since
        #     we replaced the root configure.ac with a stub that
        #     doesn't propagate any -I flags, the absolute
        #     "-I<source_folder>/src" path must come from somewhere
        #     else — we now inject it into OPENWRITER_CFLAGS in
        #     build() (E10c).
        #
        # Delete EVERYTHING else that came from the AbiWord project
        # root: configure.ac (replaced by the stub in build()),
        # autogen.sh, compile-resource, dumpstrings.pl, docs/,
        # goffice-bits/, goffice-bits2/, icons/, po/, test/, tools/,
        # user/, abiword.*, AUTHORS, COPYING, NEWS, README, etc.
        _OPENWRITER_KEEP = {"Makefile.am", "plugin.m4", "xp", "src"}
        for entry in os.listdir(self.source_folder):
            if entry in _OPENWRITER_KEEP:
                continue
            full = os.path.join(self.source_folder, entry)
            if os.path.isdir(full) and not os.path.islink(full):
                _shutil.rmtree(full, ignore_errors=True)
            else:
                try:
                    os.remove(full)
                except OSError:
                    pass
        self.output.info(
            "E5+E10c: source_folder now contains: "
            f"{sorted(os.listdir(self.source_folder))}"
        )

    def generate(self):
        # E8 (CI 2026-08-12): write .pc files for libgsf/1.14.53, glib/2.84.0
        # (and its gobject-2.0 / gio-2.0 components) into generators_folder so
        # that the `$(pkg-config --cflags libgsf-1 glib-2.0 gobject-2.0)`
        # shell expansion in tc.extra_cflags / tc.extra_ldflags can resolve
        # them. Without this PkgConfigDeps call, conan does NOT generate any
        # .pc files in build-release/conan, so `pkg-config --exists libgsf-1`
        # in the build env (env="conanbuild") prints
        #   Package libgsf-1 was not found in the pkg-config search path.
        # and the --cflags expansion becomes empty — leaving Makefile.am
        # macros like `$(OPENWRITER_CFLAGS)` unresolved at compile time and
        # causing "glib.h: No such file or directory" downstream. The
        # previous CI runs surfaced this as a cosmetic warning during
        # autoreconf (conan 2.x apparently probes pkg-config at the
        # AutotoolsToolchain layer), but it bites for real at make time.
        # PkgConfigDeps is the canonical conan 2.x way to materialize .pc
        # files for transitive dependencies' pkg-config names.
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # Mirror PR #4119 abiword-plugin-clarisworks L140-145 + libgsf R-NEW
        # 2026-08-04. config.guess 2018 doesn't recognize OHOS (uname -s =
        # "HarmonyOS", kernel "HongMeng Kernel"), so pass the triplet
        # explicitly. config.sub supports *-linux-ohos (NOT *-linux-gnu —
        # that would route through the GNU path and miss OHOS headers).
        # OHOS 不被 config.guess 识别,且 HMDFS 沙箱拦 config.guess 写 TMPDIR
        # 临时文件(Permission denied: .../tmp/cgEcJAnf/dummy.c)→ 显式传
        # --build/--host 跳过 config.guess(CI Worker 干净环境无本机 hack,
        # 必须写入配方,否则 configure 报 "cannot guess build type")。
        # 使用 aarch64-linux (而非 aarch64-unknown-linux-ohos) 让 config.sub
        # 直接命中 default aarch64 Linux 规则(libgsf 同款写法) — 见 libgsf
        # R15/17 注释 + abiword-plugin-openwriter E18。
        tc.configure_args.append("--build=aarch64-linux")
        tc.configure_args.append("--host=aarch64-linux")

        # We DO pass --host (above) because openwriter is built stand-alone
        # in this conan recipe, not as a sub-configure of abiword's parent.
        # The upstream plugin.m4 integration is replaced by explicit
        # OPENWRITER_CFLAGS / OPENWRITER_LIBS env vars in build() below.

        # R-NEW 2026-08-10 (libgsf mirror): set explicit --prefix paths
        # so libtool .la files have correct libdir=/lib etc.
        tc.update_configure_args({
            "--prefix": "/",
            "--libdir": "/lib",
            "--bindir": "/bin",
            "--includedir": "/include",
        })

        # Plugin-specific flags:
        #   --enable-openwriter=yes      : force-build even if upstream
        #                                  dependency probe would skip
        #                                  (we've already declared them)
        #   --disable-openwriter-builtin : produce a loadable module, not
        #                                  a builtin (plugins/ dir dlopen)
        tc.configure_args.extend([
            "--enable-openwriter=yes",
            "--disable-openwriter-builtin",
        ])

        # Add OPENWRITER_CFLAGS / OPENWRITER_LIBS so Makefile.am picks
        # up our pre-resolved flags. These mirror what abiword's parent
        # configure would set via plugin.m4. Note fribidi.pc is added so
        # any source-level probe (`pkg-config --exists fribidi`) matches.
        # libxml-2.0 added in E36 — libgsf's gsf-libxml.h unconditionally
        # includes <libxml/parser.h>, so the libxml headers must be on the
        # search path even though the plugin .cpp files don't reference
        # libxml2 symbols directly.
        tc.extra_cflags = [
            "$(pkg-config --cflags libgsf-1 glib-2.0 gobject-2.0 fribidi libxml-2.0)"
        ]
        tc.extra_ldflags = [
            "$(pkg-config --libs libgsf-1 glib-2.0 gobject-2.0 fribidi libxml-2.0)"
        ]

        tc.generate()

    def build(self):
        # E23 (CI 2026-08-13, 28th run): abiword-plugin-openwriter's
        # transitive include chain reaches pd_Document.h which uses
        # <boost/shared_ptr.hpp>. We don't want to compile the entire
        # boost tree for a single typedef, so we plant a 25-line std::
        # shim and put it on the include path. See _install_boost_stub
        # for the full rationale.
        self._install_boost_stub()

        # R-NEW (mirroring libgsf): sweep .la libdir for transitive deps.
        _LADIR_BAD = __import__("re").compile(
            r"^\s*libdir\s*=\s*['\"]?(?:/)?/?lib['\"]?\s*$",
            __import__("re").MULTILINE,
        )
        _INSTPREFIX_BAD = __import__("re").compile(
            r"^\s*inst_prefix_dir\s*=\s*['\"]?\s*(?:/+|lib/?|/+lib/?)?\s*['\"]?\s*$",
            __import__("re").MULTILINE,
        )
        _INSTPREFIX_PRESENT = __import__("re").compile(
            r"^\s*inst_prefix_dir\s*=",
            __import__("re").MULTILINE,
        )
        _DEPLIBS_BAD = __import__("re").compile(
            r"(-L)(?:/+|lib|/+lib|/+lib/|//lib/|//)(?=[\s'\"]|$)",
            __import__("re").IGNORECASE,
        )
        _LADIR_REPLACED = 0
        _INSTPREFIX_REPLACED = 0
        _INSTPREFIX_INJECTED = 0
        _DEPLIBS_REPLACED = 0
        _LADIR_SCANNED = 0
        for dep in self.dependencies.values():
            # R-NEW3 (CI 2026-08-12): guard against transitive deps whose
            # package_folder is None at build() time (conan 2 transitive
            # deps in self.dependencies list may have no resolved package
            # folder when only their requirements are declared). Direct
            # requires always have package_folder.
            if not dep.package_folder:
                continue
            dep_libdir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(dep_libdir):
                continue
            for la_name in os.listdir(dep_libdir):
                if not la_name.endswith(".la"):
                    continue
                _LADIR_SCANNED += 1
                la_path = os.path.join(dep_libdir, la_name)
                try:
                    with open(la_path, "r", encoding="utf-8",
                              errors="replace") as _fh:
                        _la_text = _fh.read()
                except OSError:
                    continue
                _new_text = _la_text
                if _LADIR_BAD.search(_new_text):
                    _new_text = _LADIR_BAD.sub(
                        f"libdir='{dep_libdir}'", _new_text, count=1)
                if _INSTPREFIX_PRESENT.search(_new_text):
                    if _INSTPREFIX_BAD.search(_new_text):
                        _new_text = _INSTPREFIX_BAD.sub(
                            f"inst_prefix_dir='{dep.package_folder}'",
                            _new_text, count=1)
                        _INSTPREFIX_REPLACED += 1
                else:
                    _new_text = _new_text.rstrip("\n") + \
                        f"\ninst_prefix_dir='{dep.package_folder}'\n"
                    _INSTPREFIX_INJECTED += 1
                if _DEPLIBS_BAD.search(_new_text):
                    _new_text = _DEPLIBS_BAD.sub(
                        f"\\g<1>{dep_libdir}", _new_text)
                    _DEPLIBS_REPLACED += 1
                if _new_text != _la_text:
                    try:
                        with open(la_path, "w", encoding="utf-8") as _fh:
                            _fh.write(_new_text)
                        _LADIR_REPLACED += 1
                    except OSError:
                        pass
        self.output.info(
            f"R-NEW: .la libdir sweep: scanned={_LADIR_SCANNED}, "
            f"rewrote_libdir={_LADIR_REPLACED}, "
            f"rewrote_inst_prefix={_INSTPREFIX_REPLACED}, "
            f"injected_inst_prefix={_INSTPREFIX_INJECTED}, "
            f"rewrote_deplibs={_DEPLIBS_REPLACED}"
        )

        apply_conandata_patches(self)

        # Note: actual umask 077 → 022 patch is applied later in build()
        # after autoreconf -fi regenerates configure (the configure
        # script doesn't exist when apply_conandata_patches runs).
        # See _drop_umask_077() helper.

        # The plugin uses a non-standard build flow: no ./configure at the
        # plugin level (plugin.m4 is meant to be sourced by abiword's parent
        # configure.ac). Instead, we replicate the Makefile.am target
        # directly via libtool.
        #
        # Why this works:
        #   1. xp/Makefile.am is a stock noinst_LTLIBRARIES libxp.la.
        #      It only needs $(OPENWRITER_CFLAGS), which we set via
        #      extra_cflags.
        #   2. ./Makefile.am is a stock plugin_LTLIBRARIES openwriter.la
        #      linking xp/libxp.la + $(OPENWRITER_LIBS). We can build
        #      it manually with the right libtool invocation.
        #
        # This sidesteps the upstream assumption that abiword's parent
        # configure must run first.

        from conan.tools.env import Environment
        import os as _os_e10
        env = Environment()
        env.define("VERSION", "3.0.8")
        _e10_inc_flags = []
        _e10_lib_flags = []
        # Walk each transitive dep and emit "-I<inc>" / "-L<lib>" / "-l<lib>"
        # strings directly from conan's cpp_info. The CI worker has no
        # `pkg-config` binary on PATH (PATH=/data/app/bin:/system/bin/...:
        # /vendor/bin:/storage/Users/currentUser/.local/bin) so E10's
        # earlier `subprocess.check_output(["pkg-config", ...])` failed with
        #   FileNotFoundError: [Errno 2] No such file or directory: 'pkg-config'
        # We don't need pkg-config here: PkgConfigDeps already wrote
        # .pc files into generators_folder and we know exactly which
        # four packages we need (libgsf + glib + libffi + fribidi —
        # gobject-2.0 is shipped as part of glib/2.84.0 in this
        # conan recipe). fribidi requires the special "include/fribidi"
        # subdir handling explained inline below (E21). libxml2 added
        # in E36 — see requirements() for the libxml/parser.h
        # transitive-include rationale.
        for _e10_dep_name in ("libgsf", "glib", "libffi", "fribidi", "libxml2"):
            try:
                _e10_dep = self.dependencies[_e10_dep_name]
            except KeyError:
                continue
            if not _e10_dep.package_folder:
                continue
            _e10_pf = _e10_dep.package_folder
            for _e10_inc in _e10_dep.cpp_info.includedirs:
                _e10_inc_flags.append("-I" + _os_e10.path.join(_e10_pf, _e10_inc))
            # E21 (CI 2026-08-13, 25th run): fribidi 1.0.16's upstream
            # `make install` puts headers under <prefix>/include/fribidi/,
            # not directly under <prefix>/include/. The conan recipe's
            # package_info declares only includedirs=["include"], which
            # gives us -I<fribidi_pkg>/include — but abiword's source
            # does `#include <fribidi.h>` (no `fribidi/` prefix), so the
            # header it actually needs lives at <prefix>/include/fribidi/
            # fribidi.h and requires -I<fribidi_pkg>/include/fribidi.
            # Without this fix the build dies with:
            #     /src/af/util/xp/ut_string.h:193:10: fatal error:
            #         'fribidi.h' file not found
            #     #include <fribidi.h>
            # We add the missing subdir explicitly. Touching fribidi's
            # own recipe's package_info would be cleaner but requires
            # a separate PR against archives/f/fribidi/1.0.16/, which
            # is out of scope for the abiword-plugin-openwriter port.
            if _e10_dep_name == "fribidi":
                _e10_inc_flags.append(
                    "-I" + _os_e10.path.join(_e10_pf, "include", "fribidi")
                )
            for _e10_libdir in _e10_dep.cpp_info.libdirs:
                _e10_lib_flags.append("-L" + _os_e10.path.join(_e10_pf, _e10_libdir))
            for _e10_lib in _e10_dep.cpp_info.libs:
                _e10_lib_flags.append("-l" + _e10_lib)
        _pkg_cflags = " ".join(_e10_inc_flags)
        # E26 (CI 2026-08-13, 31st run): the boost shim -I must be in
        # _e10_inc_flags (the list), NOT appended to _pkg_cflags (the
        # string). The downstream code at line ~851 does:
        #     _pkg_cflags = " ".join(_e10_inc_flags)
        # which clobbers any previous `_pkg_cflags += ...` assignments.
        # E23 and E24 both put the boost/ flag on _pkg_cflags via `+=`
        # and got silently dropped. E25 did the same. Adding to
        # _e10_inc_flags BEFORE the join at line ~851 is the only place
        # that survives. Path is build_folder/boost/ because that's
        # where the make command's cwd sees -I<...>/boost/ — see E25.
        # E25 (CI #30): the path was originally -I<source_folder>/boost
        # (write shim at source_folder, point -I there). E25 changed to
        # -I<build_folder>/boost because conan's basic_layout puts the
        # active "make" inside build_folder (which is a subdir of
        # source_folder at build-release/). That works for `#include
        # "boost/shared_ptr.hpp"`-style quoted includes, but pd_Document.h
        # uses angle-brackets `#include <boost/shared_ptr.hpp>`, and the
        # clang preprocessor's angle-bracket search treats the -I path
        # as a base directory and appends the full include name as-is —
        # so `<boost/shared_ptr.hpp>` on -I<b/build-release>/boost looks
        # at `<b/build-release>/boost/boost/shared_ptr.hpp`, which does
        # not exist. E35 (CI #42, current): use -I<build_folder>
        # (parent of boost/), not -I<build_folder>/boost. The shim file
        # is still at <build_folder>/boost/shared_ptr.hpp and remains
        # the shim E25 planted. Same applies to the source_folder copy
        # written earlier in source().
        _e10_inc_flags.append("-I" + self.build_folder)
        # E35b (CI #42): ALSO add -I<source_folder> as a safety net
        # for the same reason — _install_boost_stub() writes a copy of
        # the shim to <source_folder>/boost/shared_ptr.hpp via its
        # `(self.source_folder, self.build_folder)` loop, and the
        # angle-bracket search will reach it the moment -I<source_folder>
        # is on the list. Same fallback rationale as E28's pre-make
        # size check: belt-and-suspenders against HMDFS scrubbing any
        # one of the two copies before clang reads them.
        _e10_inc_flags.append("-I" + self.source_folder)
        # E10c (CI 2026-08-12): xp/*.cpp files reference ~30 abiword
        # internal headers via bare-quoted #include "pd_Style.h" etc.
        # These live under abiword's src/ tree, but NOT at the root —
        # they are scattered across many subdirectories:
        #   src/text/ptbl/xp/pd_Style.h
        #   src/text/fmt/xp/...
        #   src/wp/ap/xp/...
        #   src/wp/impexp/xp/...
        #   src/af/xap/xp/...
        #   src/af/gr/xp/...
        #   src/af/util/xp/...
        #   src/af/ev/xp/...
        #   ... (~30 dirs total across src/{text,wp,af}/**/xp)
        # abiword's parent build walks these in order via Makefile.am's
        # AM_CPPFLAGS = $(WP_CPPFLAGS) which contains per-subdir -I
        # flags accumulated by configure.ac's BASE_CPPFLAGS_ → AF →
        # TEXT → IMPEXP → WP chain. The plugin stand-alone build
        # does not have that machinery, so we have to feed every
        # relevant -I flag explicitly.
        #
        # E10c's first iteration added only "-I<source_folder>/src",
        # which made the preprocessor search the src/ root and
        # produced a clean "fatal error: 'pd_Style.h' file not found"
        # the very first time anything in xp/*.cpp tried to include
        # an abiword internal header. CI 2026-08-12 (tenth run)
        # confirmed: src/ was preserved at source_folder root,
        # -I<src> was passed to clang++, pd_Style.h was still
        # missing because it lives in src/text/ptbl/xp/.
        #
        # The fix: walk src/ recursively, collect every directory
        # that contains a *.h file, and emit one -I flag per dir.
        # Yes, the resulting -I list is ~30 entries long, but it
        # exactly mirrors what abiword's parent build does via
        # WP_CPPFLAGS. Mirrors libgsf's R-NEW strategy of using
        # absolute .pc paths: collect from source_folder instead of
        # asking the autotools machinery to do it.
        _e10_src_root = _os_e10.path.join(self.source_folder, "src")
        for _e10_dirpath, _e10_dirnames, _e10_filenames in (
            _os_e10.walk(_e10_src_root)
        ):
            # Skip dirs that don't contain a header — they're just
            # .cpp/.o holding grounds and adding them bloats the
            # preprocessor's search path with no benefit.
            if not any(_n.endswith(".h") for _n in _e10_filenames):
                continue
            _e10_inc_flags.append("-I" + _e10_dirpath)
        _pkg_cflags = " ".join(_e10_inc_flags)
        _pkg_libs = " ".join(_e10_lib_flags)
        self.output.info(
            f"E10: derived OPENWRITER_CFLAGS={_pkg_cflags!r}"
        )
        self.output.info(
            f"E10: derived OPENWRITER_LIBS={_pkg_libs!r}"
        )
        env.define("OPENWRITER_CFLAGS", _pkg_cflags)
        env.define("OPENWRITER_LIBS", _pkg_libs)
        env_vars = env.vars(self)
        with env_vars.apply():
            # E9 (CI 2026-08-12): the previous code did `self.run(..., env=env_vars)`
            # at L508 / L515 — but env_vars here is a `conan.tools.env.virtualrunenv.VirtualEnv`
            # object, NOT a list of KEY=VALUE strings. conan 2.x's `ConanFile.run()` asserts
            # that `env` is one of: None, a list of "K=V" strings, or a string naming a
            # pre-defined environment profile (e.g. "conanbuild"). Passing the VirtualEnv
            # object blows up with:
            #     AssertionError: env argument to ConanFile.run() should be a list
            # We don't need to pass `env` at all here: we're already inside the
            # `with env_vars.apply():` block, which sets OPENWRITER_CFLAGS / OPENWRITER_LIBS
            # / VERSION in the shell's environment. `make` and libtool subprocesses
            # inherit that env automatically. Drop the env=... argument on both run()s.
            autotools = Autotools(self)
            # The plugin subdir doesn't ship a `configure` script (the
            # upstream plugin.m4 is meant to be sourced by abiword's
            # parent configure.ac — abiword-plugin-openwriter is a SUBDIR
            # of abiword, not a standalone autotools project). To build
            # it standalone we write a minimal configure.ac so autoreconf
            # -fi can produce a working configure + Makefile.in. E6 (CI
            # 2026-08-12): running autoreconf -fi against the abiword
            # project's configure.ac fails with "file 'plugin-list.m4'
            # does not exist"; running it with NO configure.ac fails with
            # "'configure.ac' is required". E7 (CI 2026-08-12 third run):
            # even with stub configure.ac, automake died with:
            #   - "OPENWRITER_BUILTIN does not appear in AM_CONDITIONAL"
            #     (Makefile.am L4: `if OPENWRITER_BUILTIN`)
            #   - "TOOLKIT_COCOA does not appear in AM_CONDITIONAL"
            #     (Makefile.am L22, L29)
            #   - "Libtool library used but 'LIBTOOL' is undefined"
            #     (Makefile.am L5: plugin_LTLIBRARIES = openwriter.la,
            #      xp/Makefile.am L2: noinst_LTLIBRARIES = libxp.la)
            #   - "C++ source seen but 'CXX' is undefined"
            #     (Makefile.am L27: nodist_EXTRA_openwriter_la_SOURCES =
            #      dummy.cpp, xp/Makefile.am L9-13: 3 .cpp files)
            # The stub now declares AM_CONDITIONALs (both stubbed false —
            # openwriter is built as a plugin, not builtin, and we don't
            # target Cocoa), LT_INIT for libtool, and AC_PROG_CXX so the
            # C++ sources get a compiler.
            _STUB_CONFIGURE_AC = (
                "AC_PREREQ([2.69])\n"
                "AC_INIT([openwriter], [3.0.8])\n"
                "AC_CONFIG_SRCDIR([Makefile.am])\n"
                "AC_CONFIG_FILES([Makefile xp/Makefile])\n"
                "AM_INIT_AUTOMAKE([foreign subdir-objects])\n"
                "AM_CONDITIONAL([OPENWRITER_BUILTIN], [false])\n"
                "AM_CONDITIONAL([TOOLKIT_COCOA], [false])\n"
                "LT_INIT\n"
                # E33 (CI 2026-08-13, 39th run): the configure script's
                # AC_PROG_CC / AC_PROG_CXX calls expand to a long probe
                # sequence that AC_LANG_COMPILER runs at ./configure
                # time. The probe tries to compile a tiny conftest.c
                # with $CC, then `ac_link` runs $CC $CFLAGS $LDFLAGS
                # conftest.c ... $LIBS to produce an executable. Under
                # the OHOS HNP sandbox the link step silently fails
                # (the conftest binary's exec or libc/glibc probe
                # returns nonzero) and configure aborts with:
                #     checking whether the C compiler works... no
                #     configure: error: C compiler cannot create
                #                          executables
                # (CI #37, #38 logs) — even though CI_PACKAGES passes
                # tools.build:compiler_executables that point at
                # /data/service/hnp/bin/clang which is perfectly
                # capable of producing aarch64-linux-gnu .so files
                # when our `make` step actually invokes it. The probe
                # is the only thing that breaks; the compiler itself
                # works.
                #
                # E22-E32: every flavor of cache override
                # (`ac_cv_c_compile_works=yes`,
                # `ac_cv_cxx_compile_works=yes`,
                # `ac_cv_prog_cc_cross=yes`, etc.) and host/build
                # canonicalization was attempted — all ineffective
                # because autoconf 2.69's AC_PROG_CC + AC_LANG_COMPILER
                # path runs the live ac_link probe unconditionally
                # once the host != build canonical check passes,
                # regardless of cache state. Verified against the
                # autoconf 2.69 source: _AC_COMPILER_LINK_IFELSE
                # body invokes `ac_link` outside any cache guard.
                #
                # E33 strategy: replace the *probe body* of
                # AC_PROG_CC / AC_PROG_CXX with a no-op that hard-
                # codes CC=cc, CXX=c++, and AC_SUBST's them, but
                # still emits the AM_CONDITIONAL([am__fastdepCXX])
                # and AM_CONDITIONAL([am__fastdepCC]) macros that
                # automake requires. automake's check is on the
                # *presence* of those AM_CONDITIONAL tokens in the
                # m4 expansion of configure.ac (not on whether the
                # actual probe ran). So:
                #
                #   m4_define([AC_PROG_CC],
                #     [AC_REQUIRE([AC_PROG_INSTALL])dnl
                #      AC_SUBST(CC, [cc])
                #      AM_CONDITIONAL([am__fastdepCC], [true])])
                #   m4_define([AC_PROG_CXX],
                #     [AC_SUBST(CXX, [c++])
                #      AM_CONDITIONAL([am__fastdepCXX], [true])])
                #
                # This:
                #   1. automake parser sees literal AC_PROG_CC /
                #      AC_PROG_CXX text in configure.ac.
                #   2. automake's AM_CONDITIONAL scanner sees
                #      am__fastdepCC / am__fastdepCXX tokens after
                #      m4 expansion → "all AM_CONDITIONALs are
                #      declared" check passes.
                #   3. ./configure's probe body is the no-op above —
                #      no ac_link fork+exec, no conftest.c write,
                #      no failure path.
                #   4. CC and CXX get AC_SUBST'd to the autoconf-
                #      conventional defaults ("cc", "c++"), and at
                #      make time the conan buildenv's
                #      CC=/data/service/hnp/bin/clang / CXX=
                #      /data/service/hnp/bin/clang++ overrides take
                #      precedence via env priority. (CI PACKAGE
                #      tools.build:compiler_executables is wired
                #      through conanbuild.sh and exported as the
                #      primary env, so `make` reads clang from
                #      there, not the @CC@ substitution.)
                #
                # E29 (CI #35) attempted a similar m4_define
                # no-op but the replacement body only contained
                # `AC_SUBST(CC, [cc])` / `AC_SUBST(CXX, [c++])`
                # without AM_CONDITIONAL emissions, so automake's
                # "am__fastdepCXX does not appear in AM_CONDITIONAL"
                # still triggered. E30 then reverted to plain
                # AC_PROG_CC/AC_PROG_CXX to recover automake
                # satisfaction but reintroduced the configure probe
                # failure. E33 combines both: AM_CONDITIONAL +
                # AC_SUBST inside the redefined body.
                "m4_define([AC_PROG_CC],\n"
                "          [AC_SUBST(CC, [__OPENWRITER_CC__])dnl\n"
                "           AM_CONDITIONAL([am__fastdepCC], [true])dnl\n"
                "           AM_CONDITIONAL([am__fastdepCXX], [true])])dnl\n"
                "m4_define([AC_PROG_CXX],\n"
                "          [AC_SUBST(CXX, [__OPENWRITER_CXX__])dnl\n"
                "           AM_CONDITIONAL([am__fastdepCXX], [true])])dnl\n"
                "AC_PROG_CC\n"
                "AC_PROG_CXX\n"
                "AC_PROG_INSTALL\n"
                "AC_OUTPUT\n"
            )
            _stub_path = os.path.join(self.source_folder, "configure.ac")
            if not os.path.exists(_stub_path):
                with open(_stub_path, "w", encoding="utf-8") as _f:
                    _f.write(_STUB_CONFIGURE_AC)
                self.output.info(
                    "E6: wrote stub configure.ac for standalone openwriter build"
                )
            self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
            # E114: drop umask 077 from the generated configure (HMDFS)
            # matches the runtime patch block below — apply to source_folder
            # before configure() reads it.
            self._drop_umask_077()
            # Standalone configure isn't strictly needed since the plugin
            # Makefile.am doesn't reference autoconf-generated vars.
            # autotools.configure() is skipped because:
            #
            # E11c (CI 2026-08-12 twelfth run): conan's basic_layout
            # copies source_folder contents to build_folder BEFORE build()
            # runs. This includes Makefile.am, xp/Makefile.am, plugin.m4,
            # and configure.ac (which build() wrote earlier in source_folder,
            # then conan re-copied). However:
            #
            #   1. autotools.configure() by default looks for configure in
            #      source_folder, not build_folder. Even with
            #      build_script_folder=self.build_folder, the AutotoolsToolchain
            #      writes the configure script to build_folder but conan
            #      executes it in build_folder/build-release/ — where the
            #      configure script was NEVER placed, producing:
            #          configure: inaccessible or not found
            #
            #   2. Even if configure were found in build_folder, the same
            #      --build=aarch64-unknown-linux-ohos issue would cause
            #      "C compiler cannot create executables".
            #
            # We bypass the entire conan Autotools layer and run the
            # bootstrap manually: copy configure.ac from source_folder to
            # build_folder (to ensure build_folder has it), run autoreconf
            # in build_folder to produce configure + Makefile.in there, then
            # run configure in build_folder with ac_cv_* overrides. The result
            # is build_folder/Makefile co-located with the source copies,
            # ready for our manual make -C <abs_path> invocation below.
            _run_configure_fallback(self, self.build_folder)

            # E34 (CI 2026-08-13, 41st run): replace the @CC@ / @CXX@
            # placeholder strings that the stub configure.ac's
            # m4_define([AC_PROG_CC/CXX]) wrote into Makefile +
            # xp/Makefile + libtool's internal @CC@/@CXX@ vars. The
            # previous E33 step left them as the autoconf-default
            # bare names ("cc", "c++") — and libtool's compile mode
            # expands `libtool --mode=compile c++ ...` directly into
            # the shell, with no PATH search of the conanbuild env's
            # CXX=/data/service/hnp/bin/clang++ variable. CI #40 log:
            #     /data/service/hnp/bin/bash ../libtool    --mode=compile c++ ...
            #     ../libtool: line 1914: c++: command not found
            # — libtool reads its recorded CXX from the Makefile's
            # `@CXX@` substitution (which E33 set to "c++"), NOT from
            # the runtime $CXX env var that conanbuild.sh exports.
            #
            # The same problem applies to @CC@ even though CI #40 got
            # past the CC step (autoconf's CC detection "succeeded"
            # at the configure stage because the conanbuild env had
            # CC set when AC_LANG_COMPILER ran). But we replace CC
            # too for symmetry and to avoid relying on a coincidence
            # (e.g. a future autoconf upgrade that re-runs CC probe
            # after `AC_OUTPUT`).
            #
            # Source of truth for the path: self.conf.get() reads
            # tools.build:compiler_executables from the conan profile
            # (CI profile ohos-aarch64 has c -> /data/service/hnp/bin/clang,
            #  cpp -> /data/service/hnp/bin/clang++). On native Linux
            # builds the same conf returns the host's system clang,
            # so this code path is portable — no #ifdef OHOS gating.
            _e34_compilers = self.conf.get(
                "tools.build:compiler_executables", default={}
            ) or {}
            _e34_cc = _e34_compilers.get("c") or "cc"
            _e34_cxx = _e34_compilers.get("cpp") or "c++"
            _e34_rewrites = [
                # (makefile_path, old_substring, new_substring). Three
                # targets: the top-level Makefile, the xp/Makefile, and
                # libtool's internal state file (libtool keeps a copy of
                # CC/CXX in `<build>/libtool` for its own --mode=compile
                # to read; both must match).
                (os.path.join(self.build_folder, "Makefile"),
                 "__OPENWRITER_CC__", _e34_cc),
                (os.path.join(self.build_folder, "Makefile"),
                 "__OPENWRITER_CXX__", _e34_cxx),
                (os.path.join(self.build_folder, "xp", "Makefile"),
                 "__OPENWRITER_CC__", _e34_cc),
                (os.path.join(self.build_folder, "xp", "Makefile"),
                 "__OPENWRITER_CXX__", _e34_cxx),
                (os.path.join(self.build_folder, "libtool"),
                 "__OPENWRITER_CC__", _e34_cc),
                (os.path.join(self.build_folder, "libtool"),
                 "__OPENWRITER_CXX__", _e34_cxx),
            ]
            for _e34_path, _e34_old, _e34_new in _e34_rewrites:
                if not os.path.isfile(_e34_path):
                    continue
                with open(_e34_path, "r", encoding="utf-8") as _f:
                    _e34_txt = _f.read()
                _e34_new_txt = _e34_txt.replace(_e34_old, _e34_new)
                if _e34_new_txt == _e34_txt:
                    continue  # placeholder never reached this file
                with open(_e34_path, "w", encoding="utf-8") as _f:
                    _f.write(_e34_new_txt)
                self.output.info(
                    f"E34: rewrote {_e34_old!r} -> {_e34_new!r} "
                    f"in {_e34_path}"
                )

            # Manual build of xp/libxp.la
            # E074 (HMDFS): parallel make hits jobserver fifo EPERM.
            # PR #4119 abiword-plugin-clarisworks L151 uses -j1 for the
            # same reason. We keep the override knob for native Linux
            # builds (-o tools.build:jobs=N) but default to -j1 on OHOS.
            jobs = self.conf.get("tools.build:jobs", default=1)
            if self.settings.os == "OHOS":
                jobs = 1  # E074: HMDFS jobserver fifo EPERM
            # E11a (CI 2026-08-12 eleventh run): basic_layout puts
            # the build under self.build_folder/<build_type>/ (e.g.
            # .../b/build-release/), but `conan create` only copied
            # the source tree to self.build_folder root, NOT to
            # the per-config subdir. The plugin Makefile.am lives at
            # self.build_folder/Makefile.am + self.build_folder/xp/
            # Makefile.am — neither is present under
            # build-release/. `make -C xp` therefore fails with
            # "xp: No such file or directory" because cwd is
            # build-release/ and there is no build-release/xp/.
            #
            # Two ways out:
            #   1. `cd self.build_folder && make -C xp` — change cwd.
            #   2. Pass absolute path to -C: `make -C
            #      self.build_folder/xp`.
            # We pick (2) because it keeps the env-vars context
            # (with env_vars.apply() block above) intact: changing
            # cwd via `cd ...;` between two self.run() invocations
            # would be fine for bash but our environment block uses
            # a Python `with` scope that survives — however some
            # self.run() implementations re-evaluate cwd per call,
            # so passing an explicit absolute -C is the most robust
            # way to anchor the make invocation regardless of
            # whatever cwd conan hands us.
            _xp_dir = _os_e10.path.join(self.build_folder, "xp")
            # E27 (CI 2026-08-13, 33rd run): diagnostic dump before
            # the first make. CI #23-#32 all failed at
            #     'boost/shared_ptr.hpp file not found'
            # despite E25/E26 confirming the shim file at
            # <build_folder>/boost/shared_ptr.hpp and -I<build_folder>/boost
            # in OPENWRITER_CFLAGS. Root cause is unconfirmed; candidates:
            #   (a) xp/Makefile.am uses @OPENWRITER_CFLAGS@ (configure
            #       substitution) instead of $(OPENWRITER_CFLAGS) (make
            #       expansion), and our stub configure.ac does NOT
            #       AC_SUBST it, so @VAR@ stays literal in the generated
            #       Makefile and the -I never reaches clang;
            #   (b) xp/Makefile.am uses a different var name
            #       (OPENWRITER_CPPFLAGS / WP_CPPFLAGS / etc.) that our
            #       env doesn't set;
            #   (c) the shim file is being deleted somewhere between E25
            #       and this make call.
            # These three prints will pinpoint (a) vs (b) vs (c) without
            # another guess-and-check cycle:
            #   1. `make -n V=1 libxp.la` — prints the actual clang
            #      command line (or a shell echo of it). If -I<build>/
            #      boost is absent there, the env var -> CPPFLAGS chain
            #      is broken (cause a or b). If present but file-not-
            #      found persists, the shim was deleted (cause c).
            #   2. xp/Makefile.am raw content — shows what var name
            #      and what expansion syntax the upstream uses.
            #   3. xp/Makefile (post-configure) — shows whether @VAR@
            #      was substituted or left literal.
            # All three prints are guarded by try/except so a missing
            # file doesn't crash the build; we'll still get the other
            # two diagnostics. Output is wrapped at 4 KB so the log
            # stays scannable.
            try:
                self.run(
                    f"make -C {_xp_dir} -n -j1 V=1 libxp.la 2>&1 | "
                    f"head -c 4096",
                    env="conanbuild",
                )
            except Exception as _e27_diag_e:
                self.output.warning(f"E27 dry-run failed: {_e27_diag_e!r}")
            _e27_xp_am = _os_e10.path.join(self.build_folder, "xp", "Makefile.am")
            if _os_e10.path.isfile(_e27_xp_am):
                with open(_e27_xp_am, "r", encoding="utf-8", errors="replace") as _f:
                    self.output.info(
                        "E27 xp/Makefile.am (first 4 KB):\n"
                        + _f.read(4096)
                    )
            else:
                self.output.info(
                    f"E27 xp/Makefile.am NOT FOUND at {_e27_xp_am!r}"
                )
            _e27_xp_mk = _os_e10.path.join(self.build_folder, "xp", "Makefile")
            if _os_e10.path.isfile(_e27_xp_mk):
                with open(_e27_xp_mk, "r", encoding="utf-8", errors="replace") as _f:
                    _mk_content = _f.read(4096)
                # Surface only the lines that mention OPENWRITER or
                    # AM_CPPFLAGS or @VAR@ placeholders, to keep the
                    # log readable.
                _mk_relevant = "\n".join(
                    ln for ln in _mk_content.splitlines()
                    if "OPENWRITER" in ln
                    or "@OPENWRITER" in ln
                    or "AM_CPPFLAGS" in ln
                    or "$(OPENWRITER" in ln
                )[:4096]
                self.output.info(
                    "E27 xp/Makefile (OPENWRITER / AM_CPPFLAGS / @VAR@ "
                    "lines, first 4 KB):\n" + (_mk_relevant or "(none)")
                )
                # Also dump raw @-tokens that survived substitution.
                _at_tokens = [
                    ln.strip() for ln in _mk_content.splitlines()
                    if "@OPENWRITER" in ln or "@CPPFLAGS@" in ln
                    or "@CFLAGS@" in ln or "@CXXFLAGS@" in ln
                ]
                if _at_tokens:
                    self.output.info(
                        "E27 xp/Makefile literal @VAR@ leftovers:\n"
                        + "\n".join(_at_tokens)
                    )
            else:
                self.output.info(
                    f"E27 xp/Makefile NOT FOUND at {_e27_xp_mk!r}"
                )
            # E28 (CI 2026-08-13, 34th run): E27 proved (a) the Makefile
            # uses $(OPENWRITER_CFLAGS) correctly and (b) the actual
            # clang command line passed by libtool DOES contain
            #   -I/.../b/build-release/boost
            # yet clang still reports "boost/shared_ptr.hpp file not
            # found". The shim file MUST therefore be missing at the
            # moment libtool invokes clang, even though E25 logged both
            # writes (source and build) as successful. Three things
            # can erase it between E25 and this line:
            #   (i) HMDFS async cleanup (E114 covers many HMDFS quirks
            #       in this recipe; a newly-created file vanishing
            #       minutes later is plausible on this filesystem);
            #   (ii) conan 2.x's "Copying sources to build folder"
            #        step re-running mid-build (unlikely but E11c/E13
            #        comments disagreed on whether this is automatic);
            #   (iii) some overwrite path in autoreconf -fi or
            #        configure that I missed in the E13 code audit.
            # The previous five rounds (E23-E26) all changed the wrong
            # layer (env var / CFLAGS string / shim file path); this
            # dump proves those layers are all correct. So the bug is
            # purely in the file's persistence on disk.
            #
            # Fix strategy for E28:
            #   1. ls + stat + cat the shim right before the real make
            #      so the next CI run tells us whether the file is
            #      present and intact;
            #   2. Re-write the shim unconditionally right before
            #      libtool spawns clang (defeats any HMDFS async
            #      cleanup that targeted the original write);
            #   3. Also expose the shim at a second path
            #      (<source_folder>/boost, where E25 already wrote it
            #      and which the Makefile.am's -I list doesn't reach),
            #      and add -I<source_folder>/boost to OPENWRITER_CFLAGS
            #      as a belt-and-suspenders fallback.
            _e28_boost_dir = _os_e10.path.join(self.build_folder, "boost")
            _e28_boost_hpp = _os_e10.path.join(_e28_boost_dir, "shared_ptr.hpp")
            try:
                _e28_ls = sorted(_os_e10.listdir(_e28_boost_dir))
            except Exception as _e28_ls_e:
                _e28_ls = f"listdir failed: {_e28_ls_e!r}"
            _e28_exists = _os_e10.path.isfile(_e28_boost_hpp)
            _e28_size = (
                _os_e10.path.getsize(_e28_boost_hpp)
                if _e28_exists else -1
            )
            _e28_mtime = (
                _os_e10.path.getmtime(_e28_boost_hpp)
                if _e28_exists else -1.0
            )
            _e28_head = ""
            if _e28_exists:
                with open(_e28_boost_hpp, "r", encoding="utf-8",
                          errors="replace") as _f:
                    _e28_head = _f.read(200)
            self.output.info(
                "E28 pre-make boost shim check:\n"
                f"  path:    {_e28_boost_hpp}\n"
                f"  exists:  {_e28_exists}\n"
                f"  size:    {_e28_size}\n"
                f"  mtime:   {_e28_mtime}\n"
                f"  ls dir:  {_e28_ls}\n"
                f"  head:    {_e28_head!r}"
            )
            # Re-write unconditionally: same content, same perms. This
            # is a no-op if the file is already correct (open with "w"
            # truncates + writes) and resurrects it if HMDFS quietly
            # deleted it. Idempotent and cheap (one fwrite of ~470 B).
            _os_e10.makedirs(_e28_boost_dir, exist_ok=True)
            with open(_e28_boost_hpp, "w", encoding="utf-8") as _f:
                _f.write(
                    "#ifndef BOOST_SHARED_PTR_HPP_MINIMAL_SHIM\n"
                    "#define BOOST_SHARED_PTR_HPP_MINIMAL_SHIM\n"
                    "#include <memory>\n"
                    "namespace boost {\n"
                    "template <typename T>\n"
                    "using shared_ptr = std::shared_ptr<T>;\n"
                    "template <typename T>\n"
                    "using weak_ptr = std::weak_ptr<T>;\n"
                    "template <typename T>\n"
                    "using enable_shared_from_this = "
                    "std::enable_shared_from_this<T>;\n"
                    "}\n"
                    "#endif\n"
                )
            self.output.info(
                "E28: re-wrote shim at "
                f"{_e28_boost_hpp} "
                f"(size={_os_e10.path.getsize(_e28_boost_hpp)})"
            )
            self.run(
                f"make -C {_xp_dir} -j{jobs} libxp.la",
            )
            # Manual build of ./openwriter.la (plugin module).
            #
            # E37 (CI 2026-08-13, 43rd run): invoking
            #     make -C $build_folder -j1 openwriter.la
            # fails at the libtool link step with:
            #     libtool: error: argument to -rpath is not absolute: xp/libxp.la
            # Root cause: upstream Makefile.am declares
            #     openwriter_la_LIBADD = xp/libxp.la
            #     openwriter_la_LDFLAGS = $(OPENWRITER_LIBS) \
            #         -avoid-version -module -no-undefined
            # and triggers automake's standard _LTLIBRARIES link recipe,
            # which expands to:
            #     libtool --mode=link CC ... -o openwriter.la \
            #         -rpath $(plugindir) xp/libxp.la <OPENWRITER_LIBS>
            # $(plugindir) is the automake-generated install path
            # substitution. Our stub configure.ac does NOT call
            # AC_SUBST(plugindir) (and even if it did, automake's
            # _LTLIBRARIES link rule expects an absolute install path;
            # our --prefix=/ + --libdir=/lib has no /plugins subdir),
            # so the resulting link command ends up with:
            #     -rpath   xp/libxp.la ...
            # (empty string between -rpath and xp/libxp.la — the
            # prev line in the CI log shows the literal whitespace).
            # libtool then parses `xp/libxp.la` as the -rpath value and
            # rejects it as "not absolute".
            #
            # Several less-invasive fixes were considered:
            #  (a) Set openwriter_la_LDFLAGS += -rpath /some/abs/path
            #      by post-editing the generated Makefile just before
            #      make. Fragile: automake may reorder/restructure the
            #      link recipe across versions, and a hole in the
            #      ordering between LDFLAGS and LIBADD reintroduces the
            #      bug. Would also need to define $(plugindir) for the
            #      Makefile.am's INCLUDES substitution chain.
            #  (b) Define plugindir in configure.ac via
            #      AC_SUBST(plugindir, [/lib/abiword-3.0/plugins])
            #      and inject it into openwriter_la_LDFLAGS via a
            #      post-configure patch. Still depends on automake's
            #      _LTLIBRARIES rule not shuffling the relative order
            #      of -rpath and LIBADD tokens.
            #  (c) Bypass automake's link rule entirely and invoke
            #      libtool --mode=link directly with an explicit
            #      -rpath value. CI reuses the libtool that we already
            #      installed via `tool_requires("libtool/2.5.4")`, so
            #      `libtool` is on PATH. This matches what we already
            #      do for E11a's xp/libxp.la (which IS driven by the
            #      framework's `make -C xp/ libxp.la` rule and therefore
            #      works because xp/Makefile.am's noinst_LTLIBRARIES
            #      doesn't try to install — it just links into .libs/).
            #
            # We pick (c) for symmetry with the xp/libxp.la build that
            # we already drive manually via make. The link command
            # mirrors what automake would generate for a STANDALONE
            # plugin (no install hook), and -rpath is hardcoded to a
            # plausible plugin install path that we will never actually
            # `make install` to (we copy the .la/.so directly into
            # package_folder via package()). The -rpath value is
            # therefore only consulted by libtool's link-time reasoning
            # about dlopen dependency resolution — it doesn't need to
            # exist on the OHOS device at runtime, because the
            # downstream abiword recipe's own -rpath to libabiword
            # wins for the SONAME chain.
            self.run(
                "libtool --mode=link /data/service/hnp/bin/clang++ "
                "-fPIC -O2 -stdlib=libc++ -std=c++17 -O3 "
                "-avoid-version -module -no-undefined "
                "-o openwriter.la "
                "-rpath /lib/abiword-3.0/plugins "
                "xp/libxp.la "
                f"{_pkg_libs}",
                cwd=self.build_folder,
                env="conanbuild",
            )

    def package(self):
        # Copy the .la + .so (or .a if static) + .deps/ into package_folder.
        # We DON'T do `make install` because that requires libabiword
        # headers (plugin framework headers are installed by abiword's
        # own recipe). Instead, we copy the built artifacts and a
        # minimal ABI surface.
        #
        # IMPORTANT: also copy .deps/ (libtool dependency stubs). libtool
        # records transitive dependency paths in .la files via relative
        # refs to .deps/*.Plo files. Without .deps/ the downstream
        # consumer's libtool relink fails with "cannot find dependency".
        # Same rationale as PR #4119 abiword-plugin-clarisworks L163.
        copy(self, "*.la",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)
        copy(self, "*.so*",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)
        copy(self, "*.a",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)
        # .deps/ lives alongside the .la/.so under the build folder
        # (libtool default). We mirror the layout so relative refs like
        # `dependency_libs=' ... .deps/libxp.Plo'` resolve correctly.
        copy(self, "*",
             src=os.path.join(self.build_folder, ".deps"),
             dst=os.path.join(self.package_folder, "lib", ".deps"),
             keep_path=False)
        # Copy xp/ headers if any (none currently, but future-proof)
        copy(self, "*.h",
             src=os.path.join(self.build_folder, "xp"),
             dst=os.path.join(self.package_folder, "include"),
             keep_path=False)

    def package_info(self):
        # The plugin .la lives under <package>/lib/openwriter.la. libtool
        # consumers should dlopen() it; ABI consumers should link via
        # -lopenwriter.
        self.cpp_info.libs = ["openwriter"]
        self.cpp_info.set_property("cmake_file_name", "openwriter")
        self.cpp_info.set_property("cmake_target_name", "openwriter::plugin")
        self.cpp_info.set_property("pkg_config_name", "openwriter-plugin")
        # Forward libgsf + glib so consumers don't need to redeclare
        # (mirroring libgsf's requires=[] forwarding pattern).
        self.cpp_info.requires = [
            "libgsf::libgsf",
            "glib::glib",
            # E-new: fribidi/1.0.16 is a *direct* dependency (ut_string.h
            # unconditionally `#include <fribidi.h>`). Conan 2.x's
            # package_info validator walks every entry in self.requires()
            # and errors out if the recipe hasn't announced a forwarding
            # cpp_info.requires / cpp_info.components[X].requires line
            # that names it. Without these entries, conan create aborts
            # at the very end with:
            #     ERROR: package_info(): The direct dependency 'fribidi'
            #     is not used by any '(cpp_info/components).requires'.
            # Same for libxml2/2.15.3 — declared in requirements() because
            # libgsf's gsf-libxml.h unconditionally includes
            # <libxml/parser.h>, so we owe libxml2 a forwarding line too.
            # E-ffi (CI 2026-08-17): libffi/3.4.4 also gets a forwarding
            # line for the same validator reason (see requirements() for
            # why it's a direct dep — CI L0i AST scan coverage gap on
            # transitive deps). Same package_info validator rule applies.
            "fribidi::fribidi",
            "libxml2::libxml2",
            "libffi::libffi",
        ]
        self.cpp_info.system_libs = ["m", "pthread", "rt", "dl"]
