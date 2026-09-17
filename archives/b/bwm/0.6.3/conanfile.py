#!/usr/bin/env python3
"""Conan recipe — bwm 0.6.3 (Autotools CLI tool).

bwm 0.6.3 (Bandwidth Monitor, vgropp/bwm-ng upstream tag v0.6.3) is a small
live console bandwidth monitor for Linux/BSD. Upstream ships Autotools
sources (configure.in + Makefile.am) but no test suite: no tests/ directory
and no TESTS in Makefile.am, so automake's default `make check` is a no-op
(audited, see test_package/MANIFEST.yml upstream_test_audit).

OHOS adaptations:
    - Vendored autotools outputs (patches/0001-vendor-autotools-outputs.patch):
      upstream ships no pre-generated configure, and running autoreconf on CI
      became impossible with the platform perl/5.42.2 repack (revision
      ec97109d, 2026-09-09): its binary and all 47 XS .so modules carry 0750
      root:file_manager permissions, so the CI worker (uid 100, not in
      file_manager) dies with EACCES loading Cwd.so inside autoreconf, before
      any bwm source is compiled (the real machine passes only because its
      ssh user is in gid 1006). The patch vendors configure, configure.ac
      (rename copy of configure.in), aclocal.m4, Makefile.in, src/Makefile.in,
      config.h.in, compile, depcomp, install-sh and missing — generated on the
      verified real machine with the same toolchain (autoconf 2.72 /
      automake 1.18) the previous recipe used — so build() goes straight to
      ./configure with zero autotools/perl tool_requires. E114 (umask 077 &&
      mktemp HMDFS fix) is pre-applied inside the vendored configure; bwm does
      no host triplet probing (no AC_CANONICAL_HOST, no config.guess/sub).
    - Do not pass --build/--host (R15).
    - Disable curses/ncurses; use --with-proc-netdev; static link (R26) so the
      packaged CLI has no runtime NEEDED libs.
    - Upstream has no test suite: build() does not run `make check`
      (upstream_test_in_build: false); HMBS_UPSTREAM_TEST_RESULT
      status=no_tests is emitted by test_package/test.sh every run
      (re-emitted by test_package/conanfile.py on cache hits).
"""

