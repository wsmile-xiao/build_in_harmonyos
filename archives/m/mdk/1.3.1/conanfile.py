#!/usr/bin/env python3
"""Conan recipe - mdk 1.3.1 (autotools).

GNU MIX Development Kit: an emulation of Knuth's MIX computer and its MIXAL
assembly language.  Upstream ships mixasm (MIXAL assembler) and mixvm (MIX
virtual machine) as bin_PROGRAMS; mixlib/libmix.a is a noinst convenience
library that upstream does NOT install, so this is an application package.

The release tarball already contains the generated configure + Makefile.in
files, so no autoreconf bootstrap is needed on the OHOS worker.

Optional upstream features are disabled for the OHOS build:
  - --disable-gui       (gmixvm needs GTK+ 3 / Pango, unavailable on OHOS)
  - --without-guile     (mixguile shell needs Guile; the core tools,
                         libmix and the upstream test suite do not)
  - --without-readline  (mixvm line editing falls back to plain stdin;
                         avoids readline/ncurses devel on the worker)
The only remaining configure-time dependency is glib-2.0, provided by the
ohpcd artifact repository.
"""

import gc
import glob
import json
import os
import shlex
import shutil
import subprocess
import time

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


def _drop_umask_077(path):
    """E114/E011: HMDFS forces setgid on directories; `umask 077 && mktemp -d`
    creates a drwx--S--- temp dir that is not writable even by its owner.
    Replace every `umask 077` with `umask 022` in the generated configure so
    its AS_TMPDIR / config.status temp dirs stay owner-writable (E011's
    recommended method, same as the a52dec/adcli recipes)."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace("umask 077", "umask 022")
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


def _harden_intltool_version_check(path):
    """Round 3: the shipped configure probes the version with a bare
    `intltool-update --version | head -1 | cut -d" " -f3` (line ~10639)
    BEFORE consulting $INTLTOOL_UPDATE, so only PATH order decides it.
    When PATH resolves to the published intltool package script whose perl
    shebang is missing on the device, the probe yields an empty version and
    configure dies with "Your intltool is too old". Make the probe fall back
    to the tool_requires version instead of failing on an unrunnable script.
    Same category as _drop_umask_077: build-time edit of the generated
    configure, no patch file, no platform macro."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    old = 'INTLTOOL_APPLIED_VERSION=`intltool-update --version | head -1 | cut -d" " -f3`'
    new = ('INTLTOOL_APPLIED_VERSION=`(intltool-update --version 2>/dev/null '
           '|| echo "intltool-update (intltool) 0.51.0") | head -1 | cut -d" " -f3`')
    if old in data:
        data = data.replace(old, new)
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)


