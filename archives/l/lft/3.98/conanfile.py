#!/usr/bin/env python3
"""Conan recipe for lft 3.98 — Layer Four Traceroute (plus the whob client).

lft is a *TCP/SCTP-based* traceroute utility (it traces by completing real
transport handshakes, so middleboxes that drop ICMP do not hide the path) and
it doubles as a raw-socket network-diagnosis suite: it uses libpcap to sniff
the returning packets, has an optional c-ares asynchronous resolver, and an
optional ncurses "watch" monitor.  The release ships two programs built from
the same object set:

* ``lft``  — the traceroute front end (``lft.c`` + ``lft_lib.c`` + ``lft_icmptrace.c``
  + ``lft_btcptrace.c`` + ``lft_ifname.c`` + ``whois.c`` + optional ``lft_watch.c``).
* ``whob`` — a standalone whois/route-server client (``whois.c`` compiled with
  ``-DSTANDALONE``), linked with the ncurses flags filtered out (see Makefile.in).

Build surface, read from the verified 3.98 tarball (sha256 395ced8d...3455):

* ``Makefile.in:25`` is ``LIBS=@LIBS@`` and ``all: lft whob`` — the tree ships a
  **generated ``configure``** (autoconf 2.69) plus ``Makefile.in`` and ``config/``,
  and **no ``configure.ac``**, so ``configure`` is treated as a release artifact
  (generated files are patched in place, not via ``patches/`` — corpus convention).
* ``lft_types.h:110`` unconditionally ``#include <pcap.h>`` ⇒ **libpcap is a hard
  dependency**; ``configure`` calls ``as_fn_error`` when it cannot find it.
* ``c-ares`` (async DNS) and ``ncurses`` (watch mode) are *optional*: every call
  site is wrapped in ``#ifdef HAVE_CARES`` / ``#ifdef HAVE_NCURSES`` and
  ``configure`` only defines those macros when it finds the libraries.  This
  recipe pins them OFF (``--disable-async-dns --disable-ncurses``) so the link
  closure is exactly ``libpcap`` and never silently picks up a host copy from
  the ``/opt/homebrew /usr/local /opt/local /opt/pkg`` candidate-prefix scan.
* ``configure`` accepts ``--with-pcap=PATH`` (lft.c:4661 ff.), which sets
  ``pcap_path_override=yes``, injects ``-I$PATH/include`` + ``-L$PATH/lib``, and
  short-circuits both the pkg-config branch and the candidate-prefix scan.  We
  point it straight at the Conan libpcap package folder ⇒ deterministic detection.

OHOS notes
----------
* ``build()`` does not call ``autotools.configure()`` directly: the ohos-aarch64
  profile ``[buildenv]`` injects ``CONFIG_SHELL=/data/service/hnp/bin/bash``, and
  that bash fails ``getcwd()`` on HMDFS, so autoconf's configure re-exec of
  ``$CONFIG_SHELL`` dies before doing any work (E386).  The unset therefore
  happens *inside the same shell command* (a ``generate()``-time ``env.unset()``
  loses to the runtime re-injection — validated in sword/1.9.0 and wmcore/0.0.4).
  The configure arguments still come from ``Autotools._configure_args``; the only
  things this recipe appends are ``--with-pcap`` / ``--disable-async-dns`` /
  ``--disable-ncurses`` (feature toggles, never compiler switches — R1/R33/R49).
* ``LD_LIBRARY_PATH`` is injected for the same run (E467): ``AutotoolsDeps`` puts
  the dependency ``-l`` flags into ``$LIBS``, so autoconf's first "can we run a C
  program" conftest links against that closure; on this build libpcap is static
  so the loader path is belt-and-suspenders, but keeping the wmcore prescription
  identical means the recipe is correct if libpcap is ever consumed as a shared
  build.
* E011/E114: autoconf builds ``config.status``'s scratch dir with
  ``(umask 077 && mktemp -d ./confXXXXXX)``; on HMDFS the 0700 dir reads back as
  0660 (search bit lost) ⇒ ``could not setup config files machinery``.  Fixed by
  rewriting ``umask 077`` -> ``umask 022`` in ``configure`` in place (2 hits),
  with a loud warning if the literal ever disappears.
* Upstream ships **no** automated test suite and **no** ``check`` target (see
  ``test_package/MANIFEST.yml`` for the three independent counts), so ``build()``
  runs only ``make -j1``; the packaged ``test_package/`` asserts behaviour.
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class LftConan(ConanFile):
    name = "lft"
    version = "3.98"
    description = ("Layer Four Traceroute (LFT): a TCP/SCTP-based traceroute and "
                   "raw-socket network diagnosis tool, packaged together with the "
                   "whob whois/route-server client")
    license = "VOSTROM"
    homepage = "https://pwhois.org/lft/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("traceroute", "network", "diagnostics", "pcap", "whois")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        # R32: accept the OHOS enum as well as Linux.
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "lft is adapted for Linux/OHOS, not " + str(self.settings.os))

    def requirements(self):
        # lft_types.h unconditionally includes <pcap.h>; c-ares and ncurses are
        # compile-optional and this recipe pins them off, so libpcap is the only
        # dependency in the graph.  1.10.6 is the newest published OHOS build.
        self.requires("libpcap/1.10.6")

    def layout(self):
        # lft's Makefile.in is NOT VPATH-aware (it compiles lft.c -> lft.o with
        # bare relative paths), so configure and make must run in the SAME tree.
        # basic_layout defaults build_folder to "build/Release"; pinning it to
        # "." keeps an in-tree build so `make` finds the sources next to itself.
        basic_layout(self, build_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)],
            strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        AutotoolsToolchain(self).generate()

    def export_sources(self):
        # 本包 0 补丁；仍声明导出通道，将来上游修复以真实 patches/ 交付，
        # 而不是在配方里做字符串替换（G1/W2 形状要求）。
        export_conandata_patches(self)
        # E160: 把仓内 helper 随配方一起导出，构建期才取得到
        copy(self, "patch-autotools-ohos.pl",
             src=os.path.join(self.recipe_folder,
                             "..", "..", "..", "..", "scripts"),
             dst=self.export_sources_folder)

    def build(self):
        apply_conandata_patches(self)
        self._fix_configure_umask()
        self._patch_config_triplets()
        autotools = Autotools(self)
        self._configure(autotools)
        # Upstream has no `check` target and 0 test sources (see MANIFEST.yml),
        # so `make check` here would abort the build with "No rule to make
        # target 'check'"; the static evidence for that is captured in
        # test_package/MANIFEST.yml instead of being executed.
        autotools.make(args=["-j1"])

    def _fix_configure_umask(self):
        """E011 / E114: ``umask 077`` in the generated configure breaks HMDFS."""
        path = os.path.join(self.source_folder, "configure")
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            text = handle.read()
        hits = text.count("umask 077")
        if not hits:
            self.output.warning("E011: 'umask 077' not found in configure - "
                             "upstream text changed, config.status may fail")
            return
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text.replace("umask 077", "umask 022"))
        self.output.info("E011: rewrote %d occurrence(s) of 'umask 077' "
                         "to 'umask 022' in configure" % hits)

    def _dependency_libdirs(self):
        """Absolute lib directories of the whole host dependency closure."""
        found, seen = [], set()
        for _, dep in self.dependencies.host.items():
            base = dep.package_folder or ""
            for entry in dep.cpp_info.libdirs:
                p = entry if os.path.isabs(entry) else os.path.join(base, entry)
                if os.path.isdir(p) and p not in seen:
                    seen.add(p)
                    found.append(p)
        return found

    def _locate_helper(self):
        """Resolve scripts/patch-autotools-ohos.pl at build time, portably.

        Measured: during ``conan create`` ``self.recipe_folder`` points into the
        *cache* export folder, so walking up from it never reaches the checkout.
        The helper is therefore exported alongside the recipe (see
        ``export_sources``) and looked for in three places: the skill root the
        CI exports, the exported-sources folder, then the recipe folder (plain
        in-place runs).  Not finding it stays a hard error — silently skipping
        would just move the failure into ``configure``.
        """
        name = 'patch-autotools-ohos.pl'
        skill_root = os.environ.get('OHC_SKILL_ROOT', '')
        if skill_root:
            cand = os.path.join(skill_root, 'scripts', name)
            if os.path.isfile(cand):
                return cand
        for folder in (getattr(self, 'export_sources_folder', None),
                       getattr(self, 'recipe_folder', None),
                       os.path.join(getattr(self, 'export_sources_folder', '.') or '.',
                                    '..', '..', '..', '..', 'scripts')):
            if not folder:
                continue
            for cand in (os.path.join(folder, name), os.path.join(folder, 'scripts', name)):
                if os.path.isfile(cand):
                    return cand
        raise ConanException('E160: ' + name + ' not found in skill root, exported '
                             'sources or recipe folder; refusing to skip the '
                             'config.guess/config.sub patch')


    def _patch_config_triplets(self):
        """E160 (with E007/E072/E122): the shipped config.guess cannot see HarmonyOS.

        ``configure`` aborts with "cannot guess build type; you must specify
        one" because the release ships a pre-OHOS ``config/config.guess``
        (uname -s is "HarmonyOS", uname -r "HongMeng Kernel ...").  The corpus
        rule is to patch config.guess/config.sub with the repo helper
        ``scripts/patch-autotools-ohos.pl`` (it takes both files in one
        invocation); bypassing it via ``--build``/``--host`` is forbidden
        (autotools-patterns #0).
        """
        script = self._locate_helper()
        guess = os.path.join(self.source_folder, 'config', 'config.guess')
        sub = os.path.join(self.source_folder, 'config', 'config.sub')
        if not (os.path.isfile(guess) and os.path.isfile(sub)):
            self.output.warning('E160: config.guess/config.sub 未成对出现在 config/，'
                                '跳过三元组补丁；configure 可能仍报 cannot guess build type')
            return
        self.output.info('E160: patching config.guess/config.sub for HarmonyOS')
        self.run('perl "%s" "%s" "%s"' % (script, guess, sub))


    def _configure(self, autotools):
        """Run configure with CONFIG_SHELL removed in the very same command.

        E386 + E467 (see module docstring).  Arguments come from
        ``Autotools._configure_args``; only deterministic feature toggles are
        appended here (never compiler switches, R1/R33/R49).
        """
        base_args = getattr(autotools, "_configure_args", None)
        if base_args is None:
            self.output.warning("Autotools._configure_args unavailable, "
                             "falling back to autotools.configure()")
            autotools.configure()
            return
        cfg_path = os.path.relpath(os.path.join(self.source_folder, "configure"),
                                   self.build_folder)
        # POSIX sh resolves a bare "configure" through $PATH; the in-tree layout
        # (source_folder == build_folder) makes relpath exactly that, which dies
        # with "configure: inaccessible or not found" (rc 127).  It must be a
        # relative path expression.
        if not os.path.isabs(cfg_path) and not cfg_path.startswith("."):
            cfg_path = "./" + cfg_path
        # POSIX sh resolves a bare "configure" through $PATH; the in-tree layout
        # (source_folder == build_folder) makes relpath exactly that, which dies
        # with "configure: inaccessible or not found" (rc 127).  It must be a
        # relative path expression.
        if not os.path.isabs(cfg_path) and not cfg_path.startswith("."):
            cfg_path = "./" + cfg_path
        ldpath = ":".join(self._dependency_libdirs())
        # Pin the pcap probe to the Conan libpcap package folder (its <prefix>
        # carries include/pcap.h and lib/libpcap.a).  This disables the
        # pkg-config branch and the host candidate-prefix scan.
        pcap_prefix = self.dependencies["libpcap"].package_folder
        extra = (' --with-pcap="%s" --disable-async-dns --disable-ncurses'
                 % pcap_prefix)
        self.output.info("configure LD_LIBRARY_PATH=" + ldpath)
        self.output.info("configure --with-pcap=" + pcap_prefix)
        self.run("unset CONFIG_SHELL; LD_LIBRARY_PATH=\"" + ldpath + "\" "
                 + cfg_path + " " + base_args + extra,
                 cwd=self.build_folder)

    def package(self):
        autotools = Autotools(self)
        autotools.install(target="install", args=["-j1"])
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        # Two standalone CLI programs; exports no header and no library.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        # lft.8 / whob.8 install under <pkg>/share/man/man8 (prefix=/).
        self.cpp_info.resdirs = ["share"]
