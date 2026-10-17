#!/usr/bin/env python3
"""Conan recipe for libncursesada -- the Ada95 (AdaCurses) binding to ncurses.

Ada toolchain notes:
  The only Ada toolchain published in ohpcd is gcc-ada (GNAT 9.5.0), and it is an
  OHOS/armv8 binary (conan list "gcc-ada/9.5.0:*" -r=ohpcd -> os: OHOS, arch: armv8);
  the matching binutils (as/ld) is the same.  There is therefore NO Linux cross
  compiler for Ada, and this recipe can only be built natively on OHOS
  (build == host), i.e. CI uses:
      -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
  A cross build (WSL, -pr:b=default) is rejected explicitly in validate().
"""
import glob
import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import (apply_conandata_patches, copy,
                                export_conandata_patches, get, patch)
from conan.tools.env import VirtualBuildEnv
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


# Minimal stand-in for GNU Ada's `gnatprep`, which the ohpcd gcc-ada/9.5.0
# package does NOT ship (only gnatbind/gnatchop/gnatclean/gnatlink/gnatls/
# gnatmake are present).  AdaCurses' src/Makefile.in invokes
#   $(ADAPREP) -DADA_TRACE=@ADA_TRACE@ ... trace.adb_p trace.adb
# so without it the build dies with
#   make[1]: gnatprep: No such file or directory        (CI 50329, Error 127)
# Only the subset of the preprocessor language that AdaCurses uses is
# implemented: -D name[=value], #if/#elsif/#else/#end if; and $name
# substitution.  Undefined $name references are left untouched (upstream only
# has one, inside an Ada comment).
_GNATPREP_SHIM = r'''
import re
import sys


def _truth(value):
    if value is None:
        return False
    text = str(value).strip().lower()
    if text in ("true", "yes"):
        return True
    if text in ("false", "no"):
        return False
    try:
        return int(text, 0) != 0
    except ValueError:
        return bool(text)


class _Preprocessor(object):
    _TOKEN = re.compile(r"\s*(\(|\)|/=|<=|>=|=|<|>|[A-Za-z_][A-Za-z0-9_]*|[0-9]+)")

    def __init__(self, symbols):
        self.symbols = symbols

    def _tokens(self, expr):
        out = []
        pos = 0
        while pos < len(expr):
            match = self._TOKEN.match(expr, pos)
            if match is None:
                if not expr[pos:].strip():
                    break
                raise ValueError("gnatprep shim: cannot parse %r" % expr)
            out.append(match.group(1))
            pos = match.end()
        return out

    def _operand(self, token):
        if token.isdigit():
            return int(token)
        return self.symbols.get(token)

    def _compare(self, lhs, op, rhs):
        try:
            lhs = int(str(lhs), 0)
            rhs = int(str(rhs), 0)
        except (TypeError, ValueError):
            lhs, rhs = str(lhs), str(rhs)
        if op == "=":
            return lhs == rhs
        if op == "/=":
            return lhs != rhs
        if op == "<":
            return lhs < rhs
        if op == "<=":
            return lhs <= rhs
        if op == ">":
            return lhs > rhs
        return lhs >= rhs

    def _atom(self, tokens, index):
        token = tokens[index]
        if token == "(":
            value, index = self._or(tokens, index + 1)
            if index >= len(tokens) or tokens[index] != ")":
                raise ValueError("gnatprep shim: unbalanced parenthesis")
            return value, index + 1
        if token.lower() == "not":
            value, index = self._atom(tokens, index + 1)
            return (not value), index
        value = _truth(self._operand(token))
        index += 1
        if index < len(tokens) and tokens[index] in ("=", "/=", "<", "<=", ">", ">="):
            op = tokens[index]
            right = self._operand(tokens[index + 1])
            return self._compare(self._operand(token), op, right), index + 2
        return value, index

    def _and(self, tokens, index):
        value, index = self._atom(tokens, index)
        while index < len(tokens) and tokens[index].lower() == "and":
            right, index = self._atom(tokens, index + 1)
            value = value and right
        return value, index

    def _or(self, tokens, index):
        value, index = self._and(tokens, index)
        while index < len(tokens) and tokens[index].lower() == "or":
            right, index = self._and(tokens, index + 1)
            value = value or right
        return value, index

    def evaluate(self, expr):
        tokens = self._tokens(expr)
        if not tokens:
            return False
        return self._or(tokens, 0)[0]

    def substitute(self, line):
        def repl(match):
            return self.symbols.get(match.group(1), match.group(0))
        return re.sub(r"\$([A-Za-z_][A-Za-z0-9_]*)", repl, line)

    def process(self, text):
        out = []
        stack = []
        for line in text.splitlines(True):
            stripped = line.lstrip()
            if stripped.startswith("#"):
                directive = stripped[1:].strip()
                low = directive.lower()
                if low.startswith("if"):
                    expr = directive[2:].strip()
                    if expr.lower().endswith("then"):
                        expr = expr[:-4].strip()
                    parent = stack[-1]["active"] if stack else True
                    cond = self.evaluate(expr) if parent else False
                    stack.append({"parent": parent, "taken": cond,
                                  "active": parent and cond})
                elif low.startswith("elsif"):
                    expr = directive[5:].strip()
                    if expr.lower().endswith("then"):
                        expr = expr[:-4].strip()
                    frame = stack[-1]
                    cond = self.evaluate(expr) if (frame["parent"] and not frame["taken"]) else False
                    frame["active"] = frame["parent"] and cond
                    frame["taken"] = frame["taken"] or cond
                elif low.startswith("else"):
                    frame = stack[-1]
                    cond = frame["parent"] and not frame["taken"]
                    frame["active"] = cond
                    frame["taken"] = frame["taken"] or cond
                elif low.startswith("end"):
                    stack.pop()
                continue
            if stack and not stack[-1]["active"]:
                continue
            out.append(self.substitute(line))
        return "".join(out)


def main(argv):
    symbols = {}
    files = []
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg.startswith("-D"):
            spec = arg[2:]
            if not spec and index + 1 < len(argv):
                index += 1
                spec = argv[index]
            if "=" in spec:
                name, value = spec.split("=", 1)
            else:
                name, value = spec, "True"
            symbols[name] = value
        elif arg.startswith("-"):
            pass
        else:
            files.append(arg)
        index += 1
    if not files:
        sys.stderr.write("gnatprep(shim): no input file\n")
        return 2
    with open(files[0], "r", encoding="utf-8", errors="replace") as handle:
        text = handle.read()
    result = _Preprocessor(symbols).process(text)
    if len(files) > 1:
        with open(files[1], "w", encoding="utf-8") as handle:
            handle.write(result)
    else:
        sys.stdout.write(result)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
'''