def _is_runnable_pkg_config(candidate):
    """Verify a pkg-config/pkgconf candidate (xmlsec/pcre2 precedent):
    isfile alone is untrusted on this worker; only --version rc==0 with
    non-empty stdout counts as runnable."""
    if not candidate or not os.path.isfile(candidate):
        return False
    try:
        proc = subprocess.run(
            [candidate, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
            check=False,
        )
    except Exception:
        return False
    return proc.returncode == 0 and bool((proc.stdout or "").strip())


def _write_exec_shim(path, target):
    """Create a #!/bin/sh exec shim without chmod dependency
    (HMBS_CAP_CHMOD=0; xmlsec/ctpl precedent uses os.open 0o755)."""
    script = "#!/bin/sh\nexec {} \"$@\"\n".format(shlex.quote(target))
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    except OSError:
        pass
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        f.write(script)
    try:
        os.chmod(path, 0o755)
    except OSError:
        pass
    return path


def _low_mem_flags():
    """Constrained-device OOM mitigation (libgridxc/2.1.02.0.2 precedent):
    lower optimization and strip debug info. Additive tail flags only:
    -O1 cuts clang peak memory vs profile -O3, -g0 avoids large debug
    sections. No other flags touched so profile/toolchain defaults stay."""
    return ["-O1", "-g0"]


def _append_unique_flags(existing, extra):
    parts = existing.split() if existing else []
    for flag in extra:
        if flag not in parts:
            parts.append(flag)
    return " ".join(parts).strip()


def _is_oom_text(text):
    if not text:
        return False
    markers = ("Signal 9", "Out of memory", "Cannot allocate memory",
               "Killed", "killed", "posix_spawn", "unable to execute command",
               "Error 137", "exit 137", "-9")
    return any(m in text for m in markers)


def _automake_count(text, label):
    """Parse `# LABEL: N` from an automake parallel-tests test-suite.log."""
    for line in text.splitlines():
        if line.startswith("# " + label + ":"):
            try:
                return int(line.split(":", 1)[1].strip())
            except ValueError:
                return 0
    return 0


class MdkConan(ConanFile):
    name = "mdk"
    version = "1.3.1"
    description = "GNU MIX Development Kit: MIX computer emulator and MIXAL assembler"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/mdk/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        # CCI-leaf fix (libtiger/0.3.4 #5 + ayatana-ido/0.10.4-v2 15th-round
        # precedent, same fingerprint): glib's bare libffi/3.4.4 resolves to
        # the conan-center recipe on preflight (log applies the CCI-only
        # patch 0008-3.4.4-invalid-CFI-advance_loc.patch, absent from the
        # in-repo recipe), whose configure dies with
        # "/data/service/hnp/bin/bash: inaccessible or not found" (Error
        # 127). Pin the ohpcd-published RREV of the hardened in-repo recipe
        # (server-verified single revision ca8b0eb4102edbca48730e504e3afbdc,
        # 2026-07-17; libgsf validated end-to-end). Same version, so glib's
        # package_id is untouched (switching to 3.5.2 would force a glib
        # source rebuild per that precedent).
        self.requires(
            "libffi/3.4.4#ca8b0eb4102edbca48730e504e3afbdc", override=True
        )

    def layout(self):
        basic_layout(self)

    def build_requirements(self):
        # configure.ac calls IT_PROG_INTLTOOL([0.37],[no-xml])
        # unconditionally: old intltool.m4 still probes intltool-update
        # even with --disable-nls (launchpad bugs 904647/398572), and the
        # true-machine worker has no runnable intltool-update
        # ("inaccessible or not found" -> "Your intltool is too old").
        # Provide the published pure-perl tool package (pslib/dbus-test/
        # l3afpad precedent). [no-xml] already skips the XML::Parser
        # check, so no perl-module stub is needed.
        self.tool_requires("intltool/0.51.0")
        # configure runs PKG_CHECK_MODULES(GLIB, glib-2.0): it needs the
        # pkg-config script, but HMBS only injects cmake/make/ninja/python3
        # and the worker has no system pkg-config ("checking for pkg-config
        # ... no" -> "The pkg-config script could not be found"). Provide
        # the published pkgconf tool (xmlsec/ctpl/burp2/fcft precedent).
        self.tool_requires("pkgconf/3.0.5")

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "mdk is only supported on Linux/OHOS, not " + str(self.settings.os)
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # configure discovers glib through pkg-config.
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()

        tc = AutotoolsToolchain(self)
        # config.guess cannot identify HarmonyOS (uname -s = "HarmonyOS",
        # kernel "HongMeng Kernel"); pass the triplet explicitly (config.sub
        # supports *-linux-ohos) - same approach as the adcli recipe.
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # gmixvm needs GTK+ 3 / Pango (unavailable on the OHOS worker).
        tc.configure_args.append("--disable-gui")
        # The mixguile shell needs Guile; mixasm/mixvm, libmix and the
        # upstream test suite build and run without it.
        tc.configure_args.append("--without-guile")
        # mixvm readline editing is optional (falls back to plain stdin);
        # skipping it avoids readline/ncurses devel on the worker.
        tc.configure_args.append("--without-readline")
        # E027: GNU packages default to NLS (Native Language Support)
        # backed by the included intl/ directory; OHOS has no system
        # libintl/gettext runtime for it. --disable-nls drops the
        # NLS build (po/ + included intl) for the core tools, same as
        # the pslib/dbus-test OHOS recipes. Note it does NOT skip the
        # unconditional IT_PROG_INTLTOOL probe above -- that is why the
        # intltool tool_requires is still required.
        tc.configure_args.append("--disable-nls")
        # Round 7 OOM mitigation (libgridxc/2.1.02.0.2 + traildb/0.6
        # precedent; 2026-10-01 preflight died in compile with bare
        # "Signal 9" + empty logs): additively append -O1 -g0 so any
        # profile -O3/-g is followed by the low-mem tail (later option
        # wins for clang), never overwriting profile/toolchain content.
        # Idempotent: skip flags already present.
        for _f in _low_mem_flags():
            if _f not in tc.extra_cflags:
                tc.extra_cflags.append(_f)
            if _f not in tc.extra_cxxflags:
                tc.extra_cxxflags.append(_f)
        self.output.info("mdk low-mem flags: extra_cflags=%s extra_cxxflags=%s"
                         % (tc.extra_cflags, tc.extra_cxxflags))

        env = tc.environment()
        # OHOS /tmp may be a read-only mount: keep configure/make temporary
        # files inside the hmbs-injected scratch dir, falling back to an
        # isolated dir under the Conan build folder.
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or os.path.join(self.build_folder, ".tmp")
        )
        os.makedirs(tmpdir, exist_ok=True)
        env.define_path("TMPDIR", tmpdir)
        env.define_path("TMP", tmpdir)
        env.define_path("TEMP", tmpdir)
        # E266 (c-ares/babeltrace precedent, CI #30626): OHOS SDK lld links
        # libxml2.so.16 from SDK llvm/lib; worker default search path misses
        # it so lld fails to start and configure reports "C compiler cannot
        # create executables". Prepend SDK llvm/lib to LD_LIBRARY_PATH
        # (glob fallback for SDK version drift). Profile already sets one
        # revision; this covers the live host revision without touching
        # CFLAGS/LDFLAGS/test scope.
        _llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        if not os.path.isdir(_llvm_lib):
            _cands = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"))
            _llvm_lib = _cands[0] if _cands else ""
        if _llvm_lib:
            env.prepend_path("LD_LIBRARY_PATH", _llvm_lib)
        # True-machine Error 127: profile pins CC to
        # /data/service/hnp/bin/clang which is "inaccessible or not found"
        # on the current host (config.log: conftest with -O3 -DNDEBUG).
        # Resolve a runnable compiler and pin CC/CXX so configure's
        # AC_PROG_CC sanity check uses it (zydis/cassbeam/zurl precedent;
        # different strategy from last round's LD_LIBRARY_PATH-only fix).
        _cc = self._resolve_compiler("c")
        _cxx = self._resolve_compiler("cpp")
        if _cc:
            env.define("CC", _cc)
        if _cxx:
            env.define("CXX", _cxx)
        self.output.info("mdk compilers: CC=%s CXX=%s" % (_cc, _cxx))
        tc.generate(env=env)
        # True-machine guard (bwm/0.6.3 + libtiger/0.3.4 precedent): the repo
        # profile pins SHELL/CONFIG_SHELL=/data/service/hnp/bin/bash, which
        # is inaccessible on the current HMBS host (configure[139] dies with
        # "inaccessible or not found", Error 127; HMBS injects SHELL=/bin/sh
        # with capability shell=/bin/sh). Generated build-scope scripts win
        # over the profile [buildenv], while inline os.environ tweaks in
        # build() alone do not. Never return the HNP bash path.
        shell = self._usable_shell()
        fix_tmp = self._usable_tmpdir(makedirs=True)
        fix_env = Environment()
        fix_env.define("SHELL", shell)
        fix_env.define("CONFIG_SHELL", shell)
        fix_env.define("TMPDIR", fix_tmp)
        fix_env.define("TMP", fix_tmp)
        fix_env.define("TEMP", fix_tmp)
        fix_env.vars(self, scope="build").save_script("mdk_hmos_fix")
        self.output.info(
            "mdk_hmos_fix: SHELL/CONFIG_SHELL=%s TMPDIR=%s" % (shell, fix_tmp)
        )

    def _usable_shell(self):
        # HMBS capability shell=/bin/sh; the repo profile pins HNP bash
        # which exists as a file on some hosts but is not executable
        # ("inaccessible or not found"). Hard-prefer /bin/sh and never
        # return the HNP path, even if isfile() is true for it.
        if os.path.isfile("/bin/sh"):
            return "/bin/sh"
        sh_which = shutil.which("sh") or ""
        if sh_which and os.path.isfile(sh_which):
            return sh_which
        for cand in (os.environ.get("SHELL", ""), os.environ.get("CONFIG_SHELL", "")):
            if not cand:
                continue
            first = cand.split()[0]
            if "hnp/bin/bash" in first:
                continue
            if os.path.isfile(first):
                return cand
        return "/bin/sh"

    def _usable_tmpdir(self, makedirs=False):
        # Priority: HMBS task-local TMPDIR/TMP/TEMP (injected writable),
        # else build-local tmp. Reuse HMBS values when present
        # (readonly_tmp: never fall back to /tmp).
        for var in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR", "HMBS_INSTALL"):
            cand = os.environ.get(var, "")
            if cand and os.path.isdir(cand):
                return cand
        tmpd = os.path.join(self.build_folder, "tmp")
        if makedirs:
            os.makedirs(tmpd, exist_ok=True)
        return tmpd

    def _cand_works(self, prog):
        """True if prog runs (cassbeam precedent). No os.access X_OK (R49:
        HMDFS ignores chmod, X_OK is恒False). Only subprocess probe."""
        import subprocess
        if not prog:
            return False
        prog = prog.strip().split()[0].strip("\"'")
        if "/" not in prog:
            prog = shutil.which(prog) or ""
            if not prog:
                return False
        # Never trust the poisoned HNP path even if isfile() is true.
        if "hnp/bin/bash" in prog:
            return False
        try:
            r = subprocess.run([prog, "--version"],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, timeout=20)
            return r.returncode == 0
        except Exception:
            return False

    def _resolve_compiler(self, kind):
        """Return usable CC/CXX. Prefers profile conf when it actually runs
        (healthy host zero-change); else PATH-discovered clang (HMBS
        prepends tool dirs to buildenv PATH) or ~/usr/local/bin fallback.
        Only covers CC/CXX, never CFLAGS/LDFLAGS (R33). kind: 'c'/'cpp'."""
        bare = "clang" if kind == "c" else "clang++"
        try:
            exes = self.conf.get("tools.build:compiler_executables",
                                 default=None)
        except Exception:
            exes = None
        conf_val = None
        if isinstance(exes, dict):
            conf_val = (exes.get("c") if kind == "c"
                        else exes.get("cpp") or exes.get("cxx"))
        if conf_val and self._cand_works(conf_val):
            return conf_val.strip().split()[0].strip("\"'")
        if conf_val:
            self.output.warning(
                "mdk pinned compiler not runnable: %r; falling back"
                % (conf_val,))
            # Same-dir sibling (clang/clang++ convention).
            try:
                _d = os.path.dirname(conf_val.strip().split()[0])
                if _d:
                    _same = os.path.join(_d, bare)
                    if self._cand_works(_same):
                        self.output.info(
                            "mdk compiler fallback (sibling): %s" % _same)
                        return _same
            except Exception:
                pass
        for cand in (bare,
                     os.path.join(os.path.expanduser("~"), "usr", "local",
                                  "bin", bare),
                     "/storage/Users/currentUser/usr/local/bin/" + bare):
            if self._cand_works(cand):
                resolved = (cand.strip().split()[0] if "/" in cand
                            else shutil.which(cand))
                self.output.info(
                    "mdk compiler fallback: %s (conf was %r)"
                    % (resolved, conf_val))
                return resolved
        return conf_val or bare

    def _fs_env(self):
        """HMBS platform diagnosis [shell_getcwd]/[readonly_tmp] (same failure
        signature as addchain/adcli): HMDFS denies getcwd() on the conan build
        tree's parent dirs, so bash/autoconf `pwd` fails
        ("configure: error: working directory cannot be determined").  Set PWD
        explicitly (autoconf checks $PWD first; bash inits $PWD from the env
        without calling getcwd()) and pin TMPDIR/TMP/TEMP to a writable dir
        for the configure/make/install steps. Also pins SHELL/CONFIG_SHELL
        to the usable shell (bwm/0.6.3 precedent): the repo profile pins
        /data/service/hnp/bin/bash, inaccessible on the current HMBS host
        (configure[139] "inaccessible or not found", Error 127)."""
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or os.path.join(self.build_folder, ".tmp")
        )
        os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define("PWD", self.build_folder)
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        shell = self._usable_shell()
        env.define("SHELL", shell)
        env.define("CONFIG_SHELL", shell)
        # dbustest precedent (_make_gettext_stub): the published intltool
        # package's perl scripts fail to exec on the device (stale absolute
        # perl shebang -> kernel ENOENT reported against the script path,
        # exactly this round's
        # ".../p/bin/intltool-update: No such file or directory").
        # --disable-nls means po/ translations are never built, so the
        # ONLY real use of these tools is IT_PROG_INTLTOOL's
        # `intltool-update --version` probe (launchpad 904647: old
        # intltool.m4 probes even with --disable-nls). Provide sh shims
        # (no perl shebang, no exec-bit dependency beyond /bin/sh) that
        # answer --version truthfully as the tool_requires 0.51.0 and
        # delegate any other invocation to the real script via device
        # perl when available. Placed under the HMBS scratch tmpdir
        # (exec-capable) rather than the HMDFS build tree, prepended to
        # PATH ahead of the tool_requires bin, and also exported via
        # INTLTOOL_* so AC_PATH_PROG picks them without searching.
        self._mdk_shim_dir = ""
        try:
            if str(self.settings.os) == "OHOS":
                _itool_pkg = ""
                try:
                    _itool_pkg = self.dependencies.build["intltool"].package_folder or ""
                except Exception:
                    _itool_pkg = ""
                _itool_bin = os.path.join(_itool_pkg, "bin") if _itool_pkg else ""
                _perl = shutil.which("perl") or ""
                _stub = os.path.join(tmpdir, "mdk-intltool-shim")
                os.makedirs(_stub, exist_ok=True)
                for _name in ("intltool-update", "intltool-merge",
                              "intltool-extract"):
                    _orig = os.path.join(_itool_bin, _name) if _itool_bin else ""
                    _dst = os.path.join(_stub, _name)
                    _lines = ["#!/bin/sh",
                              'if [ "x$1" = "x--version" ]; then',
                              '  echo "%s (intltool) 0.51.0" >&1' % _name,
                              "  exit 0",
                              "fi"]
                    if _orig and os.path.isfile(_orig) and _perl and os.path.isfile(_perl):
                        _lines.append("exec " + shlex.quote(_perl) + " "
                                      + shlex.quote(_orig) + ' "$@"')
                    else:
                        # NLS disabled: tools never needed beyond the
                        # version probe above; succeed quietly instead of
                        # failing configure on a translation feature ELFs
                        # do not use.
                        _lines.append("exit 0")
                    with open(_dst, "w", encoding="utf-8") as _fh:
                        _fh.write("\n".join(_lines) + "\n")
                    try:
                        os.chmod(_dst, 0o755)
                    except Exception:
                        pass
                    env.define("INTLTOOL_" + _name.split("-", 1)[1].upper().replace("-", "_"),
                               _dst)
                env.prepend_path("PATH", _stub)
                self._mdk_shim_dir = _stub
                self.output.info("mdk intltool shims: dir=%s perl=%r pkg=%r"
                                 % (_stub, _perl, _itool_pkg))
        except Exception as _exc:
            self.output.warning("mdk intltool wrapper setup skipped: %s" % (_exc,))
        # Round 8 (libgda5/5.2.10 + dbustest/19.04.0 precedent, same
        # fingerprint): IT_PROG_INTLTOOL unconditionally requires GNU
        # gettext tools (msgfmt/gmsgfmt/msgmerge/xgettext --version must
        # contain "(GNU"), even with --disable-nls (launchpad 904647).
        # This round died with `checking for msgfmt... (cached) :` +
        # `configure: error: GNU gettext tools not found; required for
        # intltool`. OHOS SDK splits the tools (libgda5 lesson):
        # /data/service/hnp/bin has xgettext/msgfmt on some hosts while
        # msgmerge lives under gettext.org/*/bin, and the mdk worker has
        # none of them on PATH. Prepend SDK dirs first; stub whatever is
        # still missing under the HMBS scratch tmpdir (safe:
        # --disable-nls means po/ never builds translations beyond the
        # probe, dbustest stub precedent).
        self._mdk_gettext_shim_dir = ""
        try:
            if str(self.settings.os) == "OHOS":
                for _gdir in sorted(glob.glob("/data/service/hnp/gettext.org/*/bin")):
                    try:
                        if os.path.isdir(_gdir):
                            env.prepend_path("PATH", _gdir)
                    except Exception:
                        pass
                _gshim = os.path.join(tmpdir, "mdk-gettext-shim")
                os.makedirs(_gshim, exist_ok=True)
                # Round 10 fix: UNCONDITIONAL shims for all four tools.
                # Round 8 (existence-only) kept broken harmonybrew tools;
                # round 9 (runnable check inside _fs_env) still saw only
                # gmsgfmt broken because the check runs BEFORE the host
                # glib lib dir is prepended to LD_LIBRARY_PATH later in
                # this same function -- at check time the harmonybrew
                # binaries still work, but under configure's full env the
                # glib proxy-libintl shadows system libintl and they die
                # with rc=127 libintl_gettext relocation (gtkspell3 lesson
                # + [stale_runtime_library] diagnosis). Probing at either
                # time gives the wrong answer, so stop probing: always
                # shadow all four with sh shims (safe: --disable-nls means
                # po/ never builds, dbustest precedent) placed frontmost
                # on PATH.
                _need_stub = ("msgfmt", "gmsgfmt", "msgmerge", "xgettext")
                for _gtool in _need_stub:
                    _dst = os.path.join(_gshim, _gtool)
                    with open(_dst, "w", encoding="utf-8") as _fh:
                        _fh.write("#!/bin/sh\n"
                                  + "if [ \"x$1\" = \"x--version\" ]; then\n"
                                  + "  echo \"" + _gtool + " (GNU gettext-tools) 0.22.5\"\n"
                                  + "  exit 0\n"
                                  + "fi\n"
                                  + "exit 0\n")
                    try:
                        os.chmod(_dst, 0o755)
                    except Exception:
                        pass
                if _need_stub:
                    env.prepend_path("PATH", _gshim)
                    self._mdk_gettext_shim_dir = _gshim
                    self.output.info("mdk gettext stubs: %s" % (",".join(_need_stub),))
                else:
                    self.output.info("mdk gettext: SDK/PATH tools sufficient, no stub")
        except Exception as _exc:
            self.output.warning("mdk gettext shim setup skipped: %s" % (_exc,))
        # Round 5 (xmlsec/1.3.12 precedent, same fingerprint second strategy):
        # tool_requires(pkgconf) alone was proven insufficient on 2026-10-01
        # preflight (still `checking for pkg-config... no`) because the in-repo
        # pkgconf package only ships a `pkgconf` binary, no `pkg-config` alias,
        # and nothing exported PKG_CONFIG/PATH to configure. Bridge explicitly:
        # resolve a runnable implementation (--version verified), then expose
        # `pkg-config` + host-prefixed alias shims (os.open 0o755, no chmod
        # dependency for HMBS_CAP_CHMOD=0) under the HMBS scratch tmpdir and
        # export PKG_CONFIG so both the bare `pkg-config` probe and the
        # `aarch64-unknown-linux-ohos-pkg-config` triplet probe succeed.
        self._mdk_pkg_config = ""
        self._mdk_pkg_shim_dir = ""
        try:
            if str(self.settings.os) == "OHOS":
                _cands = [os.environ.get("PKG_CONFIG"),
                          shutil.which("pkg-config"), shutil.which("pkgconf")]
                try:
                    _ptool = self.dependencies.build.get("pkgconf")
                    _pbin = os.path.join(_ptool.package_folder, "bin") \
                        if _ptool and _ptool.package_folder else ""
                except Exception:
                    _pbin = ""
                if _pbin:
                    _cands.insert(0, os.path.join(_pbin, "pkgconf"))
                    _cands.insert(0, os.path.join(_pbin, "pkg-config"))
                _cands.append("/data/service/hnp/pkg-config.org/"
                              "pkg-config_0.29.2/bin/pkg-config")
                _resolved = ""
                for _cand in _cands:
                    if _is_runnable_pkg_config(_cand):
                        _resolved = _cand
                        break
                if _resolved:
                    _pshim = os.path.join(tmpdir, "mdk-pkgconfig-shim")
                    _write_exec_shim(os.path.join(_pshim, "pkg-config"), _resolved)
                    _write_exec_shim(os.path.join(
                        _pshim, "aarch64-unknown-linux-ohos-pkg-config"), _resolved)
                    env.define("PKG_CONFIG", _resolved)
                    env.prepend_path("PATH", _pshim)
                    self._mdk_pkg_config = _resolved
                    self._mdk_pkg_shim_dir = _pshim
                    self.output.info("mdk pkg-config: %s shim=%s" % (_resolved, _pshim))
                else:
                    self.output.warning("mdk no runnable pkg-config/pkgconf found")
        except Exception as _exc:
            self.output.warning("mdk pkg-config shim setup skipped: %s" % (_exc,))
        # Round 6: `make check` runs the 6 freshly-linked test binaries in
        # the build tree. They link glib dynamically (-lglib-2.0), but the
        # build-scope env has no LD_LIBRARY_PATH entry for the conan host
        # packages, so every test binary would die at exec with a missing
        # .so (identical FAIL x6, including the fixture-free mixtypest).
        # Prepend each host dep lib dir (glib, libffi, pcre2, ...) without
        # touching test scope or logic.
        try:
            for _dep in self.dependencies.host.values():
                try:
                    _pf = _dep.package_folder or ""
                except Exception:
                    continue
                if not _pf:
                    continue
                for _sub in ("lib",):
                    _ld = os.path.join(_pf, _sub)
                    try:
                        if os.path.isdir(_ld):
                            env.prepend_path("LD_LIBRARY_PATH", _ld)
                    except Exception:
                        pass
        except Exception as _exc:
            self.output.warning("mdk host LD_LIBRARY_PATH setup skipped: %s" % (_exc,))
        return env

    def _sync_test_fixtures(self):
        """Round 6: upstream compiles with
        -DMIX_TEST_SAMPLES_DIR="<top_srcdir>/samples" and opens relative
        "tests/..." fixtures. In a Conan out-of-source build the compiled-in
        top_srcdir (source tree) and the `make check` cwd (build tree) can
        diverge, so mirror the fixture dirs into the build tree when they
        are missing there. Pure copy, no test-logic change."""
        import shutil as _shutil
        pairs = [
            (os.path.join(self.source_folder, "samples"),
             os.path.join(self.build_folder, "samples")),
            (os.path.join(self.source_folder, "mixlib", "testsuite", "tests"),
             os.path.join(self.build_folder, "mixlib", "testsuite", "tests")),
        ]
        for _src, _dst in pairs:
            try:
                if os.path.isdir(_src) and not os.path.isdir(_dst):
                    os.makedirs(os.path.dirname(_dst), exist_ok=True)
                    _shutil.copytree(_src, _dst)
                    self.output.info("mdk fixtures synced: %s -> %s" % (_src, _dst))
            except Exception as _exc:
                self.output.warning("mdk fixture sync skipped %s: %s" % (_dst, _exc))

    def _dump_test_logs(self):
        """Round 6 forensics: `make check` failed with 6/6 FAIL but the
        summary hides per-test reasons. Dump test-suite.log plus each
        per-test .log tail and the fixture-dir state so the next round has
        evidence instead of guesses."""
        roots = []
        for _base in (self.build_folder, self.source_folder):
            try:
                if _base and os.path.isdir(_base) and _base not in roots:
                    roots.append(_base)
            except Exception:
                pass
        for _base in roots:
            for _root, _dirs, _files in os.walk(_base):
                if "test-suite.log" in _files:
                    _p = os.path.join(_root, "test-suite.log")
                    self.output.info("mdk-probe test-suite.log: %s" % _p)
                    try:
                        with open(_p, "r", encoding="utf-8", errors="replace") as _fh:
                            _c = _fh.read()
                        self.output.info("mdk-probe test-suite.log content:\n" + _c[:12000])
                    except Exception as _exc:
                        self.output.info("mdk-probe: cannot read %s: %s" % (_p, _exc))
        for _base in roots:
            for _root, _dirs, _files in os.walk(_base):
                for _fn in sorted(_files):
                    if _fn.endswith(".log") and _fn not in ("test-suite.log", "config.log"):
                        _p = os.path.join(_root, _fn)
                        if os.path.basename(_root) == "testsuite" or "testsuite" in _root:
                            try:
                                with open(_p, "r", encoding="utf-8", errors="replace") as _fh:
                                    _lines = _fh.read().splitlines()
                                _tail = "\n".join(_lines[-60:])
                                self.output.info("mdk-probe %s tail:\n%s" % (_p, _tail[:6000]))
                            except Exception:
                                pass
        for _label, _d in (("source/samples", os.path.join(self.source_folder, "samples")),
                           ("build/samples", os.path.join(self.build_folder, "samples")),
                           ("source/testsuite/tests",
                            os.path.join(self.source_folder, "mixlib", "testsuite", "tests")),
                           ("build/testsuite/tests",
                            os.path.join(self.build_folder, "mixlib", "testsuite", "tests"))):
            try:
                _names = sorted(os.listdir(_d)) if os.path.isdir(_d) else []
                self.output.info("mdk-probe %s: isdir=%s entries=%d %s"
                                 % (_label, os.path.isdir(_d), len(_names), _names[:15]))
            except Exception as _exc:
                self.output.info("mdk-probe %s list failed: %s" % (_label, _exc))

    def _dump_config_log(self):
        """True-machine forensics for Error 77 (bwm/cassbeam precedent):
        print toolchain env + clang probe + config.log compiler section."""
        import subprocess
        for var in ("CC", "CXX", "CFLAGS", "CPPFLAGS", "LDFLAGS",
                    "LD_LIBRARY_PATH", "TMPDIR", "TMP", "TEMP",
                    "SHELL", "CONFIG_SHELL", "PWD", "PKG_CONFIG",
                    "PATH", "INTLTOOL_UPDATE", "INTLTOOL_MERGE",
                    "INTLTOOL_EXTRACT"):
            self.output.info("mdk-probe %s=%r" % (var, os.environ.get(var, "")))
        for prog in (os.environ.get("CC", "").split()[0]
                     if os.environ.get("CC", "") else "", "clang"):
            if not prog:
                continue
            try:
                r = subprocess.run([prog, "--version"],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, timeout=20)
                out = r.stdout.decode("utf-8", "replace")[:2000]
                self.output.info("mdk-probe %s --version rc=%d: %s"
                                 % (prog, r.returncode, out[:500]))
            except Exception as exc:
                self.output.info("mdk-probe %s --version failed: %s" % (prog, exc))
        # intltool forensics: verify the shims answer --version from the
        # same environment configure sees (regression signal for the
        # "No such file or directory" ENOENT round).
        for _iprog in (os.environ.get("INTLTOOL_UPDATE", ""),
                        os.path.join(os.environ.get("TMPDIR", ""), "mdk-intltool-shim",
                                     "intltool-update")):
            if not _iprog or not os.path.isfile(_iprog.split()[0]):
                continue
            for _args in (["/bin/sh", _iprog.split()[0], "--version"],):
                try:
                    _r = subprocess.run(_args, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, timeout=20)
                    _out = _r.stdout.decode("utf-8", "replace")[:500]
                    self.output.info("mdk-probe intltool --version rc=%d: %s"
                                     % (_r.returncode, _out[:300]))
                except Exception as _exc:
                    self.output.info("mdk-probe intltool --version failed: %s" % (_exc,))
                break
            break
        for _gprog in ("msgfmt", "gmsgfmt", "msgmerge", "xgettext"):
            try:
                _gp = shutil.which(_gprog) or ""
                if not _gp:
                    self.output.info("mdk-probe %s: not on PATH" % (_gprog,))
                    continue
                _r = subprocess.run([_gp, "--version"],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, timeout=20)
                _out = _r.stdout.decode("utf-8", "replace")[:300]
                self.output.info("mdk-probe %s=%s rc=%d: %s"
                                 % (_gprog, _gp, _r.returncode, _out[:200]))
            except Exception as _exc:
                self.output.info("mdk-probe %s check failed: %s" % (_gprog, _exc))
        logs = []
        for root, _dirs, files in os.walk(self.build_folder):
            if "config.log" in files:
                logs.append(os.path.join(root, "config.log"))
        if not logs:
            self.output.info("mdk-probe: no config.log under build_folder")
            return
        path = logs[0]
        self.output.info("mdk-probe config.log: %s" % path)
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except Exception as exc:
            self.output.info("mdk-probe: cannot read config.log: %s" % exc)
            return
        # Compiler-failure section: from "checking whether the C compiler
        # works" to the next "configure: error", plus final 40 lines.
        lines = content.splitlines()
        start = next((i for i, l in enumerate(lines)
                      if "checking whether the C compiler works" in l), -1)
        if start >= 0:
            seg = lines[start:start + 120]
            self.output.info("mdk-probe config.log compiler section:\n"
                             + "\n".join(seg)[:8000])
        tail = lines[-40:] if len(lines) >= 40 else lines
        self.output.info("mdk-probe config.log tail:\n"
                         + "\n".join(tail)[:8000])

    def build(self):
        apply_conandata_patches(self)
        # E114/E011: drop umask 077 from the shipped configure (HMDFS).
        _drop_umask_077(os.path.join(self.source_folder, "configure"))
        # Round 3: harden the bare `intltool-update --version` probe (see
        # _harden_intltool_version_check): it ignores $INTLTOOL_UPDATE, so a
        # PATH-resolved broken package script alone fails the build.
        _harden_intltool_version_check(os.path.join(self.source_folder, "configure"))

        autotools = Autotools(self)
        # scope="build": INTLTOOL_*/PATH/SHELL/TMPDIR must reach
        # configure's build context (last round's default-scope vars
        # never arrived, so AC_PATH_PROG re-found the broken package
        # script instead of the shim). Inside the block the shim dir is
        # additionally re-asserted directly on os.environ (activity-log
        # precedent): Conan's aggregated conanbuild.sh can otherwise place
        # the tool_requires bin ahead of our shim for the bare version probe.
        with self._fs_env().vars(self, scope="build").apply():
            _shim = getattr(self, "_mdk_shim_dir", "")
            if _shim and os.path.isdir(_shim):
                os.environ["PATH"] = _shim + os.pathsep + os.environ.get("PATH", "")
                for _n, _v in (("INTLTOOL_UPDATE", "intltool-update"),
                               ("INTLTOOL_MERGE", "intltool-merge"),
                               ("INTLTOOL_EXTRACT", "intltool-extract")):
                    _p = os.path.join(_shim, _v)
                    if os.path.isfile(_p):
                        os.environ[_n] = _p
                self.output.info("mdk intltool PATH re-asserted: %s" % _shim)
            # Round 5: live re-assertion for the pkg-config bridge (xmlsec
            # precedent): aggregated conanbuild.sh alone did not make the
            # bare `pkg-config` probe see the tool package binary.
            _pshim = getattr(self, "_mdk_pkg_shim_dir", "")
            _pres = getattr(self, "_mdk_pkg_config", "")
            if _pshim and os.path.isdir(_pshim):
                os.environ["PATH"] = _pshim + os.pathsep + os.environ.get("PATH", "")
            if _pres and os.path.isfile(_pres):
                os.environ["PKG_CONFIG"] = _pres
            if _pshim or _pres:
                self.output.info("mdk pkg-config re-asserted: %s shim=%s"
                                 % (_pres, _pshim))
            _gshim = getattr(self, "_mdk_gettext_shim_dir", "")
            if _gshim and os.path.isdir(_gshim):
                os.environ["PATH"] = _gshim + os.pathsep + os.environ.get("PATH", "")
                self.output.info("mdk gettext PATH re-asserted: %s" % _gshim)
            try:
                autotools.configure()
            except Exception:
                self._dump_config_log()
                raise
            # E074: parallel make hits the HMDFS jobserver fifo EPERM.
            self._make_with_oom_retry(autotools, target=None,
                                      args=["-j1"], what="make")
            # L1: run the upstream unit-test suite (6 automake check_PROGRAMS
            # in mixlib/testsuite, driven entirely by local .mixal fixtures).
            # Round 6: mirror fixtures into the build tree first (no-op when
            # the build is in-source), then keep the real framework report:
            # on failure dump per-test logs + emit the marker BEFORE
            # re-raising, otherwise the ConanException hides the counts and
            # the backend records 0/0.
            self._sync_test_fixtures()
            try:
                self._make_with_oom_retry(autotools, target="check",
                                          args=["-j1"], what="make check")
            except Exception:
                self._dump_test_logs()
                try:
                    self._emit_upstream_test_result()
                except Exception:
                    pass
                raise
        self._emit_upstream_test_result()

    def _make_with_oom_retry(self, autotools, target, args, what):
        """Run one make step with OOM-only retry (traildb/0.6 precedent).

        Only the constrained-device memory signature retries (Signal 9 /
        Killed / Out of memory / Cannot allocate memory / exit 137);
        any other compile error re-raises immediately with no retry.
        Between retries: gc.collect() + 15s cooldown so the kernel can
        reclaim pages. Max 3 attempts, no flag changes, no targets
        skipped, no assertions touched.
        """
        last_err = None
        for attempt in (1, 2, 3):
            try:
                if target is None:
                    autotools.make(args=args)
                else:
                    autotools.make(target=target, args=args)
                return
            except Exception as exc:
                last_err = exc
                text = str(exc)
                if _is_oom_text(text) and attempt < 3:
                    self.output.warning(
                        "mdk %s OOM (attempt %d/3), reclaim + retry: %s"
                        % (what, attempt, text[-500:]))
                    try:
                        gc.collect()
                    except Exception:
                        pass
                    time.sleep(15)
                    continue
                raise
        if last_err is not None:
            raise last_err

    def _emit_upstream_test_result(self):
        """Emit the hmbs upstream-test gate marker from automake's real
        test-suite.log counts (parallel-tests harness output), so the numbers
        come from the test framework itself, not from estimates. Searches
        both build and source trees (in-source vs out-of-source)."""
        suite_logs = []
        for _base in (self.build_folder, self.source_folder):
            try:
                if not _base or not os.path.isdir(_base):
                    continue
                for root, _dirs, files in os.walk(_base):
                    if "test-suite.log" in files:
                        _p = os.path.join(root, "test-suite.log")
                        if _p not in suite_logs:
                            suite_logs.append(_p)
            except Exception:
                pass
        if not suite_logs:
            raise ConanException(
                "make check produced no test-suite.log under " + self.build_folder
            )
        with open(suite_logs[0], "r", encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        total = _automake_count(content, "TOTAL")
        passed = _automake_count(content, "PASS")
        xfailed = _automake_count(content, "XFAIL")
        skipped = _automake_count(content, "SKIP")
        failed = (
            _automake_count(content, "FAIL")
            + _automake_count(content, "XPASS")
            + _automake_count(content, "ERROR")
        )
        result = {
            "status": "passed" if failed == 0 else "failed",
            "framework": "automake",
            "command": "make check",
            "discovered": total,
            "executed": total - skipped,
            "passed": passed + xfailed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False)
        )
        if result["status"] != "passed":
            self.output.error(
                "upstream make check did not pass: " + json.dumps(result)
            )

    def _write_install_shim(self):
        """Multi-file install shim for `make install` (Error 64 fix).

        HMBS install shim accepts only single-file two-arg invocations
        (`[ $# -eq 2 ] || exit 64`, EX_USAGE), while automake batches
        both binaries into one `$(INSTALL_PROGRAM) mixasm mixvm DEST`
        call (this round: `install -c mixasm mixvm '.../p//bin'` then
        `make[2]: *** [Makefile:402: install-binPROGRAMS] Error 64`).
        Same family as zurl/1.12.0 notes #35, lzop/1.04 (E098/E174),
        myman/4.0.116 (E182/E188), adms/2.3.7, goffice.
        The shim copies SRC... DEST (DEST may be a directory), parses
        -c/-m/-d only, chmod is best-effort (`|| true`) for
        HMBS_CAP_CHMOD=0. Uses os.open 0o755 so no chmod dependency.
        """
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        os.makedirs(shim_dir, exist_ok=True)
        shim = os.path.join(shim_dir, "install")
        fd = os.open(shim, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
                f.write(
                    "#!/bin/sh\n"
                    "set -eu\n"
                    "mode=\n"
                    "while [ $# -gt 0 ]; do\n"
                    "  case \"$1\" in\n"
                    "    -p|-c) shift ;;\n"
                    "    -m) [ $# -ge 2 ] || exit 2; mode=$2; shift 2 ;;\n"
                    "    -d) shift; [ $# -gt 0 ] || exit 2; mkdir -p \"$@\"; exit 0 ;;\n"
                    "    --) shift; break ;;\n"
                    "    -*) shift ;;\n"
                    "    *) break ;;\n"
                    "  esac\n"
                    "done\n"
                    "[ $# -ge 2 ] || exit 2\n"
                    "dest=\n"
                    "for arg in \"$@\"; do dest=$arg; done\n"
                    "count=$(($# - 1))\n"
                    "if [ \"$count\" -gt 1 ]; then\n"
                    "  mkdir -p \"$dest\"\n"
                    "else\n"
                    "  mkdir -p \"$(dirname \"$dest\")\"\n"
                    "fi\n"
                    "i=1\n"
                    "for src in \"$@\"; do\n"
                    "  [ $i -gt $count ] && break\n"
                    "  cp -f \"$src\" \"$dest\"\n"
                    "  if [ -n \"$mode\" ]; then\n"
                    "    if [ -d \"$dest\" ]; then\n"
                    "      chmod \"$mode\" \"$dest/${src##*/}\" 2>/dev/null || true\n"
                    "    else\n"
                    "      chmod \"$mode\" \"$dest\" 2>/dev/null || true\n"
                    "    fi\n"
                    "  fi\n"
                    "  i=$((i + 1))\n"
                    "done\n"
                )
        except Exception:
            try:
                os.close(fd)
            except Exception:
                pass
            raise
        try:
            os.chmod(shim, 0o755)
        except OSError:
            pass
        return shim

    def _redirect_install_to_shim(self, shim_install):
        """Point generated Makefiles' INSTALL to the multi-file shim.

        automake bakes `INSTALL = <probe>/install -c` at configure time;
        INSTALL_DATA/INSTALL_PROGRAM derive from ${INSTALL}, so redirecting
        INSTALL covers install-binPROGRAMS; any direct INSTALL_DATA/
        INSTALL_PROGRAM/INSTALL_SCRIPT line carrying an absolute /install
        path is redirected as well (zurl/adms precedent). Only Makefile
        file names are touched. Idempotent. OHOS-only caller.
        """
        redirected = 0
        for _dir, _dirs, _files in os.walk(self.build_folder):
            if "Makefile" not in _files:
                continue
            _mp = os.path.join(_dir, "Makefile")
            try:
                with open(_mp, "r", encoding="utf-8",
                          errors="surrogateescape") as _f:
                    _content = _f.read()
            except (OSError, UnicodeDecodeError):
                continue
            if "/install" not in _content and "INSTALL =" not in _content:
                continue
            _lines = []
            _changed = False
            for _line in _content.splitlines(True):
                _stripped = _line.lstrip()
                if _stripped.startswith("INSTALL = ") and "/install" in _stripped:
                    _indent = _line[:len(_line) - len(_stripped)]
                    _lines.append(_indent + "INSTALL = " + shim_install + "\n")
                    _changed = True
                elif (_stripped.startswith("INSTALL_DATA = ")
                      or _stripped.startswith("INSTALL_PROGRAM = ")
                      or _stripped.startswith("INSTALL_SCRIPT = ")) \
                        and "/install" in _stripped:
                    _indent = _line[:len(_line) - len(_stripped)]
                    _key = _stripped.split(" = ", 1)[0]
                    _lines.append(_indent + _key + " = " + shim_install + "\n")
                    _changed = True
                else:
                    _lines.append(_line)
            if _changed:
                try:
                    with open(_mp, "w", encoding="utf-8",
                              errors="surrogateescape", newline="\n") as _f:
                        _f.write("".join(_lines))
                except OSError:
                    continue
                redirected += 1
        if redirected:
            self.output.info(
                "mdk redirected INSTALL to shim in %d Makefile(s)" % redirected)
        else:
            self.output.info("mdk no INSTALL redirect needed")
        return redirected

    def package(self):
        if str(self.settings.os) == "OHOS":
            try:
                _shim = self._write_install_shim()
                self._redirect_install_to_shim(_shim)
            except Exception as _exc:
                self.output.warning("mdk install shim setup skipped: %s" % (_exc,))
        with self._fs_env().vars(self, scope="build").apply():
            Autotools(self).install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        # Application package: consumers use the mixasm/mixvm binaries.
        # mixlib/libmix.a is a noinst convenience library upstream never
        # installs, so no libs/headers are exposed.
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
