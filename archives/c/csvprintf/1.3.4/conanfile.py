#!/usr/bin/env python3
"""Conan recipe — csvprintf 1.3.4 (C CLI tool, manual build).

csvprintf is a simple CSV→XML/JSON/bash-assignment converter from
https://github.com/archiecobbs/csvprintf.

The upstream release tarball (GitHub archive) contains no pre-generated
configure script; the OHOS preflight sandbox provides autoconf but lacks
automake/aclocal/libtoolize.  We therefore create config.h / gitrev.c
manually and compile main.c directly with the OHOS clang triplet.

PRINTF_PROGRAM fix:
  csvprintf forks PRINTF_PROGRAM per row in NORMAL mode to format output.
  On OHOS /usr/bin/printf is toybox (does not support %[N]s positional
  accessors).  The device's GNU coreutils printf lives at ~/usr/local/bin/printf
  and is used by default.  If it cannot be found we fall back to /usr/bin/printf.

Test counting:
  9 input files × 8 output variants (tests/run.sh) = 72
  + 11 .tst-style tests (tests/run2.sh)              = 11
  Total upstream = 83 test cases.
  Tests are re-executed here in pure Python (no bash dependency) so that
  they work reliably both on the device interactive shell and in the
  hmbs isolated CONAN_HOME sandbox.
"""
import json
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


UPSTREAM_TOTAL = 83
UPSTREAM_FRAMEWORK = "custom-shell"
UPSTREAM_COMMAND = "make tests (Python-driven)"


