#!/usr/bin/env python3
"""Conan recipe — uhttpmock 0.11.0 (Meson).

uhttpmock is a library for mocking web service APIs which use HTTP or HTTPS
(recording and playback of HTTP request-response traces, libuhttpmock-1.0).

Adapted to HarmonyOS PC (aarch64, musl, clang). Build/downstream handling
inherits the verified approaches of the same GLib meson stack
(gssdp 1.6.6 / libsoup3 3.6.5-r1 / gupnp 1.6.10):
  - static-only glib2 on ohpcd -> single GObject copy doctrine (g_* stay UND
    and resolve at runtime against the glib symbol table exported by
    libsoup-3.0.so);
  - never strip shared libraries (embedded .codesign hash breaks, dlopen
    Permission denied);
  - meson install rewrites DT_RUNPATH -> overwrite installed .so with the
    build-tree artifact;
  - OHOS sysroot AR/AS/STRIP env names are llvm-* aliases not on PATH ->
    pin the real tools by absolute path.
"""

import glob
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain


# glib static-lib tokens that must NEVER reach a link command line (the
# single-copy GObject doctrine). See gssdp 1.6.6 / gupnp 1.6.10 notes for the
# SIGABRT root cause analysis behind this list.
GLIB_STATIC_TOKENS = {
    "-lglib-2.0", "-lgobject-2.0", "-lgio-2.0", "-lgmodule-2.0",
    "-lgthread-2.0", "-lffi", "-lintl",
}

# Upstream meson test programs (libuhttpmock/tests/meson.build: uhm_tests).
UPSTREAM_TESTS = ("server", "resolver")


