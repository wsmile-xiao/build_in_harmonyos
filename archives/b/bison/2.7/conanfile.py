import os
import re
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class BisonConan(ConanFile):
    name = "bison"
    version = "2.7"
    description = "GNU parser generator"
    homepage = "https://www.gnu.org/software/bison/"
    license = "GPL-3.0-or-later"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        build_aux = os.path.join(self.source_folder, "build-aux")
        for name in ("config.sub", "config.guess", "install-sh", "missing"):
            path = os.path.join(build_aux, name)
            if os.path.isfile(path):
                os.chmod(path, 0o755)

        config_sub = os.path.join(build_aux, "config.sub")
        text = open(config_sub, encoding="utf-8").read()
        # CI may fetch the GNU tarball through different mirrors whose
        # config.sub text has small whitespace/context differences.  Patch the
        # OHOS triplet by anchor tokens instead of requiring one exact local
        # copy; otherwise source() fails before configure can even run.
        changed = 0
        if "linux-ohos*" not in text:
            new_text = text.replace(
                "  kopensolaris*-gnu* | \\\n",
                "  linux-ohos* | \\\n"
                "  kopensolaris*-gnu* | \\\n",
                1,
            )
            if new_text == text:
                new_text = re.sub(
                    r"(^[ \t]*kopensolaris\*-[^|\n]*\|[ \t]*\\\n)",
                    "  linux-ohos* | \\\n" + r"\1",
                    text,
                    count=1,
                    flags=re.M,
                )
            if new_text != text:
                text = new_text
                changed += 1

        if "-linux-ohos*" not in text:
            new_text = text.replace(
                "              | -linux-newlib* | -linux-musl* | -linux-uclibc* \\\n",
                "              | -linux-ohos* \\\n"
                "              | -linux-newlib* | -linux-musl* | -linux-uclibc* \\\n",
                1,
            )
            if new_text == text:
                new_text = re.sub(
                    r"(^[ \t]*\| -linux-newlib\* \| -linux-musl\* \| -linux-uclibc\*.*\\\n)",
                    "              | -linux-ohos* \\\n" + r"\1",
                    text,
                    count=1,
                    flags=re.M,
                )
            if new_text != text:
                text = new_text
                changed += 1

        if "\t-linux-ohos*)" not in text:
            new_text = text.replace(
                "\t-linux-dietlibc)\n"
                "\t\tos=-linux-dietlibc\n"
                "\t\t;;\n",
                "\t-linux-dietlibc)\n"
                "\t\tos=-linux-dietlibc\n"
                "\t\t;;\n"
                "\t-linux-ohos*)\n"
                "\t\tos=-linux-ohos\n"
                "\t\t;;\n",
                1,
            )
            if new_text == text:
                new_text = text.replace(
                    "\t-linux-newlib*)\n"
                    "\t\tos=-linux-newlib\n"
                    "\t\t;;\n",
                    "\t-linux-newlib*)\n"
                    "\t\tos=-linux-newlib\n"
                    "\t\t;;\n"
                    "\t-linux-ohos*)\n"
                    "\t\tos=-linux-ohos\n"
                    "\t\t;;\n",
                    1,
                )
            if new_text != text:
                text = new_text
                changed += 1

        if "linux-ohos" not in text:
            raise ConanException("failed to patch bison config.sub for OHOS")
        self.output.info("bison: widened {} config.sub spot(s) with linux-ohos".format(changed))
        with open(config_sub, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            # Bison 2.7's grammar-analysis code predates modern Clang and
            # relies on aliasing-sensitive C idioms. Keep the OHOS binary
            # conservative while preserving the upstream test suite.
            tc.extra_cflags.extend(["-O0", "-fno-strict-aliasing"])
            tc.extra_cxxflags.extend(["-O0", "-fno-strict-aliasing"])
            tc.configure_args.extend([
                "--build=aarch64-linux-ohos",
                "--host=aarch64-linux-ohos",
                "--disable-nls",
            ])
            # Use --prefix=/usr so bison hard-codes /usr/share/bison as its
            # data directory. The actual files are installed under
            # package_folder via DESTDIR (see package()), giving:
            #   <package_folder>/usr/share/bison/...
            # At runtime the consumer sets BISON_PKGDATADIR to that path.
            # This avoids both the //share double-slash (from --prefix=/)
            # and the nested absolute path (from --prefix=package_folder).
            tc.configure_args.append("--prefix=/usr")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._patch_generated_testsuite_sed()
        self._patch_cxx_register_storage()
        autotools = Autotools(self)
        try:
            autotools.configure()
        except ConanException:
            self._report_config_log_tail()
            raise
        autotools.make(args=["-j1"])
        # Bison 2.7's testsuite calls the bare name `bison` from PATH
        # (no $BISON variable, no ../src/bison relative path). On OHOS,
        # bison 3.8.2 lives at /data/service/hnp/bin/bison and appears
        # first on PATH, so every test ran against 3.8.2 output instead
        # of 2.7. Fix: prepend build_folder/src to PATH so `bison`
        # resolves to the 2.7 binary we compiled.
        # Also point BISON_PKGDATADIR at the skeleton files installed
        # under package_folder so make check can open m4sugar/m4sugar.m4.
        src_dir = os.path.join(self.build_folder, "src")
        pkgdata = os.path.join(self.package_folder, "usr", "share", "bison")
        # CC/CXX must be explicit: bison's testsuite compiles the generated
        # .c files to verify correctness. On OHOS the conanbuild env sets
        # CC but the variable is not inherited by the testsuite subshell
        # unless we forward it explicitly. Without CC the shell interprets
        # "$CC -c ..." as "-c: inaccessible or not found" (exit 127).
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        clang = str(compilers.get("c", "clang"))
        clangxx = str(compilers.get("cpp", "clang++"))
        # CPPFLAGS must include -I<build>/lib so that bison-generated .c
        # files can find config.h (which lives in the build tree, not the
        # source tree). The testsuite's atlocal.in sets this via autoconf
        # substitution but that substitution is skipped in cross-compile
        # mode, leaving CPPFLAGS empty.
        lib_dir = os.path.join(self.build_folder, "lib")
        lib_inc = lib_dir
        # LIBS: link against bison's bundled gnulib (libbison.a) so
        # that rpl_malloc / rpl_printf / rpl_fprintf are resolved.
        # The testsuite links each generated parser with "$CC ... $LIBS", so
        # this must be set in the command environment. Conan 2.29 on the CI
        # runner does not support ConanFile.run(extra_env=...), so keep these
        # as POSIX inline assignments.
        check_env = {
            "BISON_PKGDATADIR": pkgdata,
            "CC": clang,
            "CXX": clangxx,
            "CPPFLAGS": "-I{}".format(lib_inc),
            "LIBS": "-L{} -lbison".format(lib_dir),
        }
        env_prefix = "PATH={}:$PATH ".format(shlex.quote(src_dir))
        env_prefix += " ".join(
            "{}={}".format(key, shlex.quote(value))
            for key, value in check_env.items()
        )
        check_rc = self.run(
            "{} make check -j1".format(env_prefix),
            env="conanbuild",
            ignore_errors=True,
        )
        if check_rc != 0:
            testsuite_log = os.path.join(self.build_folder, "tests", "testsuite.log")
            if os.path.isfile(testsuite_log):
                self._report_testsuite_failures(testsuite_log)
            raise ConanException("bison upstream make check failed")

    def _patch_generated_testsuite_sed(self):
        sets_at = os.path.join(self.source_folder, "tests", "sets.at")
        if os.path.isfile(sets_at):
            with open(sets_at, encoding="utf-8") as handle:
                text = handle.read()
            original = text
            text = text.replace(
                "AT_DATA([extract.sed],\n[[#n\n",
                "AT_DATA([extract.sed],\n"
                "[[# Extract only selected grammar-set sections.\n",
            )
            text = text.replace(
                "AT_CHECK([sed -f extract.sed $1], 0, [stdout])",
                "AT_CHECK([sed -n -f extract.sed $1], 0, [stdout])",
            )
            if text != original:
                with open(sets_at, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(text)
                self.output.info("bison: patched sets.at sed invocations")

        testsuite = os.path.join(self.source_folder, "tests", "testsuite")
        if not os.path.isfile(testsuite):
            return
        with open(testsuite, encoding="utf-8") as handle:
            text = handle.read()
        original = text
        text = text.replace(
            "cat >extract.sed <<'_ATEOF'\n#n\n",
            "cat >extract.sed <<'_ATEOF'\n"
            "# Extract only selected grammar-set sections.\n",
        )
        text = text.replace(
            "( $at_check_trace; sed -f extract.sed stderr\n",
            "( $at_check_trace; sed -n -f extract.sed stderr\n",
        )
        if text != original:
            with open(testsuite, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
            self.output.info("bison: patched generated testsuite sed invocations")

    def _patch_cxx_register_storage(self):
        patched = 0
        for root in {self.source_folder, self.build_folder}:
            scanner = os.path.join(root, "examples", "calc++", "calc++-scanner.cc")
            if not os.path.isfile(scanner):
                continue
            with open(scanner, encoding="utf-8") as handle:
                text = handle.read()
            new_text = re.sub(r"\bregister[ \t]+", "", text)
            if new_text != text:
                with open(scanner, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(new_text)
                patched += 1
        if patched:
            self.output.info("bison: removed obsolete C++ register storage from {} scanner file(s)".format(patched))

    def _report_config_log_tail(self):
        config_log = os.path.join(self.build_folder, "config.log")
        if not os.path.isfile(config_log):
            return
        self.output.error("===== bison config.log tail =====")
        with open(config_log, encoding="utf-8", errors="replace") as handle:
            lines = [line.rstrip() for line in handle.readlines()]
        for line in lines[-120:]:
            self.output.error(line)

    def _report_testsuite_failures(self, testsuite_log):
        with open(testsuite_log, encoding="utf-8", errors="replace") as handle:
            lines = handle.readlines()

        failed_groups = []
        capture_subject = False
        for line in lines:
            text = line.rstrip()
            if "Subject: [GNU Bison 2.7] testsuite:" in text:
                capture_subject = True
                self.output.error(text)
                failed_text = text.split("testsuite:", 1)[1]
            elif capture_subject and line.startswith(" "):
                self.output.error(text)
                failed_text = text
            elif capture_subject:
                capture_subject = False
                failed_text = ""
            else:
                failed_text = ""

            if capture_subject:
                failed_groups.extend(re.findall(r"\b\d+\b", failed_text))
            if text.startswith("FAIL: "):
                failed_groups.extend(re.findall(r"\b\d+\b", text))
            if text.startswith("ERROR: ") or text.startswith("FAIL: "):
                self.output.error(text)

        tests_dir = os.path.dirname(testsuite_log)
        testsuite_dir = os.path.join(tests_dir, "testsuite.dir")
        for group in sorted(set(failed_groups), key=int):
            group_dir = os.path.join(testsuite_dir, group)
            if not os.path.isdir(group_dir):
                continue
            self.output.error("===== bison testsuite group {} details =====".format(group))
            emitted = 0
            for root, _, files in os.walk(group_dir):
                for name in sorted(files):
                    if name not in ("stdout", "stderr") and not name.endswith((".log", ".out", ".exp")):
                        continue
                    path = os.path.join(root, name)
                    try:
                        with open(path, encoding="utf-8", errors="replace") as handle:
                            content = [line.rstrip() for line in handle.readlines()]
                    except OSError:
                        continue
                    if not any(line.strip() for line in content):
                        continue
                    rel = os.path.relpath(path, group_dir)
                    self.output.error("--- {} ---".format(rel))
                    for line in content[:80]:
                        self.output.error(line)
                    emitted += 1
                    if emitted >= 4:
                        break
                if emitted >= 4:
                    break

    def package(self):
        # Standard autotools cross-install: DESTDIR relocates all files
        # under package_folder while the embedded paths keep /usr prefix.
        autotools = Autotools(self)
        autotools.install(args=["DESTDIR={}".format(self.package_folder)])
        bindir = os.path.join(self.package_folder, "usr", "bin")
        for name in ("bison", "yacc"):
            path = os.path.join(bindir, name)
            if os.path.isfile(path):
                os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["usr/bin"]
        self.runenv_info.define_path("PATH", os.path.join(self.package_folder, "usr", "bin"))
        self.runenv_info.define_path("BISON_PKGDATADIR", os.path.join(self.package_folder, "usr", "share", "bison"))