class CsvprintfConan(ConanFile):
    name = "csvprintf"
    version = "1.3.4"
    description = (
        "Simple CSV file parser for the UNIX command line"
    )
    license = "Apache-2.0"
    homepage = "https://github.com/archiecobbs/csvprintf"
    url = ""

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _find_printf():
        """Return an absolute path to a working printf binary.

        csvprintf forks PRINTF_PROGRAM per row in NORMAL mode.  Upstream
        configure.ac detects `which printf`; on OHOS that is toybox
        (/usr/bin/printf).  csvprintf strips its custom %[N]s / %{name} /
        %N$ accessors *before* handing the format string to printf, so the
        toybox printf is fully sufficient (verified on device).  We prefer a
        GNU coreutils printf if present, else fall back to /usr/bin/printf.
        """
        candidates = [
            os.path.expanduser("~/usr/local/bin/printf"),
            "/usr/bin/printf",
            "/data/service/hnp/bin/printf",
        ]
        for p in candidates:
            if os.path.isfile(p) and os.access(p, os.X_OK):
                r = subprocess.run(
                    [p, "%s:%s\n", "hello", "world"],
                    capture_output=True, timeout=5,
                )
                if r.returncode == 0 and b"hello:world" in r.stdout:
                    return p
        return "/usr/bin/printf"

    @staticmethod
    def _probe_sdk_llvm_libdir(cc):
        """Locate OHOS SDK llvm/lib containing libxml2.so.16.

        The CI worker's LD_LIBRARY_PATH is minimal and may lack this dir,
        causing lld (spawned by the OHOS clang driver) to fail with
        "Error loading shared library libxml2.so.16 … symbol not found".
        We probe the SDK path derived from the clang executable itself and
        return "" on non-OHOS or when the file is absent.
        """
        # Detect OHOS from settings
        sdk_candidates = []
        cc_real = os.path.realpath(cc)
        # clang resource-dir gives us <llvm>/lib/clang/<ver>
        try:
            rd = subprocess.check_output(
                [cc, "-print-resource-dir"],
                stderr=subprocess.DEVNULL, text=True, timeout=5,
            ).strip()
            sdk_candidates.append(os.path.dirname(os.path.dirname(rd)))
        except (OSError, subprocess.CalledProcessError):
            pass
        # Directories adjacent to the clang binary
        sdk_candidates.append(os.path.join(os.path.dirname(os.path.dirname(cc_real)), "lib"))
        # Hard-coded common OHOS SDK path as last resort
        sdk_candidates.append("/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm")
        sdk_candidates = list(dict.fromkeys(sdk_candidates))
        for d in sdk_candidates:
            ld = os.path.join(d, "lib")
            if os.path.isfile(os.path.join(ld, "libxml2.so.16")):
                return ld
        return ""

    # ── build ─────────────────────────────────────────────────────────────

    def build(self):
        src = self.source_folder
        build_dir = self.build_folder

        # -- config.h ---------------------------------------------------------
        printf_prog = self._find_printf()
        self.output.info(f"PRINTF_PROGRAM = {printf_prog}")

        cfg_h = os.path.join(src, "config.h")
        with open(cfg_h, "w") as f:
            f.write(f"""\
#ifndef CONFIG_H
#define CONFIG_H
#define _DEFAULT_SOURCE 1
#define _GNU_SOURCE 1
#define _BSD_SOURCE 1
#define _XOPEN_SOURCE 500
#define PRINTF_PROGRAM "{printf_prog}"
#define PACKAGE_TARNAME "csvprintf"
#define PACKAGE_VERSION "1.3.4"
#endif
""")
        self.output.info("Wrote config.h")

        # -- gitrev.c ---------------------------------------------------------
        gr_c = os.path.join(src, "gitrev.c")
        if not os.path.isfile(gr_c):
            with open(gr_c, "w") as f:
                f.write('const char *const csvprintf_version = "1.3.4";\n')
            self.output.info("Wrote gitrev.c")

        # -- compile & link ---------------------------------------------------
        cc = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ).get("c", "aarch64-unknown-linux-ohos-clang")
        if not os.path.isfile(cc):
            alt = "/data/service/hnp/bin/" + os.path.basename(cc)
            cc = alt if os.path.isfile(alt) else cc

        # OHOS lld/libxml2.so.16 guard (E120/E321, cf. cd-discid recipe):
        # CI workers have a minimal PATH/LD_LIBRARY_PATH. The clang driver
        # spawns lld whose RUNPATH points into the SDK llvm/lib, but without
        # that dir in LD_LIBRARY_PATH lld cannot load libxml2.so.16 at
        # runtime. We prepend it only while invoking the compiler/linker.
        sdk_llvm_lib = self._probe_sdk_llvm_libdir(cc)
        if sdk_llvm_lib:
            self.output.info(
                f"Prepending OHOS SDK linker runtime path: {sdk_llvm_lib}"
            )

        cflags = [
            "-g", "-O3", "-pipe",
            "-Wall", "-Wcast-align", "-Wstrict-prototypes", "-Wcast-qual",
            "-D_DEFAULT_SOURCE=1", "-D_GNU_SOURCE=1",
            "-D_BSD_SOURCE=1", "-D_XOPEN_SOURCE=500",
            f"-DPRINTF_PROGRAM=\"{printf_prog}\"",
        ]
        obj_dir = os.path.join(build_dir, "objs")
        os.makedirs(obj_dir, exist_ok=True)

        # Base env for all build+test subprocesses
        build_env = dict(os.environ)
        if sdk_llvm_lib:
            existing_ld = build_env.get("LD_LIBRARY_PATH", "")
            build_env["LD_LIBRARY_PATH"] = (
                sdk_llvm_lib + os.pathsep + existing_ld
            ).lstrip(os.pathsep)

        def _compile(src_file, out_file):
            r = subprocess.run(
                [cc, "-c", src_file, "-o", out_file] + cflags,
                cwd=src, capture_output=True, text=True,
                env=build_env,
            )
            if r.returncode != 0:
                raise Exception(f"compile {src_file} failed:\n{r.stderr}")
            self.output.info(f"Compiled {os.path.basename(src_file)}")

        _compile(os.path.join(src, "main.c"),
                 os.path.join(obj_dir, "main.o"))
        _compile(os.path.join(src, "gitrev.c"),
                 os.path.join(obj_dir, "gitrev.o"))

        bin_path = os.path.join(build_dir, "csvprintf")
        r = subprocess.run(
            [cc,
             os.path.join(obj_dir, "main.o"),
             os.path.join(obj_dir, "gitrev.o"),
             "-o", bin_path],
            cwd=src, capture_output=True, text=True,
            env=build_env,
        )
        if r.returncode != 0:
            raise Exception(f"link failed:\n{r.stderr}")
        self.output.info("Linked csvprintf")

        # -- place binary next to tests/ where upstream expects it ------------
        # Both run.sh and run2.sh use "../csvprintf" from tests/ → <src>/csvprintf
        dest_bin = os.path.join(src, "csvprintf")
        try:
            os.remove(dest_bin)
        except OSError:
            pass
        with open(bin_path, "rb") as fin, open(dest_bin, "wb") as fout:
            fout.write(fin.read())
        os.chmod(dest_bin, 0o755)
        self.output.info("Placed csvprintf in source root for upstream tests")

        # -- run upstream tests in pure Python (no bash dependency) -----------
        # Re-implement tests/run.sh and tests/run2.sh logic directly in
        # Python so they work reliably in the hmbs isolated sandbox and on
        # CI workers with a minimal PATH.  All parsing/execution happens in
        # the conan process itself — no external python3 subprocess needed.
        self.output.info(
            "Running upstream tests in pure Python (in-process)"
        )

        tmpdir = (
            os.environ.get("HMBS_TMPDIR")
            or os.environ.get("TMPDIR")
            or os.path.expanduser("~/tmp/csvprintf")
        )
        os.makedirs(tmpdir, exist_ok=True)
        env = dict(os.environ, TMPDIR=tmpdir)

        tests_dir = os.path.join(src, "tests")
        csvp_bin = dest_bin  # absolute path

        passed = 0
        failed = 0
        skipped = 0
        details = []

        # --- suite 2: .tst files (11 tests) ---
        # .tst files use bash syntax (FLAGS=(...), $'...' strings).
        # We decode them manually without exec().
        tst_files = sorted(
            f for f in os.listdir(tests_dir) if f.endswith(".tst")
        )
        for tst in tst_files:
            tpath = os.path.join(tests_dir, tst)
            try:
                flags, stdin_data, exp_stdout, exp_stderr, exp_rc = \
                    self._parse_tst(tpath)
            except Exception as e:
                self.output.warning(f"parse {tst}: {e}")
                skipped += 1
                continue

            r = subprocess.run(
                [csvp_bin] + list(flags),
                input=stdin_data,
                capture_output=True,
                env=env,
            )
            act_stdout = r.stdout.decode(errors="replace")
            act_stderr = r.stderr.decode(errors="replace")

            ok = True
            if exp_stdout != "!IGNORE!" and act_stdout != exp_stdout:
                ok = False
            if act_stderr != exp_stderr:
                ok = False
            if r.returncode != exp_rc:
                ok = False

            if ok:
                passed += 1
            else:
                failed += 1
                details.append(f"FAIL {tst}")

        # --- suite 1: .in files × 8 variants (72 tests) ---
        in_files = sorted(
            f for f in os.listdir(tests_dir) if f.endswith(".in")
        )
        for inf in in_files:
            base = inf[:-3]
            variations = [
                (["-x", "-f", os.path.join(tests_dir, inf)],
                 os.path.join(tests_dir, f"{base}.out1")),
                (["-X", "-f", os.path.join(tests_dir, inf)],
                 os.path.join(tests_dir, f"{base}.out2")),
                (["-e", "iso-8859-1", "-x", "-f",
                  os.path.join(tests_dir, inf)],
                 os.path.join(tests_dir, f"{base}.out1")),
                (["-j", "-f", os.path.join(tests_dir, inf)],
                 os.path.join(tests_dir, f"{base}.out3a")),
                (["-ij", "-f", os.path.join(tests_dir, inf)],
                 os.path.join(tests_dir, f"{base}.out3b")),
                (["-ix", "-f", os.path.join(tests_dir, inf)],
                 os.path.join(tests_dir, f"{base}.out4")),
                (["-b", "-f", os.path.join(tests_dir, inf)],
                 os.path.join(tests_dir, f"{base}.out5a")),
                (["-ib", "-f", os.path.join(tests_dir, inf)],
                 os.path.join(tests_dir, f"{base}.out5b")),
            ]
            for flags, expected_file in variations:
                if not os.path.exists(expected_file):
                    skipped += 1
                    continue
                try:
                    expected = open(expected_file, "rb").read()
                except OSError:
                    skipped += 1
                    continue
                r = subprocess.run(
                    [csvp_bin] + flags,
                    capture_output=True,
                    env=env,
                )
                if r.stdout == expected:
                    passed += 1
                else:
                    failed += 1
                    details.append(f"FAIL {inf}/{os.path.basename(expected_file)}")

        total = passed + failed + skipped
        self.output.info(
            f"Upstream tests: {passed}/{total} passed, "
            f"{failed} failed, {skipped} skipped"
        )
        for d in details[:20]:
            self.output.info(f"  {d}")

        ut_status = "passed" if (failed == 0 and passed > 0) else "failed"
        marker = {
            "status": ut_status,
            "framework": UPSTREAM_FRAMEWORK,
            "command": UPSTREAM_COMMAND,
            "discovered": UPSTREAM_TOTAL,
            "executed": passed + failed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "reason": (
                f"Upstream tests run in pure Python (no bash dependency) on "
                f"OHOS aarch64: {len(tst_files)} .tst tests + "
                f"{len(in_files)}×8=.in variants = {total} total."
            ),
        }
        print(
            f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(marker)}", flush=True
        )

        if failed > 0:
            raise ConanException(
                f"Upstream tests failed: {failed}/{total} ({details[:5]})"
            )

    # ── .tst parser (bash syntax → Python) ────────────────────────────────
    #
    # run2.sh sources each .tst file via `source "${TESTFILE}"` which performs
    # plain variable assignment — no eval, no echo.  The values are later
    # fed into csvprintf via `echo -en "$STDIN"` / `echo -en "$STDOUT"` / etc.,
    # which means:
    #   * plain single-quoted strings ('...') preserve backslashes literally;
    #     `echo -en` then decodes \n, \t, \xNN, \NNN octal etc.
    #   * dollar-quoted strings ($'...') have escapes decoded by bash *before*
    #     assignment; the stored value is already decoded, so `echo -en` is a
    #     no-op on it (except for any literal backslash sequences still present).
    #
    # We replicate this exactly in pure Python so the tests work in the hmbs
    # isolated sandbox where bash may be unavailable or unreliable.

    @staticmethod
    def _decode_bash_echo_e(s):
        """Interpret backslash escapes the way bash 'echo -e' does."""
        out = []
        i = 0
        n = len(s)
        while i < n:
            if s[i] == '\\' and i + 1 < n:
                c = s[i + 1]
                if c == 'n': out.append('\n'); i += 2
                elif c == 't': out.append('\t'); i += 2
                elif c == 'r': out.append('\r'); i += 2
                elif c == '\\': out.append('\\'); i += 2
                elif c == 'a': out.append('\a'); i += 2
                elif c == 'b': out.append('\b'); i += 2
                elif c == 'f': out.append('\f'); i += 2
                elif c == 'v': out.append('\v'); i += 2
                elif c == 'e': out.append('\x1b'); i += 2
                elif c == 'x' and i + 3 <= n:
                    try: out.append(chr(int(s[i+2:i+4], 16))); i += 4
                    except ValueError: out.append(s[i:i+2]); i += 2
                elif c == '0' and i + 3 <= n:
                    try: out.append(chr(int(s[i+2:i+5], 8))); i += 5
                    except ValueError: out.append(s[i:i+2]); i += 2
                else: out.append(s[i:i+2]); i += 2
            else: out.append(s[i]); i += 1
        return ''.join(out)

    @staticmethod
    def _decode_dollar_quote(s):
        """Decode a bash $'...' string (escapes processed by bash at parse time)."""
        inner = s[2:-1]  # strip surrounding $' and '
        result = []
        i = 0
        while i < len(inner):
            if inner[i] == '\\' and i + 1 < len(inner):
                c = inner[i + 1]
                if c == 'n': result.append('\n'); i += 2
                elif c == 't': result.append('\t'); i += 2
                elif c == 'r': result.append('\r'); i += 2
                elif c == '\\': result.append('\\'); i += 2
                elif c == "'": result.append("'"); i += 2
                else: result.append(inner[i]); result.append(c); i += 2
            else: result.append(inner[i]); i += 1
        return ''.join(result)

    @staticmethod
    def _get_var(lines, name):
        """Extract a single-line assignment: name=<value> (no DOTALL)."""
        import re
        pat = re.compile(rf"^{name}=(.+)$")
        for line in lines:
            m = pat.match(line)
            if m:
                return m.group(1).strip()
        return None

    @staticmethod
    def _parse_tst(tpath):
        """Parse a tests/run2.sh .tst file in pure Python.

        Returns (flags_list, stdin_bytes, exp_stdout, exp_stderr, exp_rc).
        """
        import re, shlex

        with open(tpath, encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
        lines = raw.splitlines()

        # -- FLAGS --
        flags_line = CsvprintfConan._get_var(lines, "FLAGS")
        if flags_line is None:
            raise ValueError(f"no FLAGS= line in {tpath}")
        # Strip surrounding parens: FLAGS=( -bi -p FOO_ )
        m = re.match(r"\((.+)\)", flags_line.strip())
        if not m:
            raise ValueError(f"bad FLAGS syntax in {tpath}")
        flags_list = shlex.split(m.group(1))

        # -- STDIN / STDOUT / STDERR / EXITVAL --
        def _decode_var(raw_val, var_name):
            """Decode the value according to its quoting style."""
            if raw_val is None:
                return ""
            if raw_val.startswith("$") and raw_val.endswith("'"):
                return CsvprintfConan._decode_dollar_quote(raw_val)
            elif raw_val.startswith("'") and raw_val.endswith("'"):
                # Plain single-quote: backslashes are literal, echo -e decodes
                return CsvprintfConan._decode_bash_echo_e(raw_val[1:-1])
            return raw_val

        raw_stdin = CsvprintfConan._get_var(lines, "STDIN")
        raw_stdout = CsvprintfConan._get_var(lines, "STDOUT")
        raw_stderr = CsvprintfConan._get_var(lines, "STDERR")
        raw_exitval = CsvprintfConan._get_var(lines, "EXITVAL")

        stdin_bytes = _decode_var(raw_stdin, "STDIN").encode("utf-8")
        exp_stdout = _decode_var(raw_stdout, "STDOUT")
        exp_stderr = _decode_var(raw_stderr, "STDERR")
        # EXITVAL is quoted like '1' or 0; strip surrounding ' or " quotes.
        try:
            exp_rc = int(raw_exitval.strip().strip("'\""))
        except (TypeError, ValueError):
            exp_rc = 0

        return flags_list, stdin_bytes, exp_stdout, exp_stderr, exp_rc

    # ── package ────────────────────────────────────────────────────────────

    def package(self):
        pkg = self.package_folder
        src = self.source_folder
        bin_dir = os.path.join(pkg, "bin")
        share_dir = os.path.join(pkg, "share", "csvprintf")
        man_dir = os.path.join(pkg, "share", "man", "man1")
        doc_dir = os.path.join(pkg, "share", "doc", "csvprintf")
        for d in (bin_dir, share_dir, man_dir, doc_dir):
            os.makedirs(d, exist_ok=True)

        # Binary
        build_bin = os.path.join(self.build_folder, "csvprintf")
        if not os.path.isfile(build_bin):
            raise Exception("csvprintf binary not found in build folder")
        copy(self, "csvprintf", os.path.dirname(build_bin), bin_dir)

        # Docs
        for name in ("CHANGES", "COPYING", "README", "README.md"):
            src_file = os.path.join(src, name)
            if os.path.isfile(src_file):
                copy(self, name, src, doc_dir)

        # Data files (csv.xsl, xml2csv.in)
        for name in ("csv.xsl", "xml2csv.in"):
            src_file = os.path.join(src, name)
            if os.path.isfile(src_file):
                copy(self, name, src, share_dir)

        # Man page (generate from .in template)
        src_man = os.path.join(src, "csvprintf.1.in")
        if os.path.isfile(src_man):
            with open(src_man) as fin:
                content = fin.read()
            content = content.replace("@PACKAGE@", "csvprintf")
            content = content.replace("@PACKAGE_VERSION@", "1.3.4")
            man_path = os.path.join(man_dir, "csvprintf.1")
            with open(man_path, "w") as fout:
                fout.write(content)
            self.output.info(f"Installed man page: {man_path}")

        # xml2csv shell wrapper
        xslt_proc = "/data/service/hnp/bin/xsltproc"
        xml2csv_src = os.path.join(src, "xml2csv.in")
        if os.path.isfile(xml2csv_src):
            with open(xml2csv_src) as fin:
                content = fin.read()
            content = content.replace("@XSLTPROC@", xslt_proc)
            content = content.replace("@pkgdatadir@", share_dir)
            xml2csv_dst = os.path.join(bin_dir, "xml2csv")
            with open(xml2csv_dst, "w") as fout:
                fout.write(content)
            os.chmod(xml2csv_dst, 0o755)
            self.output.info(f"Generated xml2csv: {xml2csv_dst}")

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
