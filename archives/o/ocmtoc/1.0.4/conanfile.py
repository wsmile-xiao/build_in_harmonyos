from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.env import Environment
import json
import os
import re
import shutil
import subprocess


class OcmtocConan(ConanFile):
    name = "ocmtoc"
    version = "1.0.4"
    description = "Mach-O to PE/COFF converter (mtoc) used in Acidanthera UDK and EDK II"
    license = "APSL-2.0"
    homepage = "https://github.com/acidanthera/ocmtoc"
    url = "https://github.com/acidanthera/ocmtoc"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "portability/**"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _fix_reallocate_zero_size(self, src):
        # Portability fix for musl/glibc (no patch file: conan's
        # patch applicator is strict about hunk counts while git
        # tolerates offsets, so a patch file is fragile here).
        # macOS realloc(p, 0) returns non-NULL, which upstream
        # libstuff_test/allocate_test.c relies on via
        # check_nonnull("reallocate(p, 0)", p). On musl/glibc a zero
        # size realloc may free the input and return NULL, which the
        # wrapper below would mistake for exhaustion and abort via
        # system_fatal("virtual memory exhausted (realloc failed)").
        # Normalize size 0 to 1 so the wrapper keeps macOS-like
        # non-NULL semantics. The NULL-input path is untouched:
        # reallocate(NULL, 0) still returns NULL via allocate(0).
        # No platform macro is used.
        path = os.path.join(src, "libstuff", "allocate.c")
        with open(path, "r", encoding="utf-8", newline="") as f:
            text = f.read()
        if "OCMTOC_REALLOCATE_ZERO_SIZE_FIX" in text:
            return
        old = ("\tif(p == NULL)\n"
               "\t    return(allocate(size));\n"
               "\tif((p = realloc(p, size)) == NULL)")
        new = ("\tif(p == NULL)\n"
               "\t    return(allocate(size));\n"
               "\t/* OCMTOC_REALLOCATE_ZERO_SIZE_FIX: normalize size 0 to 1\n"
               "\t * so musl/glibc keep macOS-like non-NULL semantics. */\n"
               "\tif(size == 0)\n"
               "\t    size = 1;\n"
               "\tif((p = realloc(p, size)) == NULL)")
        if old not in text:
            raise Exception(
                "reallocate zero-size anchor not found in "
                "libstuff/allocate.c")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text.replace(old, new, 1))
        self.output.info("ocmtoc: applied reallocate zero-size fix")

    def _fix_arch_test_sigabrt_trap(self, src):
        # Portability fix for the UPSTREAM TEST harness (no assertion or
        # test count is changed; the 7 arch tests still run verbatim).
        # libstuff_test/arch_test.c:check_arch_values() deliberately
        # triggers abort() for unknown cputypes ("any"/"little"/"big",
        # via get_cpu_entry_from_cputype()->abort()) and traps it with
        # signal(SIGABRT)+setjmp/longjmp. That pattern is non-portable:
        # abort() blocks SIGABRT before raising it, and plain longjmp out
        # of the handler never restores the signal mask, so on musl/
        # glibc SIGABRT stays blocked (possibly pending) and a later
        # deliberate abort kills the runner with SIGABRT (rc=-6) while
        # all buffered harness output is lost. Rewrite the trap with
        # sigaction()+sigsetjmp(env,1)/siglongjmp(), which saves and
        # restores the mask, keeping the exact same expected-abort cases.
        path = os.path.join(src, "libstuff_test", "arch_test.c")
        with open(path, "r", encoding="utf-8", newline="") as f:
            text = f.read()
        if "OCMTOC_SIGABRT_TRAP_FIX" in text:
            return
        old1 = "jmp_buf env;"
        new1 = "sigjmp_buf env; /* OCMTOC_SIGABRT_TRAP_FIX */"
        old2 = ("static void sig_handler(int signo)\n"
                "{\n"
                "  longjmp(env, 1);\n"
                "}")
        new2 = ("static void sig_handler(int signo)\n"
                "{\n"
                "  siglongjmp(env, 1);\n"
                "}")
        old3 = ("  if (0 == setjmp(env)) {\n"
                "    \n"
                "    void (*ohandler)(int);\n"
                "    ohandler = signal(SIGABRT, sig_handler);\n"
                "    if (ohandler == SIG_ERR) {\n"
                '      test_printerr("internal error: cannot install SIGABRT handler");\n'
                "      test_abort();\n"
                "      return;\n"
                "    }")
        new3 = ("  if (0 == sigsetjmp(env, 1)) {\n"
                "\n"
                "    struct sigaction ocm_act = { 0 };\n"
                "    struct sigaction ocm_oact;\n"
                "    ocm_act.sa_handler = sig_handler;\n"
                "    sigemptyset(&ocm_act.sa_mask);\n"
                "    ocm_act.sa_flags = 0;\n"
                "    if (sigaction(SIGABRT, &ocm_act, &ocm_oact) != 0) {\n"
                '      test_printerr("internal error: cannot install SIGABRT handler");\n'
                "      test_abort();\n"
                "      return;\n"
                "    }")
        old4 = ("    if (signal(SIGABRT, ohandler) == SIG_ERR) {\n"
                '      test_printerr("internal error: cannot restore SIGABRT handler");\n'
                "      test_abort();\n"
                "      return;\n"
                "    }")
        new4 = ("    if (sigaction(SIGABRT, &ocm_oact, NULL) != 0) {\n"
                '      test_printerr("internal error: cannot restore SIGABRT handler");\n'
                "      test_abort();\n"
                "      return;\n"
                "    }")
        for i, old in enumerate((old1, old2, old3, old4), 1):
            if old not in text:
                raise Exception(
                    "arch_test.c SIGABRT-trap anchor %d not found" % i)
        text = text.replace(old1, new1, 1)
        text = text.replace(old2, new2, 1)
        text = text.replace(old3, new3, 1)
        text = text.replace(old4, new4, 1)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        self.output.info("ocmtoc: applied arch_test SIGABRT-trap fix")

    def _resolve_cc(self):
        # R33: prefer Conan conf, but never crash if the conf key is absent
        # (farm profiles may not define tools.build:compiler_executables;
        # direct ':c' subkey access raises ConanException on such profiles).
        # Safe pattern: read the dict conf first, then try the subkey in a
        # guarded block; fall back to $CC and PATH lookup.
        candidates = []
        try:
            exes = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict)
            if isinstance(exes, dict) and exes.get("c"):
                candidates.append(exes.get("c"))
        except Exception:
            pass
        try:
            v = self.conf.get("tools.build:compiler_executables:c",
                              default=None)
            if v and v not in candidates:
                candidates.append(v)
        except Exception:
            pass
        env_cc = os.environ.get("CC")
        if env_cc:
            candidates.append(env_cc)
        candidates += ["aarch64-linux-ohos-clang", "clang"]
        for cand in candidates:
            if not cand:
                continue
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
            found = shutil.which(cand)
            if found:
                return found
        # Last resort: bare clang so the real toolchain error surfaces
        # via PATH resolution at build time instead of a conf crash.
        return "clang"

    def generate(self):
        env = Environment()
        env.define("OCMTOC_CC", self._resolve_cc())
        env.vars(self).save_script("ocmtoc_cc")

    @property
    def _mtoc_sources(self):
        # Closure of translation units needed to build efitools/mtoc.c.
        # mtoc links only libstuff (Xcode target "mtoc": mtoc.c + libstuff.a).
        # libstuff/lto.c is intentionally excluded: ofile.c references lto_*
        # only under #ifdef LTO_SUPPORT, which we do not define (no libLTO on
        # OHOS); LLVM-bitcode inputs are therefore rejected as unknown files.
        # libstuff/writeout.c is likewise excluded: it implements the
        # archive writer (writeout/writeout_to_mem/reset_load_command_pointers
        # for ar/ranlib-style tools) which mtoc never calls (verified: zero
        # references in mtoc.c and in every other TU of this closure; the
        # single breakout.c mention is a comment). A static archive only
        # pulls objects resolving undefined symbols, so omitting its
        # compilation is link-equivalent to upstream while avoiding its
        # macOS-only throttle path (O_FSYNC, host_sched_info/HOST_SCHED_INFO)
        # that no header shim can satisfy (it needs kernel support, and the
        # file also lacks <limits.h> for its UINT_MAX uses).
        return [
            "efitools/mtoc.c",
            "libstuff/allocate.c",
            "libstuff/apple_version.c",
            "libstuff/arch.c",
            "libstuff/breakout.c",
            "libstuff/bytesex.c",
            "libstuff/checkout.c",
            "libstuff/coff_bytesex.c",
            "libstuff/crc32.c",
            "libstuff/diagnostics.c",
            "libstuff/errors.c",
            "libstuff/fatal_arch.c",
            "libstuff/fatals.c",
            "libstuff/get_arch_from_host.c",
            "libstuff/get_toc_byte_sex.c",
            "libstuff/ofile.c",
            "libstuff/ofile_error.c",
            "libstuff/ofile_get_word.c",
            "libstuff/print.c",
            "libstuff/reloc.c",
            "libstuff/rnd.c",
            "libstuff/set_arch_flag_name.c",
            "libstuff/swap_headers.c",
            "libstuff/write64.c",
            os.path.join("portability", "mach_compat.c"),
        ]

    @property
    def _libstuff_test_sources(self):
        # Upstream libstuff unit tests (libstuff_test/, custom test.h
        # harness, no Xcode dependency) whose object-under-test is linked
        # into the shipped mtoc binary. Registration counts audited from
        # upstream sources: allocate 4 + arch 7 + get_arch_from_host 1 +
        # rnd 2 + harness init 1 = 15 tests.
        return [
            "libstuff_test/libstuff_test.c",
            "libstuff_test/test.c",
            "libstuff_test/null_test.c",
            "libstuff_test/allocate_test.c",
            "libstuff_test/arch_test.c",
            "libstuff_test/get_arch_from_host_test.c",
            "libstuff_test/rnd_test.c",
        ]

    @property
    def _test_support_sources(self):
        # Test-runner-only support objects (never linked into mtoc).
        return [
            os.path.join("portability", "test_unbuffer.c"),
        ]

    def build(self):
        apply_conandata_patches(self)
        self._fix_reallocate_zero_size(self.source_folder)
        self._fix_arch_test_sigabrt_trap(self.source_folder)
        src = self.source_folder
        inc_port = os.path.join(src, "portability", "shim")
        inc_up = os.path.join(src, "include")
        inc_stuff = os.path.join(src, "include", "stuff")
        # Forced-include compat header (BSD declarations such as reallocf
        # that musl lacks). Applied to every TU via -include so upstream
        # sources need no patching and no system header is shadowed.
        compat_h = os.path.join(inc_port, "ocmtoc_compat.h")
        # Resolve the compiler to an absolute, executable path once and
        # invoke it directly (no $VAR shell expansion). Shell-form helpers
        # (test/grep/printf) are deliberately avoided below: on the
        # HarmonyOS farm PATH may resolve coreutils (e.g. mkdir) to
        # unsigned harmonybrew shims whose exec fails with
        # "Operation not permitted". Pure-Python build asserts keep the
        # recipe off that broken PATH surface entirely.
        cc = self._resolve_cc()
        self.output.info("ocmtoc: using C compiler: %s" % cc)
        objs = []
        build_dir = os.path.join(self.build_folder, "obj")
        os.makedirs(build_dir, exist_ok=True)
        for rel in self._mtoc_sources:
            obj = os.path.join(build_dir, rel.replace("/", "_").replace(".c", ".o"))
            self.run('"{cc}" -O2 -I"{port}" -I"{up}" -I"{stuff}" '
                     '-include "{compat_h}" '
                     '-DCURRENT_PROJECT_VERSION=\'"1.0.4"\' '
                     '-c "{s}" -o "{o}"'.format(
                         cc=cc, port=inc_port, up=inc_up, stuff=inc_stuff,
                         compat_h=compat_h,
                         s=os.path.join(src, rel), o=obj))
            objs.append('"%s"' % obj)
        mtoc = os.path.join(self.build_folder, "mtoc")
        self.run('"{cc}" -O2 -o "{out}" {objs}'.format(
            cc=cc, out=mtoc, objs=" ".join(objs)))
        # Build-time smoke checks (real execution of the just-built binary,
        # asserting on output content). Equivalent to the former shell
        # test/grep/printf pipeline but implemented with subprocess + Python
        # file I/O so no sh helper binaries (test/grep/printf/mkdir) are
        # resolved via the farm PATH:
        # 1) --version prints 1.0.4; 2) --fullversion prints upstream id;
        # 3) no-arg invocation must fail via usage(); 4) garbage input must
        # fail with an error diagnostic (exercises breakout/ofile/checkout
        # error paths including ofile_unmap).
        def _run(args):
            return subprocess.run(args, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True)
        p = _run([mtoc, "--version"])
        if p.returncode != 0 or p.stdout.strip() != "1.0.4":
            raise Exception("mtoc --version failed: rc=%d stdout=%r stderr=%r"
                            % (p.returncode, p.stdout, p.stderr))
        p = _run([mtoc, "--fullversion"])
        if p.returncode != 0 or "Acidanthera ocmtoc 1.0.4" not in p.stdout:
            raise Exception("mtoc --fullversion failed: rc=%d stdout=%r stderr=%r"
                            % (p.returncode, p.stdout, p.stderr))
        p = _run([mtoc])
        if p.returncode == 0:
            raise Exception("mtoc with no args must fail via usage()")
        bad_bin = os.path.join(self.build_folder, "bad.bin")
        bad_pe = os.path.join(self.build_folder, "bad.pe")
        with open(bad_bin, "wb") as f:
            f.write(b"not-a-macho")
        if os.path.exists(bad_pe):
            os.remove(bad_pe)
        p = _run([mtoc, bad_bin, bad_pe])
        if p.returncode == 0:
            raise Exception("mtoc accepted a garbage input file")
        if "error" not in (p.stderr or "").lower():
            raise Exception("mtoc garbage-input stderr lacks 'error': %r" % p.stderr)
        if os.path.exists(bad_pe):
            raise Exception("mtoc must not create output on failure")
        # ── Upstream tests: libstuff unit suite (real execution) ──
        # Upstream ships two test collections:
        # 1) tests/test-cases (103 cctools run-tests cases): every Makefile
        #    declares `# PLATFORM: MACOS`, and the shared
        #    tests/include/common.makefile funnels every tool through
        #    `xcrun` and Apple (internal) SDKs. Upstream CI
        #    (.github/workflows/main.yml) never runs run-tests at all
        #    (only `xcodebuild -scheme mtoc`), and zero cases target mtoc.
        #    Neither runnable on HarmonyOS nor applicable to this package.
        # 2) libstuff_test/ (portable C unit tests for libstuff, custom
        #    test.h harness, no Xcode dependency): run here the subset whose
        #    object-under-test is linked into the shipped mtoc binary
        #    (allocate/arch/get_arch_from_host/rnd + harness init).
        #    The remaining files (align/args/depinfo/guess_short_name/
        #    version_number/reset_load_command_pointers) cover modules
        #    outside the mtoc link closure (verified: absent from
        #    _mtoc_sources; reset_* additionally needs writeout.c, which
        #    is excluded for its macOS-kernel-only throttle path), so they
        #    cannot validate this deliverable.
        test_inc = os.path.join(src, "libstuff_test")
        test_obj_dir = os.path.join(self.build_folder, "test_obj")
        os.makedirs(test_obj_dir, exist_ok=True)
        test_objs = []
        for rel in self._libstuff_test_sources:
            obj = os.path.join(
                test_obj_dir, rel.replace("/", "_").replace(".c", ".o"))
            self.run('"{cc}" -O2 -I"{port}" -I"{up}" -I"{stuff}" '
                     '-I"{testd}" -include "{compat_h}" '
                     '-c "{s}" -o "{o}"'.format(
                         cc=cc, port=inc_port, up=inc_up, stuff=inc_stuff,
                         testd=test_inc, compat_h=compat_h,
                         s=os.path.join(src, rel), o=obj))
            test_objs.append('"%s"' % obj)
        # Test-runner-only support objects (unbuffered stdio so that a
        # signal-death still leaves every harness line visible). They are
        # linked into libstuff_test_runner only, never into mtoc.
        for rel in self._test_support_sources:
            obj = os.path.join(
                test_obj_dir, rel.replace("/", "_").replace(".c", ".o"))
            self.run('"{cc}" -O2 -I"{port}" -I"{up}" -I"{stuff}" '
                     '-I"{testd}" -include "{compat_h}" '
                     '-c "{s}" -o "{o}"'.format(
                         cc=cc, port=inc_port, up=inc_up, stuff=inc_stuff,
                         testd=test_inc, compat_h=compat_h,
                         s=os.path.join(src, rel), o=obj))
            test_objs.append('"%s"' % obj)
        # Link the test objects against the already-built libstuff objects
        # (the whole mtoc closure except mtoc.o itself, which owns main();
        # libstuff_test.c provides the test main). This also pulls in
        # portability/mach_compat.o, whose ocmtoc_reallocf implements the
        # reallocf() the harness (test.c) uses and musl lacks.
        lib_objs = [o for o in objs if "efitools_mtoc.o" not in o]
        # NOTE: the test binary must not be named libstuff_test: when
        # source_folder == build_folder (single-folder conan layout, as on
        # the farm where sources land directly in .../b/), that path is the
        # upstream libstuff_test/ source directory and the link fails with
        # "cannot open output file .../libstuff_test: Is a directory".
        test_exe = os.path.join(self.build_folder, "libstuff_test_runner")
        self.run('"{cc}" -O2 -o "{out}" {objs}'.format(
            cc=cc, out=test_exe, objs=" ".join(lib_objs + test_objs)))
        t = subprocess.run([test_exe], stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, text=True)
        self.output.info("upstream libstuff_test stdout:\n%s" % t.stdout)
        if t.stderr:
            self.output.warning(
                "upstream libstuff_test stderr:\n%s" % t.stderr)
        m = re.search(r"tests completed \((\d+)/(\d+) passing\)",
                      t.stdout or "")
        if not m:
            raise Exception(
                "libstuff_test output lacks the summary line: rc=%d "
                "stdout=%r stderr=%r" % (t.returncode, t.stdout, t.stderr))
        passing, total = int(m.group(1)), int(m.group(2))
        if total == 0:
            raise Exception("libstuff_test reports zero tests")
        upstream = {
            "status": ("passed" if (t.returncode == 0 and passing == total)
                       else "failed"),
            "framework": "libstuff-unit-tests",
            "command": "./libstuff_test_runner",
            "discovered": total,
            "executed": total,
            "passed": passing,
            "failed": total - passing,
            "skipped": 0,
            "reason": ("Upstream libstuff unit tests for the 4 libstuff "
                       "modules linked into shipped mtoc "
                       "(allocate/arch/get_arch_from_host/rnd) + harness "
                       "init. 103 cctools run-tests cases are "
                       "PLATFORM:MACOS only (xcrun/Apple SDK) and unwired "
                       "from upstream CI (xcodebuild -scheme mtoc only); "
                       "0 mtoc cases."),
        }
        marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream)
        # Dual channel (stdout + conan output) so the marker survives log
        # capture on either stream; numbers come from the real run above.
        print(marker)
        self.output.info(marker)
        with open(os.path.join(self.build_folder,
                               "upstream_test_result.json"),
                  "w", encoding="utf-8") as _f:
            json.dump(upstream, _f)
        if upstream["status"] != "passed":
            raise Exception(
                "upstream libstuff unit tests failed: %d/%d passing rc=%d"
                % (passing, total, t.returncode))

    def package(self):
        copy(self, "mtoc", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "mtoc.1", src=os.path.join(self.source_folder, "man"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        # Persist the upstream test result so test_package can re-emit
        # HMBS_UPSTREAM_TEST_RESULT on every preflight, including rounds
        # where conan skips build() on a cached binary ("Already
        # installed!") and the build-time marker never prints.
        result_path = os.path.join(self.build_folder,
                                   "upstream_test_result.json")
        if os.path.isfile(result_path):
            copy(self, "upstream_test_result.json", src=self.build_folder,
                 dst=os.path.join(self.package_folder, "res"))
        else:
            self.output.warning(
                "upstream_test_result.json not found in build folder; "
                "package will lack upstream evidence")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = []
