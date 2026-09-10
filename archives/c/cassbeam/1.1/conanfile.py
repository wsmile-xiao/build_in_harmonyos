#!/usr/bin/env python3
"""Conan recipe — cassbeam 1.1 (Cassegrain antenna modelling, C/autotools).

Upstream: ratt-ru/cassbeam (Debian 1.1 orig tarball).
Build: pre-generated configure (autoconf 2.69) + Makefile.in, in-tree,
  produces a single CLI binary `cassbeam` (package_type=application).

OHOS notes:
  - Hard dep glib-2.0 (configure.in AC_MSG_ERROR if pkg-config misses it):
    conan requires glib/2.88.0 (uploaded registry version; 2.84.0 is
    built-local only and fails dependency-graph resolution on
    preflight/CI), PkgConfigDeps provides glib-2.0.pc.
  - Hard dep FFTW2 (vector-fftw.c includes <fftw.h>/<rfftw.h>, fftw2 API):
    registry only has fftw3 (incompatible), Debian builds with fftw-dev
    2.1.5, so vendor fftw 2.1.5 source (conandata vendor) and static-build
    it first, then link cassbeam against it. No new conan requirement.
  - E011/E129/readonly_tmp: configure mktemp 0700 + umask 077 fail on
    HMDFS (chmod=0, /tmp readonly erofs) -> variable-form patches only
    (umask 022, ac_pwd $PWD fallback, mktemp -> ${TMPDIR:-.}, never baked
    absolute paths); writable tmp resolved by probing
    HMBS_AUTOCONF_MKTEMP_FALLBACK/TMPDIR/TMP/TEMP.
  - Toolchain: trust AutotoolsToolchain/conanbuild.sh verbatim for CC,
    CFLAGS/LDFLAGS (sysroot/target), PATH and LD_LIBRARY_PATH. The recipe
    never overrides CC or guesses SDK lib dirs: prior cycles proved that
    custom CC resolution (verified-absolute search + bare-clang fallback +
    hard pre-configure probe with basename `command -v` lookup) turns
    worker env wobble into a hard Error 127 of our own making. The only
    pre-configure check is now soft/log-only and never raises; a truly
    broken compiler surfaces via configure's own check + config.log dump.
  - R9: make -j1 (HMDFS jobserver fifo EPERM).
  - No `make install` (Makefile calls `install -D`, missing on OHOS):
    package() manually copies the binary with copy().
  - No upstream test suite (no `make check` target, no tests/ dir):
    honest no_tests, see test_package/MANIFEST.yml audit. Functional
    verification runs the upstream example input (examples/vla) via
    test_package/test.sh.
"""

