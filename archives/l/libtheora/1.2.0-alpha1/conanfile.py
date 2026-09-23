#!/usr/bin/env python3
"""Conan recipe — libtheora 1.2.0-alpha1 (Theora video codec, Xiph.Org).

Build system: upstream Autotools (configure + make). The 2010-era tarball
ships a config.guess/config.sub pair (2003) that cannot recognise
HarmonyOS/OHOS, so a modern, HarmonyOS-patched pair (GNU config
2023-08-22 base, same pair as babeltrace2 2.1.2, in-repo precedent
lttoolbox 3.7.6) is vendored in patches/autotools/ and copied over the
stale pair in source().

OHOS specifics (all in-repo precedents):
  - E007: config.guess/config.sub replacement (see above). The modern
    pair detects aarch64-unknown-linux-ohos natively, so no --host/
    --build triplet hacks are needed; staying in native mode also keeps
    configure's optional-dependency probes honest (vorbis/examples are
    cleanly auto-disabled when absent — forcing cross mode would make
    XIPH_PATH_VORBIS "assume OK" and break the example build).
  - E011: configure creates temp files via `mktemp -d "./confXXXXXX"`
    under `umask 077`; on HMDFS the resulting 0700 dirs are not writable
    by the configure process, so umask is relaxed to 022 and temp files
    are redirected to $TMPDIR (libkate 0.4.3 pattern).
  - E490: autotools helper script +x bits are restored after the
    vendored-file copy.
  - Generated-file timestamps are normalised (touched newer than
    Makefile.am/configure.ac) so make never tries to re-run aclocal/
    automake, which do not exist on the CI worker (babeltrace2 2.1.2 /
    E248 pattern).
  - Shared libraries and test executables are (re-)signed with
    binary-sign-tool; unsigned/SDK-self-signed ELFs can be rejected by
    XPM on HarmonyOS PC (flac 1.5.0 / libogg 1.3.6.2 pattern).

Upstream test suite (tests/, make check) is compiled and executed in
build(): 9 programs — noop, noop_theora, noop_theoraenc, comment,
comment_theoradec, comment_theora, granulepos, granulepos_theoraenc,
granulepos_theora (R51).
"""

import glob
import json
import os
import subprocess
import time

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import (
    Autotools,
    AutotoolsDeps,
    AutotoolsToolchain,
    PkgConfigDeps,
)
from conan.tools.layout import basic_layout


