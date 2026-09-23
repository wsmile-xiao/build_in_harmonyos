#!/usr/bin/env python3
"""Conan recipe — libntruprime 0-20260717 (Streamlined NTRU Prime KEM library).

Upstream: https://libntruprime.cr.yp.to (D. J. Bernstein, public domain).
Task version "0-20260717" == upstream release 20260717 (see manifest.yaml).

Build system: djb ./configure (python3) + make, same family as the in-repo
libcpucycles/20260625 recipe, whose OHOS lessons are reused here:
  - Toolchain injection: upstream configure reads no CC/CFLAGS env vars; the
    only compiler source is the source-tree compilers/default file
    ("<command> <flags>" per line, first --version probe wins). build()
    prepends the Conan-configured OHOS clang (tools.build:compiler_executables,
    R33) to the *build-cache copy* of that file; upstream rows stay as
    fallback. No source patch needed.
  - Probes are compile-only (never run target binaries) => cross-safe.
  - Upstream `make install` (scripts-build/install, tempfile inside a
    setgid target dir under umask 077) hits the known hmfs PermissionError;
    the recipe instead collects the documented distributor files from
    build/<arch>/package/{include,lib} (upstream "For distributors" flow).
  - Only explicit make targets are built (libs + ntruprime-test). The
    benchmark (ntruprime-speed) needs libcpucycles, which has no published
    Conan package here and is irrelevant to the library, so it is skipped;
    the sntrup* CLI tools are not packaged (library-only package, hence no
    commands.json, same call as libcpucycles).

Vendored dependency: libntruprime links -lrandombytes (6 kem.c files). There
is no librandombytes Conan package in this repo and this PR must stay
single-library, so the official librandombytes-20240318 tarball (second
source in conandata.yml, libseqlib-style named keys) is built privately
(static kernel variant only — the openssl alternative needs OpenSSL headers
absent on OHOS; its .so files are removed so -lrandombytes resolves to the
.a via LIBRARY_PATH) and its objects end up *inside* libntruprime:
shared .so pulls them in at link time (no DT_NEEDED on randombytes),
static .a gets them merged with `ar r` afterwards. Consumers link only
-lntruprime. See notes.md for the full rationale.

Upstream tests: command/ntruprime-test.c main() calls 126 test_* functions
(verify/hash/decode/encode/sort/core/kem); the no-arg run is the documented
workhorse of ntruprime-fulltest. build() runs it, requires exit 0 plus the
"all tests succeeded" trailer, and persists res/upstream_test_result.json
(libcanard pattern) so test_package can re-emit the marker on cache hits.
The valgrind TIMECOP pass needs valgrind (absent on OHOS) and the fulltest
driver costs ~529 core-min; both are disclosed as not run in notes.md and
the PR 补充说明.
"""

import hashlib
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

# Number of test_* function calls in command/ntruprime-test.c main()
# (no-arg run executes all of them; see notes.md "上游测试入口").
N_UPSTREAM_TESTS = 126


