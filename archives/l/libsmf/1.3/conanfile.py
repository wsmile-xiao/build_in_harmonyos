#!/usr/bin/env python3
"""Conan recipe — libsmf 1.3 (Autotools)"""
import glob
import json
import os
import re
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps, PkgConfigDeps
from conan.tools.layout import basic_layout

# Recipe-internal install(1) shim (aircrack/1.7 merged precedent, same HMBS
# platform capabilities: install_shim=true, chmod=0, hardlink=0).
#
# AC_PROG_INSTALL bakes the HMBS install shim absolute path into every
# generated Makefile (INSTALL='<runtime>/bin/install -c'). That shim cannot
# install libtool static archives: the copy never lands, and libtool's
# post-install `chmod 644 <dest>` then dies with
# "cannot access .../p//lib/libsmf.a: No such file or directory".
# This shim ignores mode bits (chmod unsupported), copies files with cp(1)
# and creates directories with mkdir -p. It is invoked as
# INSTALL="/bin/sh <shim>" on the make command line (NOT via PATH, NOT as
# bare `sh`, because Makefiles carry the absolute path and ltmain
# func_mode_install only honours a multi-word INSTALL whose first word is
# $SHELL or literal /bin/sh).
_INSTALL_SHIM = r"""#!/bin/sh
# install(1) shim for the HarmonyOS PC target filesystem
# (hmbs capabilities: install_shim=true, chmod=0, hardlink=0).
# Mode flags are ignored (chmod unsupported); files are copied with
# cp(1), directories are created with mkdir -p.
is_dir=0
mk_leading=0
files=
while [ "$#" -gt 0 ]; do
  case "$1" in
    -d) is_dir=1 ;;
    -D) mk_leading=1 ;;
    -m) shift ;;
    -m?*|--mode=*) ;;
    -c|-p|-v|-s) ;;
    -g|-o|-t) shift ;;
    --) shift
        while [ "$#" -gt 0 ]; do files="$files $1"; shift; done
        break ;;
    -*) ;;
    *) files="$files $1" ;;
  esac
  shift
done

[ -z "$files" ] && exit 0

if [ "$is_dir" = 1 ]; then
  for d in $files; do mkdir -p "$d" || exit 1; done
  exit 0
fi

set -- $files
count=$#
[ "$count" -lt 2 ] && exit 0
if [ "$count" -ge 3 ]; then
  # multi-source install: last argument is the destination directory;
  # ensure it exists (rules usually mkdir it first, be defensive)
  eval "dest=\${$count}"
  mkdir -p "$dest" || exit 1
elif [ "$mk_leading" = 1 ]; then
  # -D with a single source: create the destination's parent directory
  eval "dest=\${$count}"
  mkdir -p "$(dirname "$dest")" || exit 1
fi
cp -f "$@" || exit 1
exit 0
"""


