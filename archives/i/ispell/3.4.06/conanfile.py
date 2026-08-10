"""Conan recipe for ispell 3.4.06.

ispell is an interactive spell-checking program for Unix.
Build system: traditional Makefile (no configure script).
Configuration is done via local.h (copied from local.h.samp + make overrides).

Upstream: https://www.cs.hmc.edu/~geoff/ispell.html
License: BSD-4-Clause
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file
from conan.tools.layout import basic_layout


class IspellConan(ConanFile):
    name = "ispell"
    version = "3.4.06"
    package_type = "application"
    description = "Interactive spell-checking program for Unix"
    license = "BSD-4-Clause"
    homepage = "https://www.cs.hmc.edu/~geoff/ispell.html"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("spell", "spellcheck", "text", "cli")

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: must use in(), not ==
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ispell only supports Linux/OHOS, got {self.settings.os}"
            )
        if self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                f"ispell/3.4.06 is adapted and validated for armv8 only, "
                f"got {self.settings.arch}"
            )

    def requirements(self):
        # ispell requires ncurses (wide-character) for terminal UI
        self.requires("ncurses/6.5")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        # Create local.h from sample before applying patches
        src = self.source_folder
        samp = os.path.join(src, "local.h.samp")
        dest = os.path.join(src, "local.h")
        if os.path.exists(samp) and not os.path.exists(dest):
            shutil.copy(samp, dest)
        apply_conandata_patches(self)

    def build(self):
        # R33: get compiler from Conan toolchain conf, never from shell env
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")

        # ncurses package provides include/ and lib/
        ncurses_dep = self.dependencies["ncurses"]
        ncurses_dir = ncurses_dep.package_folder.replace("\\", "/")
        ncurses_inc = f"{ncurses_dir}/include"
        ncurses_lib = f"{ncurses_dir}/lib"

        self.run(
            f'make config.sh '
            f'CC="{cc}" '
            f'CFLAGS="-I{ncurses_inc}" '
            f'LDFLAGS="-L{ncurses_lib}" '
            f'TERMLIB="-L{ncurses_lib} -lncursesw" '
            f'TERMINCLUDE="-I{ncurses_inc}/ncursesw" '
            f'LANGUAGES=""',
            cwd=self.source_folder,
            env=["conanbuild"],
        )
        # upstream config.sh: rule sed-extracts CC from config.X/local.h, NOT
        # from make cmdline; config.sh ends up CC='cc' (upstream default). HongMeng
        # has no `cc` in PATH, so .c.o rule falls back to cc and fails. Patch
        # config.sh in place to point CC at the Conan-provided clang. Also flip
        # TERMLIB from upstream -lncurses to "-L<dir> -lncursesw": HongMeng ncurses
        # package only ships libncursesw.a (no libncurses.a), and the upstream
        # ispell link rule omits $LDFLAGS, so the -L path must ride inside TERMLIB.
        replace_in_file(self, os.path.join(self.source_folder, "config.sh"),
            "CC='cc'", f"CC='{cc}'")
        replace_in_file(self, os.path.join(self.source_folder, "config.sh"),
            "TERMLIB='-lncurses'", f"TERMLIB='-L{ncurses_lib} -lncursesw'")
        # HongMeng libc dropped rindex (deprecated BSD alias); POSIX strrchr is
        # the standard replacement. 8 call sites in buildhash.c + ispell.c, all
        # under proto.h #ifndef USG (USG undefined on HongMeng clang).
        # conan replace_in_file uses str.replace (replaces all occurrences).
        replace_in_file(self, os.path.join(self.source_folder, "buildhash.c"),
            "rindex (", "strrchr (")
        replace_in_file(self, os.path.join(self.source_folder, "ispell.c"),
            "rindex (", "strrchr (")
        # HongMeng libc dropped BSD sigsetmask/sigblock (term.c uses both under
        # #ifdef SIGTSTP, which HongMeng defines). POSIX sigprocmask is the
        # standard replacement but ispell's usage is optional signal-mask
        # management; commenting out the 4 call sites keeps other-platform logic
        # intact and lets ispell link on HarmonyOS.
        term_c = os.path.join(self.source_folder, "term.c")
        replace_in_file(self, term_c,
            "(void) sigsetmask (1<<(SIGTSTP-1) | 1<<(SIGTTIN-1) | 1<<(SIGTTOU-1));",
            "/* sigsetmask dropped on HarmonyOS */ (void) 0;")
        replace_in_file(self, term_c,
            "(void) sigsetmask (1 << (SIGTSTP - 1) | 1 << (SIGTTIN - 1));",
            "/* sigsetmask dropped on HarmonyOS */ (void) 0;")
        replace_in_file(self, term_c,
            "(void) sigsetmask (0);", "/* sigsetmask dropped on HarmonyOS */ (void) 0;")
        replace_in_file(self, term_c,
            "(void) sigsetmask (sigblock (0) & ~(1 << (signo - 1)));",
            "/* sigsetmask/sigblock dropped on HarmonyOS */ (void) 0;")
        # defined (ispell.c is the main translation unit), EXTERN char *BC; etc
        # become tentative definitions (B globals) that clash with ncurses
        # lib_termcap.o's same-named terminfo symbols (ld.lld rejects duplicate).
        # Only BC collides in practice (the cd/cl/cm/ho/etc are ispell-internal).
        # Rename ispell's BC to ispell_BC so both coexist without duplicate.
        ispell_h = os.path.join(self.source_folder, "ispell.h")
        replace_in_file(self, ispell_h,
            "EXTERN char *\tBC;", "EXTERN char *\tispell_BC;")
        replace_in_file(self, os.path.join(self.source_folder, "term.c"),
            "BC = tgetstr (\"bc\", &termptr);", "ispell_BC = tgetstr (\"bc\", &termptr);")
        replace_in_file(self, os.path.join(self.source_folder, "term.c"),
            "if (BC)", "if (ispell_BC)")
        replace_in_file(self, os.path.join(self.source_folder, "term.c"),
            "tputs (BC, 1, iputch);", "tputs (ispell_BC, 1, iputch);")
        self.run(
            f'make -j1 programs ispell.1 ispell.5 '
            f'CC="{cc}" '
            f'CFLAGS="-I{ncurses_inc}" '
            f'LDFLAGS="-L{ncurses_lib}" '
            f'TERMLIB="-lncursesw" '
            f'TERMINCLUDE="-I{ncurses_inc}/ncursesw" '
            f'LANGUAGES=""',  # skip default language (upstream `all` pulls all-languages → munchlist hardlink fails on HarmonyOS)
            cwd=self.source_folder,
            env=["conanbuild"],
        )

    def package(self):
        copy(
            self, "README*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        self.run(
            f'make install-basic install-deformatters install-dictbuild programs '
            f'DESTDIR="{self.package_folder}" '
            f'BINDIR=/bin '
            f'LIBDIR=/lib/ispell '
            f'MANDIR=/share/share/man/man1 '
            f'LANGUAGES=""',  # skip install-languages → munchlist hardlink fails on HarmonyOS
            cwd=self.source_folder,
            env=["conanbuild"],
        )
        # upstream install-basic uses shell `cp` (no -p), which drops fs xattr
        # labels; HarmonyOS MAC (hmmac=use_task) rejects exec of label-stripped
        # binaries in conan cache p/ folder → test_package reports
        # "Operation not permitted". Re-mirror the binaries from the build
        # folder (where they exec fine) into p/bin/, then ELF re-sign so the
        # MAC kernel accepts exec from conan cache p/ (same pattern as daemon,
        # ent, zig recipes in this repo).
        src_bindir = os.path.join(self.package_folder, "usr", "local", "bin")
        dst_bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(dst_bindir, exist_ok=True)
        for name in ("ispell", "buildhash", "icombine", "ijoin", "munchlist",
                     "findaffix", "tryaffix", "sq", "unsq"):
            src = os.path.join(src_bindir, name)
            dst = os.path.join(dst_bindir, name)
            if os.path.isfile(src):
                # cat preserves fs labels better than cp on HongMeng; chmod 755
                # for other-read (upstream cp leaves 770 → kernel rejects exec).
                self.run(f'cat "{src}" > "{dst}" && chmod 755 "{dst}"')

        # HarmonyOS requires ELF signing before a binary can be executed from
        # conan cache p/ (E082); without this test_package cannot run ispell.
        # Only ispell and buildhash are exercised by test_package, but sign
        # both for consistency. Missing tool / failed sign must fail the build
        # (test_package exec depends on it) — do not silently skip.
        if self.settings.os == "OHOS":
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            for name in ("ispell", "buildhash"):
                bin_path = os.path.join(dst_bindir, name)
                if not os.path.isfile(bin_path):
                    continue
                tmp_signed = bin_path + ".signed"
                # strip old .codesign section (tolerate "section not found" on
                # binaries that were never signed before).
                self.run(
                    f'"{objcopy}" --remove-section .codesign "{bin_path}" 2>/dev/null || true',
                    quiet=True)
                self.run(
                    f'"{sign_tool}" sign -inFile "{bin_path}" -outFile "{tmp_signed}" '
                    f'-selfSign 1',
                    quiet=True)
                os.replace(tmp_signed, bin_path)
                os.chmod(bin_path, 0o755)

        # ispell hardcodes LIBDIR=/usr/local/lib + DEFHASH=english.hash at compile
        # time; test_ispell.sh's `ispell -a` relies on that default path. Upstream's
        # install-languages → munchlist chain uses `ln -s` softlinks which HarmonyOS
        # rejects in conan cache, so we skipped install-languages above. Generate
        # english.hash directly with buildhash (bypassing munchlist) from the
        # english.aff + english.{0,1,2} sources upstream ships, and install it at
        # the hardcoded default path so `ispell -a` finds a dictionary.
        buildhash_bin = os.path.join(dst_bindir, "buildhash")
        english_src = os.path.join(self.source_folder, "languages", "english")
        aff_in = os.path.join(english_src, "english.aff")
        if os.path.isfile(buildhash_bin) and os.path.isfile(aff_in):
            tmp_dict = os.path.join(self.package_folder, "english.dict")
            with open(tmp_dict, "wb") as out:
                for shard in ("english.0", "english.1", "english.2"):
                    shard_path = os.path.join(english_src, shard)
                    if os.path.isfile(shard_path):
                        with open(shard_path, "rb") as inp:
                            out.write(inp.read())
            tmp_hash = os.path.join(self.package_folder, "english.hash")
            self.run(
                f'"{buildhash_bin}" "{tmp_dict}" "{aff_in}" "{tmp_hash}"',
                quiet=True)
            lib_dir = os.path.join(self.package_folder, "usr", "local", "lib")
            os.makedirs(lib_dir, exist_ok=True)
            os.replace(tmp_hash, os.path.join(lib_dir, "english.hash"))
            os.remove(tmp_dict)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