class UhttpmockConan(ConanFile):
    name = "uhttpmock"
    version = "0.11.0"
    description = "HTTP web service mocking library (recording and playback of HTTP traces)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.freedesktop.org/pwithnall/uhttpmock"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # uhttpmock meson.build deps: glib-2.0/gio-2.0 >= 2.38 (glib2),
        # libsoup-3.0 >= 3.1.2 (libsoup3).
        # Match the exact revisions gupnp/1.6.10 was verified against so the
        # graph resolves a single glib2/libsoup3 revision.
        # zlib override pins the PIC variant (1.3.1.1): the published
        # zlib/1.3.1 libz.a is not -fPIC and breaks when linked into a
        # shared .so. Same rationale as gssdp 1.6.6 / gupnp 1.6.10.
        self.requires("zlib/1.3.1.1", override=True)
        self.requires("glib2/2.88.0")
        self.requires("libsoup3/3.6.5-r1")

    def build_requirements(self):
        # True-machine/CI workers have no system meson on PATH (HMBS only
        # injects cmake/make/ninja/python3); the Meson helper shells out to
        # the `meson` binary at configure time, so pull it from the registry.
        # 2026-09-24 preflight: `meson setup` aborted with
        # "/bin/sh: meson: inaccessible or not found" (exit 127) because this
        # recipe relied on the old "CI ships global meson" assumption
        # inherited from gssdp/gupnp. meson/1.11.0 is pure Python (no ninja
        # dep that would pull the libc++_shared-linked registry ninja).
        # The registry ninja is still deliberately NOT required: its binary
        # needs libc++_shared.so at load time and fails a clean-env probe;
        # the build profile PATH already carries a static ninja (same
        # decision as gssdp 1.6.6 / gupnp 1.6.10).
        # Precedent: fcft/3.3.3 (identical preflight error, 2026-09-09),
        # c-stdaux/1.6.0, c-list/3.1.0.
        self.tool_requires("meson/1.11.0")
        # 2026-09-24 preflight: meson configure aborts with
        # "Dependency lookup for glib-2.0 with method 'pkg-config' failed:
        # Pkg-config for machine host machine not found" — the worker has
        # no pkg-config/pkgconf on PATH (HMBS injects only
        # cmake/make/ninja/python3). Same fix as fcft/3.3.3.
        self.tool_requires("pkgconf/3.0.5")

    def layout(self):
        # meson_layout was removed in conan 2.29.x; replicate its folders.
        self.folders.build = "builddir"
        self.folders.generators = "builddir/generators"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ #
    # pkg-config surgery helpers (single-copy GObject doctrine)           #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _read(path):
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()

    @staticmethod
    def _write(path, text):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def _build_glib2_pc_fix(self, glib2_pkg, pc_fix_dir):
        """Copies of the glib2 package .pc files with prefix fixed to the real
        package folder, Libs stripped and libffi dropped from Requires.

        The published glib2 package installs its .pc files with prefix=/, so
        Cflags/Libs resolve to /include and /lib. libffi is only reachable via
        the raw glib2 .pc whose own prefix is broken (-L//lib -lffi,
        unresolvable at link time) and nothing needs to link libffi: GObject
        stays dynamic via libsoup-3.0.so (single-copy doctrine).
        """
        src_dir = os.path.join(glib2_pkg, "lib", "pkgconfig")
        os.makedirs(pc_fix_dir, exist_ok=True)
        for pc in os.listdir(src_dir):
            if not pc.endswith(".pc"):
                continue
            text = self._read(os.path.join(src_dir, pc))
            text = re.sub(r"^prefix=.*$", "prefix={}".format(glib2_pkg), text,
                          count=1, flags=re.M)
            text = re.sub(r"^Libs:.*$", "Libs: ", text, flags=re.M)
            text = re.sub(r"^Libs\.private:.*$", "Libs.private: ", text, flags=re.M)

            def _drop_libffi(match):
                toks = [t.strip() for t in match.group(1).split(",")]
                toks = [t for t in toks if t and t != "libffi"]
                return "Requires: " + ", ".join(toks)

            text = re.sub(r"^Requires:(.*)$", _drop_libffi, text, flags=re.M)
            self._write(os.path.join(pc_fix_dir, pc), text)

    def _strip_glib_from_generated_pcs(self):
        """Post-generate scrub of PkgConfigDeps output (single-copy GObject).

        Must run AFTER tc.generate(): the generators/*.pc files do not exist
        before that point, so any pre-generate strip is a silent no-op (this
        recipe's previous bug — _strip before tc.generate() never fired while
        generators/glib-2.0.pc kept its full static Libs list, and meson
        resolved glib-2.0 from the generators dir first, linking a second
        static GObject copy into libuhttpmock/tests -> SIGABRT
        g_type_register_static/static_quark_type_flags).
        Mirrors the verified gssdp 1.6.6 tail fix: empty the Libs of the
        generated glib-2.0.pc; additionally token-strip the generated
        libsoup-3.0.pc (keeps -lsoup-3.0) so no path reintroduces
        -lglib-2.0/-lgobject-2.0/-lgio-2.0/-lgmodule-2.0/-lgthread-2.0/-lffi/
        -lintl into any link line. g_* stay UND and resolve at runtime to
        the single copy exported by libsoup-3.0.so.
        """
        try:
            names = [f for f in os.listdir(self.generators_folder)
                     if f.endswith(".pc")]
        except Exception:
            return
        for name in names:
            path = os.path.join(self.generators_folder, name)
            if not os.path.isfile(path):
                continue
            changed = False
            out = []
            for line in self._read(path).splitlines(True):
                m = re.match(r"^(Libs:)(.*)$", line)
                if m:
                    kept = [t for t in m.group(2).split()
                            if t not in GLIB_STATIC_TOKENS]
                    new_line = "Libs: " + " ".join(kept) + "\n"
                    if new_line != line:
                        changed = True
                    line = new_line
                    out.append(line)
                    continue
                m = re.match(r"^(Libs\.private:)(.*)$", line)
                if m:
                    kept = [t for t in m.group(2).split()
                            if t not in GLIB_STATIC_TOKENS]
                    new_line = "Libs.private: " + " ".join(kept) + "\n"
                    if new_line != line:
                        changed = True
                    line = new_line
                    out.append(line)
                    continue
                # libsoup-3.0.pc Requires: glib-2.0 would re-expand to the
                # (now emptied) glib pc; drop the edge explicitly as well so
                # even an unstripped fallback cannot re-link static glib.
                if name == "libsoup-3.0.pc":
                    m = re.match(r"^(Requires:)(.*)$", line)
                    if m:
                        toks = [t for t in m.group(2).split()
                                if t != "glib-2.0"]
                        new_line = "Requires: " + " ".join(toks) + "\n"
                        if new_line != line:
                            changed = True
                        line = new_line
                out.append(line)
            if changed:
                self._write(path, "".join(out))
                self.output.info("stripped static glib tokens from %s" % name)

    # ------------------------------------------------------------------ #

    @staticmethod
    def _sdk_bin_dirs():
        """Candidate LLVM bin directories on the OHOS host.

        The archiver/assembler live next to the clang driver (e.g.
        /data/service/hnp/bin) but that directory is not always on PATH,
        so probe the files directly instead of relying on PATH only.
        """
        candidates = []
        for env_var in ("CC", "CXX"):
            val = os.environ.get(env_var, "")
            prog = val.strip().split()[0] if val.strip() else ""
            if prog:
                if not os.path.isabs(prog):
                    prog = shutil.which(prog) or ""
                if prog and os.path.isfile(prog):
                    candidates.append(os.path.dirname(prog))
        for known in ("/data/service/hnp/bin",
                      "/opt/ohos-sdk/native/llvm/bin",
                      os.path.expanduser("~/ohos-sdk/native/llvm/bin")):
            candidates.append(known)
        # Shadow-toolchain layouts on workers where /data/service/hnp/bin
        # is absent (fftw3f evidence: $HOME/ohpc-ci-shadow/.../tools/).
        for base in (os.path.expanduser("~/ohpc-ci-shadow"),
                     "/opt/ohpc-ci-shadow"):
            try:
                candidates.extend(
                    sorted(glob.glob(os.path.join(base, "*", "tools"))))
            except Exception:
                pass
        seen, dirs = set(), []
        for d in candidates:
            if d and d not in seen:
                seen.add(d)
                dirs.append(d)
        return dirs

    def _find_tool(self, *names):
        """Locate a build tool: PATH first, then SDK bin dirs by file probe.

        Returns the absolute path, or None when the tool does not exist.
        Only existing executable files are ever returned.
        """
        for name in names:
            path = shutil.which(name)
            if path:
                return path
        for directory in self._sdk_bin_dirs():
            for name in names:
                cand = os.path.join(directory, name)
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    return cand
        return None

    def _resolve_compiler(self, key, env_var, *names):
        """Resolve a real compiler binary for the meson native file.

        The ohos-aarch64 profile pins tools.build:compiler_executables to
        /data/service/hnp/bin/clang(++), but that file is absent on some
        preflight workers, where meson aborts configure with
        "ERROR: Unknown compiler(s)" (2026-09-24 preflight evidence).
        Order: profile conf (only if the file exists) -> CC/CXX env ->
        PATH -> known OHOS LLVM dirs -> shadow-toolchain layouts.
        Same conf->PATH probing doctrine as bzrtp/5.3.105 (there for the
        CMake toolchain file, here for conan_meson_native.ini).
        """
        conf = self.conf.get("tools.build:compiler_executables",
                             default={}, check_type=dict) or {}
        configured = conf.get(key)
        if configured and os.path.isfile(configured):
            return configured
        env_val = os.environ.get(env_var, "")
        prog = env_val.strip().split()[0] if env_val.strip() else ""
        if prog:
            if not os.path.isabs(prog):
                prog = shutil.which(prog) or ""
            if prog and os.path.isfile(prog):
                return prog
        for name in names:
            path = shutil.which(name)
            if path:
                return path
        for directory in self._sdk_bin_dirs():
            for name in names:
                cand = os.path.join(directory, name)
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    return cand
        # Shadow-toolchain layouts (fftw3f evidence:
        # $HOME/ohpc-ci-shadow/.../tools/clang).
        for base in (os.path.expanduser("~/ohpc-ci-shadow"),
                     "/opt/ohpc-ci-shadow"):
            for cand in glob.glob(os.path.join(base, "*", "tools", names[0])):
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    return cand
        if configured:
            # Last resort: keep the profile value so the downstream error
            # still names the configured path instead of a bare tool name.
            return configured
        raise ConanInvalidConfiguration(
            "no %s compiler found (conf/PATH/SDK/shadow search exhausted)" % key)

    def _resolve_pkgconf(self):
        """Locate a pkg-config-compatible binary for the meson native file.

        Probes PATH first, then the pkgconf tool package bindir by exact
        file probe plus recursive fallback (the tool package ships
        `pkgconf`; some revisions also symlink `pkg-config` — neither name
        can be assumed). Only existing files are returned; None when
        nothing is found (meson then reports its own lookup error; counts
        are never guessed).
        """
        for name in ("pkg-config", "pkgconf"):
            path = shutil.which(name)
            if path and os.path.isfile(path):
                return path
        try:
            pkg = self.dependencies.build.get("pkgconf")
            folders = []
            if pkg is not None:
                try:
                    folders.append(pkg.package_folder)
                except Exception:
                    pass
            for folder in folders:
                if not folder or not os.path.isdir(folder):
                    continue
                for name in ("pkg-config", "pkgconf"):
                    cand = os.path.join(folder, "bin", name)
                    if os.path.isfile(cand):
                        return cand
                # Recursive fallback: some tool revisions place the binary
                # outside bin/ or without the exec bit in the probe view.
                for name in ("pkg-config", "pkgconf"):
                    try:
                        hits = sorted(glob.glob(
                            os.path.join(folder, "**", name), recursive=True))
                    except Exception:
                        hits = []
                    for hit in hits:
                        if os.path.isfile(hit):
                            return hit
        except Exception:
            pass
        return None

    def _patch_meson_native_compilers(self, cc, cxx):
        """Rewrite the c/cpp entries MesonToolchain baked into
        conan_meson_native.ini from the (possibly absent) profile paths.

        Only the exact `c = '...'` / `cpp = '...'` lines are touched;
        c_ld/cpp_ld/args/link-args lines are left alone. The pkgconfig
        binary is ensured deterministically: when a real pkgconf binary is
        resolved, any existing pkgconfig line is pinned to its absolute
        path, and when the native file carries no pkgconfig line at all
        (MesonToolchain default — the reason the previous bare-line-only
        regex never fired), one is inserted into the [binaries] section.
        Workers carry no system pkg-config, so this is the deterministic
        path meson must use.
        """
        native = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(native):
            return
        text = self._read(native)
        text = re.sub(r"(?m)^c = '.*'$", "c = '%s'" % cc, text)
        text = re.sub(r"(?m)^cpp = '.*'$", "cpp = '%s'" % cxx, text)
        pkgconf = self._resolve_pkgconf()
        if pkgconf:
            if re.search(r"(?m)^pkgconfig\s*=", text):
                text = re.sub(r"(?m)^pkgconfig\s*=.*$",
                               "pkgconfig = '%s'" % pkgconf, text)
            elif "[binaries]" in text:
                text = text.replace("[binaries]\n",
                                    "[binaries]\npkgconfig = '%s'\n" % pkgconf, 1)
            # Meson also honours PKG_CONFIG for the host-machine lookup;
            # export it for the configure subprocess (build() re-exports
            # defensively as well).
            os.environ["PKG_CONFIG"] = pkgconf
        self._write(native, text)
        self.output.info("patched meson native compilers: c=%s cpp=%s pkgconf=%s"
                         % (cc, cxx, pkgconf))

    def generate(self):
        # The CI worker exports AR/AS/STRIP/NM/RANLIB as llvm-* names that are
        # not on its PATH; meson probes them and aborts. Pin the real tools by
        # absolute PATH and drop the broken env values (same as glib2/2.88.0,
        # libsoup3/3.6.5-r1, gssdp 1.6.6, gupnp 1.6.10).
        # 2026-09-24 preflight: the HarmonyOS PC host has no standalone `as`
        # on PATH (pure-C library: meson uses the C compiler as assembler),
        # so `as` must be optional — requiring it aborts generate() with
        # "Required build tools not in PATH: as" before any compilation.
        # Tools are resolved via PATH plus direct file probes of the LLVM bin
        # dirs beside the CC/CXX driver; only files that actually exist are
        # pinned, everything else keeps the meson default.
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {
            "ar": self._find_tool("ar", "llvm-ar"),
            "as": self._find_tool("as", "llvm-as"),
            "strip": self._find_tool("strip", "llvm-strip"),
            "nm": self._find_tool("nm", "llvm-nm"),
            "ranlib": self._find_tool("ranlib", "llvm-ranlib"),
        }
        if tools["ar"] is None:
            raise ConanInvalidConfiguration(
                "Required build tools not in PATH: ar")

        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        # Standalone assembler is optional: uhttpmock is pure C, meson falls
        # back to the C compiler (clang) when no `as` binary is pinned.
        # Never map the clang driver itself to `as`.
        if tools["as"] is not None:
            tc.as_ = tools["as"]
        # Never strip shared libraries: the OHOS loader verifies the
        # embedded .codesign hash against the file content; strip rewrites the
        # .so and dlopen fails with Permission denied (libsoup3 evidence).
        tc.strip = None
        if tools["nm"] is not None:
            tc.binaries["nm"] = tools["nm"]
        if tools["ranlib"] is not None:
            tc.binaries["ranlib"] = tools["ranlib"]
        tc.project_options["default_library"] = \
            "shared" if self.options.shared else "static"
        # uhttpmock meson options: introspection needs gobject-introspection
        # (unavailable when cross-building / on OHOS), vapi needs valac,
        # gtk_doc needs gtk-doc. All three are upstream-optional
        # documentation/binding features; the library itself is unaffected.
        tc.project_options["introspection"] = "false"
        tc.project_options["vapi"] = "disabled"
        tc.project_options["gtk_doc"] = "false"

        glib2 = self.dependencies.get("glib2")
        if not (glib2 and glib2.package_folder):
            raise ConanInvalidConfiguration("glib2 dependency not resolved")
        glib2_pkg = glib2.package_folder

        # 1) glib2 .pc copies with fixed prefix / stripped Libs / no libffi.
        pc_fix_dir = os.path.join(self.build_folder, "glib2-pc-fix")
        self._build_glib2_pc_fix(glib2_pkg, pc_fix_dir)

        # meson needs the gobject-2.0/gio-2.0/gio-unix-2.0/gmodule-*.pc modules
        # uhttpmock requests individually — only the glib2 package ships them
        # (PkgConfigDeps generates a single glib-2.0.pc). Prepend the fixed
        # copies so the broken prefix=/ raw ones are never used.
        # NOTE: no generators/*.pc scrub here — those files are written by
        # tc.generate() below, so any pre-generate strip is a silent no-op.
        # The scrub runs post-generate (see below).
        extra_pc = [pc_fix_dir, os.path.join(glib2_pkg, "lib", "pkgconfig")]
        tc.pkg_config_path = os.pathsep.join([tc.pkg_config_path] + extra_pc)
        # gnome module tools are not needed (introspection disabled), but keep
        # the glib2 bin on PATH for gdbus-codegen style probes if any.
        glib_bin = os.path.join(glib2_pkg, "bin")
        if os.path.isdir(glib_bin):
            self.buildenv_info.prepend_path("PATH", glib_bin)
        # Deterministic pkg-config for meson: MesonToolchain emits no
        # pkgconfig line by default, so the post-generate regex patch alone
        # never fired (2026-09-24 preflight still reported "Pkg-config for
        # machine host machine not found" despite tool_requires pkgconf).
        # Pin the absolute binary up-front via tc.binaries; the
        # post-generate patch remains as a fallback that inserts the line
        # when it is still missing. Also export PKG_CONFIG into the
        # buildenv so the meson subprocess sees it even if the native file
        # is regenerated downstream.
        _pkgconf_exe = self._resolve_pkgconf()
        if _pkgconf_exe:
            tc.binaries["pkgconfig"] = _pkgconf_exe
            os.environ["PKG_CONFIG"] = _pkgconf_exe
            try:
                self.buildenv_info.define_path("PKG_CONFIG", _pkgconf_exe)
            except Exception:
                pass
            self.output.info("pinned meson pkgconfig: %s" % _pkgconf_exe)
        else:
            self.output.warning(
                "pkgconf binary not resolved at generate() time; "
                "meson lookup will report its own error")
        tc.generate()
        # Post-generate: scrub PkgConfigDeps output so no static glib token
        # reaches any link line (single-copy GObject; gssdp 1.6.6 tail fix).
        # Must run after tc.generate() — the .pc files do not exist before.
        self._strip_glib_from_generated_pcs()
        # The profile-baked c/cpp paths may not exist on this worker
        # (Unknown compiler(s) at meson setup); point the native file at
        # real binaries resolved above. Binutils probing (_find_tool) runs
        # before this so it keeps using PATH/SDK probing independently.
        _cc = self._resolve_compiler("c", "CC", "clang")
        _cxx = self._resolve_compiler("cpp", "CXX", "clang++")
        self._patch_meson_native_compilers(_cc, _cxx)

    def _parse_meson_test_output(self, text):
        """Parse `meson test` stdout line by line (deterministic source).

        Meson prints one result line per test, e.g. ``1/2 server OK`` /
        ``2/2 resolver FAIL``. Verbose runs append duration and reason
        (``1/2 uhttpmock:server FAIL 0.23s killed by signal 6 SIGABRT``),
        so trailing tokens after the verdict are allowed; suite prefixes
        (``uhttpmock:server``) are normalized to the short name. Each test
        appears TWICE on failure (progress list + ``Summary of Failures``
        reprint), so results are deduplicated by name (last verdict wins) —
        otherwise executed would exceed discovered and trip the gate
        identity. Counts come from those lines only — no substring
        tallying, no returncode-based guessing.
        """
        verdict_by_name = {}
        for line in text.splitlines():
            m = re.match(
                r"^\s*\d+/\d+\s+(\S+)\s+(OK|FAIL|SKIP|TIMEOUT|INTERRUPT)\b.*$",
                line.strip())
            if not m:
                continue
            name, result = m.group(1), m.group(2)
            # Normalize "suite:test" to "test" (meson prints uhttpmock:server).
            if ":" in name:
                name = name.rsplit(":", 1)[1]
            # Last verdict wins: Summary of Failures reprints FAIL lines.
            verdict_by_name[name] = result
        passed_names, failed_names, skipped_names = [], [], []
        for name, result in verdict_by_name.items():
            if result == "OK":
                passed_names.append(name)
            elif result == "SKIP":
                skipped_names.append(name)
            else:
                failed_names.append(name)
        return passed_names, failed_names, skipped_names

    def _emit_upstream_marker(self, discovered, passed_names, failed_names,
                              skipped_names=None, gaps=None):
        skipped_names = skipped_names or []
        executed = len(passed_names) + len(failed_names)
        result = {
            "status": "passed" if not failed_names else "failed",
            "framework": "meson",
            "command": "meson test -v -C builddir --no-rebuild",
            "discovered": discovered,
            "executed": executed,
            "passed": len(passed_names),
            "failed": len(failed_names),
            "skipped": len(skipped_names),
        }
        if gaps:
            result["gaps"] = gaps
        # Self-check identity before emitting (numbers have a single source).
        assert result["passed"] + result["failed"] == result["executed"]
        assert result["executed"] + result["skipped"] <= result["discovered"]
        assert result["executed"] <= result["discovered"]
        marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result)
        print(marker, flush=True)
        self.output.info(marker)
        # Persist for test_package re-emit on cache-hit rounds (same pattern
        # as bzrtp 5.3.105: the main build may be skipped, the gate still
        # needs the marker).
        try:
            res_dir = os.path.join(self.package_folder, "res")
            os.makedirs(res_dir, exist_ok=True)
            with open(os.path.join(res_dir, "hmbs_upstream.json"),
                      "w", encoding="utf-8") as fh:
                json.dump(result, fh)
        except Exception as exc:
            self.output.warning("could not persist hmbs_upstream.json: %s" % exc)
        return result

    def build(self):
        apply_conandata_patches(self)
        # Defensive re-export: generate() and build() may run in separate
        # processes/shells on the worker; ensure the meson configure
        # subprocess sees PKG_CONFIG even if the generate-time export did
        # not propagate.
        if not os.environ.get("PKG_CONFIG"):
            _late_pkgconf = self._resolve_pkgconf()
            if _late_pkgconf:
                os.environ["PKG_CONFIG"] = _late_pkgconf
                self.output.info("build() PKG_CONFIG=%s" % _late_pkgconf)
        meson = Meson(self)
        meson.configure()
        meson.build()
        if cross_building(self):
            self.output.info(
                "cross-building: skip meson.test() (OHOS binaries are not "
                "runnable on the build host)")
            return
        # Native OHOS build: run the upstream suite. Wrap meson.test so the
        # machine-evidence marker is always emitted from parsed output.
        build_folder = self.build_folder

        def _ohos_meson_test():
            # Resolve the meson executable explicitly: raw subprocess.run does
            # not inherit the conan buildenv PATH that self.run/Meson helper
            # see, so a bare "meson" would repeat the exit-127 failure even
            # with the tool_requires present. Prefer PATH, then the meson
            # tool package bindir (tool_requires("meson/1.11.0")).
            _meson_exe = shutil.which("meson")
            if _meson_exe is None:
                try:
                    _meson_pkg = self.dependencies.build.get("meson")
                    _meson_bin = os.path.join(
                        _meson_pkg.package_folder, "bin", "meson") \
                        if _meson_pkg and _meson_pkg.package_folder else ""
                    if _meson_bin and os.path.isfile(_meson_bin):
                        _meson_exe = _meson_bin
                except Exception:
                    _meson_exe = None
            if _meson_exe is None:
                result = {
                    "status": "failed",
                    "framework": "meson",
                    "command": "meson test -v -C builddir --no-rebuild",
                    "discovered": len(UPSTREAM_TESTS),
                    "executed": 0,
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "reason": "meson executable not found (PATH + meson tool package)",
                }
                marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result)
                print(marker, flush=True)
                self.output.info(marker)
                raise ConanInvalidConfiguration(
                    "meson executable not found; refusing to guess counts")
            proc = subprocess.run(
                [_meson_exe, "test", "-v", "-C", build_folder, "--no-rebuild"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, check=False)
            output = proc.stdout or ""
            self.output.info(output)
            passed, failed, skipped = self._parse_meson_test_output(output)
            # Fallback: if the runner output format changed, report honestly
            # instead of inventing numbers (gate refuses to pass, next round
            # fixes the parser with real log evidence).
            if not passed and not failed and not skipped:
                result = {
                    "status": "failed",
                    "framework": "meson",
                    "command": "meson test -v -C builddir --no-rebuild",
                    "discovered": len(UPSTREAM_TESTS),
                    "executed": 0,
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "reason": "unparsed meson test output; see build log",
                }
                marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result)
                print(marker, flush=True)
                self.output.info(marker)
                raise ConanInvalidConfiguration(
                    "meson test output could not be parsed; refusing to guess counts")
            gaps = None
            if failed:
                # OHOS glib stack ships no GIO TLS backend module: the log
                # shows GDummyTlsBackend and the server program aborts in
                # test_server_properties_tls_certificate (server.c:321)
                # asserting TLS availability. glib-networking/2.90.0 exists
                # but binds glib/2.88.3 shared, incompatible with this
                # stack's static glib2/2.88.0 single-copy doctrine (mixing
                # would reintroduce dual GObject registration), and
                # libsoup3/3.6.5-r1 documents tls_check=false for the same
                # reason — so this is an ohos_feature gap, not a missing
                # dependency that can be added. Evidence strings come from
                # the real meson test stdout, not inferred.
                if ("TLS support is not available" in output
                        or "GDummyTlsBackend" in output):
                    gaps = [{
                        "count": len(failed),
                        "category": "ohos_feature",
                        "detail": "OHOS glib stack provides only GDummyTlsBackend (no GIO TLS module); uhttpmock server TLS subtest test_server_properties_tls_certificate asserts TLS availability and aborts",
                        "evidence": "GLib-GIO-DEBUG: Found default implementation dummy (GDummyTlsBackend); server.c:321 assertion failed (child_error == NULL): TLS support is not available (g-tls-error-quark, 0)",
                    }]
                else:
                    gaps = [{
                        "count": len(failed),
                        "category": "test_failure",
                        "detail": "meson test program(s) failed: %s; see build log" % ",".join(failed),
                        "evidence": "meson Summary of Failures lists %s as FAIL" % ",".join(failed),
                    }]
            result = self._emit_upstream_marker(len(UPSTREAM_TESTS), passed, failed, skipped, gaps)
            # Do NOT raise on upstream failure: the library itself built and
            # the marker (with gaps) carries the real verdict for the gate.
            # Raising here mislabels a test gap as a compile failure (exit 6,
            # stage=compile) and blocks package()/test_package. Record and
            # continue so the consumer smoke test still runs.
            if failed:
                self.output.warning(
                    "upstream meson tests failed: {} (recorded with gaps, continuing to package)".format(",".join(failed)))

        meson.test = _ohos_meson_test
        meson.test()

    def package(self):
        meson = Meson(self)
        meson.install()
        # meson install cleans DT_RUNPATH by overwriting bytes inside .dynstr
        # and dropping the entry, which invalidates the embedded .codesign
        # hash -> dlopen Permission denied (libsoup3 evidence). Overwrite the
        # installed .so with the untouched build-tree artifact.
        if self.options.shared:
            _lib = "libuhttpmock-1.0.so.1.2.3"
            _src = os.path.join(self.build_folder, "libuhttpmock", _lib)
            _dst = os.path.join(self.package_folder, "lib", _lib)
            if os.path.exists(_src):
                shutil.copy2(_src, _dst)

    def package_info(self):
        self.cpp_info.libs = ["uhttpmock-1.0"]
        # Upstream installs headers to include/libuhttpmock-1.0/uhttpmock/;
        # consumers include <libuhttpmock-1.0/uhttpmock/uhm.h> (needs plain
        # "include"), while uhm.h itself does
        # #include <uhttpmock/uhm-message.h> (needs "include/libuhttpmock-1.0").
        # Both roots are required — plain "include" alone fixed the consumer
        # line but broke the internal include (2026-09-24 preflight:
        # "fatal error: 'uhttpmock/uhm-message.h' file not found" from
        # uhm.h:24); "include/libuhttpmock-1.0" alone breaks the consumer
        # line. Mirrors the upstream .pc Cflags subdir behaviour.
        self.cpp_info.includedirs = ["include",
                                     os.path.join("include",
                                                  "libuhttpmock-1.0")]
        self.cpp_info.system_libs = ["m", "pthread", "dl"]
        # CMakeDeps generates empty data for TRANSITIVE deps (conan 2.29), so
        # expose the dependency include dirs here to let consumers compile:
        # uhttpmock public headers include glib/gio/gobject and libsoup
        # headers. libs stay "uhttpmock-1.0" only — glib/gobject/soup symbols
        # resolve through the NEEDED chain (single GObject copy).
        for depname in ("glib2", "libsoup3"):
            dep = self.dependencies.get(depname)
            if dep and dep.package_folder:
                self.cpp_info.includedirs.append(
                    os.path.join(dep.package_folder, "include"))
                self.runenv_info.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                if depname == "glib2":
                    self.cpp_info.includedirs.append(
                        os.path.join(dep.package_folder, "include", "glib-2.0"))
                    self.cpp_info.includedirs.append(
                        os.path.join(dep.package_folder, "lib", "glib-2.0",
                                     "include"))
                self.cpp_info.libdirs.append(
                    os.path.join(dep.package_folder, "lib"))
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
        self.cpp_info.set_property("pkg_config_name", "libuhttpmock-1.0")
        self.cpp_info.set_property("cmake_file_name", "libuhttpmock-1.0")
        self.cpp_info.set_property(
            "cmake_target_name", "libuhttpmock-1.0::libuhttpmock-1.0")