import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.env import Environment
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class BwmConan(ConanFile):
    name = "bwm"
    version = "0.6.3"
    description = (
        "bwm (Bandwidth Monitor) — small live console bandwidth monitor "
        "for Linux/BSD (vgropp/bwm-ng upstream v0.6.3)."
    )
    license = "GPL-2.0-only"
    homepage = "https://www.gropp.org/?id=projects&sub=bwm-ng"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        # In-source autotools: configure is generated next to configure.in.
        self.folders.build = "."

    def source(self):
        src = dict(self.conan_data["sources"])
        src.setdefault("filename", "bwm-0.6.3.tar.gz")
        get(self, **src, strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R15/E007: never pass --build/--host; patched config.guess detects OHOS.
        tc.configure_args = [
            a for a in tc.configure_args
            if not str(a).startswith("--build=") and not str(a).startswith("--host=")
        ]
        # R26: static CLI binary, no runtime NEEDED libs. NOTE: -static is
        # deliberately NOT in extra_ldflags: LDFLAGS poisons configure's
        # conftest ("checking whether the C compiler works") and the true
        # machine fails there with "C compiler cannot create executables"
        # when the link-time -static cannot be satisfied. Configure therefore
        # runs with clean LDFLAGS; -static is appended only to the final
        # `make` link step in build() (bearer: make-time LDFLAGS override).
        # If the SDK lacks static libc, make (not conftest) will then show
        # the real linker error instead of the opaque Error 77.
        tc.configure_args.append("--without-curses")
        tc.configure_args.append("--without-ncurses")
        tc.configure_args.append("--with-proc-netdev")
        tc.generate()
        # True-machine guard: the repo profile pins
        # CONFIG_SHELL/SHELL=/data/service/hnp/bin/bash, which is
        # inaccessible on the current HMBS host (configure[139] dies with
        # "inaccessible or not found", Error 127). HMBS injects SHELL=/bin/sh
        # (capabilities shell=/bin/sh). Save a build-scope env script so every
        # conanbuild aggregation (autoreconf/configure/make) sees a usable
        # shell plus a writable TMPDIR instead of read-only /tmp.
        # Generated scripts win over the profile [buildenv], while inline
        # os.environ tweaks in build() alone do not.
        shell = self._usable_shell()
        tmpdir = self._usable_tmpdir(makedirs=True)
        env = Environment()
        env.define("SHELL", shell)
        env.define("CONFIG_SHELL", shell)
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        # True-machine compiler guard: profile pins
        # tools.build:compiler_executables to /data/service/hnp/bin/clang,
        # which is absent on some HMBS hosts (preflight probe: ls "No such
        # file", conftest rc=127 "inaccessible or not found"). When the
        # conf path exists it is kept (CI worker unchanged); otherwise fall
        # back to a PATH/SDK-resolved clang so configure's conftest can run.
        _cc, _cxx, _lbl = self._resolve_compiler()
        if _cc:
            env.define("CC", _cc)
        if _cxx:
            env.define("CXX", _cxx)
        env.vars(self, scope="build").save_script("bwm_hmos_fix")
        self.output.info(f"bwm_hmos_fix: SHELL/CONFIG_SHELL={shell} TMPDIR={tmpdir} compiler={_lbl} CC={_cc} CXX={_cxx}")

    def build(self):
        apply_conandata_patches(self)
        # Vendored autotools outputs (configure/Makefile.in/...) ship in the
        # patch with E114 pre-applied, so there is no autoreconf step and no
        # autotools/perl tool_requires on the CI path anymore (see docstring).
        # Inline env hardening, same reasons as generate(): the repo profile
        # pins SHELL/CONFIG_SHELL=/data/service/hnp/bin/bash, unusable on some
        # HMBS hosts, and profile CC may not exist. Inline exports run after
        # conanbuild.sh is sourced, so the good values win in the same shell
        # invocation.
        shell = self._usable_shell()
        tmpdir = self._usable_tmpdir(makedirs=True)
        for var, val in (("SHELL", shell), ("CONFIG_SHELL", shell),
                         ("TMPDIR", tmpdir), ("TMP", tmpdir), ("TEMP", tmpdir)):
            os.environ[var] = val
        cc, cxx, lbl = self._resolve_compiler()
        self.output.info(f"bwm build shell={shell} tmpdir={tmpdir} compiler={lbl} CC={cc} CXX={cxx}")
        prefix = (
            f'export SHELL="{shell}" && export CONFIG_SHELL="{shell}" && '
            f'export TMPDIR="{tmpdir}" && export TMP="{tmpdir}" && export TEMP="{tmpdir}" && '
        )
        if cc:
            prefix += f'export CC="{cc}" && '
            os.environ["CC"] = cc
        if cxx:
            prefix += f'export CXX="{cxx}" && '
            os.environ["CXX"] = cxx
        # Do NOT use Autotools.configure()/make(): the helper runs
        # `configure` via env="conanbuild", which re-exports the profile's
        # stale CONFIG_SHELL=/data/service/hnp/bin/bash AFTER our override.
        # Run everything explicitly via the usable shell with inline exports
        # AFTER conanbuild.sh is sourced (juise-style).
        configure_path = os.path.join(self.source_folder, "configure")
        cfg_dir = self.source_folder if os.path.isfile(configure_path) else self.build_folder
        conf_args = (
            "--prefix=/ '--bindir=${prefix}/bin' '--sbindir=${prefix}/bin' "
            "'--libdir=${prefix}/lib' '--includedir=${prefix}/include' "
            "'--oldincludedir=${prefix}/include' "
            "--without-curses --without-ncurses --with-proc-netdev"
        )
        # Pre-configure toolchain probe: dump CC/CFLAGS/LDFLAGS, clang
        # liveness, and a minimal compile so a failure log shows whether the
        # toolchain itself is at fault. Also dump config.log on configure
        # failure (re-raise after).
        self._probe_toolchain(cfg_dir, prefix, shell)
        try:
            self.run(prefix + f'"{shell}" ./configure {conf_args}', cwd=cfg_dir, env="conanbuild")
        except Exception:
            self._dump_config_log(cfg_dir)
            raise
        # Link-time -static only (see generate(): keep conftest clean).
        # $LDFLAGS expands to the conanbuild LDFLAGS at shell time.
        self.run(prefix + 'make -j1 LDFLAGS="$LDFLAGS -static"', cwd=cfg_dir, env="conanbuild")
        # Upstream has no test suite (audited: no tests/ dir, no TESTS/
        # check_PROGRAMS in either Makefile.am - see test_package/
        # MANIFEST.yml upstream_test_audit). build() therefore does NOT
        # invoke make check (upstream_test_in_build: false); the
        # HMBS_UPSTREAM_TEST_RESULT status=no_tests evidence is produced
        # by test_package/test.sh in the test phase (re-emitted by
        # test_package/conanfile.py on cache-hit runs). This mirrors the
        # merged osmctools/0.9 + sipcalc/1.1.6 no_tests precedent.

    def _probe_toolchain(self, cfg_dir, prefix, shell):
        # Best-effort diagnostics only; never fail the build here.
        try:
            cc = self.conf.get("tools.build:compiler_executables:c", check_type=str) or ""
        except Exception:
            cc = ""
        try:
            self.output.info(f"bwm probe: conf CC={cc!r} SHELL={shell}")
            probe = (
                prefix +
                'echo \"bwm probe: CC=$CC CFLAGS=$CFLAGS LDFLAGS=$LDFLAGS\"; '
                'echo \"bwm probe: LD_LIBRARY_PATH=$LD_LIBRARY_PATH TMPDIR=$TMPDIR\"; '
                'ls -l \"$CC\" 2>&1 || ls -l /data/service/hnp/bin/clang* 2>&1 || true; which clang clang++ cc gcc 2>&1 || true; ls -l /storage/Users/currentUser/usr/local/bin/clang* 2>&1 || true; ls -l ~/.harmonybrew/bin/clang* 2>&1 || true; '
                '\"$CC\" --version 2>&1 | head -5 || true; '
                'echo \'int main(){return 0;}\' > .bwm_cc_probe.c; '
                '\"$CC\" .bwm_cc_probe.c -o .bwm_cc_probe 2>&1 && echo \"bwm probe: plain cc OK\" || echo \"bwm probe: plain cc FAILED rc=$?\"; '
                '\"$CC\" .bwm_cc_probe.c -o .bwm_cc_probe_static -static 2>&1 && echo \"bwm probe: static cc OK\" || echo \"bwm probe: static cc FAILED rc=$?\"; '
                'rm -f .bwm_cc_probe.c .bwm_cc_probe .bwm_cc_probe_static; '
                'echo \"bwm probe: tmpdir writable test:\"; touch \"$TMPDIR/.bwm_tmp_wtest\" 2>&1 && echo OK || echo \"TMPDIR NOT WRITABLE rc=$?\"; rm -f \"$TMPDIR/.bwm_tmp_wtest\"'
            )
            self.run(probe, cwd=cfg_dir, env="conanbuild")
        except Exception as e:
            self.output.warning(f"bwm probe failed (non-fatal): {e}")

    def _dump_config_log(self, cfg_dir):
        try:
            log = os.path.join(cfg_dir, "config.log")
            if not os.path.isfile(log):
                self.output.warning("bwm: config.log not found after configure failure")
                return
            with open(log, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            # Print tail + compiler-error section so preflight log carries evidence.
            tail = text[-12000:]
            self.output.info("bwm config.log tail (last 12k):\n" + tail)
            m = re.search(r"(checking whether the C compiler works.*)", text, re.S)
            if m:
                idx = m.start()
                self.output.info("bwm config.log compiler section:\n" + text[idx:idx + 8000])
        except Exception as e:
            self.output.warning(f"bwm: dump config.log failed: {e}")

    def _resolve_compiler(self):
        """Return (cc, cxx, label) for a compiler that exists on this host.

        Profile pins tools.build:compiler_executables to
        /data/service/hnp/bin/clang, absent on some HMBS hosts (preflight:
        ls "No such file", conftest rc=127). Keep the conf value when the
        file exists (CI worker unchanged); otherwise search true-machine
        PATH plus SDK/harmonybrew candidate dirs. Pure isfile probing, no
        X_OK probing per R49. Returns ("", "", "unresolved") when nothing
        is found (caller keeps toolchain defaults).
        """
        def _ok(p):
            try:
                return bool(p) and os.path.isfile(p)
            except Exception:
                return False

        def _conf(key):
            try:
                return (self.conf.get(key, check_type=str) or "").split()[0]
            except Exception:
                return ""

        conf_cc = _conf("tools.build:compiler_executables:c")
        conf_cxx = _conf("tools.build:compiler_executables:cpp")
        if _ok(conf_cc) and _ok(conf_cxx):
            return conf_cc, conf_cxx, "profile"
        if _ok(conf_cc) and not conf_cxx:
            sib = conf_cc + "++" if conf_cc.endswith("clang") else ""
            if _ok(sib):
                return conf_cc, sib, "profile-cxx-sibling"

        cc_names = ["clang", "cc", "gcc"]
        cxx_names = ["clang++"]
        cand_dirs = []
        for d in (
            "/storage/Users/currentUser/usr/local/bin",
            os.path.join(os.path.expanduser("~"), ".harmonybrew", "bin"),
            "/data/service/hnp/bin",
            "/opt/llvm/bin",
            "/usr/local/bin",
            "/usr/bin",
        ):
            if d and d not in cand_dirs:
                cand_dirs.append(d)
        # Same SDK root as LD_LIBRARY_PATH's llvm/lib (preflight shows
        # .../ohos-sdk_26.0.0.18/ohos/native/llvm/lib): sibling bin dir.
        try:
            for entry in (os.environ.get("LD_LIBRARY_PATH", "") or "").split(os.pathsep):
                if "llvm" in entry:
                    sib = os.path.join(os.path.dirname(entry.rstrip("/")), "bin")
                    if sib not in cand_dirs:
                        cand_dirs.append(sib)
        except Exception:
            pass

        found_cc, found_cxx = "", ""
        for name in cc_names:
            w = shutil.which(name)
            if _ok(w):
                found_cc = w
                break
        for name in cxx_names:
            w = shutil.which(name)
            if _ok(w):
                found_cxx = w
                break
        if not found_cc or not found_cxx:
            for d in cand_dirs:
                try:
                    if not os.path.isdir(d):
                        continue
                except Exception:
                    continue
                if not found_cc:
                    for n in cc_names:
                        p = os.path.join(d, n)
                        if _ok(p):
                            found_cc = p
                            break
                if not found_cxx:
                    for n in cxx_names:
                        p = os.path.join(d, n)
                        if _ok(p):
                            found_cxx = p
                            break
                if found_cc and found_cxx:
                    break
        if _ok(conf_cc) and found_cc and found_cc != conf_cc:
            pass  # prefer discovered working binary over stale conf path
        cc = found_cc or (conf_cc if _ok(conf_cc) else "")
        cxx = found_cxx or (conf_cxx if _ok(conf_cxx) else "")
        if cc and not cxx and cc.endswith("clang"):
            sib = cc + "++"
            if _ok(sib):
                cxx = sib
        if cc:
            return cc, cxx, "fallback"
        return "", "", "unresolved"

    def _usable_shell(self):
        # HMBS capability shell=/bin/sh; the repo profile pins HNP bash which
        # exists as a file on some hosts but is not executable
        # ("inaccessible or not found"). Hard-prefer /bin/sh and never return
        # the HNP path, even if isfile() is true for it.
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
        # then HMBS_TMPDIR/HMBS_INSTALL, else build-local tmp. Reuse HMBS
        # values when present (readonly_tmp: never fall back to /tmp).
        for var in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR", "HMBS_INSTALL"):
            cand = os.environ.get(var, "")
            if cand and os.path.isdir(cand):
                return cand
        tmpd = os.path.join(self.build_folder, "tmp")
        if makedirs:
            os.makedirs(tmpd, exist_ok=True)
        return tmpd

    def package(self):
        # Same stale-CONFIG_SHELL reason as build(): run make install
        # explicitly with inline good-shell/TMPDIR exports (juise-style)
        # instead of Autotools.install() which inherits the profile's bad
        # HNP bash via env="conanbuild".
        shell = self._usable_shell()
        tmpdir = self._usable_tmpdir(makedirs=True)
        fix = (
            f'export SHELL="{shell}" && export CONFIG_SHELL="{shell}" && '
            f'export TMPDIR="{tmpdir}" && export TMP="{tmpdir}" && export TEMP="{tmpdir}" && '
        )
        cfg_dir = self.source_folder if os.path.isfile(
            os.path.join(self.source_folder, "Makefile")) else self.build_folder
        self.run(fix + f'make install DESTDIR="{self.package_folder}"', cwd=cfg_dir, env="conanbuild")
        import glob

        lib_dir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(lib_dir):
            for pattern in ("*.la", "*.dylib"):
                for f in glob.glob(os.path.join(lib_dir, pattern)):
                    os.remove(f)
        # Upstream installs bin/bwm-ng (historical binary name). This package
        # is named bwm, so also provide bin/bwm as an alias copy; both are
        # the same static binary. Consumers may use either name.
        import shutil

        src_bin = os.path.join(self.package_folder, "bin", "bwm-ng")
        dst_bin = os.path.join(self.package_folder, "bin", "bwm")
        try:
            if os.path.isfile(src_bin) and not os.path.isfile(dst_bin):
                shutil.copy2(src_bin, dst_bin)
        except Exception:
            pass
        # True-machine diagnosis (2nd test_package retry): PATH prepend alone
        # was proven insufficient — preflight still reported "neither bwm nor
        # bwm-ng found on PATH" even with package bin/ on PATH. That means
        # bin/ is empty or files lack +x (HMDFS chmod=0). Verify here and
        # fall back to copying the just-linked binary straight from the
        # build tree (src/bwm-ng) so packaging never silently yields an
        # empty bin/. Use conan copy + chmod||true (HMDFS tolerates chmod
        # failure); log ls -l so the next preflight shows real evidence.
        try:
            bin_dir = os.path.join(self.package_folder, "bin")
            self.output.info(f"bwm package bin listing: {sorted(os.listdir(bin_dir)) if os.path.isdir(bin_dir) else 'MISSING bin/'}")
        except Exception as e:
            self.output.warning(f"bwm package bin listing failed: {e}")
        if not os.path.isfile(src_bin):
            cand_built = [
                os.path.join(cfg_dir, "src", "bwm-ng"),
                os.path.join(cfg_dir, "bwm-ng"),
                os.path.join(cfg_dir, "src", "bwm"),
                os.path.join(self.source_folder, "src", "bwm-ng"),
                os.path.join(self.build_folder, "src", "bwm-ng"),
            ]
            for cand in cand_built:
                if os.path.isfile(cand):
                    try:
                        os.makedirs(os.path.dirname(src_bin), exist_ok=True)
                        shutil.copyfile(cand, src_bin)
                        self.output.info(f"bwm package fallback: copied built binary {cand} -> {src_bin}")
                        break
                    except Exception as e:
                        self.output.warning(f"bwm package fallback copy failed {cand}: {e}")
            try:
                if os.path.isfile(src_bin) and not os.path.isfile(dst_bin):
                    shutil.copyfile(src_bin, dst_bin)
                    self.output.info(f"bwm package fallback: alias copy {src_bin} -> {dst_bin}")
            except Exception as e:
                self.output.warning(f"bwm package fallback alias failed: {e}")
        for _b in (src_bin, dst_bin):
            try:
                if os.path.isfile(_b):
                    os.chmod(_b, 0o755)
            except OSError:
                pass
        try:
            self.run(f'ls -l "{self.package_folder}/bin" 2>&1 || true')
        except Exception:
            pass

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
