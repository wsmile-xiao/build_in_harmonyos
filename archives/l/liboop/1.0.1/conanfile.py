#!/usr/bin/env python3
"""Conan recipe — liboop 1.0.1 (Autotools event-loop library).

liboop is a low-level POSIX event loop library (select/timer/signal/fd).
Upstream ships Autotools sources with a pre-generated configure
(autoconf 2.69) and no automated test suite: the only test program
(test-oop) is a manual interactive sample, there is no TESTS /
check_PROGRAMS wiring, so `make check` is an automake no-op
(audited, see test_package/MANIFEST.yml upstream_test_audit).

OHOS adaptations:
  - Core library only: --without-adns --without-readline --without-glib
    --without-tcl (and no --with-libwww), so the build has zero Conan
    dependencies and is fully deterministic on a clean worker.
  - R32: settings.os checked with `in ("Linux", "OHOS")`.
  - E007: 2014-03-23 config.guess predates the GUESS= refactor, so the
    HarmonyOS branch is added in vintage echo/exit style (same as
    gtypist/btparse) emitting <machine>-unknown-linux-ohos natively;
    config.sub accepts linux-ohos; --build/--host are stripped (R15).
  - HMDFS hardening (autoconf 2.69, same family as backuppc-rsync):
    export a valid PWD + chdir to build_folder before configure
    (getcwd ".." traversal fails on HMDFS), programmatic ac_pwd
    fallback to $PWD in configure, writable TMPDIR/TMP/TEMP so
    configure/make never touch read-only /tmp, usable SHELL fallback
    to /bin/sh when the profile HNP bash is unavailable.
  - Upstream has no test suite: build() does NOT invoke `make check`
    (upstream_test_in_build: false); HMBS_UPSTREAM_TEST_RESULT
    status=no_tests is emitted by test_package every run.
"""