class LibntruprimeConan(ConanFile):
    name = "libntruprime"
    version = "0-20260717"
    description = "Microlibrary for the Streamlined NTRU Prime lattice-based KEM (sntrup)"
    # Upstream dual-offers MIT among (LicenseRef-PD-hp OR CC0-1.0 OR 0BSD OR
    # MIT-0 OR MIT); declare MIT terms. Full text: doc/license.md upstream.
    license = "MIT"
    homepage = "https://libntruprime.cr.yp.to"
    topics = ("ntruprime", "sntrup", "post-quantum", "kem", "lattice")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    # sha256 of the gate-verified libntruprime.so.1 (set in
    # _verify_library_completeness, compared in _lib_forensics).
    _gate_so1_digest = None

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def validate(self):
        # R32: membership test, never `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libntruprime is only supported on Linux/OHOS, not %s" % self.settings.os
            )

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"]["main"], strip_root=True)
        # Vendored CSPRNG dependency (see module docstring); lands in the
        # source cache only, never as a separate Conan package.
        get(
            self,
            **self.conan_data["sources"]["randombytes"],
            destination=os.path.join(self.source_folder, "deps", "randombytes"),
            strip_root=True,
        )

    # -- toolchain ------------------------------------------------------
    def _usable_cc(self):
        # R33: never rely on bare ${CC}; prefer the profile conf, fall back
        # to PATH lookup (also keeps plain-Linux builds working where the
        # conf is unset). Fail closed when nothing resolves.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cand = compilers.get("c")
        if cand and os.path.isabs(str(cand)) and os.path.isfile(str(cand)):
            return str(cand)
        for tool in ("clang", "cc", "gcc"):
            found = shutil.which(tool)
            if found and os.path.isfile(found):
                self.output.info("using PATH compiler %s (conf c=%s)" % (found, cand))
                return found
        if cand and os.path.isfile(str(cand)):
            return str(cand)
        raise ConanException(
            "no usable C compiler: tools.build:compiler_executables.c=%r "
            "and no clang/cc/gcc on PATH" % (cand,)
        )

    def _usable_ar(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cand = compilers.get("ar")
        if cand and os.path.isfile(str(cand)):
            return str(cand)
        for tool in ("llvm-ar", "ar"):
            found = shutil.which(tool)
            if found and os.path.isfile(found):
                return found
        raise ConanException("no usable archiver (ar) on PATH")

    # Upstream compilers/default rows, verbatim from the inspected tarball:
    #   clang: "-Wall -fPIC -fwrapv -Qunused-arguments -O2"
    #   gcc:   "-Wall -fPIC -fwrapv -O2" (no -Qunused-arguments).
    # -Qunused-arguments is clang-only; feeding it to gcc fails every
    # compilation, and upstream scripts/compile turns failures into empty .o
    # files *without* failing make (silent empty libs -> mass "symbol not
    # found" relocation errors from ntruprime-test). Choose the row by
    # compiler family; unknown compilers get the gcc row (omitting the flag
    # is harmless everywhere, adding it is fatal on gcc).
    _CC_FLAGS_CLANG = "-Wall -fPIC -fwrapv -Qunused-arguments -O2"
    _CC_FLAGS_GCC = "-Wall -fPIC -fwrapv -O2"

    def _cc_flags(self, cc):
        base = os.path.basename(str(cc)).lower()
        if "clang" in base:
            return self._CC_FLAGS_CLANG
        if "gcc" in base:
            return self._CC_FLAGS_GCC
        try:
            proc = subprocess.run(
                [str(cc), "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=60,
            )
            if "clang" in (proc.stdout or "").lower():
                return self._CC_FLAGS_CLANG
        except Exception:
            pass
        return self._CC_FLAGS_GCC

    def _sha256(self, path):
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def _nm_defined_symbols(self, so_path):
        """Defined dynamic symbols of a shared object (strict parse).

        Returns (tool, dict(name -> typechar)). Falls back to (tool, None)
        when no nm exists or no line parses (tool incompatibility: caller
        warns and skips instead of failing on the parser itself).
        The type map matters: "i"/"I" means STT_GNU_IFUNC, which nm counts
        as defined but the OHOS/musl loader cannot relocate (see
        --no-tryifunc note in build()).
        """
        nm = None
        for tool in ("llvm-nm", "nm"):
            found = shutil.which(tool)
            if found and os.path.isfile(found):
                nm = found
                break
        if nm is None:
            return None, None
        proc = subprocess.run(
            [nm, "-D", "--defined-only", so_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
        )
        syms = {}
        for line in (proc.stdout or "").splitlines():
            parts = line.split()
            if len(parts) < 3:
                continue
            symtype, name = parts[-2], parts[-1]
            if len(symtype) != 1 or symtype in ("U", "u", "?", "N"):
                continue
            syms.setdefault(name.split("@")[0], symtype)
        if not syms:
            return nm, None
        return nm, syms

    def _prepend_configured_compiler(self, src_dir):
        """Prepend the resolved compiler to compilers/default (build-cache
        copy only; upstream candidate rows stay untouched as fallback)."""
        cc = self._usable_cc()
        # Keep upstream flags byte-for-byte per compiler family; only the
        # compiler path is ours.
        line = "%s %s" % (cc, self._cc_flags(cc))
        self.output.info("injected compiler row: %s" % line)
        path = os.path.join(src_dir, "compilers", "default")
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
        if content.startswith(line + "\n"):
            return
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(line + "\n" + content)
        self.output.info("prepended compiler to %s: %s" % (path, line))

    def _configure_host(self):
        arch = str(self.settings.arch)
        if arch in ("armv8", "armv8.3", "arm64", "aarch64"):
            return "arm64"
        if arch in ("x86_64", "x86"):
            return "amd64"
        return None

    def _ensure_writable_tmp(self):
        # Never rely on system /tmp (read-only on the true machine). Prefer
        # the injected TMPDIR/TMP/TEMP, else use a dir under build_folder.
        for var in ("TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(var)
            if val and os.path.isdir(val) and os.access(val, os.W_OK):
                return val
        fallback = os.path.join(self.build_folder, ".hmbs-tmp")
        try:
            os.makedirs(fallback, exist_ok=True)
        except Exception:
            pass
        for var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[var] = fallback
        return fallback

    def _python3(self):
        found = shutil.which("python3")
        if found:
            return found
        raise ConanException("python3 not on PATH (needed for ./configure)")

    # -- build ----------------------------------------------------------
    def build(self):
        tmpdir = self._ensure_writable_tmp()
        apply_conandata_patches(self)

        host = self._configure_host()
        host_flag = " --host=%s" % host if host else ""
        build_subdir = host or "arm64"
        if not host:
            # Upstream auto-detects from platform.machine(); the build dir
            # name follows hostsanitize(). aarch64 Linux/OHOS => arm64.
            import platform as _platform

            m = _platform.machine().lower()
            build_subdir = "arm64" if ("aarch64" in m or m.startswith("arm")) else m

        py3 = self._python3()

        # 1) Vendored librandombytes first (static, kernel variant only).
        # Upstream `make` default builds both librandombytes-kernel and
        # librandombytes-openssl; the openssl variant needs <openssl/rand.h>
        # + -lcrypto, which OHOS does not provide (true-machine error:
        # "fatal error: 'openssl/rand.h' file not found" while building
        # package/lib/librandombytes-openssl.a). The kernel variant
        # (getrandom/getentropy//dev/urandom) is the upstream default
        # (defaultimpl='kernel') and is self-contained, so build only its
        # explicit targets and skip the openssl alternative entirely.
        rb_src = os.path.join(self.source_folder, "deps", "randombytes")
        self._prepend_configured_compiler(rb_src)
        # Never touch system /tmp (read-only on the true machine): point
        # the unused --prefix at the writable TMPDIR-backed dir instead.
        rb_prefix = os.path.join(tmpdir, "librandombytes-private")
        try:
            os.makedirs(rb_prefix, exist_ok=True)
        except Exception:
            pass
        self.run(
            "%s ./configure%s --prefix=%s" % (py3, host_flag, rb_prefix),
            cwd=rb_src,
        )
        # NOTE: package/* targets live in the generated build/<host>/Makefile,
        # not the top-level Makefile (which only forwards default/install).
        # Running them from the source root yields "No rule to make target".
        rb_build = os.path.join(rb_src, "build", build_subdir)
        self.run(
            "make -j1 package/lib/librandombytes-kernel.a "
            "package/lib/librandombytes.a",
            cwd=rb_build,
        )
        rb_pkg_lib = os.path.join(rb_src, "build", build_subdir, "package", "lib")
        rb_pkg_inc = os.path.join(rb_src, "build", build_subdir, "package", "include")
        # The generic librandombytes.a is a symlink to the kernel archive
        # (defaultimpl='kernel'); hmfs symlink support varies, so fall back
        # to a plain copy when the link is missing but the kernel archive
        # exists.
        _generic_a = os.path.join(rb_pkg_lib, "librandombytes.a")
        _kernel_a = os.path.join(rb_pkg_lib, "librandombytes-kernel.a")
        if not os.path.lexists(_generic_a) and os.path.isfile(_kernel_a):
            shutil.copy2(_kernel_a, _generic_a)
            self.output.info("copied kernel archive to generic name (no symlink)")
        # Force static resolution of -lrandombytes: only the .a may exist.
        for fn in os.listdir(rb_pkg_lib):
            if ".so" in fn or fn.endswith(".dylib"):
                os.remove(os.path.join(rb_pkg_lib, fn))
                self.output.info("removed vendored shared object (static-only): %s" % fn)
        if not os.path.isfile(os.path.join(rb_pkg_lib, "librandombytes.a")):
            raise ConanException("vendored librandombytes.a missing in %s" % rb_pkg_lib)

        # 2) libntruprime configure + explicit targets only.
        # OHOS has no valgrind: pass --no-valgrind so configure copies the
        # plain include-build/crypto_declassify.h (no-op stub) instead of
        # include-build-valgrind (needs <valgrind/memcheck.h>). Without this,
        # every kem compile fails and scripts/selected aborts with
        # AssertionError on selected/kem_sntrup653.
        self._prepend_configured_compiler(self.source_folder)
        # --no-tryifunc: upstream dispatch defaults to GNU IFUNC resolvers
        # when the compiler merely *accepts* __attribute__((ifunc)) (probe is
        # compile+readelf only, never runs the loader). The OHOS/musl loader
        # cannot relocate STT_GNU_IFUNC, so every public ntruprime_* symbol
        # then fails at startup with "symbol not found" even though nm -D
        # lists it as defined (type i) -- the exact 126/126 exit=127 seen on
        # the true machine. --no-tryifunc forces the documented
        # constructor-pointer dispatch (plain FUNC symbols) instead.
        self.run(
            "%s ./configure%s --no-valgrind --no-tryifunc --prefix=%s" % (py3, host_flag, self.package_folder),
            cwd=self.source_folder,
        )
        # Harness-only robustness (does not touch shipped artifacts): embed
        # an absolute RPATH to the build-tree package lib into the generated
        # command/link script, so package/bin/ntruprime-test resolves
        # DT_NEEDED libntruprime.so.1 without depending on LD_LIBRARY_PATH
        # propagation (musl ignores it for setuid; a scrubbed env would show
        # the same mass "symbol not found" fingerprint). LD_LIBRARY_PATH is
        # still set at run time as well (belt and suspenders).
        self._patch_test_link_rpath(build_subdir)
        old_libpath = os.environ.get("LIBRARY_PATH")
        old_cpath = os.environ.get("CPATH")
        os.environ["LIBRARY_PATH"] = rb_pkg_lib + (
            os.pathsep + old_libpath if old_libpath else ""
        )
        os.environ["CPATH"] = rb_pkg_inc + (
            os.pathsep + old_cpath if old_cpath else ""
        )
        try:
            # Same as above: explicit package/* targets live in
            # build/<host>/Makefile, so run from the build subdir.
            # Two phases: libraries first, then the test binary. Between
            # them the .so linker name is normalized to a regular file
            # (upstream's Makefile creates it via `ln -s`, whose hmfs
            # semantics are uncertain) and the libs are gated for
            # completeness -- scripts/compile silences per-file failures
            # into empty .o files, so without a gate a broken tree only
            # surfaces as mass relocation errors from ntruprime-test.
            ntru_build = os.path.join(self.source_folder, "build", build_subdir)
            self.run(
                "make -j1 package/lib/libntruprime.a "
                "package/lib/libntruprime.so.1",
                cwd=ntru_build,
            )
            self._normalize_so_linkname(ntru_build)
            self._verify_library_completeness(ntru_build)
            self._verify_elf_machine_and_needed(ntru_build)
            self.run(
                "make -j1 package/bin/ntruprime-test result-impl",
                cwd=ntru_build,
            )
        finally:
            if old_libpath is None:
                os.environ.pop("LIBRARY_PATH", None)
            else:
                os.environ["LIBRARY_PATH"] = old_libpath
            if old_cpath is None:
                os.environ.pop("CPATH", None)
            else:
                os.environ["CPATH"] = old_cpath

        build_dir = os.path.join(self.source_folder, "build", build_subdir)
        self._log_implementation_selection(build_dir)

        # 3) Merge vendored randombytes objects into the static archive so
        # consumers of -lntruprime never need a separate -lrandombytes.
        self._bundle_randombytes_static(
            os.path.join(build_dir, "package", "lib", "libntruprime.a"),
            os.path.join(rb_pkg_lib, "librandombytes.a"),
        )

        # 4) Upstream test suite (conventional ntruprime-test, all 126 cases).
        result = self._run_upstream_tests(build_dir)
        with open(
            os.path.join(self.build_folder, "upstream_test_result.json"),
            "w",
            encoding="utf-8",
            newline="\n",
        ) as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result))
        if result["status"] != "passed":
            raise ConanException("libntruprime upstream tests failed: %r" % (result,))

    def _log_implementation_selection(self, build_dir):
        # `make` prints selections for build logs (20260717 changelog). Mirror
        # that: surface selected/* + result-impl into the conan log.
        try:
            selected_dir = os.path.join(build_dir, "selected")
            if os.path.isdir(selected_dir):
                for fn in sorted(os.listdir(selected_dir)):
                    with open(os.path.join(selected_dir, fn), encoding="utf-8") as fh:
                        self.output.info("selected %s: %s" % (fn, fh.read().strip()))
            result_impl = os.path.join(build_dir, "result-impl")
            if os.path.isfile(result_impl):
                with open(result_impl, encoding="utf-8") as fh:
                    for line in fh.read().splitlines()[:40]:
                        self.output.info("result-impl: %s" % line)
        except Exception as exc:
            self.output.warning("could not log implementation selection: %r" % (exc,))

    def _patch_test_link_rpath(self, build_subdir):
        """Embed an absolute RPATH into the generated command/link script.

        Only the build-cache copy is edited (upstream sources untouched).
        The test binary is a harness artifact, never shipped, so an absolute
        build-tree RPATH is safe and makes DT_NEEDED resolution independent
        of environment propagation.
        """
        link = os.path.join(
            self.source_folder, "build", build_subdir, "command", "link"
        )
        libdir = os.path.join(
            self.source_folder, "build", build_subdir, "package", "lib"
        )
        try:
            with open(link, encoding="utf-8") as fh:
                content = fh.read()
        except OSError as exc:
            self.output.warning("command/link not found, RPATH skipped: %r" % (exc,))
            return
        marker = "-Wl,-rpath,%s" % libdir
        if marker in content:
            return
        # Upstream script shape: firstcompiler line, then flag lines ending
        # with backslash, then '-o "$target" "$@"'. Insert the rpath flag
        # right after the -fvisibility=hidden line when present.
        anchor = "  -fvisibility=hidden \\\n"
        insert = "  -Wl,-rpath,\"%s\" \\\n" % libdir
        if anchor in content:
            content = content.replace(anchor, anchor + insert, 1)
        else:
            lines = content.splitlines(keepends=True)
            lines.insert(2, insert)
            content = "".join(lines)
        with open(link, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
        try:
            os.chmod(link, 0o755)
        except OSError:
            pass
        self.output.info("patched command/link with RPATH %s" % libdir)

    def _readelf(self):
        for tool in ("llvm-readelf", "readelf"):
            found = shutil.which(tool)
            if found and os.path.isfile(found):
                return found
        return None

    def _verify_elf_machine_and_needed(self, build_dir):
        """Fail closed on wrong-arch objects or leaked shared dependencies.

        The mass "symbol not found" fingerprint is also produced when
        libntruprime.so.1 itself fails to load (musl prints the primary
        "Error loading shared library ..." line first, then one relocation
        error per symbol). Two silent build faults cause exactly that:
        (a) objects built for the wrong machine, (b) a DT_NEEDED on a
        shared librandombytes/libcpucycles that is absent at run time.
        """
        libdir = os.path.join(build_dir, "package", "lib")
        so1 = os.path.join(libdir, "libntruprime.so.1")
        readelf = self._readelf()
        if readelf is None:
            self.output.warning("no readelf; skipping ELF machine/NEEDED gate")
            return
        proc = subprocess.run(
            [readelf, "-h", so1],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=120,
        )
        machine = ""
        for line in (proc.stdout or "").splitlines():
            if "Machine:" in line:
                machine = line.split("Machine:")[1].strip()
                break
        self.output.info("ELF machine of libntruprime.so.1: %s" % machine)
        arch = str(self.settings.arch)
        if arch in ("armv8", "armv8.3", "arm64", "aarch64"):
            if "AArch64" not in machine:
                raise ConanException(
                    "shared object built for wrong machine: %r "
                    "(expected AArch64 for arch %s)" % (machine, arch)
                )
        proc = subprocess.run(
            [readelf, "-d", so1],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=120,
        )
        needed = sorted(
            line.split("[")[1].split("]")[0]
            for line in (proc.stdout or "").splitlines()
            if "NEEDED" in line and "[" in line
        )
        self.output.info("DT_NEEDED of libntruprime.so.1: %s" % needed)
        for dep in needed:
            low = dep.lower()
            if "randombytes" in low or "cpucycles" in low:
                raise ConanException(
                    "shared object leaks vendored dependency %r; "
                    "must be statically bundled (no DT_NEEDED)" % dep
                )
            if os.path.isabs(dep):
                raise ConanException(
                    "shared object has absolute DT_NEEDED %r" % dep
                )

    def _normalize_so_linkname(self, build_dir):
        # Upstream links the test binary against package/lib/libntruprime.so,
        # which its Makefile creates via `ln -s libntruprime.so.1` (hmfs
        # symlink semantics are uncertain). Make it a regular-file copy of
        # the SONAME file instead: make then sees it as up-to-date and skips
        # the ln rule, and the test link never depends on a symlink.
        libdir = os.path.join(build_dir, "package", "lib")
        soname = os.path.join(libdir, "libntruprime.so.1")
        linkname = os.path.join(libdir, "libntruprime.so")
        if not os.path.isfile(soname):
            raise ConanException("expected shared object missing: %s" % soname)
        if os.path.islink(linkname) or not os.path.lexists(linkname):
            try:
                if os.path.lexists(linkname):
                    os.remove(linkname)
            except OSError:
                pass
            shutil.copy2(soname, linkname)
            os.utime(linkname, None)
            self.output.info("normalized .so linkname to regular copy")

    def _dump_build_diagnostics(self, build_dir):
        # Best-effort log spew for a completeness-gate failure: selected
        # implementations plus the first failing compiler outputs, bounded.
        try:
            selected_dir = os.path.join(build_dir, "selected")
            if os.path.isdir(selected_dir):
                for fn in sorted(os.listdir(selected_dir)):
                    with open(
                        os.path.join(selected_dir, fn), encoding="utf-8"
                    ) as fh:
                        self.output.info(
                            "diag selected %s: %s" % (fn, fh.read().strip()[:500])
                        )
        except Exception as exc:
            self.output.warning("diag selected failed: %r" % (exc,))
        try:
            shown = 0
            scanned = 0
            for root, _dirs, files in os.walk(build_dir):
                for fn in sorted(files):
                    if not fn.startswith("result-compile-"):
                        continue
                    scanned += 1
                    if scanned > 200 or shown >= 3:
                        continue
                    path = os.path.join(root, fn)
                    try:
                        if os.path.getsize(path) == 0:
                            continue
                        with open(path, encoding="utf-8", errors="replace") as fh:
                            self.output.info(
                                "diag %s: %s"
                                % (
                                    os.path.relpath(path, build_dir),
                                    fh.read(2000),
                                )
                            )
                        shown += 1
                    except OSError:
                        continue
        except Exception as exc:
            self.output.warning("diag result-compile failed: %r" % (exc,))

    def _verify_library_completeness(self, build_dir):
        """Fail closed if the just-built libs are incomplete.

        Upstream scripts/compile turns per-file failures into empty .o files
        without failing make, so a broken tree otherwise surfaces only as
        mass "symbol not found" relocation errors from ntruprime-test
        (exit 127). Gate here with a clear message instead. Runs before the
        vendored randombytes merge so 4 bundled objects cannot mask an empty
        archive.
        """
        ofiles_dir = os.path.join(build_dir, "ofiles")
        try:
            ofiles = [fn for fn in os.listdir(ofiles_dir) if fn.endswith(".o")]
        except OSError as exc:
            raise ConanException("ofiles/ missing after make: %r" % (exc,))
        # A healthy arm64 selection compiles hundreds of units (6 sntrup
        # parameter sets x verify/hash/decode/encode/sort/core/kem, plus
        # dispatch/cpuid/cryptoint); a dispatch-only degenerate tree has
        # ~15. 50 separates them with wide margin on both sides.
        if len(ofiles) < 50:
            self._dump_build_diagnostics(build_dir)
            raise ConanException(
                "incomplete build: only %d objects in ofiles/ (expected "
                ">= 50); see diag lines above" % len(ofiles)
            )
        empty = []
        for fn in ofiles:
            try:
                if os.path.getsize(os.path.join(ofiles_dir, fn)) == 0:
                    empty.append(fn)
            except OSError:
                empty.append(fn)
        if empty:
            self._dump_build_diagnostics(build_dir)
            raise ConanException(
                "incomplete build: %d empty objects in ofiles/ (e.g. %s); "
                "per-file compilations failed, see diag lines above"
                % (len(empty), ", ".join(sorted(empty)[:5]))
            )
        libdir = os.path.join(build_dir, "package", "lib")
        so1 = os.path.join(libdir, "libntruprime.so.1")
        if not os.path.isfile(so1) or os.path.getsize(so1) == 0:
            raise ConanException("shared object empty or missing: %s" % so1)
        nm, defined_syms = self._nm_defined_symbols(so1)
        if nm is None or defined_syms is None:
            self.output.warning(
                "no usable nm output for %s; skipping export check" % so1
            )
        else:
            for sym in (
                "ntruprime_kem_sntrup761_keypair",
                "ntruprime_sort_int32",
            ):
                if sym not in defined_syms:
                    raise ConanException(
                        "shared object missing defined export %s "
                        "(strict nm -D parse, %d defined symbols)" % (sym, len(defined_syms))
                    )
                if defined_syms[sym] in ("i", "I"):
                    raise ConanException(
                        "shared object exports %s as GNU IFUNC (type %s); "
                        "the OHOS/musl loader cannot relocate IFUNC, rebuild "
                        "with --no-tryifunc" % (sym, defined_syms[sym])
                    )
            self.output.info(
                "shared object exports verified (%d defined symbols, plain FUNC)" % len(defined_syms)
            )
        try:
            self._gate_so1_digest = self._sha256(so1)
        except OSError:
            self._gate_so1_digest = None
        self.output.info(
            "gate so1 sha256=%s" % (self._gate_so1_digest or "unknown")
        )
        ar = self._usable_ar()
        proc = subprocess.run(
            [ar, "t", os.path.join(libdir, "libntruprime.a")],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
        )
        if "kem" not in (proc.stdout or "").lower():
            self.output.info(proc.stdout or "")
            raise ConanException(
                "static archive has no kem objects (ar t output above)"
            )
        self.output.info(
            "library completeness verified (%d objects)" % len(ofiles)
        )

    def _bundle_randombytes_static(self, lib_path, rb_archive):
        if not os.path.isfile(lib_path):
            raise ConanException("expected static archive missing: %s" % lib_path)
        ar = self._usable_ar()
        tmpdir = os.path.join(self.build_folder, ".hmbs-tmp", "rb-objs")
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
            os.makedirs(tmpdir, exist_ok=True)
            proc = subprocess.run(
                [ar, "x", rb_archive],
                cwd=tmpdir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            if proc.returncode != 0:
                raise ConanException("ar x failed: %s" % (proc.stdout or ""))
            objs = sorted(
                os.path.join(tmpdir, fn)
                for fn in os.listdir(tmpdir)
                if fn.endswith(".o")
            )
            if not objs:
                raise ConanException("no objects extracted from %s" % rb_archive)
            proc = subprocess.run(
                [ar, "r", lib_path] + objs,
                cwd=self.build_folder,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            if proc.returncode != 0:
                raise ConanException("ar r failed: %s" % (proc.stdout or ""))
            self.output.info(
                "bundled %d vendored randombytes objects into %s"
                % (len(objs), lib_path)
            )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def _lib_forensics(self, build_dir, test_env=None):
        """Compact one-line forensics for a test-run failure.

        The focused preflight summary elides middle logs but always shows
        the result reason, so the decisive facts (was the verified .so.1
        rebuilt? what does the loader actually see?) must travel in it.
        """
        libdir = os.path.join(build_dir, "package", "lib")
        test_bin = os.path.join(build_dir, "package", "bin", "ntruprime-test")
        bits = []
        if test_env is not None:
            bits.append("ldpath=%s" % test_env.get("LD_LIBRARY_PATH"))
            bits.append("preload=%s" % test_env.get("LD_PRELOAD"))
        try:
            entries = sorted(os.listdir(libdir))
        except OSError as exc:
            return "libdir unreadable: %r" % (exc,)
        sizes = []
        for fn in entries:
            try:
                sizes.append(
                    "%s:%d" % (fn, os.path.getsize(os.path.join(libdir, fn)))
                )
            except OSError:
                sizes.append("%s:?" % fn)
        bits.append("libfiles=[%s]" % ",".join(sizes))
        so1 = os.path.join(libdir, "libntruprime.so.1")
        try:
            digest = self._sha256(so1)[:16]
        except OSError:
            digest = "missing"
        gate = getattr(self, "_gate_so1_digest", None)
        bits.append(
            "so1sha=%s gate=%s rebuilt=%s"
            % (
                digest,
                (gate[:16] if gate else "none"),
                (gate is not None and gate[:16] != digest),
            )
        )
        _nm, syms = self._nm_defined_symbols(so1)
        if syms is None:
            bits.append("nm=unavailable")
        else:
            kem = sum(1 for s in syms if ".kem_sntrup" in s or "_kem_" in s)
            n_ifunc = sum(1 for t in syms.values() if t in ("i", "I"))
            bits.append(
                "nm_defined=%d nm_kem=%d nm_kem761=%s%s nm_sort=%s%s nm_ifunc=%d"
                % (
                    len(syms),
                    kem,
                    ("ntruprime_kem_sntrup761_keypair" in syms),
                    (":" + syms.get("ntruprime_kem_sntrup761_keypair", "?")),
                    ("ntruprime_sort_int32" in syms),
                    (":" + syms.get("ntruprime_sort_int32", "?")),
                    n_ifunc,
                )
            )
        readelf = self._readelf()
        if readelf is None:
            bits.append("readelf=unavailable")
        else:
            try:
                proc = subprocess.run(
                    [readelf, "-d", test_bin],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=120,
                )
                needed = sorted(
                    line.split("[")[1].split("]")[0]
                    for line in (proc.stdout or "").splitlines()
                    if "NEEDED" in line and "[" in line
                )
                bits.append("needed=%s" % needed)
                rpaths = sorted(
                    line.split("[")[1].split("]")[0]
                    for line in (proc.stdout or "").splitlines()
                    if ("PATH" in line) and ("[" in line)
                )
                bits.append("rpaths=%s" % rpaths)
            except Exception as exc:
                bits.append("readelf failed: %r" % (exc,))
            # The shared object's own dependencies: if libntruprime.so.1
            # itself fails to load, musl prints the primary error first and
            # then one "symbol not found" per relocation -- the exact mass
            # fingerprint seen so far. Its NEEDED decides that.
            try:
                proc = subprocess.run(
                    [readelf, "-d", so1],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=120,
                )
                libneeded = sorted(
                    line.split("[")[1].split("]")[0]
                    for line in (proc.stdout or "").splitlines()
                    if "NEEDED" in line and "[" in line
                )
                bits.append("libneeded=%s" % libneeded)
            except Exception as exc:
                bits.append("libneeded failed: %r" % (exc,))
            # ELF machines: a wrong-arch .so/.o mix links but never loads.
            try:
                machines = []
                for path in (so1, test_bin):
                    proc = subprocess.run(
                        [readelf, "-h", path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        timeout=120,
                    )
                    machine = "?"
                    for line in (proc.stdout or "").splitlines():
                        if "Machine:" in line:
                            machine = line.split("Machine:")[1].strip()
                            break
                    machines.append(
                        "%s=%s" % (os.path.basename(path), machine)
                    )
                bits.append("machine=[%s]" % ",".join(machines))
            except Exception as exc:
                bits.append("machine failed: %r" % (exc,))
        # Explicit-path dlopen probe: uses the same loader as the test
        # binary but bypasses *all* search-path logic. If this fails, the
        # verified file itself is unloadable (primary load error carried in
        # the message); if it succeeds, implicit resolution picks another
        # file and the impostor scan below must explain it.
        try:
            import ctypes

            lib = ctypes.CDLL(so1)
            _sym = lib["ntruprime_kem_sntrup761_keypair"]
            bits.append("dlopen=ok dlsym_kem761=ok")
        except Exception as exc:
            bits.append("dlopen_probe=%s" % str(exc)[:220])
        impostors = []
        sysdirs = [
            "/lib",
            "/lib64",
            "/usr/lib",
            "/usr/lib64",
            "/usr/local/lib",
            "/usr/local/lib64",
            "/data/service/hnp/lib",
        ]
        if test_env is not None:
            for entry in (test_env.get("LD_LIBRARY_PATH") or "").split(os.pathsep):
                entry = entry.strip()
                if entry and entry not in sysdirs:
                    sysdirs.append(entry)
        for d in sysdirs:
            for fn in ("libntruprime.so.1", "libntruprime.so"):
                p = os.path.join(d, fn)
                if os.path.lexists(p):
                    try:
                        impostors.append("%s:%d" % (p, os.path.getsize(p)))
                    except OSError:
                        impostors.append("%s:?" % p)
        bits.append("impostors=%s" % impostors)
        return " ".join(bits)

    def _run_upstream_tests(self, build_dir):
        test_bin = os.path.join(build_dir, "package", "bin", "ntruprime-test")
        command = "%s (no args: all %d test_* functions)" % (test_bin, N_UPSTREAM_TESTS)
        if not os.path.isfile(test_bin):
            return {
                "status": "failed",
                "framework": "ntruprime-test",
                "command": command,
                "discovered": N_UPSTREAM_TESTS,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "test binary missing: %s" % test_bin,
            }
        libdir = os.path.join(build_dir, "package", "lib")
        env = dict(os.environ)
        prev = env.get("LD_LIBRARY_PATH")
        env["LD_LIBRARY_PATH"] = libdir + (os.pathsep + prev if prev else "")
        # No LD_PRELOAD: the preload pin (impostor theory) had zero effect --
        # with preload set the run still failed 126/126, impostors=[] and
        # digests unchanged, disproving the tree-external-file hypothesis.
        # Resolution was already correct; the symbols themselves were
        # unloadable (GNU IFUNC, now disabled via --no-tryifunc).
        env.pop("LD_PRELOAD", None)
        try:
            proc = subprocess.run(
                [test_bin],
                cwd=build_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=1800,
            )
            output = proc.stdout or ""
        except Exception as exc:
            return {
                "status": "failed",
                "framework": "ntruprime-test",
                "command": command,
                "discovered": N_UPSTREAM_TESTS,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "harness could not run test binary: %r" % (exc,),
            }
        # Anti silent-pass: a healthy run prints version/arch/cpuid lines
        # (proof the real binary executed) plus the success trailer.
        # Log BOTH head and tail: musl prints the primary error ("Error
        # loading shared library ...") first and per-symbol relocation
        # errors after it. Four rounds only kept the tail, so a primary
        # load failure of libntruprime.so.1 itself stayed invisible.
        self.output.info(output[:3000])
        self.output.info(output[-4000:])
        ran = "ntruprime version" in output and "ntruprime arch" in output
        succeeded = "all tests succeeded" in output
        failed_mark = "some tests failed" in output or "failure:" in output
        ok = proc.returncode == 0 and ran and succeeded and not failed_mark
        if not ok:
            head = " ".join(
                line.strip() for line in output.splitlines() if line.strip()
            )[:600]
            reason = "exit=%d ran=%s succeeded=%s failed_mark=%s head=%s | %s" % (
                proc.returncode,
                ran,
                succeeded,
                failed_mark,
                head,
                self._lib_forensics(build_dir, env),
            )
            return {
                "status": "failed",
                "framework": "ntruprime-test",
                "command": command,
                "discovered": N_UPSTREAM_TESTS,
                "executed": N_UPSTREAM_TESTS,
                "passed": 0,
                "failed": N_UPSTREAM_TESTS,
                "skipped": 0,
                "reason": reason,
            }
        return {
            "status": "passed",
            "framework": "ntruprime-test",
            "command": command,
            "discovered": N_UPSTREAM_TESTS,
            "executed": N_UPSTREAM_TESTS,
            "passed": N_UPSTREAM_TESTS,
            "failed": 0,
            "skipped": 0,
        }

    # -- package --------------------------------------------------------
    def package(self):
        build_subdir = self._configure_host() or "arm64"
        pkg = os.path.join(self.source_folder, "build", build_subdir, "package")
        copy(
            self,
            "ntruprime.h",
            os.path.join(pkg, "include"),
            os.path.join(self.package_folder, "include"),
            keep_path=False,
        )
        lib_src = os.path.join(pkg, "lib")
        lib_dst = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            # Ship the SONAME file under both the SONAME and the linker
            # name as regular files (no symlinks: hmfs symlink support is
            # not guaranteed). The DT_NEEDED entry (.so.1) and -lntruprime
            # (.so) then both resolve to identical content.
            copy(self, "libntruprime.so.1", lib_src, lib_dst, keep_path=False)
            shipped = os.path.join(lib_dst, "libntruprime.so.1")
            link_name = os.path.join(lib_dst, "libntruprime.so")
            try:
                if os.path.isfile(link_name) and not os.path.islink(link_name):
                    os.remove(link_name)
            except OSError:
                pass
            if not os.path.lexists(link_name):
                shutil.copy2(shipped, link_name)
        else:
            copy(self, "libntruprime.a", lib_src, lib_dst, keep_path=False)
        copy(
            self,
            "license.md",
            os.path.join(self.source_folder, "doc"),
            os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "upstream_test_result.json",
            self.build_folder,
            os.path.join(self.package_folder, "res"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["ntruprime"]
        self.cpp_info.set_property("cmake_file_name", "ntruprime")
        self.cpp_info.set_property("cmake_target_name", "ntruprime::ntruprime")
        self.cpp_info.set_property("pkg_config_name", "libntruprime")
