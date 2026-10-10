#!/usr/bin/env python3
"""Conan recipe for ifplugd 0.28 (0pointer link-detection daemon, autotools).

Same family as ifmetric 0.3 (same author, same 2004-era autotools):
explicit --build/--host triplets, doc tools disabled, umask relaxed at
build time, single-job make on HMDFS. Native OHOS exec hardening follows
ec16022 0.3.1 precedent: build-local TMPDIR (E002) plus explicit-shell
configure launch (E232).

Dependency note (2026-10-08, temporary): upstream ifplugd mandates
``libdaemon >= 0.5`` via ``PKG_CHECK_MODULES``. The registry package
``libdaemon/0.14`` is published but its recipe has no E002 (writable
TMPDIR) / E232 (verified-shell configure launch) hardening, so any
from-source rebuild dies on drifted workers with
``/data/service/hnp/bin/bash: inaccessible`` (stale profile [buildenv]
SHELL/CONFIG_SHELL) followed by ``C compiler cannot create executables``
at AC_PROG_CC -- the exact signature blocking this package's preflight
since 2026-10-04. A consumer-side SHELL/TMPDIR fix cannot propagate into
a dependency's own generate()/build() (Conan build env is per-package;
deps build first), and single-PR atomicity (W2/JC6) forbids touching
``archives/l/libdaemon`` or ``ci/conan/profiles/ohos-aarch64`` here.
As a temporary unblock, this recipe builds an IDENTICAL upstream
libdaemon 0.14 tarball (same URL + sha256 as
``archives/l/libdaemon/0.14/conandata.yml``) as a private static prefix
used only at build time; nothing extra is packaged or exported. Restore
``self.requires("libdaemon/0.14")`` once libdaemon is re-adapted with
E002/E232 hardening (TODO).
"""
import os
import re
import shutil
import shlex
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class IfplugdConan(ConanFile):
    name = "ifplugd"
    version = "0.28"
    description = "Linux daemon for automatic Ethernet link detection and interface configuration"
    license = "GPL-2.0-or-later"
    homepage = "https://0pointer.de/lennart/projects/ifplugd/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ifplugd needs Linux net ioctls/netlink, got {self.settings.os}"
            )

    # No external requires(): libdaemon 0.14 is bundled privately (see
    # module docstring). Intentionally dependency-free until the registry
    # libdaemon carries E002/E232 hardening.

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        vendor = self._vendor_src()
        get(self, **self.conan_data["vendor_libdaemon"],
            destination=vendor, strip_root=True)
        # E490/E543: HMDFS checks sources out mode 660, autotools helpers lose +x.
        # HMBS reports HMBS_CAP_CHMOD=0 on some workers (chmod ignored); a hard
        # failure here would block an otherwise healthy build, so tolerate it.
        for name in ("configure", "config.guess", "config.sub", "install-sh", "missing", "mkinstalldirs"):
            for root in (self.source_folder, vendor):
                for cur, _dirs, files in os.walk(root):
                    if name in files:
                        path = os.path.join(cur, name)
                        try:
                            os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                        except OSError as exc:
                            self.output.warning(f"chmod +x ignored for {path}: {exc}")

    def _vendor_src(self):
        # Private libdaemon sources live under the ifplugd source tree so the
        # Conan source backup stays self-contained (no cross-folder layout).
        return os.path.join(self.source_folder, "vendor-libdaemon")

    def _private_prefix(self):
        return os.path.join(self.build_folder, "private-prefix")

    def _writable_tmpdir(self):
        # E002: /tmp is read-only (erofs) on HarmonyOS; clang spills temporaries
        # via TMPDIR, so an unset/missing/unwritable TMPDIR makes AC_PROG_CC
        # fail with "C compiler cannot create executables" on a healthy
        # toolchain (precedent: iec16022 0.3.1, coinor-vol 1.5.4 draft).
        # Reuse the HMBS-injected TMPDIR when it is really writable (real
        # open/write/unlink probe; os.access is unreliable on HMDFS per E046),
        # otherwise fall back to a build-local dir the toolchain guarantees.
        candidates = [
            os.environ.get("TMPDIR"),
            os.environ.get("TMP"),
            os.path.join(self.build_folder, "tmp"),
        ]
        for cand in candidates:
            if not cand:
                continue
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".tmp-write-probe")
                with open(probe, "w") as _pf:
                    _pf.write("ok")
                os.unlink(probe)
                return cand
            except OSError:
                continue
        fallback = os.path.join(self.build_folder, "tmp")
        os.makedirs(fallback, exist_ok=True)
        return fallback

    def _working_shell(self):
        # E232/profile staleness: the checked-in profile hardcodes
        # SHELL/CONFIG_SHELL=/data/service/hnp/bin/bash, which the 2026-10
        # preflight reported as "inaccessible or not found" while running
        # libdaemon's configure. Prefer the HMBS-injected SHELL (/bin/sh)
        # and other on-device shells; only use a PATH-resolved bash when the
        # fixed candidates are absent. Existence (not os.access X_OK, broken
        # on HMDFS per E046) is the probe, matching ical2html precedent.
        candidates = [
            os.environ.get("SHELL"),
            os.environ.get("CONFIG_SHELL"),
            "/bin/sh",
            "/system/bin/sh",
            shutil.which("sh"),
            shutil.which("bash"),
        ]
        for cand in candidates:
            if cand and os.path.exists(cand):
                return cand
        return "/bin/sh"

    def _build_jobs(self):
        # Rely on the injected job configuration (HMBS sets
        # tools.build:jobs=1); fall back to single-job for HMDFS FIFO safety
        # (E074) when the conf is absent (e.g. plain local runs).
        try:
            jobs = self.conf.get("tools.build:jobs", default=1)
        except Exception:
            jobs = 1
        try:
            jobs = int(jobs)
        except (TypeError, ValueError):
            jobs = 1
        return jobs if jobs and jobs > 0 else 1

    def _resolve_compiler(self):
        # Profile conf pins tools.build:compiler_executables to
        # /data/service/hnp/bin/clang{,++}. That path is missing or
        # non-functional on some preflight runners (this round:
        # "/bin/sh: /data/service/hnp/bin/clang: inaccessible or not
        # found" at the toolchain pre-probe, Error 127). Existence alone
        # is not enough; the binary must also answer --version.
        # Healthy machine: conf path works -> zero change.
        # Broken machine: discover via PATH + conf-dir siblings, override
        # CC/CXX exports only, never touch CFLAGS/LDFLAGS.
        # Precedent: archives/i/idsgrep/0.6 _resolve_compiler (same
        # fingerprint: "checking for gcc... /data/service/hnp/bin/clang"
        # then "C compiler cannot create executables").
        try:
            conf = self.conf.get("tools.build:compiler_executables") or {}
        except Exception:
            conf = {}
        conf_c = conf.get("c") if isinstance(conf, dict) else None
        conf_cpp = conf.get("cpp") if isinstance(conf, dict) else None

        def _works(exe):
            try:
                if not exe or not os.path.isfile(exe):
                    return False
                p = subprocess.run(
                    [exe, "--version"], capture_output=True,
                    text=True, timeout=15)
                return p.returncode == 0
            except Exception:
                return False

        if conf_c and _works(conf_c):
            self.output.info(
                "ifplugd: conf compiler works as-is: %s" % conf_c)
            return conf_c, conf_cpp
        self.output.warning(
            "ifplugd: conf compiler %s missing or non-functional; "
            "probing PATH fallback" % (conf_c,))
        found_c = None
        found_cpp = None
        for name in ("clang", "clang-15", "cc", "gcc"):
            p = shutil.which(name)
            if p and _works(p):
                found_c = p
                break
        for name in ("clang++", "clang++-15", "c++", "g++"):
            p = shutil.which(name)
            if p and _works(p):
                found_cpp = p
                break
        try:
            conf_dir = os.path.dirname(conf_c) if conf_c else None
        except Exception:
            conf_dir = None
        if conf_dir and os.path.isdir(conf_dir):
            for name in ("clang", "clang++"):
                cand = os.path.join(conf_dir, name)
                if _works(cand):
                    if name == "clang" and not found_c:
                        found_c = cand
                    if name == "clang++" and not found_cpp:
                        found_cpp = cand
        if found_c:
            self.output.info(
                "ifplugd: compiler fallback C=%s CXX=%s "
                "(conf was %s)" % (found_c, found_cpp, conf_c))
            return found_c, found_cpp
        raise ConanException(
            "ifplugd: no working C compiler: conf %s is non-functional "
            "and PATH/sibling probe found none "
            "(clang/clang-15/cc/gcc). Environment fault, not a "
            "recipe bug; needs infra routing." % (conf_c,))

    def _fix_compiler(self):
        # Triple-scope override (idsgrep 0.6 precedent): os.environ plus a
        # rewrite of the generated conanbuild/toolchain scripts that
        # re-export the bad CC/CXX, plus inline CC/CXX assignments on the
        # configure/make command lines (nearest scope wins). Flags
        # untouched. Rounds 5-6 proved an Environment overlay alone never
        # reaches the subprocess: self.run(env="conanbuild") layers the
        # toolchain exports ON TOP of os.environ, so only the script
        # rewrite + inline assignments win over the stale toolchain value.
        cc, cxx = self._resolve_compiler()
        try:
            conf = self.conf.get("tools.build:compiler_executables") or {}
        except Exception:
            conf = {}
        bad_c = conf.get("c") if isinstance(conf, dict) else None
        bad_cpp = conf.get("cpp") if isinstance(conf, dict) else None
        if bad_c and cc != bad_c:
            os.environ["CC"] = cc
            if cxx:
                os.environ["CXX"] = cxx
            for bad, good in ((bad_c, cc), (bad_cpp, cxx)):
                if not bad or not good or bad == good:
                    continue
                try:
                    root = self.build_folder
                except Exception:
                    root = None
                if not root or not os.path.isdir(root):
                    continue
                for dirpath, _dn, filenames in os.walk(root):
                    for name in filenames:
                        if not (name.endswith(".sh") or name.endswith(".mk")
                                or "toolchain" in name
                                or "conanbuild" in name):
                            continue
                        path = os.path.join(dirpath, name)
                        try:
                            with open(path, "r", encoding="utf-8",
                                      errors="ignore", newline="") as f:
                                text = f.read()
                        except OSError:
                            continue
                        if bad in text:
                            try:
                                with open(path, "w", encoding="utf-8",
                                          newline="\n") as f:
                                    f.write(text.replace(bad, good))
                                self.output.info(
                                    "ifplugd: rewrote compiler ref %s -> %s "
                                    "in %s" % (bad, good, path))
                            except OSError:
                                continue
        else:
            self.output.info("ifplugd: keeping conf compiler %s" % cc)
            try:
                if cc:
                    os.environ.setdefault("CC", cc)
                if cxx:
                    os.environ.setdefault("CXX", cxx)
            except Exception:
                pass
        return cc, cxx

    def _find_install_sh(self, roots):
        # Device toybox/HMBS `install -c` fails multi-source header installs
        # with `Error 64` (EX_USAGE); single-file installs pass. Precedent:
        # libnih 1.0.3 (single libnih.h OK, 28 headers via am__base_list ->
        # install-nihincludeHEADERS Error 64, fixed by /bin/sh install-sh -c),
        # lftp 4.9.3 (install-man1 Error 64, _find_install_sh + INSTALL
        # override), openfst E596-C (toybox install -c + chmod unsupported).
        # Prefer the tarball's own install-sh (pure shell, needs no +x when
        # driven as `<shell> install-sh -c`).
        for root in roots:
            if not root or not os.path.isdir(root):
                continue
            for dirpath, _dn, filenames in os.walk(root):
                for name in ("install-sh", "install.sh"):
                    if name in filenames:
                        return os.path.join(dirpath, name)
        return None

    def _patch_install_to_install_sh(self, build_dir, install_sh):
        # Rewrite only the exact `INSTALL = ...` line in every generated
        # Makefile under build_dir to `<verified-shell> <install-sh> -c`.
        # INSTALL_DATA/INSTALL_PROGRAM reference ${INSTALL} and follow
        # automatically; no make-command-line override (spaces would need
        # re-quoting per libnih prohibition). Content and modes unchanged.
        shell = self._working_shell()
        replacement = "%s %s -c" % (shell, install_sh)
        patched = 0
        for dirpath, _dn, filenames in os.walk(build_dir):
            if "Makefile" not in filenames:
                continue
            path = os.path.join(dirpath, "Makefile")
            try:
                with open(path, "r", encoding="utf-8",
                          errors="ignore", newline="") as _f:
                    text = _f.read()
            except OSError:
                continue
            new_text, n = re.subn(r"^INSTALL\s*=.*$",
                                  "INSTALL = %s" % replacement,
                                  text, flags=re.M)
            if n:
                try:
                    with open(path, "w", encoding="utf-8",
                              newline="\n") as _f:
                        _f.write(new_text)
                    patched += 1
                except OSError as exc:
                    self.output.warning(
                        "ifplugd: INSTALL rewrite skipped for %s: %s"
                        % (path, exc))
        self.output.info(
            "ifplugd: INSTALL -> '%s' in %d Makefile(s) under %s"
            % (replacement, patched, build_dir))

    def _patch_conf_install_portable(self, roots):
        # 2026-10-08 preflight package() failure (main tree, after the
        # install-sh INSTALL rewrite): conf/Makefile install-data-local
        # runs `$(INSTALL) -b -D -m755 ...` and dies with
        # `install-sh: -b does not exist` (Error 1 at Makefile:323).
        # Root cause: upstream conf/Makefile.am uses GNU install extensions
        # `-b` (backup) + `-D` (create leading dirs). The device install-sh
        # (2004-era, X11-derived) only supports -c/-d/-m/-o/-g/-s/-t, so the
        # global INSTALL->install-sh rewrite (round 11, needed for toybox
        # `install -c` Error 64 on multi-file installs) breaks exactly these
        # three single-file lines (the only `-b -D` users in the tarball;
        # verified by grep over all Makefile.am/in). Stripping the flags
        # alone is not enough: -D also created ${sysinitdir} and
        # ${sysconfdir}/ifplugd, which automake does NOT auto-create for
        # install-data-local. Fix: `$(INSTALL) -b -D ` -> `$(INSTALL) ` plus
        # one portable `$(mkdir_p) ...` line (mkdir_p is defined in the same
        # Makefile, @mkdir_p@ -> mkdir -p after configure; mkinstalldirs
        # equivalent would also work). `$(INSTALL)` keeps the install-sh
        # `-c` form. Round 18: upstream writes the mode attached
        # (`-m755`/`-m644`, valid for GNU install); the 2004-era install-sh
        # only parses `-m <mode>` with a space (`-m) chmodcmd=... $2`),
        # so `-m755` is treated as a filename (`install-sh: -m755 does not
        # exist`). Normalize to `-m 755`/`-m 644` via regex. Idempotent via
        # the `-b -D`/attached-`-m` absence + mkdir_p presence checks;
        # applied to the pre-configure template (conf/Makefile.in, inherited
        # by config.status) and to the generated conf/Makefile
        # (post-configure + package()).
        patched = 0
        for _root in (roots or []):
            if not _root or not os.path.isdir(_root):
                continue
            for _dirpath, _dn, _filenames in os.walk(_root):
                for _fname in ("Makefile", "Makefile.in", "Makefile.am"):
                    if _fname not in _filenames:
                        continue
                    _path = os.path.join(_dirpath, _fname)
                    try:
                        with open(_path, "r", encoding="utf-8",
                                  errors="ignore", newline="") as _f:
                            _text = _f.read()
                    except OSError:
                        continue
                    if "install-data-local: ifplugd.init" not in _text:
                        continue
                    if ("$(INSTALL) -b -D" not in _text
                            and not re.search(r"\$\(INSTALL\) -m[0-9]",
                                               _text)):
                        continue
                    _orig = _text
                    _text = _text.replace("$(INSTALL) -b -D ",
                                           "$(INSTALL) ")
                    _text = re.sub(r"\$\(INSTALL\) -m(\d)",
                                   r"$(INSTALL) -m \1", _text)
                    _mkdir = ("$(mkdir_p) ${DESTDIR}${sysinitdir} "
                              "${DESTDIR}${sysconfdir}/ifplugd")
                    if _mkdir not in _text:
                        _lines = _text.split("\n")
                        _out = []
                        _inserted = False
                        for _line in _lines:
                            _out.append(_line)
                            if (not _inserted
                                    and _line.strip() ==
                                    "install-data-local: ifplugd.init"):
                                _out.append("\t%s" % _mkdir)
                                _inserted = True
                        if _inserted:
                            _text = "\n".join(_out)
                    if _text != _orig:
                        try:
                            with open(_path, "w", encoding="utf-8",
                                      newline="\n") as _f:
                                _f.write(_text)
                            patched += 1
                            self.output.info(
                                "ifplugd portability patch applied "
                                f"(conf install portable) to {_path}")
                        except OSError as _exc:
                            self.output.warning(
                                "ifplugd conf install patch skipped "
                                f"(unwritable {_path}): {_exc}")
        self.output.info(f"ifplugd conf install portable files: {patched}")

    def _patch_text(self, path, old, new, what):
        # Best-effort text patch with warning (never hard-fail the build when
        # upstream wording already matches, e.g. re-runs over patched trees).
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as _f:
                content = _f.read()
        except OSError as exc:
            self.output.warning(f"private libdaemon patch skipped ({what}): cannot read {path}: {exc}")
            return
        if old not in content:
            self.output.info(f"private libdaemon patch not needed ({what})")
            return
        with open(path, "w", encoding="utf-8", newline="\n") as _f:
            _f.write(content.replace(old, new))
        self.output.info(f"private libdaemon patch applied ({what})")

    def _patch_ifplugd_portability(self):
        # 2026-10-08 preflight compile failure (main ifplugd tree, after the
        # private libdaemon + configure/install-sh/pkg-config rounds):
        #   round 13: src/ethtool-local.h:25: unknown type '__uint32_t'
        #     (plus __uint16_t/__uint8_t) and linux/socket.h:23:
        #     redefinition of 'sockaddr_storage' via nlapi.h.
        #   round 14 (this fix): the round-13 guard-skip approach
        #     (#define _LINUX_SOCKET_H/_UAPI_LINUX_SOCKET_H before
        #     <linux/netlink.h>) removed the redefinition but ALSO hid
        #     __kernel_sa_family_t, which on this OHOS sysroot lives in
        #     <linux/socket.h>: netlink.h:49 and rtnetlink.h:308 then fail
        #     with 'unknown type name __kernel_sa_family_t'. So whole-file
        #     skipping is the wrong scope; the file IS needed, only the one
        #     colliding struct is not.
        # Root causes: __uint32_t et al. are glibc <sys/types.h> internals,
        # absent on the musl/OHOS sysroot; the kernel <linux/socket.h> copy
        # of sockaddr_storage collides with the libc <sys/socket.h> one.
        # Fixes are unconditional and portable (no platform macro, so no
        # PF5 concern): standard <stdint.h> uintN_t types, plus a
        # macro-rename hide -- #define sockaddr_storage to a hidden name
        # around the kernel linux includes so the kernel copy
        # lands under the alias while __kernel_sa_family_t and sockaddr_nl
        # still parse normally (neither netlink header uses sockaddr_storage;
        # verified against the 0.28 tarball). Patched in both the source
        # and build trees because the layout at build time keeps a copy
        # under build_folder/src.
        #   round 15 (this fix): round-14 proved the hide works -- ifplugd.c
        #     (via nlapi.h) now compiles, but the build moved to the NEXT TU
        #     src/interface.c:30, which hits the SAME redefinition through a
        #     different path (<sys/socket.h> then <linux/if.h> ->
        #     <linux/socket.h>) and was never patched because round-14 only
        #     anchored on the linux/types.h+netlink pair in nlapi.h /
        #     ifmonitor.c. Different strategy from round-14's per-file
        #     anchors: a generic TU-wide rule -- any .c/.h including BOTH
        #     <sys/socket.h> and at least one <linux/*.h> gets the hide
        #     opened before its FIRST <linux/> include and closed after its
        #     LAST <linux/> include, covering netlink, if.h, sockios.h,
        #     if_ether.h and any future path in one go.
        #   round 16 (this fix): rounds 13-15 proved compile moves forward
        #     (ifplugd.c then interface.c preprocess OK) but link now dies
        #     with ld.lld duplicate symbol interface_do_message /
        #     interface_auto_up (ifplugd.o vs interface.o). interface.h
        #     carries tentative definitions while ifplugd.c (=1) and
        #     ifplugstatus.c (=0) each define them; interface.c includes the
        #     header. clang-15 defaults to -fno-common so both TUs export
        #     strong symbols (2004 code assumed -fcommon merging). Fixed at
        #     the root with extern declarations in the header (one
        #     definition per binary stays in its main TU) instead of a
        #     -fcommon flag workaround.
        roots = []
        for _root in (getattr(self, "source_folder", None),
                      getattr(self, "build_folder", None)):
            if _root and os.path.isdir(_root) and _root not in roots:
                roots.append(_root)
        found = {"ethtool-local.h": 0, "socket-hide": 0, "interface-extern": 0}
        for _root in roots:
            for _dirpath, _dn, _filenames in os.walk(_root):
                for _name in _filenames:
                    if not (_name.endswith(".c") or _name.endswith(".h")):
                        continue
                    _path = os.path.join(_dirpath, _name)
                    try:
                        with open(_path, "r", encoding="utf-8",
                                  errors="replace", newline="") as _f:
                            _text = _f.read()
                    except OSError as _exc:
                        self.output.warning(
                            "ifplugd portability patch skipped "
                            f"(unreadable {_path}): {_exc}")
                        continue
                    _orig = _text
                    if _name == "interface.h":
                        # Round 16: -fno-common duplicate symbols. Upstream
                        # interface.h carries tentative definitions
                        # (int interface_auto_up; int interface_do_message;)
                        # while ifplugd.c defines them (=1) and
                        # ifplugstatus.c defines them (=0); interface.c
                        # includes the header, so with clang-15 default
                        # -fno-common both ifplugd.o and interface.o export
                        # strong symbols -> ld.lld duplicate symbol at link
                        # (2004-era code assumed -fcommon merging). Fix at
                        # the root: declare extern in the header, leaving
                        # exactly one definition per binary in its main TU.
                        # Portable, no platform macro, no flag dependency.
                        # Idempotent via the extern check.
                        if ("extern int interface_auto_up" not in _text
                                or "extern int interface_do_message"
                                not in _text):
                            # Newline-anchored so an already-extern line
                            # never matches again (idempotent even without
                            # the guard above).
                            _text = _text.replace(
                                "\nint interface_auto_up;",
                                "\nextern int interface_auto_up;")
                            _text = _text.replace(
                                "\nint interface_do_message;",
                                "\nextern int interface_do_message;")
                        if _text != _orig:
                            try:
                                with open(_path, "w", encoding="utf-8",
                                          newline="\n") as _f:
                                    _f.write(_text)
                                found["interface-extern"] += 1
                                self.output.info(
                                    "ifplugd portability patch applied "
                                    f"(interface extern) to {_path}")
                            except OSError as _exc:
                                self.output.warning(
                                    "ifplugd portability patch skipped "
                                    f"(unwritable {_path}): {_exc}")
                        continue
                    if _name == "ethtool-local.h":
                        if "#include <stdint.h>" not in _text:
                            _text = _text.replace(
                                "typedef unsigned long long u64;",
                                "#include <stdint.h>\n\n"
                                "typedef unsigned long long u64;",
                                1)
                        _text = _text.replace("__uint32_t", "uint32_t")
                        _text = _text.replace("__uint16_t", "uint16_t")
                        _text = _text.replace("__uint8_t", "uint8_t")
                        if _text != _orig:
                            try:
                                with open(_path, "w", encoding="utf-8",
                                          newline="\n") as _f:
                                    _f.write(_text)
                                found["ethtool-local.h"] += 1
                                self.output.info(
                                    "ifplugd portability patch applied to "
                                    f"{_path}")
                            except OSError as _exc:
                                self.output.warning(
                                    "ifplugd portability patch skipped "
                                    f"(unwritable {_path}): {_exc}")
                        continue
                    # Generic socket-hide: needs BOTH the libc socket header
                    # and at least one kernel linux header in the same TU.
                    # Idempotent via the hidden-marker check.
                    if "__hmbs_hidden_sockaddr_storage" in _text:
                        continue
                    if "#include <sys/socket.h>" not in _text:
                        continue
                    _lines = _text.split("\n")
                    _sock = next(
                        (_i for _i, _l in enumerate(_lines)
                         if _l.strip() == "#include <sys/socket.h>"),
                        None)
                    _linux = [_i for _i, _l in enumerate(_lines)
                              if _l.strip().startswith("#include <linux/")]
                    if not _linux:
                        continue
                    # Open the hide after the libc header so the libc copy
                    # keeps its real name; only kernel copies land under the
                    # alias. (interface.c has linux/sockios.h + if_ether.h
                    # BEFORE sys/socket.h -- those pull no socket header, so
                    # leaving them outside is correct; the collider,
                    # linux/if.h, sits after.)
                    _after = [_i for _i in _linux
                              if _sock is not None and _i > _sock]
                    _first = min(_after) if _after else min(_linux)
                    _last = max(_linux)
                    _hide_open = (
                        "/* HMBS portability: <linux/socket.h> (pulled in by "
                        "<linux/netlink.h>/<linux/if.h>) redefines struct "
                        "sockaddr_storage from <sys/socket.h> on musl/OHOS "
                        "sysroots, but it also provides __kernel_sa_family_t "
                        "needed below, so the file must still parse. Hide "
                        "only the colliding struct under an alias; the "
                        "kernel headers here never use sockaddr_storage. "
                        "Portable, no platform macro. */\n"
                        "#define sockaddr_storage "
                        "__hmbs_hidden_sockaddr_storage")
                    _hide_close = "#undef sockaddr_storage"
                    _lines.insert(_first, _hide_open)
                    # _last shifts by the one inserted line above it.
                    _lines.insert(_last + 2, _hide_close)
                    _text = "\n".join(_lines)
                    if _text != _orig:
                        try:
                            with open(_path, "w", encoding="utf-8",
                                      newline="\n") as _f:
                                _f.write(_text)
                            found["socket-hide"] += 1
                            self.output.info(
                                f"ifplugd portability patch applied to "
                                f"{_path}")
                        except OSError as _exc:
                            self.output.warning(
                                "ifplugd portability patch skipped "
                                f"(unwritable {_path}): {_exc}")
        self.output.info(f"ifplugd portability patch files: {found}")

    def _dump_config_log(self, build_dir, label):
        # Bounded self-diagnosis: on configure failure print the effective
        # compiler env plus the config.log tail to preflight stdout, so the
        # next round sees the REAL compiler error (stale sysroot flag, moved
        # SDK, lld loader issue, unwritable tmpdir, ...) instead of guessing
        # from the one-line "cannot create executables". Never fails itself.
        # Returns the tail text so callers can embed it in the raised
        # exception message (exception text is never summarised away, while
        # plain stdout lines may be omitted from focused digests).
        try:
            self.output.info(
                f"{label} env: CC={os.environ.get('CC')} "
                f"CXX={os.environ.get('CXX')} "
                f"CFLAGS={os.environ.get('CFLAGS')} "
                f"LDFLAGS={os.environ.get('LDFLAGS')}"
            )
            self.output.info(
                f"{label} env: SHELL={os.environ.get('SHELL')} "
                f"CONFIG_SHELL={os.environ.get('CONFIG_SHELL')} "
                f"TMPDIR={os.environ.get('TMPDIR')}"
            )
        except Exception:
            pass
        cand = os.path.join(build_dir, "config.log")
        try:
            with open(cand, "r", encoding="utf-8", errors="replace") as _f:
                lines = _f.read().splitlines()
        except OSError:
            self.output.info(f"{label}: no config.log under {build_dir}")
            return f"no config.log under {build_dir}"
        tail = lines[-60:]
        self.output.info(f"{label}: ---- {cand} last {len(tail)}/{len(lines)} lines ----")
        for _line in tail:
            self.output.info(f"{label}: {_line}"[:1500])
        return "\n".join(_line[:500] for _line in tail[-40:])

    def _private_configure_args(self, prefix):
        # Explicit triplets bypass the 2008-era config.guess, which cannot
        # recognise HarmonyOS (UNAME_SYSTEM=HarmonyOS -> "unable to guess
        # system type" -> "cannot guess build type"). Verified empirically
        # against the vendored tarball's own config.sub (2008-01-23):
        #   sh config.sub aarch64-unknown-linux-gnu  -> OK (canonicalises)
        #   sh config.sub aarch64-unknown-linux-ohos -> RC=1, machine
        #   `aarch64-unknown-linux' not recognized (exactly this round's
        #   preflight error, after the previous round's ohos triplets).
        # So the private build uses linux-gnu triplets, which the old
        # script accepts verbatim -- no config.sub patching required.
        # This is behaviour-neutral here: libdaemon 0.14 configure.ac has
        # no host_os-dependent branches (only generic AC_CHECK_HEADERS /
        # AC_CHECK_FUNCS / AC_FUNC_* probes), build==host keeps
        # cross_compiling=no so every probe compiles+links+runs natively,
        # and OS defines come from the OHOS-targeting device clang, not
        # from the triplet string. The result is a native static archive
        # consumed only via build-scope PKG_CONFIG_PATH; nothing triplet
        # -derived is exported.
        return (
            f"--prefix={prefix} "
            "--build=aarch64-unknown-linux-gnu "
            "--host=aarch64-unknown-linux-gnu "
            "--enable-static --disable-shared"
        )

    def _pkg_config_shim_dir(self):
        return os.path.join(self.build_folder, "pkgconfig-shim")

    def _pkg_config_shim_path(self):
        return os.path.join(self._pkg_config_shim_dir(), "pkg-config")

    def _ensure_pkg_config_shim(self):
        # This round's blocker: ifplugd configure dies in PKG_CHECK_MODULES
        # with "The pkg-config script could not be found or is too old"
        # because the preflight worker has no pkg-config/pkgconf binary on
        # PATH (HMBS_BUILD_TOOLS only probes cmake/make/ninja/python3).
        # Only libdaemon is queried (configure.ac has no other PKG_CHECK),
        # and its .pc lives in the private static prefix, so ship a minimal
        # pure-shell pkg-config shim answering libdaemon from that prefix.
        # Hermetic by design: no tool_requires edge (pkgconf/2.5.1 would pull
        # a Meson chain rebuild when its OHOS binary is absent from the
        # remote). Unknown modules exit 1 so configure fails honestly
        # instead of linking wrong flags.
        # chmod-proof: configure is driven via PKG_CONFIG="sh <shim>", so a
        # +x bit ignored under HMBS_CAP_CHMOD=0 never blocks exec.
        prefix = self._private_prefix()
        shim_dir = self._pkg_config_shim_dir()
        shim = self._pkg_config_shim_path()
        try:
            os.makedirs(shim_dir, exist_ok=True)
        except OSError as exc:
            self.output.warning(f"ifplugd: pkg-config shim dir skipped: {exc}")
            return shim
        script = r'''#!/bin/sh
# HMBS pkg-config shim for ifplugd 0.28 (build-local, private libdaemon only).
# Answers queries for the private libdaemon prefix; any other module exits 1
# so configure fails honestly instead of linking wrong flags.
HMBS_PREFIX="__HMBS_PRIVATE_PREFIX__"
HMBS_PCFILE="$HMBS_PREFIX/lib/pkgconfig/libdaemon.pc"
WANT_CFLAGS=0
WANT_LIBS=0
WANT_MODVERSION=0
WANT_VARIABLE=""
WANT_EXISTS_ONLY=1
MODULES=""
for _hmbs_arg in "$@"; do
    case "$_hmbs_arg" in
        --atleast-pkgconfig-version*)
            exit 0
            ;;
        --version)
            echo "0.29.2"
            exit 0
            ;;
        --cflags)
            WANT_CFLAGS=1
            WANT_EXISTS_ONLY=0
            ;;
        --libs*)
            WANT_LIBS=1
            WANT_EXISTS_ONLY=0
            ;;
        --static)
            ;;
        --modversion)
            WANT_MODVERSION=1
            WANT_EXISTS_ONLY=0
            ;;
        --variable=*)
            WANT_VARIABLE="$_hmbs_arg"
            WANT_EXISTS_ONLY=0
            ;;
        --exists|--print-errors|--short-errors|--silence-errors|--errors-to-stdout)
            ;;
        --define-variable=*|--print-variables|--print-provides|--print-requires*)
            WANT_EXISTS_ONLY=0
            ;;
        --*)
            ;;
        *)
            MODULES="$MODULES $_hmbs_arg"
            ;;
    esac
done
case "$MODULES" in
    *libdaemon*)
        ;;
    *)
        echo "hmbs pkg-config shim: unsupported module(s):$MODULES (only private libdaemon is provided)" >&2
        exit 1
        ;;
esac
if [ ! -f "$HMBS_PCFILE" ]; then
    echo "hmbs pkg-config shim: $HMBS_PCFILE not installed yet" >&2
    exit 1
fi
if [ "$WANT_MODVERSION" = "1" ]; then
    _hmbs_ver=$(grep '^Version:' "$HMBS_PCFILE" | head -n 1 | cut -d: -f2 | tr -d ' \t\r\n')
    if [ -z "$_hmbs_ver" ]; then
        _hmbs_ver="0.14"
    fi
    echo "$_hmbs_ver"
    exit 0
fi
if [ -n "$WANT_VARIABLE" ]; then
    case "$WANT_VARIABLE" in
        --variable=prefix) echo "$HMBS_PREFIX" ;;
        --variable=libdir) echo "$HMBS_PREFIX/lib" ;;
        --variable=includedir) echo "$HMBS_PREFIX/include" ;;
        *) echo "$HMBS_PREFIX" ;;
    esac
    exit 0
fi
if [ "$WANT_EXISTS_ONLY" = "1" ]; then
    exit 0
fi
_hmbs_out=""
if [ "$WANT_CFLAGS" = "1" ]; then
    _hmbs_out="$_hmbs_out -I$HMBS_PREFIX/include"
fi
if [ "$WANT_LIBS" = "1" ]; then
    _hmbs_out="$_hmbs_out -L$HMBS_PREFIX/lib -ldaemon"
fi
echo "$_hmbs_out" | sed 's/^ //'
exit 0
'''.replace("__HMBS_PRIVATE_PREFIX__", prefix).replace(chr(92) + chr(34), chr(34))
        # Unescape \" -> " (the template above is a raw string, so shell
        # quoting was written escaped; the .pc grep/tr sequences keep
        # their single backslashes untouched).
        try:
            with open(shim, "w", encoding="utf-8", newline="\n") as _f:
                _f.write(script)
        except OSError as exc:
            self.output.warning(f"ifplugd: pkg-config shim write skipped: {exc}")
            return shim
        try:
            os.chmod(shim, os.stat(shim).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        except OSError as exc:
            self.output.warning(f"chmod +x ignored for {shim}: {exc}")
        self.output.info(f"ifplugd: pkg-config shim ready: {shim} (prefix {prefix})")
        return shim

    def generate(self):
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        # Upstream configure was generated by autoconf 2.59 whose config.sub
        # cannot canonicalise an aarch64 OHOS host, so both triples are explicit.
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # Doc-only tools: configure hard-aborts (AC_MSG_ERROR) when lynx is
        # missing; xmltoman/subversion only gate doc/man rebuild. Neither
        # affects the compiled binaries, so all are turned off.
        tc.configure_args.append("--disable-lynx")
        tc.configure_args.append("--disable-xmltoman")
        tc.configure_args.append("--disable-subversion")
        # Upstream requires --with-initdir (defaults probe /etc/init.d which
        # does not exist on OHOS); install the init script under the package
        # prefix so `make install` stays staged and relocatable.
        tc.configure_args.append("--with-initdir=${prefix}/etc/init.d")
        # AC_FUNC_MALLOC cross-compile false positive would substitute
        # rpl_malloc (undefined at link). Seed the cache to use real malloc.
        tc.configure_args.append("ac_cv_func_malloc_0_nonnull=yes")
        tc.configure_args.append("ac_cv_func_realloc_0_nonnull=yes")
        tc.generate()
        # E002 + E232 (precedent: iec16022 0.3.1 generate()/build()):
        # TMPDIR reuses the HMBS-injected value when writable, else a
        # build-local dir; SHELL/CONFIG_SHELL override the stale profile
        # value (/data/service/hnp/bin/bash, "inaccessible" in 2026-10
        # preflight) with a verified on-device shell. Build scope: these
        # are consumed by configure/compiler tempfiles at build time.
        # PKG_CONFIG_PATH exposes the private libdaemon prefix to ifplugd's
        # PKG_CHECK_MODULES probe (no external PkgConfigDeps anymore).
        shell = self._working_shell()
        tmpdir = self._writable_tmpdir()
        self.output.info(f"ifplugd configure shell: {shell} TMPDIR={tmpdir}")
        env = Environment()
        env.define("SHELL", shell)
        env.define("CONFIG_SHELL", shell)
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        pkgconfig_dir = os.path.join(self._private_prefix(), "lib", "pkgconfig")
        env.define("PKG_CONFIG_PATH", pkgconfig_dir)
        # No pkg-config binary on preflight workers (this round's
        # PKG_CHECK_MODULES failure); drive configure via the build-local
        # shim. "sh <shim>" form needs no +x bit (HMBS_CAP_CHMOD=0 safe).
        # LIBDAEMON_* preset is belt-and-suspenders: pkg.m4 honors preset
        # _CFLAGS/_LIBS and it pins the flags even if a future probe
        # bypasses the shim.
        try:
            _shim = self._ensure_pkg_config_shim()
        except Exception as exc:
            _shim = self._pkg_config_shim_path()
            self.output.warning(f"ifplugd: pkg-config shim ensure failed: {exc}")
        _prefix = self._private_prefix()
        env.define("PKG_CONFIG", "sh %s" % _shim)
        env.define("LIBDAEMON_CFLAGS", "-I%s" % os.path.join(_prefix, "include"))
        env.define("LIBDAEMON_LIBS", "-L%s -ldaemon" % os.path.join(_prefix, "lib"))
        env.append_path("PATH", self._pkg_config_shim_dir())
        env.vars(self, scope="build").save_script("conanbuild_hmbs_shell_tmpdir")

    def _build_private_libdaemon(self, autotools):
        # Build the vendored libdaemon 0.14 (identical upstream tarball) as a
        # private STATIC prefix. Mirrors the hardening of archives/l/libdaemon
        # 0.14 plus this recipe's E002/E232 handling; see module docstring.
        # The configure uses native minimal args (see
        # _private_configure_args) and runs out-of-source in private-build.
        vendor = self._vendor_src()
        configure = os.path.join(vendor, "configure")
        if not os.path.isfile(configure):
            raise ConanInvalidConfiguration(
                f"vendored libdaemon sources missing configure: {vendor}"
            )
        # Same umask relaxation as ifplugd itself (HMDFS setgid scratch dirs).
        self._patch_text(configure, "umask 077", "umask 022", "umask")
        # No config.sub patching: _private_configure_args uses linux-gnu
        # triplets, which the vendored 2008 script accepts verbatim
        # (verified with the tarball's own config.sub).
        # Same include fix as libdaemon patch 0004 (OHOS lacks sys/unistd.h);
        # examples are not installed but a broken compile would still fail make.
        testd = os.path.join(vendor, "examples", "testd.c")
        if os.path.isfile(testd):
            self._patch_text(testd, "sys/unistd.h", "unistd.h", "testd include")
        shell = self._working_shell()
        prefix = self._private_prefix()
        priv_build = os.path.join(self.build_folder, "private-build")
        # HMDFS forces setgid on new directories; create ours under a
        # relaxed umask so conftest writes never hit E011-style
        # drwx--S--- denials (probe source + scratch files live here).
        old_umask = os.umask(0o022)
        try:
            os.makedirs(prefix, exist_ok=True)
            os.makedirs(priv_build, exist_ok=True)
        finally:
            os.umask(old_umask)
        args = self._private_configure_args(prefix)
        make = os.environ.get("HMBS_MAKE") or shutil.which("make") or "make"
        jobs = self._build_jobs()
        # Toolchain drift fallback (idsgrep 0.6 precedent): the profile pins
        # CC to /data/service/hnp/bin/clang, which this round reports as
        # "inaccessible or not found" (Error 127 at the pre-probe). Rounds
        # 5-6 proved an Environment overlay alone never wins: self.run with
        # env="conanbuild" layers toolchain exports ON TOP of os.environ, so
        # only the generated-script rewrite (_fix_compiler) + inline CC/CXX
        # assignments (nearest scope) reach the subprocess. Flags untouched.
        cc, cxx = self._fix_compiler()
        inline_cc = ""
        if cc:
            inline_cc += shlex.quote("CC=" + cc) + " "
        if cxx:
            inline_cc += shlex.quote("CXX=" + cxx) + " "
        environment = Environment()
        environment.define("SHELL", shell)
        environment.define("CONFIG_SHELL", shell)
        tmpdir = self._writable_tmpdir()
        environment.define("TMPDIR", tmpdir)
        environment.define("TMP", tmpdir)
        self.output.info(f"private libdaemon: shell={shell} TMPDIR={tmpdir} prefix={prefix} args={args} CC={cc} CXX={cxx}")
        with environment.vars(self).apply():
            # Pre-probe with the SAME env configure will see: compile and
            # run a trivial program via $CC (inline CC= wins over the stale
            # toolchain export when drifted, no-op when healthy). A failure
            # here means no usable compiler exists (not this old configure
            # script); success isolates the fault to configure itself.
            probe_c = os.path.join(priv_build, "hmbs_cc_probe.c")
            with open(probe_c, "w", encoding="utf-8", newline="\n") as _pf:
                _pf.write("int main(void){return 0;}\n")
            try:
                self.run(inline_cc + 'echo "HMBS_CC_PROBE_ENV: CC=$CC CXX=$CXX SHELL=$SHELL TMPDIR=$TMPDIR" && $CC -o hmbs_cc_probe hmbs_cc_probe.c && ./hmbs_cc_probe && echo HMBS_CC_PROBE_PASS', cwd=priv_build, env="conanbuild")
            except Exception as exc:
                tail = self._dump_config_log(priv_build, "private-libdaemon-probe")
                raise ConanException(
                    f"private libdaemon: toolchain pre-probe failed before configure: {exc}\n"
                    f"CONFIG_LOG_TAIL:\n{tail}"
                )
            try:
                self.run(inline_cc + f'"{shell}" "{configure}" {args}', cwd=priv_build, env="conanbuild")
            except Exception as exc:
                tail = self._dump_config_log(priv_build, "private-libdaemon")
                raise ConanException(
                    f"private libdaemon configure failed: {exc}\n"
                    f"CONFIG_LOG_TAIL:\n{tail}"
                )
            # Device install fix (libnih/lftp/openfst precedent): generated
            # Makefiles probe INSTALL to the HMBS/toybox `install -c`, which
            # fails multi-header installs with Error 64 (this round:
            # install-pkgincludeHEADERS with 7 headers). Rewrite INSTALL to
            # the vendored install-sh driven via the verified shell before
            # any make/install runs. Single scope: priv_build only.
            _inst = self._find_install_sh([vendor, priv_build])
            if _inst:
                self._patch_install_to_install_sh(priv_build, _inst)
            else:
                self.output.warning(
                    "private libdaemon: install-sh not found; "
                    "keeping probed INSTALL (multi-header install may fail "
                    "with Error 64)")
            self.run(inline_cc + f'"{make}" -j{jobs}', cwd=priv_build, env="conanbuild")
            self.run(inline_cc + f'"{make}" install', cwd=priv_build, env="conanbuild")
        pc = os.path.join(prefix, "lib", "pkgconfig", "libdaemon.pc")
        if not os.path.isfile(pc):
            raise ConanInvalidConfiguration(
                f"private libdaemon install produced no pkg-config file: {pc}"
            )
        self.output.info(f"private libdaemon ready: {pc}")

    def build(self):
        apply_conandata_patches(self)
        self._patch_ifplugd_portability()
        # conf/ install-data-local uses GNU `install -b -D`, which the
        # install-sh INSTALL rewrite cannot run (round 17). Patch the
        # pre-configure template now so config.status inherits the portable
        # form; the generated conf/Makefile is patched again post-configure.
        try:
            self._patch_conf_install_portable([self.source_folder])
        except Exception as exc:
            self.output.warning(f"ifplugd conf pre-configure patch skipped: {exc}")
        # The pkg-config shim file must exist before either configure runs,
        # even if generate() was cached from a previous revision.
        try:
            self._ensure_pkg_config_shim()
        except Exception as exc:
            self.output.warning(f"ifplugd: pkg-config shim ensure failed: {exc}")
        # E011/E114: configure's generated config.status creates its scratch
        # dir with "(umask 077 && mktemp -d ./confstatXXXXXX)". HMDFS forces
        # setgid on new directories, yielding drwx--S--- which even the owner
        # cannot write into. Relax to 022, keeping real temp-dir creation
        # (precedent: ifmetric 0.3, iec16022 0.3.1 patches/0003).
        replace_in_file(
            self,
            os.path.join(self.source_folder, "configure"),
            "umask 077",
            "umask 022",
        )
        # Private dependency first (build-time only, never packaged).
        autotools = Autotools(self)
        self._build_private_libdaemon(autotools)
        # E232 (precedent: iec16022 0.3.1 build()): on a native HarmonyOS
        # build host the source `configure` cannot be launched via its
        # shebang (refused before Autoconf starts; CONFIG_SHELL alone cannot
        # help). Drive it through the verified shell instead, keeping
        # autotools._configure_args authoritative. Keyed on settings_build
        # (the executor), not settings (the target).
        build_os = str(getattr(self, "settings_build", self.settings).os)
        if build_os == "OHOS":
            shell = self._working_shell()
            configure = os.path.join(self.source_folder, "configure")
            # Same drift fallback as the private build: inline CC/CXX wins
            # over the stale toolchain export when the profile compiler
            # moved; no-op when healthy. Flags untouched.
            _cc, _cxx = self._fix_compiler()
            _inline = ""
            if _cc:
                _inline += shlex.quote("CC=" + _cc) + " "
            if _cxx:
                _inline += shlex.quote("CXX=" + _cxx) + " "
            _jobs = self._build_jobs()
            _make = os.environ.get("HMBS_MAKE") or shutil.which("make") or "make"
            environment = Environment()
            environment.define("SHELL", shell)
            environment.define("CONFIG_SHELL", shell)
            # Same pkg-config shim as generate(): re-ensure the file here so
            # a cached generate() can never leave configure without it, and
            # mirror the build-scope exports in this overlay (nearest scope
            # wins for the manual self.run below).
            try:
                _main_shim = self._ensure_pkg_config_shim()
            except Exception as exc:
                _main_shim = self._pkg_config_shim_path()
                self.output.warning(f"ifplugd: pkg-config shim ensure failed: {exc}")
            _main_prefix = self._private_prefix()
            environment.define("PKG_CONFIG", "sh %s" % _main_shim)
            environment.define("PKG_CONFIG_PATH", os.path.join(_main_prefix, "lib", "pkgconfig"))
            environment.define("LIBDAEMON_CFLAGS", "-I%s" % os.path.join(_main_prefix, "include"))
            environment.define("LIBDAEMON_LIBS", "-L%s -ldaemon" % os.path.join(_main_prefix, "lib"))
            environment.append_path("PATH", self._pkg_config_shim_dir())
            try:
                with environment.vars(self).apply():
                    # env="conanbuild" carries the toolchain CFLAGS/
                    # LDFLAGS (helper-equivalent env); inline CC/CXX only
                    # swaps the compiler binary.
                    self.run(_inline + f'"{shell}" "{configure}" {autotools._configure_args}', env="conanbuild")
            except Exception as exc:
                tail = self._dump_config_log(self.build_folder, "ifplugd")
                raise ConanException(
                    f"ifplugd configure failed: {exc}\n"
                    f"CONFIG_LOG_TAIL:\n{tail}"
                )
            # Same device install fix as the private build: rewrite INSTALL
            # to the source install-sh so `make install` (build + package
            # steps) never hits toybox `install -c` Error 64.
            _main_inst = self._find_install_sh(
                [self.source_folder, self.build_folder])
            if _main_inst:
                self._patch_install_to_install_sh(self.build_folder,
                                                   _main_inst)
            self._patch_conf_install_portable([self.build_folder])
            # Inline CC/CXX for make as well so the fallback compiler is
            # used even if a generated script still re-exports the bad path.
            # Job count comes from the injected tools.build:jobs conf
            # (HMBS sets 1); explicit -j keeps single-job HMDFS safety.
            self.run(_inline + f'"{_make}" -j{_jobs}', cwd=self.build_folder, env="conanbuild")
        else:
            try:
                autotools.configure()
            except Exception as exc:
                tail = self._dump_config_log(self.build_folder, "ifplugd")
                raise ConanException(
                    f"ifplugd configure failed: {exc}\n"
                    f"CONFIG_LOG_TAIL:\n{tail}"
                )
            _main_inst = self._find_install_sh(
                [self.source_folder, self.build_folder])
            if _main_inst:
                self._patch_install_to_install_sh(self.build_folder,
                                                   _main_inst)
            self._patch_conf_install_portable([self.build_folder])
            # Job count comes from the injected tools.build:jobs conf
            # (HMBS sets 1); plain helper call avoids duplicating -j flags.
            autotools.make()
        # Upstream 0.28 ships no test entry point: no TESTS/check_PROGRAMS in
        # any Makefile.am, no tests/ dir, no `make check` cases. See notes.md
        # and test_package/MANIFEST.yml audit; nothing is executed here.

    def package(self):
        # Defensive re-apply (idempotent): package() may run against
        # Makefiles regenerated after build()'s rewrite; ensure INSTALL
        # still points at install-sh before `make install`.
        try:
            _pkg_inst = self._find_install_sh(
                [self.source_folder, self.build_folder])
            if _pkg_inst and os.path.isdir(self.build_folder):
                self._patch_install_to_install_sh(self.build_folder,
                                                   _pkg_inst)
            self._patch_conf_install_portable([self.build_folder])
        except Exception as exc:
            self.output.warning(f"ifplugd package INSTALL rewrite skipped: {exc}")
        autotools = Autotools(self)
        autotools.install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        # Upstream installs sbin_PROGRAMS; Conan's AutotoolsToolchain maps
        # sbindir to <package>/bin. Declare both layouts for robustness.
        self.cpp_info.bindirs = ["bin", "sbin"]
        for d in self.cpp_info.bindirs:
            self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, d))
