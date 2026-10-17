#!/usr/bin/env python3
"""Conan recipe — libfuzzy2 2.14.1 (Autotools).

libfuzzy2 is the fuzzy-hashing (CTPH) library from the ssdeep project.
Upstream ships a release configure script plus libtool; the library target
is libfuzzy.la (SONAME libfuzzy.so.2, Debian libfuzzy2) and a statically
linked ssdeep CLI built from C++ sources.
"""

import json
import os
import re

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# Profile ci/conan/profiles/ohos-aarch64 sets
# CONFIG_SHELL=/data/service/hnp/bin/bash via [buildenv], but that path is
# absent on the HMBS preflight device (configure[159]: inaccessible or not
# found, Error 127). HMBS only guarantees /bin/sh.
_BAD_SHELL = "/data/service/hnp/bin/bash"
_DEVICE_SHELL_FALLBACKS = ("/bin/sh", "/system/bin/sh")


def _device_shell():
    """Pick a shell that exists on the build machine.

    Prefer HMBS-injected SHELL/CONFIG_SHELL unless polluted with the absent
    profile path; otherwise fall back to /bin/sh (HMBS guaranteed) then
    /system/bin/sh (CI worker precedent: opusfile/abx/cyrus-sasl-login).
    Never returns the known-bad profile path.
    """
    for cand in (os.environ.get("SHELL"), os.environ.get("CONFIG_SHELL")):
        if cand and cand != _BAD_SHELL and os.path.isfile(cand):
            return cand
    for cand in _DEVICE_SHELL_FALLBACKS:
        if os.path.isfile(cand):
            return cand
    # Local Windows authoring host has neither; return the HMBS guarantee
    # so generated commands stay correct for the device.
    return "/bin/sh"


def _resolve_compilers(conanfile):
    """Sanitize profile compiler paths (ladspa-sdk precedent).

    ci/conan/profiles/ohos-aarch64 advertises absolute CC/CXX
    (/data/service/hnp/bin/clang{,++}). On some HMBS preflight devices
    that absolute path is a dead symlink / inaccessible, so configure
    fails with `/data/service/hnp/bin/clang: inaccessible or not found`
    (exit 127) -> `C compiler cannot create executables`. Bare `clang`
    resolves via PATH (conanbuild.sh prepends the HNP bin dir), so only
    trust the conf path when it is a real executable file; otherwise
    fall back to the bare name and let PATH resolve it.
    """
    ce = None
    try:
        ce = conanfile.conf.get("tools.build:compiler_executables",
                                default=None, check_type=dict)
    except Exception:
        try:
            ce = conanfile.conf.get("tools.build:compiler_executables",
                                    default=None)
        except Exception:
            ce = None
    cc = cxx = None
    if ce:
        try:
            d = json.loads(ce) if isinstance(ce, str) else ce
            if isinstance(d, dict):
                cc = d.get("c")
                cxx = d.get("cpp")
        except Exception:
            pass

    def _sanitize(candidate, fallback):
        if candidate and os.path.isfile(candidate):
            try:
                if os.access(candidate, os.X_OK):
                    return candidate
            except Exception:
                pass
            conanfile.output.warning(
                f"profile compiler '{candidate}' not executable, "
                f"falling back to '{fallback}' via PATH"
            )
            return fallback
        if candidate:
            conanfile.output.warning(
                f"profile compiler '{candidate}' missing, "
                f"falling back to '{fallback}' via PATH"
            )
        return fallback

    # Prefer PATH-resolved bare names when the absolute path is dead.
    cc_fallback = "clang"
    cxx_fallback = "clang++"
    cc = _sanitize(cc, cc_fallback)
    cxx = _sanitize(cxx, cxx_fallback)
    # Keep a trace for HMBS_DIAG forensics.
    try:
        conanfile.output.info(f"resolved compilers: CC={cc} CXX={cxx}")
    except Exception:
        pass
    return cc, cxx


