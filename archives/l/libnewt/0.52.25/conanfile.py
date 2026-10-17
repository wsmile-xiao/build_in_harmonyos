#!/usr/bin/env python3
"""Conan recipe — libnewt 0.52.25 (configure + Makefile)

Newt (Not Erik's Windowing Toolkit) is a C library for color text-mode,
widget-based user interfaces, built on S-Lang. The same source tree also
builds the whiptail dialog utility (popt-based) and interactive demo
programs. Upstream ships no automated test suite.
"""
import glob
import os
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibnewtConan(ConanFile):
    name = "libnewt"
    version = "0.52.25"
    description = "Not Erik's Windowing Toolkit - text mode windowing with slang"
    license = "LGPL-2.0-only"
    homepage = "https://pagure.io/newt"
    url = "https://pagure.io/newt"

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

    def validate(self):
        # R32: accept both Linux and OHOS
        if hasattr(self, "settings") and self.settings.os not in (None, "Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # R27-style plain refs (no channel); transitive libs propagate
        # -lslang/-lpopt to consumers (whiptail needs popt, lib needs slang).
        self.requires("slang/2.3.3", transitive_headers=True, transitive_libs=True)
        self.requires("popt/1.16", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _writable_tmpdir(self):
        # HMBS readonly_tmp (/tmp is erofs read-only): prefer the HMBS-injected
        # writable TMPDIR/TMP/TEMP, verify it is actually writable, else fall
        # back to a private tmp dir under the build folder (pattern: c-client).
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            d = os.environ.get(var)
            if d and os.path.isdir(d):
                try:
                    fd, p = tempfile.mkstemp(dir=d)
                    os.close(fd)
                    os.unlink(p)
                    return d
                except Exception:
                    continue
        d = os.path.join(self.build_folder, "tmp")
        os.makedirs(d, exist_ok=True)
        return d

    def generate(self):
        tc = AutotoolsToolchain(self)
        # E001: clang on OHOS needs --target to find CRT files and produce
        # executables, else configure dies with "C compiler cannot create
        # executables" (proven pattern: slang/2.3.3 in this repo).
        if self.settings.os == "OHOS":
            tc.extra_cflags.append("--target=aarch64-unknown-linux-ohos")
            tc.extra_cxxflags.append("--target=aarch64-unknown-linux-ohos")
            tc.extra_ldflags.append("--target=aarch64-unknown-linux-ohos")
        # --without-python: no python dev headers on OHOS; prevents _snack build
        # --without-tcl: no tclConfig.sh on OHOS; skips whiptcl.so
        # --disable-nls: no libintl on OHOS; avoids AC_MSG_FAILURE in configure
        tc.configure_args.extend(["--without-python", "--without-tcl", "--disable-nls"])
        # newt's configure probes slang.h/popt.h via plain header checks and
        # links with LIBS=-lslang / -lpopt, so expose the Conan dep paths.
        # Only existing dirs: a stale -I/-L must never break the compiler
        # sanity check (conftest links nothing but the trivial main).
        for dep in self.dependencies.values():
            for include_dir in dep.cpp_info.includedirs:
                if include_dir and os.path.isdir(include_dir):
                    tc.extra_cflags.append(f"-I{include_dir}")
            for lib_dir in dep.cpp_info.libdirs:
                if lib_dir and os.path.isdir(lib_dir):
                    tc.extra_ldflags.append(f"-L{lib_dir}")
        # fPIC: static with PIC so it can link into shared consumers.
        if self.options.get_safe("fPIC"):
            tc.extra_cflags.append("-fPIC")
        tc.generate()

        # HMBS buildenv SHELL/CONFIG_SHELL may point at HNP bash whose getcwd()
        # fails on HMFS/HMDFS dirs; force system /bin/sh (pattern: most 5.2.0).
        # HMBS readonly_tmp: /tmp is erofs read-only, so export the writable
        # TMPDIR/TMP/TEMP (injected by HMBS, verified above) into the buildenv
        # so autoconf/configure/clang temp files avoid /tmp (pattern: c-client).
        tmp = self._writable_tmpdir()
        env = Environment()
        env.define("TMPDIR", tmp)
        env.define("TMP", tmp)
        env.define("TEMP", tmp)
        env.define_path("SHELL", "/bin/sh")
        env.define_path("CONFIG_SHELL", "/bin/sh")
        for _k in ("HMBS_AUTOCONF_MKTEMP_FALLBACK", "HMBS_CAP_LOCAL_MKTEMP",
                   "HMBS_TMPDIR", "HMBS_CAP_HARDLINK", "HMBS_CAP_CHMOD",
                   "HMBS_CAP_SYMLINK", "HMBS_INSTALL"):
            _v = os.environ.get(_k)
            if _v:
                env.define(_k, _v)
        env.vars(self, scope="build").save_script("conanfixenv")

    def build(self):
        # E420: make sure child processes start from a valid cwd.
        os.chdir(self.build_folder)
        # HMBS readonly_tmp: export writable tmp for this process and all
        # children (configure compiler checks, clang temp files, mktemp).
        tmp = self._writable_tmpdir()
        os.makedirs(tmp, exist_ok=True)
        for k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[k] = tmp
        os.environ["SHELL"] = "/bin/sh"
        os.environ["CONFIG_SHELL"] = "/bin/sh"
        # CC may be unrunnable from the conan build domain (cassbeam
        # precedent); resolve a proven executable, keep toolchain verbatim
        # when it runs. Exported via os.environ now and re-exported at the
        # end of conanbuild.sh by _fix_conanbuild_shell (wins over toolchain).
        os.environ["CC"] = self._resolve_cc()
        # newt's Makefile.in has no VPATH support (relative sources such as
        # newt.c, newt.0.52.ver and the shared/ obj dir), so build in-tree on
        # a copy of the sources inside the build folder.
        self._sync_sources_intree()
        # E011: autoconf boilerplate "umask 077" breaks config.status writes
        # on HMDFS; use 022 (pattern: most 5.2.0).
        self._fix_umask()
        # OHOS has no standalone install(1); provide the used subset.
        self._ensure_install_shim()
        # conanbuild.sh sources the HMBS buildenv AFTER conanfixenv,
        # overriding SHELL; re-append our overrides last (pattern: most 5.2.0).
        self._fix_conanbuild_shell()
        apply_conandata_patches(self)
        autotools = Autotools(self)
        try:
            autotools.configure(build_script_folder=self.build_folder)
        except Exception:
            # Never fail blind a 4th time: leave the real linker error in
            # the preflight log for the next round, then re-raise.
            self._dump_config_log()
            raise
        # GNU_LD=<non-empty> selects the -soname/--version-script branch so
        # libnewt.so carries a DT_SONAME (L5a gate). OHOS clang/lld supports
        # both flags; configure leaves GNU_LD empty because `ld -v` does not
        # report "GNU ld". SHELL/TMPDIR passed explicitly so make children
        # never fall back to read-only /tmp (readonly_tmp).
        autotools.make(args=["-j1", "GNU_LD=ld", "SHELL=/bin/sh",
                             f"TMPDIR={tmp}", f"TMP={tmp}", f"TEMP={tmp}"])

    def package(self):
        os.chdir(self.build_folder)
        install_bin = self._resolve_install()
        mkdir_p = self._ensure_mkinstalldirs()
        # NOTE: every VAR=value below must be a single shell token (no
        # spaces). A value with a space (e.g. "INSTALL=/x -c" or
        # "MKINSTALLDIRS=mkdir -p") is split by make into a stray flag
        # (-c/-p), which makes GNU make print usage and exit 2 — exactly
        # the previous round's failure. The shim/toybox needs no -c flag.
        tmp = os.environ.get("TMPDIR", "") or self._writable_tmpdir()
        autotools = Autotools(self)
        # Installs libnewt.a + libnewt.so.* + newt.h + libnewt.pc plus the
        # whiptail binary, man page and po files (install depends install-sh).
        # OHOS has no /usr/bin/install: top Makefile uses bare `install`
        # (covered by PATH in _resolve_install) while the static po/Makefile
        # hardcodes `/usr/bin/install -c` (PATH cannot fix it), so override
        # every INSTALL* variable explicitly (etsh/5.4.0 precedent:
        # INSTALL=/system/bin/install). INSTALL_NLS= forces empty so `make
        # install` never recurses into po/ when --disable-nls is active,
        # even if configure left INSTALL_NLS=install-nls behind.
        autotools.install(args=["-j1", "INSTALL_NLS=",
                                f"INSTALL={install_bin}",
                                f"INSTALL_PROGRAM={install_bin}",
                                f"INSTALL_DATA={install_bin}",
                                f"INSTALL_SCRIPT={install_bin}",
                                f"MKINSTALLDIRS={mkdir_p}",
                                "SHELL=/bin/sh",
                                f"TMPDIR={tmp}", f"TMP={tmp}", f"TEMP={tmp}"])
        # Static package ships a dynamically-linked whiptail by default
        # (DT_NEEDED libnewt.so.0.52), which breaks once the .so files are
        # removed. Relink the installed whiptail against the static
        # libnewt.a so `whiptail --version` works without any .so.
        # Relink BEFORE stripping the .so files; only strip when the
        # static relink succeeded so a failed relink keeps a working
        # dynamic binary instead of a broken package.
        relink_ok = True
        if not self.options.shared:
            relink_ok = self._relink_whiptail_static()
        # Make `shared` functional: upstream always installs both .a and
        # .so.*; keep only the selected linkage (Conan convention).
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            if self.options.shared:
                for f in glob.glob(os.path.join(libdir, "*.a")):
                    os.remove(f)
            elif relink_ok:
                for pat in ("*.so", "*.so.*"):
                    for f in glob.glob(os.path.join(libdir, pat)):
                        if os.path.islink(f) or os.path.isfile(f):
                            try:
                                os.remove(f)
                            except FileNotFoundError:
                                pass

    def package_info(self):
        self.cpp_info.libs = ["newt"]
        # whiptail ships in bin/ (library package with a helper tool,
        # same shape as slang shipping slsh without commands.json).
        self.cpp_info.bindirs = ["bin"]

    # ── helpers ────────────────────────────────────────────────

    def _sync_sources_intree(self):
        src = os.path.abspath(self.source_folder)
        dst = os.path.abspath(self.build_folder)
        if src == dst:
            return
        for item in sorted(os.listdir(src)):
            s = os.path.join(src, item)
            d = os.path.join(dst, item)
            if os.path.isdir(s) and not os.path.islink(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)

    def _fix_umask(self):
        # Byte-level replace: never decode/re-encode the whole script, so no
        # non-UTF8 byte or line ending elsewhere in configure can be altered.
        conf = os.path.join(self.build_folder, "configure")
        if not os.path.isfile(conf):
            return
        with open(conf, "rb") as f:
            content = f.read()
        if b"umask 077" in content:
            content = content.replace(b"umask 077", b"umask 022")
            with open(conf, "wb") as f:
                f.write(content)

    def _cand_works(self, prog):
        """True if prog can actually run --version (proven executable)."""
        if not prog:
            return False
        prog = prog.strip().split()[0].strip("\"'")
        if not prog:
            return False
        try:
            r = subprocess.run([prog, "--version"], stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, timeout=30)
            return r.returncode == 0
        except Exception:
            return False

    def _resolve_cc(self):
        """Resolve a runnable CC, preferring the toolchain value verbatim.

        Same-image precedent (cassbeam/1.1): /data/service/hnp/bin/clang can
        be 'inaccessible or not found' from the conan build domain, which
        surfaces as 'C compiler cannot create executables'. Probe it; only
        fall back when it is actually unrunnable. Always ensure --target is
        present so the flag survives even if configure clobbers CFLAGS.
        """
        try:
            exes = self.conf.get("tools.build:compiler_executables",
                                 check_type=dict)
        except Exception:
            try:
                exes = self.conf.get("tools.build:compiler_executables",
                                     default={}, check_type=dict)
            except Exception:
                exes = None
        conf_c = (exes.get("c") if isinstance(exes, dict) else None)
        conf_c = (conf_c or os.environ.get("CC") or
                  "/data/service/hnp/bin/clang").strip()
        prog = conf_c.split()[0].strip("\"'") if conf_c else ""
        if prog and self._cand_works(prog):
            base = conf_c
            self.output.info(f"HMBS: toolchain CC works verbatim: {base}")
        else:
            self.output.warning(
                f"HMBS: toolchain CC unrunnable: {conf_c!r}; searching fallback")
            base = ""
            for cand in ("clang", "/data/service/hnp/bin/clang",
                         "cc", "gcc"):
                p = cand.split()[0]
                if self._cand_works(p):
                    base = (shutil.which(p) if "/" not in p else p) or p
                    self.output.warning(f"HMBS: CC fallback in use: {base}")
                    break
            if not base:
                base = conf_c or "/data/service/hnp/bin/clang"
                self.output.warning(
                    f"HMBS: no working CC found; keeping {base}")
        if "--target=" not in base:
            base += " --target=aarch64-unknown-linux-ohos"
        return base

    def _dump_config_log(self):
        """Print config.log tail so the next round has ground truth."""
        for d in (self.build_folder, self.source_folder):
            p = os.path.join(d, "config.log")
            if not os.path.isfile(p):
                continue
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.read().splitlines()
                tail = "\n".join(lines[-80:])
                print(f"HMBS config.log tail ({p}):\n{tail}", flush=True)
                self.output.info(f"dumped config.log tail from {p}")
            except Exception as exc:
                self.output.warning(f"could not dump {p}: {exc}")
            return

    def _ensure_install_shim(self):
        """Create .hmbs-bin/install shim; return its absolute path.

        OHOS lacks standalone install(1): top-level newt Makefile calls
        bare `install`, while the static po/Makefile hardcodes
        `/usr/bin/install -c` (not generated by configure, so PATH alone
        cannot fix it). The shim supports the used subset: -c/-p/-s (noop),
        -m MODE, -o/-g (ignored), -D (mkdir -p parent), -d (mkdir -p dirs),
        -t DIR, single or multi-source `install src... dst` file copy.
        Directories via mkdir -p. chmod is best-effort (|| true) because
        the preflight FS reports HMBS_CAP_CHMOD=0 (chmod unsupported).
        """
        shim_dir = os.path.join(self.build_folder, ".hmbs-bin")
        os.makedirs(shim_dir, exist_ok=True)
        shim = os.path.join(shim_dir, "install")
        with open(shim, "w", encoding="utf-8", newline="\n") as f:
            f.write(
                "#!/bin/sh\n"
                "# minimal install(1) for newt top Makefile + gettext po Makefile\n"
                "# supports: -c/-p/-s noop, -m MODE, -o/-g ignored, -D, -d, -t DIR,\n"
                "# single or multi-source copy install src... dst; chmod best-effort\n"
                "mode=\n"
                "dodir=0\n"
                "mkparent=0\n"
                "target_dir=\n"
                "while [ $# -gt 0 ]; do\n"
                '  case "$1" in\n'
                "    -c|-p|-s) shift ;;\n"
                "    -m) mode=$2; shift 2 ;;\n"
                "    -m*) mode=${1#-m}; shift ;;\n"
                "    -o|-g) shift 2 ;;\n"
                "    -o*|-g*) shift ;;\n"
                "    -D) mkparent=1; shift ;;\n"
                "    -d) dodir=1; shift ;;\n"
                "    -t) target_dir=$2; shift 2 ;;\n"
                "    -T) shift ;;\n"
                "    --) shift; break ;;\n"
                "    -*) shift ;;\n"
                "    *) break ;;\n"
                "  esac\n"
                "done\n"
                'if [ "$dodir" = "1" ]; then\n'
                '  for d in "$@"; do mkdir -p "$d" || exit $?; done\n'
                "  exit 0\n"
                "fi\n"
                'if [ -n "$target_dir" ]; then\n'
                '  mkdir -p "$target_dir" || exit $?\n'
                '  for src in "$@"; do\n'
                '    base=${src##*/}\n'
                '    cp "$src" "$target_dir/$base" || exit $?\n'
                '    [ -z "$mode" ] || chmod "$mode" "$target_dir/$base" || true\n'
                "  done\n"
                "  exit 0\n"
                "fi\n"
                "[ $# -ge 2 ] || exit 64\n"
                "n=$#\n"
                "dst=\n"
                "i=1\n"
                'for a in "$@"; do if [ "$i" -eq "$n" ]; then dst=$a; fi; i=$((i+1)); done\n'
                'if [ -d "$dst" ]; then\n'
                '  for src in "$@"; do\n'
                '    [ "$src" = "$dst" ] && continue\n'
                '    base=${src##*/}\n'
                '    cp "$src" "$dst/$base" || exit $?\n'
                '    [ -z "$mode" ] || chmod "$mode" "$dst/$base" || true\n'
                "  done\n"
                "  exit 0\n"
                "fi\n"
                "[ $# -eq 2 ] || exit 64\n"
                'src=$1\n'
                'if [ "$mkparent" = "1" ]; then\n'
                '  parent=${dst%/*}\n'
                '  [ -n "$parent" ] && mkdir -p "$parent"\n'
                "fi\n"
                'cp "$src" "$dst" || exit $?\n'
                '[ -z "$mode" ] || chmod "$mode" "$dst" || true\n'
            )
        os.chmod(shim, 0o700)
        path = os.environ.get("PATH", "")
        if shim_dir not in path.split(os.pathsep):
            os.environ["PATH"] = shim_dir + os.pathsep + path
        return shim

    def _ensure_mkinstalldirs(self):
        """Create .hmbs-bin/mkinstalldirs wrapper; return its path.

        MKINSTALLDIRS must be passed to make as a single token, so the
        shell fragment `mkdir -p` (with a space) cannot be used directly:
        make would split it into a stray `-p` flag and abort with usage.
        The wrapper carries no spaces and just execs `mkdir -p "$@"`.
        """
        shim_dir = os.path.join(self.build_folder, ".hmbs-bin")
        os.makedirs(shim_dir, exist_ok=True)
        wrapper = os.path.join(shim_dir, "mkinstalldirs")
        with open(wrapper, "w", encoding="utf-8", newline="\n") as f:
            f.write("#!/bin/sh\n"
                    'exec mkdir -p "$@"\n')
        os.chmod(wrapper, 0o700)
        return wrapper

    def _relink_whiptail_static(self):
        """Relink installed bin/whiptail against static libnewt.a.

        Upstream always links whiptail with `-lnewt`, which resolves to
        libnewt.so when both .a/.so are built, leaving DT_NEEDED
        libnewt.so.0.52 in the binary. The static package deletes the
        .so files (Conan convention), so the shipped whiptail dies with
        'Error loading shared library libnewt.so.0.52' (truth on the
        2026-09-17 preflight). Re-run the link with the installed
        libnewt.a path so libnewt is embedded; slang/popt stay dynamic
        via -l (runenv provides them, as before).

        Upstream link rule is `whiptail: $(NDIALOGOBJS) $(LIBNEWTSH)`
        with NDIALOGOBJS = whiptail.o dialogboxes.o, i.e.
        `$(CC) -o whiptail whiptail.o dialogboxes.o -L. -lnewt -lpopt`.
        The previous round linked only whiptail.o + libnewt.a and missed
        dialogboxes.o, so lld failed with undefined useFullButtons,
        setButtonText, messageBox, checkList, inputBox, listBox, min/max
        (all defined in dialogboxes.o), the fallback kept the dynamic
        binary, and after the .so strip `whiptail --version` died with
        Error 127 'symbol not found: newt*' (2026-09-17 preflight).
        This version links BOTH objects, mirroring upstream.

        Returns True on success, False when the original binary is kept.
        """
        pkg_bin = os.path.join(self.package_folder, "bin", "whiptail")
        if not os.path.isfile(pkg_bin):
            return True
        libnewt_a = os.path.join(self.package_folder, "lib", "libnewt.a")
        if not os.path.isfile(libnewt_a):
            return True
        # Link inputs: both upstream NDIALOGOBJS members. Prefer the
        # built .o files; if one is missing, compile its .c from the
        # build/source tree so the link still mirrors upstream.
        objs = []
        pending_srcs = []
        for name in ("whiptail.o", "dialogboxes.o"):
            p = os.path.join(self.build_folder, name)
            if os.path.isfile(p):
                objs.append(p)
                continue
            base = name[:-2] + ".c"
            cand = None
            for d in (self.build_folder, self.source_folder):
                q = os.path.join(d, base)
                if os.path.isfile(q):
                    cand = q
                    break
            if cand is None:
                self.output.warning(
                    f"HMBS: {name}/{base} not found; keeping binary")
                return False
            pending_srcs.append(cand)
        src = None
        if pending_srcs:
            # Only the all-source fallback: compile missing .c files
            # together with existing .o files in one cc invocation.
            src = pending_srcs
        # -L dirs + -l slang/popt from the dep graph (same set the
        # consumer test uses); libnewt passed as an explicit .a path.
        libdirs, libs = [], []
        for dep in self.dependencies.values():
            try:
                info = dep.cpp_info
            except Exception:
                continue
            for d in getattr(info, "libdirs", []) or []:
                if d and os.path.isdir(d) and d not in libdirs:
                    libdirs.append(d)
            for lib in getattr(info, "libs", []) or []:
                if lib and lib not in libs and lib != "newt":
                    libs.append(lib)
        for lib in ("slang", "popt"):
            if lib not in libs:
                libs.append(lib)
        cc = os.environ.get("CC", "") or self._resolve_cc()
        tmp = os.environ.get("TMPDIR", "") or self._writable_tmpdir()
        for k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[k] = tmp
        cmd_in = " ".join([f'"{p}"' for p in objs + (src or [])])
        ldflags = " ".join(f'-L"{d}"' for d in libdirs)
        ldlibs = " ".join(f"-l{lib}" for lib in libs)
        # Extra -I for the .c compile path (slang.h/popt.h/newt.h).
        incs = []
        for dep in self.dependencies.values():
            try:
                info = dep.cpp_info
            except Exception:
                continue
            for d in getattr(info, "includedirs", []) or []:
                if d and os.path.isdir(d) and d not in incs:
                    incs.append(d)
        # newt.h for the source-compile path: installed header or build tree.
        for d in (os.path.join(self.package_folder, "include"),
                  self.build_folder, self.source_folder):
            if d and os.path.isdir(d) and d not in incs:
                incs.append(d)
        incflags = " ".join(f'-I"{d}"' for d in incs)
        cmd = (f'{cc} {cmd_in} -o "{pkg_bin}.static" '
               f'{incflags} "{libnewt_a}" {ldflags} {ldlibs}')
        self.output.info(f"HMBS: relinking whiptail statically: {cmd}")
        # lld needs libxml2.so.16 from the SDK llvm/lib dir, which the profile
        # buildenv injects through conanbuild.sh. A bare clang/lld invocation
        # bypasses that env and dies with 'Error loading shared library
        # libxml2.so.16' (known OHOS issue). Source conanbuild.sh first so the
        # link runs with the full LD_LIBRARY_PATH; the _fix_conanbuild_shell
        # overrides (CC/PATH/TMPDIR/SHELL) are appended last and win.
        env_prefix = ""
        conanbuild_sh = os.path.join(self.generators_folder, "conanbuild.sh")
        if os.path.isfile(conanbuild_sh):
            env_prefix = f'. "{conanbuild_sh}" && '
        try:
            subprocess.run(env_prefix + cmd, shell=True,
                           cwd=self.build_folder, check=True)
        except Exception as exc:
            self.output.warning(f"HMBS: static whiptail relink failed: {exc}")
            return False
        try:
            os.replace(f"{pkg_bin}.static", pkg_bin)
        except Exception as exc:
            self.output.warning(f"HMBS: replacing whiptail failed: {exc}")
            return False
        try:
            os.chmod(pkg_bin, 0o755)
        except Exception:
            pass  # HMBS_CAP_CHMOD=0: chmod unsupported, best-effort only.
        self.output.info("HMBS: whiptail relinked against static libnewt.a")
        return True

    def _resolve_install(self):
        """Prefer HMBS/system install, else the .hmbs-bin shim.

        Priority: HMBS_INSTALL injected by hmbs (platform capability
        install_shim:true, already handles the chmod-less FS) > OHOS
        toybox /system/bin/install (etsh/5.4.0 precedent) > install found
        on PATH > the shim created above. Either way ensure the chosen
        dir is first on PATH so bare `install` calls in the top-level
        Makefile resolve, and return the absolute binary for explicit
        INSTALL* make overrides (covers absolute /usr/bin/install in the
        static po/Makefile).
        """
        shim = self._ensure_install_shim()
        cands = [os.environ.get("HMBS_INSTALL") or "",
                 "/system/bin/install",
                 shutil.which("install") or ""]
        for cand in cands:
            prog = cand.strip().split()[0].strip("\"'") if cand else ""
            if prog and os.path.isfile(prog) and os.access(prog, os.X_OK):
                d = os.path.dirname(prog)
                path = os.environ.get("PATH", "")
                if d and d not in path.split(os.pathsep):
                    os.environ["PATH"] = d + os.pathsep + path
                self.output.info(f"HMBS: using system install: {prog}")
                return prog
        self.output.info(f"HMBS: using install shim: {shim}")
        return shim

    def _fix_conanbuild_shell(self):
        conanbuild_sh = os.path.join(self.generators_folder, "conanbuild.sh")
        if not os.path.isfile(conanbuild_sh):
            return
        with open(conanbuild_sh, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        # Re-export writable TMPDIR (readonly_tmp) alongside SHELL overrides
        # so configure/clang children sourced via conanbuild.sh avoid /tmp.
        # Also re-export the probed CC last so it wins over the toolchain
        # script (which may point at a clang unreachable from this domain).
        tmp = os.environ.get("TMPDIR", "")
        cc = os.environ.get("CC", "")
        path = os.environ.get("PATH", "")
        fix = (
            '\n# Override HMBS buildenv SHELL/CONFIG_SHELL (HNP bash getcwd)\n'
            'export SHELL="/bin/sh"\n'
            'export CONFIG_SHELL="/bin/sh"\n'
        )
        if cc:
            fix += f'export CC="{cc}"\n'
        if tmp:
            fix += (
                '# Writable tmp for readonly /tmp (HMBS readonly_tmp)\n'
                f'export TMPDIR="{tmp}"\n'
                f'export TMP="{tmp}"\n'
                f'export TEMP="{tmp}"\n'
            )
        if path:
            # Bare `install` in newt top Makefile resolves via PATH; the
            # conanbuild.sh-sourced env would otherwise lose the shim dir
            # (and /system/bin toybox dir) set via os.environ in build().
            fix += (
                '# Prefer .hmbs-bin shim / toybox install dir for bare install\n'
                f'export PATH="{path}"\n'
            )
        if 'Prefer .hmbs-bin shim' not in content:
            with open(conanbuild_sh, "w", encoding="utf-8", newline="\n") as f:
                f.write(content + fix)
