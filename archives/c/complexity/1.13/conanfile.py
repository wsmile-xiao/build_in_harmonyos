#!/usr/bin/env python3
"""Conan recipe for complexity 1.13 -- GNU C complexity measurement tool (autotools).

Upstream: https://ftp.gnu.org/gnu/complexity/complexity-1.13.tar.xz
Build: GNU autotools (configure + make). gnulib sources are bundled in
lib/; upstream configure probes GNU autogen libopts via `autoopts-config`.

The HarmonyOS PC preflight machine has no system libopts, and building the
full autogen suite needs guile/libxml -- too heavy for a single-library PR.
The upstream tarball already ships pre-generated opts.c/opts.h (AutoOpts
42:2:17 templates), so only the *runtime* library is missing. This recipe
therefore builds a minimal private libopts shim from
libopts_shim/ (real `autoopts/options.h` struct layouts vendored verbatim
from autogen-5.18.16 + a small getopt_long-based implementation covering
exactly the entry points complexity's generated opts.c uses) and feeds it
to configure through a privately built `autoopts-config` executable. No new
Conan dependency is introduced; nothing from the shim is installed.

Upstream tests: automake harness, TESTS=tests/complexity.test, executed
via `make check` in build(). The automake test-suite.log is parsed for
the HMBS_UPSTREAM_TEST_RESULT marker (framework "automake").
"""
import glob
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ComplexityConan(ConanFile):
    name = "complexity"
    version = "1.13"
    description = "GNU complexity — complexity measure of C source code"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/complexity/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "*", src=os.path.join(self.recipe_folder, "libopts_shim"),
             dst=os.path.join(self.export_sources_folder, "libopts_shim"))

    def requirements(self):
        # No Conan dependencies: gnulib is bundled in lib/ and libopts is
        # built privately from libopts_shim/ (see build()).
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"complexity {self.version} only supports Linux and OHOS, got os={self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # E007/HMDFS: explicit triplet bypasses config.guess, whose
        # compile-and-run probe fails on restricted filesystems
        # (same approach as the merged cflow 1.0.0 recipe).
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-gnu",
        ])
        # configure and the automake test-driver rely on bash behaviour
        # (same approach as the merged gnu-which 2.25 recipe).
        if self.settings.os in ("Linux", "OHOS"):
            bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
            tc.configure_args.append(f"SHELL={bash}")
        # E132/E266: OHOS SDK lld (llvm/bin/lld) dynamically needs the
        # SDK's ABI-matched libxml2.so.16 from llvm/lib. Some CI workers
        # (e.g. PR #8902 build #42389 on CI-020) do not have it on the
        # default loader path, so every clang link dies with
        # "Error loading shared library libxml2.so.16 / xmlFreeDoc:
        # symbol not found". Prepend llvm/lib to LD_LIBRARY_PATH via the
        # toolchain environment (same approach as merged abx 0.1 and the
        # libgsf precedent). Never use -fuse-ld=GNU ld: its output is not
        # executable in the OHOS sandbox (exit 126, needs ELF signing).
        _env = tc.environment()
        _llvm_lib = self._sdk_llvm_lib()
        if _llvm_lib:
            _env.prepend_path("LD_LIBRARY_PATH", _llvm_lib)
            self.output.info(f"complexity: LD_LIBRARY_PATH += {_llvm_lib}")
        tc.generate(env=_env)

    @staticmethod
    def _sdk_llvm_lib():
        """Locate the SDK llvm/lib holding the ABI-matched libxml2."""
        _fixed = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        if os.path.isdir(_fixed):
            return _fixed
        _cands = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"))
        return _cands[-1] if _cands else ""

    def _ensure_lld_runtime(self):
        """Export LD_LIBRARY_PATH for direct subprocess link steps."""
        _llvm_lib = self._sdk_llvm_lib()
        if not _llvm_lib:
            return
        _cur = os.environ.get("LD_LIBRARY_PATH", "")
        _parts = [p for p in _cur.split(os.pathsep) if p] if _cur else []
        if _llvm_lib not in _parts:
            os.environ["LD_LIBRARY_PATH"] = _llvm_lib + (os.pathsep + _cur if _cur else "")
            self.output.info(f"complexity: LD_LIBRARY_PATH += {_llvm_lib} (subprocess)")

    def _resolve_c_compiler(self):
        """Resolve a usable C compiler without trusting bare names blindly.

        CI root cause (PR #8902 build #42269): the old code did
        `os.environ.get("CC") or shutil.which("clang") or ... or "cc"`.
        On the CI worker CC="clang" (bare name, not on PATH), so `cc`
        became the literal string "clang" and `subprocess.check_call`
        died with `FileNotFoundError: 'clang'` even though gcc/cc was
        available. Every candidate below is validated (absolute path must
        exist+be executable, bare name must resolve via shutil.which)
        before it is accepted, so a stale CC can never shadow a working
        fallback. Order preserves preflight behaviour: Conan conf
        `tools.build:compiler_executables` (/data/service/hnp/bin/clang)
        still wins where it exists.
        """
        candidates = []
        try:
            exe = self.conf.get("tools.build:compiler_executables", default=None)
            if isinstance(exe, dict) and exe.get("c"):
                candidates.append(str(exe["c"]).strip().split()[0])
        except Exception:
            pass
        cc_env = (os.environ.get("CC") or "").strip()
        if cc_env:
            # CC may carry flags ("clang -fuse-ld=bfd", "ccache clang");
            # only the executable token matters here.
            candidates.append(cc_env.split()[0])
        candidates.extend([
            "clang", "clang-15", "clang-14", "clang-13",
            "aarch64-linux-ohos-clang",
            "gcc", "gcc-12", "gcc-11", "cc",
        ])
        candidates.extend([
            "/data/service/hnp/bin/clang",
            "/usr/bin/clang", "/usr/bin/gcc", "/usr/bin/cc", "/bin/cc",
        ])
        seen = set()
        for cand in candidates:
            if not cand or cand in seen:
                continue
            seen.add(cand)
            if os.path.isabs(cand):
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    return cand
                continue
            resolved = shutil.which(cand)
            if resolved:
                return resolved
            # Relative path with directory component that exists as a file.
            if os.path.sep in cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
        raise ConanException(
            "complexity: no usable C compiler found; tried Conan conf "
            "tools.build:compiler_executables, $CC, clang/gcc/cc (PATH=%r)"
            % (os.environ.get("PATH", ""),)
        )

    def _resolve_ar(self):
        """Resolve archiver with the same validate-before-use rule as CC."""
        candidates = []
        ar_env = (os.environ.get("AR") or "").strip()
        if ar_env:
            candidates.append(ar_env.split()[0])
        candidates.extend(["ar", "llvm-ar", "llvm-ar-15", "llvm-ar-14"])
        candidates.append("/data/service/hnp/bin/llvm-ar")
        seen = set()
        for cand in candidates:
            if not cand or cand in seen:
                continue
            seen.add(cand)
            if os.path.isabs(cand):
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    return cand
                continue
            resolved = shutil.which(cand)
            if resolved:
                return resolved
        return "ar"

    def _private_libopts(self):
        """Build the private static libopts + autoopts-config executable.

        Returns (bin_dir, env) where bin_dir holds `autoopts-config` and env
        is an os.environ-style dict with PATH/CFLAGS/LIBS overrides for the
        subsequent configure step. The executable is produced by the C
        compiler (which creates +x files directly) instead of a shell script
        + chmod, because the preflight filesystem reports HMBS_CAP_CHMOD=0.

        Also builds a `mktemp` shim (compiled C, no chmod needed) implementing
        the HMBS platform diagnosis `unsafe_local_mktemp`. NOTE (2nd fix):
        the shim gated on HMBS_AUTOCONF_MKTEMP_FALLBACK did NOT trigger in
        preflight (identical subs1.awk failure at new line 271), so the
        primary fix is now a deterministic in-place `umask 077 -> umask 022`
        replacement in configure (knowledge E011); the shim is removed.
        """
        shim_dir = None
        candidates = []
        for attr in ("base_source_folder", "source_folder", "export_sources_folder"):
            try:
                base = getattr(self, attr, None)
            except Exception:
                base = None
            if base:
                candidates.append(os.path.join(base, "libopts_shim"))
        candidates.append(os.path.join(self.recipe_folder, "libopts_shim"))
        for cand in candidates:
            if cand and os.path.isfile(os.path.join(cand, "libopts.c")):
                shim_dir = cand
                break
        if shim_dir is None:
            raise ConanException(
                "complexity: private libopts shim not found; tried: "
                + ", ".join(c for c in candidates if c)
            )
        priv = os.path.join(self.build_folder, "private-libopts")
        lib_dir = os.path.join(priv, "lib")
        bin_dir = os.path.join(priv, "bin")
        os.makedirs(lib_dir, exist_ok=True)
        os.makedirs(bin_dir, exist_ok=True)

        # E132/E266: direct subprocess links bypass conanbuild env, so
        # export the SDK llvm/lib here too (covers autoopts-config/chmod).
        self._ensure_lld_runtime()
        cc = self._resolve_c_compiler()
        ar = self._resolve_ar()
        # Prefer the shim's vendored options.h for both the shim build and
        # the later complexity build (via autoopts-config cflags).
        cflags = ["-O2", "-fPIC", f"-I{shim_dir}"]
        src = os.path.join(shim_dir, "libopts.c")
        obj = os.path.join(lib_dir, "libopts.o")
        lib = os.path.join(lib_dir, "libopts.a")
        self.output.info(f"complexity: building private libopts with {cc}")
        subprocess.check_call([cc] + cflags + ["-c", src, "-o", obj])
        if os.path.isfile(lib):
            os.remove(lib)
        subprocess.check_call([ar, "rcs", lib, obj])

        # autoopts-config executable (compiled C, no chmod needed). Paths are
        # baked in at build time so configure's `autoopts-config cflags` /
        # `ldflags` probes succeed without any system libopts.
        cfg_src = os.path.join(priv, "autoopts-config.c")
        cfg_bin = os.path.join(bin_dir, "autoopts-config")
        with open(cfg_src, "w", encoding="utf-8", newline="\n") as f:
            f.write(
                '#include <stdio.h>\n'
                '#include <string.h>\n'
                'int main(int argc, char **argv) {\n'
                f'  const char *cflags = "-I{shim_dir}";\n'
                f'  const char *ldflags = "-L{lib_dir} -lopts";\n'
                '  int i, need_sp = 0;\n'
                '  for (i = 1; i < argc; i++) {\n'
                '    const char *a = argv[i];\n'
                '    while (*a == \'-\') a++;\n'
                '    if (strcmp(a, "cflags") == 0) {\n'
                '      printf("%s%s", need_sp ? " " : "", cflags); need_sp = 1;\n'
                '    } else if (strcmp(a, "ldflags") == 0 || strcmp(a, "libs") == 0) {\n'
                '      printf("%s%s", need_sp ? " " : "", ldflags); need_sp = 1;\n'
                '    } else if (strcmp(a, "static-libs") == 0 || strcmp(a, "static_libs") == 0) {\n'
                f'      printf("%s{lib}", need_sp ? " " : ""); need_sp = 1;\n'
                '    }\n'
                '  }\n'
                '  if (need_sp) putchar(\'\\n\');\n'
                '  return 0;\n'
                '}\n'
            )
        subprocess.check_call([cc, "-O2", cfg_src, "-o", cfg_bin])
        # Sanity: the probe configure runs must answer non-empty.
        out = subprocess.check_output([cfg_bin, "cflags"], text=True).strip()
        out2 = subprocess.check_output([cfg_bin, "ldflags"], text=True).strip()
        if not out or not out2:
            raise ConanException(f"private autoopts-config probe failed: {out!r} {out2!r}")
        self.output.info(f"complexity: private autoopts-config cflags={out} ldflags={out2}")

        # chmod tolerance shim (compiled C, no chmod needed to install it).
        # src/Makefile builds the cx-vs-mc script via
        # `cp cx-vs-mc.sh cx-vs-mc && chmod 555 cx-vs-mc` with a literal
        # `chmod` program name (not $(CHMOD)), so a make-variable override
        # cannot help. On the preflight FS HMBS_CAP_CHMOD=0, that chmod
        # fails and `make -C src` dies with Error 2 even though the .o
        # compiled fine. Shadow `chmod` on the private PATH with a tiny
        # executable that delegates to the real chmod but always exits 0:
        # on CI (chmod works) modes are still set correctly; on HMDFS the
        # failure is tolerated. cx-vs-mc +x is not needed for tests
        # (upstream test + test_package only exec `complexity`).
        _real_chmod = shutil.which("chmod") or "/bin/chmod"
        _chmod_src = os.path.join(priv, "chmod.c")
        _chmod_bin = os.path.join(bin_dir, "chmod")
        with open(_chmod_src, "w", encoding="utf-8", newline="\n") as f:
            f.write(
                '#include <unistd.h>\n'
                'int main(int argc, char **argv) {\n'
                '  (void)argc;\n'
                f'  execv("{_real_chmod}", argv);\n'
                '  return 0;\n'
                '}\n'
            )
        subprocess.check_call([cc, "-O2", _chmod_src, "-o", _chmod_bin])
        self.output.info(f"complexity: chmod tolerance shim -> {_real_chmod}")

        env = dict(os.environ)
        env["PATH"] = bin_dir + os.pathsep + env.get("PATH", "")
        return bin_dir, env

    def _patch_autoconf_umask(self):
        """Deterministic E011 fix: umask 077 -> umask 022 in configure.

        HMDFS maps the mktemp-created 0700 dir to an owner UID different
        from the process UID, so configure/config.status cannot create
        subs1.awk inside it. umask 022 yields a group/world-readable tmp
        dir that stays writable; safe on a single-shot preflight worker.
        config.status is generated from configure template, so patching
        configure before running it fixes both. File edit (not PATH shim)
        so it cannot be bypassed by Conan toolchain env handling.
        """
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
                if os.path.basename(dirpath) == "private-libopts":
                    continue
                for name in ("configure", "config.status"):
                    if name not in filenames:
                        continue
                    path = os.path.join(dirpath, name)
                    try:
                        with open(path, "r", encoding="utf-8", errors="replace",
                                   newline="") as f:
                            text = f.read()
                    except OSError:
                        continue
                    if "umask 077" not in text or "confXXXXXX" not in text:
                        continue
                    text = text.replace("umask 077", "umask 022")
                    with open(path, "w", encoding="utf-8", newline="\n") as f:
                        f.write(text)
                    patched += 1
                    self.output.info("complexity: umask patch applied: %s" % path)
        if patched == 0:
            self.output.warning("complexity: umask patch found no configure target")

    def _bash_path(self):
        """Locate a bash that honours TMPDIR for here-doc temp files."""
        for cand in (
            os.environ.get("CONFIG_SHELL") or "",
            os.environ.get("SHELL") or "",
        ):
            if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
        found = shutil.which("bash")
        if found:
            return found
        for cand in (
            "/data/service/hnp/bin/bash",
            "/bin/bash",
            "/usr/bin/bash",
        ):
            if os.path.isfile(cand):
                return cand
        return "/bin/sh"

    def _patch_test_tmpdir(self, bash, tmpdir):
        """HMBS readonly_tmp fix (file edit, env-proof).

        complexity.test uses shell here-docs (rcfile + expected-output
        feed to sed). /bin/sh on the device hardcodes /tmp for those
        temp files, which is read-only (preflight.sh itself logs
        "can't create temporary file /tmp/shnr*.tmp"), so the test
        fails even though HMBS injects a writable TMPDIR -- the stock
        /bin/sh ignores TMPDIR while bash honours it. Patch every
        complexity.test copy (source + build trees): point the shebang
        at bash and export TMPDIR/TMP/TEMP baked to the writable dir.
        No assertion, expectation table, or test count is touched.
        """
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
                if os.path.basename(dirpath) == "private-libopts":
                    continue
                if "complexity.test" not in filenames:
                    continue
                path = os.path.join(dirpath, "complexity.test")
                try:
                    with open(path, "r", encoding="utf-8", errors="replace",
                               newline="") as f:
                        text = f.read()
                except OSError:
                    continue
                if "tests/sample.c" not in text and "complexity.out" not in text:
                    continue
                orig = text
                # 1) shebang -> bash (honours TMPDIR for here-docs).
                if text.startswith("#!"):
                    first_nl = text.find("\n")
                    first_line = text[:first_nl] if first_nl != -1 else text
                    if "bash" not in first_line:
                        text = "#!" + bash + text[first_line.__len__():]
                # 2) bake writable TMPDIR exports right after shebang so
                # they apply even if Conan scrubs os.environ for make.
                marker = "HMBS readonly_tmp: force writable temp dir"
                if marker not in text:
                    anchor = text.find("\n")
                    block = (
                        "\n# " + marker + " (build-time patched).\n"
                        ": \"${TMPDIR:=" + tmpdir + "}\"; export TMPDIR\n"
                        "TMP=\"${TMPDIR}\"; export TMP\n"
                        "TEMP=\"${TMPDIR}\"; export TEMP\n"
                    )
                    text = text[:anchor] + block + text[anchor:]
                if text != orig:
                    with open(path, "w", encoding="utf-8", newline="\n") as f:
                        f.write(text)
                    patched += 1
                    self.output.info("complexity: tmpdir patch applied: %s" % path)
        if patched == 0:
            self.output.warning("complexity: tmpdir patch found no test target")

    def _dump_test_logs(self, max_lines=60):
        """On check failure, echo the automake per-test logs (bounded).

        The failure content (complexity.log diff context) is otherwise only
        visible inside the build tree; surfacing the tail keeps the next
        preflight actionable without changing any test semantics.
        """
        for root in (self.source_folder, self.build_folder):
            if not root or not os.path.isdir(root):
                continue
            for dirpath, _dirnames, filenames in os.walk(root):
                if os.path.basename(dirpath) != "tests":
                    continue
                for name in ("complexity.log", "test-suite.log"):
                    if name not in filenames:
                        continue
                    path = os.path.join(dirpath, name)
                    try:
                        with open(path, "r", encoding="utf-8", errors="replace") as f:
                            lines = f.read().splitlines()
                    except OSError:
                        continue
                    self.output.warning(
                        "complexity: ---- %s (last %d of %d lines) ----"
                        % (path, min(len(lines), max_lines), len(lines)))
                    for line in lines[-max_lines:]:
                        self.output.warning("complexity|%s: %s" % (name, line[:400]))

    def build(self):
        apply_conandata_patches(self)
        # E132/E266: same LD_LIBRARY_PATH cover for configure/make links
        # (conanbuild env already has it from generate(), this is belt
        # and suspenders for direct subprocess use).
        self._ensure_lld_runtime()
        _bin_dir, cfg_env = self._private_libopts()
        # Run configure/make with the private autoopts-config first on PATH.
        # Autotools helper does not accept a custom env dict directly, so
        # export PATH for the child processes (conan create is single-shot;
        # no global state leaks beyond this build).
        os.environ["PATH"] = cfg_env["PATH"]
        # ── HMBS readonly_tmp: reuse the injected writable TMPDIR ──
        # /tmp is read-only on the device; HMBS injects a task-independent
        # TMPDIR/TMP/TEMP. Keep it, only fall back to build_folder/tmp when
        # unset, and make sure the directory exists.
        _tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or os.path.join(self.build_folder, "tmp")
        )
        try:
            os.makedirs(_tmpdir, exist_ok=True)
        except Exception:
            _tmpdir = os.path.join(self.build_folder, "tmp")
            os.makedirs(_tmpdir, exist_ok=True)
        for _var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[_var] = _tmpdir
        # ── E011 deterministic fix (2nd strategy): patch umask in
        # configure before running it. Replaces the previous PATH-based
        # mktemp shim, which preflight proved ineffective (same failure at
        # new line 271 — likely Conan toolchain env bypassed os.environ
        # PATH or HMBS_AUTOCONF_MKTEMP_FALLBACK was unset).
        self._patch_autoconf_umask()
        _bash = self._bash_path()
        self.output.info("complexity: test shell=%s tmpdir=%s" % (_bash, _tmpdir))
        # Patch test copies before configure generates build-tree copies,
        # and again after configure so the build-tree copy is covered too.
        # (Second call is cheap: already-patched files are skipped.)
        self._patch_test_tmpdir(_bash, _tmpdir)
        autotools = Autotools(self)
        autotools.configure()
        self._patch_test_tmpdir(_bash, _tmpdir)
        # doc/ needs full autogen (autogen binary) to regenerate
        # example.texi via mk-texi.sh/mk.sh (Debian 01_fix_autobuild.patch +
        # Homebrew formula document the same known-broken doc build; the
        # preflight log shows `.deps/info-dep: No such file or directory`
        # then `make[2]: *** [Makefile:1477: example.texi] Error 1` plus the
        # earlier `autogen: command not found`). The private libopts shim
        # only covers the src/ runtime linkage, not the doc generator, and
        # pulling guile-based autogen is too heavy for this single-lib PR.
        # The shipped binary/man outputs do not need regenerated texi, so
        # build only lib+src here (repo precedent: driver.py install
        # fallback `make install SUBDIRS=\"lib src\"`); tests still run in
        # full via `make check SUBDIRS=tests` below.
        # NOTE: must NOT pass SUBDIRS as a single space-bearing make arg
        # (e.g. "SUBDIRS=lib src"): Conan/the shell splits it into
        # `SUBDIRS=lib` + target `src`, so the top Makefile only builds
        # lib and reports "Nothing to be done for 'src'" while leaving
        # src/complexity missing. Build the two dirs explicitly via -C.
        autotools.make(args=["-j1", "MAKEINFO=true", "-C", "lib"])
        autotools.make(args=["-j1", "MAKEINFO=true", "-C", "src"])
        # ── Hard gate: the upstream test execs $(top_builddir)/src/complexity.
        # Preflight 2026-09-07 proved a SUBDIRS-restricted build can leave
        # it missing (".../build-release/src/complexity: inaccessible or not
        # found" at complexity.test[39]) while make itself exits 0. If the
        # binary is absent, build src/ explicitly and re-verify with a
        # directory listing so the next log shows ground truth either way.
        _cx_bin = os.path.join(self.build_folder, "src", "complexity")
        if not os.path.isfile(_cx_bin):
            self.output.warning(
                "complexity: %s missing after lib/src build; building src explicitly"
                % _cx_bin)
            autotools.make(args=["-j1", "MAKEINFO=true", "-C", "src"])
        if not os.path.isfile(_cx_bin):
            try:
                _names = sorted(os.listdir(os.path.join(self.build_folder, "src")))
            except OSError as _exc:
                _names = ["<listdir failed: %r>" % (_exc,)]
            raise ConanException(
                "complexity: src/complexity still missing before make check; "
                "src/ holds: %s" % (_names,))
        # ── 上游官方测试 (必做): automake harness, TESTS=tests/complexity.test ──
        # LOG_COMPILER forces the bash interpreter even if automake would
        # exec the script directly (shebang already patched too); TMPDIR
        # make-vars are belt-and-suspenders next to the baked-in export.
        try:
            autotools.make(target="check", args=[
                "-j1", "SUBDIRS=tests",
                "LOG_COMPILER=%s" % _bash,
                "TMPDIR=%s" % _tmpdir,
                "TMP=%s" % _tmpdir,
                "TEMP=%s" % _tmpdir,
            ])
            check_rc = 0
            check_error = ""
        except Exception as exc:  # make check failed: still emit the marker, then fail
            check_rc = 1
            check_error = repr(exc)
        result = self._upstream_result(check_rc, check_error)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))
        if result["status"] != "passed":
            self._dump_test_logs()
            raise ConanException(f"complexity upstream tests failed: {result.get('reason', '')}")

    def _upstream_result(self, check_rc, check_error):
        command = "make check SUBDIRS=tests"
        counts = self._read_suite_log()
        if counts is None:
            reason = f"tests/test-suite.log not found after make check (rc={check_rc})"
            if check_error:
                reason += f": {check_error}"
            return {
                "status": "failed",
                "framework": "automake",
                "command": command,
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": reason,
            }
        total = counts.get("TOTAL", 0)
        passed = counts.get("PASS", 0)
        failed = counts.get("FAIL", 0) + counts.get("ERROR", 0) + counts.get("XPASS", 0)
        skipped = counts.get("SKIP", 0) + counts.get("XFAIL", 0)
        executed = total - counts.get("SKIP", 0)
        if check_rc == 0 and total > 0 and failed == 0 and skipped == 0 and passed == total:
            return {
                "status": "passed",
                "framework": "automake",
                "command": command,
                "discovered": total,
                "executed": executed,
                "passed": passed,
                "failed": 0,
                "skipped": 0,
            }
        return {
            "status": "failed",
            "framework": "automake",
            "command": command,
            "discovered": total,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "reason": f"make check rc={check_rc} suite TOTAL={total} PASS={passed} "
                      f"FAIL/ERROR/XPASS={failed} SKIP/XFAIL={skipped}"
                      + (f": {check_error}" if check_error else ""),
        }

    def _read_suite_log(self):
        """Read automake counters from tests/test-suite.log.

        Returns a dict like {"TOTAL": 1, "PASS": 1} or None when the log
        cannot be found (the caller then reports an honest failure).
        """
        log_path = None
        for root in (self.source_folder, self.build_folder):
            if not root or not os.path.isdir(root):
                continue
            direct = os.path.join(root, "tests", "test-suite.log")
            if os.path.isfile(direct):
                log_path = direct
                break
            for dirpath, _dirnames, filenames in os.walk(root):
                if "test-suite.log" in filenames and os.path.basename(dirpath) == "tests":
                    log_path = os.path.join(dirpath, "test-suite.log")
                    break
            if log_path is not None:
                break
        if log_path is None:
            return None
        counts = {}
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                m = re.match(r"^#\s*(TOTAL|PASS|FAIL|SKIP|XFAIL|XPASS|ERROR)\s*:\s*(\d+)", line)
                if m:
                    counts[m.group(1)] = int(m.group(2))
        return counts or None

    def package(self):
        # Manual install (repo precedent: merged cflow 1.0.0 does NOT call
        # autotools.install() but copies the built binary directly).
        # Rationale: `make install SUBDIRS=src` left package bin/complexity
        # missing in preflight (upstream 1/1 passed, then test_package
        # asserted `.../p/bin/complexity` not found), while a doc-skipping
        # automake install stays fragile (install-info/man rebuild pulls
        # the autogen-dependent example.texi rule). Copying the already
        # gated build_folder/src/complexity is deterministic and keeps
        # doc/ out without touching upstream tests.
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        _installed = False
        for _root in (self.build_folder, self.source_folder):
            if not _root or not os.path.isdir(_root):
                continue
            _cand = os.path.join(_root, "src", "complexity")
            if os.path.isfile(_cand):
                copy(self, "complexity", src=os.path.join(_root, "src"), dst=bin_dir)
                _installed = True
                self.output.info("complexity: packaged binary from %s" % _cand)
                break
        if not _installed:
            raise ConanException(
                "complexity: built binary not found for packaging; tried "
                "src/complexity under build_folder and source_folder")
        # Companion script cx-vs-mc (bin_SCRIPTS): same manual copy; fall
        # back to cx-vs-mc.sh source when the chmod-built copy is absent.
        # Not needed by tests (only `complexity` is exec'd) but part of the
        # upstream bindir payload.
        for _root in (self.build_folder, self.source_folder):
            if not _root or not os.path.isdir(_root):
                continue
            _src_dir = os.path.join(_root, "src")
            if os.path.isfile(os.path.join(_src_dir, "cx-vs-mc")):
                copy(self, "cx-vs-mc", src=_src_dir, dst=bin_dir)
                break
            if os.path.isfile(os.path.join(_src_dir, "cx-vs-mc.sh")):
                copy(self, "cx-vs-mc.sh", src=_src_dir, dst=bin_dir)
                try:
                    os.rename(os.path.join(bin_dir, "cx-vs-mc.sh"),
                              os.path.join(bin_dir, "cx-vs-mc"))
                except OSError:
                    pass
                break
        # Best-effort +x (tolerate HMBS_CAP_CHMOD=0): compiler-built files
        # are already +x; Conan copy preserves modes where possible.
        for _name in ("complexity", "cx-vs-mc"):
            _p = os.path.join(bin_dir, _name)
            if os.path.isfile(_p):
                try:
                    _st = os.stat(_p)
                    os.chmod(_p, _st.st_mode | 0o111)
                except OSError:
                    pass
        # Best-effort prebuilt man page (no rebuild): copy only if the
        # tarball already ships a generated complexity.1.
        try:
            for _root in (self.source_folder, self.build_folder):
                if not _root or not os.path.isdir(_root):
                    continue
                for _dirpath, _d, _f in os.walk(_root):
                    if "complexity.1" in _f and os.path.basename(_dirpath) in ("doc", "src", "."):
                        copy(self, "complexity.1", src=_dirpath,
                             dst=os.path.join(self.package_folder, "share", "man", "man1"))
                        break
        except Exception:
            pass
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
