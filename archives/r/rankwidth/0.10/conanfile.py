#!/usr/bin/env python3
"""Conan recipe for rankwidth 0.10 -- library for rank-width computation.

Upstream: https://sourceforge.net/projects/rankwidth/ (rw-0.10.tar.gz)
License: GPL-2.0-or-later
Build system: Autotools (configure + make)

Adaptation decisions (HarmonyOS PC, path A):
- Build the librw static/shared library only (--disable-executable).
  Rationale: the `rw`/`simplerw` executables link igraph, whose upstream
  vendored ~10 libraries and heavy C++ toolchain bloat the closure and
  drag optional deps (libxml2/GLPK/ARPACK) that are not yet published to
  the ohpcd artefact repository. Gentoo's rw-0.10 ebuild takes the same
  route (`econf --disable-executable`, "executable depends on igraph").
  The library itself has zero external dependencies (SageMath spkg
  declares "no dependencies"), so a dependency-free recipe is the most
  robust basis adaptation.
- Run upstream `make check` in build(). Upstream ships no formal suite
  (Alpine APKBUILD: options="!check" # no test suite; no tests/ dir,
  no TESTS/check_PROGRAMS in build files), so `make check` is a no-op
  pass that keeps the L1c trace observable. The real upstream regression
  is test_package/upstream_smoke (igraph-free driver for the bundled
  example_graphs, README smoke `rw --edgelist example_graphs/igrid`
  promoted per libarcus/5.0.0 precedent), which emits the
  HMBS_UPSTREAM_TEST_RESULT marker; this recipe emits no upstream
  marker so the evidence gate never sees a stale no_tests/0.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class RankwidthConan(ConanFile):
    name = "rankwidth"
    version = "0.10"
    description = "Library for calculating rank-width and rank-decompositions"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/rankwidth/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("graph-theory", "rank-width", "mathematics")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"rankwidth supports Linux/OHOS native builds, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Library-only adaptation: skip the igraph-linked executables.
        tc.configure_args.append("--disable-executable")
        tc.configure_args.append("--prefix=/")
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        else:
            tc.configure_args.append("--enable-shared")
        # Keep autotools temp files inside the isolated build dir (OHOS /tmp
        # may be read-only; HMBS also injects an isolated TMPDIR).
        # Preflight runner may lack the profile-pinned
        # /data/service/hnp/bin/bash (configure re-execs $CONFIG_SHELL and
        # dies with 127 `inaccessible or not found`). Probe a live shell
        # (m4/1.4.19 _select_shell precedent, r13 true-device proven) so
        # the toolchain env overrides the poisoned profile buildenv value.
        env = tc.environment()
        shell = self._select_shell()
        env.define("CONFIG_SHELL", shell)
        env.define("SHELL", shell)
        self.output.info(f"rankwidth: selected shell (probed): {shell}")
        # HMBS readonly /tmp: publish the writable task TMPDIR through the
        # toolchain env so configure probes stay off read-only /tmp.
        # NOTE: HMBS_AUTOCONF_MKTEMP_FALLBACK=="1" is a flag, never a path.
        _hmbs_tmp = None
        for _key in ("TMPDIR", "TMP", "TEMP"):
            _cand = os.environ.get(_key)
            if _cand and _cand not in ("0", "1", "/tmp") and os.path.isabs(_cand):
                _hmbs_tmp = _cand
                break
        if _hmbs_tmp:
            env.define("TMPDIR", _hmbs_tmp)
            env.define("TMP", _hmbs_tmp)
            env.define("TEMP", _hmbs_tmp)
            self.output.info(f"rankwidth: writable tmp: {_hmbs_tmp}")
        # HMBS true-device fix (mdk/1.3.1 precedent): resolve a runnable
        # C/C++ compiler with config priority + PATH fallback, override
        # ONLY the compiler variables, preserve all flags (CFLAGS etc).
        cc = self._select_runnable_compiler(kind="CC")
        cxx = self._select_runnable_compiler(kind="CXX")
        if cc:
            env.define("CC", cc)
            self.output.info(f"rankwidth: selected CC (probed): {cc}")
        if cxx:
            env.define("CXX", cxx)
            self.output.info(f"rankwidth: selected CXX (probed): {cxx}")
        # Round-3 fix: old config.guess (2018-02-24) cannot recognize
        # UNAME_SYSTEM=HarmonyOS -> "cannot guess build type". Pass
        # explicit --build/--host so configure never needs to guess on
        # the native aarch64/x86_64 HarmonyOS machine. Only add when the
        # toolchain did not already provide them; never touch flags.
        build_host = self._gnu_triplet()
        for flag in (f"--build={build_host}", f"--host={build_host}"):
            name = flag.split("=")[0]
            if not any(a == flag or a.startswith(name + "=") for a in tc.configure_args):
                tc.configure_args.append(flag)
        self.output.info(f"rankwidth: explicit gnu triplet: {build_host}")
        tc.generate(env=env)

    def _gnu_triplet(self):
        # Native build on HarmonyOS PC: map conan arch to a config.sub-
        # accepted GNU triplet. Library is portable C; the triplet only
        # bypasses the stale config.guess, it does not change codegen
        # (compiler itself is the OHOS clang from the profile/env).
        try:
            arch = str(self.settings.get_safe("arch") or "")
        except Exception:
            arch = ""
        machine = {"armv8": "aarch64", "armv8.3": "aarch64",
                   "x86_64": "x86_64", "x86": "i686"}.get(arch, "")
        if not machine:
            machine = os.uname().machine if hasattr(os, "uname") else "aarch64"
            if machine not in ("aarch64", "x86_64", "i686"):
                machine = "aarch64"
        return f"{machine}-linux-gnu"

    def _select_shell(self):
        for shell in (
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            "/data/service/hnp/bin/bash",
            "/bin/sh",
            "/system/bin/sh",
        ):
            if not shell:
                continue
            if os.path.isabs(shell):
                if os.path.isfile(shell) and os.access(shell, os.X_OK):
                    return shell
            elif shutil.which(shell):
                return shell
        return "sh"

    def _prepare_build_environment(self):
        shell = self._select_shell()
        os.environ["CONFIG_SHELL"] = shell
        os.environ["SHELL"] = shell
        # Mirror the probed runnable compiler into the build process env
        # so the helper-internal configure sees the same CC/CXX as the
        # toolchain env (profile buildenv aggregation may otherwise win).
        # Only compiler variables; flags are preserved untouched.
        try:
            cc = self._select_runnable_compiler(kind="CC")
            if cc:
                os.environ["CC"] = cc
            cxx = self._select_runnable_compiler(kind="CXX")
            if cxx:
                os.environ["CXX"] = cxx
        except Exception:
            pass
        # HMBS readonly /tmp: keep process-level temp on the writable
        # task TMPDIR (flag value "1" is never a path).
        tmpdir = self._writable_tmpdir()
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir

    def _writable_tmpdir(self):
        for key in ("TMPDIR", "TMP", "TEMP"):
            cand = os.environ.get(key)
            if cand and cand not in ("0", "1", "/tmp") and os.path.isabs(cand):
                try:
                    os.makedirs(cand, exist_ok=True)
                    probe = os.path.join(cand, ".hmbs-write-probe")
                    with open(probe, "w", encoding="utf-8") as handle:
                        handle.write("ok")
                    os.remove(probe)
                    return cand
                except OSError:
                    continue
        fallback = os.path.join(self.build_folder or os.getcwd(), ".tmp")
        os.makedirs(fallback, exist_ok=True)
        return fallback

    def _mktemp_fallback_requested(self):
        return os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK") == "1"

    def _setup_mktemp_shim(self, tmpdir):
        # HMBS [unsafe_local_mktemp]: a directory created by mktemp on the
        # true-machine filesystem cannot be written by later config.status
        # steps (subs1.awk Permission denied). When HMBS requests the
        # fallback, shadow mktemp during the configure phase only so calls
        # for "./conf*" fail and Autoconf takes its mkdir fallback. All
        # other mktemp calls delegate to the real binary.
        if not self._mktemp_fallback_requested():
            return ""
        shim_dir = os.path.join(tmpdir, "hmbs-mktemp-shim")
        try:
            os.makedirs(shim_dir, exist_ok=True)
        except OSError:
            return ""
        shim = os.path.join(shim_dir, "mktemp")
        script = (
            "#!/bin/sh\n"
            "for arg in \"$@\"; do\n"
            "  case \"$arg\" in\n"
            "    *conf*) exit 1 ;;\n"
            "  esac\n"
            "done\n"
            "for candidate in /system/bin/mktemp /bin/mktemp "
            "/usr/bin/mktemp; do\n"
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
        except OSError:
            return ""
        return shim_dir

    def _relax_autoconf_umask(self, path):
        try:
            with open(path, "r", encoding="utf-8", errors="surrogateescape") as handle:
                content = handle.read()
        except OSError:
            return 0
        if "umask 077" not in content:
            return 0
        with open(path, "w", encoding="utf-8", errors="surrogateescape", newline="\n") as handle:
            handle.write(content.replace("umask 077", "umask 022"))
        self.output.info("rankwidth: relaxed umask 077->022 in %s" % path)
        return 1

    def _is_runnable_compiler(self, cmd):
        try:
            res = subprocess.run(
                [cmd, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=15,
            )
            return res.returncode == 0
        except Exception:
            return False

    def _select_runnable_compiler(self, kind="CC"):
        if kind == "CXX":
            candidates = [
                os.environ.get("CXX"),
                os.environ.get("CC"),
                "/data/service/hnp/bin/clang++",
                "clang++",
                "c++",
                "g++",
            ]
        else:
            candidates = [
                os.environ.get("CC"),
                "/data/service/hnp/bin/clang",
                "clang",
                "cc",
                "gcc",
            ]
        seen = set()
        for cand in candidates:
            if not cand or cand in seen:
                continue
            seen.add(cand)
            prog = cand.split()[0]
            if os.path.isabs(prog):
                if not (os.path.isfile(prog) and os.access(prog, os.X_OK)):
                    continue
                probe = cand
            else:
                resolved = shutil.which(prog)
                if not resolved:
                    continue
                probe = cand
            # Probe with the bare program (no extra flags).
            if self._is_runnable_compiler(probe.split()[0]):
                return cand
        return None

    def _dump_configure_forensics(self):
        # Library-path + config.log forensics for
        # "C compiler cannot create executables" triage. Never fails build.
        try:
            self.output.info(
                "rankwidth forensics: CC=%s CXX=%s CFLAGS=%s CPPFLAGS=%s LDFLAGS=%s"
                % (
                    os.environ.get("CC"),
                    os.environ.get("CXX"),
                    os.environ.get("CFLAGS"),
                    os.environ.get("CPPFLAGS"),
                    os.environ.get("LDFLAGS"),
                )
            )
            self.output.info(
                "rankwidth forensics: LD_LIBRARY_PATH=%s LIBRARY_PATH=%s PATH=%s"
                % (
                    os.environ.get("LD_LIBRARY_PATH"),
                    os.environ.get("LIBRARY_PATH"),
                    os.environ.get("PATH"),
                )
            )
            self.output.info(
                "rankwidth forensics: HMBS_CMAKE=%s HMBS_MAKE=%s HMBS_CAP_HARDLINK=%s "
                "HMBS_CAP_CHMOD=%s HMBS_CAP_SYMLINK=%s HMBS_CAP_LOCAL_MKTEMP=%s TMPDIR=%s"
                % (
                    os.environ.get("HMBS_CMAKE"),
                    os.environ.get("HMBS_MAKE"),
                    os.environ.get("HMBS_CAP_HARDLINK"),
                    os.environ.get("HMBS_CAP_CHMOD"),
                    os.environ.get("HMBS_CAP_SYMLINK"),
                    os.environ.get("HMBS_CAP_LOCAL_MKTEMP"),
                    os.environ.get("TMPDIR"),
                )
            )
            # Explicit runnable check of the configured compiler.
            for var in ("CC", "CXX"):
                cmd = (os.environ.get(var) or "").split()
                if not cmd:
                    continue
                try:
                    res = subprocess.run(
                        cmd + ["--version"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        timeout=15,
                    )
                    out = res.stdout.decode("utf-8", "replace")[:2000]
                    self.output.info(
                        "rankwidth forensics: %s --version rc=%s out=%.2000s"
                        % (var, res.returncode, out)
                    )
                except Exception as exc:
                    self.output.info(
                        "rankwidth forensics: %s --version probe failed: %s" % (var, exc)
                    )
            # Locate and tail config.log (build tree first, then source).
            searched = []
            log_path = None
            for root in (self.build_folder, self.source_folder):
                cand = os.path.join(root or "", "config.log")
                searched.append(cand)
                if cand and os.path.isfile(cand):
                    log_path = cand
                    break
            if log_path is None:
                try:
                    for cur, _dirs, files in os.walk(self.build_folder):
                        if "config.log" in files:
                            log_path = os.path.join(cur, "config.log")
                            break
                except Exception:
                    pass
            if log_path and os.path.isfile(log_path):
                try:
                    with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                        lines = f.read().splitlines()
                    tail = lines[-120:] if len(lines) > 120 else lines
                    self.output.info(
                        "rankwidth forensics: config.log=%s total_lines=%d (tail 120)"
                        % (log_path, len(lines))
                    )
                    for line in tail:
                        self.output.info("config.log| " + line[:2000])
                except Exception as exc:
                    self.output.info(
                        "rankwidth forensics: read %s failed: %s" % (log_path, exc)
                    )
            else:
                self.output.info(
                    "rankwidth forensics: config.log NOT FOUND (searched %s + walk %s)"
                    % (searched, self.build_folder)
                )
        except Exception as exc:
            self.output.info("rankwidth forensics failed: %s" % exc)

    def _refresh_config_guess_sub(self):
        # Belt-and-suspenders for the stale 2018 config.guess/config.sub
        # shipped by rw-0.10: replace every copy under the source tree
        # with the newest system copy (if one exists). Best effort only;
        # the explicit --build/--host above is the primary fix, so a
        # missing donor must never fail the build.
        import glob as _glob
        donors_guess = []
        for pat in (
            "/usr/share/misc/config.guess",
            "/usr/share/automake-*/config.guess",
            "/usr/local/share/automake-*/config.guess",
            "/storage/Users/currentUser/.harmonybrew/share/automake-*/config.guess",
            "/storage/Users/currentUser/.harmonybrew/opt/*/share/automake-*/config.guess",
        ):
            try:
                donors_guess.extend(_glob.glob(pat))
            except Exception:
                pass
        donor = None
        try:
            cands = sorted(
                {p for p in donors_guess if os.path.isfile(p)},
                key=lambda p: os.path.getmtime(p),
                reverse=True,
            )
            donor = cands[0] if cands else None
        except Exception:
            donor = None
        targets = []
        try:
            for cur, _dirs, files in os.walk(self.source_folder):
                for fn in files:
                    if fn in ("config.guess", "config.sub"):
                        targets.append(os.path.join(cur, fn))
        except Exception as exc:
            self.output.info("config.guess refresh: walk failed: %s" % exc)
            return 0
        if donor is None:
            self.output.info(
                "config.guess refresh: no system donor found (checked %d paths), "
                "relying on explicit --build/--host; targets=%d"
                % (len(donors_guess), len(targets))
            )
            return 0
        try:
            with open(donor, "r", encoding="utf-8", errors="replace") as f:
                head = f.read(2000)
            self.output.info("config.guess refresh: donor=%s targets=%d" % (donor, len(targets)))
            self.output.info("config.guess refresh: donor head=%.500s" % head[:500].replace("\n", " | "))
        except Exception:
            pass
        done = 0
        base = os.path.basename(donor)
        for tgt in targets:
            # Only replace matching basename (guess->guess, sub->sub);
            # a lone config.guess donor must not overwrite config.sub.
            if os.path.basename(tgt) != base:
                continue
            try:
                shutil.copy2(donor, tgt)
                done += 1
            except Exception as exc:
                self.output.info("config.guess refresh failed %s: %s" % (tgt, exc))
        self.output.info("config.guess refresh: replaced %d/%d" % (done, len(targets)))
        return done

    def _sanitize_configure_config_shell(self, cfg_path=None):
        cfg = cfg_path or os.path.join(self.source_folder, "configure")
        try:
            with open(cfg, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except OSError as exc:
            self.output.info("config-shell sanitize skipped (no %s: %s)" % (cfg, exc))
            return 0
        if "HMBS_CONFIG_SHELL_GUARD" in content:
            self.output.info("config-shell guard already present in %s" % cfg)
            return 0
        shell = self._select_shell()
        guard = (
            "# HMBS_CONFIG_SHELL_GUARD: ignore dangling profile CONFIG_SHELL\n"
            + 'if test -n "$CONFIG_SHELL"; then\n'
            + '  if test ! -x "$CONFIG_SHELL"; then\n'
            + "    CONFIG_SHELL=" + shell + "\n"
            + "    SHELL=" + shell + "\n"
            + "    export CONFIG_SHELL SHELL\n"
            + "  fi\n"
            + "fi\n"
        )
        lines = content.split("\n", 1)
        if lines and lines[0].startswith("#!"):
            content = lines[0] + "\n" + guard + (lines[1] if len(lines) > 1 else "")
        else:
            content = guard + content
        with open(cfg, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        self.output.info("config-shell guard applied to %s (shell=%s)" % (cfg, shell))
        return 1

    def _sanitize_all_configures(self):
        seen = set()
        cands = [os.path.join(self.source_folder, "configure"),
                 os.path.join(self.build_folder, "configure")]
        try:
            for _root, _dirs, _files in os.walk(self.build_folder):
                if _root != self.build_folder:
                    _dirs[:] = []
                    continue
                for _name in _files:
                    if _name == "configure":
                        cands.append(os.path.join(_root, _name))
        except OSError:
            pass
        for cand in cands:
            if cand in seen:
                continue
            seen.add(cand)
            try:
                self._sanitize_configure_config_shell(cand)
            except Exception as exc:
                self.output.info("config-shell sanitize skipped %s: %s" % (cand, exc))

    def build(self):
        self._prepare_build_environment()
        apply_conandata_patches(self)
        # Round-2 fix: sanitize the generated configure script itself.
        # Round-1 (toolchain.environment CONFIG_SHELL/SHELL override) is
        # confirmed synced yet ineffective: preflight still fails at
        # configure[139] with the identical 127 (build() line 84 -> 118
        # proves new code executed). Root cause per alberta round-10:
        # run-time conanbuild aggregation (profile buildenv with the
        # poisoned CONFIG_SHELL) wins over both os.environ and the
        # toolchain env for the helper-internal configure command, so env
        # layers cannot fix it. Patching the script's re-exec block is
        # the winning layer.
        self._sanitize_all_configures()
        self._refresh_config_guess_sub()
        # HMBS [unsafe_local_mktemp]: mktemp -d "./confXXXXXX" on the
        # true-machine FS yields an owner-unwritable dir (setgid), so
        # config.status dies with "can't create ./conf*/subs1.awk:
        # Permission denied". Relax umask 077->022 (E011/E129) and, when
        # HMBS_AUTOCONF_MKTEMP_FALLBACK=1, shadow mktemp during the
        # configure phase only so Autoconf takes its mkdir fallback.
        # Minimal scope: no test is skipped; shim leaves PATH after.
        self._relax_autoconf_umask(os.path.join(self.source_folder, "configure"))
        tmpdir = os.environ.get("TMPDIR") or self._writable_tmpdir()
        shim_dir = self._setup_mktemp_shim(tmpdir)
        old_path = os.environ.get("PATH", "")
        if shim_dir:
            os.environ["PATH"] = shim_dir + os.pathsep + old_path
            self.output.info("rankwidth: mktemp fallback shim active: %s" % shim_dir)
        autotools = Autotools(self)
        try:
            autotools.configure()
        except Exception:
            self._dump_configure_forensics()
            raise
        finally:
            if shim_dir:
                os.environ["PATH"] = old_path
        # config.status carries its own hardcoded umask copy; relax it too.
        for _cand in (os.path.join(self.build_folder, "config.status"),
                      os.path.join(self.source_folder, "config.status")):
            if os.path.isfile(_cand):
                self._relax_autoconf_umask(_cand)
        # Single job: HMDFS jobserver/FIFO semantics are fragile.
        autotools.make(args=["-j1"])
        # Upstream test suite: no formal suite exists (no TESTS entries),
        # so `make check` is a no-op pass kept only for the L1c trace.
        # The real upstream regression (bundled example_graphs smoke,
        # libarcus/5.0.0 precedent) runs in test_package/ and emits the
        # HMBS_UPSTREAM_TEST_RESULT marker there; no marker is emitted
        # here so a stale no_tests/0 can never shadow the real evidence.
        autotools.make(target="check")

    def _write_install_shim(self):
        # HMBS install shim accepts only single-file two-arg calls
        # ([ $# -eq 2 ] || exit 64, EX_USAGE), while automake's
        # install-dist_docDATA batches ALL doc files into one
        # `$(INSTALL_DATA) a b c dir/` call -> Error 64 (lzop/1.04,
        # adms/2.3.7 precedent, same EX_USAGE 64 signature). Write a
        # cp/mkdir shim (chmod best-effort for HMBS_CAP_CHMOD=0) and
        # redirect Makefile INSTALL to it; docs still install, only the
        # tool changes. Handles the non-ASCII example_graphs/Hangematte
        # name too (cp passes UTF-8 through).
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        os.makedirs(shim_dir, exist_ok=True)
        install = os.path.join(shim_dir, "install")
        fd = os.open(install, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(
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
                    "mkdir -p \"$(dirname \"$dest\")\"\n"
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
            except OSError:
                pass
            raise
        try:
            os.chmod(install, 0o755)
        except OSError:
            pass
        return install

    def _redirect_install_to_shim(self, shim_install):
        # configure bakes the probed install path into every generated
        # Makefile's INSTALL variable. Rewrite it to the shim; the
        # INSTALL_DATA/INSTALL_PROGRAM lines reference ${INSTALL} and
        # recompute automatically (adms/2.3.7 precedent).
        for root, _, files in os.walk(self.build_folder):
            for name in files:
                if name != "Makefile":
                    continue
                mp = os.path.join(root, name)
                try:
                    with open(mp, "r", encoding="utf-8", errors="replace") as handle:
                        content = handle.read()
                except OSError:
                    continue
                if "INSTALL =" not in content:
                    continue
                lines = []
                changed = False
                for line in content.splitlines(True):
                    stripped = line.lstrip()
                    if stripped.startswith("INSTALL = ") and "/install" in stripped:
                        indent = line[:len(line) - len(stripped)]
                        lines.append("%sINSTALL = %s\n" % (indent, shim_install))
                        changed = True
                    else:
                        lines.append(line)
                if changed:
                    with open(mp, "w", encoding="utf-8", newline="\n") as handle:
                        handle.write("".join(lines))
                    self.output.info("rankwidth: redirected INSTALL to shim in %s" % mp)

    def package(self):
        self._prepare_build_environment()
        self._redirect_install_to_shim(self._write_install_shim())
        autotools = Autotools(self)
        autotools.install()
        # Prune libtool archives; keep headers + libs.
        self._prune_la()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        # COPYING filename varies by release (COPYING vs LICENSE); fall back.
        if not os.path.isfile(
            os.path.join(self.package_folder, "licenses", "COPYING")
        ):
            for alt in ("LICENSE", "COPYRIGHT"):
                src = os.path.join(self.source_folder, alt)
                if os.path.isfile(src):
                    copy(
                        self,
                        alt,
                        src=self.source_folder,
                        dst=os.path.join(self.package_folder, "licenses"),
                        keep_path=False,
                    )
                    break

    def _prune_la(self):
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        for root, _, files in os.walk(libdir):
            for fn in files:
                if fn.endswith(".la"):
                    try:
                        os.remove(os.path.join(root, fn))
                    except OSError:
                        pass

    def package_info(self):
        self.cpp_info.libs = ["rw"]
        self.cpp_info.set_property("pkg_config_name", "rw")