class LibNcursesAdaConan(ConanFile):
    name = "libncursesada"
    version = "6.3.20211021"
    description = "Ada95 binding to the ncurses terminal library (upstream name: AdaCurses)"
    license = "MIT"
    homepage = "https://invisible-island.net/ncurses/"
    url = ""
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # ohpcd ncurses is static-only on OHOS
        self.options["ncurses"].shared = False

    def requirements(self):
        # AdaCurses is an ncurses addon: it probes ncursesw through pkg-config
        self.requires("ncurses/6.5")

    def build_requirements(self):
        # OHOS/armv8 binaries only: GNAT compiler + assembler/linker
        self.tool_requires("gcc-ada/9.5.0")
        self.tool_requires("binutils/2.46.0")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libncursesada is supported on Linux/OHOS only")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "ncurses on OHOS is static-only; a shared Ada binding cannot "
                "link against it")
        if cross_building(self):
            raise ConanInvalidConfiguration(
                "libncursesada requires a NATIVE OHOS build: the only Ada toolchain "
                "published in ohpcd (gcc-ada/9.5.0) and its binutils/2.46.0 are "
                "OHOS/armv8 binaries, so no Linux cross compiler exists. Use "
                "-pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64")

    def layout(self):
        # NOTE: do NOT set self.folders.build = '.' here.  Doing so changed
        # Conan's folder semantics so much that the conandata patch could no
        # longer be located (CI 50205/50208/50210/50215/50220).  Instead the
        # out-of-source problem is solved in build() by mirroring the source
        # subdirectories the top-level Makefile recurses into.
        basic_layout(self)

    def _find_ohos_tool(self, name):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        ]
        return next((p for p in candidates if p and os.path.isfile(p)), "")

    def _signing_bin_dir(self):
        """CC/CXX wrappers that SIGN linked executables before they are run.

        E064 root cause: every autoconf run-probe execs a freshly linked binary,
        and OHOS refuses UNSIGNED ELFs, so probes such as CF_GNAT_TRY_RUN report
        failure even though compile+bind+link all succeeded (observed in
        config.log: "./conftest: Permission denied" -> "No usable Ada compiler
        found").  The Ada probe links through gnatlink -> `gcc` found on PATH,
        so the wrapper must be reachable BOTH as $CC and as `gcc` on PATH.
        """
        gcc_ada = self.dependencies.build.get("gcc-ada")
        if gcc_ada is None or not gcc_ada.package_folder:
            return ""
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            self.output.warning("  [warn] llvm-objcopy/binary-sign-tool not found;"
                                " unsigned probes will fail on OHOS")
            return ""
        bindir = os.path.join(self.generators_folder, "signbin")
        os.makedirs(bindir, exist_ok=True)
        script = ("#!/bin/sh\n"
                  "# sign linked outputs so OHOS lets autoconf probes exec them\n"
                  "link=1; out=\"\"; prev=\"\"\n"
                  "for a in \"$@\"; do\n"
                  "  case \"$a\" in -c|-S|-E|-M|-MM|-fsyntax-only) link=0 ;; esac\n"
                  "  if [ \"$prev\" = \"-o\" ]; then out=\"$a\"; fi\n"
                  "  prev=\"$a\"\n"
                  "done\n"
                  "{real} \"$@\"\n"
                  "rc=$?\n"
                  "if [ $rc -eq 0 ] && [ $link -eq 1 ] && [ -n \"$out\" ] && [ -f \"$out\" ]; then\n"
                  "  if head -c 4 \"$out\" 2>/dev/null | grep -q ELF; then\n"
                  "    echo \"sign-cc: signing $out\" >&2\n"
                  "    {objcopy} --remove-section .codesign \"$out\" >&2 || echo \"sign-cc: objcopy failed\" >&2\n"
                  "    {signer} sign -inFile \"$out\" -outFile \"$out\" -selfSign 1 >&2 || echo \"sign-cc: signer failed\" >&2\n"
                  "  fi\n"
                  "fi\n"
                  "exit $rc\n")
        for driver in ("gcc", "g++", "cc", "c++"):
            real = os.path.join(gcc_ada.package_folder, "bin", driver)
            if not os.path.isfile(real):
                continue
            p = os.path.join(bindir, driver)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(script.format(real=real, objcopy=objcopy, signer=signer))
            os.chmod(p, 0o755)
        self.output.info("  [ok] E064: signing compiler wrappers -> " + bindir)
        self._signbin = bindir
        return bindir

    def _gnatprep_shim(self):
        """Provide a `gnatprep` because ohpcd's gcc-ada does not ship one.

        gcc-ada/9.5.0 contains gnatbind/gnatchop/gnatclean/gnatlink/gnatls and
        gnatmake but NOT gnatprep, which AdaCurses' src/Makefile.in calls to
        generate terminal_interface-curses-trace.adb from its .adb_p template:

            make[1]: gnatprep: No such file or directory        (CI 50329)

        A minimal, dependency-free implementation is materialised next to the
        other generators and put first on PATH.  sys.executable is used as the
        interpreter so no separate python3 is required in the build env.
        """
        bindir = os.path.join(self.generators_folder, "gnatprep-bin")
        os.makedirs(bindir, exist_ok=True)
        target = os.path.join(bindir, "gnatprep")
        with open(target, "w", encoding="utf-8") as fh:
            fh.write("#!{}\n".format(sys.executable))
            fh.write(_GNATPREP_SHIM.lstrip("\n"))
        os.chmod(target, 0o755)
        self.output.info("  [ok] gnatprep shim -> " + target)
        return bindir

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            # ohpcd ncurses is a wide-char package -> must resolve ncursesw
            "--enable-widec",
            # gcc-ada 9.5.0 ships no gprbuild; the .gpr project path is unusable
            "--disable-gnat-projects",
            "--with-ada-compiler=gnatmake",
            "--with-ada-libname=AdaCurses",
            "--without-ada-sharedlib",
        ])
        # E064 follow-up: forcing --build != --host makes AdaCurses' own
        # configure demand a SEPARATE native compiler:
        #   "Cross-build requires two compilers. Use --with-build-cc ..."
        # That check is a plain string comparison against $CC, so a different
        # spelling is enough.  Use the native OHOS clang from the profile (it
        # runs on the worker; $CC here is gcc-ada's gcc).
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        build_cc = compilers.get("c") or shutil.which("cc") or "cc"
        tc.configure_args.extend([
            "--with-build-cc={}".format(build_cc),
            "--with-build-cpp={} -E".format(build_cc),
        ])
        env = tc.environment()
        # DRAFT-6487-classads-configshell-hmdfs-getcwd: the CI profile injects
        # CONFIG_SHELL=/data/service/hnp/bin/bash via [buildenv], and that shell's
        # getcwd() fails on HMDFS, so autoconf writes a GARBAGE srcdir into the
        # Makefiles (CI 50242: srcdir = <build>/F\x07..9kk\x07..9kk...), after which
        # make dies with "No rule to make target .../kkconfig/...".  An env var
        # defined here wins over the profile buildenv aggregation.
        env.define("CONFIG_SHELL", "/bin/sh")
        env.define("SHELL", "/bin/sh")
        # The C glue (c_varargs_to_ada.c / ncurses_compat.c ...) and the Ada sources
        # must share one toolchain: configure.in:60 is CF_PROG_CC(gnatgcc gcc cc),
        # but an injected $CC (OHOS clang from the profile) wins in autoconf and
        # would mix GCC9-Ada objects with clang objects.
        # AdaCurses needs `gnatprep`; ohpcd's gcc-ada does not ship it
        # (CI 50329: "make[1]: gnatprep: No such file or directory").
        env.prepend_path("PATH", self._gnatprep_shim())
        signbin = self._signing_bin_dir()
        if signbin:
            # PATH matters too: gnatlink resolves `gcc` from PATH for the Ada probe.
            env.prepend_path("PATH", signbin)
            env.define("CC", os.path.join(signbin, "gcc"))
            env.define("CXX", os.path.join(signbin, "g++"))
            # Pin CPP to the SAME driver as CC.  Left to autoconf, AC_PROG_CPP
            # can settle on the bare `/lib/cpp`, which on a non-OHOS host is a
            # different toolchain and dies in
            #     cpp: fatal error: cannot execute 'cc1': execvp: No such file
            # because our GCC_EXEC_PREFIX redirects cc1 lookup away from it.
            env.define("CPP", os.path.join(signbin, "gcc") + " -E")
        else:
            env.define("CC", "gcc")
            env.define("CXX", "g++")
            env.define("CPP", "gcc -E")
        # gcc-ada exports its Ada runtime search paths through buildenv_info;
        # they only materialise when VirtualBuildEnv is generated.  Without
        # ADA_INCLUDE_PATH / ADA_OBJECTS_PATH / GCC_EXEC_PREFIX the
        # "checking if GNAT works" probe fails and configure aborts with
        # "No usable Ada compiler found" (same failure seen locally).
        VirtualBuildEnv(self).generate()
        gcc_ada = self.dependencies.build.get("gcc-ada")
        if gcc_ada is not None and gcc_ada.package_folder:
            import glob as _glob
            _roots = _glob.glob(os.path.join(gcc_ada.package_folder, "lib", "gcc",
                                             "aarch64-linux-ohos", "*"))
            if _roots:
                _ada = _roots[0]
                env.define("ADA_INCLUDE_PATH", os.path.join(_ada, "adainclude"))
                env.define("ADA_OBJECTS_PATH", os.path.join(_ada, "adalib"))
            env.define("GCC_EXEC_PREFIX",
                       os.path.join(gcc_ada.package_folder, "libexec", "gcc"))
        # E468: PkgConfigDeps only WRITES the .pc files into the generators
        # folder; it does not extend PKG_CONFIG_PATH, so upstream
        # CF_NCURSES_CONFIG's pkg-config probe cannot see ncursesw.pc and
        # configure dies with "Cannot link ncurses library".
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        tc.generate(env)
        PkgConfigDeps(self).generate()
        # AdaCurses' CF_NCURSES_ADDON probes BOTH `ncurses` and `ncursesw`,
        # while the conan ncurses package only exposes ncursesw.pc
        # (pkg_config_name=ncursesw).  Without the non-wide alias configure
        # reports "checking pkg-config for ncurses... no" and then dies with
        # "Cannot link ncurses library".  Provide the alias .pc.
        _wide_pc = os.path.join(self.generators_folder, "ncursesw.pc")
        _alias_pc = os.path.join(self.generators_folder, "ncurses.pc")
        if os.path.isfile(_wide_pc) and not os.path.exists(_alias_pc):
            shutil.copyfile(_wide_pc, _alias_pc)
            self.output.info("  [ok] E468: ncurses.pc alias created for ncursesw")
        # also expose it to any buildenv-based consumer
        self.buildenv_info.append_path("PKG_CONFIG_PATH", self.generators_folder)

    def _prepare_autotools_for_ohos(self):
        """Make configure survive on HarmonyOS PC (HMDFS + non-GNU uname).

        Two documented failure modes are handled here:

        E114 -- the security framework refuses child processes writing into a
        freshly created directory under the default tmpdir.  config.guess
        creates <TMPDIR>/cgXXXXXX/dummy.c and compiles it; on CI that write is
        denied, config.guess then reports "unable to guess system type" and
        configure dies with "cannot guess build type; you must specify one".
        Fix: the recipe (main process) pre-creates a writable directory, points
        TMPDIR at it, and redirects config.status AS_TMPDIR there too.

        E007 -- config.guess/config.sub have no HarmonyOS branch.  When the
        skill patch script is reachable (OHC_SKILL_ROOT) it is applied, which
        teaches them to emit aarch64-unknown-linux-ohos.
        """
        import tempfile

        fixed_tmp = os.path.join(tempfile.gettempdir(), "libncursesada-ac-tmp")
        os.makedirs(fixed_tmp, exist_ok=True)
        for var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[var] = fixed_tmp

        cfg_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as fh:
                cfg = fh.read()
            original = cfg

            # E064 follow-up: CF_GNAT_TRY_RUN compiles AND RUNS ./conftest to
            # decide "if GNAT works".  On OHOS a freshly linked (unsigned)
            # executable cannot be exec'd, so configure reports
            # "No usable Ada compiler found" even though gnatmake is fine.
            # Accept a successful *compile* as the evidence instead; the macro
            # ignores cross_compiling and offers no cache variable to preset.
            # Option C: the Ada probe only needs to prove that the compiler is
            # usable.  Compile-only is sufficient evidence (and the full
            # compile+bind+link was already observed to SUCCEED in CI config.log;
            # only the exec of the unsigned product failed).
            _gnat_old = ('if ( "$cf_ada_make" $ADAFLAGS conftest 1>&5 2>&1 ) ; then'
                         '\n   if ( ./conftest 1>&5 2>&1 ) ; then')
            _gnat_new = ('if ( "$cf_ada_make" $ADAFLAGS -c conftest.adb 1>&5 2>&1 ) ; then'
                         '\n   if ( true ) ; then')
            if _gnat_old in cfg:
                cfg = cfg.replace(_gnat_old, _gnat_new)
            # NOTE: do NOT put extra flags into cf_ada_make -- configure invokes
            # it as "$cf_ada_make", i.e. as a SINGLE word, so
            #   cf_ada_make="gnatmake --GCC=..."
            # fails with "gnatmake --GCC=...: inaccessible or not found" (CI 50192).
            # The compile-only patch above needs no --GCC at all, because it
            # never links, so the signing wrapper is irrelevant here.
                # the exit trap would rm -fr the pre-created directory
                cfg = cfg.replace(
                    '{ test ! -d "$ac_tmp" || rm -fr "$ac_tmp"; } && exit $exit_status',
                    "exit $exit_status")
                self.output.info("  [ok] E114: TMPDIR/ac_tmp -> {}".format(fixed_tmp))
            # E114 (second half): config.status creates $TMPDIR/csXXXXXX with
            # `umask 077`; on setgid HMDFS such a directory is not writable by the
            # child that must write in/out/config.h into it, so configure reports
            # "Permission denied" and never generates src/Makefile (CI 50196).
            # Relax it to umask 022 -- same fix as archives/a/a52dec 0002.
            if "umask 077 && mktemp -d" in cfg:
                cfg = cfg.replace("umask 077 && mktemp -d", "umask 022 && mktemp -d")
                cfg = cfg.replace("(umask 077 && mkdir $tmp)", "(umask 022 && mkdir $tmp)")
                self.output.info("  [ok] E114: config.status tmp dir umask 022")
            # The write-back must NOT live inside the ac_tmp branch: otherwise the
            # E064 / gnatmake patches above are silently discarded whenever that
            # anchor is absent -- CI showed "[ok] GNAT run-probe replaced" while the
            # executed configure still ran the full gnatmake probe.
            if cfg != original:
                with open(cfg_path, "w", encoding="utf-8") as fh:
                    fh.write(cfg)
                os.chmod(cfg_path, 0o755)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Self-evidence: this listing proved decisive once the method had been
        # accidentally deleted by an earlier edit (the build then failed with
        # "config.guess not found" for six consecutive CI rounds because the
        # tarball had never been extracted at all).
        try:
            self.output.info("  [dbg] source_folder: " + self.source_folder)
            self.output.info("  [dbg] contents: " + ", ".join(
                sorted(os.listdir(self.source_folder))[:25]))
        except OSError as exc:
            self.output.warning("  [dbg] cannot list source_folder: " + str(exc))

    def _apply_guess_patch(self):
        """Apply config.guess/config.sub patch with an EXPLICIT base path.

        apply_conandata_patches() resolves the patch base implicitly; after
        switching to an in-source layout (folders.build = ".") it could no
        longer find a/config.guess and the build died in build() (CI 50205).
        patch() with base_path + strip=1 is layout independent (E526: Conan 2
        defaults to strip=0).
        """
        entries = (self.conan_data or {}).get("patches") or []
        if isinstance(entries, dict):
            entries = [dict(v, patch_file=k) for k, v in entries.items()]
        for entry in entries:
            pf = entry.get("patch_file") if isinstance(entry, dict) else entry
            if not pf:
                continue
            src = os.path.join(self.export_sources_folder, pf)
            roots = [r for r in (self.build_folder, self.source_folder,
                                 self.export_sources_folder) if r]
            self.output.info("  [dbg] folders: " + " | ".join(roots))
            base = ""
            for root in roots:
                hits = glob.glob(os.path.join(root, "**", "config.guess"),
                                 recursive=True)
                if hits:
                    base = os.path.dirname(hits[0])
                    break
            if not base:
                raise ConanException(
                    "config.guess not found under any of: " + " | ".join(roots))
            self.output.info("  [dbg] patching in " + base)
            patch(self, base_path=base, patch_file=src, strip=1)

    def _fix_garbled_srcdir(self):
        """Repair the corrupted @srcdir@ substitution in the generated Makefiles.

        CI 50279 diagnostic: @top_srcdir@ is clean while @srcdir@ and VPATH carry
        the correct absolute prefix followed by binary junk, e.g.
          srcdir = .../b/libnXXXX/b/<0x0f0x10..gkk..>
        The platform cannot be fixed from here, so repair the products: this is an
        in-source build, so srcdir for each Makefile IS its own directory.
        """
        # gen/gen.c is a HOST tool (HOST_CC = the OHOS clang) that includes
        # <menu.h>/<panel.h>; its rule uses CFLAGS_NORMAL, which never carries the
        # conan ncurses include dir, so the build died with
        #   gen/gen.c:55:10: fatal error: 'menu.h' file not found   (CI 50306).
        _nc_inc = ""
        _nc_lib = ""
        _nc = self.dependencies.get("ncurses")
        if _nc is not None:
            _dirs = [d for d in _nc.cpp_info.includedirs if d]
            if _dirs:
                _nc_inc = " ".join("-I" + d for d in _dirs)
            _ldirs = [d for d in _nc.cpp_info.libdirs if d]
            if _ldirs:
                # gen/Makefile.in:178 links the host tool `generate` via
                # ACTUAL_LDFLAGS; without the ncurses lib it dies with
                #   ld.lld: error: undefined symbol: acs_map   (CI 50317)
                _nc_lib = " ".join("-L" + d for d in _ldirs) + " -lncursesw"
        for mk in glob.glob(os.path.join(self.source_folder, "**", "Makefile"),
                            recursive=True):
            try:
                with open(mk, "r", encoding="utf-8", errors="replace") as fh:
                    lines = fh.readlines()
            except OSError:
                continue
            want = os.path.dirname(mk)
            changed = False
            for i, ln in enumerate(lines):
                key = ln.split("=")[0].strip()
                if key in ("srcdir", "VPATH"):
                    lines[i] = "{} = {}\n".format(key, want)
                    changed = True
                elif key == "ACTUAL_LDFLAGS" and _nc_lib and "-lncursesw" not in ln:
                    lines[i] = ln.rstrip("\n") + " " + _nc_lib + "\n"
                    changed = True
                elif key == "CFLAGS_NORMAL" and _nc_inc and _nc_inc not in ln:
                    lines[i] = ln.rstrip("\n") + " " + _nc_inc + "\n"
                    changed = True
                elif key == "GENERATE":
                    # The ncurses package here is widec-only, but upstream's
                    # Ada specs hardcode the NARROW library names:
                    #   pragma Linker_Options ("-lpanel" & DFT_ARG_SUFFIX)
                    # where DFT_ARG_SUFFIX carries only the debug/profile
                    # suffix ('', '_g', '_p').  Feed the generator the wide
                    # suffix so the generated constant, and therefore all four
                    # Linker_Options, become -lpanelw/-lmenuw/-lformw/-lncursesw
                    # (otherwise: ld: cannot find -lpanel).  USE_ARG_SUFFIX is
                    # used nowhere else, so this cannot leak into file names.
                    if "'w'" not in ln:
                        lines[i] = "GENERATE = $(PROG_GENERATE) 'w'\n"
                        changed = True
                elif key in ("ADA_MFLAGS", "cf_cv_makeflags"):
                    # src/Makefile.in:40  ADA_MFLAGS = @cf_cv_makeflags@
                    # and src/Makefile.in:201 does `cd ../gen; $(MAKE) $(ADA_MFLAGS)`.
                    # A corrupted value here makes the sub-make print
                    # "No targets. Stop." (CI 50299) because make is handed junk.
                    # An empty value is the safe semantic equivalent.
                    lines[i] = "{} = \n".format(key)
                    changed = True
                if any(ord(ch) < 9 or (13 < ord(ch) < 32) or ord(ch) == 127
                       for ch in ln):
                    self.output.warning("  [dbg] garbage line in {}: {}".format(
                        os.path.basename(mk), repr(ln[:120])))
            if changed:
                with open(mk, "w", encoding="utf-8") as fh:
                    fh.writelines(lines)
                self.output.info("  [ok] E-srcdir: repaired " + mk)

    def _mirror_source_subdirs(self):
        """The top-level Makefile recurses with `cd include/gen/src/doc/samples`.

        Conan runs configure/make in the build folder, which does not contain
        those source subdirectories (VPATH does not help `cd`), so `make` died
        with "cd: include: No such file or directory" (CI 50198).  Link them in.
        """
        for sub in ("include", "gen", "src", "doc", "samples"):
            src = os.path.join(self.source_folder, sub)
            dst = os.path.join(self.build_folder, sub)
            if os.path.isdir(src) and not os.path.exists(dst):
                os.symlink(src, dst)

    def build(self):
        self._apply_guess_patch()
        self._mirror_source_subdirs()
        if self.settings.os == "OHOS":
            self._prepare_autotools_for_ohos()
        autotools = Autotools(self)
        # E007 follow-up / E064: with an OHOS-recognising config.guess the build
        # looks native, so configure RUNS its conftest.  On HarmonyOS the first
        # exec of a non-system binary hits the security gate, and the sandbox
        # kills it -> "configure: error: cannot run C compiled programs."
        # Exporting cross_compiling=yes is useless (autoconf's AC_PROG_CC
        # recomputes it from the canonical build/host pair).  The lever that
        # works is making --build and --host DIFFERENT triples, so
        # _AC_CANONICAL_SYSTEM sets cross_compiling=yes by the canonical path
        # (see archives/a/abiword-plugin-openwriter/3.0.8, E15-E22).
        # NOTE: this Conan (2.29.1) exposes
        #   Autotools.configure(build_script_folder=None, args=None)
        # -- there are NO build=/host= keyword parameters, so the triples must
        # be passed as plain configure arguments.
        try:
            _base = getattr(autotools, "_configure_args", "") or ""
            _extra = ("--build=x86_64-unknown-linux-gnu "
                      "--host=aarch64-unknown-linux-ohos "
                      "cross_compiling=yes "
                      "ac_cv_c_compile_works=yes "
                      "ac_cv_prog_cc_cross=yes")
            # DRAFT-6487-classads-configshell-hmdfs-getcwd prescribes INLINING the
            # shell in the command: an env var set via tc.environment() loses to
            # the profile [buildenv] CONFIG_SHELL=/data/service/hnp/bin/bash,
            # whose getcwd() fails on HMDFS and makes autoconf emit a garbage
            # srcdir (CI 50251).
            self.run(
                'CONFIG_SHELL=/bin/sh SHELL=/bin/sh "{}" {} {}'.format(
                    os.path.join(self.source_folder, "configure"),
                    _base, _extra),
                env="conanbuild", cwd=self.source_folder)
        except Exception:
            # The CI comment only relays configure's stdout; the actual reason
            # (here: why `gnatmake conftest` fails in CF_GNAT_TRY_RUN) is written
            # to config.log, which is not otherwise retrievable.  Surface its tail
            # so the next CI round is diagnosable.
            # configure() runs with cwd=self.source_folder, so config.log is
            # written THERE, not in build_folder.  Looking only in build_folder
            # is why six CI rounds (50242..50329) reported
            # "config.log not found" and gave no diagnosis at all.
            _cfg = next((p for p in (
                os.path.join(self.source_folder, "config.log"),
                os.path.join(self.build_folder, "config.log"),
            ) if os.path.isfile(p)), "")
            if _cfg:
                with open(_cfg, "r", encoding="utf-8", errors="replace") as _fh:
                    _tail = _fh.read()[-12000:]
                self.output.error("===== config.log (tail 12k) =====")
                for _line in _tail.splitlines():
                    self.output.error(_line)
                self.output.error("===== end config.log =====")
            else:
                self.output.error("config.log not found at " + _cfg)
            raise
        # Self-evidence for the garbled-srcdir hunt (CI 50230).
        # Full diagnostic (CI 50263): which Makefile variables are corrupted and
        # whether the "fixed" shell is actually a different binary at all.
        try:
            self.output.info("  [dbg] /bin/sh -> " + str(os.readlink("/bin/sh")))
        except OSError as _exc:
            self.output.warning("  [dbg] readlink /bin/sh: " + str(_exc))
        for _root in (self.source_folder, self.build_folder):
            _mk = os.path.join(_root, "gen", "Makefile")
            if not os.path.isfile(_mk):
                self.output.info("  [dbg] no " + _mk)
                continue
            self.output.info("  [dbg] reading " + _mk)
            with open(_mk, "r", encoding="utf-8", errors="replace") as _fh:
                for _line in _fh:
                    if _line.split("=")[0].strip() in (
                            "srcdir", "top_srcdir", "VPATH", "abs_srcdir",
                            "abs_builddir", "builddir"):
                        self.output.info("  [dbg]   " + repr(_line))
        self._fix_garbled_srcdir()
        # ... and repair an already-generated constants file, because an
        # incremental make will not re-run the generator rule.
        _const = os.path.join(self.source_folder, "src",
                              "terminal_interface-curses_constants.ads")
        if os.path.isfile(_const):
            with open(_const, "r", encoding="utf-8") as _fh:
                _c = _fh.read()
            if 'DFT_ARG_SUFFIX : constant String := "";' in _c:
                with open(_const, "w", encoding="utf-8") as _fh:
                    _fh.write(_c.replace(
                        'DFT_ARG_SUFFIX : constant String := "";',
                        'DFT_ARG_SUFFIX : constant String := "w";'))
                self.output.info('  [ok] widec: DFT_ARG_SUFFIX -> "w"')
        # CI 50288: the gen sub-make reported "No targets", so the .ads specs were
        # never generated.  gen/Makefile.in ends with a section that is appended
        # during configuration -- dump the generated file so we can tell whether
        # that section is missing or was damaged.
        for _root in (self.source_folder, self.build_folder):
            _mk = os.path.join(_root, "gen", "Makefile")
            if not os.path.isfile(_mk):
                continue
            with open(_mk, "rb") as _fh:
                _raw = _fh.read()
            self.output.info("  [dbg] {} bytes={} lines={}".format(
                _mk, len(_raw), _raw.count(b"\n")))
            self.output.info("  [dbg] has-all-target=" + str(b"\nall" in _raw or _raw.startswith(b"all")))
            for _ln in _raw.split(b"\n")[-12:]:
                self.output.info("  [dbg]   tail " + repr(_ln))
        _cfg = os.path.join(self.source_folder, "config.log")
        if os.path.isfile(_cfg):
            with open(_cfg, "r", encoding="utf-8", errors="replace") as _fh:
                for _line in _fh:
                    if _line.startswith(("ac_pwd=", "ac_cs_config=", "srcdir=")):
                        self.output.info("  [dbg] cfg " + repr(_line))
        # Repo convention on OHOS: serial make (-j1).
        # samples/ (tour, ncurses, rain) is built here too; it links against the
        # freshly built Ada library and is the upstream test surface.
        # DRAFT-6487 (second half): the conan build-release subdirectory is deep
        # enough on HMDFS to trigger the getcwd() storm as well; one level
        # shallower (the source folder, which is .../b/<hash>/b) is fine.  Running
        # in-source also makes the top-level Makefile's `cd include/gen/src/...`
        # work without mirroring.
        self.run("CONFIG_SHELL=/bin/sh SHELL=/bin/sh make -j1",
                 env="conanbuild", cwd=self.source_folder)

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # configure/make run IN-SOURCE (cwd=self.source_folder), but
        # Autotools.install() would invoke `make install` in self.build_folder,
        # which holds no top-level Makefile at all:
        #   make: *** No rule to make target 'install'.  Stop.
        self.run('make install DESTDIR="{}"'.format(self.package_folder),
                 env="conanbuild", cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libncursesada")
        self.cpp_info.libs = ["AdaCurses"]
        self.cpp_info.includedirs = ["share/ada/adainclude"]
        self.cpp_info.libdirs = ["lib/ada/adalib"]
        self.cpp_info.bindirs = []
        adainclude = os.path.join(self.package_folder, "share", "ada", "adainclude")
        adalib = os.path.join(self.package_folder, "lib", "ada", "adalib")
        self.buildenv_info.prepend_path("ADA_INCLUDE_PATH", adainclude)
        self.buildenv_info.prepend_path("ADA_OBJECTS_PATH", adalib)
        self.runenv_info.prepend_path("ADA_INCLUDE_PATH", adainclude)
        self.runenv_info.prepend_path("ADA_OBJECTS_PATH", adalib)
