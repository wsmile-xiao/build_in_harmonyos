#!/usr/bin/env python3
"""Conan recipe — omniorb 4.3.4 (Autotools)

omniORB is a robust high performance CORBA 2.6 ORB for C++: ORB runtime
libraries (libomniORB4, libomnithread, ...), the omniidl IDL compiler and
the omniNames naming service.
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, rm
from conan.tools.files import export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class OmniorbConan(ConanFile):
    name = "omniorb"
    version = "4.3.4"
    description = "omniORB is a robust high performance CORBA ORB for C++."
    # COPYING.LIB (LGPL-2.1) covers the runtime libraries,
    # COPYING (GPL-2) covers the tools (omniidl, omniNames, utilities).
    license = "LGPL-2.1-or-later", "GPL-2.0-or-later"
    homepage = "https://omniorb.sourceforge.io/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No Conan requirements. OpenSSL / zlib / zstd support is
        # auto-detected by configure and stays off on the worker (no
        # system OpenSSL or compression dev files), so the package has
        # no link-time dependencies outside libc/libc++. Python 3 is
        # needed at build time for the omniidl backends; it is taken
        # from the worker PATH (see generate()).
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "omniorb only supports Linux/OHOS, got: %s"
                % self.settings.os)
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "OHOS builds require armv8/aarch64, got: %s"
                % self.settings.arch)

    def layout(self):
        basic_layout(self)

    def build_requirements(self):
        # configure gates unconditionally on a working pkg-config
        # (the PKG_CHECK_MODULES expansion inside OMNI_OPENSSL_ROOT's
        # macro runs PKG_PROG_PKG_CONFIG's "at least version 0.9.0"
        # check even with the default --with-openssl=no, whose branch is
        # a shell no-op). Without it configure dies with
        # "pkg-config not found" although SSL stays off anyway (no system
        # OpenSSL on the worker, auto-detected). pkgconf is pkg-config
        # compatible and answers --atleast-pkgconfig-version; its result
        # is unused here. Precedent: ctpl/0.3.5, cassbeam (tool_requires
        # pkgconf/3.0.5 on OHOS).
        self.tool_requires("pkgconf/3.0.5")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _python3(self):
        # omniidl backends run on Python 3 at build time. Prefer the
        # hmbs-injected absolute path, then PATH lookup; never rely on
        # an unresolved bare name inside build().
        candidate = os.environ.get("HMBS_PYTHON3")
        if candidate:
            return candidate
        from shutil import which
        found = which("python3")
        return found if found else "python3"

    # E386: the ohos-aarch64 profile exports
    # CONFIG_SHELL=/data/service/hnp/bin/bash and autoconf re-execs
    # itself through it (configure:139 exec); that bash is inaccessible
    # from the conan build cache dir on some HMDFS runners (Error 127).
    # os.environ alone is NOT enough: Autotools.configure() sources the
    # generated conanbuild.sh (profile buildenv + toolchain env) in the
    # child shell AFTER Python sets os.environ, so the stale export can
    # overwrite our value right before configure runs. The guard is
    # therefore two-layered, always going through the Autotools helper
    # so the toolchain env (CC/CFLAGS/LDFLAGS with OHOS sysroot and
    # --target) is preserved:
    #   1) generate(): save an Environment build-scope script
    #      (zzz_hmbs_shell, sorts after conanautotoolchain) exporting
    #      CONFIG_SHELL/SHELL=/bin/sh (HMBS-guaranteed) so the
    #      aggregated conanbuild.sh ends with the good value;
    #   2) build()/package(): os.environ override + on-disk scrub of
    #      any generated .sh still containing the stale hnp bash path.
    # A bare command prefix must NOT be used with a manual
    # self.run(configure) call: bypassing the Autotools helper drops
    # the whole toolchain env and configure falls back to a bare clang
    # without target/sysroot flags. c-ares-dev/1.34.5 and
    # c-client/2007f use the same os.environ + Environment pattern.
    _STALE_SHELLS = ("/data/service/hnp/bin/bash",)

    def _apply_shell_guard(self):
        os.environ["CONFIG_SHELL"] = "/bin/sh"
        os.environ["SHELL"] = "/bin/sh"
        self._scrub_shell_scripts()

    def _scrub_shell_scripts(self):
        roots = [self.build_folder, getattr(self, "base_build_folder", None)]
        seen = set()
        for root in roots:
            if not root or root in seen:
                continue
            seen.add(root)
            if not os.path.isdir(root):
                continue
            for dirpath, _dirnames, filenames in os.walk(root):
                for name in filenames:
                    if not name.endswith(".sh"):
                        continue
                    path = os.path.join(dirpath, name)
                    try:
                        with open(path, "r", encoding="utf-8", errors="replace") as handle:
                            content = handle.read()
                    except OSError:
                        continue
                    fixed = content
                    for stale in self._STALE_SHELLS:
                        fixed = fixed.replace(stale, "/bin/sh")
                    if fixed != content:
                        try:
                            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                                handle.write(fixed)
                        except OSError as exc:
                            self.output.warning("cannot scrub %s: %s" % (path, exc))
                            continue
                        self.output.info("scrubbed stale CONFIG_SHELL path in %s" % path)

    # E011/E129 + HMBS [unsafe_local_mktemp] (c-ares 0003-configure.patch
    # + cyrus-sasl-login precedent, adapted to the Autotools helper).
    # omniORB's configure is autoconf 2.71 output and embeds
    # `umask 077 && mktemp -d "./confXXXXXX"` both for its own temp dir
    # and for the generated config.status. On HMDFS that yields an
    # owner-unwritable dir (0700 + setgid -> drwx--S---), so config.status
    # dies with `can't create ./conf*/subs1.awk: Permission denied`
    # (this round's fatal). Rewriting 077 -> 022 keeps the same
    # mktemp/mkdir flow with group/world-readable temp dirs, safe on a
    # single-user build machine. Runs after apply_conandata_patches so
    # the patched tree is what gets fixed; no-op when the pattern is
    # absent (healthy runners: only temp-dir bits change).
    def _fix_autoconf_umask(self):
        configure = os.path.join(self.source_folder, "configure")
        try:
            with open(configure, "r", encoding="utf-8",
                      errors="surrogateescape") as handle:
                content = handle.read()
        except OSError as exc:
            self.output.warning("umask fix: cannot read %s: %s"
                                % (configure, exc))
            return
        if "umask 077" not in content:
            self.output.info("umask fix: no umask 077 in configure, skip")
            return
        count = content.count("umask 077")
        content = content.replace("umask 077", "umask 022")
        try:
            with open(configure, "w", encoding="utf-8",
                      errors="surrogateescape", newline="\n") as handle:
                handle.write(content)
        except OSError as exc:
            self.output.warning("umask fix: cannot write %s: %s"
                                % (configure, exc))
            return
        self.output.info("umask fix: replaced %d umask 077 -> 022 in %s"
                         % (count, configure))

    # CI #66639/#67804 (2026-10-02): build-release/lib/_omniidl...so
    # dlopen says "Permission denied" while the same tree links
    # libomnithread fine. Link only needs read; dlopen needs PROT_EXEC
    # mmap. /storage build trees (HMDFS/FUSE) are noexec for exec
    # mappings. Two-layer fix, healthy runners no-op:
    #   1) _fix_makefile_symlinks: export real file copies instead of the
    #      versioned symlink chain (lib.so -> lib.so.N -> lib.so.N.M).
    #      HMDFS does not reliably resolve that chain (E018/E050); copies
    #      hold identical bytes.
    #   2) _patch_omniidl_noexec_fallback (hardened for #67804): round 1
    #      patched only omniidl.in and tried a single base dir (TMPDIR or
    #      /tmp), yet CI failed byte-identical. Two holes: (a) the
    #      build-time IDL path can also run through omniidlrun.py (same
    #      "import _omniidl" block, exported as-is; the checked-in shell
    #      wrapper execs it), which had no fallback; (b) on CI workers
    #      TMPDIR/TMP are unset and /tmp may be missing or itself noexec,
    #      so mkdtemp raised and the original error was re-raised with
    #      zero diagnostics. The hardened fallback patches BOTH python3
    #      scripts, scans archlibdir + binarchdir + every sys.path entry +
    #      the sibling lib/ for _omniidl files, and retries the
    #      copy/import across several temp bases (TMPDIR/TMP/TEMP/
    #      XDG_RUNTIME_DIR/RUNNER_TEMP, /dev/shm, /var/tmp, /tmp,
    #      /data/local/tmp, $HOME, ~/.cache), logging each attempt to stderr so
    #      the next log shows what was found and where the exec copy
    #      landed. Only permission errors enter the branch; other
    #      ImportErrors still raise immediately. First-import success
    #      keeps the upstream path untouched.
    #   3) CI #68143 (2026-10-03): the #67804 fallback DID run, but every
    #      base failed: TMPDIR (/storage/.../.cache/tmp) + ~/.cache both
    #      \"import failed: Permission denied\" (same HMDFS noexec as the
    #      build tree), /tmp \"mkdtemp failed: Read-only file system\",
    #      /data/local/tmp \"not a dir\". So the retry loop needs tmpfs
    #      exec candidates that live off /storage (XDG_RUNTIME_DIR,
    #      /dev/shm, /var/tmp) plus $HOME itself, a chmod 0755 attempt on
    #      the exec copy (OHOS musl dlopen reports EACCES for file-mode
    #      issues too; no-op where chmod is unavailable), and one-shot
    #      mount/df diagnostics so the next log shows the worker's exec
    #      map even if all bases still fail.
    #   4) CI #68271 (2026-10-03): the expanded retry ALSO ran to
    #      exhaustion (/dev/shm mkdtemp Permission denied, /var/tmp +
    #      /data/local/tmp not dirs, /tmp read-only, $HOME + ~/.cache +
    #      TMPDIR all import Permission denied). Every writable dir on
    #      that worker is HMDFS noexec, so no copy-to-temp can ever
    #      dlopen there. Escape hatch: os.memfd_create anonymous file +
    #      dlopen via /proc/self/fd/N (no filesystem mount involved;
    #      only runs after all filesystem bases already failed, so
    #      previously-fatal path only).
    #   5) CI #74775 (2026-10-09, worker 012): all filesystem bases AND
    #      memfd denied again, but the log proves the mount is NOT noexec:
    #      the freshly built C executable ../../../bin/omkdepend RUNS fine
    #      from the same /storage build tree, while only the dlopen() of
    #      the freshly built _omniidl...so fails with EACCES. The
    #      difference is file mode at creation: executables are installed
    #      via `install -c -m 0755` (INSTEXEFLAGS) whereas shared libs use
    #      `install -c -m 0644` (INSTLIBFLAGS) plus `cp -f` soname copies
    #      (0644); OHOS/HMDFS ignores chmod-after-the-fact (HMBS reports
    #      chmod capability 0), so every fallback copy (copyfile + chmod,
    #      same 0644) failed identically on every base -- including
    #      /data/storage/el2/base/cache, which is exec-capable on HMBS
    #      runners. Fix: create every .so with the exec bit AT CREATION
    #      (open(O_CREAT, 0755) / `install -m 0755`, the proven omkdepend
    #      path), never chmod-after. Concretely: (a) the ExportShared*
    #      soname/libname copies use `$(INSTALL) -m 0755` instead of
    #      `cp -f`; (b) the omniidl fallback writes its exec copy via
    #      os.open(..., 0755) and logs src/dst octal modes; (c) package()
    #      mirrors/materializes of importable _omniidl .so use the same
    #      0755-at-creation helper (.py files unchanged). Mode lines in
    #      diagnostics make the next round decisive either way.
    #   6) CI #81330 (2026-10-10, worker 030): decisive falsification --
    #      the patch DID apply (`install -m 0755` ran, src-modes shows
    #      0o750/0o755 on every copy) yet dlopen still fails EACCES on
    #      every base and via memfd. File mode is therefore NOT the
    #      blocker; the worker denies dlopen() of any freshly built .so
    #      while execve of freshly built executables works. Fix: build
    #      the IDL front-end as a standalone executable with the parser
    #      statically registered (upstream Win32 OMNIIDL_EXECUTABLE
    #      precedent: main() + PyImport_AppendInittab in idlpython.cc, so
    #      no _omniidl.so is ever loaded) and point OMNIIDL at it for all
    #      in-build stub generation; install the same binary as the
    #      packaged bin/omniidl so test_package needs no dlopen either.
    def _fix_makefile_symlinks(self):
        for rel in ("mk/beforeauto.mk.in", "mk/unix.mk"):
            path = os.path.join(self.source_folder, rel)
            try:
                with open(path, "r", encoding="utf-8",
                          errors="surrogateescape") as handle:
                    content = handle.read()
            except OSError as exc:
                self.output.info("symlink fix: cannot read %s: %s"
                                 % (rel, exc))
                continue
            orig = content
            # CI #68962: the two exact patterns above never matched
            # (log shows "no ln -s" yet build still runs `ln -s`), because
            # the mk files use tabs/other spacing. Fall back to a generic
            # token replace so ExportSharedLibraryToDir really emits copies.
            # CI #74775: copies must be created with the exec bit AT
            # CREATION (`$(INSTALL) -m 0755`, the proven omkdepend path):
            # plain `cp -f` yields 0644 and HMDFS ignores chmod-after, so
            # dlopen keeps failing with EACCES on locked-down workers.
            n_exact = 0
            for _old, _new in (
                    ("ln -s $(<F) $soname;", "$(INSTALL) -m 0755 $(<F) $soname;"),
                    ("ln -s $soname $libname;", "$(INSTALL) -m 0755 $soname $libname;")):
                if _old in content:
                    n_exact += content.count(_old)
                    content = content.replace(_old, _new)
            n_generic = 0
            if n_exact == 0 and "ln -s" in content:
                n_generic = content.count("ln -s")
                content = content.replace("ln -s", "$(INSTALL) -m 0755")
            if content == orig:
                self.output.info("symlink fix: no ln -s in %s, skip" % rel)
                continue
            try:
                with open(path, "w", encoding="utf-8",
                          errors="surrogateescape", newline="\n") as handle:
                    handle.write(content)
            except OSError as exc:
                self.output.warning("symlink fix: cannot write %s: %s"
                                    % (path, exc))
                continue
            self.output.info("symlink fix: ln -s -> install -m 0755 in %s (exact=%d generic=%d)"
                             % (rel, n_exact, n_generic))

    def _probe_libpython(self):
        # CI #81330: locate libpython for the OMNIIDL_EXECUTABLE static
        # binary (see _patch_omniidl_executable). Runs on the worker, so
        # paths are exact. Prefers the static archive (fully
        # self-contained exe, no runtime search); else shared with an
        # rpath. Returns (link_flags, exec_prefix) or (None, None) when
        # nothing usable is found (caller keeps the script path then).
        # CI #82966 hardening (2026-10-11): the first probe only looked
        # at LIBDIR/LDLIBRARY/LIBPYTHON, so any worker whose dev files
        # live in LIBPL, exec_prefix/lib, or a versioned subdir (or
        # whose LIBDIR is a build-time path absent on device) fell back
        # to the dead script path and failed again at the same
        # _omniidl.so dlopen. This version additionally queries LIBPL /
        # BLDLIBRARY / VERSION / ABIFLAGS, consults `python3-config
        # --ldflags --embed` when present, and globs every candidate
        # dir for libpython*.a / libpython*.so* before giving up; every
        # step is logged so the next CI log shows exactly what the
        # worker offers. Healthy runners keep the previous result.
        import glob
        import json
        import subprocess

        py = self._python3()
        prog = ("import sys, sysconfig, json; print(json.dumps({"
                "'libdir': sysconfig.get_config_var('LIBDIR'),"
                "'libpl': sysconfig.get_config_var('LIBPL'),"
                "'ldversion': sysconfig.get_config_var('LDVERSION'),"
                "'ldlibrary': sysconfig.get_config_var('LDLIBRARY'),"
                "'libpython': sysconfig.get_config_var('LIBPYTHON'),"
                "'bldlibrary': sysconfig.get_config_var('BLDLIBRARY'),"
                "'version': sysconfig.get_config_var('VERSION'),"
                "'abiflags': sysconfig.get_config_var('ABIFLAGS'),"
                "'shared': sysconfig.get_config_var('Py_ENABLE_SHARED'),"
                "'libs': sysconfig.get_config_var('LIBS'),"
                "'syslibs': sysconfig.get_config_var('SYSLIBS'),"
                "'exec_prefix': sys.exec_prefix,"
                "'base_exec_prefix': getattr(sys, 'base_exec_prefix', '')}))")
        try:
            proc = subprocess.run(
                [py, "-c", prog], stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, timeout=60,
                text=True, errors="replace")
        except Exception as exc:
            self.output.warning("libpython probe: exec failed: %r" % (exc,))
            return None, None
        if proc.returncode != 0:
            self.output.warning("libpython probe: rc=%s out=%s"
                                % (proc.returncode,
                                   (proc.stdout or "")[:500]))
            return None, None
        try:
            info = json.loads((proc.stdout or "").strip().splitlines()[-1])
        except Exception as exc:
            self.output.warning("libpython probe: parse failed: %r" % (exc,))
            return None, None
        libdir = info.get("libdir") or ""
        libpl = info.get("libpl") or ""
        ldversion = info.get("ldversion") or ""
        ldlibrary = info.get("ldlibrary") or ""
        prefix = info.get("exec_prefix") or ""
        base_prefix = info.get("base_exec_prefix") or ""
        extra = " ".join(part for part in
                         ((info.get("libs") or ""),
                          (info.get("syslibs") or "")) if part).strip()
        self.output.info("libpython probe: sysconfig libdir=%s libpl=%s "
                         "ldversion=%s ldlibrary=%s libpython=%s "
                         "bldlibrary=%s version=%s abiflags=%s shared=%s "
                         "exec_prefix=%s base_exec_prefix=%s"
                         % (libdir, libpl, ldversion, ldlibrary,
                            info.get("libpython"), info.get("bldlibrary"),
                            info.get("version"), info.get("abiflags"),
                            info.get("shared"), prefix, base_prefix))
        # 1) python3-config --ldflags --embed: the interpreter's own
        # answer for how to embed it. Sibling of the probed python3
        # when HMBS_PYTHON3 is an absolute path, else PATH lookup.
        cfg_flags = ""
        cfg_cands = []
        try:
            import shutil as _shutil_cfg
            if py and py != "python3" and (
                    py.endswith("/python3") or py.endswith("python3")):
                cfg_cands.append(py + "-config")
            which_cfg = _shutil_cfg.which("python3-config")
            if which_cfg and which_cfg not in cfg_cands:
                cfg_cands.append(which_cfg)
        except Exception:
            cfg_cands = []
        for cfg in cfg_cands:
            try:
                cproc = subprocess.run(
                    [cfg, "--ldflags", "--embed"], stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, timeout=60,
                    text=True, errors="replace")
            except Exception as exc:
                self.output.info("libpython probe: %s failed: %r"
                                 % (cfg, exc))
                continue
            out = (cproc.stdout or "").strip()
            self.output.info("libpython probe: %s --ldflags --embed rc=%s "
                             "out=%s" % (cfg, cproc.returncode, out[:400]))
            if cproc.returncode == 0 and out:
                cfg_flags = out.replace("\n", " ").strip()
                break
        # 2) Assemble candidate dirs (existing ones only) and glob for
        # libpython artifacts. LIBDIR first (previous behavior), then
        # LIBPL / prefix lib dirs / well-known system dirs.
        search_dirs = []
        for _d in (libdir, libpl,
                   os.path.join(prefix, "lib") if prefix else "",
                   os.path.join(base_prefix, "lib") if base_prefix else "",
                   "/system/lib64", "/system/lib"):
            if _d and _d not in search_dirs and os.path.isdir(_d):
                search_dirs.append(_d)
        self.output.info("libpython probe: search_dirs=%s"
                         % (search_dirs if search_dirs else "<none>"))
        for _d in search_dirs:
            try:
                _names = sorted(os.listdir(_d))
            except OSError as exc:
                self.output.info("libpython probe: listdir %s failed: %s"
                                 % (_d, exc))
                continue
            _hits = [n for n in _names if n.startswith("libpython")]
            self.output.info("libpython probe: %s libpython*=%s"
                             % (_d, _hits[:12] if _hits else "<none>"))
        static = os.path.join(libdir, ldlibrary) if libdir and ldlibrary else ""
        if static.endswith(".a") and os.path.isfile(static):
            self.output.info("libpython probe: static %s" % static)
            return ("%s %s" % (static, extra)).strip(), prefix
        # Exact-name shared candidates (previous behavior).
        for cand in (os.path.join(libdir, "libpython%s.so" % ldversion)
                     if (libdir and ldversion) else "",
                     os.path.join(libdir, info.get("libpython") or "")
                     if libdir else ""):
            if cand and os.path.isfile(cand):
                self.output.info("libpython probe: shared %s" % cand)
                return ("-L%s -lpython%s -Wl,-rpath,%s"
                        % (libdir, ldversion, libdir)), prefix
        # Glob fallback: any libpython*.a preferred, else any
        # libpython*.so* (versioned .so.1.0 included). Static links by
        # path; shared links by -L/-l with rpath on its own dir.
        for _d in search_dirs:
            try:
                _static_hits = sorted(glob.glob(os.path.join(_d, "libpython*.a")))
            except Exception:
                _static_hits = []
            for _hit in _static_hits:
                if os.path.isfile(_hit):
                    self.output.info("libpython probe: glob static %s" % _hit)
                    return ("%s %s" % (_hit, extra)).strip(), prefix
        for _d in search_dirs:
            try:
                _shared_hits = sorted(glob.glob(os.path.join(_d, "libpython*.so*")))
            except Exception:
                _shared_hits = []
            for _hit in _shared_hits:
                if os.path.isfile(_hit):
                    self.output.info("libpython probe: glob shared %s" % _hit)
                    return ("-L%s -lpython%s -Wl,-rpath,%s"
                            % (_d, ldversion, _d)), prefix
        # python3-config answer as last resort before giving up: it may
        # reference -lpythonX.Y resolvable via the toolchain library
        # search even when no single file matched above.
        if cfg_flags and ("-lpython" in cfg_flags or "libpython" in cfg_flags):
            self.output.info("libpython probe: config fallback %s" % cfg_flags[:300])
            return cfg_flags, prefix
        # Unverified -lpython<ldversion> so the link step (not the stub
        # step) decides: a missing dev lib then fails loudly at the
        # static-exe link instead of silently keeping the dead script.
        if ldversion:
            self.output.warning("libpython probe: no file hit; trying "
                                "unverified -lpython%s (link will decide)"
                                % ldversion)
            return ("-lpython%s %s" % (ldversion, extra)).strip(), prefix
        self.output.warning("libpython probe: no static/shared lib in %s "
                            "(ldlibrary=%s libpython=%s libpl=%s)"
                            % (libdir, ldlibrary, info.get("libpython"),
                               libpl))
        return None, None

    def _fix_idlpython_pyargv(self):
        # Preflight 2026-10-10 (Python 3.14): the OMNIIDL_EXECUTABLE
        # main() in idlpython.cc calls PySys_SetArgv(argc, argv) with
        # char**, but since Python 3 the API takes wchar_t** (3.14
        # header: PySys_SetArgv(int, wchar_t**), char** no longer
        # converts) so idlpython_exe.o fails with no matching function
        # for call to PySys_SetArgv. Upstream predates Python 3 here
        # (Win32-only precedent, never built against py3 on unix).
        # Minimal fix: decode argv via Py_DecodeLocale and pass wchar_t**.
        # Same treatment for Py_SetProgramName(argv[0]) when present
        # (also wchar_t* since py3); other errors surface verbatim.
        import re as _re
        rel = os.path.join("src", "tool", "omniidl", "cxx", "idlpython.cc")
        path = os.path.join(self.source_folder, rel)
        try:
            with open(path, "r", encoding="utf-8",
                      errors="surrogateescape") as handle:
                content = handle.read()
        except OSError as exc:
            self.output.warning("pyargv fix: cannot read %s: %s"
                                % (rel, exc))
            return
        orig = content
        if "#include <stdlib.h>" not in content:
            content = content.replace(
                "#include <Python.h>",
                "#include <Python.h>\n#include <stdlib.h>", 1)
        widen = (
            "{\n"
            "  wchar_t **_hmbs_wargv = (wchar_t **)malloc(\n"
            "      sizeof(wchar_t *) * ((argc > 0) ? argc : 1));\n"
            "  if (_hmbs_wargv) {\n"
            "    int _hmbs_i;\n"
            "    for (_hmbs_i = 0; _hmbs_i < argc; ++_hmbs_i) {\n"
            "      _hmbs_wargv[_hmbs_i] = Py_DecodeLocale(argv[_hmbs_i], NULL);\n"
            "    }\n"
            "    PySys_SetArgv(argc, _hmbs_wargv);\n"
            "  }\n"
            "}")
        content, n_argv = _re.subn(
            r"PySys_SetArgv\s*\(\s*argc\s*,\s*argv\s*\)\s*;",
            widen, content)
        prog_widen = (
            "{ wchar_t *_hmbs_prog = Py_DecodeLocale(argv[0], NULL); \n"
            "if (_hmbs_prog) Py_SetProgramName(_hmbs_prog); }")
        content, n_prog = _re.subn(
            r"Py_SetProgramName\s*\(\s*argv\s*\[\s*0\s*\]\s*\)\s*;",
            prog_widen, content)
        if content == orig:
            self.output.info("pyargv fix: no PySys_SetArgv pattern, skip")
            return
        try:
            with open(path, "w", encoding="utf-8",
                      errors="surrogateescape", newline="\n") as handle:
                handle.write(content)
        except OSError as exc:
            self.output.warning("pyargv fix: cannot write %s: %s"
                                % (rel, exc))
            return
        self.output.info("pyargv fix: widened argv in %s (argv=%d prog=%d)"
                         % (rel, n_argv, n_prog))

    def _patch_omniidl_preprocessor_paths(self):
        # True-machine 2026-10-12 round 4: static exe runs the front end
        # but dies with "/bin/sh: omnicpp: inaccessible or not found".
        # Round 3 prepended TOP/lib+TOP/bin to os.environ PATH, yet the
        # failure is byte-identical, so the prepend never reached the
        # preprocessor shell (Autotools.make re-sources the aggregated
        # conanbuild.sh, which resets PATH to generate-time values and
        # drops build()-time os.environ PATH edits; a NEW var such as
        # HMBS_OMNIIDL_EXEC_BASE survives, PATH does not). Different
        # route: fix the lookup at the source instead of the env --
        # patch omniidl/main.py so the static exe finds omnicpp without
        # PATH. Upstream resolves [dirname(_omniidl.__file__),
        # dirname(sys.argv[0])]; the static module has no __file__ and
        # make invokes via relative ../../../bin/omniidl_static while
        # unix cccp/dir.mk exports omnicpp to LIBDIR (TOP/lib), not
        # BINDIR, so both candidates miss and it falls back to bare
        # "omnicpp". The patch appends abspath + sibling-lib candidates
        # (TOP/bin abspath, sys.executable dir, and each entry's
        # ../lib + abspath form); the existing isfile loop then picks
        # an absolute omnicpp path. No PATH reliance, healthy runners
        # only gain extra isfile checks.
        rel = os.path.join("src", "tool", "omniidl", "python3",
                           "omniidl", "main.py")
        path = os.path.join(self.source_folder, rel)
        try:
            with open(path, "r", encoding="utf-8",
                      errors="surrogateescape") as handle:
                content = handle.read()
        except OSError as exc:
            self.output.warning("omnicpp fix: cannot read %s: %s"
                                % (rel, exc))
            return
        if "HMBS_OMNIIDL_PREPROCESSOR_SIBLING_LIB" in content:
            self.output.info("omnicpp fix: already applied, skip")
            return
        anchor = "    preprocessor_paths.append(os.path.dirname(sys.argv[0]))"
        if anchor not in content:
            self.output.warning("omnicpp fix: anchor not found in %s, skip"
                                % rel)
            return
        block = (
            "\n"
            "    # HMBS/OHOS 2026-10-12 round 4 (omnicpp sibling lib): static\n"
            "    # exe has no _omniidl.__file__ and unix omnicpp lives in\n"
            "    # sibling lib/, not bin/. Add abspath + sibling-lib\n"
            "    # candidates so the isfile loop below finds an absolute\n"
            "    # path without PATH. Marker: HMBS_OMNIIDL_PREPROCESSOR_SIBLING_LIB.\n"
            "    try:\n"
            "        _hmbs_cands = []\n"
            "        _a0 = sys.argv[0] if sys.argv and sys.argv[0] else \"\"\n"
            "        if _a0:\n"
            "            try:\n"
            "                _d = os.path.dirname(os.path.abspath(_a0))\n"
            "            except Exception:\n"
            "                _d = \"\"\n"
            "            if _d:\n"
            "                _hmbs_cands.append(_d)\n"
            "        try:\n"
            "            _ed = os.path.dirname(os.path.abspath(sys.executable))\n"
            "        except Exception:\n"
            "            _ed = \"\"\n"
            "        if _ed:\n"
            "            _hmbs_cands.append(_ed)\n"
            "        for _b in list(preprocessor_paths) + list(_hmbs_cands):\n"
            "            if not _b:\n"
            "                continue\n"
            "            try:\n"
            "                _absb = _b if os.path.isabs(_b) else os.path.abspath(_b)\n"
            "            except Exception:\n"
            "                _absb = \"\"\n"
            "            if _absb and _absb not in preprocessor_paths and _absb not in _hmbs_cands:\n"
            "                _hmbs_cands.append(_absb)\n"
            "            try:\n"
            "                _sib = os.path.normpath(os.path.join(_absb or _b, \"..\", \"lib\"))\n"
            "            except Exception:\n"
            "                _sib = \"\"\n"
            "            if _sib and _sib not in preprocessor_paths and _sib not in _hmbs_cands:\n"
            "                _hmbs_cands.append(_sib)\n"
            "        for _c in _hmbs_cands:\n"
            "            if _c and _c not in preprocessor_paths:\n"
            "                preprocessor_paths.append(_c)\n"
            "    except Exception:\n"
            "        pass\n"
        )
        content = content.replace(anchor, anchor + block, 1)
        try:
            with open(path, "w", encoding="utf-8",
                      errors="surrogateescape", newline="\n") as handle:
                handle.write(content)
        except OSError as exc:
            self.output.warning("omnicpp fix: cannot write %s: %s"
                                % (rel, exc))
            return
        self.output.info("omnicpp fix: sibling-lib candidates added in %s"
                         % rel)

    def _patch_omniidl_executable(self, pylib):
        # CI #81330: append a standalone-omniidl build to the autoconf
        # section of src/tool/omniidl/cxx/dir.mk and point mk/unix.mk's
        # OMNIIDL at it. The binary links the normal parser objects plus
        # idlpython.cc recompiled with -DOMNIIDL_EXECUTABLE (main() +
        # AppendInittab, upstream Win32 precedent) against the probed
        # libpython flags (filter-out drops the module-build idlpython.o so\n        # the exe link has no duplicate symbols); make then exports it as bin/omniidl_static and
        # every stub rule uses it instead of the python script, so no
        # _omniidl.so is ever dlopened during the build. Returns True on
        # success; any missing anchor warns and returns False (caller
        # keeps the script path, healthy runners unaffected).
        block = (
            "# HMBS/OHOS CI #81330: standalone IDL front-end (dlopen of\n"
            "# freshly built .so is denied on locked-down workers, execve\n"
            "# works; upstream Win32 OMNIIDL_EXECUTABLE precedent).\n"
            "# CI #85709 (2026-10-12, true-machine): the previous revision\n"
            "# linked directly to $(BASE_OMNI_TREE)/$(BINDIR)/omniidl_static\n"
            "# (source tree) while the stub driver resolves via\n"
            "# $(TOOLBINDIR)/omniidl_static = $(TOP)/$(BINDIR) (build tree),\n"
            "# so src/lib/omniORB died with\n"
            "# `../../../bin/omniidl_static: No such file`. Mirror the\n"
            "# upstream Win32 pattern instead: link a local omniidl_static\n"
            "# in this dir, then $(ExportExecutable) copies it to\n"
            "# $(EXPORT_TREE)/$(BINDIR) (== $(TOP)/$(BINDIR), the exact\n"
            "# TOOLBINDIR the stub rules exec). No self-copy: link target\n"
            "# and install destination differ.\n"
            "HMBS_OMNIIDL_STATIC_EXE = omniidl_static\n"
            "\n"
            "idlpython_exe.o: idlpython.cc\n"
            "\t$(CXX) -c $(CXXFLAGS) $(DIR_CPPFLAGS) -DOMNIIDL_EXECUTABLE -o $@ $<\n"
            "\n"
            "$(HMBS_OMNIIDL_STATIC_EXE): $(filter-out idlpython.o,$(OBJS)) idlpython_exe.o\n"
            "\t@(libs=\"" + pylib + "\"; $(CXXExecutable))\n"
            "\n"
            "all:: $(HMBS_OMNIIDL_STATIC_EXE)\n"
            "\n"
            "export:: $(HMBS_OMNIIDL_STATIC_EXE)\n"
            "\t@$(ExportExecutable)\n"
            "\n"
        )
        cxx_rel = os.path.join("src", "tool", "omniidl", "cxx", "dir.mk")
        cxx_path = os.path.join(self.source_folder, cxx_rel)
        try:
            with open(cxx_path, "r", encoding="utf-8",
                      errors="surrogateescape") as handle:
                content = handle.read()
        except OSError as exc:
            self.output.warning("omniidl exe: cannot read %s: %s"
                                % (cxx_rel, exc))
            return False
        anchor = "ifdef INSTALLTARGET"
        head = content.find("export:: $(shlib)")
        idx = content.find(anchor, head) if head >= 0 else -1
        if idx < 0 or head < 0:
            self.output.warning("omniidl exe: anchor not found in %s, skip"
                                % cxx_rel)
            return False
        if "HMBS_OMNIIDL_STATIC_EXE" in content:
            self.output.info("omniidl exe: already applied, skip")
        else:
            content = content[:idx] + block + content[idx:]
            try:
                with open(cxx_path, "w", encoding="utf-8",
                          errors="surrogateescape", newline="\n") as handle:
                    handle.write(content)
            except OSError as exc:
                self.output.warning("omniidl exe: cannot write %s: %s"
                                    % (cxx_rel, exc))
                return False
            self.output.info("omniidl exe: appended static-exe rules to %s"
                             % cxx_rel)
        unix_rel = os.path.join("mk", "unix.mk")
        unix_path = os.path.join(self.source_folder, unix_rel)
        try:
            with open(unix_path, "r", encoding="utf-8",
                      errors="surrogateescape") as handle:
                lines = handle.read().splitlines(keepends=True)
        except OSError as exc:
            self.output.warning("omniidl exe: cannot read %s: %s"
                                % (unix_rel, exc))
            return False
        done = False
        for pos, line in enumerate(lines):
            if line.strip() == "OMNIIDL = $(BASE_OMNI_TREE)/$(BINDIR)/omniidl":
                lines[pos] = ("OMNIIDL = "
                              "$(BASE_OMNI_TREE)/$(BINDIR)/omniidl_static\n")
                done = True
                break
        if not done:
            if any("omniidl_static" in line for line in lines):
                self.output.info("omniidl exe: OMNIIDL already static, skip")
            else:
                self.output.warning("omniidl exe: OMNIIDL line not found "
                                    "in %s, skip" % unix_rel)
                return False
        else:
            try:
                with open(unix_path, "w", encoding="utf-8",
                          errors="surrogateescape", newline="\n") as handle:
                    handle.writelines(lines)
            except OSError as exc:
                self.output.warning("omniidl exe: cannot write %s: %s"
                                    % (unix_rel, exc))
                return False
            self.output.info("omniidl exe: OMNIIDL now points at "
                             "bin/omniidl_static in %s" % unix_rel)
        # CI #85708 (2026-10-12): the unix.mk redirect alone never took
        # effect. Full CI log proves the static binary WAS linked yet the
        # stub step still ran `../../../bin/omniidl` (relative TOOLBINDIR
        # form, not the absolute BASE_OMNI_TREE form): the effective
        # driver is mk/beforeauto.mk.in's native branch
        # `OMNIORB_IDL_ONLY = $(TOOLBINDIR)/omniidl -bcxx` (config.status
        # generates beforeauto.mk from it pre-make; unix.mk's
        # OMNIORB_IDL_ONLY is shadowed), so every in-build stub rule
        # bypassed OMNIIDL entirely. Redirect that line at the .in level
        # (pre-configure, same mechanism as the proven symlink fix).
        # rtems/vxWorks/mingw drivers are other platforms, untouched.
        before_rel = os.path.join("mk", "beforeauto.mk.in")
        before_path = os.path.join(self.source_folder, before_rel)
        try:
            with open(before_path, "r", encoding="utf-8",
                      errors="surrogateescape") as handle:
                before_lines = handle.read().splitlines(keepends=True)
        except OSError as exc:
            self.output.warning("omniidl exe: cannot read %s: %s"
                                % (before_rel, exc))
            return False
        before_done = False
        for pos, line in enumerate(before_lines):
            if line.strip() == ("OMNIORB_IDL_ONLY = $(TOOLBINDIR)/omniidl"
                                " -bcxx"):
                before_lines[pos] = ("OMNIORB_IDL_ONLY = "
                                     "$(TOOLBINDIR)/omniidl_static -bcxx\n")
                before_done = True
                break
        if not before_done:
            if any("omniidl_static" in line for line in before_lines):
                self.output.info("omniidl exe: OMNIORB_IDL_ONLY already "
                                 "static, skip")
            else:
                self.output.warning("omniidl exe: OMNIORB_IDL_ONLY line not "
                                    "found in %s, skip" % before_rel)
                return False
        else:
            try:
                with open(before_path, "w", encoding="utf-8",
                          errors="surrogateescape", newline="\n") as handle:
                    handle.writelines(before_lines)
            except OSError as exc:
                self.output.warning("omniidl exe: cannot write %s: %s"
                                    % (before_rel, exc))
                return False
            self.output.info("omniidl exe: OMNIORB_IDL_ONLY now points at "
                             "bin/omniidl_static in %s" % before_rel)
        return True

    def _patch_omniidl_noexec_fallback(self):
        # Both scripts carry the same "import _omniidl" block: omniidl.in
        # (template for the generated build-time omniidl) and
        # omniidlrun.py (exported as-is; the checked-in shell wrapper
        # execs it). Patching only one leaves the other fatal path open.
        for _leaf in ("omniidl.in", "omniidlrun.py"):
            _rel = os.path.join("src", "tool", "omniidl", "python3",
                                "scripts", _leaf)
            self._patch_one_omniidl_script(_rel)

    def _patch_one_omniidl_script(self, rel):
        path = os.path.join(self.source_folder, rel)
        try:
            with open(path, "r", encoding="utf-8",
                      errors="surrogateescape") as handle:
                content = handle.read()
        except OSError as exc:
            self.output.warning("omniidl fallback: cannot read %s: %s"
                                % (rel, exc))
            return
        if "_omniidl_import_with_noexec_fallback" in content:
            self.output.info("omniidl fallback: already applied, skip")
            return
        anchor = "try:\n    import _omniidl\n"
        if anchor not in content:
            self.output.warning("omniidl fallback: anchor not found, skip")
            return
        # Injected fallback body, one generated line per element.
        # Single-quoted conanfile strings so the generated "..." need no
        # escaping; an embedded \\n below becomes \n in the generated
        # script (a real escape there), while the join "\n" separates
        # generated lines.
        _fb = [
            'def _omniidl_import_with_noexec_fallback():',
            '    _first_msg = None',
            '    try:',
            '        import _omniidl as _mod',
            '        return _mod',
            '    except ImportError as _e:',
            '        _first_msg = _e',
            '    _err = str(_first_msg).lower()',
            '    if "permission denied" not in _err and "eacces" not in _err and "eperm" not in _err:',
            '        raise _first_msg',
            '    try:',
            '        import shutil as _shutil',
            '        import sysconfig as _sysconfig',
            '        import tempfile as _tempfile',
            '        import importlib as _importlib',
            '    except Exception:',
            '        raise _first_msg',
            '    try:',
            '        import importlib.util as _ilu',
            '    except Exception:',
            '        _ilu = None',
            '    _search_dirs = []',
            '    for _d in (archlibdir, binarchdir):',
            '        if _d and _d not in _search_dirs:',
            '            _search_dirs.append(_d)',
            '    for _d in list(sys.path):',
            '        if _d and _d not in _search_dirs:',
            '            _search_dirs.append(_d)',
            '    try:',
            '        _sib = os.path.join(os.path.dirname(binarchdir or ""), "lib")',
            '        if _sib and _sib not in _search_dirs:',
            '            _search_dirs.append(_sib)',
            '    except Exception:',
            '        pass',
            '    _candidates = []',
            '    for _d in _search_dirs:',
            '        try:',
            '            _names = os.listdir(_d)',
            '        except OSError:',
            '            continue',
            '        for _n in _names:',
            '            if _n.startswith("_omniidl"):',
            '                _p = os.path.join(_d, _n)',
            '                try:',
            '                    if os.path.isfile(_p):',
            '                        _candidates.append(_p)',
            '                except OSError:',
            '                    continue',
            '    _seen = set()',
            '    _uniq = []',
            '    for _p in _candidates:',
            '        if _p not in _seen:',
            '            _seen.add(_p)',
            '            _uniq.append(_p)',
            '    _sized = []',
            '    for _p in _uniq[:16]:',
            '        try:',
            '            _sized.append((os.path.getsize(_p), _p))',
            '        except OSError:',
            '            continue',
            '    _so = sorted([(s, p) for (s, p) in _sized if p.endswith(".so")], reverse=True)',
            '    _ver = sorted([(s, p) for (s, p) in _sized if not p.endswith(".so")], reverse=True)',
            '    _ordered = [p for (s, p) in _so] + [p for (s, p) in _ver]',
            '    _ordered = _ordered[:4]',
            '    if not _ordered:',
            '        sys.stderr.write("omniidl: HMBS noexec fallback: no readable _omniidl file found\\n")',
            '        raise _first_msg',
            '    try:',
            '        _ext = _sysconfig.get_config_var("EXT_SUFFIX") or ".so"',
            '    except Exception:',
            '        _ext = ".so"',
            '    _bases = []',
            '    for _k in ("HMBS_OMNIIDL_EXEC_BASE", "TMPDIR", "TMP", "TEMP", "XDG_RUNTIME_DIR", "RUNNER_TEMP", "DOWNLOAD_CACHE", "HNP_PRIVATE_HOME", "HNP_PUBLIC_HOME"):',
            '        try:',
            '            _v = os.environ.get(_k)',
            '        except Exception:',
            '            _v = None',
            '        if _v and _v not in _bases:',
            '            _bases.append(_v)',
            '    for _v in ("/data/storage/el2/base/cache", "/data/storage/el2/base", "/data/cache", "/dev/shm", "/var/tmp", "/tmp", "/data/local/tmp"):',
            '        if _v not in _bases:',
            '            _bases.append(_v)',
            '    try:',
            '        _home = os.path.expanduser("~")',
            '        if _home and os.path.isdir(_home):',
            '            if _home not in _bases:',
            '                _bases.append(_home)',
            '            _hc = os.path.join(_home, ".cache")',
            '            if _hc not in _bases:',
            '                _bases.append(_hc)',
            '    except Exception:',
            '        pass',
            '    _diag = ["candidates=%r" % (sorted(_ordered),)]',
            '    try:',
            '        import subprocess as _sp',
            '    except Exception:',
            '        _sp = None',
            '    if _sp is not None:',
            '        try:',
            '            _p = _sp.run(["df", "-T"], stdout=_sp.PIPE, stderr=_sp.STDOUT, timeout=30, text=True, errors="replace")',
            '            _diag.append("df=" + ((_p.stdout or "")[:600].replace(chr(10), "|")))',
            '        except Exception as _e0:',
            '            _diag.append("df failed: %r" % (_e0,))',
            '        try:',
            '            _p2 = _sp.run(["mount"], stdout=_sp.PIPE, stderr=_sp.STDOUT, timeout=30, text=True, errors="replace")',
            '            _out2 = _p2.stdout or ""',
            '            _keep = [ln for ln in _out2.splitlines() if ("storage" in ln or "shm" in ln or "tmp" in ln)][:12]',
            '            _diag.append("mount=" + ("|".join(_keep)[:900] if _keep else _out2[:900].replace(chr(10), "|")))',
            '        except Exception as _e01:',
            '            _diag.append("mount failed: %r" % (_e01,))',
            '    _src_modes = []',
            '    for _p in _ordered:',
            '        try:',
            '            _src_modes.append("%s:%s" % (_p, oct(os.stat(_p).st_mode & 0o7777)))',
            '        except Exception as _e29:',
            '            _src_modes.append("%s:stat-failed:%r" % (_p, _e29))',
            '    _diag.append("src-modes=" + ("|".join(_src_modes)[:900] if _src_modes else "none"))',
            '    for _base in _bases:',
            '        try:',
            '            if not os.path.isdir(_base):',
            '                try:',
            '                    os.makedirs(_base, exist_ok=True)',
            '                except Exception:',
            '                    pass',
            '            if not os.path.isdir(_base):',
            '                _diag.append("%s: not a dir" % (_base,))',
            '                continue',
            '            _execdir = _tempfile.mkdtemp(prefix="omniidl_exec_", dir=_base)',
            '        except Exception as _e2:',
            '            _diag.append("%s: mkdtemp failed: %r" % (_base, _e2))',
            '            continue',
            '        for _src in _ordered:',
            '            _last_dmode = "nocopy"',
            '            try:',
            '                _dst = os.path.join(_execdir, "_omniidl" + _ext)',
            '                _fd = os.open(_dst, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)',
            '                try:',
            '                    _fout = os.fdopen(_fd, "wb")',
            '                except Exception:',
            '                    try:',
            '                        os.close(_fd)',
            '                    except Exception:',
            '                        pass',
            '                    raise',
            '                with _fout:',
            '                    with open(_src, "rb") as _fin:',
            '                        _shutil.copyfileobj(_fin, _fout, 1048576)',
            '                try:',
            '                    _last_dmode = oct(os.stat(_dst).st_mode & 0o7777)',
            '                except Exception as _e32:',
            '                    _last_dmode = "stat-failed:%r" % (_e32,)',
            '            except Exception as _e3:',
            '                _diag.append("%s: copy failed: %r [dstmode=%s]" % (_base, _e3, _last_dmode))',
            '                continue',
            '            try:',
            '                sys.modules.pop("_omniidl", None)',
            '            except Exception:',
            '                pass',
            '            try:',
            '                _importlib.invalidate_caches()',
            '            except Exception:',
            '                pass',
            '            try:',
            '                if _execdir not in sys.path:',
            '                    sys.path.insert(0, _execdir)',
            '                import _omniidl as _mod2',
            '                sys.stderr.write("omniidl: HMBS noexec fallback: loaded %s via %s\\n" % (_src, _dst))',
            '                return _mod2',
            '            except ImportError as _e4:',
            '                _diag.append("%s: import failed: %s [dstmode=%s]" % (_base, _e4, _last_dmode))',
            '                continue',
            '            except Exception as _e5:',
            '                _diag.append("%s: import error: %r [dstmode=%s]" % (_base, _e5, _last_dmode))',
            '                continue',
            '        if _ilu is not None:',
            '            for _src in _ordered:',
            '                try:',
            '                    _dst2 = os.path.join(_execdir, "_omniidl" + _ext)',
            '                    sys.modules.pop("_omniidl", None)',
            '                    _spec = _ilu.spec_from_file_location("_omniidl", _dst2)',
            '                    if _spec is None or _spec.loader is None:',
            '                        continue',
            '                    _mod3 = _ilu.module_from_spec(_spec)',
            '                    sys.modules["_omniidl"] = _mod3',
            '                    _spec.loader.exec_module(_mod3)',
            '                    sys.stderr.write("omniidl: HMBS noexec fallback: spec-loaded %s\\n" % (_dst2,))',
            '                    return _mod3',
            '                except Exception as _e6:',
            '                    _diag.append("%s: spec load failed: %r [dstmode=%s]" % (_base, _e6, _last_dmode))',
            '                    continue',
            '    _has_memfd = hasattr(os, "memfd_create")',
            '    _EFLoader = None',
            '    _memfd_diag = []',
            '    if _has_memfd:',
            '        try:',
            '            from importlib.machinery import ExtensionFileLoader as _EFLoader',
            '        except Exception:',
            '            _EFLoader = None',
            '        _mflags = getattr(os, "MFD_CLOEXEC", 0)',
            '        try:',
            '            _mflags |= getattr(os, "MFD_EXEC", 0)',
            '        except Exception:',
            '            pass',
            '        if _EFLoader is not None:',
            '            for _src in _ordered:',
            '                try:',
            '                    _fd = os.memfd_create("_omniidl", _mflags)',
            '                except Exception as _e7:',
            '                    _memfd_diag.append("memfd_create failed: %r" % (_e7,))',
            '                    break',
            '                try:',
            '                    with open(_src, "rb") as _fh:',
            '                        while True:',
            '                            _chunk = _fh.read(1048576)',
            '                            if not _chunk:',
            '                                break',
            '                            os.write(_fd, _chunk)',
            '                    _fdpath = "/proc/self/fd/%d" % (_fd,)',
            '                    _loader = _EFLoader("_omniidl", _fdpath)',
            '                    try:',
            '                        sys.modules.pop("_omniidl", None)',
            '                    except Exception:',
            '                        pass',
            '                    if _ilu is not None:',
            '                        _spec = _ilu.spec_from_loader("_omniidl", _loader)',
            '                        if _spec is None:',
            '                            raise RuntimeError("spec_from_loader returned None")',
            '                        _mod4 = _ilu.module_from_spec(_spec)',
            '                    else:',
            '                        import types as _types',
            '                        _mod4 = _types.ModuleType("_omniidl")',
            '                    sys.modules["_omniidl"] = _mod4',
            '                    _loader.exec_module(_mod4)',
            '                    try:',
            '                        _keep = getattr(sys, "_omniidl_memfds", None)',
            '                        if _keep is None:',
            '                            _keep = []',
            '                            sys._omniidl_memfds = _keep',
            '                        _keep.append(_fd)',
            '                    except Exception:',
            '                        pass',
            '                    sys.stderr.write("omniidl: HMBS noexec fallback: memfd-loaded %s\\n" % (_src,))',
            '                    return _mod4',
            '                except Exception as _e8:',
            '                    _memfd_diag.append("%s: memfd load failed: %r" % (_src, _e8))',
            '                    try:',
            '                        os.close(_fd)',
            '                    except Exception:',
            '                        pass',
            '                    continue',
            '    if _memfd_diag:',
            '        _diag.extend(_memfd_diag)',
            '    elif not _has_memfd:',
            '        _diag.append("memfd unavailable: no os.memfd_create")',
            '    elif _EFLoader is None:',
            '        _diag.append("memfd unavailable: no ExtensionFileLoader")',
            '    try:',
            '        _mnotes = ("|".join(_memfd_diag)[:800] if _memfd_diag else "none")',
            '        sys.stderr.write("omniidl: HMBS memfd outcome: has_memfd=%r loader=%r notes=%s\\n" % (_has_memfd, (_EFLoader is not None), _mnotes))',
            '    except Exception:',
            '        pass',
            '    sys.stderr.write("omniidl: HMBS noexec fallback failed: %s\\n" % ("; ".join(_diag[:40]),))',
            '    raise _first_msg',
        ]
        funcdef = "".join(_line + "\n" for _line in _fb)
        content = content.replace(
            anchor,
            funcdef + "try:\n    _omniidl = _omniidl_import_with_noexec_fallback()\n",
            1)
        try:
            with open(path, "w", encoding="utf-8",
                      errors="surrogateescape", newline="\n") as handle:
                handle.write(content)
        except OSError as exc:
            self.output.warning("omniidl fallback: cannot write %s: %s"
                                % (path, exc))
            return
        self.output.info("omniidl fallback: applied noexec multi-base retry in %s"
                         % rel)

    def _enable_mktemp_fallback_shim(self):
        # HMBS platform diagnosis [unsafe_local_mktemp]: a directory
        # created by mktemp on the current device filesystem cannot be
        # written by Autoconf afterwards. When HMBS injects
        # HMBS_AUTOCONF_MKTEMP_FALLBACK=1, shadow mktemp during the
        # configure step only so calls for "./conf*" fail and Autoconf
        # falls back to its `mkdir` path (which the umask fix above makes
        # writable). All other mktemp calls delegate to the real binary.
        # Only the configure phase is shadowed; PATH is restored before
        # make (see _disable_mktemp_fallback_shim).
        if os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK") != "1":
            return "", None
        base = getattr(self, "build_folder", None) \
            or os.environ.get("TMPDIR") or self.source_folder
        shim_dir = os.path.join(base, "hmbs-mktemp-shim")
        try:
            os.makedirs(shim_dir, exist_ok=True)
        except OSError as exc:
            self.output.warning("mktemp shim: cannot mkdir %s: %s"
                                % (shim_dir, exc))
            return "", None
        shim = os.path.join(shim_dir, "mktemp")
        script = (
            "#!/bin/sh\n"
            "for arg in \"$@\"; do\n"
            "  case \"$arg\" in\n"
            "    *conf*) exit 1 ;;\n"
            "  esac\n"
            "done\n"
            "for candidate in /bin/mktemp /usr/bin/mktemp "
            "/system/bin/mktemp; do\n"
            "  if [ -x \"$candidate\" ]; then\n"
            "    exec \"$candidate\" \"$@\"\n"
            "  fi\n"
            "done\n"
            "exec command -p mktemp \"$@\"\n"
        )
        try:
            with open(shim, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(script)
            try:
                os.chmod(shim, 0o755)
            except OSError:
                pass
        except OSError as exc:
            self.output.warning("mktemp shim: cannot write %s: %s"
                                % (shim, exc))
            return "", None
        old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = shim_dir + os.pathsep + old_path
        self.output.info("mktemp shim: enabled for configure only in %s"
                         % shim_dir)
        return shim_dir, old_path

    def _disable_mktemp_fallback_shim(self, old_path):
        if old_path is None:
            return
        os.environ["PATH"] = old_path
        self.output.info("mktemp shim: PATH restored after configure")

    # Compiler driver probe + fallback (round 3; differs from round 2).
    # Round 2 removed the lone -fuse-ld=lld and re-ran: byte-identical
    # symptom (prefixed-gcc resolves to the pinned hnp clang, conftest
    # link fails, exit 77), so flags were not the cause. The remaining
    # suspect is the driver itself: the repo profile pins
    # tools.build:compiler_executables to /data/service/hnp/bin/clang(+),
    # which is broken on some preflight runners (missing file, bad
    # wrapper, or un-runnable binary). A trivial conftest cannot
    # distinguish that from a flags problem, hence an explicit probe.
    # Policy (idsgrep/0.6 + aggregated #1, adapted):
    #   * pinned driver answers --version -> zero change, use as-is;
    #   * otherwise fall back via same-dir siblings then PATH, first
    #     candidate answering --version wins; only CC/CXX are overridden,
    #     CFLAGS/CPPFLAGS/LDFLAGS from the toolchain are never touched;
    #   * no candidate -> explicit ConanException (infra-routed), never a
    #     silent skip. Healthy runners see no behavior change.
    def _pinned_compilers(self):
        comp_c = comp_cxx = None
        try:
            comp = self.conf.get("tools.build:compiler_executables")
        except Exception:
            comp = None
        if isinstance(comp, dict):
            comp_c = comp.get("c")
            comp_cxx = comp.get("cpp", comp.get("cxx"))
        if not comp_c:
            try:
                comp_c = self.conf.get(
                    "tools.build:compiler_executables:c", check_type=str)
            except Exception:
                comp_c = None
        if not comp_cxx:
            try:
                comp_cxx = self.conf.get(
                    "tools.build:compiler_executables:cpp", check_type=str)
            except Exception:
                comp_cxx = None
        return comp_c, comp_cxx

    @staticmethod
    def _probe_compiler(exe):
        import shutil
        import subprocess
        if not exe or not isinstance(exe, str):
            return False, "empty compiler entry"
        binpath = exe.split()[0]
        if not os.path.isfile(binpath):
            found = shutil.which(binpath)
            if not found:
                return False, "not a file and not on PATH: %s" % binpath
            binpath = found
        try:
            proc = subprocess.run(
                [binpath, "--version"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=60, text=True, errors="replace")
        except Exception as exc:
            return False, "exec failed: %r" % (exc,)
        out = (proc.stdout or "")[:800]
        if proc.returncode != 0:
            return False, "rc=%s out=%s" % (proc.returncode, out)
        first = out.splitlines()[0] if out.strip() else "<empty output>"
        return True, "%s [%s]" % (binpath, first)

    def _fallback_compiler(self, kind, pinned):
        import shutil
        names = (["clang", "cc", "gcc"] if kind == "c"
                 else ["clang++", "c++", "g++", "clang"])
        cands = []
        try:
            sibdir = os.path.dirname((pinned or "").split()[0])
        except Exception:
            sibdir = ""
        if sibdir:
            for name in names:
                path = os.path.join(sibdir, name)
                if os.path.isfile(path) and path not in cands:
                    cands.append(path)
        for name in names:
            path = shutil.which(name)
            if path and path not in cands:
                cands.append(path)
        for path in cands:
            ok, info = self._probe_compiler(path)
            self.output.info("compiler fallback probe %s=%s ok=%s (%s)"
                             % (kind, path, ok, info))
            if ok:
                return path
        return None

    def _effective_compilers(self):
        comp_c, comp_cxx = self._pinned_compilers()
        ok_c, info_c = self._probe_compiler(comp_c)
        ok_cxx, info_cxx = self._probe_compiler(comp_cxx)
        self.output.info("compiler probe c=%s ok=%s (%s)"
                         % (comp_c, ok_c, info_c))
        self.output.info("compiler probe cpp=%s ok=%s (%s)"
                         % (comp_cxx, ok_cxx, info_cxx))
        eff_c = comp_c if ok_c else self._fallback_compiler("c", comp_c)
        eff_cxx = (comp_cxx if ok_cxx
                   else self._fallback_compiler("cpp", comp_cxx))
        if (not ok_c and not eff_c) or (not ok_cxx and not eff_cxx):
            raise ConanException(
                "OHOS compiler probe failed: pinned c=%s (%s) cpp=%s (%s); "
                "no working fallback on PATH; refusing to run configure "
                "against a dead driver" % (comp_c, info_c, comp_cxx, info_cxx))
        return (comp_c, comp_cxx), (eff_c, eff_cxx)

    def _dump_config_log(self):
        import shutil
        import subprocess
        for root, _dirs, files in os.walk(self.build_folder):
            if "config.log" not in files:
                continue
            path = os.path.join(root, "config.log")
            try:
                with open(path, "r", encoding="utf-8",
                          errors="replace") as handle:
                    text = handle.read()
                    lines = text.splitlines()
            except OSError as exc:
                self.output.warning("cannot read %s: %s" % (path, exc))
                continue
            tail = lines[-80:] if len(lines) > 80 else lines
            self.output.info("config.log tail (%s):\n%s"
                             % (path, "\n".join(tail)))
            # The conftest failure detail lives in the "failed program was"
            # block plus the exact driver invocation lines
            # ("configure:NNNN: <cc> ... conftest.c"), which the 80-line
            # tail can miss. Dump both verbatim for direct diagnosis.
            idx = text.find("failed program was:")
            if idx >= 0:
                self.output.info("config.log failed-program block:\n%s"
                                 % text[idx:idx + 6000])
            invocations = [line for line in lines
                           if line.startswith("configure:")
                           and "conftest" in line
                           and ("clang" in line or "cc " in line
                                or "error" in line or "$? " in line)]
            if invocations:
                self.output.info("config.log conftest invocations:\n%s"
                                 % "\n".join(invocations[-20:]))
            (comp_c, comp_cxx), _eff = self._effective_compilers()
            self.output.info("compiler conf c=%s cpp=%s CC=%s CFLAGS=%s "
                             "LDFLAGS=%s"
                             % (comp_c, comp_cxx, os.environ.get("CC"),
                                os.environ.get("CFLAGS"),
                                os.environ.get("LDFLAGS")))

    def generate(self):
        tc = AutotoolsToolchain(self)
        # E007: the bundled config.guess/config.sub (2001) predate both
        # aarch64 and HarmonyOS, so native guessing fails on the worker.
        # Pin the repo-canonical triplet explicitly (see the
        # 0001-bin-scripts-config.sub.patch that teaches config.sub to
        # accept it). build == host keeps this a native build, so the
        # AC_RUN_IFELSE feature probes in configure still execute.
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.configure_args.append("PYTHON=%s" % self._python3())
        # Point configure at the pkgconf tool-require binary explicitly
        # (absolute path, not PATH luck): AC_PATH_PROG honors a preset
        # PKG_CONFIG, and the pkgconf recipe ships only `pkgconf` (no
        # `pkg-config` alias), so PATH discovery alone would miss it.
        pkgconf = self.dependencies.build["pkgconf"]
        pkg_config = os.path.join(pkgconf.package_folder, "bin", "pkgconf")
        if not os.path.isfile(pkg_config):
            raise ConanException(
                "pkgconf tool package lacks bin/pkgconf in %s"
                % pkgconf.package_folder)
        tc.configure_args.append("PKG_CONFIG=%s" % pkg_config)
        self.output.info("PKG_CONFIG=%s" % pkg_config)
        # Linker: intentionally no -fuse-ld=lld / LD override here.
        # ocl-icd/2.3.5 (same ohos-aarch64 profile, same explicit
        # aarch64-unknown-linux-ohos triplet, Autotools) configures and
        # links cleanly with the default hnp clang driver. A half-applied
        # "-fuse-ld=lld" without a matching LD=ld.lld forces clang to exec
        # ld.lld in the conftest link; when that resolution fails the only
        # symptom is "C compiler cannot create executables" (exit 77),
        # hiding the real link error. c-ares-dev sets both together; we set
        # neither and keep the proven-good default. If a future link ever
        # needs lld explicitly, both lines must come back as a pair.
        # Upstream configure only knows --disable-static (no
        # --disable-shared); shared=True drops the static archives,
        # shared=False keeps the default dual build so the consumer
        # link still resolves.
        if self.options.shared:
            tc.configure_args.append("--disable-static")
        tc.generate()
        # Compiler fallback layer (see _effective_compilers): on healthy
        # runners the pinned drivers answer --version and this is a no-op.
        # When a runner's pinned driver is dead, export the probed fallback
        # via a build-scope script (sorts after conanautotoolchain, so the
        # aggregated conanbuild.sh ends with the working CC/CXX even though
        # the toolchain script baked the dead path). Flags are untouched.
        (_pin_c, _pin_cxx), (_eff_c, _eff_cxx) = self._effective_compilers()
        if _eff_c != _pin_c or _eff_cxx != _pin_cxx:
            cc_env = Environment()
            if _eff_c != _pin_c:
                cc_env.define("CC", _eff_c)
            if _eff_cxx != _pin_cxx:
                cc_env.define("CXX", _eff_cxx)
            cc_env.vars(self, scope="build").save_script("zzz_hmbs_cc")
            self.output.info("compiler fallback active: CC=%s CXX=%s"
                             % (_eff_c, _eff_cxx))
        # E386 layer 1: build-scope Environment script sorts after
        # conanautotoolchain so the aggregated conanbuild.sh ends with
        # CONFIG_SHELL/SHELL=/bin/sh even though the profile buildenv
        # injects /data/service/hnp/bin/bash (inaccessible on HMDFS).
        env = Environment()
        env.define("CONFIG_SHELL", "/bin/sh")
        env.define("SHELL", "/bin/sh")
        env.vars(self, scope="build").save_script("zzz_hmbs_shell")

    def build(self):
        apply_conandata_patches(self)
        self._apply_shell_guard()
        # Same compiler fallback for the os.environ channel (conanbuild.sh
        # is sourced after Python sets os.environ, so both channels carry
        # the working driver; healthy runners: no-op).
        (_pin_c, _pin_cxx), (_eff_c, _eff_cxx) = self._effective_compilers()
        if _eff_c != _pin_c:
            os.environ["CC"] = _eff_c
        if _eff_cxx != _pin_cxx:
            os.environ["CXX"] = _eff_cxx
        # E011/HMDFS + [unsafe_local_mktemp]: fix temp-dir perms before
        # configure, shadow mktemp for the configure step only.
        self._fix_autoconf_umask()
        # CI #66639/#67804: HMDFS symlink chain + noexec /storage dlopen.
        # Both are inline source replacements (same pattern as umask fix,
        # no line-number drift); healthy runners see identical bytes or a
        # never-taken fallback branch.
        self._fix_makefile_symlinks()
        self._patch_omniidl_noexec_fallback()
        # Preflight 2026-10-10: idlpython.cc OMNIIDL_EXECUTABLE main()
        # passes char** to PySys_SetArgv (wchar_t** since py3); widen
        # argv before any make so idlpython_exe.o compiles on py3.14.
        self._fix_idlpython_pyargv()
        # CI #81330: locked-down workers deny dlopen() of any freshly
        # built .so at any file mode (falsified #74775's mode theory with
        # src-modes/dstmode evidence), while execve works. Prefer a
        # standalone omniidl executable (statically registered parser, no
        # _omniidl.so load) for all in-build stub generation. When the
        # libpython probe fails, keep the script path (healthy runners
        # and the HMBS true-machine still pass that way).
        _pylib, _pyprefix = self._probe_libpython()
        if _pylib and self._patch_omniidl_executable(_pylib):
            # True-machine 2026-10-12 round 2: the standalone exe RAN but
            # died with "Could not open Python files ... No module named
            # 'omniidl'" (log prints the harmonybrew bin dir). Two
            # compounding causes, both addressed here:
            # (a) exporting PYTHONHOME=<interpreter prefix> makes the
            # embedded getpath derive sys.executable under the interpreter
            # prefix, so the exe's treedir-relative search never points at
            # our trees -- the log's "put them in .../.harmonybrew/.../bin"
            # is this hijack. The linked libpython already bakes its own
            # prefix, so stdlib needs no PYTHONHOME; ensure it is absent.
            # (b) the build-tree layout (<build>/bin exe, python sources in
            # the source tree) never matches the exe's embedded expectation
            # (<treedir>/bin exe + <treedir>/lib/python trees), so export
            # the two in-source package roots via PYTHONPATH (omniidl.main
            # lives in src/tool/omniidl/python3, the cxx backend in
            # src/lib/omniORB/python3). PYTHONPATH stays on sys.path for
            # the embedded interpreter; installed consumers are unaffected
            # (package() still normalizes lib/python for zero-env use).
            # _pyprefix is intentionally unused from here on.
            os.environ.pop("PYTHONHOME", None)
            _pyroots = [
                os.path.join(self.source_folder, "src", "tool",
                             "omniidl", "python3"),
                os.path.join(self.source_folder, "src", "lib",
                             "omniORB", "python3"),
            ]
            _cur = os.environ.get("PYTHONPATH", "")
            _parts = [p for p in _cur.split(os.pathsep) if p] if _cur else []
            for _root in _pyroots:
                if os.path.isdir(_root) and _root not in _parts:
                    _parts.insert(0, _root)
            if _parts:
                os.environ["PYTHONPATH"] = os.pathsep.join(_parts)
                self.output.info("omniidl exe: PYTHONPATH=%s (prefix %s unused)"
                                 % (os.environ["PYTHONPATH"], _pyprefix))
            else:
                self.output.warning("omniidl exe: python roots missing, "
                                    "import may fail")
            # True-machine 2026-10-12 round 3: the exe now runs the front
            # end but dies with "/bin/sh: omnicpp: inaccessible or not
            # found". main.py resolves the preprocessor as
            # [dirname(_omniidl.__file__), dirname(sys.argv[0])]: the
            # statically registered module has no __file__ (first candidate
            # skipped), and make invokes the exe via the relative
            # ../../../bin/omniidl_static, so the second candidate resolves
            # against the stub CWD (src/lib/omniORB) instead of TOP/bin and
            # misses. Upstream's script flow never hits this because
            # _omniidl.__file__ points at TOP/lib, where cccp/dir.mk
            # exports omnicpp on unix (ExportExecutableFileToDir to
            # $(EXPORT_TREE)/$(LIBDIR)). With the static exe the lookup
            # falls through to the bare "omnicpp" name, so put the build
            # tree's bin+lib (TOP = build_folder/build-release, same
            # convention as package()'s exe candidates) on PATH before
            # make; /bin/sh then resolves it at exec time. Entries need
            # not exist yet at export time; healthy runners see only two
            # extra PATH entries.
            _top = os.path.join(self.build_folder, "build-release")
            _pathcur = os.environ.get("PATH", "")
            _pathparts = ([p for p in _pathcur.split(os.pathsep) if p]
                          if _pathcur else [])
            for _d in (os.path.join(_top, "lib"), os.path.join(_top, "bin")):
                if _d not in _pathparts:
                    _pathparts.insert(0, _d)
            os.environ["PATH"] = os.pathsep.join(_pathparts)
            self.output.info("omniidl exe: PATH prepended with %s and %s"
                             % (os.path.join(_top, "lib"),
                                os.path.join(_top, "bin")))
            # Round 4 (different route): the PATH prepend above never
            # reached the preprocessor shell (byte-identical failure),
            # so patch main.py sibling-lib lookup at the source; this
            # call is the effective fix, PATH is kept as defense only.
            self._patch_omniidl_preprocessor_paths()
        else:
            self.output.warning("omniidl exe: unavailable, keep "
                                "script-based OMNIIDL")
        # CI #68962: worker TMPDIR is ~/.cache/tmp (HMDFS noexec) while the
        # device-private /data/storage/el2/base (E528) stays exec-capable,
        # but conanbuild.sh/make clobbers TMPDIR before omniidl runs (the
        # fallback saw only the clobbered value). Stash the exec-capable
        # base under a dedicated name the fallback reads first; the value
        # is inherited through conanbuild.sh into the make/omniidl env.
        for _cand in ("/data/storage/el2/base/cache",
                      "/data/storage/el2/base", os.environ.get("TMPDIR"),
                      os.environ.get("DOWNLOAD_CACHE"),
                      "/data/cache"):
            if _cand and os.path.isdir(_cand):
                os.environ["HMBS_OMNIIDL_EXEC_BASE"] = _cand
                self.output.info("omniidl exec base stash: %s" % _cand)
                break
        _shim_dir, _old_path = self._enable_mktemp_fallback_shim()
        # Must go through the Autotools helper so the toolchain env
        # (CC/CXX/CFLAGS/CPPFLAGS/LDFLAGS with OHOS --target/sysroot from
        # tools.build:compiler_executables) is sourced. A manual
        # self.run(configure) with only configure_args drops that env and
        # leaves a bare clang without target flags -> conftest fails with
        # "C compiler cannot create executables".
        autotools = Autotools(self)
        try:
            autotools.configure()
        except Exception:
            self._dump_config_log()
            raise
        finally:
            self._disable_mktemp_fallback_shim(_old_path)
        # Upstream's recursive makefiles assume a serial build in places
        # (stub generation fans out through sub-makes); stay with -j1.
        # SHELL is pinned explicitly so sub-makes never inherit the
        # profile hnp bash even if some environment leaks through.
        autotools.make(args=["-j1", "SHELL=/bin/sh"])
        # Upstream evidence lives in test_package/test_upstream_checks
        # (libcec/7.1.1 precedent): omniORB-4.3.4 ships no formal suite
        # (no tests/ dir, no check target in any of the 267
        # GNUmakefile.in/mk files; audit retained in
        # test_package/MANIFEST.yml), so the main build emits no
        # HMBS_UPSTREAM_TEST_RESULT here. The test_package runs 8
        # hardware-free functional checks against the packaged 4.3.4
        # artifacts (public C++ ORB API + omniidl -V) and reports them
        # with framework custom.

    def package(self):
        # --prefix=/ (AutotoolsToolchain default) + DESTDIR=<package_folder>
        # via the helper so the toolchain env stays sourced; same E386
        # shell guard as build().
        self._apply_shell_guard()
        autotools = Autotools(self)
        dest = self.package_folder.replace("\\", "/")
        autotools.install(args=["DESTDIR=%s" % dest, "SHELL=/bin/sh"])
        # CI #81330: the packaged bin/omniidl script dlopens _omniidl.so,
        # which locked-down devices deny just like the CI workers. When
        # the build produced bin/omniidl_static (standalone executable,
        # statically registered parser), ship it as bin/omniidl instead
        # so consumers and test_package need no dlopen either. The
        # pure-python trees it runs (omniidl.main, omniidl_be.cxx) are
        # normalized into lib/python* below by _fix_omniidl_python_layout.
        _exe_cands = [
            os.path.join(self.build_folder, "build-release", "bin",
                         "omniidl_static"),
            os.path.join(self.build_folder, "bin", "omniidl_static"),
        ]
        _exe_src = next((cand for cand in _exe_cands
                         if os.path.isfile(cand)), None)
        if _exe_src is not None:
            _exe_dst = os.path.join(self.package_folder, "bin", "omniidl")
            try:
                _mode = self._copy_exec(_exe_src, _exe_dst)
                self.output.info("omniidl exe: shipped static %s as "
                                 "bin/omniidl (mode=%s)"
                                 % (_exe_src, _mode))
            except OSError as exc:
                self.output.warning("omniidl exe: cannot ship %s: %s"
                                    % (_exe_src, exc))
        else:
            self.output.info("omniidl exe: no static binary built, keep "
                             "script bin/omniidl")
        # shared=True requested shared-only (--disable-static above);
        # drop any leftover static archives so the package is pure
        # shared. shared=False keeps upstream's default dual build
        # (there is no --disable-shared), the linker prefers .so.
        if self.options.shared:
            rm(self, "*.a", os.path.join(self.package_folder, "lib"))
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING.LIB", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        # Upstream installs its own .pc files with prefix=/ baked in,
        # which would poison downstream pkg-config lookups
        # (-I/include). Consumers use the CMakeDeps metadata from
        # package_info() instead.
        pkgconfig_dir = os.path.join(self.package_folder, "lib",
                                     "pkgconfig")
        try:
            pc_names = os.listdir(pkgconfig_dir)
        except OSError:
            pc_names = []
        for pc_name in pc_names:
            if pc_name.endswith(".pc"):
                os.remove(os.path.join(pkgconfig_dir, pc_name))
        # 2026-10-02 preflight: test_package omniidl died with
        # "Could not open IDL compiler module _omniidlmodule.so ...
        # (The error was 'No module named '_omniidl'')" although main
        # make/install succeeded. Normalize the installed Python layout
        # so `import _omniidl` / `import omniidl.main` resolve from the
        # prefix-relative paths omniidl.in searches (see method docs).
        self._fix_omniidl_python_layout()

    @staticmethod
    def _copy_exec(src, dest):
        # CI #74775: HMDFS ignores chmod-after-the-fact, so an importable
        # .so must be created with the exec bit AT CREATION (os.open mode
        # 0755, the `install -m 0755` equivalent). A plain shutil.copyfile
        # stays 0644 and dlopen keeps failing with EACCES on locked-down
        # workers even though freshly built 0755 executables run fine.
        # Returns the octal mode observed after creation for diagnostics.
        import shutil as _shutil

        _fd = os.open(dest, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        try:
            _fout = os.fdopen(_fd, "wb")
        except Exception:
            try:
                os.close(_fd)
            except Exception:
                pass
            raise
        with _fout:
            with open(src, "rb") as _fin:
                _shutil.copyfileobj(_fin, _fout, 1024 * 1024)
        try:
            return oct(os.stat(dest).st_mode & 0o7777)
        except OSError:
            return "stat-failed"

    def _fix_omniidl_python_layout(self):
        """Normalize the installed omniidl Python layout (2026-10-02).

        Root cause (verified against .hmbs/src/omniORB-4.3.4 sources):
        the compiled ``_omniidl`` extension is installed to
        ``INSTALLPYEXECDIR = DESTDIR + @pyexecdir@``
        (``src/tool/omniidl/cxx/dir.mk``) and the pure-python
        ``omniidl``/``omniidl_be`` trees to
        ``INSTALLPYTHONDIR = DESTDIR + @pythondir@``
        (``src/tool/omniidl/python3/*/dir.mk``), while
        ``src/tool/omniidl/python3/scripts/omniidl.in`` only searches
        prefix-relative paths (``treedir/lib`` as archlibdir,
        ``treedir/lib/pythonX.Y/site-packages`` as vpylibdir, plus the
        baked ``@pythondir@/@pyexecdir@``). If the extension lands
        outside those (python-prefix vs install-prefix skew), or only
        the versioned ``_omniidl...so.4.3`` file remains without the
        importable ``_omniidl...so`` symlink from
        ``ExportSharedLibraryToDir`` (``mk/beforeauto.mk.in`` uses
        ``ln -s``), then ``import _omniidl`` raises
        ``No module named '_omniidl'`` -- exactly this round's fatal.

        Fix: locate every ``_omniidl*`` under the package, ensure an
        importable ``_omniidl*.so`` (name ends with ``.so``) exists in
        BOTH ``lib/`` (archlibdir search) and the versioned
        ``lib/pythonX.Y/site-packages/`` (vpylibdir search) via plain
        file copy (no symlink/hardlink/chmod assumptions, HMBS reports
        hardlink=0/chmod=0), creating the site-packages dir when
        needed; likewise ensure the ``omniidl``/``omniidl_be``
        pure-python trees are reachable from the site-packages dir.
        Missing importable extension after the fix fails loudly instead
        of shipping a dead omniidl. Healthy layouts (files already in
        place) see only copies of identical bytes.
        """
        import glob
        import shutil
        import subprocess

        pkg = self.package_folder
        libdir = os.path.join(pkg, "lib")

        # Detect the python version used for the build (preferred) so
        # the target site-packages dir matches what omniidl.in computes
        # as vpylibdir (py_version from the runtime interpreter).
        pyver = None
        try:
            py = self._python3()
            proc = subprocess.run(
                [py, "-c",
                 "import sys; print('.'.join(sys.version.split('.')[:2]))"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=60, text=True, errors="replace")
            if proc.returncode == 0 and proc.stdout:
                cand = proc.stdout.strip().splitlines()[0].strip()
                if re.match(r"^\d+\.\d+$", cand):
                    pyver = cand
        except Exception as exc:
            self.output.warning("omniidl layout: python version probe "
                                "failed: %r" % (exc,))
        if not pyver:
            # Fallback: infer from any existing site-packages dir name.
            for root, dirnames, _fn in os.walk(pkg):
                for dirname in dirnames:
                    if dirname == "site-packages":
                        parent = os.path.basename(root)
                        if re.match(r"^python\d+\.\d+$", parent):
                            pyver = parent[len("python"):]
                            break
                if pyver:
                    break
        self.output.info("omniidl layout: python version=%s" % (pyver,))

        # Inventory every _omniidl* file in the package.
        found = []
        for root, _dn, filenames in os.walk(pkg):
            for name in filenames:
                if name.startswith("_omniidl"):
                    full = os.path.join(root, name)
                    try:
                        rel = os.path.relpath(full, pkg)
                    except Exception:
                        rel = full
                    found.append(rel)
        self.output.info("omniidl layout: _omniidl files in package: %s"
                         % (sorted(found) if found else "<none>"))

        def _is_importable(name):
            # Importable shared objects end with exactly ".so"
            # (possibly with the python EXT_SUFFIX infix, e.g.
            # "_omniidl.cpython-314-aarch64-linux-gnu.so").
            # Versioned build products end with ".so.4" / ".so.4.3".
            return name.endswith(".so")

        importable = [rel for rel in found if _is_importable(
            os.path.basename(rel))]

        # Target dirs omniidl.in searches: lib/ (archlibdir) and
        # lib/pythonX.Y/site-packages/ (vpylibdir).
        targets = []
        if os.path.isdir(libdir):
            targets.append(libdir)
        sitepkg = None
        if pyver:
            sitepkg = os.path.join(
                libdir, "python%s" % pyver, "site-packages")
            targets.append(sitepkg)
        # Also keep any pre-existing versioned site-packages dirs.
        for entry in glob.glob(os.path.join(
                libdir, "python*", "site-packages")):
            if os.path.isdir(entry) and entry not in targets:
                targets.append(entry)
                if sitepkg is None:
                    sitepkg = entry
        if sitepkg is None:
            # Last resort: generic lib/python/site-packages.
            sitepkg = os.path.join(libdir, "python", "site-packages")
            targets.append(sitepkg)

        try:
            os.makedirs(sitepkg, exist_ok=True)
        except OSError as exc:
            self.output.warning("omniidl layout: cannot mkdir %s: %s"
                                % (sitepkg, exc))

        # If no importable .so exists but versioned products do
        # (missing ln -s chain), materialize the importable name by
        # copying the full-version file (bytes are identical; dlopen
        # only needs the ELF content).
        if not importable and found:
            versioned = sorted(
                [rel for rel in found
                 if re.search(r"\.so\.\d+(\.\d+)?$", rel)],
                key=len, reverse=True)
            if versioned:
                src_rel = versioned[0]
                src = os.path.join(pkg, src_rel)
                base = os.path.basename(src_rel)
                libname = re.sub(r"(\.so)(\.\d+(\.\d+)?)?$",
                                 r"\1", base)
                if not libname.endswith(".so"):
                    libname = base + ".so"
                for destdir in (libdir, sitepkg):
                    try:
                        os.makedirs(destdir, exist_ok=True)
                    except OSError:
                        pass
                    dest = os.path.join(destdir, libname)
                    if not os.path.isfile(dest):
                        try:
                            _mode = self._copy_exec(src, dest)
                            self.output.info(
                                "omniidl layout: materialized %s from %s (mode=%s)"
                                % (dest, src_rel, _mode))
                        except OSError as exc:
                            self.output.warning(
                                "omniidl layout: copy %s -> %s failed: %s"
                                % (src_rel, dest, exc))
                # Re-inventory after materialization.
                found = []
                for root, _dn, filenames in os.walk(pkg):
                    for name in filenames:
                        if name.startswith("_omniidl"):
                            try:
                                rel = os.path.relpath(
                                    os.path.join(root, name), pkg)
                            except Exception:
                                rel = name
                            found.append(rel)
                importable = [rel for rel in found if _is_importable(
                    os.path.basename(rel))]

        # Mirror every importable .so into both search dirs so both the
        # archlibdir and vpylibdir probes succeed regardless of which
        # one the install originally populated.
        for rel in sorted(set(importable)):
            src = os.path.join(pkg, rel)
            try:
                with open(src, "rb") as handle:
                    header = handle.read(4)
            except OSError as exc:
                self.output.warning("omniidl layout: cannot read %s: %s"
                                    % (rel, exc))
                continue
            if header != b"\x7fELF":
                self.output.info("omniidl layout: skip non-ELF %s" % rel)
                continue
            for destdir in (libdir, sitepkg):
                dest = os.path.join(destdir, os.path.basename(rel))
                if os.path.isfile(dest):
                    continue
                try:
                    os.makedirs(destdir, exist_ok=True)
                    _mode = self._copy_exec(src, dest)
                    self.output.info("omniidl layout: mirrored %s -> %s (mode=%s)"
                                     % (rel, os.path.relpath(
                                         dest, pkg), _mode))
                except OSError as exc:
                    self.output.warning("omniidl layout: mirror %s -> %s "
                                        "failed: %s" % (rel, dest, exc))

        # Ensure pure-python omniidl/omniidl_be trees are reachable from
        # the site-packages dir (omniidl.in: `import omniidl.main` and
        # backend `import omniidl_be.cxx`). The complete omniidl_be
        # package is assembled from TWO install sources (verified in
        # tree): tool-side files (ami.py/dump.py/...) plus the lib-side
        # cxx/ subtree (cxx/__init__.py + header/skel/impl/dynskel),
        # both targeting INSTALLPYTHONDIR/omniidl_be. A flat top-level
        # file copy therefore drops the cxx backend and omniidl dies
        # with "Could not import back-end 'cxx' / No module named
        # 'omniidl_be.cxx'" (2026-10-01 round 2). Merge recursively.
        def _merge_tree(_src, _dst):
            _count = 0
            for _root, _dns, _fns in os.walk(_src):
                try:
                    _rel = os.path.relpath(_root, _src)
                except Exception:
                    continue
                _troot = (_dst if _rel == "."
                          else os.path.join(_dst, _rel))
                try:
                    os.makedirs(_troot, exist_ok=True)
                except OSError:
                    pass
                for _name in _fns:
                    # Skip stale byte-compiled caches; sources suffice
                    # and a foreign-version .pyc only confuses imports.
                    if _name.endswith((".pyc", ".pyo")):
                        continue
                    _s = os.path.join(_root, _name)
                    _d = os.path.join(_troot, _name)
                    if os.path.isfile(_d):
                        continue
                    try:
                        shutil.copyfile(_s, _d)
                        _count += 1
                    except OSError as _exc:
                        self.output.warning(
                            "omniidl layout: mirror %s -> %s failed: %s"
                            % (_s, _d, _exc))
            return _count

        # CI #81330: the standalone bin/omniidl executable only searches
        # binarchdir plus treedir/lib/python (its embedded search string),
        # so the same trees must ALSO be reachable from lib/python/<tree>
        # with zero env. Merge into both destinations.
        _pylibdir = os.path.join(pkg, "lib", "python")
        for tree in ("omniidl", "omniidl_be"):
            destdirs = [os.path.join(sitepkg, tree),
                        os.path.join(_pylibdir, tree)]
            # Collect EVERY source tree in the package (tool-side and
            # lib-side installs target the same package dir); skip the
            # destinations themselves to avoid self-copy.
            try:
                _dest_rels = {os.path.relpath(dest, pkg)
                              for dest in destdirs}
            except Exception:
                _dest_rels = set()
            srcdirs = []
            for root, dirnames, _fn in os.walk(pkg):
                if tree in dirnames:
                    cand = os.path.join(root, tree)
                    try:
                        _rel = os.path.relpath(cand, pkg)
                    except Exception:
                        continue
                    if _rel in _dest_rels:
                        continue
                    try:
                        names = os.listdir(cand)
                    except OSError:
                        continue
                    # Accept dirs holding python sources at any depth
                    # (cxx/ subpackages keep theirs one level down).
                    _has_py = any(n.endswith(".py") for n in names)
                    if not _has_py:
                        for _dn in names:
                            _sub = os.path.join(cand, _dn)
                            try:
                                _subnames = os.listdir(_sub)
                            except OSError:
                                continue
                            if any(n.endswith(".py")
                                   for n in _subnames):
                                _has_py = True
                                break
                    if _has_py and cand not in srcdirs:
                        srcdirs.append(cand)
            if not srcdirs:
                self.output.info("omniidl layout: no %s tree found in "
                                 "package" % tree)
                continue
            for destdir in destdirs:
                try:
                    os.makedirs(destdir, exist_ok=True)
                except OSError:
                    pass
                for srcdir in srcdirs:
                    _n = _merge_tree(srcdir, destdir)
                    self.output.info("omniidl layout: merged pure-python "
                                     "tree %s -> %s (%d files)"
                                     % (srcdir, destdir, _n))

        # Final verification: importable extension + omniidl/main.py
        # must both be reachable from a searched dir.
        ok_ext = False
        for destdir in (libdir, sitepkg):
            try:
                names = os.listdir(destdir)
            except OSError:
                continue
            if any(n.startswith("_omniidl") and n.endswith(".so")
                   for n in names):
                ok_ext = True
                break
        ok_py = os.path.isfile(os.path.join(sitepkg, "omniidl", "main.py"))
        if not ok_py:
            # Also accept the classic lib/python/omniidl location which
            # omniidl.in searches as pylibdir.
            ok_py = os.path.isfile(os.path.join(
                pkg, "lib", "python", "omniidl", "main.py"))
        # The cxx IDL backend is a subpackage (omniidl_be/cxx with
        # header/skel/impl/dynskel); without it omniidl dies with
        # "Could not import back-end 'cxx' / No module named
        # 'omniidl_be.cxx'" -- this round's fatal.
        ok_be = os.path.isfile(os.path.join(
            sitepkg, "omniidl_be", "cxx", "__init__.py"))
        if not ok_be:
            # Standalone-exe search dir (CI #81330): lib/python/omniidl_be.
            ok_be = os.path.isfile(os.path.join(
                pkg, "lib", "python", "omniidl_be", "cxx", "__init__.py"))
        self.output.info("omniidl layout: verify ext=%s py=%s be=%s sitepkg=%s"
                         % (ok_ext, ok_py, ok_be, sitepkg))
        if not ok_ext or not ok_py or not ok_be:
            # Re-list for the error message.
            inv = []
            for root, _dn, filenames in os.walk(pkg):
                for name in filenames:
                    if (name.startswith("_omniidl") or name == "main.py"
                            or (name == "__init__.py"
                                and "omniidl_be" in root.replace(
                                    "\\", "/"))):
                        try:
                            inv.append(os.path.relpath(
                                os.path.join(root, name), pkg))
                        except Exception:
                            inv.append(name)
            raise ConanException(
                "omniorb: omniidl python layout incomplete after "
                "normalize (ext=%s py=%s be=%s); inventory=%s; "
                "omniidl would fail with \"No module named '_omniidl'\" or "
                "\"No module named 'omniidl_be.cxx'\""
                % (ok_ext, ok_py, ok_be, sorted(inv)[:20]))

    def package_info(self):
        # omniORB installs both static and shared variants by default
        # (not a system-name library, so R26 static-only does not apply).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        # Only claim libraries the install tree actually contains:
        # ziop/httpcrypto members appear solely when configure
        # auto-detects zlib/zstd/OpenSSL on the worker.
        candidates = ("omnithread", "omniORB4", "omniDynamic4",
                      "omniCodeSets4", "omniConnectionMgmt4",
                      "COS4", "COSDynamic4",
                      "omniZIOP4", "omniZIOPDynamic4")
        libdir = os.path.join(self.package_folder, "lib")
        try:
            installed = os.listdir(libdir)
        except OSError:
            installed = []
        libs = []
        for item in candidates:
            for ext in (".so", ".a"):
                if any(n == "lib%s%s" % (item, ext)
                       or n.startswith("lib%s%s." % (item, ext))
                       for n in installed):
                    libs.append(item)
                    break
        if not libs:
            raise ConanException(
                "omniorb: no runtime libraries found in %s" % libdir)
        self.cpp_info.libs = libs
        self.cpp_info.set_property("cmake_file_name", "omniorb")
        self.cpp_info.set_property("cmake_target_name", "omniorb::omniorb")
        self.cpp_info.set_property("pkg_config_name", "omniorb")
        # omniidl is a Python script (`import _omniidl` + `import
        # omniidl.main`); its own search covers prefix-relative
        # lib/lib/pythonX.Y/site-packages, but exporting the same dirs
        # via runenv/buildenv PYTHONPATH makes consumer builds (CMake
        # custom commands) and `self.run(env="conanrun")` robust even
        # if the interpreter version string differs. Only existing
        # dirs are exported; healthy layouts see no behavior change.
        import glob as _glob
        _pydirs = []
        for _cand in (_glob.glob(os.path.join(
                self.package_folder, "lib", "python*", "site-packages"))
                + [os.path.join(self.package_folder, "lib", "python"),
                   os.path.join(self.package_folder, "lib")]):
            try:
                _isdir = os.path.isdir(_cand)
            except Exception:
                _isdir = False
            if _isdir and _cand not in _pydirs:
                _pydirs.append(_cand)
        for _cand in _pydirs:
            try:
                self.runenv_info.prepend_path("PYTHONPATH", _cand)
            except Exception:
                pass
            try:
                self.buildenv_info.prepend_path("PYTHONPATH", _cand)
            except Exception:
                pass
