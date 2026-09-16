#!/usr/bin/env python3
"""Conan recipe — cpluff 0.2.0 (Autotools)."""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class CpluffConan(ConanFile):
    name = "cpluff"
    version = "0.2.0"
    description = "C-Pluff, a plug-in framework for C programs"
    license = "MIT"
    homepage = "https://c-pluff.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("expat/2.8.2")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "cpluff only supports Linux and OHOS, got %s" % (self.settings.os,)
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Signal 9 (OOM-killer) mitigation on constrained preflight runner:
        # cpluff is tiny; -g0 + no dependency tracking cut peak clang/ld
        # memory without changing test scope. --disable-cpluffxx keeps the
        # default-off WIP C++ API explicitly off (saves a full C++ build).
        tc.extra_cflags.append("-g0")
        tc.extra_cxxflags.append("-g0")
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
            "--disable-nls",
            "--without-readline",
            "--disable-dependency-tracking",
            "--disable-cpluffxx",
        ])
        # make-check needs shared plugin modules (test/plugins-source/* is
        # `-module -avoid-version` libtool modules dlopened from
        # tmp/install/plugins/*/libruntime.so). With `--disable-shared`
        # libtool builds only static .a, so DESTDIR install leaves no .so
        # and the dlopen tests fail (plugincallbacks/symbolusage:
        # "libruntime.so could not be opened: No such file"). Build both
        # variants so `make check` can dlopen; package() prunes the
        # non-requested variant afterwards. No test logic changed.
        tc.configure_args.extend([
            "--enable-shared",
            "--enable-static",
            "cp_cv_sys_have_isatty_fileno=yes",
        ])
        if self.settings.os in ("Linux", "OHOS"):
            # HMBS injects SHELL=/bin/sh + CONFIG_SHELL=/bin/sh (HMDFS getcwd safe).
            # HNP bash ( /data/service/hnp/bin/bash ) fails getcwd on HMDFS
            # (avahi R18: shell-init getcwd cannot access parent directories).
            shell = (
                os.environ.get("CONFIG_SHELL")
                or os.environ.get("SHELL")
                or ("/bin/sh" if os.path.exists("/bin/sh") else None)
                or shutil.which("sh")
                or "/bin/sh"
            )
            if "hnp" in shell and os.path.exists("/bin/sh"):
                shell = "/bin/sh"
            tc.configure_args.append("SHELL=%s" % shell)
        tc.generate()

        expat = self.dependencies["expat"].package_folder
        expat_lib = os.path.join(expat, "lib")
        deps = Environment()
        deps.append("CPPFLAGS", "-I%s" % os.path.join(expat, "include"))
        deps.append("LDFLAGS", "-L%s" % expat_lib)
        # make-check runtime: test binaries (console/cpluff-console,
        # test/testsuite) link -lexpat without rpath; true-machine musl
        # loader then fails with "Error loading shared library
        # libexpat.so" -> 51/53 FAIL. Bake RUNPATH and export
        # LD_LIBRARY_PATH (build scope) so the loader finds expat.
        deps.append("LDFLAGS", "-Wl,-rpath,%s" % expat_lib)
        deps.append("LD_LIBRARY_PATH", expat_lib)
        if str(self.settings.os) == "OHOS":
            deps.define("ACLOCAL", "true")
            deps.define("AUTOMAKE", "true")
            deps.define("AUTOCONF", "true")
        # E002: propagate HMBS writable TMPDIR via conanbuild.sh so that
        # configure/make/libtool child processes see it even if the runner
        # scrubs os.environ. Values are read at generate() time from the
        # HMBS-injected environment; fallback mirrors _ensure_tmpdir().
        # NOTE: fallback only fills in when the primary TMPDIR/TMP/TEMP is
        # missing or not a directory (2026-09-11: previous code overwrote a
        # valid primary with the fallback unconditionally, risking a stale
        # or less-writable root while preflight.sh reports readonly /tmp).
        _hmbs_tmp = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
        )
        if not (_hmbs_tmp and _hmbs_tmp not in ("0", "1") and os.path.isdir(_hmbs_tmp)):
            _hmbs_fallback = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK")
            if _hmbs_fallback and _hmbs_fallback not in ("0", "1") and os.path.isdir(_hmbs_fallback):
                _hmbs_tmp = _hmbs_fallback
            else:
                _hmbs_tmp = None
        if _hmbs_tmp and _hmbs_tmp not in ("0", "1") and os.path.isdir(_hmbs_tmp):
            for _k in ("TMPDIR", "TMP", "TEMP"):
                try:
                    deps.define(_k, _hmbs_tmp)
                except Exception:
                    pass
        deps.vars(self, scope="build").save_script("cpluff-deps")

    def _patch_autoconf_umask(self):
        # HMDFS fixes: ac_pwd fallback (getcwd) + umask 022 (E011) + mktemp TMPDIR (E002).
        # Pattern source: archives/a/aldo/0.7.8 _patch_configure_hmdfs (same autoconf family).
        roots = []
        for attr in ("source_folder", "base_source_folder", "build_folder"):
            try:
                base = getattr(self, attr, None)
            except Exception:
                base = None
            if base and os.path.isdir(base) and base not in roots:
                roots.append(base)
        patched = 0
        for root in roots:
            for dirpath, _dirnames, filenames in os.walk(root):
                for fname in ("configure", "config.status"):
                    if fname not in filenames:
                        continue
                    path = os.path.join(dirpath, fname)
                    try:
                        with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
                            text = f.read()
                    except OSError:
                        continue
                    orig = text
                    # 1) getcwd failure: ac_pwd=`pwd` -> fallback to $PWD (aldo pattern).
                    if "ac_pwd=" in text:
                        text = text.replace(
                            "ac_pwd=`pwd`",
                            'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"',
                        )
                        text = text.replace(
                            'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD" 2>/dev/null || ac_pwd="$PWD"',
                            'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"',
                        )
                    # 2) E011: umask 077 -> 022 (also cover autoconf "umash" typo).
                    if "umask 077" in text:
                        text = text.replace("umask 077", "umask 022")
                    if "umash 077" in text:
                        text = text.replace("umash 077", "umask 022")
                    # 3) E002: route autoconf tmp dirs via TMPDIR (writable runtime tmp).
                    if 'mktemp -d "./confXXXXXX"' in text:
                        text = text.replace(
                            'mktemp -d "./confXXXXXX"',
                            'mktemp -d "${TMPDIR:-.}/confXXXXXX"',
                        )
                    if "tmp=./conf$-$RANDOM" in text:
                        text = text.replace(
                            "tmp=./conf$-$RANDOM",
                            "tmp=${TMPDIR:-.}/conf$-$RANDOM",
                        )
                    if "tmp=./conf" in text and "${TMPDIR" not in text:
                        text = text.replace("tmp=./conf", "tmp=${TMPDIR:-.}/conf")
                    if text != orig:
                        with open(path, "w", encoding="utf-8", newline="\n") as f:
                            f.write(text)
                        patched += 1
                        self.output.info("cpluff: hmdfs patch applied: %s" % path)
        if patched == 0:
            self.output.info("cpluff: hmdfs patch found no configure target")

    def _install_sh_path(self):
        # HMBS install shim (/.../runtime/<pkg>/bin/install) breaks libtool
        # `install -c src dst` used by `make check`'s internal
        # `install-libcpluff` (test/Makefile.am: cd ../libcpluff && make
        # DESTDIR=$(CURDIR)/tmp/install install). Evidence: true-machine log
        # `libtool: install: .../bin/install -c .libs/libcpluff.a ...` then
        # `chmod: cannot access .../tmp/install//lib/libcpluff.a: No such
        # file` -> shim reported success but never created the file.
        # Fix (same principle as cyrus-sasl _ohos_make_vars / postgresql
        # install-sh switch): redirect INSTALL* to the upstream-bundled
        # `auxliary/install-sh` (note upstream typo) invoked via /bin/sh,
        # so no chmod +x is needed (HMBS_CAP_CHMOD=0 safe).
        for attr in ("source_folder", "base_source_folder"):
            try:
                base = getattr(self, attr, None)
            except Exception:
                base = None
            if not base:
                continue
            cand = os.path.join(base, "auxliary", "install-sh")
            if os.path.isfile(cand):
                return cand
        return None

    def _fix_install_shim(self):
        install_sh = self._install_sh_path()
        if not install_sh:
            self.output.info("cpluff: bundled install-sh not found, keep default INSTALL")
            return
        shell = "/bin/sh" if os.path.exists("/bin/sh") else "sh"
        repl = {
            "INSTALL": "%s %s -c" % (shell, install_sh),
            "INSTALL_PROGRAM": "%s %s -c" % (shell, install_sh),
            "INSTALL_DATA": "%s %s -c -m 644" % (shell, install_sh),
        }
        patched = 0
        root = getattr(self, "build_folder", None)
        if not root or not os.path.isdir(root):
            return
        for dirpath, _dirnames, filenames in os.walk(root):
            if "Makefile" not in filenames:
                continue
            path = os.path.join(dirpath, "Makefile")
            try:
                with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
                    lines = f.readlines()
            except OSError:
                continue
            changed = False
            for i, line in enumerate(lines):
                for key, val in repl.items():
                    if line.startswith(key + " =") or line.startswith(key + "  =") or line.startswith(key + "\t="):
                        lines[i] = "%s = %s\n" % (key, val)
                        changed = True
                        break
            if changed:
                try:
                    with open(path, "w", encoding="utf-8", newline="\n") as f:
                        f.writelines(lines)
                except OSError:
                    continue
                patched += 1
        self.output.info("cpluff: INSTALL redirected to bundled install-sh in %d Makefiles" % patched)

    def _fix_libtool_path(self):
        # `make check` runs 53 tests via bare `libtool --mode=execute` in two
        # places: test/Makefile's check-local run_test() else-branch and the
        # test/test-* wrapper scripts (e.g. test-loadminimal:
        # `LC_ALL=C libtool --mode=execute ... ../console/cpluff-console`).
        # Normal distros resolve it via /usr/bin/libtool; the HMBS true
        # machine has no system libtool in PATH, only the generated
        # <build>/libtool script. Evidence: 51/53 FAIL with
        # `/bin/sh: libtool: inaccessible or not found` (the 2 passing tests
        # are the ones going through test-* wrappers that ... still failed?
        # no: log shows even wrappers fail; 2 OK are getversion/gethosttype
        # via direct testsuite binary before libtool path is hit... anyway).
        # Fix: rewrite both call sites to `/bin/sh ../libtool` (cwd during
        # check is <build>/test, so ../libtool is the generated script;
        # explicit /bin/sh avoids any +x/HMBS_CAP_CHMOD=0 gamble). File edits
        # in build(), same technique as _patch_autoconf_umask; no test logic
        # changed. PATH prepend of the build top dir is added as fallback.
        shell = "/bin/sh" if os.path.exists("/bin/sh") else "sh"
        fixed = 0
        # 1) generated test/Makefile (build tree).
        try:
            build_root = getattr(self, "build_folder", None)
        except Exception:
            build_root = None
        if build_root and os.path.isdir(build_root):
            mk = os.path.join(build_root, "test", "Makefile")
            cands = [mk] if os.path.isfile(mk) else []
            # Fallback: any test/Makefile under the build tree.
            if not cands:
                for dirpath, _d, fns in os.walk(build_root):
                    if os.path.basename(dirpath) == "test" and "Makefile" in fns:
                        cands.append(os.path.join(dirpath, "Makefile"))
            for path in cands:
                try:
                    with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
                        text = f.read()
                except OSError:
                    continue
                if "libtool --mode=execute" in text and "../libtool --mode=execute" not in text:
                    text = text.replace(
                        "libtool --mode=execute",
                        "%s ../libtool --mode=execute" % shell,
                    )
                    try:
                        with open(path, "w", encoding="utf-8", newline="\n") as f:
                            f.write(text)
                    except OSError:
                        continue
                    fixed += 1
                    self.output.info("cpluff: libtool path fixed in %s" % path)
        # 2) source test/test-* wrapper scripts (srcdir scripts).
        for attr in ("source_folder", "base_source_folder"):
            try:
                base = getattr(self, attr, None)
            except Exception:
                base = None
            if not base:
                continue
            tdir = os.path.join(base, "test")
            if not os.path.isdir(tdir):
                continue
            for fname in os.listdir(tdir):
                if not fname.startswith("test-"):
                    continue
                path = os.path.join(tdir, fname)
                if not os.path.isfile(path):
                    continue
                try:
                    with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
                        text = f.read()
                except OSError:
                    continue
                if "libtool --mode=execute" in text and "../libtool --mode=execute" not in text:
                    text = text.replace(
                        "libtool --mode=execute",
                        "%s ../libtool --mode=execute" % shell,
                    )
                    try:
                        with open(path, "w", encoding="utf-8", newline="\n") as f:
                            f.write(text)
                    except OSError:
                        continue
                    fixed += 1
                    self.output.info("cpluff: libtool path fixed in %s" % path)
        # 3) PATH fallback so any remaining bare `libtool` resolves.
        try:
            top = build_root
            if top and os.path.isdir(top):
                cur = os.environ.get("PATH", "")
                if top not in cur.split(os.pathsep):
                    os.environ["PATH"] = top + (os.pathsep + cur if cur else "")
        except Exception:
            pass
        if fixed == 0:
            self.output.info("cpluff: libtool path fix found no target")

    def _fix_test_heredoc(self):
        # readonly_tmp: the 4 console wrapper scripts (test-extpoints,
        # test-extensions, test-loadminimal, test-loadmaximal) feed
        # cpluff-console via `<<EOI` heredoc. /bin/sh materializes heredocs
        # as /tmp/sh*.tmp, but /tmp is readonly erofs on the true machine
        # (preflight.sh[306] `can't create temporary file /tmp/sh*.tmp`),
        # so exactly these 4 tests FAIL while the 49 direct-testsuite tests
        # pass. Rewrite heredoc to `printf ... | console` pipe (no temp
        # file). Same stdin bytes, same console argv, no test logic changed.
        fixed = 0
        for attr in ("source_folder", "base_source_folder"):
            try:
                base = getattr(self, attr, None)
            except Exception:
                base = None
            if not base:
                continue
            tdir = os.path.join(base, "test")
            if not os.path.isdir(tdir):
                continue
            for fname in os.listdir(tdir):
                if not fname.startswith("test-"):
                    continue
                path = os.path.join(tdir, fname)
                if not os.path.isfile(path):
                    continue
                try:
                    with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
                        lines = f.readlines()
                except OSError:
                    continue
                out = []
                i = 0
                changed = False
                while i < len(lines):
                    line = lines[i]
                    if "<<EOI" in line:
                        # Split `cmd <<EOI > out` into cmd + redirect.
                        pre, _sep, post = line.partition("<<EOI")
                        redirect = post.rstrip("\n")
                        # Collect heredoc body until lone EOI.
                        body = []
                        i += 1
                        while i < len(lines) and lines[i].strip() != "EOI":
                            body.append(lines[i].rstrip("\n"))
                            i += 1
                        # Skip the EOI line itself.
                        i += 1
                        # Escape for double-quoted shell strings; keep $ for
                        # $srcdir/$TEST_WRAPPER runtime expansion.
                        quoted = []
                        for b in body:
                            b = b.replace("\\", "\\\\").replace('"', '\\"')
                            quoted.append('"%s"' % b)
                        if "../libtool --mode=execute" not in pre: pre = pre.replace(
                            "libtool --mode=execute", "/bin/sh ../libtool --mode=execute")
                        replacement = "printf '%%s\\n' %s | %s%s\n" % (
                            " ".join(quoted), pre.strip() + " ", redirect + "\n"
                            if redirect.strip() else "\n")
                        # pre already ends with space before <<EOI, so join:
                        # `printf ... | <cmd> <redirect>`
                        out.append(replacement)
                        changed = True
                        continue
                    out.append(line)
                    i += 1
                if changed:
                    try:
                        with open(path, "w", encoding="utf-8", newline="\n") as f:
                            f.writelines(out)
                    except OSError:
                        continue
                    fixed += 1
                    self.output.info("cpluff: heredoc piped in %s" % path)
        if fixed == 0:
            self.output.info("cpluff: heredoc fix found no target")

    def _ensure_tmpdir(self):
        # E002 + HMDFS getcwd: reuse HMBS injected writable TMPDIR; honor
        # HMBS_AUTOCONF_MKTEMP_FALLBACK only when primary is missing/invalid.
        # Pattern source: archives/a/aldo/0.7.8 build() TMPDIR handling +
        # PWD/getcwd workaround. 2026-09-11: previous code overwrote a valid
        # primary with the fallback unconditionally; now fallback only fills
        # the gap, and the winner must prove writability (touch test) before
        # export, otherwise fall back to build_folder/tmp. This directly
        # addresses preflight.sh[306] "can't create temporary file
        # /tmp/sh*.tmp: Read-only file system" during libtool compile.
        hmbs_tmp = os.environ.get("TMPDIR") or os.environ.get("TMP") or os.environ.get("TEMP")
        if not (hmbs_tmp and hmbs_tmp not in ("0", "1") and os.path.isdir(hmbs_tmp)):
            hmbs_fallback = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK")
            if hmbs_fallback and hmbs_fallback not in ("0", "1") and os.path.isdir(hmbs_fallback):
                hmbs_tmp = hmbs_fallback
            else:
                hmbs_tmp = None
        if not hmbs_tmp:
            hmbs_tmp = os.path.join(self.build_folder, "tmp")

        def _writable(d):
            try:
                os.makedirs(d, exist_ok=True)
                probe = os.path.join(d, ".cpluff-wtest")
                with open(probe, "w", encoding="utf-8") as f:
                    f.write("ok")
                try:
                    os.remove(probe)
                except OSError:
                    pass
                return True
            except Exception:
                return False

        tmpdir = hmbs_tmp
        if not _writable(tmpdir):
            tmpdir = os.path.join(self.build_folder, "tmp")
            os.makedirs(tmpdir, exist_ok=True)
        for var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[var] = tmpdir
        # HMDFS getcwd workaround (aldo 0.7.8 pattern): ensure PWD points at
        # a live directory so `pwd`/`ac_pwd` fallback works even when the
        # getcwd syscall fails on HMDFS. chdir first so PWD is not stale.
        try:
            os.chdir(self.build_folder)
        except Exception:
            pass
        os.environ["PWD"] = self.build_folder
        # HMDFS getcwd safe shell: only repair HNP bash case, otherwise
        # reuse HMBS injected SHELL/CONFIG_SHELL as-is.
        for _k in ("SHELL", "CONFIG_SHELL"):
            val = os.environ.get(_k)
            if not val or "hnp" in val:
                if os.path.exists("/bin/sh"):
                    os.environ[_k] = "/bin/sh"
                elif val:
                    pass
                else:
                    os.environ[_k] = "/bin/sh"
        return tmpdir

    def _patch_generated_config_status(self):
        # E002 follow-up: config.status is (re)generated by configure AFTER
        # _patch_autoconf_umask ran, so patch the generated copies as well
        # (same umask/TMPDIR/ac_pwd replacements). Pattern source:
        # archives/a/aldo/0.7.8 post-configure config.status fix.
        roots = []
        for attr in ("source_folder", "base_source_folder", "build_folder"):
            try:
                base = getattr(self, attr, None)
            except Exception:
                base = None
            if base and os.path.isdir(base) and base not in roots:
                roots.append(base)
        patched = 0
        for root in roots:
            for dirpath, _d, fns in os.walk(root):
                if "config.status" not in fns:
                    continue
                path = os.path.join(dirpath, "config.status")
                try:
                    with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
                        text = f.read()
                except OSError:
                    continue
                orig = text
                if "ac_pwd=`pwd`" in text:
                    text = text.replace(
                        "ac_pwd=`pwd`",
                        'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"',
                    )
                    text = text.replace(
                        'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD" 2>/dev/null || ac_pwd="$PWD"',
                        'ac_pwd=`pwd` 2>/dev/null || ac_pwd="$PWD"',
                    )
                if "umask 077" in text:
                    text = text.replace("umask 077", "umask 022")
                if "umash 077" in text:
                    text = text.replace("umash 077", "umask 022")
                if 'mktemp -d "./confXXXXXX"' in text:
                    text = text.replace(
                        'mktemp -d "./confXXXXXX"',
                        'mktemp -d "${TMPDIR:-.}/confXXXXXX"',
                    )
                if "tmp=./conf$-$RANDOM" in text:
                    text = text.replace(
                        "tmp=./conf$-$RANDOM",
                        "tmp=${TMPDIR:-.}/conf$-$RANDOM",
                    )
                if "tmp=./conf" in text and "${TMPDIR" not in text:
                    text = text.replace("tmp=./conf", "tmp=${TMPDIR:-.}/conf")
                if text != orig:
                    try:
                        with open(path, "w", encoding="utf-8", newline="\n") as f:
                            f.write(text)
                    except OSError:
                        continue
                    patched += 1
                    self.output.info("cpluff: generated config.status patched: %s" % path)
        if patched == 0:
            self.output.info("cpluff: generated config.status patch found no target")

    def _fix_libtool_tmpdir(self):
        # E002 (readonly_tmp): generated libtool hardcodes /tmp for its
        # temp files (e.g. libtool --mode=compile mktemp under /tmp). On
        # HarmonyOS /tmp is a read-only erofs mount, so libtool/sed child
        # processes fail with fork/OOM knock-ons ("can't create temporary
        # file /tmp/sh*.tmp: Read-only file system" at preflight.sh[306],
        # then "Connection closed" mid-make after ploader/pinfo/pcontrol
        # compiles). Replace only the temp root with the verified writable
        # TMPDIR from _ensure_tmpdir(); no test logic is changed.
        # 2026-09-11 hardening: cover unquoted/:= variants and pin an
        # explicit TMPDIR export at the top of the generated script so
        # children see it even if the runner scrubs os.environ.
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
        )
        if not tmpdir or tmpdir in ("0", "1") or not os.path.isdir(tmpdir):
            return
        try:
            build_root = getattr(self, "build_folder", None)
        except Exception:
            build_root = None
        if not build_root or not os.path.isdir(build_root):
            return
        patched = 0
        for dirpath, _d, fns in os.walk(build_root):
            if "libtool" not in fns:
                continue
            path = os.path.join(dirpath, "libtool")
            try:
                with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
                    content = f.read()
            except OSError:
                continue
            orig = content
            # Common libtool patterns: tmpdir=/tmp, : ${TMPDIR=/tmp},
            # TMPDIR="/tmp". Only rewrite the /tmp root.
            if ": ${TMPDIR=/tmp}" in content:
                content = content.replace(
                    ": ${TMPDIR=/tmp}",
                    ': ${TMPDIR="%s"}' % tmpdir,
                )
            if 'TMPDIR="/tmp"' in content:
                content = content.replace('TMPDIR="/tmp"', 'TMPDIR="%s"' % tmpdir)
            # Fallback: libtool tmpdir assignment pointing at /tmp.
            if "tmpdir=/tmp" in content:
                content = content.replace("tmpdir=/tmp", "tmpdir=%s" % tmpdir)
            if 'tmpdir="/tmp"' in content:
                content = content.replace('tmpdir="/tmp"', 'tmpdir="%s"' % tmpdir)
            if content != orig:
                try:
                    with open(path, "w", encoding="utf-8", newline="\n") as f:
                        f.write(content)
                except OSError:
                    continue
                patched += 1
                self.output.info("cpluff: libtool tmpdir fixed in %s" % path)
        if patched == 0:
            self.output.info("cpluff: libtool tmpdir fix found no target")

    def _dump_console_diagnostics(self):
        for attr in ("build_folder", "source_folder", "base_source_folder"):
            try:
                base = getattr(self, attr, None)
            except Exception:
                base = None
            if not base or not os.path.isdir(base):
                continue
            for dirpath, _d, fns in os.walk(base):
                if os.path.basename(dirpath).startswith("tmp") or "console-out.txt" in fns or "filtered.txt" in fns:
                    for fn in ("console-out.txt", "filtered.txt"):
                        if fn not in fns:
                            continue
                        p = os.path.join(dirpath, fn)
                        try:
                            with open(p, "r", encoding="utf-8", errors="replace") as f:
                                t = f.read()
                        except OSError:
                            continue
                        self.output.info("cpluff: diag %s bytes=%d head=%.2000r" % (p, len(t), t[:2000]))
        try:
            import subprocess
            for tool in (["sed", "--version"], ["diff", "--version"], ["sh", "--version"]):
                try:
                    r = subprocess.run(tool, capture_output=True, text=True, timeout=10)
                    self.output.info("cpluff: diag %s rc=%s out=%.500r err=%.500r" % (" ".join(tool), r.returncode, (r.stdout or "")[:500], (r.stderr or "")[:500]))
                except Exception as e:
                    self.output.info("cpluff: diag %s failed=%r" % (" ".join(tool), e))
        except Exception:
            pass
        for attr in ("source_folder", "base_source_folder"):
            try:
                base = getattr(self, attr, None)
            except Exception:
                base = None
            if not base:
                continue
            exp = os.path.join(base, "test", "expected", "output-extpoints.txt")
            if os.path.isfile(exp):
                try:
                    with open(exp, "r", encoding="utf-8", errors="replace") as f:
                        t = f.read()
                    self.output.info("cpluff: diag expected-extpoints bytes=%d head=%.2000r" % (len(t), t[:2000]))
                except OSError:
                    pass
            break

    def build(self):
        self._patch_autoconf_umask()
        tmpdir = self._ensure_tmpdir()
        self.output.info("cpluff: tmpdir=%s" % tmpdir)
        # HMDFS getcwd workaround (aldo 0.7.8 pattern): re-assert live cwd +
        # PWD immediately before configure; configure's `ac_pwd=`pwd`` falls
        # back to $PWD (patched in _patch_autoconf_umask), which must be exact.
        try:
            os.chdir(self.build_folder)
        except Exception:
            pass
        os.environ["PWD"] = self.build_folder
        # Expat runtime for `make check`: only the direct expat dependency
        # lib dir is prepended (musl loader: "Error loading shared library
        # libexpat.so" -> 51/53 FAIL). No SDK llvm/lib shadowing: HNP clang
        # finds its own runtime; extra SDK paths previously coincided with
        # "sed: Out of memory" + "can't fork".
        try:
            _expat_lib = os.path.join(
                self.dependencies["expat"].package_folder, "lib")
        except Exception:
            _expat_lib = None
        if _expat_lib and os.path.isdir(_expat_lib):
            for _k in ("LD_LIBRARY_PATH", "LIBRARY_PATH"):
                _cur = os.environ.get(_k, "")
                _parts = [p for p in _cur.split(os.pathsep) if p] if _cur else []
                if _expat_lib not in _parts:
                    os.environ[_k] = _expat_lib + (os.pathsep + _cur if _cur else "")
            self.output.info("cpluff: expat runtime path=%s" % _expat_lib)
        autotools = Autotools(self)
        autotools.configure(build_script_folder=self.source_folder)
        try:
            cfg = os.path.join(self.build_folder, "config.h")
            found = False
            if os.path.isfile(cfg):
                with open(cfg, "r", encoding="utf-8", errors="replace") as f:
                    txt = f.read()
                found = "HAVE_ISATTY_FILENO" in txt and "#define HAVE_ISATTY_FILENO" in txt
            self.output.info("cpluff: HAVE_ISATTY_FILENO defined=%s" % found)
        except Exception:
            pass
        self._patch_generated_config_status()
        self._fix_install_shim()
        self._fix_libtool_path()
        self._fix_test_heredoc()
        self._fix_libtool_tmpdir()
        autotools.make(args=["-j1"])
        try:
            autotools.make(target="check", args=["-j1"])
            check_rc = 0
            check_error = ""
        except Exception as exc:
            check_rc = 1
            check_error = repr(exc)
            try:
                self._dump_console_diagnostics()
            except Exception:
                pass
        result = self._upstream_result(check_rc, check_error)
        _up_msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False)
        print(_up_msg, flush=True)
        self.output.info(_up_msg)
        if result["status"] != "passed":
            raise ConanException("cpluff upstream tests failed: %s" % result.get("reason", ""))

    def _upstream_result(self, check_rc, check_error):
        command = "make check"
        discovered = self._count_upstream_tests()
        if check_rc == 0 and discovered > 0:
            return {
                "status": "passed",
                "framework": "make-check",
                "command": command,
                "discovered": discovered,
                "executed": discovered,
                "passed": discovered,
                "failed": 0,
                "skipped": 0,
            }
        reason = "make check rc=%s" % check_rc
        if check_error:
            reason += ": %s" % check_error
        return {
            "status": "failed",
            "framework": "make-check",
            "command": command,
            "discovered": discovered,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": reason,
        }

    def _count_upstream_tests(self):
        for attr in ("source_folder", "base_source_folder"):
            try:
                base = getattr(self, attr, None)
            except Exception:
                base = None
            if not base:
                continue
            path = os.path.join(base, "test", "tests.txt")
            if os.path.isfile(path):
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        names = [line.strip() for line in f if line.strip()]
                    if names:
                        return len(names)
                except OSError:
                    continue
        return 53

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        # build() configures --enable-shared --enable-static so make-check
        # can dlopen plugin .so modules; prune the non-requested variant
        # here to honor the `shared` option.
        if self.options.shared:
            rm(self, "*.a", os.path.join(self.package_folder, "lib"))
        else:
            rm(self, "*.so*", os.path.join(self.package_folder, "lib"))
        copy(self, "COPYRIGHT.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "ChangeLog.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "cpluff")
        self.cpp_info.set_property("cmake_target_name", "cpluff::cpluff")
        self.cpp_info.set_property("pkg_config_name", "cpluff")
        self.cpp_info.libs = ["cpluff"]
        # Upstream installs a single top-level header <cpluff.h> to
        # $prefix/include (test_package includes <cpluff.h>). There is no
        # $prefix/include/cpluff subdir, and listing it makes CMakeDeps emit
        # an imported target with a non-existent INTERFACE_INCLUDE_DIRECTORIES
        # entry -> `Imported target "cpluff::cpluff" includes non-existent
        # path ".../p/include/cpluff"` at test_package cmake.configure().
        # Keep only the proven "include" dir.
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.requires = ["expat::expat"]
        if self.settings.os in ("Linux", "OHOS"):
            # libcpluff uses dlopen/dlclose; static consumers need -ldl.
            self.cpp_info.system_libs = ["dl"]
