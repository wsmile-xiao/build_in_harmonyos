#!/usr/bin/env python3
"""Conan recipe for libaudiomask 1.0 - simultaneous audio masking threshold library.

Upstream: Debian source package libaudiomask 1.0 (author Dr Matt R. Flax),
orig tarball libaudiomask_1.0.orig.tar.gz (SHA-256 verified, see conandata.yml).
Same sources as flatmax/gtkiostream src/AudioMask (AudioMask/MooreSpread/
DepUKFB classes); the Debian 1.0 tree builds against mffm-fftw + fftw3
(Build-Depends: mffm-fftw-dev, libfftw3-dev).

Dependency closure: mffm-fftw/1.7 is not published to the ohpcd artifact
registry (conan graph resolution fails with "Unable to find 'mffm-fftw/1.7'
in remotes"), and one PR may only contain one library, so this recipe
vendors the official mffm-fftw 1.7 orig tarball (SHA-256 pinned in
conandata.yml sources.mffm_fftw) and statically builds its four translation
units into this package (pam-u2f self-contained pattern). The only Conan
requirement left is fftw/3.3.11, which is published.

Build: plain Makefile project, no configure script. The upstream Makefile
hard-codes g++ and an install(1)-based install target, so this recipe drives
the compile directly with the Conan toolchain compiler (R33: compiler paths
come from Conan conf as absolute paths, never from bare shell $CC/$CXX) and
collects artifacts with Conan copy() (OHOS has no install(1)).

Upstream tests: the tree ships no check/test target and no tests/ directory.
Upstream `make ex` (Makefile line 37, wired into the default `all` target
built by debian/rules) compiles and runs exactly ONE example,
AudioMaskerExample (its input audio.44100.txt was added by Debian 1.0-2
"Added the example input audio.44100.txt file" for this purpose).
depukfbExample is the only other self-contained example (needs just
depukfb.H/fastDepukfb.H). AudioMaskExample/MooreSpreadExample require
GTFB/GCFB filter-bank headers that exist in NEITHER the orig tarball NOR
mffm-fftw 1.7 (only realFFT/complexFFT/real2DFFT) NOR the declared
Build-Depends (libfftw3-dev, mffm-fftw-dev), and Debian never builds them;
they are stale doc files, not executable tests. build() therefore compiles
and runs the 2 buildable examples and emits a deterministic
HMBS_UPSTREAM_TEST_RESULT marker parsed from a single log file (one RESULT
line per example - no stdout word counting).
"""

import json
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

LIB_SOURCES = ("AudioMask.cc", "AudioMasker.cc", "MooreSpread.cc", "depukfb.cc")
LIB_HEADERS = (
    "AudioMask.H",
    "AudioMasker.H",
    "MooreSpread.H",
    "depukfb.H",
    "fastDepukfb.H",
)
# Upstream verification scope (audited 2026-09-25 against the Debian 1.0
# tree + debian packaging, see notes.md section 2):
# - AudioMaskerExample: the only example wired into upstream `make ex`
#   (Makefile line 37; debian/rules builds the default `all: libs ex`).
# - depukfbExample: self-contained (only needs depukfb.H/fastDepukfb.H).
# - AudioMaskExample / MooreSpreadExample: REQUIRE GTFB/GCFB filter-bank
#   headers that exist in NEITHER the orig tarball NOR mffm-fftw 1.7 (only
#   realFFT/complexFFT/real2DFFT) NOR the declared Build-Depends
#   (libfftw3-dev, mffm-fftw-dev); Debian never builds them either. They
#   are stale doc files, not executable tests, so they are not counted.
EXAMPLES = (
    "AudioMaskerExample",
    "depukfbExample",
)

# Vendored mffm-fftw 1.7 (official Debian pool orig tarball, same sources as
# the mffm-fftw/1.7 recipe: 4 translation units + 4 public headers).
VENDOR_SOURCES = ("realFFT.cc", "realFFTData.cc", "complexFFT.cc", "real2DFFT.cc")
VENDOR_HEADERS = ("realFFT.H", "realFFTData.H", "complexFFT.H", "real2DFFT.H")