class LibsmfConan(ConanFile):
    name = "libsmf"
    version = "1.3"
    description = "Standard MIDI File format library for handling SMF (.mid) files"
    license = "BSD-2-Clause"
    homepage = "https://sourceforge.net/projects/libsmf/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # NOTE: use uploaded glib/2.88.0.1 (vendored libffi meson
        # subproject, closure pcre2/10.45 + zlib/1.3.1.1.1.1). The 2.84 line
        # (2.84.0/2.84.0.1) pulls external libffi/3.4.4 whose old autotools
        # recipe fails on preflight configure with
        # "/data/service/hnp/bin/bash: inaccessible or not found" (Error
        # 127); 2.88.0.1 builds libffi offline inside glib so that node is
        # never built. Precedent: cassbeam notes 2.84.0 built-local only,
        # 2.88.0 uploaded/resolvable.
        self.requires("glib/2.88.0.1", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def build_requirements(self):
        # True-machine/CI workers have no system pkg-config on PATH (HMBS
        # only injects cmake/make/ninja/python3); libsmf configure uses
        # PKG_CHECK_MODULES(GLIB) which execs `pkg-config`. Pull pkgconf
        # from ohpcd (gulkan/0.15.1, fcft/3.3.3, ekg2/0.3.1 precedent).
        self.tool_requires("pkgconf/3.0.5")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _resolve_tmpdir(self):
        """Return a writable tmpdir (readonly_tmp: OHOS /tmp is erofs).

        Priority: HMBS-injected HMBS_AUTOCONF_MKTEMP_FALLBACK (when path-like),
        then HMBS_TMPDIR/TMPDIR/TMP/TEMP (skipping bare /tmp), each created and
        write-probed. Final fallback is a build-folder-local directory.
        Only replaces the temp-file root; never deletes tests.
        """
        candidates = []
        fallback_var = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK", "")
        if fallback_var and fallback_var not in ("0", "1"):
            candidates.append(fallback_var)
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(var, "")
            if val and val != "/tmp" and val not in candidates:
                candidates.append(val)
        for cand in candidates:
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs_probe")
                with open(probe, "w", encoding="utf-8") as handle:
                    handle.write("probe")
                try:
                    os.remove(probe)
                except OSError:
                    pass
                return cand
            except OSError:
                continue
        fallback = os.path.join(self.build_folder or os.getcwd(), ".conan_tmp")
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            pass
        return fallback

    def _resolve_pkg_config(self):
        """Return an existing pkg-config/pkgconf binary path.

        The preflight runner has no system pkg-config; configure's
        PKG_CHECK_MODULES first probes $PKG_CONFIG (ac_cv_path_PKG_CONFIG
        override) then PATH for `pkg-config`. The ohpcd pkgconf package
        ships `bin/pkgconf` (no `pkg-config` alias), so PATH alone is not
        enough. Probe order: conf tools.gnu:pkg_config if it is a file ->
        build-require pkgconf package bin -> PATH via shutil.which.
        """
        try:
            conf_val = self.conf.get("tools.gnu:pkg_config", default=None)
        except Exception:
            conf_val = None
        if conf_val and os.path.isfile(str(conf_val)):
            return str(conf_val)
        try:
            build_deps = getattr(self.dependencies, "build", {})
            pkgconf_dep = build_deps.get("pkgconf") if build_deps else None
            if pkgconf_dep is not None:
                pkg_folder = getattr(pkgconf_dep, "package_folder", "")
                if pkg_folder:
                    for name in ("pkgconf", "pkg-config"):
                        candidate = os.path.join(pkg_folder, "bin", name)
                        if os.path.isfile(candidate):
                            return candidate
        except Exception:
            pass
        for name in ("pkg-config", "pkgconf"):
            found = shutil.which(name)
            if found:
                return found
        return None

    def _ohos_shell(self):
        """Return first existing shell (HMBS /bin/sh preferred).

        The repo CI profile exports CONFIG_SHELL/SHELL as
        /data/service/hnp/bin/bash, which is missing on HMBS preflight
        runners (configure: inaccessible or not found). Probe the
        filesystem instead of trusting the profile value.
        """
        for cand in (
            os.environ.get("SHELL"),
            os.environ.get("CONFIG_SHELL"),
            "/bin/sh",
            "/system/bin/sh",
            "/data/service/hnp/bin/bash",
        ):
            if cand and os.path.isfile(cand):
                return cand
        return "/bin/sh"

    @staticmethod
    def _req_name(_ref, _dep=None):
        """Extract package name from Conan 2 Requirement/Dependency pair.

        Conan 2.30 Requirement has no `.name`; the name lives on
        Requirement.ref.name (likewise Dependency.ref.name). Probe both
        objects so host/build filtering works instead of silently matching
        nothing (getattr(_ref, 'name', '') always returned '').
        """
        for _obj in (_ref, _dep):
            if _obj is None:
                continue
            try:
                _n = getattr(_obj, "name", None)
                if _n:
                    return _n
            except Exception:
                pass
            try:
                _r = getattr(_obj, "ref", None)
                if _r is not None:
                    _n = getattr(_r, "name", None)
                    if _n:
                        return _n
            except Exception:
                pass
        return ""

    def _la_free_dir(self):
        """Build-private directory holding clean .a copies (E236)."""
        base = self.build_folder or self.generators_folder or os.getcwd()
        return os.path.join(base, "la-free")

    def _prepare_la_free(self):
        """E236 scoped-la-free-static-archive-directory.

        Published pcre2/glib/zlib Conan packages ship libtool *.la files
        whose libdir was recorded as '//lib' (prefix=/ on the release
        worker). Libtool probes lib<name>.la BEFORE lib<name>.a in each -L
        dir, so the libsmf link resolves '//lib/libpcre2-8.la' and dies
        with "is not a valid libtool archive". Copy only the static
        archives into a build-private directory with no .la metadata and
        reference it via -L/-l (never absolute .a via LIBADD, never mutate
        the Conan cache). Returns the directory path.
        """
        la_free = self._la_free_dir()
        try:
            os.makedirs(la_free, exist_ok=True)
        except OSError:
            pass
        try:
            host_deps = self.dependencies.host
        except Exception:
            host_deps = self.dependencies
        try:
            items = list(host_deps.items())
        except Exception:
            items = []
            try:
                for _ref, _d in self.dependencies.items():
                    items.append((_ref, _d))
            except Exception:
                pass
        for _ref, _dep in items:
            try:
                _name = self._req_name(_ref, _dep)
            except Exception:
                _name = ""
            if _name in ("pkgconf",):
                continue
            try:
                _pkg = getattr(_dep, "package_folder", "") or ""
                _info = _dep.cpp_info.aggregated_components()
                _libdirs = list(getattr(_info, "libdirs", []) or [])
            except Exception:
                continue
            for _d in _libdirs:
                _ad = _d if os.path.isabs(_d) else os.path.join(_pkg, _d)
                try:
                    _files = os.listdir(_ad)
                except OSError:
                    continue
                for _f in _files:
                    # Static archives plus shared objects: glib defaults to
                    # shared so -lglib-2.0 needs a .so shadow as well,
                    # otherwise libtool falls through la-free back to the
                    # poisoned package dir.
                    _is_a = _f.endswith(".a")
                    _is_so = ".so" in _f and (_f.endswith(".so") or ".so." in _f)
                    if not (_is_a or _is_so):
                        continue
                    _src = os.path.join(_ad, _f)
                    _dst = os.path.join(la_free, _f)
                    if os.path.lexists(_dst):
                        continue
                    try:
                        if os.path.islink(_src):
                            _target = os.readlink(_src)
                            try:
                                os.symlink(_target, _dst)
                            except OSError:
                                shutil.copy2(_src, _dst)
                        else:
                            shutil.copy2(_src, _dst)
                    except OSError:
                        continue
        return la_free

    def _glib_la_free_flags(self, la_free):
        """Build GLIB_CFLAGS/GLIB_LIBS routed through la-free first.

        Both-variables-set bypasses pkg.m4 PKG_CHECK_MODULES so the
        poisoned -L dirs from glib-2.0.pc never reach the libtool command
        line. Values are derived from the live dependency graph (no
        hardcoded absolute paths): -I from every host dep include dir,
        -L with la-free first then each dep libdir as fallback, -l from
        every host dep lib + system_lib (deduplicated, dependency order
        preserved so static link order stays valid).
        """
        try:
            host_deps = self.dependencies.host
        except Exception:
            host_deps = self.dependencies
        try:
            items = list(host_deps.items())
        except Exception:
            items = []
        incs = []
        seen_inc = set()
        libs = []
        seen_lib = set()
        syslibs = []
        seen_sys = set()
        for _ref, _dep in items:
            try:
                _name = self._req_name(_ref, _dep)
            except Exception:
                _name = ""
            if _name in ("pkgconf",):
                continue
            try:
                _pkg = getattr(_dep, "package_folder", "") or ""
            except Exception:
                _pkg = ""
            try:
                _infos = [_dep.cpp_info] + list(_dep.cpp_info.components.values())
            except Exception:
                try:
                    _infos = [_dep.cpp_info]
                except Exception:
                    continue
            for _info in _infos:
                for _p in getattr(_info, "includedirs", []) or []:
                    _a = _p if os.path.isabs(_p) else os.path.join(_pkg, _p)
                    if _a not in seen_inc and os.path.isdir(_a):
                        seen_inc.add(_a)
                        incs.append("-I" + _a)
                for _lib in getattr(_info, "libs", []) or []:
                    _f = "-l" + _lib
                    if _f not in seen_lib:
                        seen_lib.add(_f)
                        libs.append(_f)
                for _lib in getattr(_info, "system_libs", []) or []:
                    _f = "-l" + _lib
                    if _f not in seen_lib and _f not in seen_sys:
                        seen_sys.add(_f)
                        syslibs.append(_f)
        cflags = " ".join(incs)
        # NOTE (round 7): emit ONLY -L la-free. Appending the raw dependency
        # libdirs here re-exposes the stale .la files to libtool's
        # -L-ordered probe and defeats the isolation, so they are deliberately
        # omitted (all required archives/objects are shadowed in la-free).
        ldflags = "-L" + la_free
        all_libs = " ".join(libs + syslibs)
        if "-lm" not in seen_lib and "-lm" not in seen_sys:
            all_libs = (all_libs + " -lm").strip()
        glib_libs = (ldflags + " " + all_libs).strip()
        return cflags, glib_libs

    def _sanitize_dependency_la(self):
        """Delete stale dependency *.la metadata before configure/make.

        Round-7 different strategy (bookloupe/2.0 + cyrus-sasl/2.1.28 merged
        precedent): the round-6 GLIB_LIBS la-free bypass alone did not move
        the failure because automake's LINK order places AutotoolsDeps
        LDFLAGS (-L of every dependency, carrying the poisoned dirs) BEFORE
        LIBADD ($(GLIB_LIBS)) on the libtool command line, so libtool still
        probes the stale lib<name>.la first. Removing the stale *.la files
        wins regardless of -L ordering: libtool then falls back to the
        sibling .a/.so, whose link info is already provided by .pc +
        cpp_info. Only *.la metadata is removed; no archive or binary is
        touched, and the action is logged per file.
        """
        try:
            host_deps = self.dependencies.host
        except Exception:
            host_deps = self.dependencies
        try:
            items = list(host_deps.items())
        except Exception:
            items = []
        for _ref, _dep in items:
            try:
                _name = self._req_name(_ref, _dep)
            except Exception:
                _name = ""
            if _name in ("pkgconf",):
                continue
            try:
                _pkg = getattr(_dep, "package_folder", "") or ""
                _info = _dep.cpp_info.aggregated_components()
                _libdirs = list(getattr(_info, "libdirs", []) or [])
            except Exception:
                continue
            for _d in _libdirs:
                _ad = _d if os.path.isabs(_d) else os.path.join(_pkg, _d)
                try:
                    _files = os.listdir(_ad)
                except OSError:
                    continue
                for _f in _files:
                    if not _f.endswith(".la"):
                        continue
                    _la = os.path.join(_ad, _f)
                    try:
                        os.remove(_la)
                        self.output.info("OHOS E236 sanitize: removed stale %s" % _la)
                    except OSError as _e:
                        self.output.warning("OHOS E236 sanitize skip %s: %s" % (_la, _e))

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()
        # PKG_CHECK_MODULES(glib) needs glib-2.0.pc on PKG_CONFIG_PATH;
        # AutotoolsDeps alone only carries CFLAGS/LDFLAGS.
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        # libsmf 1.3 ships a 2010-vintage config.sub that predates the
        # aarch64/OHOS triplets: `aarch64-linux-ohos' and even
        # `aarch64-unknown-linux-musl' are rejected as "machine not
        # recognized", while `aarch64-unknown-linux-gnu' canonicalizes
        # cleanly. Passing an explicit --build/--host both skips the
        # HMDFS-hostile config.guess probe (E129 family: mktemp dummy.c
        # Permission denied) and satisfies the old config.sub.
        # build == host keeps configure on the native path so its
        # run-time probes execute normally.
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        # smfsh has optional readline support (fancy command-line editing);
        # it pulls in readline+ncurses for an interactive shell only.
        # Disable it to keep this package dependency-closed on glib.
        tc.configure_args.append("--with-readline=no")
        tc.configure_args.append("--disable-dependency-tracking")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        else:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        if self.settings.os == "OHOS":
            # readonly_tmp + E165/HMBS shell: os.environ alone loses to the
            # aggregated Conan buildenv at self.run time (Autotools helper
            # runs with env="conanbuild"; profile [buildenv] wins). Inject
            # via the toolchain environment (lands in conanbuild*.sh) plus
            # a saved hmbs_shell script; build() re-applies on top via
            # on-disk conanbuild*.sh patch (courier-unicode/2.6.0 precedent,
            # conan 2.29/2.30 has no environment_append).
            tmpdir = self._resolve_tmpdir()
            try:
                os.makedirs(tmpdir, exist_ok=True)
            except OSError:
                pass
            shell = self._ohos_shell()
            env = tc.environment()
            env.define("TMPDIR", tmpdir)
            env.define("TMP", tmpdir)
            env.define("TEMP", tmpdir)
            env.define("TMP_DIR", tmpdir)
            env.define("SHELL", shell)
            env.define("CONFIG_SHELL", shell)
            # pkgconf ships bin/pkgconf (no pkg-config alias); configure
            # honours $PKG_CONFIG as an override (ac_cv_path_PKG_CONFIG),
            # so export the resolved absolute path when found.
            _pkg_config = self._resolve_pkg_config()
            if _pkg_config:
                env.define("PKG_CONFIG", _pkg_config)
            # E236: poisoned dependency .la (libdir='//lib' in pcre2/glib
            # packages) makes libtool die on '//lib/libpcre2-8.la'. Route
            # GLIB_CFLAGS/GLIB_LIBS through a build-private la-free dir
            # (-L la-free first, no absolute .a, cache untouched); the
            # both-variables-set bypasses pkg.m4 so poisoned -L dirs never
            # reach the libtool command line (bitlbee-facebook/ezstream
            # precedent).
            _la_free = self._prepare_la_free()
            _glib_cflags, _glib_libs = self._glib_la_free_flags(_la_free)
            if _glib_cflags:
                env.define("GLIB_CFLAGS", _glib_cflags)
            if _glib_libs:
                env.define("GLIB_LIBS", _glib_libs)
            self.output.info("OHOS E236 la-free: %s (%s)" % (_la_free, _glib_libs))
            tc.generate(env=env)
            keep = Environment()
            keep.define("SHELL", shell)
            keep.define("CONFIG_SHELL", shell)
            keep.define("TMPDIR", tmpdir)
            keep.define("TMP", tmpdir)
            keep.define("TEMP", tmpdir)
            keep.define("TMP_DIR", tmpdir)
            if _pkg_config:
                keep.define("PKG_CONFIG", _pkg_config)
            if _glib_cflags:
                keep.define("GLIB_CFLAGS", _glib_cflags)
            if _glib_libs:
                keep.define("GLIB_LIBS", _glib_libs)
            keep.vars(self).save_sh("hmbs_shell")
        else:
            tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os == "OHOS":
            self._patch_ohos_build_scripts()
            shell, tmpdir = self._sanitize_ohos_env()
            self._override_conan_buildenv(shell, tmpdir)
            self._ensure_ohos_compiler()
            # E236 belt-and-braces: regenerate the la-free dir here as well
            # (generate() already did; build_folder survives between the two
            # phases) and mirror GLIB_* into os.environ so even a fallback
            # configure path sees the clean flags.
            try:
                _la_free = self._prepare_la_free()
                _cflags, _libs = self._glib_la_free_flags(_la_free)
                if _cflags:
                    os.environ["GLIB_CFLAGS"] = _cflags
                if _libs:
                    os.environ["GLIB_LIBS"] = _libs
                self.output.info("OHOS E236 la-free (build): %s (%s)" % (_la_free, _libs))
            except Exception as _e:
                self.output.warning("OHOS E236 la-free rebuild skipped: %s" % _e)
            # Round-7 different strategy: sanitize stale dependency *.la
            # BEFORE configure/make (LINK-order-proof; see method docstring).
            # Runs after the la-free rebuild so every -l still resolves.
            try:
                self._sanitize_dependency_la()
            except Exception as _e:
                self.output.warning("OHOS E236 sanitize skipped: %s" % _e)
            try:
                os.chdir(self.build_folder)
            except OSError:
                pass
            # HMDFS getcwd fallback: autoconf checks $PWD first.
            try:
                if self.build_folder:
                    os.environ["PWD"] = self.build_folder
            except Exception:
                pass
        else:
            # Non-OHOS: keep prior minimal writable-tmp handling.
            bf = self.build_folder
            if bf and os.path.isdir(bf):
                try:
                    os.chdir(bf)
                except OSError:
                    pass
                os.environ["PWD"] = bf
            tmpdir = self._resolve_tmpdir()
            for _k in ("TMPDIR", "TMP", "TEMP"):
                os.environ[_k] = tmpdir
            _shell = os.environ.get("SHELL", "") or "/bin/sh"
            os.environ["SHELL"] = _shell
            os.environ["CONFIG_SHELL"] = _shell
        autotools = Autotools(self)
        if self.settings.os == "OHOS":
            self._probe_ohos_compiler()
        try:
            autotools.configure()
        except Exception:
            self._dump_config_log()
            raise
        # Single job: parallel make hits HMDFS jobserver fifo EPERM (E074).
        autotools.make(args=["-j1"])

    def package(self):
        if self.settings.os == "OHOS":
            shell, tmpdir = self._sanitize_ohos_env()
            self._override_conan_buildenv(shell, tmpdir)
            # HMBS install-shim/chmod=0 (aircrack/1.7 merged precedent):
            # AC_PROG_INSTALL bakes the HMBS install shim into Makefiles and
            # that shim cannot install libtool static archives (the copy
            # never lands, then libtool's post-install `chmod 644` dies with
            # ENOENT on p//lib/libsmf.a). Override INSTALL/INSTALL_DATA on
            # the make command line with the recipe-internal shim. First word
            # must be literal /bin/sh for ltmain func_mode_install dispatch
            # (bare `sh` misparses shim path + flags as files to install).
            # Invoked as `sh <script>`, so no exec bit is needed (chmod=0).
            shim_path = os.path.join(self.build_folder, "install-shim.sh")
            with open(shim_path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(_INSTALL_SHIM)
            self.output.info("OHOS install shim written: %s" % shim_path)
            cmd = (
                'make install DESTDIR="%s" '
                'INSTALL="/bin/sh %s" '
                "INSTALL_DATA='$(INSTALL)'"
            ) % (self.package_folder, shim_path)
            self.run(cmd, cwd=self.build_folder, env="conanbuild")
        else:
            autotools = Autotools(self)
            autotools.install()
        # Drop obsolete libtool archives; Conan tracks linkage itself.
        for _la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            try:
                os.remove(_la)
            except OSError:
                pass

    def package_info(self):
        self.cpp_info.libs = ["smf"]
        # smfsh CLI is installed to bin/; declare explicitly so the
        # consumer runenv PATH wiring carries it (preflight showed a bare
        # `smfsh` lookup failing under env="conanrun").
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "smf")
        self.cpp_info.set_property("cmake_target_name", "smf::smf")
        self.cpp_info.set_property("pkg_config_name", "smf")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]

    # ---- OHOS helpers (courier-unicode/2.6.0 precedent, adapted) ----

    def _sanitize_ohos_env(self):
        """Point SHELL/CONFIG_SHELL/TMPDIR at existing writable locations."""
        shell = self._ohos_shell()
        for key in ("SHELL", "CONFIG_SHELL"):
            cur = os.environ.get(key, "")
            if cur and not os.path.isfile(cur):
                os.environ[key] = shell
                self.output.info("OHOS env fix: %s=%s (was missing %s)" % (key, shell, cur))
        tmpdir = self._resolve_tmpdir()
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        for key in ("TMPDIR", "TMP", "TEMP", "TMP_DIR"):
            os.environ[key] = tmpdir
        # Wire the pkgconf binary via $PKG_CONFIG (configure override).
        _pkg_config = self._resolve_pkg_config()
        if _pkg_config:
            os.environ["PKG_CONFIG"] = _pkg_config
            self.output.info("OHOS pkg-config: PKG_CONFIG=%s" % _pkg_config)
        else:
            self.output.warning("OHOS pkg-config not found (configure PKG_CHECK_MODULES will fail)")
        try:
            if self.build_folder:
                os.environ["PWD"] = self.build_folder
        except Exception:
            pass
        self.output.info("OHOS shell/tmpdir: shell=%s tmpdir=%s" % (shell, tmpdir))
        return shell, tmpdir

    def _override_conan_buildenv(self, shell, tmpdir):
        """Force probed shell/tmpdir over profile [buildenv] (conan 2.29/2.30).

        os.environ alone does not win over the aggregated Conan buildenv at
        self.run time, so patch the generated conanbuild*.sh scripts on disk
        to replace the missing profile shell and force writable TMPDIR.
        """
        for key, val in (("SHELL", shell), ("CONFIG_SHELL", shell),
                         ("TMPDIR", tmpdir), ("TMP", tmpdir),
                         ("TEMP", tmpdir), ("TMP_DIR", tmpdir)):
            os.environ[key] = val
        _pkg_config = self._resolve_pkg_config()
        if _pkg_config:
            os.environ["PKG_CONFIG"] = _pkg_config
        try:
            if self.build_folder:
                os.environ["PWD"] = self.build_folder
        except Exception:
            pass
        folders = []
        for folder in (self.build_folder, self.generators_folder):
            if folder and folder not in folders:
                folders.append(folder)
        bad_shells = [p for p in ("/data/service/hnp/bin/bash",
                                   "/data/service/hnp/bin/sh")
                       if p != shell]
        for folder in folders:
            try:
                names = os.listdir(folder)
            except OSError:
                continue
            for name in names:
                if not (name.startswith("conanbuild") and name.endswith(".sh")):
                    continue
                path = os.path.join(folder, name)
                try:
                    with open(path, encoding="utf-8", errors="surrogateescape") as handle:
                        content = handle.read()
                except OSError:
                    continue
                orig = content
                for bad in bad_shells:
                    content = content.replace(bad, shell)
                for key in ("TMPDIR", "TMP", "TEMP", "TMP_DIR"):
                    export_line = 'export %s="%s"' % (key, tmpdir)
                    pattern = re.compile(r'(?m)^export %s=.*' % key)
                    if pattern.search(content):
                        content = pattern.sub(export_line, content)
                    else:
                        if not content.endswith("\n"):
                            content += "\n"
                        content += export_line + "\n"
                if _pkg_config:
                    export_line = 'export PKG_CONFIG="%s"' % _pkg_config
                    pattern = re.compile(r'(?m)^export PKG_CONFIG=.*')
                    if pattern.search(content):
                        content = pattern.sub(export_line, content)
                    else:
                        if not content.endswith("\n"):
                            content += "\n"
                        content += export_line + "\n"
                if content != orig:
                    try:
                        with open(path, "w", encoding="utf-8", errors="surrogateescape") as handle:
                            handle.write(content)
                    except OSError:
                        continue
                    self.output.info("OHOS patch applied (conanbuild shell %s tmpdir %s) in %s" % (shell, tmpdir, name))

    def _ensure_ohos_compiler(self):
        """Use the profile compiler when present, else PATH clang (OHOS).

        The repo profile pins tools.build:compiler_executables to
        /data/service/hnp/bin/clang{,++}, absent on some HMBS preflight
        runners (probe: "inaccessible or not found", surfacing as
        "C compiler cannot create executables"). When the conf path exists
        this is a no-op. Otherwise CC/CXX point at PATH-discovered
        clang/clang++ via os.environ plus the same on-disk conanbuild*.sh
        override; CFLAGS/LDFLAGS (--target/--sysroot) are never modified.
        """
        conf = {}
        try:
            conf = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        except Exception:
            conf = {}
        conf_cc = conf.get("c", "") if isinstance(conf, dict) else ""
        conf_cxx = conf.get("cpp", "") if isinstance(conf, dict) else ""
        if conf_cc and os.path.isfile(conf_cc) and conf_cxx and os.path.isfile(conf_cxx):
            self.output.info("OHOS compiler: profile CC/CXX present, no override")
            return
        cc = conf_cc if conf_cc and os.path.isfile(conf_cc) else ""
        cxx = conf_cxx if conf_cxx and os.path.isfile(conf_cxx) else ""
        if not cc:
            cc = shutil.which("clang") or ""
        if not cxx:
            if cc:
                sib = os.path.join(os.path.dirname(cc), "clang++")
                if os.path.isfile(sib):
                    cxx = sib
            if not cxx:
                cxx = shutil.which("clang++") or ""
        if not cc or not cxx:
            from conan.errors import ConanException
            raise ConanException(
                "OHOS compiler missing (environment failure, not recipe): "
                "profile CC=%r CXX=%r absent and no clang/clang++ on PATH." % (conf_cc, conf_cxx))
        self.output.info("OHOS compiler fallback: CC=%s CXX=%s (profile %r absent)" % (cc, cxx, conf_cc))
        for key, val in (("CC", cc), ("CXX", cxx)):
            os.environ[key] = val
        folders = []
        for folder in (self.build_folder, self.generators_folder):
            if folder and folder not in folders:
                folders.append(folder)
        for folder in folders:
            try:
                names = os.listdir(folder)
            except OSError:
                continue
            for name in names:
                if not (name.startswith("conanbuild") and name.endswith(".sh")):
                    continue
                path = os.path.join(folder, name)
                try:
                    with open(path, encoding="utf-8", errors="surrogateescape") as handle:
                        content = handle.read()
                except OSError:
                    continue
                orig = content
                for key, val in (("CC", cc), ("CXX", cxx)):
                    export_line = 'export %s="%s"' % (key, val)
                    pattern = re.compile(r'(?m)^export %s=.*' % key)
                    if pattern.search(content):
                        content = pattern.sub(export_line, content)
                    else:
                        if not content.endswith("\n"):
                            content += "\n"
                        content += export_line + "\n"
                if content != orig:
                    try:
                        with open(path, "w", encoding="utf-8", errors="surrogateescape") as handle:
                            handle.write(content)
                    except OSError:
                        continue
                    self.output.info("OHOS patch applied (conanbuild CC/CXX fallback) in %s" % name)

    def _probe_ohos_compiler(self):
        """Non-fatal pre-configure compiler probe (diagnostic only)."""
        try:
            self.run("$CC --version", env="conanbuild")
        except Exception as exc:
            self.output.warning("OHOS compiler probe ($CC --version) failed: %s" % exc)

    def _dump_config_log(self):
        """Dump config.log tail on configure failure (diagnostic only)."""
        for folder in (self.build_folder, self.source_folder):
            if not folder:
                continue
            path = os.path.join(folder, "config.log")
            if not os.path.isfile(path):
                continue
            try:
                with open(path, encoding="utf-8", errors="replace") as handle:
                    lines = handle.read().splitlines()
            except OSError:
                continue
            tail = lines[-80:] if len(lines) > 80 else lines
            self.output.warning("config.log tail (%s, %d lines total):" % (path, len(lines)))
            for line in tail:
                self.output.warning("config.log| " + line)

    def _patch_ohos_build_scripts(self):
        """Scrub generated configure for OHOS workers (sources untouched)."""
        shell = self._ohos_shell()
        try:
            os.makedirs(self._resolve_tmpdir(), exist_ok=True)
        except OSError:
            pass
        shebang = "#!%s" % shell if shell.startswith("/") else "#!/bin/sh"
        for old in ("#! /bin/sh", "#!/bin/sh", "#!/system/bin/sh"):
            if old == shebang:
                continue
            self._replace_if_found(
                os.path.join(self.source_folder, "configure"),
                old,
                shebang,
                what="configure shebang (E165/HMBS shell)",
            )
        configure_path = os.path.join(self.source_folder, "configure")
        for bad in ("/data/service/hnp/bin/bash", "/data/service/hnp/bin/sh"):
            if bad == shell:
                continue
            self._replace_all_in_file(
                configure_path,
                bad,
                shell,
                what="configure profile-shell path (E165/HMBS shell)",
            )
        self._replace_all_in_file(
            os.path.join(self.source_folder, "configure"),
            "umask 077",
            "umask 022",
            what="configure umask HMDFS (E011/readonly_tmp)",
        )

    def _replace_if_found(self, path, old, new, what=""):
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                content = handle.read()
        except OSError:
            self.output.warning("OHOS patch skipped (%s): cannot read %s" % (what, path))
            return
        if old not in content:
            self.output.warning("OHOS patch skipped (%s): anchor not found in %s" % (what, os.path.basename(path)))
            return
        if new in content:
            self.output.info("OHOS patch already applied (%s)" % what)
            return
        content = content.replace(old, new, 1)
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
        self.output.info("OHOS patch applied (%s)" % what)

    def _replace_all_in_file(self, path, old, new, what=""):
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                content = handle.read()
        except OSError:
            self.output.warning("OHOS patch skipped (%s): cannot read %s" % (what, path))
            return
        if old not in content:
            self.output.warning("OHOS patch skipped (%s): anchor not found in %s" % (what, os.path.basename(path)))
            return
        content = content.replace(old, new)
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
        self.output.info("OHOS patch applied (%s)" % what)

    def _fix_config_status_umask(self):
        # Kept for reference: config.status umask is patched post-configure
        # in recipes that reach that stage; libsmf configure currently fails
        # earlier, so the pre-configure umask scrub in
        # _patch_ohos_build_scripts() is authoritative.
        return