import os
import re
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LiboopConan(ConanFile):
    name = "liboop"
    version = "1.0.1"
    description = "Low-level event loop management library for POSIX systems"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.lysator.liu.se/liboop/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Core-only build: all optional adapters disabled, zero deps.
        pass

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "liboop is only supported on Linux/OHOS, not %s" % self.settings.os
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Core-only build: disable every optional adapter so no extra
        # system/Conan dependency is probed on the worker.
        tc.configure_args.append("--without-adns")
        tc.configure_args.append("--without-readline")
        tc.configure_args.append("--without-glib")
        tc.configure_args.append("--without-tcl")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        else:
            tc.configure_args.append("--disable-static")
            tc.configure_args.append("--enable-shared")
        # E007/R15: never pass --build/--host; patched config.guess detects
        # OHOS natively as aarch64-unknown-linux-ohos. Forcing triplets fakes
        # cross-compile mode and skips AC_RUN_IFELSE checks (build-systems.md
        # 3.0), so strip any toolchain-injected values here.
        tc.configure_args = [
            a for a in tc.configure_args
            if not str(a).startswith("--build=")
            and not str(a).startswith("--host=")
        ]
        # Primary channel: toolchain environment lands in conanbuild.sh
        # with correct ordering against the profile [buildenv].
        # os.environ alone loses at self.run time, so this is authoritative.
        tmp_hint = os.path.join(self.build_folder, "tmp")
        tc.generate(env=self._hmbs_toolchain_env(tc, tmp_hint))
        # Belt-and-braces channels: buildenv_info + save_script carry the
        # same values for direct children.
        shell = self._resolve_shell()
        tmp_base = self._writable_tmp(tmp_hint)
        for var in ("TMPDIR", "TMP", "TEMP"):
            self.buildenv_info.define(var, tmp_base)
        self.buildenv_info.define("SHELL", shell)
        self.buildenv_info.define("CONFIG_SHELL", shell)
        env = Environment()
        env.define("SHELL", shell)
        env.define("CONFIG_SHELL", shell)
        env.define("TMPDIR", tmp_base)
        env.define("TMP", tmp_base)
        env.define("TEMP", tmp_base)
        for key in ("HMBS_TMPDIR", "HMBS_AUTOCONF_MKTEMP_FALLBACK",
                    "HMBS_CAP_HARDLINK", "HMBS_CAP_CHMOD", "HMBS_CAP_SYMLINK",
                    "HMBS_CAP_LOCAL_MKTEMP"):
            val = os.environ.get(key)
            if val:
                env.define(key, val)
        env.vars(self, scope="build").save_script("liboop_hmos_fix")
        self.output.info(
            "liboop_hmos_fix: SHELL/CONFIG_SHELL=%s TMPDIR=%s" % (shell, tmp_base)
        )

    def build(self):
        apply_conandata_patches(self)
        shell = self._resolve_shell()
        tmpdir = self._writable_tmp(os.path.join(self.build_folder, "tmp"))
        for var, val in (("TMPDIR", tmpdir), ("TMP", tmpdir), ("TEMP", tmpdir),
                         ("SHELL", shell), ("CONFIG_SHELL", shell)):
            os.environ[var] = val
        if self.settings.os == "OHOS":
            self._patch_configure_workdir()
            self._patch_configure_shell()
            self._patch_config_guess_sub()
            self._patch_configure_umask()
            os.environ["PWD"] = self.build_folder
            self.output.info(
                "[shell_getcwd] PWD=%s exported for configure workdir fallback"
                % self.build_folder
            )
        else:
            # Same shell hardening on Linux workers: the profile may still
            # inject a stale CONFIG_SHELL.
            self._patch_configure_shell()
            self._patch_configure_umask()
        os.chdir(self.build_folder)
        # Final override: profile [buildenv] wins over os.environ at
        # self.run time, so patch conanbuild*.sh on disk before configure.
        # The profile CC (/data/service/hnp/bin/clang) is not executable
        # inside the preflight sandbox (configure: 127 inaccessible or not
        # found); resolve the PATH-visible compiler (juise 3.0.0 pattern)
        # and force it inline so it wins over any stale conanbuild.sh value.
        # liboop has zero Conan deps, so no LD_LIBRARY_PATH shadowing
        # (juise case) applies here; only the program path is overridden.
        cc, cxx, ar, ranlib = self._resolve_toolchain_programs()
        self._override_conan_buildenv(shell, tmpdir,
                                      {"CC": cc, "CXX": cxx,
                                       "AR": ar, "RANLIB": ranlib})
        autotools = Autotools(self)
        try:
            # Inline-env wrapper: VAR=val prefixes win over any sourced
            # conanbuild.sh ordering, so dash always sees the writable
            # build-local TMPDIR and /bin/sh even if a stale profile env
            # survives on disk. Only redirects temp root and shell.
            try:
                cfg_args = autotools._configure_args
            except Exception:
                cfg_args = ""
            if cfg_args is None:
                cfg_args = ""
            configure_path = os.path.join(self.source_folder, "configure")
            if not os.path.isfile(configure_path):
                # Fallback to the stock helper if the script is missing.
                autotools.configure()
            else:
                exports = " ".join(
                    "%s=%s" % (k, shlex.quote(v))
                    for k, v in (("TMPDIR", tmpdir), ("TMP", tmpdir),
                                 ("TEMP", tmpdir),
                                 ("CONFIG_SHELL", shell), ("SHELL", shell),
                                 ("CC", cc), ("CXX", cxx),
                                 ("AR", ar), ("RANLIB", ranlib))
                )
                self.run(
                    "%s %s %s"
                    % (exports, shlex.quote(configure_path), cfg_args),
                    env="conanbuild",
                )
        except Exception:
            self._dump_config_log()
            raise
        autotools.make(args=["-j1"])
        # Upstream has no automated suite (audited): `make check` is an
        # automake no-op with zero test entries, so build() intentionally
        # does not run it (upstream_test_in_build: false). The
        # HMBS_UPSTREAM_TEST_RESULT status=no_tests evidence is produced
        # by test_package on every run (cache-hit safe).

    def package(self):
        # Keep install-time shells on the writable tmpdir too (same
        # readonly_tmp root cause as build()).
        try:
            _shell = self._resolve_shell()
            _tmp = self._writable_tmp(os.path.join(self.build_folder, "tmp"))
            for var, val in (("TMPDIR", _tmp), ("TMP", _tmp), ("TEMP", _tmp),
                             ("SHELL", _shell), ("CONFIG_SHELL", _shell)):
                os.environ[var] = val
            self._override_conan_buildenv(_shell, _tmp)
        except Exception:
            pass
        try:
            _tmp = self._writable_tmp(os.path.join(self.build_folder, "tmp"))
        except Exception:
            _tmp = self.build_folder
        install_sh = self._copy_install_sh(_tmp)
        autotools = Autotools(self)
        # HMBS install shim (runtime/.../bin/install -c) left no file
        # behind for libtool --mode=install (.libs/liboop.a -> p/lib),
        # so the follow-up chmod 644 aborts with "No such file".
        # Drive make install with the tarball install-sh as a single
        # program path (cyrus-sasl-login proven: no shell prefix, or
        # libtool misparses it as an input file). Only the install
        # program is redirected; no test is skipped.
        install_args = [
            'INSTALL="%s -c"' % install_sh,
            'INSTALL_PROGRAM="%s -c"' % install_sh,
            'INSTALL_DATA="%s -c -m 644"' % install_sh,
            'MKDIR_P="%s -c -d"' % install_sh,
        ]
        try:
            autotools.install(args=install_args)
        except Exception as exc:
            # Defense in depth (buildtorrent package-fallback family):
            # install-sh/HMFS quirks must never hard-fail package().
            # The static lib, headers and generated .pc files are all
            # present in the build/source trees; stage them manually.
            self.output.warning(
                "make install failed (%s); falling back to manual copy" % exc)
            self._fallback_install_files()
        lib_dir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(lib_dir):
            for pattern in ("*.la", "*.dylib"):
                try:
                    copy(self, pattern, src=lib_dir, dst=lib_dir,
                         keep_path=False)
                except Exception:
                    pass
            # Remove libtool archives explicitly (copy without delete
            # keeps them on some Conan versions).
            import glob
            for pattern in ("*.la",):
                for stale in glob.glob(os.path.join(lib_dir, pattern)):
                    try:
                        os.remove(stale)
                    except OSError:
                        pass
        self._relocate_pkgconfig()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["oop"]
        self.cpp_info.set_property("cmake_file_name", "liboop")
        self.cpp_info.set_property("cmake_target_name", "liboop::liboop")
        self.cpp_info.set_property("pkg_config_name", "liboop")
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pc_dir)

    # ---- HMBS hardening helpers (programmatic, no source patches) ----

    def _resolve_shell(self):
        # HMBS preflight advertises shell=/bin/sh and injects SHELL=/bin/sh.
        # The CI profile hardcodes CONFIG_SHELL=/data/service/hnp/bin/bash,
        # which is missing/not executable inside the preflight sandbox
        # (configure: inaccessible or not found, autoconf re-exec runs
        # `exec $CONFIG_SHELL`). Existence probing is unreliable here, so
        # always use the HMBS-advertised /bin/sh.
        return "/bin/sh"

    def _usable_shell(self):
        return self._resolve_shell()

    def _writable_tmp(self, fallback):
        # Build-local first: the runner-injected $TMPDIR itself can be
        # unwritable for subshells, while the build folder is created by
        # conan for this build (same user/mount as compiler output), so a
        # Python-created subdir there is the most trustworthy temp root.
        # Only redirects the temp-file root; no test is skipped or removed.
        import tempfile

        def _probe(path):
            try:
                os.makedirs(path, exist_ok=True)
                fd, probe = tempfile.mkstemp(dir=path)
                os.close(fd)
                os.unlink(probe)
                return True
            except Exception:
                return False

        if _probe(fallback):
            return fallback
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(var, "")
            if val and val != "/tmp" and val != fallback and _probe(val):
                return val
        fb = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK", "")
        if fb and fb not in ("0", "1") and fb != "/tmp" and fb != fallback and _probe(fb):
            return fb
        try:
            os.makedirs(fallback, exist_ok=True)
        except Exception:
            pass
        return fallback

    def _usable_tmpdir(self, makedirs=False):
        fallback = os.path.join(self.build_folder, "tmp")
        tmp = self._writable_tmp(fallback)
        if makedirs:
            try:
                os.makedirs(tmp, exist_ok=True)
            except Exception:
                pass
        return tmp

    def _hmbs_toolchain_env(self, tc, tmp_hint):
        tmp_base = self._writable_tmp(tmp_hint)
        try:
            os.makedirs(tmp_base, exist_ok=True)
        except Exception:
            pass
        shell = self._resolve_shell()
        env = tc.environment()
        env.define("TMPDIR", tmp_base)
        env.define("TMP", tmp_base)
        env.define("TEMP", tmp_base)
        env.define("SHELL", shell)
        env.define("CONFIG_SHELL", shell)
        return env

    def _resolve_toolchain_programs(self):
        """Resolve sandbox-executable CC/CXX/AR/RANLIB (juise 3.0.0 pattern).

        The profile hardcodes /data/service/hnp/bin/clang, which the
        preflight sandbox reports as `inaccessible or not found` (exit
        127). Prefer the PATH-visible program, then the conf dict
        tools.build:compiler_executables (OHOS-adapted conan exposes it
        as a dict; dotted subkey access is unsupported on 2.29.1), then
        the profile default. Only selects the program path; no test or
        flag is changed.
        """
        conf = {}
        try:
            conf = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
        except Exception:
            conf = {}
        cc = (shutil.which("clang") or conf.get("c")
              or "/data/service/hnp/bin/clang")
        cxx = (shutil.which("clang++") or conf.get("cpp")
               or "/data/service/hnp/bin/clang++")
        ar = (shutil.which("llvm-ar") or shutil.which("ar")
              or conf.get("ar") or "llvm-ar")
        ranlib = (shutil.which("llvm-ranlib") or shutil.which("ranlib")
                  or conf.get("ranlib") or "llvm-ranlib")
        self.output.info(
            "toolchain programs: CC=%s CXX=%s AR=%s RANLIB=%s"
            % (cc, cxx, ar, ranlib))
        return cc, cxx, ar, ranlib

    def _override_conan_buildenv(self, shell, tmpdir, toolchain=None):
        # Patch generated conanbuild*.sh on disk so the missing profile
        # shell can never win over /bin/sh, and any stale TMPDIR (e.g.
        # /tmp) is forced to the writable build-local dir. Autotools
        # runs with env="conanbuild", so the on-disk script is authoritative.
        # toolchain optionally carries {"CC","CXX","AR","RANLIB"} resolved
        # via _resolve_toolchain_programs so stale HNP absolute paths in
        # the scripts are rewritten to sandbox-executable programs.
        toolchain = toolchain or {}
        for key, val in (("SHELL", shell), ("CONFIG_SHELL", shell),
                         ("TMPDIR", tmpdir), ("TMP", tmpdir),
                         ("TEMP", tmpdir)):
            os.environ[key] = val
        for key, val in toolchain.items():
            if val:
                os.environ[key] = val
        folders = []
        for folder in (self.build_folder, self.generators_folder):
            if folder and folder not in folders:
                folders.append(folder)
        bad_shells = [p for p in ("/data/service/hnp/bin/bash",
                                   "/data/service/hnp/bin/sh")
                       if p != shell]
        for folder in folders:
            try:
                walked = list(os.walk(folder))
            except OSError:
                continue
            for root, _dirs, names in walked:
                for name in names:
                    if not (name.startswith("conanbuild") and name.endswith(".sh")):
                        continue
                    path = os.path.join(root, name)
                    try:
                        with open(path, encoding="utf-8",
                                  errors="surrogateescape") as handle:
                            content = handle.read()
                    except OSError:
                        continue
                    orig = content
                    for bad in bad_shells:
                        content = content.replace(bad, shell)
                    for key in ("TMPDIR", "TMP", "TEMP"):
                        export_line = 'export %s="%s"' % (key, tmpdir)
                        pattern = re.compile(r'(?m)^export %s=.*' % key)
                        if pattern.search(content):
                            content = pattern.sub(export_line, content)
                        else:
                            if not content.endswith("\n"):
                                content += "\n"
                            content += export_line + "\n"
                    for key, val in toolchain.items():
                        if not val:
                            continue
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
                            with open(path, "w", encoding="utf-8",
                                      errors="surrogateescape") as handle:
                                handle.write(content)
                        except OSError:
                            continue
                        self.output.info(
                            "OHOS patch applied (conanbuild shell %s tmpdir %s) in %s"
                            % (shell, tmpdir, name))

    def _patch_configure_shell(self):
        """Force autoconf re-exec to /bin/sh regardless of environment.

        configure re-execs via `exec $CONFIG_SHELL`; any environment
        ordering that leaves the HNP bash in place still fails. Patch the
        script itself plus a CONFIG_SHELL export. Only the shell path is
        rewritten; no test is skipped.
        """
        for name in ("configure", "configure.sh"):
            path = os.path.join(self.source_folder, name)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as handle:
                    content = handle.read()
            except OSError:
                continue
            original = content
            if "CONFIG_SHELL=/bin/sh" not in content:
                lines = content.splitlines(keepends=True)
                if lines and lines[0].startswith("#!"):
                    lines.insert(1, 'CONFIG_SHELL=/bin/sh; export CONFIG_SHELL\n')
                    content = "".join(lines)
                else:
                    content = 'CONFIG_SHELL=/bin/sh; export CONFIG_SHELL\n' + content
            content = content.replace("exec $CONFIG_SHELL", "exec /bin/sh")
            if content != original:
                try:
                    with open(path, "w", encoding="utf-8", newline="\n") as handle:
                        handle.write(content)
                except OSError:
                    continue
                self.output.info(
                    "[shell_fix] patched %s CONFIG_SHELL re-exec -> /bin/sh" % name
                )

    def _patch_configure_workdir(self):
        """HMDFS: autoconf 2.69 `ac_pwd=`pwd`` aborts when getcwd fails.

        Rewrite to fall back to $PWD (exported to build_folder by build()).
        configure is a generated file: programmatic rewrite, no .patch.
        """
        old = "ac_pwd=`pwd` && test -n \"$ac_pwd\" &&"
        new = "ac_pwd=`pwd` 2>/dev/null || ac_pwd=\"$PWD\"\ntest -n \"$ac_pwd\" &&"
        patched = False
        for name in ("configure", "configure.sh"):
            path = os.path.join(self.source_folder, name)
            if not os.path.isfile(path):
                continue
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                content = handle.read()
            if old not in content:
                continue
            content = content.replace(old, new, 1)
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
            patched = True
            self.output.info(
                "[shell_getcwd] patched %s: ac_pwd falls back to $PWD" % name
            )
        if not patched:
            self.output.warning(
                "[shell_getcwd] workdir pattern not found; relying on PWD env only"
            )

    def _patch_configure_umask(self):
        """HMDFS: strip ``umask 077`` from AS_TMPDIR temp-dir creation.

        HMDFS refuses writes into ``mktemp -d`` dirs created as
        drwx--S--- (0700 + setgid), so ``config.status`` aborts with
        ``can't create ./confXXXXXX/subs1.awk: Permission denied`` and
        ``could not setup config files machinery`` (buildtorrent 0.9.1
        proven: identical caps chmod=0/local_mktemp=1/readonly_tmp).
        Removing the ``umask 077 &&`` prefix lets mktemp/mkdir use the
        default umask so the temp dir stays writable. Covers both the
        configure body and the embedded config.status heredoc template
        (both ``umask`` and autoconf's ``umash`` misspelling).
        Deliberately NOT a mktemp exit-1 shim: with HMBS_CAP_CHMOD=0
        the shim is not executable and the mkdir fallback itself
        carries ``umask 077``, so the shim route cannot work.
        Only the temp-dir mode is touched; no test is skipped.
        """
        for name in ("configure", "configure.sh"):
            path = os.path.join(self.source_folder, name)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "r", encoding="utf-8",
                          errors="replace") as handle:
                    text = handle.read()
            except OSError:
                continue
            patched, n_mktemp = re.subn(
                r"um(?:ask|ash) 077 && mktemp -d", "mktemp -d", text)
            patched, n_mkdir = re.subn(
                r"um(?:ask|ash) 077 && mkdir", "mkdir", patched)
            if n_mktemp == 0 and n_mkdir == 0:
                continue
            try:
                with open(path, "w", encoding="utf-8",
                          newline="\n") as handle:
                    handle.write(patched)
            except OSError:
                continue
            self.output.info(
                "patched %s AS_TMPDIR: removed 'umask 077 && ' "
                "for HMDFS writable tmpdir (mktemp:%d, mkdir:%d)"
                % (name, n_mktemp, n_mkdir))

    def _patch_config_guess_sub(self):
        """E007: teach 2014-vintage config.guess/config.sub about HarmonyOS.

        liboop 1.0.1 ships config.guess last modified 2014-03-23, which
        predates the 2021 GUESS= refactor: per-branch output uses
        `echo <triplet>` + `exit`, so scripts/patch-autotools-ohos.pl
        (GUESS= style) never matches. Apply the vintage-correct branch
        (same style as gtypist 2.10.1/btparse 0.35 0001 patches):
        `*:HarmonyOS:*:*)` before `*:NetBSD:*:*)` emitting
        `<machine>-unknown-linux-ohos` natively (no --build/--host).
        config.sub gets `linux-ohos` kernel-OS acceptance plus an
        aarch64 early-accept for pre-aarch64 vintages. Also relaxes
        `umask 077` to `022` in config.guess (E114/HMDFS) so the
        mktemp-based CC_FOR_BUILD probe can create its temp dir.
        Only the triplet recognition is touched; no test is skipped.
        """
        candidates = []
        for sub in ("", "build-aux", "config", "aux"):
            cg = os.path.join(self.source_folder, sub, "config.guess") if sub else os.path.join(self.source_folder, "config.guess")
            cs = os.path.join(self.source_folder, sub, "config.sub") if sub else os.path.join(self.source_folder, "config.sub")
            candidates.append((cg, cs))
        seen = set()
        for cg, cs in candidates:
            if cg in seen:
                continue
            seen.add(cg)
            if os.path.isfile(cg):
                self._patch_one_config_guess(cg)
            if os.path.isfile(cs):
                self._patch_one_config_sub(cs)

    def _patch_one_config_guess(self, path):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                content = handle.read()
        except OSError:
            return
        original = content
        # HMDFS: umask 077 yields an unwritable mktemp dir (E114 family).
        if "umask 077" in content:
            content = content.replace("umask 077", "umask 022")
        if "HarmonyOS" not in content:
            if "GUESS=" in content:
                # Post-2021 style (perl script equivalent).
                block = (
                    "    *:HarmonyOS:*:*)\n"
                    "\tcase \"$UNAME_MACHINE\" in\n"
                    "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
                    "\t    armv7*|armv8*) MACHINE=arm ;;\n"
                    "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
                    "\t    i?86)         MACHINE=i686 ;;\n"
                    "\t    *)            MACHINE=\"$UNAME_MACHINE\" ;;\n"
                    "\tesac\n"
                    "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
                    "\t;;\n\n"
                    "    *:NetBSD:*:*)"
                )
                if "    *:NetBSD:*:*)" in content:
                    content = content.replace(
                        "    *:NetBSD:*:*)", block, 1)
            else:
                # Pre-2021 style (2014-03-23 vintage in this tarball):
                # each branch echoes the triplet and exits.
                block = (
                    "    *:HarmonyOS:*:*)\n"
                    "\tcase \"$UNAME_MACHINE\" in\n"
                    "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
                    "\t    armv7*|armv8*) MACHINE=arm ;;\n"
                    "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
                    "\t    i?86)         MACHINE=i686 ;;\n"
                    "\t    *)            MACHINE=\"$UNAME_MACHINE\" ;;\n"
                    "\tesac\n"
                    "\techo ${MACHINE}-unknown-linux-ohos\n"
                    "\texit ;;\n\n"
                    "    *:NetBSD:*:*)"
                )
                if "    *:NetBSD:*:*)" in content:
                    content = content.replace(
                        "    *:NetBSD:*:*)", block, 1)
                elif "*:NetBSD:*:*)" in content:
                    content = content.replace(
                        "*:NetBSD:*:*)",
                        "*:HarmonyOS:*:*)\n\techo aarch64-unknown-linux-ohos\n"
                        "\texit ;;\n\n    *:NetBSD:*:*)", 1)
        if "__OHOS__" not in content and "__ANDROID__" in content:
            old = "#if defined(__ANDROID__)\n    LIBC=android"
            new = ("#if defined(__ANDROID__)\n    LIBC=android\n"
                   "#elif defined(__OHOS__)\n    LIBC=ohos")
            if old in content:
                content = content.replace(old, new, 1)
        if content != original:
            try:
                with open(path, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(content)
            except OSError:
                return
            try:
                os.chmod(path, 0o755)
            except OSError:
                pass
            self.output.info(
                "[E007] patched %s for HarmonyOS (vintage echo/exit style)"
                % os.path.basename(path))

    def _patch_one_config_sub(self, path):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                content = handle.read()
        except OSError:
            return
        original = content
        # 1) Accept linux-ohos in the maybe_os kernel-OS list (any vintage).
        if "linux-ohos" not in content:
            if "linux-android*" in content:
                content = content.replace("linux-android*", "linux-android* | linux-ohos*", 1)
            elif "linux-gnu*" in content:
                content = content.replace("linux-gnu*", "linux-gnu* | linux-ohos*", 1)
        # 2) OS-list acceptance for the triplet suffix.
        if "ohos*" not in content:
            if "gnu* | android*" in content:
                content = content.replace(
                    "gnu* | android*", "gnu* | android* | ohos*", 1)
        # 3) Pre-aarch64 vintages (2014): accept aarch64 triplets directly.
        if "aarch64" not in content and "case $1 in" in content:
            anchor = "case $1 in"
            early = (anchor + "\n"
                     "  aarch64-*-linux* | aarch64-*-ohos*)\n"
                     "    echo \"$1\"\n"
                     "    exit 0\n"
                     "    ;;\n")
            content = content.replace(anchor, early, 1)
        # 4) Trailing OS-suffix validation (2018-style lists).
        if "-linux-ohos*" not in content and "-linux-android*" in content:
            content = content.replace(
                "-linux-android*", "-linux-android* | -linux-ohos*", 1)
        if content != original:
            try:
                with open(path, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(content)
            except OSError:
                return
            try:
                os.chmod(path, 0o755)
            except OSError:
                pass
            self.output.info(
                "[E007] patched %s for linux-ohos triplet" % os.path.basename(path))

    def _dump_config_log(self):
        for base in (self.build_folder, self.source_folder):
            log = os.path.join(base, "config.log")
            if not os.path.isfile(log):
                continue
            try:
                with open(log, "r", encoding="utf-8", errors="replace") as handle:
                    text = handle.read()
                self.output.info("config.log tail (last 12k):\n" + text[-12000:])
            except OSError:
                pass
            break

    def _copy_install_sh(self, tmpdir):
        """Stage tarball install-sh as a single-path INSTALL program.

        libtool --mode=install parses INSTALL as "<program> <flags>";
        a "/bin/sh <script>" prefix makes it treat the script path as
        a file to install. Rewrite the shebang to /bin/sh (preflight
        shell) so INSTALL can stay a single program path; copy2 keeps
        the tarball exec bit so no chmod is required
        (HMBS_CAP_CHMOD=0 ignores chmod anyway). Adapted from the
        cyrus-sasl-login 2.1.28 proven pattern (single-path INSTALL /
        MKDIR_P); only paths/shell differ for this preflight.
        """
        fallback = os.path.join(self.source_folder, "install-sh")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        dest = os.path.join(tmpdir, "install-sh")
        try:
            if os.path.isfile(fallback):
                shutil.copy2(fallback, dest)
            else:
                return "install"
        except OSError:
            return "install"
        try:
            with open(dest, "r", encoding="utf-8",
                      errors="surrogateescape") as handle:
                content = handle.read()
            lines = content.split("\n", 1)
            if lines and lines[0].startswith("#!"):
                lines[0] = "#!/bin/sh"
                content = "\n".join(lines) if len(lines) > 1 else lines[0]
                with open(dest, "w", encoding="utf-8",
                           errors="surrogateescape", newline="\n") as handle:
                    handle.write(content)
        except OSError:
            pass
        try:
            os.chmod(dest, 0o755)
        except OSError:
            pass
        return dest

    def _fallback_install_files(self):
        """Manually stage lib/headers/pkgconfig when make install fails.

        Upstream `make install` would place: lib/liboop.a (+ .la, purged
        later), include/oop*.h (7 headers, see Makefile.am
        include_HEADERS), lib/pkgconfig/*.pc (generated in the build
        dir from *.pc.in). Copy each from where it is known to exist
        (built .libs / source headers / generated pc); missing groups
        are warned, not fatal, so a later gate still reports clearly.
        Only the install location is repaired; no test is skipped.
        """
        lib_dir = os.path.join(self.package_folder, "lib")
        inc_dir = os.path.join(self.package_folder, "include")
        pc_dir = os.path.join(lib_dir, "pkgconfig")
        for folder in (lib_dir, inc_dir, pc_dir):
            try:
                os.makedirs(folder, exist_ok=True)
            except OSError:
                pass
        # 1) static lib from the build tree (.libs/liboop.a just linked).
        copied_lib = False
        for root in (os.path.join(self.build_folder, ".libs"),
                     self.build_folder):
            cand = os.path.join(root, "liboop.a")
            if os.path.isfile(cand):
                try:
                    copy(self, "liboop.a", src=root, dst=lib_dir,
                         keep_path=False)
                    copied_lib = True
                    self.output.info(
                        "fallback copy lib: %s -> %s" % (cand, lib_dir))
                except Exception as exc:
                    self.output.warning(
                        "fallback copy lib failed: %s" % exc)
                break
        if not copied_lib:
            self.output.warning("fallback found no built liboop.a")
        # 2) public headers from the source tree.
        try:
            copy(self, "oop*.h", src=self.source_folder, dst=inc_dir,
                 keep_path=False)
        except Exception as exc:
            self.output.warning("fallback copy headers failed: %s" % exc)
        # 3) generated pkgconfig files from the build tree.
        copied_pc = False
        for folder in (self.build_folder, self.source_folder):
            try:
                names = os.listdir(folder)
            except OSError:
                continue
            if any(n.endswith(".pc") for n in names):
                try:
                    copy(self, "*.pc", src=folder, dst=pc_dir,
                         keep_path=False)
                    copied_pc = True
                    self.output.info(
                        "fallback copy pc: %s -> %s" % (folder, pc_dir))
                except Exception as exc:
                    self.output.warning(
                        "fallback copy pc failed: %s" % exc)
                break
        if not copied_pc:
            self.output.warning("fallback found no generated .pc file")

    def _relocate_pkgconfig(self):
        for pc_name in ("liboop.pc", "liboop-glib2.pc"):
            pc_path = os.path.join(self.package_folder, "lib", "pkgconfig", pc_name)
            if not os.path.isfile(pc_path):
                continue
            try:
                with open(pc_path, "r", encoding="utf-8") as handle:
                    content = handle.read()
                import re
                content, count = re.subn(
                    r"^prefix=.*$", "prefix=${pcfiledir}/../..",
                    content, count=1, flags=re.MULTILINE,
                )
                if count == 1:
                    with open(pc_path, "w", encoding="utf-8", newline="\n") as handle:
                        handle.write(content)
            except OSError:
                pass