class LibtheoraConan(ConanFile):
    name = "libtheora"
    version = "1.2.0-alpha1"
    description = "Theora video codec library (free, patent-unencumbered, derived from On2 VP3)"
    license = "BSD-3-Clause"
    homepage = "https://xiph.org/theora/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    # Upstream tests/Makefile.am check_PROGRAMS (encode support enabled)
    _upstream_tests = [
        "noop", "noop_theora", "noop_theoraenc",
        "comment", "comment_theoradec", "comment_theora",
        "granulepos", "granulepos_theoraenc", "granulepos_theora",
    ]

    def config_options(self):
        if str(self.settings.os) == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)
        # Vendored autotools aux files (patches/autotools/config.*,
        # babeltrace2 2.1.2 in-repo precedent)
        copy(self, "patches/autotools/*",
             src=self.recipe_folder, dst=self.export_sources_folder)

    def requirements(self):
        # theora.h/theoradec.h/theoraenc.h include <ogg/ogg.h>
        self.requires("libogg/1.3.6.2",
                      transitive_headers=True, transitive_libs=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libtheora {self.version} only supports Linux and OHOS, "
                f"got os={self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        self._vendor_modern_config_scripts()
        self._patch_autoconf_hmdfs_tempdirs()
        self._normalize_generated_timestamps()

    # ------------------------------------------------------------------
    # source() helpers
    # ------------------------------------------------------------------
    def _vendor_modern_config_scripts(self):
        # E007: replace the 2003-era config.guess/config.sub with the
        # modern (2023-08-22, HarmonyOS-patched) pair vendored next to
        # this recipe. Files come from export_sources_folder when the
        # recipe runs from the conan cache.
        import shutil

        at_src = os.path.join(self.recipe_folder, "patches", "autotools")
        if not os.path.isdir(at_src):
            at_src = os.path.join(self.export_sources_folder,
                                  "patches", "autotools")
        if not os.path.isdir(at_src):
            raise ConanInvalidConfiguration(
                "vendored patches/autotools/ missing from recipe export")
        for name in ("config.guess", "config.sub"):
            src = os.path.join(at_src, name)
            dst = os.path.join(self.source_folder, name)
            shutil.copy2(src, dst)
            os.chmod(dst, 0o755)
        # E490: keep autotools helper scripts executable after the
        # source-tree copy dance (some paths drop the +x bit).
        for name in ("configure", "config.guess", "config.sub",
                     "install-sh", "missing", "compile", "depcomp"):
            f = os.path.join(self.source_folder, name)
            if os.path.isfile(f):
                os.chmod(f, 0o755)

    def _patch_autoconf_hmdfs_tempdirs(self):
        # E011 (libkate 0.4.3 pattern): umask 077 -> 022 and redirect
        # configure temp files to $TMPDIR so HMDFS permission quirks
        # cannot break config.status.
        configure_path = os.path.join(self.source_folder, "configure")
        if not os.path.isfile(configure_path):
            return
        with open(configure_path, "r", encoding="utf-8") as handle:
            content = handle.read()
        patched = content
        patched = patched.replace("umask 077", "umask 022")
        patched = patched.replace(
            'mktemp -d "./confXXXXXX"',
            'mktemp -d "${TMPDIR:-.}/confXXXXXX"')
        patched = patched.replace(
            "tmp=./conf$$-$RANDOM",
            "tmp=${TMPDIR:-.}/conf$$-$RANDOM")
        if patched != content:
            with open(configure_path, "w", encoding="utf-8",
                      newline="") as handle:
                handle.write(patched)
            self.output.info(
                "Patched configure Autoconf temp-dir creation for HMDFS")

    def _normalize_generated_timestamps(self):
        # E248 (babeltrace2 2.1.2 pattern): make must never consider
        # Makefile.am/configure.ac newer than the shipped Makefile.in/
        # configure, otherwise it re-runs aclocal/automake which are
        # absent on the CI worker (exit 127).
        new_ns = time.time_ns()
        patterns = ["configure", "aclocal.m4", "config.h.in",
                    "Makefile.in", "*/Makefile.in", "*/*/Makefile.in"]
        for pat in patterns:
            for f in glob.glob(os.path.join(self.source_folder, pat)):
                if os.path.isfile(f):
                    os.utime(f, ns=(new_ns, new_ns))

    # ------------------------------------------------------------------
    # build
    # ------------------------------------------------------------------
    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        # NOTE: deliberately NOT using --host/--build here. The vendored
        # 2023-era config.guess detects aarch64-unknown-linux-ohos
        # natively (validated end-to-end: configure + make + 9/9 tests).
        # Forcing cross mode makes configure's XIPH_PATH_VORBIS fallback
        # "assume OK" and enable vorbis-dependent examples, which then
        # fail on the missing vorbis/codec.h. In native mode the vorbis
        # pkg-config probe fails cleanly and those noinst examples are
        # simply skipped (upstream behaviour for missing optional deps).
        tc.generate()

    def build(self):
        apply_conandata_patches(self)  # patches: {} — no-op, keep pipeline
        self._inject_runtime_lib_path()
        old_umask = None
        if str(self.settings.os) == "OHOS":
            # E011: config.status re-opens its generated helper scripts
            # (conf*/subs1.awk); a restrictive umask breaks that on HMDFS.
            old_umask = os.umask(0o022)
        try:
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j4"])
            self._run_upstream_tests(autotools)
        finally:
            if old_umask is not None:
                os.umask(old_umask)

    def _inject_runtime_lib_path(self):
        # Native build with a shared conan dependency: AutotoolsDeps puts
        # -L<libogg>/lib -logg into the global LDFLAGS, so configure's
        # very first sanity conftest ("checking whether the C compiler
        # works") links libogg.so.0 — and fails to RUN unless the
        # loader can find it. Put every dependency libdir on
        # LD_LIBRARY_PATH for the whole build.
        extra = []
        for _, dep in self.dependencies.items():
            if not dep.package_folder:
                continue
            for libdir in dep.cpp_info.libdirs:
                extra.append(os.path.join(dep.package_folder, libdir))
        if extra:
            current = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = (
                os.pathsep.join(extra) +
                (os.pathsep + current if current else ""))
            self.output.info("build-time LD_LIBRARY_PATH: %s"
                             % os.environ["LD_LIBRARY_PATH"])

    # ------------------------------------------------------------------
    # upstream tests (R51)
    # ------------------------------------------------------------------
    def _sign_elf(self, path):
        # flac 1.5.0 / libogg 1.3.6.2 pattern: strip the linker
        # self-signature and re-sign with binary-sign-tool. Skipped
        # (with warning) where the tool is unavailable.
        objcopy = os.environ.get(
            "LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy")
        signer = os.environ.get(
            "BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool")
        if not (os.path.isfile(signer) and os.path.isfile(objcopy)):
            self.output.warning(
                "binary-sign-tool not found ({}); skipping ELF code "
                "signing".format(signer))
            return
        tmp = path + ".resigned"
        mode = os.stat(path).st_mode & 0o777
        subprocess.run([objcopy, "--remove-section", ".codesign", path],
                       check=False, timeout=60,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run([signer, "sign", "-inFile", path, "-outFile", tmp,
                        "-selfSign", "1"], check=True, timeout=60)
        # binary-sign-tool drops the executable bit on its output; restore
        # it before/after the move (E046: HMDFS chmod may be refused —
        # try both sides of the rename, never fail the build on it).
        for target in (tmp, path):
            try:
                os.chmod(target, mode | 0o111)
            except OSError:
                pass
        # HMDFS: rename-over-existing can fail with EACCES (E018 family);
        # remove the target first, then move the signed file into place.
        try:
            os.replace(tmp, path)
        except PermissionError:
            os.remove(path)
            os.replace(tmp, path)

    def _run_upstream_tests(self, autotools):
        # Compile the 9 upstream check programs, sign them (OHOS) and run
        # each one directly from the build tree with the conan libogg
        # runtime path. Equivalent to `make check` but with explicit
        # per-program exit codes as evidence.
        tests_dir = os.path.join(self.build_folder, "tests")
        lib_build_dir = os.path.join(self.build_folder, "lib", ".libs")
        try:
            autotools.make(args=["-C", "tests"] + self._upstream_tests)
        except Exception as exc:
            self._hmbs_emit_upstream({
                "status": "failed",
                "framework": "automake-check-programs",
                "command": "make -C tests <9 programs>",
                "discovered": len(self._upstream_tests),
                "executed": 0, "passed": 0, "failed": 0,
                "skipped": len(self._upstream_tests),
                "reason": f"test build failed: {exc}",
            })
            raise

        if not can_run(self):
            self._hmbs_emit_upstream({
                "status": "skipped",
                "framework": "automake-check-programs",
                "command": " && ".join(self._upstream_tests),
                "discovered": len(self._upstream_tests),
                "executed": 0, "passed": 0, "failed": 0,
                "skipped": len(self._upstream_tests),
                "reason": "cross-building: test binaries cannot run on host",
            })
            return

        ogg = self.dependencies["libogg"]
        ogg_libdir = os.path.join(ogg.package_folder,
                                  ogg.cpp_info.libdirs[0])
        ld_path = os.pathsep.join([lib_build_dir, ogg_libdir])
        commands, passed, failed = [], 0, 0
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = ld_path + os.pathsep + env.get(
            "LD_LIBRARY_PATH", "")
        for name in self._upstream_tests:
            exe = os.path.join(tests_dir, ".libs", name)
            if not os.path.isfile(exe):
                self._hmbs_emit_upstream({
                    "status": "failed",
                    "framework": "automake-check-programs",
                    "command": " && ".join(commands),
                    "discovered": len(self._upstream_tests),
                    "executed": passed + failed,
                    "passed": passed, "failed": failed + 1,
                    "skipped": 0,
                    "reason": f"test binary not built: {name}",
                })
                raise ConanException(
                    f"upstream test binary missing: {exe}")
            if str(self.settings.os) == "OHOS":
                self._sign_elf(exe)
            commands.append(exe)
            proc = subprocess.run(
                [exe], cwd=tests_dir, env=env, timeout=120,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            self.output.info("--- %s (rc=%s) ---\n%s" % (
                name, proc.returncode, (proc.stdout or "")[-2000:]))
            if proc.returncode == 0:
                passed += 1
            else:
                failed += 1
        result = {
            "status": "passed" if failed == 0 else "failed",
            "framework": "automake-check-programs",
            "command": " && ".join(commands),
            "discovered": len(self._upstream_tests),
            "executed": len(self._upstream_tests),
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        self._hmbs_emit_upstream(result)
        if failed:
            raise ConanException(
                f"{failed}/{len(self._upstream_tests)} upstream tests failed")

    def _hmbs_emit_upstream(self, data):
        # libogg 1.3.6.2 pattern: dual-channel marker so the CI preflight
        # captures upstream-test evidence regardless of log routing.
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
            data, ensure_ascii=False)
        print(msg, flush=True)
        self.output.info(msg)

    # ------------------------------------------------------------------
    # package
    # ------------------------------------------------------------------
    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # libtool .la wrappers embed absolute build-machine paths; drop
        # them (a52dec 0.7.4 in-repo precedent).
        for la in glob.glob(os.path.join(self.package_folder, "lib",
                                         "*.la")):
            os.remove(la)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        if self.options.shared and str(self.settings.os) == "OHOS":
            self._sign_package_libs()

    def _sign_package_libs(self):
        # flac 1.5.0 pattern: re-sign packaged shared libraries (real
        # files only; versioned symlinks are skipped).
        targets = []
        for f in sorted(glob.glob(
                os.path.join(self.package_folder, "lib", "libtheora*.so*"))):
            if os.path.isfile(f) and not os.path.islink(f):
                targets.append(f)
        for f in targets:
            self._sign_elf(f)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "theora")
        self.cpp_info.set_property("pkg_config_name", "theora")

        dec = self.cpp_info.components["theoradec"]
        dec.libs = ["theoradec"]
        dec.set_property("cmake_target_name", "theora::theoradec")
        dec.set_property("pkg_config_name", "theoradec")
        dec.requires = ["libogg::libogg"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            dec.system_libs = ["m"]

        enc = self.cpp_info.components["theoraenc"]
        enc.libs = ["theoraenc"]
        enc.set_property("cmake_target_name", "theora::theoraenc")
        enc.set_property("pkg_config_name", "theoraenc")
        # upstream theoraenc.pc: Requires: theoradec, ogg >= 1.1
        enc.requires = ["theoradec", "libogg::libogg"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            enc.system_libs = ["m"]

        full = self.cpp_info.components["theora"]
        full.libs = ["theora"]
        full.set_property("cmake_target_name", "theora::theora")
        full.set_property("pkg_config_name", "theora")
        full.requires = ["libogg::libogg"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            full.system_libs = ["m"]