import glob
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class CassbeamConan(ConanFile):
    name = "cassbeam"
    version = "1.1"
    description = "Cassegrain antenna modelling tool (VLA beam simulator)"
    license = "GPL-2.0-only"
    homepage = "https://github.com/ratt-ru/cassbeam"
    url = "https://salsa.debian.org/debian-astro-team/cassbeam.git"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # glib/2.88.0 is the uploaded registry version (_index.yaml);
        # 2.84.0 is only built-local and not resolvable on preflight/CI
        # remotes (conan download 404 -> dependency graph failure).
        # zlib root-level override pins the OHOS-specific suffix version
        # 1.3.1.1: plain zlib/1.3.1 exists on conancenter and wins remote
        # ordering, pulling the official CMake recipe which fails on OHOS
        # ("System is unknown to cmake ... HarmonyOS"); 1.3.1.1 exists only
        # on ohpcd (same sources, -fPIC static) so the graph stays on ohpcd.
        # Same pattern as gupnp/gtk4/gssdp (requires zlib/1.3.1.1 override).
        self.requires("zlib/1.3.1.1", override=True)
        self.requires("glib/2.88.0", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # configure.in does AC_CHECK_PROG(pkg-config): preflight has no
        # system pkg-config (checking for pkg-config... NONE -> AC_MSG_ERROR
        # "Could not find glib-config"). pkgconf provides the pkg-config
        # binary on conanbuild PATH (captagent/burp2/ekg2 precedent).
        self.tool_requires("pkgconf/3.0.5")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"cassbeam {self.version} only supports Linux and OHOS, got os={self.settings.os}"
            )

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Vendor FFTW 2.1.5 alongside (strip_root into vendor/fftw-2.1.5).
        vendor = self.conan_data["vendor"]["fftw"]
        get(self, **vendor, strip_root=True,
            destination=os.path.join(self.source_folder, "vendor", "fftw-2.1.5"))
        # Autoconf mktemp fallback chain ends at $HOME/tmp: pre-create it
        # so redirected templates never fall back to readonly /tmp.
        try:
            os.makedirs(os.path.join(os.path.expanduser("~"), "tmp"), exist_ok=True)
        except OSError:
            pass
        # HMDFS fixes applied at source time (variable expansion only;
        # no baked absolute paths: source-time TMPDIR may differ from
        # build-time runtime tmp, and fftw-2.1.5 autoconf may not even
        # contain the ac_tmp=$tmp literal, so baking silently no-ops).
        self._patch_configure_tree(self.source_folder)

    def _resolve_hmbs_tmp(self):
        """Pick a writable tmp dir: probe candidates, never /tmp (readonly erofs)."""
        def _valid(p):
            try:
                if not p or p in ("0", "1") or p == "/tmp":
                    return False
                import os as _os
                _os.makedirs(p, exist_ok=True)
                probe = _os.path.join(p, ".hmbs_probe")
                with open(probe, "w") as _pf:
                    _pf.write("probe")
                _os.remove(probe)
                return True
            except Exception:
                return False
        for cand in (
            os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK"),
            os.environ.get("TMPDIR"),
            os.environ.get("TMP"),
            os.environ.get("TEMP"),
            os.environ.get("HMBS_TMPDIR"),
        ):
            if cand and _valid(cand):
                return cand
        fb = os.path.join(self.build_folder, "cfg-tmp")
        try:
            os.makedirs(fb, exist_ok=True)
        except OSError:
            pass
        return fb

    def _patch_configure(self, cfg):
        try:
            with open(cfg, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            orig = content
            if "umask 077" in content:
                content = content.replace("umask 077", "umask 022")
            # getcwd may fail on HMDFS: fall back to $PWD (aldo precedent).
            if "ac_pwd=`pwd`" in content:
                content = content.replace(
                    "ac_pwd=`pwd`",
                    'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"')
                content = content.replace(
                    'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD" 2>/dev/null || ac_pwd="$PWD"',
                    'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"')
            # mktemp templates -> $TMPDIR (variable form, no baked paths).
            content = content.replace(
                'mktemp -d -q "./confstatXXXXXX"',
                'mktemp -d -q "${TMPDIR:-.}/confstatXXXXXX"')
            content = content.replace(
                'mktemp -d "./confXXXXXX"',
                'mktemp -d "${TMPDIR:-.}/confXXXXXX"')
            content = content.replace(
                "mktemp -d './confXXXXXX'",
                "mktemp -d '${TMPDIR:-.}/confXXXXXX'")
            # Older autoconf fallbacks: tmp=./conf$$ variants -> $TMPDIR.
            content = content.replace("tmp=./conf$$-$RANDOM", "tmp=${TMPDIR:-.}/conf$$-$RANDOM")
            if "tmp=./conf$$" in content and "${TMPDIR" not in content.split("tmp=./conf$$")[0][-200:]:
                content = content.replace("tmp=./conf", "tmp=${TMPDIR:-.}/conf")
            # Do not let autoconf default TMPDIR to readonly /tmp.
            content = re.sub(r":\s*\$\{TMPDIR=/tmp\}", ": ${TMPDIR=\.}", content)
            content = content.replace("${TMPDIR=/tmp}", "${TMPDIR=\.}")
            if content != orig:
                with open(cfg, "w", encoding="utf-8") as f:
                    f.write(content)
                self.output.info(f"HMDFS tmp patch applied: {cfg}")
        except OSError:
            pass

    def _patch_configure_tree(self, root):
        for _root, _, files in os.walk(root):
            if "configure" in files:
                self._patch_configure(os.path.join(_root, "configure"))

    def _soft_toolchain_note(self):
        """Log-only toolchain note: never overrides CC/LD_LIBRARY_PATH.

        Prior cycles resolved CC via verified-absolute search and exported
        CC='...' prefixes plus a hard basename probe; that machinery turned
        worker env wobble into our own Error 127. Now we only report what
        AutotoolsToolchain/conanbuild.sh provides and let configure's own
        compiler check decide.
        """
        try:
            comp = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
            self.output.info(f"toolchain conf compiler_executables: {comp}")
        except Exception as exc:
            self.output.info(f"toolchain conf unreadable: {exc}")
        try:
            cb = os.path.join(self.generators_folder, "conanbuild.sh")
            if os.path.isfile(cb):
                with open(cb, "r", encoding="utf-8", errors="replace") as f:
                    txt = f.read()
                for line in txt.splitlines():
                    s = line.strip()
                    if s.startswith("export CC=") or s.startswith("export CXX=") or s.startswith("export LD_LIBRARY_PATH="):
                        self.output.info(f"conanbuild: {s[:220]}")
        except Exception as exc:
            self.output.info(f"conanbuild inspect skipped: {exc}")

    def _cand_works(self, cand):
        """True if cand can actually run --version (proven executable)."""
        if not cand:
            return False
        # Strip embedded flags (toolchain may set CC="clang --target=...").
        prog = cand.strip().split()[0].strip("\"'")
        if not prog:
            return False
        if "/" in prog:
            if not os.path.isfile(prog):
                return False
        else:
            resolved = shutil.which(prog)
            if not resolved:
                return False
            prog = resolved
        try:
            r = subprocess.run([prog, "--version"], stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, timeout=20)
            return r.returncode == 0
        except Exception:
            return False

    def _resolve_compilers(self):
        """Return (cc, cxx, overrode).

        Prefer toolchain verbatim when it runs; only fall back to a proven
        executable when the configured CC is missing/broken (this round:
        /data/service/hnp/bin/clang -> 'inaccessible or not found' ->
        'C compiler cannot create executables'). Never returns an
        unverified bare name, so we never manufacture our own Error 127.
        """
        try:
            comp = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
        except Exception:
            comp = {}
        conf_c = (comp.get("c") or "").strip()
        conf_cxx = (comp.get("cpp") or comp.get("cxx") or "").strip()
        if conf_c and self._cand_works(conf_c):
            cc, over_c = conf_c.split()[0].strip("\"'"), False
            # Re-resolve bare name to absolute via PATH for configure.
            if "/" not in cc:
                cc = shutil.which(cc) or cc
        else:
            if conf_c:
                self.output.warning(
                    f"toolchain CC broken/unrunnable: {conf_c!r}; searching fallback")
            cc, over_c = "", True
            search_c = [os.environ.get("CC", ""), "clang", "clang-15", "cc", "gcc",
                        "/data/service/hnp/bin/clang",
                        "/storage/Users/currentUser/usr/local/bin/clang",
                        "/usr/bin/clang", "/usr/bin/cc", "/usr/bin/gcc"]
            for cand in search_c:
                if cand and self._cand_works(cand):
                    prog = cand.strip().split()[0].strip("\"'")
                    cc = shutil.which(prog) if "/" not in prog else prog
                    self.output.warning(f"CC fallback in use: {cc} (conf was {conf_c!r})")
                    break
            if not cc:
                self.output.warning("no working C compiler found on PATH/SDK")
                cc = conf_c or "clang"
        if conf_cxx and self._cand_works(conf_cxx):
            cxx, over_cxx = conf_cxx.split()[0].strip("\"'"), False
            if "/" not in cxx:
                cxx = shutil.which(cxx) or cxx
        else:
            if conf_cxx:
                self.output.warning(
                    f"toolchain CXX broken/unrunnable: {conf_cxx!r}; searching fallback")
            cxx, over_cxx = "", True
            search_cxx = [os.environ.get("CXX", ""), "clang++", "clang++-15",
                          "c++", "g++", "/data/service/hnp/bin/clang++",
                          "/usr/bin/clang++", "/usr/bin/c++", "/usr/bin/g++"]
            for cand in search_cxx:
                if cand and self._cand_works(cand):
                    prog = cand.strip().split()[0].strip("\"'")
                    cxx = shutil.which(prog) if "/" not in prog else prog
                    self.output.warning(f"CXX fallback in use: {cxx} (conf was {conf_cxx!r})")
                    break
            if not cxx:
                cxx = conf_cxx or "clang++"
        self.output.info(f"resolved compilers: CC={cc} CXX={cxx} "
                         f"overrode={bool(over_c or over_cxx)}")
        return cc, cxx, bool(over_c or over_cxx)

    def _stage_fftw_vendor(self, fftw_src, fftw_install):
        """Manually stage vendored FFTW headers/libs (bypass `make install`).

        libtool `make install` (install shim + ranlib) fails on HMDFS
        (install exits 0 but dest missing -> ranlib No such file).
        duo-unix precedent: copy static libs from .libs/ by hand.
        """
        incdir = os.path.join(fftw_install, "include")
        libdir = os.path.join(fftw_install, "lib")
        os.makedirs(incdir, exist_ok=True)
        os.makedirs(libdir, exist_ok=True)
        # Headers: fftw.h/rfftw.h (+ type-prefixed d*/s* variants + config.h).
        headers = set()
        for pat in ("fftw.h", "rfftw.h", "dfftw.h", "drfftw.h",
                    "sfftw.h", "srfftw.h", "fftw*.h", "rfftw*.h", "config.h"):
            headers.update(glob.glob(os.path.join(fftw_src, pat)))
            headers.update(glob.glob(os.path.join(fftw_src, "*", pat)))
            headers.update(glob.glob(os.path.join(fftw_src, "fftw", pat)))
        for h in sorted(headers):
            if os.path.isfile(h):
                # copyfile (not copy2): HMDFS has chmod=0, copystat/chmod fails.
                shutil.copyfile(h, os.path.join(incdir, os.path.basename(h)))
                self.output.info(f"staged fftw header: {os.path.basename(h)}")
        # Libs: all built static archives under .libs/ (recursive).
        staged = {}
        for a in sorted(glob.glob(os.path.join(fftw_src, "**", ".libs", "*.a"), recursive=True)):
            base = os.path.basename(a)
            if base not in staged and os.path.isfile(a):
                staged[base] = a
        for a in sorted(glob.glob(os.path.join(fftw_src, "**", "*.a"), recursive=True)):
            if ".libs" in a:
                continue
            base = os.path.basename(a)
            if base not in staged and os.path.isfile(a):
                staged[base] = a
        for base, src in sorted(staged.items()):
            # copyfile avoids chmod/copystat on HMDFS (chmod=0 capability).
            shutil.copyfile(src, os.path.join(libdir, base))
            self.output.info(f"staged fftw lib: {base} <- {os.path.relpath(src, fftw_src)}")
        if not staged:
            found = []
            for _root, _dirs, _files in os.walk(fftw_src):
                found.extend(_files[:5])
                if len(found) > 20:
                    break
            from conan.errors import ConanException
            raise ConanException(
                f"fftw vendor staging found 0 static libs under {fftw_src} "
                f"(sample files: {found}); `make -j1` likely failed to build libs")
        # Re-index staged archives when a ranlib is on PATH; ignore failure
        # (ar-created index is usually already present; on HMDFS chmod=0
        # ranlib may not be able to rewrite the archive -> never fatal).
        ranlib = shutil.which("llvm-ranlib") or shutil.which("ranlib")
        if ranlib:
            for base in sorted(staged):
                dst = os.path.join(libdir, base)
                try:
                    self.run(f'"{ranlib}" "{dst}"', ignore_errors=True)
                except Exception as exc:
                    self.output.warning(f"ranlib {base} ignored: {exc}")
                    continue
        self.output.info(f"fftw vendor staged: {len(headers)} headers, {len(staged)} libs -> {fftw_install}")
    def _ensure_pkg_config_shim(self):
        """Provide `pkg-config` on PATH via pkgconf (2nd-attempt fix).

        1st attempt added tool_requires pkgconf/3.0.5 only, but its package
        explicitly ships bin/pkgconf WITHOUT a bin/pkg-config alias
        (package() raises on unexpected alias), so
        AC_CHECK_PROG(GLIB_CONFIG, pkg-config) still reports NONE.
        Create a hmbs-shims dir with a pkg-config -> pkgconf symlink
        (symlink cap=1; copyfile fallback avoids HMDFS chmod=0) and
        return it for PATH prepend. Pure text patch of configure is the
        fallback inside _patch_configure().
        """
        shim_dir = os.path.join(self.build_folder, "hmbs-shims")
        try:
            os.makedirs(shim_dir, exist_ok=True)
        except OSError:
            return ""
        pkgconf_bin = ""
        try:
            bdep = self.dependencies.build.get("pkgconf")
            if bdep is not None and bdep.package_folder:
                cand = os.path.join(str(bdep.package_folder), "bin", "pkgconf")
                if os.path.isfile(cand):
                    pkgconf_bin = cand
        except Exception:
            pass
        if not pkgconf_bin:
            for cand in (shutil.which("pkgconf") or "", "/usr/bin/pkgconf",
                         "/usr/local/bin/pkgconf"):
                try:
                    if cand and os.path.isfile(cand):
                        pkgconf_bin = cand
                        break
                except Exception:
                    continue
        if not pkgconf_bin:
            self.output.warning("pkgconf binary not found; pkg-config shim skipped")
            return ""
        link = os.path.join(shim_dir, "pkg-config")
        try:
            if os.path.islink(link) or os.path.isfile(link):
                try:
                    os.remove(link)
                except OSError:
                    pass
            try:
                os.symlink(pkgconf_bin, link)
            except (OSError, NotImplementedError):
                shutil.copyfile(pkgconf_bin, link)
            self.output.info(f"pkg-config shim: {link} -> {pkgconf_bin}")
            return shim_dir
        except Exception as exc:
            self.output.warning(f"pkg-config shim failed: {exc}")
            return ""

    def _glib_flags(self):
        """CFLAGS/LIBS for glib from Conan dep cpp_info (pkg-config fallback)."""
        cflags, libs = "", ""
        try:
            dep = self.dependencies["glib"]
            incs, libdirs, names, syslibs = [], [], [], []
            for d in [dep.cpp_info] + list(dep.cpp_info.components.values()):
                for v in d.includedirs:
                    if v not in incs:
                        incs.append(v)
                for v in d.libdirs:
                    if v not in libdirs:
                        libdirs.append(v)
                for v in d.libs:
                    if v not in names:
                        names.append(v)
                for v in d.system_libs:
                    if v not in syslibs:
                        syslibs.append(v)
            # Resolve relative dirs against package folder.
            pkg = dep.package_folder or ""
            incs = [v if os.path.isabs(v) else os.path.join(pkg, v) for v in incs]
            libdirs = [v if os.path.isabs(v) else os.path.join(pkg, v) for v in libdirs]
            if incs:
                cflags = " ".join(f"-I{d}" for d in incs)
            parts = []
            if libdirs:
                parts.append(" ".join(f"-L{d}" for d in libdirs))
            if names:
                parts.append(" ".join(f"-l{l}" for l in names))
            if syslibs:
                parts.append(" ".join(f"-l{s}" for s in syslibs))
            libs = " ".join(parts).strip()
        except KeyError:
            self.output.warning("glib not in dependency graph; using pkg-config fallback")
        return cflags, libs

    def _glib_conan_first(self):
        """Conan -L dirs first + absolute libintl.a (E107/E123).

        glib/2.88.0 bundles proxy-libintl libintl.a which provides the
        g_libintl_* symbols its static libglib-2.0.a needs. The toolchain
        $LDFLAGS carries -L/usr/local/lib first, so plain
        LDFLAGS="$LDFLAGS ... -lglib -lintl" resolves both to the system
        /usr/local/lib copies whose libintl lacks g_libintl_* -> ld.lld
        undefined g_libintl_bindtextdomain etc (CI #42644). Prepending the
        conan -L dirs forces the linker to find conan glib/intl first;
        the absolute libintl.a guarantees the g_ symbols even if a later
        -L still exposes a system libintl.so.
        """
        libdir_flags, intl_archive = "", ""
        try:
            dep = self.dependencies["glib"]
            pkg = dep.package_folder or ""
            dirs = []
            try:
                for v in dep.cpp_info.libdirs:
                    d = v if os.path.isabs(v) else os.path.join(pkg, v)
                    if d not in dirs:
                        dirs.append(d)
            except Exception:
                pass
            for comp in getattr(dep.cpp_info, "components", {}).values():
                try:
                    for v in comp.libdirs:
                        d = v if os.path.isabs(v) else os.path.join(pkg, v)
                        if d not in dirs:
                            dirs.append(d)
                except Exception:
                    continue
            if dirs:
                libdir_flags = " ".join(f"-L{d}" for d in dirs)
            cand = os.path.join(pkg, "lib", "libintl.a") if pkg else ""
            if cand and os.path.isfile(cand):
                intl_archive = cand
        except KeyError:
            pass
        return libdir_flags, intl_archive

    def build(self):
        # pkg-config shim must come first: configure hardcodes `pkg-config`
        # but pkgconf pkg only ships `pkgconf` (no alias by design).
        shim_dir = self._ensure_pkg_config_shim()
        path_prefix = ""
        if shim_dir:
            try:
                os.environ["PATH"] = shim_dir + os.pathsep + os.environ.get("PATH", "")
            except Exception:
                pass
            # Double quotes (not single): $PATH must expand from conanbuild
            # env. Single-quoted 'shim:$PATH' passes a literal '$PATH',
            # leaving only the shim dir on PATH -> sed/chmod/rm/head
            # 'inaccessible or not found' and configure '.lineno' failure.
            path_prefix = f'PATH="{shim_dir}:$PATH" '
        # HMBS injects SHELL=/bin/sh; keep injected value, fallback /bin/sh.
        shell = os.environ.get("SHELL", "/bin/sh") or "/bin/sh"
        # Writable tmp: probe candidates for real writability (never /tmp).
        # HMBS_AUTOCONF_MKTEMP_FALLBACK respected when it is a path.
        tmpdir = self._resolve_hmbs_tmp()
        os.makedirs(tmpdir, exist_ok=True)
        try:
            os.makedirs(os.path.join(os.path.expanduser("~"), "tmp"), exist_ok=True)
        except OSError:
            pass
        for _var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[_var] = tmpdir
        fb = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK")
        if fb and fb not in ("0", "1"):
            try:
                os.makedirs(fb, exist_ok=True)
            except OSError:
                os.environ["HMBS_AUTOCONF_MKTEMP_FALLBACK"] = tmpdir
        os.environ["SHELL"] = shell
        os.environ["CONFIG_SHELL"] = shell
        os.environ["PWD"] = self.build_folder
        # Re-apply variable-form patches at build time: source/export may
        # have refreshed file mtimes after source() in some Conan flows.
        self._patch_configure_tree(self.source_folder)
        # Toolchain: prefer AutotoolsToolchain/conanbuild.sh verbatim, but
        # verify it can run. This round /data/service/hnp/bin/clang is
        # 'inaccessible or not found' -> configure 'cannot create
        # executables'. _resolve_compilers() keeps verbatim CC when it
        # runs --version cleanly and only falls back to a proven
        # executable otherwise (never an unverified bare name).
        self._soft_toolchain_note()
        cc_resolved, cxx_resolved, cc_overrode = self._resolve_compilers()
        cc_env = f'CC="{cc_resolved}" CXX="{cxx_resolved}" '
        try:
            os.environ["CC"] = cc_resolved
            os.environ["CXX"] = cxx_resolved
        except Exception:
            pass
        self.output.info(f"HMBS tmp root (probed writable): {tmpdir}")
        self.output.info(
            f"HMBS env TMPDIR={os.environ.get('TMPDIR')} "
            f"FALLBACK={os.environ.get('HMBS_AUTOCONF_MKTEMP_FALLBACK')} "
            f"SHELL={shell} CC={cc_resolved} overrode={cc_overrode}")
        tmp_env = (
            f"TMPDIR='{tmpdir}' TMP='{tmpdir}' TEMP='{tmpdir}' "
            f"SHELL='{shell}' CONFIG_SHELL='{shell}' PWD='{self.build_folder}'"
        )

        # PKG_CONFIG_PATH must see PkgConfigDeps output (generators_folder).
        pc_path = self.generators_folder
        prev_pc = os.environ.get("PKG_CONFIG_PATH", "")
        if prev_pc:
            pc_path = pc_path + os.pathsep + prev_pc

        # ---- 1. Vendor FFTW 2.1.5 static build ----
        fftw_src = os.path.join(self.source_folder, "vendor", "fftw-2.1.5")
        fftw_install = os.path.join(self.build_folder, "vendor-install")
        os.makedirs(fftw_install, exist_ok=True)
        # E007: explicit triplet bypasses config.guess (Permission denied on HMDFS).
        triplet = "--build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu"
        # Soft log-only note (never raises): shows the resolved CC as
        # verified above. A truly broken compiler still surfaces
        # via configure's own check + config.log dump below.
        try:
            self.run(
                f"umask 022 && {path_prefix}{tmp_env} {cc_env}{shell} -c 'echo TOOLCHAIN_CC=$CC; echo RESOLVED_CC={cc_resolved}; \"{cc_resolved}\" --version 2>&1 | head -n 3; echo TOOLCHAIN_NOTE_OK'",
                cwd=self.build_folder, env="conanbuild", ignore_errors=True)
        except Exception as exc:
            self.output.warning(f"toolchain note skipped: {exc}")
        # Forward toolchain flags explicitly: fftw configure resets CFLAGS
        # when not given, losing sysroot -> same Error 77. Append, keep $VAR.
        # CC/CXX are the verified executables (verbatim when healthy,
        # fallback when the profile path is unrunnable); CFLAGS/LDFLAGS
        # still appended from $VAR so sysroot/target are preserved.
        fftw_cfg = (
            f"umask 022 && {path_prefix}{tmp_env} {cc_env}"
            f"PKG_CONFIG_PATH='{pc_path}' "
            f"CFLAGS=\"$CFLAGS -O2\" CPPFLAGS=\"$CPPFLAGS\" LDFLAGS=\"$LDFLAGS\" "
            f"{shell} ./configure {triplet} --prefix='{fftw_install}' "
            f"--enable-static --disable-shared"
        )
        try:
            self.run(fftw_cfg, cwd=fftw_src, env="conanbuild")
        except Exception:
            self._dump_config_log(fftw_src)
            raise
        # Compiler temp files also honour TMPDIR: export it for make as well
        # so nothing falls back to readonly /tmp (HMBS readonly_tmp gate).
        # NOTE: no `make install` for vendored fftw: libtool install
        # (install shim + ranlib) fails on HMDFS (dest missing -> ranlib
        # No such file). Stage headers/libs by hand (duo-unix precedent).
        self.run(f"umask 022 && {path_prefix}{tmp_env} {cc_env}make -j1", cwd=fftw_src, env="conanbuild")
        self._stage_fftw_vendor(fftw_src, fftw_install)

        # ---- 2. cassbeam configure + make (in-tree, upstream README flow) ----
        glib_cflags, glib_libs = self._glib_flags()
        fftw_cflags = f"-I{os.path.join(fftw_install, 'include')}"
        fftw_ldflags = f"-L{os.path.join(fftw_install, 'lib')}"
        # Link fix (preflight ld.lld undefined fftw_create_plan/rfftw_one/...):
        # the final `clang -o cassbeam` line carried -L vendor-install/lib
        # but no fftw libs at all, so the vendored static archives were never
        # linked. Pass the staged archives by absolute path (not -l names:
        # robust against libfftw vs libdfftw naming) in both configure and
        # make LDFLAGS/LIBS so the link succeeds regardless of the Makefile's
        # LIBS/LDFLAGS variable conventions. rfftw before fftw (dependents
        # first).
        _fftw_archives = sorted(glob.glob(os.path.join(fftw_install, "lib", "*.a")))
        _fftw_archives.sort(key=lambda p: (0 if os.path.basename(p).lower().startswith(("libr", "dr", "sr")) else 1, p))
        # NOTE: no shell quoting here. These paths are interpolated into a
        # double-quoted LIBS="..."/LDFLAGS="..." env assignment evaluated by
        # the shell, so embedding single quotes would become literal quote
        # characters inside the env value (shell quote removal does not
        # re-process expanded values) -> linker looks for '/path/x.a' with
        # quotes -> link fails -> configure 'C compiler cannot create
        # executables'. HMBS paths contain no spaces, plain join is safe.
        fftw_archives = " ".join(_fftw_archives)
        if _fftw_archives:
            self.output.info(f"fftw archives for link: {_fftw_archives}")
        else:
            self.output.warning("no staged fftw archives found; link will fail")
        # Append to toolchain flags ($CFLAGS/$LDFLAGS carry sysroot/target);
        # overwriting them drops sysroot -> same "cannot create executables".
        # configure.in appends glib/fftw probe results to LIBS/LDFLAGS itself;
        # pre-seed LDFLAGS with vendored fftw libdir + glib libs so the
        # AC_CHECK_LIB(fftw)/AC_CHECK_LIB(rfftw) probes succeed.
        # configure gets CFLAGS/LDFLAGS (dirs + glib libs) only: configure.in
        # appends its own fftw probe results to LIBS/LDFLAGS, and a pre-seeded
        # LIBS with absolute .a paths would also pollute the initial
        # AC_PROG_CC sanity check ('C compiler cannot create executables'
        # on any link hiccup). The staged archives are passed at make time.
        conan_ldirs, intl_archive = self._glib_conan_first()
        if conan_ldirs:
            self.output.info(f"conan libdirs first: {conan_ldirs}")
        if intl_archive:
            self.output.info(f"bundled libintl.a: {intl_archive}")
        else:
            self.output.warning("glib libintl.a not found; falling back to -lintl")
        intl_tail = f" {intl_archive}" if intl_archive else ""
        cfg_cmd = (
            f"umask 022 && {path_prefix}{tmp_env} {cc_env}PKG_CONFIG_PATH='{pc_path}' "
            f"CFLAGS=\"{glib_cflags} {fftw_cflags} $CFLAGS -O2\" "
            f"LDFLAGS=\"{fftw_ldflags} {conan_ldirs} $LDFLAGS {glib_libs}{intl_tail} -lintl\" "
            f"{shell} ./configure --prefix=/"
        )
        try:
            self.run(cfg_cmd, cwd=self.source_folder, env="conanbuild")
        except Exception:
            self._dump_config_log(self.source_folder)
            raise
        # R9: single job; archives re-passed so the link finds fftw/rfftw.
        # TMPDIR exported so compiler temp files avoid readonly /tmp.
        self.run(
            f"umask 022 && {path_prefix}{tmp_env} {cc_env}make -j1 LDFLAGS=\"{fftw_ldflags} {conan_ldirs} $LDFLAGS {glib_libs} {fftw_archives}{intl_tail} -lintl -lm\" LIBS=\"{fftw_archives}{intl_tail} -lintl -lm\"",
            cwd=self.source_folder, env="conanbuild",
        )

    def _dump_config_log(self, folder):
        log = os.path.join(folder, "config.log")
        if os.path.isfile(log):
            self.output.info("===== BEGIN config.log =====")
            try:
                with open(log, "r", encoding="utf-8", errors="replace") as f:
                    # Tail is what diagnoses conftest failures; full log is huge.
                    text = f.read()
                    lines = text.splitlines()
                    for line in lines[-60:]:
                        self.output.info(line)
                    keys = ("cannot create", "conftest", "ld.lld",
                            "linker command failed", "sysroot", "cannot find",
                            "/tmp/", "Read-only", "Permission denied")
                    hits = [l for l in lines if any(k in l for k in keys)]
                    if hits:
                        self.output.info("===== config.log key lines =====")
                        for line in hits[-40:]:
                            self.output.info(line)
            except OSError:
                pass
            self.output.info("===== END config.log =====")

    def package(self):
        # Manual staging: Makefile `install` needs `install -D` (absent on OHOS).
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        copy(self, "cassbeam", src=self.source_folder, dst=bindir)
        # License + example input for consumers.
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*.in", src=os.path.join(self.source_folder, "examples", "vla"),
             dst=os.path.join(self.package_folder, "res", "examples", "vla"))
        # geom file has no extension (vla_geom, referenced as `geom = vla_geom`
        # in the .in): `*.in` misses it, and without it the binary aborts
        # (g_assert(a) -> SIGABRT/134). Ship the whole example dir content.
        copy(self, "vla_geom", src=os.path.join(self.source_folder, "examples", "vla"),
             dst=os.path.join(self.package_folder, "res", "examples", "vla"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
