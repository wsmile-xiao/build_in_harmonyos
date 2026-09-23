#!/usr/bin/env python3
"""Conan recipe — libcitadel 917 (Autotools).

Citadel shared toolbox library with StrBuf, hash, MIME and
vCard/vNote helpers used by the Citadel server, clients and WebCit.
"""

import json
import os
import re
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibcitadelConan(ConanFile):
    name = "libcitadel"
    version = "917"
    description = "Common code shared across the Citadel system (server, clients, WebCit)"
    license = "GPL-3.0-only"
    homepage = "https://www.citadel.org/"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def build_requirements(self):
        # Upstream tests/ are CUnit programs (tests/run_tests.sh plus
        # *_test.c in the 917 tree). CUnit is needed only to build and
        # run them, never at runtime, so it stays a build requirement.
        # cunit/2.1-3 is already published in this repository
        # (archives/c/cunit/2.1-3): low-cost fill for the missing test
        # framework per the upstream-test policy.
        self.tool_requires("cunit/2.1-3")

    def layout(self):
        basic_layout(self)
        # In-source build (zzuf precedent): the Conan default
        # out-of-source "build-release" dir sits on HMDFS where the old
        # 917 configure loses its cwd ("working directory cannot be
        # determined" + cascading getcwd failures in preflight). Building
        # in the source tree avoids the fragile extra directory level.
        self.folders.build = "."

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libcitadel supports Linux and OHOS, not %s" % self.settings.os
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _configure_args(self):
        # Explicit --prefix=/: manual configure runs bypass the toolchain
        # arg plumbing, so pin the prefix here (cyrus-sasl-login
        # precedent); package() installs with DESTDIR=<package_folder>.
        args = ["--prefix=/"]
        if not self.options.shared:
            args.append("--disable-shared")
            args.append("--enable-static")
        else:
            args.append("--enable-shared")
            args.append("--disable-static")
        # 917-era config.sub predates the OHOS triplet; build and host as
        # generic aarch64 Linux so the old classifier accepts the tuple.
        # The active Conan compiler still targets OHOS (vo-amrwbenc precedent).
        if str(self.settings.os) == "OHOS":
            args.append("--build=aarch64-unknown-linux-gnu")
            args.append("--host=aarch64-unknown-linux-gnu")
        return args

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        for arg in self._configure_args():
            tc.configure_args.append(arg)
        tc.generate()

    def _writable_tmpdir(self, source_folder):
        # HMBS injects a task-private writable TMPDIR on the real machine
        # (/tmp is read-only erofs: E002). Prefer it; fall back to a dir
        # inside the source tree (cyrus-sasl-login precedent).
        for key in ("TMPDIR", "TMP", "TEMP"):
            candidate = os.environ.get(key)
            if candidate and os.path.isdir(candidate):
                return candidate
        tmpdir = os.path.join(source_folder, "tmp")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        return tmpdir

    def _fix_autoconf_umask_for_ohos(self, source_folder):
        # HMDFS + setgid: autoconf template `umask 077 && mktemp -d
        # "./confXXXXXX"` yields an owner-unwritable dir (E011). Rewrite to
        # umask 022 (same mktemp/mkdir flow, group/world-readable temp dirs,
        # safe on a single-user build machine; zzuf/daemonize precedent).
        configure = os.path.join(source_folder, "configure")
        try:
            with open(configure, "r", encoding="utf-8",
                      errors="surrogateescape") as handle:
                content = handle.read()
        except OSError:
            return
        if "umask 077" not in content:
            return
        content = content.replace("umask 077", "umask 022")
        with open(configure, "w", encoding="utf-8",
                   errors="surrogateescape") as handle:
            handle.write(content)

    def _fix_loff_t_for_musl(self, source_folder):
        # 917 lib/libcitadel.h uses glibc-only loff_t for
        # IOBuffer.TotalSentAlready/TotalReadAlready (lines 264-265).
        # OHOS/musl <sys/types.h> provides off_t but not loff_t, so
        # clang fails with "unknown type name 'loff_t'". Provide a
        # portable fallback: off_t is 64-bit on LP64 (aarch64), same
        # width as loff_t. Guarded by __GLIBC__ so glibc builds keep
        # the system definition with zero behaviour change.
        header = os.path.join(source_folder, "lib", "libcitadel.h")
        try:
            with open(header, "r", encoding="utf-8",
                      errors="surrogateescape") as handle:
                content = handle.read()
        except OSError:
            return
        if "loff_t" not in content:
            return
        if "LIBCITADEL_LOFF_T_FALLBACK" in content:
            return
        anchor = "#include <sys/types.h>"
        fallback = (
            "#include <sys/types.h>\n"
            "/* Portable loff_t fallback for musl/OHOS (conan recipe):\n"
            "   glibc provides loff_t; musl does not. off_t is 64-bit\n"
            "   on LP64 so it is a compatible width. */\n"
            "#if !defined(__GLIBC__) && !defined(LIBCITADEL_LOFF_T_FALLBACK)\n"
            "#define LIBCITADEL_LOFF_T_FALLBACK 1\n"
            "typedef off_t loff_t;\n"
            "#endif"
        )
        if anchor in content:
            content = content.replace(anchor, fallback, 1)
        else:
            # Anchor on the double-include guard; header always has it.
            guard = "#define LIBCITADEL_H"
            if guard in content:
                content = content.replace(
                    guard,
                    guard + "\n#include <sys/types.h>\n"
                    "/* Portable loff_t fallback for musl/OHOS (conan recipe). */\n"
                    "#if !defined(__GLIBC__) && "
                    "!defined(LIBCITADEL_LOFF_T_FALLBACK)\n"
                    "#define LIBCITADEL_LOFF_T_FALLBACK 1\n"
                    "typedef off_t loff_t;\n"
                    "#endif",
                    1,
                )
            else:
                return
        with open(header, "w", encoding="utf-8",
                   errors="surrogateescape") as handle:
            handle.write(content)

    def _fix_mime_null_fallback_for_ohos(self, source_folder):
        # OHOS ships no XDG mime database (/usr/share/mime) and no
        # /etc/mime.types. The 917 GuessMimeType/GuessMimeByFilename
        # fall through to xdg_mime_* helpers which return NULL when the
        # database is absent; the tests then printf("%s", NULL) and the
        # mime_xdg_lookup_test demos exit non-zero (all 21 -x runs plus
        # the ./mimeparser_test.c content run in preflight). Upstream
        # rolling already fixed this direction by never returning NULL
        # (hardcoded table + "application/octet-stream" fallback), so
        # mirror that here: wrap the two xdg fallbacks with a NULL check.
        # Idempotent via LIBCITADEL_MIME_NULL_FALLBACK; no-op when the
        # patterns are absent (e.g. already-fixed trees).
        path = os.path.join(source_folder, "lib", "mime_parser.c")
        try:
            with open(path, "r", encoding="utf-8",
                      errors="surrogateescape") as handle:
                content = handle.read()
        except OSError:
            return
        if "LIBCITADEL_MIME_NULL_FALLBACK" in content:
            return
        original = content
        old_data = "return (xdg_mime_get_mime_type_for_data(data, dlen));"
        new_data = (
            "/* OHOS adaptation (conan recipe): xdg database absent -> NULL; */\n"
            "\t/* never propagate NULL to printf(\"%s\"); upstream rolling */\n"
            "\t/* uses application/octet-stream the same way. */\n"
            "\t{ /* LIBCITADEL_MIME_NULL_FALLBACK */\n"
            "\t\tconst char *fallback_mime =\n"
            "\t\t\txdg_mime_get_mime_type_for_data(data, dlen);\n"
            "\t\treturn (fallback_mime != NULL) ? fallback_mime\n"
            "\t\t\t: \"application/octet-stream\";\n"
            "\t}"
        )
        if old_data in content:
            content = content.replace(old_data, new_data, 1)
        old_name = "return xdg_mime_get_mime_type_from_file_name(what);"
        new_name = (
            "{ /* LIBCITADEL_MIME_NULL_FALLBACK */\n"
            "\t\tconst char *fallback_mime =\n"
            "\t\t\txdg_mime_get_mime_type_from_file_name(what);\n"
            "\t\treturn (fallback_mime != NULL) ? fallback_mime\n"
            "\t\t\t: \"application/octet-stream\";\n"
            "\t}"
        )
        if old_name in content:
            content = content.replace(old_name, new_name, 1)
        if content == original:
            self.output.info(
                "libcitadel mime NULL-fallback: patterns absent, no-op")
            return
        with open(path, "w", encoding="utf-8",
                   errors="surrogateescape") as handle:
            handle.write(content)
        self.output.info(
            "libcitadel mime NULL-fallback applied to lib/mime_parser.c")

    def _fix_strbuf_strip_guard_for_ohos(self, source_folder):
        # StrBufStripAllBut (lib/stringbuf.c) truncates at the first '>'
        # then cuts left at the last '<', with no rb>=lb guard, while the
        # C-string stripallbut() (lib/tools.c) only strips when the first
        # rightboundary sits at/after the last leftboundary and otherwise
        # leaves the input unchanged. The CUnit stripallbut_test expects
        # both to agree (cases like "<><><>" stay unchanged), so the
        # StrBuf variant fails its asserts on every platform, OHOS
        # included (preflight: stripallbut_test rc=0 with failed asserts).
        # Mirror the C semantics here; pure logic alignment, no assert
        # weakened, no test skipped. Idempotent via STRIP_GUARD.
        path = os.path.join(source_folder, "lib", "stringbuf.c")
        try:
            with open(path, "r", encoding="utf-8",
                      errors="surrogateescape") as handle:
                content = handle.read()
        except OSError:
            return
        if "LIBCITADEL_STRIP_GUARD" in content:
            return
        old_body = (
            "\tpRight = strchr(Buf->buf, rightboundary);\n"
            "\tif (pRight != NULL) {\n"
            "\t\tStrBufCutAt(Buf, 0, pRight);\n"
            "\t}\n"
            "\n"
            "\tpLeft = strrchr(ChrPtr(Buf), leftboundary);\n"
            "\tif (pLeft != NULL) {\n"
            "\t\tStrBufCutLeft(Buf, pLeft - Buf->buf + 1);\n"
            "\t}\n"
        )
        new_body = (
            "\t/* OHOS/CUnit adaptation (conan recipe): mirror */\n"
            "\t/* stripallbut() C-string semantics; LIBCITADEL_STRIP_GUARD */\n"
            "\tpLeft = strrchr(Buf->buf, leftboundary);\n"
            "\tpRight = strchr(Buf->buf, rightboundary);\n"
            "\tif ((pLeft == NULL) || (pRight == NULL) || (pRight < pLeft)) {\n"
            "\t\treturn;\n"
            "\t}\n"
            "\tStrBufCutAt(Buf, 0, pRight);\n"
            "\tpLeft = strrchr(ChrPtr(Buf), leftboundary);\n"
            "\tif (pLeft != NULL) {\n"
            "\t\tStrBufCutLeft(Buf, pLeft - Buf->buf + 1);\n"
            "\t}\n"
        )
        if old_body not in content:
            self.output.info(
                "libcitadel StrBuf strip guard: pattern absent, no-op")
            return
        content = content.replace(old_body, new_body, 1)
        with open(path, "w", encoding="utf-8",
                   errors="surrogateescape") as handle:
            handle.write(content)
        self.output.info(
            "libcitadel StrBuf strip guard applied to lib/stringbuf.c")

    def _fix_getopt_char_for_arm(self, source_folder):
        # ARM/aarch64 ABI: plain `char` is unsigned, so
        # `char a; while ((a = getopt(...)) != EOF)` never observes EOF
        # (-1 truncates to 255) and spins forever. Upstream
        # tests/mime_xdg_lookup_type.c (built as mime_xdg_lookup_test) and
        # tests/mimeparser_test.c both declare the getopt result as `char a`,
        # which is why every mime_xdg_lookup_test run hung to the 60s timeout
        # (rc=124) on the OHOS aarch64 preflight regardless of arguments,
        # while the no-arg CUnit mains (no getopt) passed. x86 (signed char
        # by default) hides the bug. One-word fix per file: `char a;` ->
        # `int a;` (getopt returns int by contract). Also covers
        # stringbuf_IO_test.c / stringbuf_stream.c with the identical pattern
        # (built but omitted from the run plan); no test skipped, no assert
        # changed. Idempotent via regex no-match on repeat runs.
        candidates = (
            "mime_xdg_lookup_type.c",
            "mime_xdg_lookup_test.c",
            "mimeparser_test.c",
            "stringbuf_IO_test.c",
            "stringbuf_stream.c",
        )
        for name in candidates:
            path = os.path.join(source_folder, "tests", name)
            try:
                with open(path, "r", encoding="utf-8",
                          errors="surrogateescape") as handle:
                    content = handle.read()
            except OSError:
                continue
            if "getopt" not in content:
                continue
            updated = re.sub(
                r"(^|\n[ \t]*)char([ \t]+a[ \t]*;)",
                r"\1int\2",
                content,
            )
            if updated == content:
                continue
            with open(path, "w", encoding="utf-8",
                       errors="surrogateescape") as handle:
                handle.write(updated)
            self.output.info(
                "libcitadel getopt char->int applied to tests/%s" % name
            )

    def _mktemp_fallback_shim_for_ohos(self, tmpdir):
        # HMBS platform diagnosis [unsafe_local_mktemp]: a directory created
        # by mktemp on the current device filesystem cannot be written by
        # Autoconf afterwards. When HMBS injects
        # HMBS_AUTOCONF_MKTEMP_FALLBACK=1, shadow mktemp during the configure
        # step only so calls for "./conf*" fail and Autoconf falls back to
        # its `mkdir` path. All other mktemp calls delegate to the real
        # binary; TMPDIR itself stays writable (cyrus-sasl-login precedent).
        # No per-library invention: inactive without the HMBS signal.
        if os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK") != "1":
            return ""
        shim_dir = os.path.join(tmpdir, "hmbs-mktemp-shim")
        try:
            os.makedirs(shim_dir, exist_ok=True)
        except OSError:
            return ""
        shim = os.path.join(shim_dir, "mktemp")
        script = (
            "#!/system/bin/sh\n"
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
            with open(shim, "w", encoding="utf-8") as handle:
                handle.write(script)
            try:
                os.chmod(shim, 0o755)
            except OSError:
                pass
        except OSError:
            return ""
        return shim_dir

    def _build_cc_for_ohos(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={})
        if isinstance(executables, dict):
            return executables.get("c") or executables.get("cc") or "clang"
        return "clang"

    def _cunit_dirs(self):
        # Locate CUnit headers/libs from the build-context requirement
        # (tool_requires). Returns (include_dir, lib_dir); either may be
        # None when the layout is unexpected (caller fails honestly).
        dep = None
        try:
            dep = self.dependencies.build["cunit"]
        except Exception:
            try:
                dep = self.dependencies["cunit"]
            except Exception:
                return (None, None)
        try:
            pkg = dep.package_folder
            incs = list(dep.cpp_info.includedirs or [])
            libdirs = list(dep.cpp_info.libdirs or [])
        except Exception:
            return (None, None)
        if not pkg:
            return (None, None)
        inc_dir = None
        for d in incs:
            p = d if os.path.isabs(d) else os.path.join(pkg, d)
            if os.path.isdir(p):
                inc_dir = p
                break
        lib_dir = None
        for d in libdirs:
            p = d if os.path.isabs(d) else os.path.join(pkg, d)
            if os.path.isdir(p):
                lib_dir = p
                break
        return (inc_dir, lib_dir)

    def _makefile_has_target(self, makefile_path, target):
        try:
            with open(makefile_path, "r", encoding="utf-8",
                      errors="replace") as handle:
                for line in handle:
                    if re.match(r"^%s\s*:" % re.escape(target), line):
                        return True
        except OSError:
            pass
        return False

    def _parse_cunit_summary(self, output):
        # CUnit Basic "Run Summary" table, e.g.:
        #   Run Summary:    Type  Total    Ran Passed Failed Inactive
        #                 suites      2      2    n/a      0        0
        #                  tests     10     10     10      0        0
        #                asserts    123    123    123      0      n/a
        # Prefer the asserts row (finest honest unit); fall back to tests.
        m = re.search(r"^\s*asserts\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)",
                      output, re.M)
        if m:
            vals = [int(m.group(i)) for i in range(1, 5)]
            return (vals[0], vals[1], vals[2], vals[3])
        m = re.search(r"^\s*tests\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)",
                      output, re.M)
        if m:
            vals = [int(m.group(i)) for i in range(1, 5)]
            return (vals[0], vals[1], vals[2], vals[3])
        return None

    def _write_upstream_result_json(self, source_folder, result):
        # Persist the real upstream counts so test_package can re-emit
        # them on cache-hit runs where conan skips build() entirely
        # (binary reuse => no fresh marker). Numbers are the true
        # framework counts from this build run, not estimates.
        path = os.path.join(source_folder, "hmbs-upstream-result.json")
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(result, handle, ensure_ascii=False)
        except OSError as exc:
            self.output.warning(
                "could not persist upstream result: %s" % exc
            )

    def _build_upstream_tests_dir(self, source_folder, tmpdir):
        # The 917 top-level Makefile wires no `check` target (that is why a
        # bare `make check` exits rc=2 with "No rule to make target
        # 'check'"), so build the tests/ subdir explicitly via the Makefile
        # that configure generates from tests/Makefile.in.
        tests_dir = os.path.join(source_folder, "tests")
        tests_makefile = os.path.join(tests_dir, "Makefile")
        if not os.path.isfile(tests_makefile):
            raise ConanException(
                "libcitadel upstream tests/ has no generated Makefile: %s"
                % tests_makefile
            )
        inc_dir, lib_dir = self._cunit_dirs()
        self.output.info(
            "libcitadel upstream tests CUnit dirs: inc=%s lib=%s"
            % (inc_dir, lib_dir)
        )
        if inc_dir is None or lib_dir is None:
            raise ConanException(
                "libcitadel upstream tests need CUnit headers/libs but none "
                "were found (tool_requires cunit/2.1-3)"
            )
        # tests/Makefile.in hardcodes LDFLAGS="@LDFLAGS@ -dn"; OHOS clang
        # rejects a bare -dn, so drop exactly that token via a command-line
        # override (values are the already-substituted ones from configure).
        make_overrides = ""
        try:
            with open(tests_makefile, "r", encoding="utf-8",
                      errors="replace") as handle:
                for line in handle:
                    m = re.match(r"^LDFLAGS\s*=\s*(.*)$", line.rstrip("\n"))
                    if m:
                        tokens = m.group(1).split()
                        if "-dn" in tokens:
                            cleaned = " ".join(
                                t for t in tokens if t != "-dn"
                            )
                            make_overrides += " LDFLAGS=\"%s\"" % cleaned
                            self.output.info(
                                "libcitadel upstream tests: stripped '-dn' "
                                "from LDFLAGS (was: %s)" % m.group(1)
                            )
                        break
        except OSError:
            pass
        build_cc = self._build_cc_for_ohos()
        # Inject CUnit search paths via compiler env (C_INCLUDE_PATH /
        # LIBRARY_PATH), leaving configure's own CFLAGS/LDFLAGS/LIBS
        # untouched; TMPDIR stays on the HMBS writable dir (readonly /tmp).
        prefix = (
            "umask 022 && TMPDIR=\"%s\" TMP=\"%s\" TEMP=\"%s\" "
            % (tmpdir, tmpdir, tmpdir)
            + "C_INCLUDE_PATH=\"%s${C_INCLUDE_PATH:+:$C_INCLUDE_PATH}\" "
            % inc_dir
            + "CPLUS_INCLUDE_PATH=\"%s${CPLUS_INCLUDE_PATH:+:$CPLUS_INCLUDE_PATH}\" "
            % inc_dir
            + "LIBRARY_PATH=\"%s${LIBRARY_PATH:+:$LIBRARY_PATH}\" "
            % lib_dir
        )
        self.run(
            prefix + "make -j1 CC=\"%s\"%s" % (build_cc, make_overrides),
            cwd=tests_dir,
            env="conanbuild",
        )
        return tests_dir

    def _discover_upstream_test_binaries(self, tests_dir):
        # Built test programs are extensionless executables; sources,
        # scripts (*.sh), objects and logs all carry a suffix.
        found = []
        for name in sorted(os.listdir(tests_dir)):
            path = os.path.join(tests_dir, name)
            if not os.path.isfile(path):
                continue
            if "." in name:
                continue
            if name in ("Makefile", "config", "configure"):
                continue
            try:
                if os.access(path, os.X_OK):
                    found.append(path)
            except OSError:
                continue
        return found

    def _extract_mime_part_numbers(self, output):
        # Upstream run_tests.sh part loop:
        #   for j in `./mimeparser_test -p -d -f $i | grep part= |
        #     sed "s;part=.*|.*|\\([0-9\\.]*\\)|.*|.*|.*|.*|;\\1;"`
        # list_this_part() prints "part=<name>|<filename>|<partnum>|...".
        # The sed grabs the third field when it looks like [0-9.]*.
        parts = []
        for line in (output or "").splitlines():
            line = line.strip()
            if not line.startswith("part="):
                continue
            fields = line.split("|")
            if len(fields) >= 3:
                cand = fields[2].strip()
                if cand and re.match(r"^[0-9.]+$", cand) and cand not in parts:
                    parts.append(cand)
        return parts

    def _plan_upstream_test_runs(self, tests_dir, binaries):
        # Faithful mirror of upstream tests/run_tests.sh (default mode)
        # plus tests/Makefile.in TARGETS. Verified against
        # mingodad/citadel master libcitadel/tests/:
        #   run_tests.sh invokes wildfire_test, mime_xdg_lookup_test
        #   (two loops), hashlist_test, stringbuf_conversion_test
        #   (plain + piped -i), stringbuf_test, stripallbut_test and
        #   the mimeparser_test -f/-p/-p -d matrix with a -P part loop.
        # stringbuf_IO_test is commented out upstream (needs a manual
        # nc server); stringbuf_stream_test has a Makefile target but
        # is never invoked by run_tests.sh (stdin/stdout filter that
        # would block on interactive input). Both stay omitted with a
        # logged reason instead of a silent skip. mimeparser -P part
        # runs expand dynamically at execution time from each -p -d
        # output, exactly like the shell loop.
        # Runs are (label, argv, stdin_path|None) triples.
        by_name = {}
        for path in binaries:
            by_name[os.path.basename(path)] = path
        runs = []
        omitted = []
        if "stringbuf_IO_test" in by_name:
            omitted.append(
                ("stringbuf_IO_test", "not invoked by upstream "
                 "tests/run_tests.sh (needs manual nc server on "
                 "127.0.0.1:6666)")
            )
        for key in list(by_name):
            if "io_test" in key.lower() and key != "stringbuf_IO_test":
                omitted.append(
                    (key, "not invoked by upstream tests/run_tests.sh "
                     "(needs manual nc server on 127.0.0.1:6666)")
                )
        if "stringbuf_stream_test" in by_name:
            omitted.append(
                ("stringbuf_stream_test", "not invoked by upstream "
                 "tests/run_tests.sh (stdin/stdout filter, would block "
                 "without interactive input)")
            )
        # 1. No-arg mains, exactly as run_tests.sh lists them.
        for name in ("wildfire_test", "hashlist_test", "stringbuf_test",
                     "stripallbut_test", "stringbuf_conversion_test"):
            if name in by_name:
                runs.append((name, [by_name[name]], None))
        # stringbuf_conversion_test piped variant:
        #   cat testdata/emailaddresses/email_recipientstrings.txt |
        #     ./stringbuf_conversion_test -i
        if "stringbuf_conversion_test" in by_name:
            mail_txt = os.path.join(
                tests_dir, "testdata", "emailaddresses",
                "email_recipientstrings.txt")
            if not os.path.isfile(mail_txt):
                mail_dir = os.path.join(tests_dir, "testdata",
                                        "emailaddresses")
                if os.path.isdir(mail_dir):
                    for fn in sorted(os.listdir(mail_dir)):
                        fp = os.path.join(mail_dir, fn)
                        if os.path.isfile(fp):
                            mail_txt = fp
                            break
            if os.path.isfile(mail_txt):
                rel = os.path.relpath(mail_txt, tests_dir)
                runs.append(
                    ("stringbuf_conversion_test -i < %s" % rel,
                     [by_name["stringbuf_conversion_test"], "-i"],
                     mail_txt)
                )
            else:
                omitted.append(
                    ("stringbuf_conversion_test -i (piped)",
                     "upstream testdata/emailaddresses input not present "
                     "in source tree")
                )
        # 2. mimeparser_test full matrix over the shipped tree.
        if "mimeparser_test" in by_name:
            mime_bin = by_name["mimeparser_test"]
            mime_data = os.path.join(tests_dir, "testdata", "mime")
            files = []
            if os.path.isdir(mime_data):
                for fn in sorted(os.listdir(mime_data)):
                    fp = os.path.join(mime_data, fn)
                    if os.path.isfile(fp):
                        files.append(fp)
            if not files:
                omitted.append(
                    ("mimeparser_test", "no files under testdata/mime "
                     "in source tree")
                )
            for fp in files:
                rel = os.path.relpath(fp, tests_dir)
                runs.append(
                    ("mimeparser_test -f %s" % rel,
                     [mime_bin, "-f", fp], None)
                )
                runs.append(
                    ("mimeparser_test -p -f %s" % rel,
                     [mime_bin, "-p", "-f", fp], None)
                )
                runs.append(
                    ("mimeparser_test -p -d -f %s" % rel,
                     [mime_bin, "-p", "-d", "-f", fp], None)
                )
                # -P part sub-runs expand at execution time.
        # 3. mime_xdg_lookup_test: mirror both run_tests.sh loops.
        # Loop 1: ../../webcit/static/* (sibling repo, absent from the
        # libcitadel tarball) plus ./mimeparser_test.c; each with and
        # without -x, always with -i /usr/share/icons/... Loop 2:
        # bare names (test.txt ...) with -x -i. By-extension (-x)
        # runs never open the file (GuessMimeByFilename only), so they
        # run even when the name is absent; content runs (-x absent)
        # open the file, so missing inputs become logged omissions
        # rather than false failures. A missing host IconDir drops the
        # -i flag with a logged adaptation (lookup still validates the
        # MIME guess path).
        if "mime_xdg_lookup_test" in by_name:
            xdg_bin = by_name["mime_xdg_lookup_test"]
            icon_dir = "/usr/share/icons/gnome/24x24/mimetypes"
            icon_ok = os.path.isdir(icon_dir)
            if not icon_ok:
                omitted.append(
                    ("mime_xdg_lookup_test -i %s" % icon_dir,
                     "host icon dir absent on OHOS; -x/-f runs execute "
                     "without -i (adaptation, still real lookup)")
                )
            loop1 = ["../../webcit/static/bgcolor.gif",
                     "../../webcit/static/resizecorner.png",
                     "../../webcit/static/roomops.js",
                     "./mimeparser_test.c"]
            loop2 = ["test.txt", "test.css", "test.htc", "test.jpg",
                     "test.png", "test.ico", "test.vcf", "test.html",
                     "test.htm", "test.wml", "test.wmls", "test.wmlc",
                     "test.wmlsc", "test.wbmp", "test.blarg", "a.1", "a"]
            for rel_name in loop1:
                abs_path = os.path.normpath(
                    os.path.join(tests_dir, rel_name))
                exists = os.path.isfile(abs_path)
                argv_x = [xdg_bin, "-f", abs_path, "-x"]
                if icon_ok:
                    argv_x += ["-i", icon_dir]
                runs.append(
                    ("mime_xdg_lookup_test -f %s -x%s" % (
                        rel_name, " -i icons" if icon_ok else ""),
                     argv_x, None)
                )
                if exists:
                    argv_f = [xdg_bin, "-f", abs_path]
                    if icon_ok:
                        argv_f += ["-i", icon_dir]
                    runs.append(
                        ("mime_xdg_lookup_test -f %s%s" % (
                            rel_name, " -i icons" if icon_ok else ""),
                         argv_f, None)
                    )
                else:
                    omitted.append(
                        ("mime_xdg_lookup_test -f %s (content)" % rel_name,
                         "upstream input absent from libcitadel source "
                         "package (sibling webcit tree)")
                    )
            for rel_name in loop2:
                argv_x = [xdg_bin, "-f", rel_name, "-x"]
                if icon_ok:
                    argv_x += ["-i", icon_dir]
                runs.append(
                    ("mime_xdg_lookup_test -f %s -x%s" % (
                        rel_name, " -i icons" if icon_ok else ""),
                     argv_x, None)
                )
        return (runs, omitted)

    def _run_upstream_tests_with_marker(self, source_folder, tmpdir):
        # Upstream official suite: the 917 tree ships tests/ but wires no
        # top-level `make check` target, so build tests/ explicitly and run
        # each test program for real under TMPDIR (never the read-only
        # /tmp), then dual-emit the HMBS_UPSTREAM_TEST_RESULT machine
        # marker (stdout + Conan output). Any genuine failure raises.
        log_lines = []
        top_makefile = os.path.join(source_folder, "Makefile")
        if os.path.isfile(top_makefile) and self._makefile_has_target(
                top_makefile, "check"):
            # Source trees that do wire `check` keep the classic path.
            log = os.path.join(source_folder, "hmbs-make-check.log")
            self.run(
                "umask 022 && TMPDIR=\"%s\" TMP=\"%s\" TEMP=\"%s\" "
                "make check -j1 > \"%s\" 2>&1; "
                "echo \"HMBS_MAKE_CHECK_RC=$?\" >> \"%s\""
                % (tmpdir, tmpdir, tmpdir, log, log),
                cwd=source_folder,
                env="conanbuild",
            )
            try:
                with open(log, "r", encoding="utf-8",
                          errors="replace") as handle:
                    output = handle.read()
            except OSError:
                output = ""
            self.output.info(output[-6000:])
            m = re.search(r"HMBS_MAKE_CHECK_RC=(\d+)", output)
            returncode = int(m.group(1)) if m else 1
            if returncode == 0:
                result = {
                    "status": "passed",
                    "framework": "autotools-make-check",
                    "command": "make check -j1",
                    "discovered": 1,
                    "executed": 1,
                    "passed": 1,
                    "failed": 0,
                    "skipped": 0,
                }
            else:
                result = {
                    "status": "failed",
                    "framework": "autotools-make-check",
                    "command": "make check -j1",
                    "discovered": 1,
                    "executed": 1,
                    "passed": 0,
                    "failed": 1,
                    "skipped": 0,
                    "reason": "make check exited rc=%s, see build log tail"
                    % returncode,
                }
            msg = ("HMBS_UPSTREAM_TEST_RESULT="
                   + json.dumps(result, ensure_ascii=False))
            self._write_upstream_result_json(source_folder, result)
            print(msg, flush=True)
            self.output.info(msg)
            if result["status"] != "passed":
                raise ConanException(
                    "libcitadel upstream make check failed: %s"
                    % json.dumps(result)
                )
            return
        # 917 path: no `check` target -> explicit tests/ build + runs.
        # On a cross host the OHOS binaries cannot execute here; building
        # them still proves they compile (barrier precedent: warn, no fake
        # marker). The native preflight machine runs them for real.
        if not can_run(self):
            self.output.warning(
                "cross-building: upstream tests built but not executed "
                "on this host"
            )
            return
        tests_dir = self._build_upstream_tests_dir(source_folder, tmpdir)
        binaries = self._discover_upstream_test_binaries(tests_dir)
        self.output.info(
            "libcitadel upstream test binaries: %s"
            % ([os.path.basename(p) for p in binaries] or ["<none>"])
        )
        if not binaries:
            raise ConanException(
                "libcitadel upstream tests/ built but no test binaries "
                "were produced in %s" % tests_dir
            )
        runs, omitted = self._plan_upstream_test_runs(tests_dir, binaries)
        for base, reason in omitted:
            self.output.info(
                "libcitadel upstream test omitted: %s (%s)" % (base, reason)
            )
            log_lines.append("OMITTED: %s (%s)\n" % (base, reason))
        _inc_dir, lib_dir = self._cunit_dirs()
        run_env = dict(os.environ)
        run_env["TMPDIR"] = run_env["TMP"] = run_env["TEMP"] = tmpdir
        if lib_dir:
            old_ld = run_env.get("LD_LIBRARY_PATH", "")
            run_env["LD_LIBRARY_PATH"] = (
                lib_dir + (os.pathsep + old_ld if old_ld else "")
            )
        discovered = executed = passed = failed = skipped = 0
        failed_runs = []

        def _execute_one(label, argv, stdin_path):
            # Returns (rc, out). stdin_path feeds a file as stdin
            # (conversion -i piped variant); /dev/null stdin otherwise
            # so filter-style binaries can never block on a terminal.
            # Per-test timeout is 60s (CUnit units finish in seconds):
            # a hung binary fails fast with rc=124 instead of holding
            # the whole preflight SSH session silent until the server
            # drops it ("Connection closed by remote host"). Timeouts
            # are tallied as failures, never as passes/skips.
            try:
                if stdin_path is not None:
                    with open(stdin_path, "rb") as handle:
                        proc = subprocess.run(
                            argv, cwd=tests_dir, env=run_env,
                            stdin=handle, capture_output=True,
                            text=True, timeout=60,
                        )
                else:
                    with open(os.devnull, "rb") as handle:
                        proc = subprocess.run(
                            argv, cwd=tests_dir, env=run_env,
                            stdin=handle, capture_output=True,
                            text=True, timeout=60,
                        )
                rc = proc.returncode
                out = (proc.stdout or "") + (proc.stderr or "")
            except subprocess.TimeoutExpired as exc:
                rc = 124
                part = ""
                try:
                    part = (exc.stdout or "") + (exc.stderr or "")
                except Exception:
                    part = ""
                out = part + "\n[TIMEOUT after 60s: %s]\n" % label
            except OSError as exc:
                rc = 127
                out = "failed to execute %s: %s\n" % (label, exc)
            return (rc, out)

        def _tally(label, rc, out):
            nonlocal discovered, executed, passed, failed, skipped
            log_lines.append("===== RUN: %s (rc=%s) =====\n" % (label, rc))
            log_lines.append(out if out.endswith("\n") else out + "\n")
            counts = self._parse_cunit_summary(out)
            if counts is None:
                if rc == 0:
                    discovered += 1
                    executed += 1
                    passed += 1
                else:
                    discovered += 1
                    executed += 1
                    failed += 1
                    failed_runs.append(label)
            else:
                total, ran, ok, bad = counts
                discovered += total
                executed += ran
                passed += ok
                failed += bad
                skipped += max(total - ran, 0)
                if rc != 0 or bad > 0:
                    failed_runs.append("%s (rc=%s)" % (label, rc))

        for item in runs:
            if len(item) == 3:
                label, argv, stdin_path = item
            else:
                label, argv = item
                stdin_path = None
            # Stream per-run progress (Conan output + stdout flush):
            # the loop previously buffered everything until the end, so
            # a long/silent test window looked like a dead SSH session
            # to the preflight server. Streaming is a keepalive only;
            # it changes no test semantics, counts, or pass criteria.
            start_msg = "libcitadel upstream test start: %s" % label
            self.output.info(start_msg)
            print(start_msg, flush=True)
            rc, out = _execute_one(label, argv, stdin_path)
            _tally(label, rc, out)
            tail_lines = (out or "").splitlines()[-8:]
            done_msg = ("libcitadel upstream test done: %s (rc=%s)"
                        % (label, rc))
            self.output.info(done_msg)
            print(done_msg, flush=True)
            if tail_lines:
                self.output.info("\n".join(tail_lines)[-2000:])
            # Upstream shell part loop: after each `-p -d` matrix run,
            # re-run with -P <part> for every discovered part number.
            # Only expands on success, mirroring `... | grep part= ...`.
            if (rc == 0 and "-p" in argv and "-d" in argv
                    and "-f" in argv
                    and "mimeparser" in os.path.basename(argv[0]).lower()):
                try:
                    base_bin = argv[0]
                    file_arg = argv[argv.index("-f") + 1]
                except (ValueError, IndexError):
                    base_bin = None
                    file_arg = None
                if base_bin is not None and file_arg is not None:
                    for part_no in self._extract_mime_part_numbers(out):
                        sub_label = ("%s -P %s" % (label, part_no))
                        sub_argv = [base_bin, "-p", "-d", "-f",
                                    file_arg, "-P", part_no]
                        sub_start = ("libcitadel upstream test start: %s"
                                     % sub_label)
                        self.output.info(sub_start)
                        print(sub_start, flush=True)
                        sub_rc, sub_out = _execute_one(
                            sub_label, sub_argv, None)
                        _tally(sub_label, sub_rc, sub_out)
                        sub_done = ("libcitadel upstream test done: %s (rc=%s)"
                                    % (sub_label, sub_rc))
                        self.output.info(sub_done)
                        print(sub_done, flush=True)
        log_path = os.path.join(source_folder, "hmbs-make-check.log")
        try:
            with open(log_path, "w", encoding="utf-8",
                      errors="replace") as handle:
                handle.writelines(log_lines)
        except OSError:
            pass
        tail = "".join(log_lines)[-6000:]
        if tail:
            self.output.info(tail)
        names = sorted({label.split()[0] for label, _argv, _stdin in runs})
        ok = (not failed_runs and failed == 0 and skipped == 0
              and discovered > 0 and passed == discovered
              and executed == discovered)
        result = {
            "status": "passed" if ok else "failed",
            "framework": "cunit",
            "command": "make -C tests && run %s" % ", ".join(names),
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        if omitted:
            result["omitted"] = ["%s: %s" % item for item in omitted]
        if not ok:
            result["reason"] = "failed runs: %s" % "; ".join(failed_runs[:10])
        msg = ("HMBS_UPSTREAM_TEST_RESULT="
               + json.dumps(result, ensure_ascii=False))
        self._write_upstream_result_json(source_folder, result)
        print(msg, flush=True)
        self.output.info(msg)
        if not ok:
            raise ConanException(
                "libcitadel upstream tests failed: %s" % json.dumps(result)
            )

    def build(self):
        apply_conandata_patches(self)
        source_folder = self.source_folder
        tmpdir = self._writable_tmpdir(source_folder)
        self._fix_autoconf_umask_for_ohos(source_folder)
        self._fix_loff_t_for_musl(source_folder)
        self._fix_mime_null_fallback_for_ohos(source_folder)
        self._fix_strbuf_strip_guard_for_ohos(source_folder)
        self._fix_getopt_char_for_arm(source_folder)
        mktemp_shim = self._mktemp_fallback_shim_for_ohos(tmpdir)
        build_cc = self._build_cc_for_ohos()
        configure = os.path.join(source_folder, "configure")
        if not os.path.isfile(configure):
            raise ConanInvalidConfiguration(
                "configure not found in source tree: %s" % configure
            )
        configure_args = " ".join(
            shlex.quote(arg) for arg in self._configure_args()
        )
        shell = os.environ.get("CONFIG_SHELL") or "/system/bin/sh"
        path_prefix = ("%s:" % mktemp_shim) if mktemp_shim else ""
        # In-source configure with writable TMPDIR (E002) under umask 022
        # (E011); PATH shim only when HMBS signals unsafe_local_mktemp.
        self.run(
            "umask 022 && TMPDIR=\"%s\" TMP=\"%s\" TEMP=\"%s\" "
            "CONFIG_SHELL=\"%s\" SHELL=\"%s\" "
            "CC_FOR_BUILD=\"%s\" CPP_FOR_BUILD=\"%s -E\" "
            "PATH=\"%s$PATH\" "
            "\"%s\" \"%s\" %s"
            % (tmpdir, tmpdir, tmpdir, shell, shell, build_cc, build_cc,
               path_prefix, shell, configure, configure_args),
            cwd=source_folder,
            env="conanbuild",
        )
        self.run(
            "umask 022 && TMPDIR=\"%s\" TMP=\"%s\" TEMP=\"%s\" make -j1"
            % (tmpdir, tmpdir, tmpdir),
            cwd=source_folder,
            env="conanbuild",
        )
        # Upstream suite: 917 ships tests/ but wires no top-level
        # `make check` target, so build tests/ explicitly (CUnit) and
        # run each test program for real.
        self._run_upstream_tests_with_marker(source_folder, tmpdir)

    def _ohos_install_caps_unsupported(self):
        # HMBS platform diagnosis: only the unsupported filesystem
        # sub-capabilities (hardlink/chmod) trigger the manual fallback.
        # Reads the HMBS-injected signals without reinventing probing.
        # Anything unknown or supported returns False so unrelated
        # install failures still raise instead of being masked.
        blob = os.environ.get("HMBS_PLATFORM_CAPABILITIES", "")
        if blob:
            try:
                caps = json.loads(blob)
                hardlink = caps.get("hardlink", 1)
                chmod = caps.get("chmod", 1)
                if int(hardlink) == 0 or int(chmod) == 0:
                    return True
            except Exception:
                pass
        for key in ("HMBS_CAP_HARDLINK", "HMBS_CAP_CHMOD"):
            val = os.environ.get(key, "").strip().lower()
            if val in ("0", "false", "no", "off"):
                return True
        return False

    def _ohos_manual_install(self):
        # Pure-Python fallback for `make install` under HMBS
        # hardlink/chmod caps (courier-unicode precedent): the HMBS
        # install shim can exit 0 without materializing the file and the
        # follow-up `chmod 644` then fails with "No such file or
        # directory" (this round: build + 112/112 upstream passed, only
        # install-lib step failed). Uses shutil/copy (no ln/chmod) to
        # place exactly what the 917 `make install` would place: the
        # libtool static archive, public lib/*.h headers and the
        # generated pkg-config file. Never fakes outputs: missing build
        # artefacts raise instead of producing an empty package.
        import glob
        import shutil

        pkg_lib = os.path.join(self.package_folder, "lib")
        pkg_inc = os.path.join(self.package_folder, "include")
        pkg_pc = os.path.join(pkg_lib, "pkgconfig")
        for folder in (pkg_lib, pkg_inc, pkg_pc):
            try:
                os.makedirs(folder, exist_ok=True)
            except OSError:
                pass
        # Static archive: prefer the libtool .libs output.
        candidates = []
        for folder in (self.source_folder,):
            if folder:
                candidates.append(os.path.join(
                    folder, ".libs", "libcitadel.a"))
                candidates.append(os.path.join(
                    folder, "libcitadel.a"))
                candidates.append(os.path.join(
                    folder, "lib", ".libs", "libcitadel.a"))
        found = ""
        for cand in candidates:
            if cand and os.path.isfile(cand):
                found = cand
                break
        if not found and self.source_folder:
            for hit in glob.glob(os.path.join(
                    self.source_folder, "**", "libcitadel.a"),
                    recursive=True):
                if os.path.isfile(hit) and ".libs" in hit.replace(
                        os.sep, "/"):
                    found = hit
                    break
            if not found:
                for hit in glob.glob(os.path.join(
                        self.source_folder, "**", "libcitadel.a"),
                        recursive=True):
                    if os.path.isfile(hit):
                        found = hit
                        break
        if not found:
            raise RuntimeError(
                "OHOS manual install: libcitadel.a not found under "
                "source tree; refusing to fake the package")
        shutil.copyfile(found, os.path.join(pkg_lib, "libcitadel.a"))
        self.output.info("OHOS manual install: lib from %s" % found)
        # Shared objects when options.shared=True: plain copies only
        # (hardlink cap is 0 on current runners).
        try:
            if self.options.shared and self.source_folder:
                for hit in glob.glob(os.path.join(
                        self.source_folder, "**",
                        "libcitadel.so*"), recursive=True):
                    if os.path.isfile(hit) and not os.path.islink(hit):
                        try:
                            shutil.copyfile(
                                hit,
                                os.path.join(pkg_lib,
                                             os.path.basename(hit)))
                        except OSError:
                            pass
        except Exception:
            pass
        # Public headers: 917 installs lib/libcitadel.h (plus sibling
        # lib/*.h helpers); copy every lib/*.h to include/.
        header_copied = 0
        lib_dir = os.path.join(self.source_folder, "lib")
        if os.path.isdir(lib_dir):
            for hit in glob.glob(os.path.join(lib_dir, "*.h")):
                try:
                    copy(self, os.path.basename(hit),
                         src=lib_dir, dst=pkg_inc, keep_path=False)
                    header_copied += 1
                except Exception:
                    pass
        if header_copied == 0:
            raise RuntimeError(
                "OHOS manual install: no lib/*.h headers found; "
                "refusing to fake the package")
        self.output.info(
            "OHOS manual install: %s headers" % header_copied)
        # Pkg-config metadata when the build generated one.
        for folder in (self.source_folder,):
            if not folder:
                continue
            for hit in glob.glob(os.path.join(folder, "**", "*.pc"),
                                 recursive=True):
                try:
                    copy(self, os.path.basename(hit),
                         src=os.path.dirname(hit), dst=pkg_pc,
                         keep_path=False)
                except Exception:
                    pass

    def package(self):
        tmpdir = self._writable_tmpdir(self.source_folder)
        # Pre-create destinations so a missing-dir cause is ruled out
        # before delegating to the standard install (courier-unicode
        # precedent for the same install -c + chmod 644 failure mode).
        try:
            os.makedirs(os.path.join(self.package_folder, "lib"),
                        exist_ok=True)
            os.makedirs(os.path.join(self.package_folder, "include"),
                        exist_ok=True)
        except OSError:
            pass
        try:
            self.run(
                "umask 022 && TMPDIR=\"%s\" TMP=\"%s\" TEMP=\"%s\" "
                "make install DESTDIR=\"%s\" -j1"
                % (tmpdir, tmpdir, tmpdir, self.package_folder),
                cwd=self.source_folder,
                env="conanbuild",
            )
        except Exception as exc:
            if not self._ohos_install_caps_unsupported():
                raise
            self.output.warning(
                "OHOS manual install fallback after make install "
                "failed under hardlink/chmod caps: %s" % exc)
            self._ohos_manual_install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        # Cache-hit resilience: persist the true build-time upstream
        # counts inside the package so test_package can re-emit them
        # when conan reuses the cached binary and skips build().
        upstream_json = os.path.join(
            self.source_folder, "hmbs-upstream-result.json"
        )
        if os.path.isfile(upstream_json):
            copy(
                self,
                "hmbs-upstream-result.json",
                src=self.source_folder,
                dst=os.path.join(
                    self.package_folder, "share", "libcitadel"
                ),
                keep_path=False,
            )
        # Static-only default: drop libtool archives so downstream can only
        # resolve libcitadel.a (shared artefacts would risk a system .so).
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            for name in os.listdir(libdir):
                if name.endswith(".la"):
                    try:
                        os.remove(os.path.join(libdir, name))
                    except OSError:
                        pass

    def package_info(self):
        self.cpp_info.libs = ["citadel"]
        self.cpp_info.requires = ["zlib::zlib"]
        self.cpp_info.set_property("cmake_file_name", "libcitadel")
        self.cpp_info.set_property("cmake_target_name", "libcitadel::libcitadel")
        self.cpp_info.set_property("pkg_config_name", "libcitadel")
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
