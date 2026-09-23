#!/usr/bin/env python3
"""Conan test_package for libjose 14.

Builds a small consumer program against the installed libjose package and
runs it. The program performs 8 real API checks (Base64 round-trip, oct JWK
generation, thumbprint, HS256 JWS sign/verify). Emits the
HMBS_TEST_PACKAGE_RESULT marker with the real assertion counts.
"""

import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class LibjoseTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    exports_sources = "CMakeLists.txt", "test_jose.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        # Round-7 route: symlink staging + absolute RUNPATH, no file copies,
        # no explicit loader. Rounds 4-6 all used shutil.copy2 staging
        # (exe-dir .so copies, then a loader copy) and failed with an
        # unchanged fingerprint: the staged loader died with
        # "Permission denied" (Error 126) while the bare run kept loading
        # the system stale libjose.so.0 (missing jose_* symbols). The true
        # machine reports chmod:0/hardlink:0/symlink:1, so a copied file can
        # never regain +x, and OHOS XPM rejects ELF files touched without a
        # resign (jansson precedent with binary-sign-tool). Copies are the
        # poison: the loader skips the invalid staged files and falls back
        # to the stale system library. This round therefore never copies an
        # ELF file: runtime libs are exposed via absolute RUNPATH pointing
        # at the intact package-cache files plus $ORIGIN symlinks (symlink
        # needs no chmod and keeps the target signature intact). No LD_* env
        # is used anywhere.
        lib_dirs = []
        for ref in ("libjose", "jansson", "openssl", "zlib"):
            lib_dir = self._dep_lib_dir(ref)
            if lib_dir and lib_dir not in lib_dirs:
                lib_dirs.append(lib_dir)
        rpath = ";".join(lib_dirs + ["$ORIGIN", "$ORIGIN/../lib"])
        cmake = CMake(self)
        cmake.configure(variables={
            "CMAKE_INSTALL_RPATH": rpath,
            "CMAKE_BUILD_WITH_INSTALL_RPATH": True,
            "TEST_RPATH_DIRS": ";".join(lib_dirs),
        })
        cmake.build()
        self._stage_shared_libs_symlink(lib_dirs)
        self._log_built_rpath()

    def _find_test_exe(self):
        # Absolute resolution of the just-built binary: the relative
        # bindirs path ("./test_jose") may not equal the binary produced
        # by this build; glob the build tree and take the newest.
        import glob

        cands = glob.glob(
            os.path.join(self.build_folder, "**", "test_jose"), recursive=True
        ) + glob.glob(
            os.path.join(self.build_folder, "**", "test_jose.exe"), recursive=True
        )
        files = [c for c in cands if os.path.isfile(c)]
        if not files:
            return None
        try:
            files.sort(key=lambda p: os.path.getmtime(p))
        except OSError:
            pass
        return os.path.abspath(files[-1])

    def _log_built_rpath(self):
        # One-line ground truth whether RPATH/RUNPATH landed in the real
        # binary (survives HMBS truncation).
        import subprocess

        exe = self._find_test_exe()
        if not exe:
            self.output.info("HMBS_DIAG_BUILT_EXE missing")
            return
        try:
            proc = subprocess.run(
                ["readelf", "-d", exe],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30,
            )
            out = proc.stdout.decode("utf-8", errors="replace")
        except Exception as exc:
            self.output.info("HMBS_DIAG_BUILT_RPATH EXC %r" % exc)
            return
        keep = []
        for line in out.splitlines():
            stripped = " ".join(line.split())
            if "RPATH" in stripped or "RUNPATH" in stripped or "NEEDED" in stripped:
                keep.append(stripped)
        self.output.info("HMBS_DIAG_BUILT_EXE=%s" % exe)
        self.output.info(
            "HMBS_DIAG_BUILT_DEPS %s" % (" | ".join(keep)[:400] if keep else "none")
        )

    def _dep_lib_dir(self, ref):
        try:
            lib_dir = os.path.join(
                self.dependencies[ref].package_folder, "lib"
            )
        except Exception:
            return None
        return lib_dir if os.path.isdir(lib_dir) else None

    def _stage_shared_libs_symlink(self, lib_dirs):
        # Expose runtime shared objects next to every built test_jose via
        # symlinks (never copies): symlink needs no chmod (chmod:0 on the
        # true machine) and keeps the cache target's signature intact, so
        # the OHOS loader accepts the file. Absolute RUNPATH (set in
        # build()) already points at the intact cache files; the $ORIGIN
        # symlinks are a second path for loaders that prefer exe-dir.
        # Writes go to the build dir (writable), never to /tmp.
        import glob

        exes = glob.glob(
            os.path.join(self.build_folder, "**", "test_jose"), recursive=True
        ) + glob.glob(
            os.path.join(self.build_folder, "**", "test_jose.exe"), recursive=True
        )
        exe_dirs = set()
        for exe in exes:
            if os.path.isfile(exe):
                exe_dirs.add(os.path.dirname(os.path.abspath(exe)))
        try:
            bindir = self.cpp.build.bindirs[0]
        except Exception:
            bindir = None
        if bindir and not os.path.isabs(bindir):
            cand = os.path.abspath(os.path.join(self.build_folder, bindir))
            if os.path.isdir(cand):
                exe_dirs.add(cand)
        if not exe_dirs:
            return
        for lib_dir in lib_dirs:
            try:
                names = os.listdir(lib_dir)
            except OSError:
                continue
            for name in names:
                if ".so" not in name:
                    continue
                if not (name.startswith("libjose") or name.startswith("libjansson")
                        or name.startswith("libcrypto") or name.startswith("libssl")
                        or name.startswith("libz")):
                    continue
                src = os.path.join(lib_dir, name)
                try:
                    if not os.path.isfile(src) and not os.path.islink(src):
                        continue
                except Exception:
                    continue
                for exe_dir in exe_dirs:
                    dst = os.path.join(exe_dir, name)
                    try:
                        if os.path.islink(dst) or os.path.isfile(dst):
                            try:
                                if os.path.realpath(dst) == os.path.realpath(src):
                                    continue
                            except Exception:
                                pass
                            try:
                                os.unlink(dst)
                            except OSError:
                                continue
                        os.symlink(src, dst)
                    except OSError as exc:
                        self.output.info(
                            "HMBS_DIAG_SYMLINK fail %s -> %s %r" % (dst, src, exc))
                    except Exception as exc:
                        self.output.info(
                            "HMBS_DIAG_SYMLINK fail %s -> %s %r" % (dst, src, exc))

    def _diagnose_loader(self, exe, lib_dirs):
        # Compact loader evidence (survives HMBS truncation): proves
        # whether RPATH was embedded and whether the .so files exist.
        import subprocess

        def _out(argv):
            try:
                p = subprocess.run(argv, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, timeout=30)
                return p.stdout.decode("utf-8", errors="replace")
            except Exception as exc:
                return "EXC %r" % exc

        self.output.info("HMBS_DIAG_EXE=%s" % exe)
        for lib_dir in lib_dirs:
            try:
                names = sorted(os.listdir(lib_dir))[:20]
            except OSError as exc:
                self.output.info("HMBS_DIAG_LSDIR %s EXC %r" % (lib_dir, exc))
                continue
            sos = [n for n in names if ".so" in n]
            self.output.info("HMBS_DIAG_LSDIR %s so=%s" % (lib_dir, ",".join(sos[:8])))
        exe_abs = exe if os.path.isabs(exe) else os.path.join(self.build_folder, exe)
        try:
            exe_dir = os.path.dirname(os.path.abspath(exe_abs))
            self.output.info("HMBS_DIAG_EXEDIR %s ls=%s"
                             % (exe_dir, ",".join(sorted(os.listdir(exe_dir))[:12])))
        except OSError as exc:
            self.output.info("HMBS_DIAG_EXEDIR EXC %r" % exc)
        for argv, tag in ((["readelf", "-d", exe_abs], "RUNPATH"),
                          (["file", exe_abs], "FILE")):
            out = _out(argv)
            keep = " ".join(out.split())[:300]
            self.output.info("HMBS_DIAG_%s %s" % (tag, keep))
        for lib_dir in lib_dirs:
            for base in ("libjose.so.0", "libjansson.so"):
                cand = os.path.join(lib_dir, base)
                if os.path.isfile(cand):
                    out = _out(["file", cand])
                    self.output.info("HMBS_DIAG_LIB %s %s"
                                     % (base, " ".join(out.split())[:160]))
                    break

    def test(self):
        # Round-7: single bare run by absolute path. The explicit-loader
        # fallback of rounds 5-6 is deleted: staging a loader copy can never
        # be executable with chmod:0 and without a resign, so it only
        # masked the real result with Error 126. The same 8-check binary
        # runs once with no LD_* env; failure re-raises so the gate keeps
        # authority (no skip, no stub).
        lib_dirs = []
        for ref in ("libjose", "jansson", "openssl", "zlib"):
            lib_dir = self._dep_lib_dir(ref)
            if lib_dir and lib_dir not in lib_dirs:
                lib_dirs.append(lib_dir)
        self._stage_shared_libs_symlink(lib_dirs)
        exe = self._find_test_exe()
        if not exe:
            exe = os.path.join(self.cpp.build.bindirs[0], "test_jose")
        self._diagnose_loader(exe, lib_dirs)
        exe_abs = exe if os.path.isabs(exe) else os.path.abspath(
            os.path.join(self.build_folder, exe))
        self.run('"{}"'.format(exe_abs))
        # test_jose.c contains 8 real API assertions (b64 x2, jwk gen/kty/thp,
        # HS256 gen, JWS sign/verify); exit 0 above means all 8 passed.
        marker = {
            "executed": True,
            "passed": True,
            "command": exe_abs,
            "discovered": 8,
            "passedCount": 8,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