def _patch_config_sub_for_ohos(conanfile):
    """Teach vendor config.sub to accept aarch64-unknown-linux-ohos (E072).

    ssdeep-2.14.1 ships a pre-OHOS config.sub, so
    `--host=aarch64-unknown-linux-ohos` fails with
    "Invalid configuration ... config.sub ... failed".
    Insert `linux-ohos*` alongside the existing `linux-android*` entries
    in every config.sub copy (top-level and build-aux variants), following
    the zeitgeist 0002-config-sub-ohos.patch pattern but applied at runtime
    via anchor replacement so it works across config.sub vintages without
    a context-sensitive patch file. Idempotent: skips files that already
    know linux-ohos.
    """
    candidates = [
        os.path.join(conanfile.source_folder, "config.sub"),
        os.path.join(conanfile.source_folder, "build-aux", "config.sub"),
        os.path.join(conanfile.source_folder, "config", "config.sub"),
        os.path.join(conanfile.source_folder, "aux", "config.sub"),
    ]
    patched_any = False
    for path in candidates:
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError as exc:
            conanfile.output.warning(f"config.sub read skipped {path}: {exc}")
            continue
        if "linux-ohos" in text:
            continue
        orig = text
        # Kernel-OS whitelist (e.g. `linux-gnu* | linux-android* | ...` and
        # the maybe_os recognizer `nto-qnx* | linux-gnu* | linux-android*`).
        if "linux-android*" in text:
            text = text.replace("linux-android*", "linux-ohos* | linux-android*")
        # OS whitelist with dash prefix (`-linux-android*`).
        if "-linux-ohos*" not in text and "-linux-android*" in text:
            text = text.replace("-linux-android*", "-linux-ohos* | -linux-android*")
        # Fallback OS whitelist (`case $os in` with bare `android*`).
        if "linux-ohos" not in text and "| android*" in text:
            text = text.replace("| android*", "| ohos* | android*")
        if text != orig:
            try:
                with open(path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(text)
                conanfile.output.info(f"config.sub patched for OHOS: {path}")
                patched_any = True
            except OSError as exc:
                conanfile.output.warning(f"config.sub patch failed {path}: {exc}")
    if not patched_any:
        conanfile.output.warning(
            "config.sub OHOS patch applied to 0 files "
            "(already patched or no config.sub found)"
        )


def _writable_tmpdir(build_folder):
    """Return a writable tmpdir (readonly_tmp: device /tmp is read-only).

    Priority follows HMBS-injected capabilities (courier-unicode
    precedent): a path-valued HMBS_AUTOCONF_MKTEMP_FALLBACK first, then
    HMBS_TMPDIR, TMPDIR, TMP, TEMP (never bare /tmp). Each candidate is
    created and probe-tested for writability; final fallback is a
    build-folder-local directory. Only replaces the temp-file root.
    """
    candidates = []
    fallback_var = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK", "")
    if fallback_var and fallback_var not in ("0", "1"):
        candidates.append(fallback_var)
    for key in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
        cand = os.environ.get(key, "")
        if cand and cand != "/tmp" and cand not in candidates:
            candidates.append(cand)
    for cand in candidates:
        try:
            os.makedirs(cand, exist_ok=True)
            probe = os.path.join(cand, ".hmbs_probe")
            with open(probe, "w") as handle:
                handle.write("probe")
            try:
                os.remove(probe)
            except OSError:
                pass
            return cand
        except OSError:
            continue
    tmpdir = os.path.join(build_folder, "tmp")
    try:
        os.makedirs(tmpdir, exist_ok=True)
    except OSError:
        pass
    return tmpdir


def _install_sh_for_ohos(conanfile, workdir):
    """Stage a working BSD-install for `make install` (E174/E108).

    configure accepted the HMBS shim
    (`.../runtime/<pkg>/bin/install -c`) as a BSD-compatible INSTALL,
    but on the device that shim silently installs nothing: libtool's
    `install -c .libs/libfuzzy.a <DESTDIR>/lib/libfuzzy.a` reports
    success yet the file is absent, so the next step
    `chmod 644 <DESTDIR>/lib/libfuzzy.a` dies with
    `No such file or directory` and `install-libLTLIBRARIES` fails.
    Bypass the shim (cyrus-sasl-login precedent): copy the tarball's
    own `install-sh` aside, point its shebang at the device shell, and
    return the staged path so package() can override
    INSTALL/INSTALL_PROGRAM/INSTALL_DATA/INSTALL_SCRIPT/MKDIR_P on the
    `make install` command line (command-line variables beat the
    shim path baked into the generated Makefiles). Returns None when
    no install-sh exists, letting the caller fall back to the default.
    Pure-Python copy: needs no chmod persistence (HMBS_CAP_CHMOD=0).
    """
    candidates = [
        os.path.join(conanfile.source_folder, "install-sh"),
        os.path.join(conanfile.source_folder, "install.sh"),
        os.path.join(conanfile.source_folder, "config", "install-sh"),
        os.path.join(conanfile.source_folder, "build-aux", "install-sh"),
        os.path.join(conanfile.source_folder, "aux", "install-sh"),
    ]
    src = next((p for p in candidates if os.path.isfile(p)), None)
    if src is None:
        conanfile.output.warning(
            "install-sh not found; make install keeps default INSTALL"
        )
        return None
    try:
        os.makedirs(workdir, exist_ok=True)
    except OSError:
        pass
    dst = os.path.join(workdir, "hmbs-install-sh")
    shell = _device_shell()
    try:
        with open(src, "r", encoding="utf-8",
                   errors="surrogateescape") as handle:
            content = handle.read()
        lines = content.split("\n", 1)
        if lines and lines[0].startswith("#!"):
            lines[0] = "#!%s" % shell
            content = "\n".join(lines) if len(lines) > 1 else lines[0]
        with open(dst, "w", encoding="utf-8",
                   errors="surrogateescape", newline="\n") as handle:
            handle.write(content)
    except OSError as exc:
        conanfile.output.warning(
            f"install-sh staging failed ({exc}); keeping default INSTALL"
        )
        return None
    try:
        os.chmod(dst, 0o755)
    except OSError:
        pass  # HMBS_CAP_CHMOD=0: mode bits not persistent; exec bit
        # from the tarball copy is normally enough for shebang exec.
    conanfile.output.info(f"make install will use staged install-sh: {dst}")
    return dst


class Libfuzzy2Conan(ConanFile):
    name = "libfuzzy2"
    version = "2.14.1"
    description = "Fuzzy hashing (CTPH) library for identifying almost identical files"
    license = "GPL-2.0-only"
    homepage = "https://github.com/ssdeep-project/ssdeep"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        if self.settings.os == "OHOS":
            tc.configure_args.extend([
                "--build=aarch64-unknown-linux-gnu",
                "--host=aarch64-unknown-linux-ohos",
            ])
        # Round-3 route (round-1/2 os.environ + .sh string-replace failed:
        # profile [buildenv] re-exports the bad CONFIG_SHELL via
        # conanbuild.sh AFTER our os.environ assignment, so
        # Autotools.configure() still re-execed with the absent bash and
        # the error stayed byte-identical at configure[159], Error 127).
        # Follow opusfile/abx precedent: publish the good shell through
        # the toolchain environment so the generated toolchain script
        # overrides the profile buildenv instead of fighting it.
        shell = _device_shell()
        tmpdir = _writable_tmpdir(self.build_folder)
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        env = tc.environment()
        env.define_path("SHELL", shell)
        env.unset("CONFIG_SHELL")
        env.define_path("TMPDIR", tmpdir)
        env.define_path("TMP", tmpdir)
        env.define_path("TEMP", tmpdir)
        # Round-6 route: profile CC/CXX may be a dead absolute path on this
        # device (configure: `/data/service/hnp/bin/clang: inaccessible or
        # not found`, exit 127). Publish the sanitized compilers through
        # the toolchain env so conanautotoolstoolchain.sh exports a PATH-
        # resolvable CC/CXX instead of the dead absolute path.
        _cc, _cxx = _resolve_compilers(self)
        env.define("CC", _cc)
        env.define("CXX", _cxx)
        tc.generate(env=env)

    def build(self):
        # HMDFS workaround: default umask may create 640 files invisible to
        # other processes (test_package, CI workers). Use 022 instead.
        if self.settings.os in ("Linux", "OHOS"):
            os.umask(0o022)
        apply_conandata_patches(self)
        # HMDFS: getcwd() can fail inside Conan build dirs (broken parent
        # chain), which makes autoconf die with "working directory cannot be
        # determined". Seed $PWD and chdir so sh pwd resolves logically.
        bf = self.build_folder
        if os.path.isdir(bf):
            try:
                os.chdir(bf)
            except OSError:
                pass
            os.environ["PWD"] = bf
        # E046 HMDFS workaround: generated configure embeds 'umask 077' for
        # config.status temp dirs, which are then unwritable on HMDFS.
        # Relax it in the source-tree copy so config.status can proceed.
        if self.settings.os in ("Linux", "OHOS"):
            conf = os.path.join(self.source_folder, "configure")
            if os.path.isfile(conf):
                try:
                    with open(conf, "r", encoding="utf-8", errors="replace") as f:
                        _c = f.read()
                    if "umask 077" in _c:
                        _c = _c.replace("umask 077", "umask 022")
                        with open(conf, "w", encoding="utf-8", newline="\n") as f:
                            f.write(_c)
                except OSError as exc:
                    self.output.warning(f"umask relax failed for configure: {exc}")
        # E072: vendor config.sub predates OHOS; teach it linux-ohos before
        # configure validates --host=aarch64-unknown-linux-ohos.
        if self.settings.os in ("Linux", "OHOS"):
            _patch_config_sub_for_ohos(self)
        # Round-4 route: neutralize CONFIG_SHELL instead of overriding it.
        # Verified against upstream ssdeep-2.14.1/configure: line 139
        # `if test x"${_as_can_reexec}" != xno && test "x$CONFIG_SHELL" != x`
        # then line 154 `exec $CONFIG_SHELL ...`. Any non-empty CONFIG_SHELL
        # triggers re-exec. Rounds 1-3 set CONFIG_SHELL=/bin/sh via
        # os.environ / toolchain env / Environment.apply(), but the profile
        # [buildenv] (conanbuild.sh, sourced later in the same shell)
        # re-exports CONFIG_SHELL=/data/service/hnp/bin/bash, so the bad
        # value still won and configure[159] stayed byte-identical
        # (RUN line now shows "/bin/sh" "configure" yet line 159 still
        # execs the absent bash -> Error 127). Unsetting CONFIG_SHELL for
        # the configure child makes the line-139 test false, so configure
        # skips re-exec entirely and keeps running under the /bin/sh we
        # invoked it with. The `(unset ...; ...)` subshell wrapper runs
        # AFTER conanbuild.sh is sourced, so it wins regardless of profile
        # priority. Pure POSIX shell, no `env` dependency.
        # Round-5 fix (C compiler cannot create executables): the manual
        # self.run() calls below only applied a fresh Environment with
        # SHELL/TMPDIR, never sourcing the AutotoolsToolchain output, so
        # configure ran with a bare clang and no sysroot/target flags.
        # Pass env=["conanbuild", "conanautotoolstoolchain"] so CC/CFLAGS/
        # LDFLAGS reach the child; the `(unset CONFIG_SHELL; ...)` prefix
        # still runs after sourcing and keeps the Round-4 neutralization.
        shell = _device_shell()
        tmpdir = _writable_tmpdir(bf)
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        # Sanitized compilers: if the profile absolute path is dead,
        # force CC/CXX to the PATH-resolvable bare names. Exported both
        # via the toolchain env (generate) and explicitly on the shell
        # command line here so the value wins even if conanbuild.sh
        # ordering changes.
        _cc, _cxx = _resolve_compilers(self)
        _conan_env = ["conanbuild", "conanautotoolstoolchain"]
        autotools = Autotools(self)
        configure = os.path.join(self.source_folder, "configure")
        cfg_args = getattr(autotools, "_configure_args", "") or ""
        if not cfg_args:
            # Fallback if the helper exposes no args (keep triplet + static).
            parts = ["--disable-shared", "--enable-static"]
            if self.settings.os == "OHOS":
                parts += ["--build=aarch64-unknown-linux-gnu",
                          "--host=aarch64-unknown-linux-ohos"]
            cfg_args = " ".join(parts)
        env = Environment()
        env.define_path("SHELL", shell)
        env.define_path("TMPDIR", tmpdir)
        env.define_path("TMP", tmpdir)
        env.define_path("TEMP", tmpdir)
        env.unset("CONFIG_SHELL")
        with env.vars(self).apply():
            # Compact forensics on failure (cstream precedent): the full
            # config.log tail is make-variable noise that never survives
            # log summarization, so print only the compiler-check section
            # plus error-pattern lines and the effective toolchain env.
            self.run(
                f'(unset CONFIG_SHELL; SHELL="{shell}" TMPDIR="{tmpdir}" '
                f'TMP="{tmpdir}" TEMP="{tmpdir}" CC="{_cc}" CXX="{_cxx}" '
                f'"{shell}" "{configure}" {cfg_args} || '
                f'{{ echo "===== HMBS_DIAG configure failed ====="; '
                f'echo "CC=$CC"; echo "CFLAGS=$CFLAGS"; echo "LDFLAGS=$LDFLAGS"; '
                f'echo "TMPDIR=$TMPDIR TEMP=$TEMP"; which mktemp || true; which clang || true; ls -l /data/service/hnp/bin/clang 2>&1 | head -5; '
                f'grep -n -A12 "checking whether the C compiler works" config.log 2>/dev/null | head -30; '
                f'grep -nE "error:|Error|fatal|cannot|not found|Read-only|temporary file|while loading|inaccessible" config.log 2>/dev/null | head -30; '
                f'exit 77; }})',
                cwd=self.build_folder,
                env=_conan_env,
            )
            if self.settings.os == "OHOS":
                # Upstream links the ssdeep CLI with -static (Makefile.am:
                # ssdeep_LDFLAGS=-static). Full static link of the C++ binary
                # fails against the OHOS SDK runtime, while the library itself
                # builds fine. Drop the flag in the generated Makefile (build
                # tree only, R6: no source patch) so the tool links dynamically.
                mk = os.path.join(self.build_folder, "Makefile")
                if os.path.isfile(mk):
                    with open(mk, "r", encoding="utf-8") as f:
                        content = f.read()
                    content = re.sub(
                        r"^ssdeep_LDFLAGS\s*=.*$",
                        "ssdeep_LDFLAGS =",
                        content,
                        flags=re.MULTILINE,
                    )
                    with open(mk, "w", encoding="utf-8", newline="\n") as f:
                        f.write(content)
            # R9: single job — parallel make hits HMDFS jobserver fifo EPERM.
            # Same unset wrapper: make re-exports SHELL to children
            # (compile/link/install-sh); keep the bad value out of it.
            self.run(
                f'(unset CONFIG_SHELL; SHELL="{shell}" TMPDIR="{tmpdir}" '
                f'TMP="{tmpdir}" TEMP="{tmpdir}" CC="{_cc}" CXX="{_cxx}" make -j1)',
                cwd=self.build_folder,
                env=_conan_env,
            )

    def package(self):
        shell = _device_shell()
        tmpdir = _writable_tmpdir(self.build_folder)
        try:
            _pcc, _pcxx = _resolve_compilers(self)
        except Exception:
            _pcc, _pcxx = "clang", "clang++"
        env = Environment()
        env.define_path("SHELL", shell)
        env.define_path("TMPDIR", tmpdir)
        env.define_path("TMP", tmpdir)
        env.define_path("TEMP", tmpdir)
        env.unset("CONFIG_SHELL")
        with env.vars(self).apply():
            # `make install` children (install-sh, libtool) also honor
            # SHELL/CONFIG_SHELL; run them under the same unset wrapper.
            # R10: override INSTALL* with the staged install-sh (see
            # _install_sh_for_ohos). configure baked the HMBS shim
            # (.../runtime/<pkg>/bin/install -c) into the Makefiles, but
            # that shim silently installs nothing for libtool's
            # `install -c src destfile` call, so the follow-up
            # `chmod 644 destfile` dies with No such file. Command-line
            # make variables beat the baked-in shim path.
            _install_sh = _install_sh_for_ohos(self, tmpdir)
            if _install_sh:
                _install_vars = (
                    f'INSTALL="{_install_sh} -c" '
                    f'INSTALL_PROGRAM="{_install_sh} -c" '
                    f'INSTALL_DATA="{_install_sh} -c -m 644" '
                    f'INSTALL_SCRIPT="{_install_sh} -c" '
                    f'MKDIR_P="{_install_sh} -c -d" '
                )
            else:
                _install_vars = ""
            self.run(
                f'(unset CONFIG_SHELL; SHELL="{shell}" TMPDIR="{tmpdir}" '
                f'TMP="{tmpdir}" TEMP="{tmpdir}" CC="{_pcc}" CXX="{_pcxx}" '
                f'make install {_install_vars}DESTDIR="{self.package_folder}" -j1)',
                cwd=self.build_folder,
                env=["conanbuild", "conanautotoolstoolchain"],
            )
            # HMDFS workaround: ensure installed files are world-readable so
            # test_package and CI workers can access them.
            if self.settings.os in ("Linux", "OHOS"):
                try:
                    self.run(f'chmod -R a+r "{self.package_folder}"')
                except Exception as exc:
                    self.output.warning(f"chmod a+r skipped: {exc}")
                try:
                    self.run(f'find "{self.package_folder}" -type d -exec chmod a+rx {{}} \\;')
                except Exception as exc:
                    self.output.warning(f"chmod dirs skipped: {exc}")
        # Remove libtool archive files; they are never consumed on OHOS.
        for root, _dirs, files in os.walk(self.package_folder):
            for fn in files:
                if fn.endswith(".la"):
                    try:
                        os.remove(os.path.join(root, fn))
                    except OSError:
                        pass

    def package_info(self):
        self.cpp_info.libs = ["fuzzy"]