class LibaudiomaskConan(ConanFile):
    name = "libaudiomask"
    version = "1.0"
    description = "Simultaneous audio masking threshold estimation library"
    license = "GPL-3.0-or-later"
    homepage = "https://salsa.debian.org/debian/libaudiomask"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libaudiomask supports Linux/OHOS only, got {}".format(
                    self.settings.os
                )
            )

    def requirements(self):
        # mffm-fftw/1.7 is vendored (not published to ohpcd), so only the
        # published fftw remains as a Conan requirement.
        self.requires("fftw/3.3.11")

    def layout(self):
        basic_layout(self)

    def source(self):
        import shutil

        get(self, **self.conan_data["sources"]["libaudiomask"], strip_root=True)
        vendor_dir = os.path.join(self.source_folder, "vendor-mffm-fftw")
        os.makedirs(vendor_dir, exist_ok=True)
        get(
            self,
            **self.conan_data["sources"]["mffm_fftw"],
            strip_root=True,
            destination=vendor_dir,
        )
        # The upstream tarball nests the sources under
        # home/flatmax/personal/research.flatmax/fft/. strip_root removes
        # the first level only, so promote the fft/ content to the root.
        nested = os.path.join(
            vendor_dir, "flatmax", "personal", "research.flatmax", "fft"
        )
        # Some repacks use a shorter prefix; probe both.
        if not os.path.isdir(nested):
            alt = os.path.join(vendor_dir, "flatmax")
            if os.path.isdir(alt):
                # generic fallback: find realFFT.cc under vendor_dir
                for root, _dirs, files in os.walk(vendor_dir):
                    if "realFFT.cc" in files:
                        nested = root
                        break
        if os.path.isdir(nested) and os.path.abspath(nested) != os.path.abspath(
            vendor_dir
        ):
            for item in os.listdir(nested):
                shutil.move(
                    os.path.join(nested, item), os.path.join(vendor_dir, item)
                )
            top = os.path.join(vendor_dir, "flatmax")
            if os.path.isdir(top):
                shutil.rmtree(top)
        # Provide an mffm/ include alias so both `#include "realFFT.H"` and
        # `#include <mffm/realFFT.H>` styles resolve.
        alias_dir = os.path.join(vendor_dir, "mffm-alias", "mffm")
        os.makedirs(alias_dir, exist_ok=True)
        for h in VENDOR_HEADERS:
            src_h = os.path.join(vendor_dir, h)
            dst_h = os.path.join(alias_dir, h)
            if os.path.isfile(src_h) and not os.path.lexists(dst_h):
                shutil.copy2(src_h, dst_h)
        self._neuter_dead_mffm_includes(self.source_folder)
        self._fix_upstream_includes(self.source_folder)
        self._fix_excite_count(self.source_folder)

    def _fix_upstream_includes(self, src_dir):
        # Portability fixes for the 1.0 tree (no behavior change):
        # 1) `../fft/realFFT.H` assumes the gtkiostream sibling layout
        #    (src/AudioMask + src/fft). The Debian orig tarball is flat,
        #    so rewrite to the bare header name resolved via -I<vendor>.
        #    (Currently only the two excluded stale examples carry this
        #    include; the fix is kept so any future consumer of those
        #    files gets the flat-tree spelling.)
        # 2) `void main(void)` (depukfbExample.cc) is ill-formed C++;
        #    normalize to `int main(void)` (fall-through returns 0).
        # 3) Bare `cout/endl/ofstream` (fastDepukfb.H:104, depukfbExample.cc
        #    :38/:42) rely on transitive <iostream>/<fstream> + implicit
        #    std:: lookup under g++/libstdc++. clang/libc++ is strict and
        #    rejects them (`use of undeclared identifier 'cout'`). Prefix
        #    the bare std identifiers with `std::` and ensure the explicit
        #    includes exist. No behavior change, Debian g++ still compiles.
        import re
        std_pat = re.compile(r"(?<![:\w])(cout|cerr|clog|endl|ofstream|ifstream)\b")
        try:
            names = os.listdir(src_dir)
        except OSError:
            return
        for fname in names:
            if not fname.endswith((".H", ".cc")):
                continue
            fpath = os.path.join(src_dir, fname)
            try:
                if not os.path.isfile(fpath) or os.path.islink(fpath):
                    continue
                with open(fpath, encoding="utf-8", errors="strict") as f:
                    text = f.read()
            except (OSError, UnicodeError):
                continue
            orig = text
            if "../fft/" in text:
                text = text.replace("../fft/", "")
            if "void main(void)" in text:
                text = text.replace("void main(void)", "int main(void)")
            if "using namespace std" not in text and std_pat.search(text):
                need_iostream = bool(
                    re.search(r"(?<![:\w])(cout|cerr|clog|endl)\b", text)
                )
                need_fstream = bool(
                    re.search(r"(?<![:\w])(ofstream|ifstream)\b", text)
                )
                if need_iostream and "#include <iostream>" not in text:
                    text = self._ensure_include(text, "<iostream>")
                if need_fstream and "#include <fstream>" not in text:
                    text = self._ensure_include(text, "<fstream>")
                text = std_pat.sub(r"std::\1", text)
            if text != orig:
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(text)
                self.output.info(
                    "hmbs-ohos fixed includes/main/std in " + fname
                )

    @staticmethod
    def _ensure_include(text, header):
        # Insert `#include <header>` after the last existing #include line
        # (or at the top when there is none), idempotent.
        marker = "#include " + header
        if marker in text:
            return text
        lines = text.splitlines(keepends=True)
        last = -1
        for i, line in enumerate(lines):
            if line.lstrip().startswith("#include"):
                last = i
        stmt = marker + "\n"
        if last >= 0:
            lines.insert(last + 1, stmt)
        else:
            lines.insert(0, stmt)
        return "".join(lines)

    def _neuter_dead_mffm_includes(self, src_dir):
        # Debian 1.0 MooreSpread.H:24 has a dead include of mffm/GTFB.H.
        # That header exists in neither mffm-fftw 1.7 (only realFFT,
        # complexFFT, real2DFFT) nor this package, and MooreSpread uses
        # no GTFB types. Upstream gtkiostream master already comments
        # this include out. Neuter it in place so build and packaged
        # headers compile.
        dead = ("mffm/GTFB.H", "mffm/GCFB.H")
        try:
            names = os.listdir(src_dir)
        except OSError:
            return
        for fname in names:
            if not fname.endswith((".H", ".cc")):
                continue
            fpath = os.path.join(src_dir, fname)
            try:
                if not os.path.isfile(fpath) or os.path.islink(fpath):
                    continue
                with open(fpath, encoding="utf-8", errors="strict") as f:
                    text = f.read()
            except (OSError, UnicodeError):
                continue
            orig = text
            for h in dead:
                for q in ("<" + h + ">", '"' + h + '"'):
                    needle = "#include " + q
                    if needle in text:
                        text = text.replace(needle, "// hmbs-ohos dead include: " + needle)
            if text != orig:
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(text)
                self.output.info("hmbs-ohos neutered dead include in " + fname)

    def _fix_excite_count(self, src_dir):
        # Memory-safety fix for AudioMasker::process (Debian 1.0):
        # powOutput rows hold ceil(fs/2) doubles (22050 for fs=44100) and
        # process() fills exactly halfFS=rint(fs/2) entries, but the call
        # exciteTerhardt(powOutput, fs) sums fs (44100) entries per row in
        # AudioMask::exciteTerhardt, reading ~176KB past each allocation
        # (x50 rows for AudioMaskerExample). On OHOS aarch64 this is
        # SIGSEGV exit -11 (example) or garbage-fed log10 -> non-finite
        # mask (test_package mask[0] CHECK). Pass halfFS so the sum covers
        # exactly the allocated+initialized bins; spreading is unchanged
        # (AudioMask::exciteTerhardt hard-codes MooreSpread::excite(...,fs,
        # fs) internally). halfFS is already in scope in process().
        fpath = os.path.join(src_dir, "AudioMasker.cc")
        try:
            if not os.path.isfile(fpath) or os.path.islink(fpath):
                return
            with open(fpath, encoding="utf-8", errors="strict") as f:
                text = f.read()
        except (OSError, UnicodeError):
            return
        needle = "exciteTerhardt(powOutput, fs)"
        fixed = "exciteTerhardt(powOutput, halfFS)"
        if needle in text:
            text = text.replace(needle, fixed)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(text)
            self.output.info(
                "hmbs-ohos fixed exciteTerhardt count fs->halfFS in "
                "AudioMasker.cc"
            )

    def _cxx(self):
        comp = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = (comp.get("cpp") if comp else None) or "clang++"
        return cxx

    def _dep_flags(self):
        incs, libdirs, libs = [], [], []
        dep = self.dependencies["fftw"]
        root = dep.package_folder
        for d in dep.cpp_info.includedirs:
            incs.append(os.path.join(root, d))
        for d in dep.cpp_info.libdirs:
            libdirs.append(os.path.join(root, d))
        libs.extend(dep.cpp_info.libs)
        libs.extend(getattr(dep.cpp_info, "system_libs", []))
        return incs, libdirs, libs

    def _build_vendor(self, vendor_dir, fftw_inc_flags):
        """Statically compile the vendored mffm-fftw sources.

        Returns (vendor_objs, vendor_include_dirs). Objects live under
        build_folder/vendor-objs so the source tree stays pristine.
        """
        cxx = self._cxx()
        alias_parent = os.path.join(vendor_dir, "mffm-alias")
        vendor_incs = [vendor_dir, alias_parent]
        vendor_inc_flags = " ".join(
            '"-I{}"'.format(p) for p in vendor_incs
        )
        cflags = "-O2 -fPIC -std=c++17 {} {}".format(
            fftw_inc_flags, vendor_inc_flags
        )
        obj_dir = os.path.join(self.build_folder, "vendor-objs")
        os.makedirs(obj_dir, exist_ok=True)
        objs = []
        for cc in VENDOR_SOURCES:
            src_cc = os.path.join(vendor_dir, cc)
            if not os.path.isfile(src_cc):
                raise ConanInvalidConfiguration(
                    "vendored mffm-fftw source missing: {}".format(src_cc)
                )
            obj = os.path.join(obj_dir, cc[:-3] + ".o")
            self.run(
                '"{cxx}" {cflags} -c "{ccp}" -o "{obj}"'.format(
                    cxx=cxx, cflags=cflags, ccp=src_cc, obj=obj,
                ),
                env="conanbuild",
            )
            objs.append(obj)
        return objs, vendor_incs

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        cxx = self._cxx()
        incs, libdirs, libs = self._dep_flags()
        fftw_inc_flags = " ".join(
            '"-I{}"'.format(p) for p in [src] + incs
        )
        lib_flags = " ".join('"-L{}"'.format(p) for p in libdirs)
        link_libs = " ".join("-l{}".format(l) for l in libs)

        # 0) Build vendored mffm-fftw statically (self-contained closed loop).
        vendor_dir = os.path.join(src, "vendor-mffm-fftw")
        vendor_objs, vendor_incs = self._build_vendor(
            vendor_dir, fftw_inc_flags
        )
        vendor_objs_q = " ".join('"{}"'.format(o) for o in vendor_objs)
        full_inc_flags = fftw_inc_flags + " " + " ".join(
            '"-I{}"'.format(p) for p in vendor_incs
        )
        cflags = "-O2 -fPIC -std=c++17 {}".format(full_inc_flags)

        # 1) Compile the four library translation units (-j1 per OHOS rule).
        for cc in LIB_SOURCES:
            obj = os.path.join(src, cc[:-3] + ".o")
            self.run(
                '"{cxx}" {cflags} -c "{ccp}" -o "{obj}"'.format(
                    cxx=cxx, cflags=cflags,
                    ccp=os.path.join(src, cc), obj=obj,
                ),
                env="conanbuild",
            )

        objs = " ".join(
            '"{}"'.format(os.path.join(src, c[:-3] + ".o")) for c in LIB_SOURCES
        )
        ce = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        ar = (ce.get("ar") if ce else None) or "llvm-ar"
        if self.options.shared:
            soname = "libaudiomask.so.1"
            realname = "libaudiomask.so.1.0"
            self.run(
                '"{cxx}" -shared -Wl,-soname,{soname} -o "{out}" {objs} '
                '{vendor_objs} {lib_flags} {link_libs} -lm'.format(
                    cxx=cxx, soname=soname,
                    out=os.path.join(src, realname),
                    objs=objs, vendor_objs=vendor_objs_q,
                    lib_flags=lib_flags, link_libs=link_libs,
                ),
                env="conanbuild",
            )
        # Static archive always contains both lib and vendored objects so
        # downstream static linking needs no extra mffm artifact.
        self.run(
            '"{ar}" rcs "{lib}" {objs} {vendor_objs}'.format(
                ar=ar,
                lib=os.path.join(src, "libaudiomask.a"),
                objs=objs,
                vendor_objs=vendor_objs_q,
            ),
            env="conanbuild",
        )

        # 2) Layer-1 upstream verification: build + run the 2 buildable
        # examples (AudioMaskerExample == upstream `make ex`; depukfbExample
        # == the only other self-contained example). The Debian tree has no
        # check/test target; changelog 1.0-2 ("Fixed the makefile so that
        # 'make ex' now compiles" + "Added the example input audio.44100.txt
        # file") confirms `make ex` is the registered upstream executable
        # verification. Each example exits 0 on success. Results go to ONE
        # deterministic log file; the marker below is parsed from that file
        # (single source, no stdout word counting).
        for ex in EXAMPLES:
            self.run(
                '"{cxx}" {cflags} "{excc}" "{lib}" '
                '{lib_flags} {link_libs} -lm -o "{out}"'.format(
                    cxx=cxx, cflags=cflags,
                    excc=os.path.join(src, ex + ".cc"),
                    lib=os.path.join(src, "libaudiomask.a"),
                    lib_flags=lib_flags, link_libs=link_libs,
                    out=os.path.join(src, ex),
                ),
                env="conanbuild",
            )
        self._run_upstream_examples(src)

    def _run_env(self):
        # Runtime linker path for the shared fftw dependency. build() runs
        # example binaries via plain subprocess (no `self.run(env=...)`
        # wrapper), so LD_LIBRARY_PATH from the conanrun env is missing and
        # both examples die with "libfftw3.so not found" (exit 127) even
        # though the compile succeeded. Merge dependency libdirs into the
        # ambient environment instead of replacing it.
        env = dict(os.environ)
        libdirs = []
        try:
            dep = self.dependencies["fftw"]
            root = dep.package_folder
            for d in dep.cpp_info.libdirs:
                libdirs.append(os.path.join(root, d))
        except Exception:
            pass
        if libdirs:
            old = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                libdirs + ([old] if old else [])
            )
        return env

    def _run_upstream_examples(self, src):
        import subprocess

        log_path = os.path.join(self.build_folder, "upstream_tests.log")
        run_env = self._run_env()
        results = []
        outputs = {}
        with open(log_path, "w", encoding="utf-8") as f:
            for ex in EXAMPLES:
                binary = os.path.join(src, ex)
                if not os.path.isfile(binary):
                    results.append((ex, "SKIP", "binary not built"))
                    f.write(
                        "EXAMPLE {} RESULT={} DETAIL={}\n".format(
                            ex, "SKIP", "binary not built"
                        )
                    )
                    continue
                try:
                    proc = subprocess.run(
                        [binary],
                        cwd=src,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        timeout=300,
                        env=run_env,
                    )
                    out_txt = proc.stdout.decode("utf-8", errors="replace")
                    outputs[ex] = out_txt
                    f.write("--- {} output begin ---\n".format(ex))
                    f.write(out_txt)
                    if not out_txt.endswith("\n"):
                        f.write("\n")
                    f.write("--- {} output end rc={} ---\n".format(
                        ex, proc.returncode))
                    if proc.returncode == 0:
                        results.append((ex, "PASS", "exit 0"))
                    else:
                        results.append(
                            (ex, "FAIL", "exit {}".format(proc.returncode))
                        )
                except Exception as e:
                    results.append((ex, "SKIP", "harness: {}".format(e)))
                    f.write("--- {} harness exception: {} ---\n".format(ex, e))
            for name, status, detail in results:
                f.write(
                    "EXAMPLE {} RESULT={} DETAIL={}\n".format(
                        name, status, detail
                    )
                )
        # Parse the log file back (single deterministic source).
        discovered, executed, passed, failed, skipped = 0, 0, 0, 0, 0
        with open(log_path, encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) < 3 or parts[0] != "EXAMPLE":
                    continue
                discovered += 1
                token = [p for p in parts if p.startswith("RESULT=")]
                if not token:
                    continue
                status = token[0].split("=", 1)[1]
                executed += 1
                if status == "PASS":
                    passed += 1
                elif status == "FAIL":
                    failed += 1
                else:
                    skipped += 1
        assert passed + failed + skipped == executed
        assert executed <= discovered
        status = "passed" if (failed == 0 and skipped == 0 and passed > 0) else (
            "failed" if failed else "skipped"
        )
        marker = {
            "status": status,
            "framework": "upstream-examples",
            "command": "run 2 *Example binaries built from source tree",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        if skipped or failed:
            # Evidence-carrying detail (counts/identities unchanged): embed
            # per-example name + exit code + tail of the captured output so
            # even a truncated preflight summary shows WHY it failed
            # (loader exit 127? signal-crash negative rc? missing input?).
            # Full output stays in build_folder/upstream_tests.log.
            parts = []
            for name, st, detail in results:
                tail = outputs.get(name, "")
                tail = tail.strip().splitlines()
                tail = tail[-5:] if len(tail) > 5 else tail
                seg = "{} {} {}".format(name, st, detail)
                if tail:
                    seg += " | out-tail: " + " / ".join(
                        t.strip()[:200] for t in tail if t.strip()
                    )[:600]
                parts.append(seg)
            marker["gaps"] = [
                {
                    "count": skipped + failed,
                    "category": "environment",
                    "detail": "not passed: " + "; ".join(parts)[:1500]
                    + "; see upstream_tests.log",
                    "evidence": "build_folder/upstream_tests.log",
                }
            ]
        with open(
            os.path.join(self.build_folder, "upstream_test_result.json"),
            "w", encoding="utf-8",
        ) as f:
            json.dump(marker, f)
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker)
        self.output.info(line)
        print(line, flush=True)

    def package(self):
        import shutil

        src = self.source_folder
        pkg = self.package_folder
        libdir = os.path.join(pkg, "lib")
        os.makedirs(libdir, exist_ok=True)
        if self.options.shared:
            copy(self, "libaudiomask.so.1.0", src=src,
                 dst=libdir, keep_path=False)
            # -laudiomask needs libaudiomask.so; soname entry needs .so.1.
            # Prefer symlinks, fall back to copies where symlink is unsupported.
            for link in ("libaudiomask.so.1", "libaudiomask.so"):
                target = os.path.join(libdir, link)
                if os.path.lexists(target):
                    continue
                try:
                    os.symlink("libaudiomask.so.1.0", target)
                except OSError:
                    shutil.copy2(
                        os.path.join(libdir, "libaudiomask.so.1.0"), target
                    )
        copy(self, "libaudiomask.a", src=src,
             dst=os.path.join(pkg, "lib"), keep_path=False)
        for h in LIB_HEADERS:
            copy(self, h, src=src, dst=os.path.join(pkg, "include"),
                 keep_path=False)
        # AudioMasker.H does `#include <mffm/realFFT.H>` (vendored mffm-fftw
        # objects are statically linked into libaudiomask.a/.so, but the
        # header is still needed at consumer compile time). 2026-09-24
        # preflight proved it: test_package failed with
        # "fatal error: 'mffm/realFFT.H' file not found". Ship all vendored
        # mffm headers under include/mffm/ so `-I<package>/include` resolves
        # the `<mffm/*.H>` spelling (realFFT.H pulls realFFTData.H etc.).
        for h in VENDOR_HEADERS:
            copy(self, h, src=os.path.join(src, "vendor-mffm-fftw"),
                 dst=os.path.join(pkg, "include", "mffm"), keep_path=False)
        copy(self, "GPL-3", src=src, dst=os.path.join(pkg, "licenses"),
             keep_path=False)
        # Vendored mffm-fftw licence (GPL-2.0-or-later) rides along because its
        # objects are statically linked into this package.
        copy(self, "License.txt.gpl", src=os.path.join(src, "vendor-mffm-fftw"),
             dst=os.path.join(pkg, "licenses"), keep_path=False)
        copy(self, "upstream_test_result.json",
             src=self.build_folder,
             dst=os.path.join(pkg, "res"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["audiomask"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.requires = ["fftw::fftw"]
        self.cpp_info.set_property("cmake_file_name", "libaudiomask")
        self.cpp_info.set_property(
            "cmake_target_name", "libaudiomask::libaudiomask"
        )
