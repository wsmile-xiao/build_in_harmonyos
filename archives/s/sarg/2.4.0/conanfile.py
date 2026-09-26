#!/usr/bin/env python3
"""Conan recipe for sarg 2.4.0 - Squid Analysis Report Generator.

sarg is a command line log analyzer (an application, not a library): it parses
squid / combined / sarg-native access logs and emits a static HTML report tree.

Upstream build system: a generated ``configure`` plus a hand written
``Makefile.in`` whose install target uses plain ``cp`` (never ``install(1)``)
and whose compile flags bake absolute paths (BINDIR / SYSCONFDIR / FONTDIR /
IMAGEDIR / SARGPHPDIR / LOCALEDIR) into the binary with -D.

OHOS adaptation points (full write-up in notes.md):
  * 0001/0002  cfgaux/config.guess and cfgaux/config.sub are the 2015-03-04
    releases and reject the ``aarch64-unknown-linux-ohos`` triplet.
    ``scripts/patch-autotools-ohos.pl`` cannot be used here: it inserts a
    ``GUESS=...`` assignment, but this config.guess has no GUESS consumer
    (every case branch does ``echo; exit``), so the patched value is never
    read and configure still reports "cannot guess build type".
  * 0003       configure builds its conftest scratch directory under
    ``umask 077``. Preventive only: the same-family precedent
    ``archives/a/aide/0.19.3`` and ``archives/a/a52dec/0.7.4`` needed
    ``umask 022`` on HMDFS, but sarg
    never showed that symptom, and a probe on this device shows the mode HMDFS
    forces on new directories (2771) is the same for ``umask 077`` and
    ``umask 022``, with the follow-up ``cp`` succeeding in both cases
    (notes.md symptom 4).
  * 0004       util.c my_mkdir() probes each path prefix with access(R_OK).
    OHOS mounts /storage 0711, so an existing prefix reports EACCES, the
    following mkdir() reports EEXIST and upstream treats EEXIST as fatal.
  * -fcommon is mandatory: include/conf.h holds tentative definitions
    (BgImage, LogoImage, outdir, period, code, code2, ...) which clang >= 10
    compiles as strong symbols by default, so the final link dies with
    "ld.lld: error: duplicate symbol".
  * in-tree build: the Makefile.in is hand written (not automake generated),
    its ``%.o: %.c`` pattern has no VPATH, so objects can only be built in
    the directory that holds the sources - see layout().
  * absolute prefix: the report assets (fonts/images) are located through
    compile-time -D macros, so ``--prefix`` must be the real package folder
    or the binary looks for ``//share/sarg/...`` at run time - see build().
    ``test_package/test_sarg.sh`` asserts this behaviourally: the four pngs of
    the baked IMAGEDIR have to turn up in ``<output_dir>/images/`` of the
    generated report.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, export_conandata_patches, get,
                               load, replace_in_file, save)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SargConan(ConanFile):
    name = "sarg"
    version = "2.4.0"
    description = ("Squid Analysis Report Generator - parses squid, combined and "
                   "sarg native access logs into a static HTML usage report")
    license = "GPL-2.0-or-later"
    homepage = "http://sarg.sourceforge.net/"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Zero Conan dependencies: every optional upstream feature is switched
        # off below (see generate()), so nothing is linked against the system
        # libraries of the same name (R26).
        # bash/5.3 is a build-context shell only (tool_requires does not enter the
        # host package_id): the profile [buildenv] pins CONFIG_SHELL/SHELL to the
        # harmonybrew bash, whose getcwd() fails intermittently in HMDFS build dirs
        # (E386), and /bin/sh here is mksh, which autoconf-generated configure does
        # not accept for its bash-isms.  Same route as archives/x/xrdp/0.10.6.1.
        self.tool_requires("bash/5.3")

    def layout(self):
        # sarg's Makefile.in is written by hand (there is no ``VPATH`` and no
        # automake ``$(srcdir)`` prefix on the prerequisites), so the implicit
        # ``%.o: %.c`` rule only ever finds a source file in the directory make
        # runs in.  With the default basic_layout split (source in <b>, build in
        # <b>/build-release) ``make`` stops at
        # "No rule to make target 'util.c', needed by 'util.o'" even though
        # configure succeeded.  Point the build folder back at the source folder
        # for a genuine in-tree build instead of editing the upstream Makefile
        # (adding VPATH there would widen the change surface for no gain).
        # The generated files land in <b>/build-release/conan (set by
        # basic_layout before the override), i.e. still outside the tree
        # configure populates.  Same idiom as archives/a/acpitool/0.5.1.
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # clang >= 10 defaults to -fno-common.  include/conf.h defines its
        # globals as tentative definitions, therefore every object file emits
        # a strong symbol and the link fails with duplicate symbols.
        # R33: flag goes through the Conan toolchain, never a raw shell env.
        tc.extra_cflags.append("-fcommon")
        # Optional upstream features are disabled deliberately: gd/ldap/iconv/
        # pcre/zlib/bzlib/liblzma would each pull a system library of the same
        # base name (R26) and none of them is needed for the text report path.
        # --disable-nls drops the po/ catalogs, the build then needs no
        # gettext and LOCALEDIR stays unused.
        for arg in ("--disable-nls",
                    "--without-gd",
                    "--without-ldap",
                    "--without-iconv",
                    "--without-pcre",
                    "--without-zlib",
                    "--without-bzlib",
                    "--without-liblzma"):
            tc.configure_args.append(arg)
        tc.generate()

    def _install_root_marker(self):
        return os.path.join(self.build_folder, "conan-sarg-install-root.txt")

    def build(self):
        apply_conandata_patches(self)
        # E386（经验汇总 §12.70 / 适配检查清单#11）：profile [buildenv] 把 CONFIG_SHELL/SHELL
        # 钉死 /data/service/hnp/bin/bash，autoconf 用它重新 exec configure；该 bash 在 HMDFS
        # 构建目录下 getcwd 间歇失败 → configure: error: working directory cannot be determined
        # （本轮 conan-verify 的 G2 首错即此，见 archives/s/sarg/2.4.0/reports/conan-create.log）。
        # 工具链级 env 会被 profile buildenv 覆盖（§12.20），唯一可靠位置是对聚合 env 脚本做
        # 文本替换（禁止同名二次 save_script：聚合器自 source 会无限递归）。不改框架 profile。
        shell_bin = "/bin/sh"
        try:
            _b = self.dependencies.build["bash"].cpp_info.bindirs[0]
            if os.path.isfile(os.path.join(_b, "bash")):
                shell_bin = os.path.join(_b, "bash")
        except Exception:
            pass
        self.output.info("E386 shell routing: CONFIG_SHELL/SHELL -> %s" % shell_bin)
        for _name in os.listdir(self.generators_folder):
            if _name.endswith(".sh"):
                _p = os.path.join(self.generators_folder, _name)
                with open(_p, "r", encoding="utf-8", errors="ignore") as _f:
                    _t = _f.read()
                if "/data/service/hnp/bin/bash" in _t:
                    replace_in_file(self, _p,
                                    "/data/service/hnp/bin/bash", shell_bin)

        # sarg bakes BINDIR / SYSCONFDIR / FONTDIR / IMAGEDIR into the binary
        # with -D, so the values configure prints are the values the program
        # uses at run time.  AutotoolsToolchain's default ``--prefix=/`` turns
        # the defaults into ``//share/sarg/fonts`` and ``//share/sarg/images``
        # (see the "using //share/..." lines of the previous conan-create.log),
        # i.e. an absolute path outside the package that never exists on OHOS:
        # copy_images() then logs ``Cannot open directory`` and every report
        # ships an empty images/ folder.
        # ``--enable-fontdir``/``--enable-imagedir`` take literal strings with no
        # ${prefix} expansion and are used *unprefixed* by the install rules, so
        # the only self-consistent knob is the prefix itself: hand it the Conan
        # package folder (same route as archives/g/gnuspool/1.8).  configure
        # re-expands datarootdir/sysconfdir/man1dir from it, which yields
        # FONTDIR=<pkg>/share/sarg/fonts, IMAGEDIR=<pkg>/share/sarg/images,
        # SYSCONFDIR=<pkg>/etc - exactly where package() puts those files, and
        # the leading ``//`` artefact disappears.  It is appended after the
        # toolchain's own ``--prefix=/`` so autoconf keeps the last assignment.
        # The trade-off (an application package whose data path is absolute to
        # the build-time package folder) is written up in notes.md.
        install_root = self.package_folder.replace("\\", "/")
        self.output.info("baked install prefix: %s" % install_root)
        save(self, self._install_root_marker(), install_root)

        autotools = Autotools(self)
        autotools.configure(args=["--prefix=%s" % install_root,
                                  # SARGPHPDIR defaults to /var/www/html, which is
                                  # not writable on OHOS.  It is only a Makefile
                                  # install destination (nothing is compiled in:
                                  # no .c/.h references SARGPHPDIR), so switch the
                                  # PHP installation off through upstream's own
                                  # AC_ARG_ENABLE(sargphp) knob instead of
                                  # redirecting it somewhere inside the package -
                                  # there is no PHP runtime on HarmonyOS anyway.
                                  "--disable-sargphp"])
        # -j1: upstream's Makefile has no dependency on itself, so a changed
        # CFLAGS does not trigger a rebuild of the existing objects; a clean
        # single job build keeps that trap away from every future invocation.
        autotools.make(args=["-j1"])
        # Upstream ships no test suite at all: `make check` aborts with
        # "No rule to make target 'check'" (evidence in notes.md), so there is
        # nothing real to execute here.  The substance is covered by the
        # consumer test in test_package/ (R51/R34).

    def package(self):
        autotools = Autotools(self)
        # make install uses $(DESTDIR)$(bindir), $(DESTDIR)$(IMAGEDIR), ...
        # with bindir/IMAGEDIR already absolute inside the package folder (the
        # prefix handed to configure in build()), so DESTDIR must stay empty -
        # otherwise every file lands in <pkg><pkg>/...
        # The install rules are upstream's own: bin/sarg, share/man/man1/sarg.1,
        # etc/{sarg.conf,exclude_codes,user_limit_block,css.tpl},
        # share/sarg/images/* and share/sarg/fonts/*.
        autotools.install(args=["DESTDIR="])

        # Guard for the (cache relocation) case where conan packages the build
        # into a folder other than the one that was baked in: the tree above
        # then lives outside the collected package, so mirror it in.  Ordinary
        # ``conan create`` runs build() and package() against the same package
        # folder and this is a no-op; the log line records which happened.
        baked = load(self, self._install_root_marker()).strip()
        if os.path.abspath(baked) != os.path.abspath(self.package_folder):
            self.output.warning(
                "install root %s != package folder %s: mirroring the tree"
                % (baked, self.package_folder))
            if os.path.isdir(baked):
                shutil.copytree(baked, self.package_folder, dirs_exist_ok=True)
            else:
                raise Exception("make install wrote to %s which no longer exists"
                                % baked)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        # fonts/ and images/ live under share/sarg/, man under share/man/
        self.cpp_info.resdirs = ["share"]
