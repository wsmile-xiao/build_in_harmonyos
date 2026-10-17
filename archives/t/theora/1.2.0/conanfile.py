#!/usr/bin/env python3
"""Conan recipe for theora 1.2.0 — Theora video codec (Xiph trio finale).

Upstream: xiph/theora tag v1.2.0 (official release tarball
downloads.xiph.org/releases/theora/libtheora-1.2.0.tar.gz, 2025-03-29).
Xiph chain finale: ogg/1.1.1 (#10038) -> vorbis/1.3.7 (#10592) -> theora.

Upstream facts (libtheora-1.2.0.tar.gz):
  - Pure C, three libraries: libtheoradec (decoder), libtheoraenc (encoder),
    libtheora (pre-1.0 legacy combined API).
  - Pure autotools (configure.ac + pre-generated configure, no CMake).
  - The tarball ships a 2022-01-09 config.guess/config.sub pair (new-style
    GUESS= scripts) — the official patch-autotools-ohos.pl applies cleanly,
    no autoreconf needed (unlike ogg 1.1.1's 2004 tarball).
  - configure.ac checks `ogg >= 1.3.4` through pkg-config first; when that
    fails it falls back to XIPH_PATH_OGG (--with-ogg prefix probing, link
    test only, no version gate). We consume the `ogg` package line
    (ogg/1.1.1, PR #10038): the theora sources only use the oggpackB_write
    family + oggpack_write/writeclear, all present in ogg 1.1.1's public
    header — the pkg-config version string is the only mismatch, bypassed
    by the documented --with-ogg fallback (vorbis/#10592 precedent keeps
    libvorbis separate; theora's lib/ itself never links vorbis).
  - The library build needs only ogg; SDL/PNG/TIFF/cairo are examples-only
    and are switched off with --disable-examples. vorbis is likewise only
    used by encoder_example (also inside examples/).
  - aarch64 matches no `arm*` case in configure.ac's asm dispatcher, so the
    build takes the plain-C path (no ARM asm, no perl dependency).
  - Upstream test suite (tests/Makefile.am): 9 check programs driven by
    `make check` — TESTS_DEC (noop_theora, comment, comment_theoradec,
    comment_theora) + TESTS_ENC (noop, noop_theoraenc, granulepos,
    granulepos_theoraenc, granulepos_theora); all link the in-tree .la
    libraries with $(OGG_LIBS) and run under the libtool wrapper.

OHOS adaptations (ogg 1.1.1 / bwm-ng 0.6.3 lineage):
  - E007: patch the shipped 2022 config.guess/config.sub with the official
    perl patcher (new-style scripts, GUESS= anchors); never --build/--host.
  - E114: relax `umask 077` to `umask 022` in the generated configure so
    config.status temp dirs stay writable on HMDFS.
  - E074: parallel make hits the HMDFS jobserver fifo EPERM — use -j1.
  - R26: not a system-same-name library (no libtheora* in /lib /lib64),
    default shared build managed by Conan.
  - DT_NEEDED hygiene: pass `-L<ogglibdir> -logg` via OGG_LIBS instead of
    absolute .la paths, keeping DT_NEEDED entries bare sonames (same
    approach as vorbis 1.3.7's 0002 patch).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class TheoraConan(ConanFile):
    name = "theora"
    version = "1.2.0"
    description = "Theora video codec reference implementation (Xiph.Org)"
    license = "BSD-3-Clause"
    homepage = "https://xiph.org/theora/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "theora 1.2.0 is only supported on Linux/OHOS, not "
                + str(self.settings.os)
            )

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # theora.h/theoradec.h/theoraenc.h publicly include <ogg/ogg.h>
        # (ogg_int64_t / ogg_packet types in the public API), so ogg
        # headers and libs are transitive for consumers.
        self.requires(
            "ogg/1.1.1",
            transitive_headers=True,
            transitive_libs=True,
        )

    def source(self):
        src = dict(self.conan_data["sources"][self.version])
        src.setdefault("filename", "libtheora-1.2.0.tar.gz")
        get(self, **src, strip_root=True)
        # R04: apply the versioned patch declared in conandata.yml:
        #  0001-ogg-uint64-portability.patch — lib/state.c uses
        #  ogg_uint64_t (a libogg >= 1.3.x type) for the border mask;
        #  replace with uint64_t + explicit <stdint.h> so the old ogg
        #  package line (ogg/1.1.1, Xiph chain pairing) builds cleanly.
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # Examples-only deps (SDL/PNG/TIFF/vorbis/cairo) are switched off;
        # the three libraries themselves need only ogg.
        tc.configure_args.append("--disable-examples")
        # R15/E007: never pass --build/--host; the patched config.guess
        # detects HarmonyOS as aarch64-unknown-linux-ohos natively.
        tc.configure_args = [
            a for a in tc.configure_args
            if not str(a).startswith("--build=") and not str(a).startswith("--host=")
        ]

        # ogg/1.1.1's pkg-config Version is 1.1.1 < the 1.3.4 gate in
        # PKG_CHECK_MODULES, so force the documented XIPH_PATH_OGG fallback:
        # --with-ogg takes a prefix; --disable-oggtest skips the run test
        # (cross-compile environment), leaving the compile+link probe which
        # the conan build env satisfies through OGG_CFLAGS/OGG_LIBS below.
        ogg = self.dependencies["ogg"]
        ogg_libdir = os.path.join(ogg.package_folder, ogg.cpp_info.libdirs[0])
        ogg_includedir = os.path.join(ogg.package_folder, ogg.cpp_info.includedirs[0])
        tc.configure_args.append(f"--with-ogg={ogg.package_folder}")
        tc.configure_args.append("--disable-oggtest")
        # DT_NEEDED hygiene: bare -l linking (no absolute paths), same
        # approach as the vorbis 1.3.7 0002-link-ogg-by-soname patch.
        # configure accepts VAR=VALUE assignments (AC_ARG_VAR style), which
        # land in the generated Makefile's OGG_CFLAGS/OGG_LIBS.
        tc.configure_args.append(f"OGG_CFLAGS=-I{ogg_includedir}")
        tc.configure_args.append(f"OGG_LIBS=-L{ogg_libdir} -logg")

        # Upstream `make check` executes the 9 test programs through the
        # libtool wrapper in-build; the tests link the freshly built
        # libtheora*.so which DT_NEED libogg.so.0 from the conan package
        # folder. Expose ogg's libdir to the runtime loader (the profile's
        # LD_LIBRARY_PATH only covers the toolchain, not dependencies).
        env = tc.environment()
        env.prepend_path("LD_LIBRARY_PATH", ogg_libdir)
        tc.generate(env=env)

    def build(self):
        src = self.source_folder

        # E007: patch the shipped 2022 config.guess/config.sub so HarmonyOS
        # (uname -s = HarmonyOS) is detected as aarch64-unknown-linux-ohos.
        # The shipped scripts are new-style (GUESS= variable), so the
        # official perl patcher applies cleanly (CI passes CI_REPO_ROOT,
        # see bwm-ng 0.6.3 / ogg 1.1.1).
        self._patch_config_scripts()

        # E114: HMDFS + `umask 077 && mktemp -d` yields an unwritable
        # drwx--S--- temp dir — relax to 022 before configure runs.
        configure_path = os.path.join(src, "configure")
        if os.path.isfile(configure_path):
            replace_in_file(self, configure_path, "umask 077", "umask 022",
                            strict=False)

        autotools = Autotools(self)
        autotools.configure()
        # E074: parallel make hits the HMDFS jobserver fifo EPERM.
        autotools.make(args=["-j1"])
        # Upstream test suite: tests/Makefile.am wires `check:` to build and
        # run 9 check programs (4 decoder + 5 encoder) under the libtool
        # wrapper, linking the in-tree libraries with $(OGG_LIBS).
        autotools.make(target="check", args=["-j1"])

    def _config_script_pairs(self):
        root = self.source_folder
        return [
            (os.path.join(root, "config.guess"), os.path.join(root, "config.sub")),
        ]

    def _patch_config_scripts(self):
        """E007: HarmonyOS detection for config.guess/config.sub.

        Two layers:
          1. The official perl patcher (when CI_REPO_ROOT is set) adds the
             HarmonyOS system case, ohos-linux triplet and ohos* OS entry.
             On 2022-era scripts its __OHOS__ LIBC step does not match
             (theora's config.guess separates the #if from LIBC=android),
             so the python guess fallback below runs unconditionally —
             it is idempotent and only adds what is still missing.
          2. The kernel-OS whitelist fix (_patch_config_sub_kernel_whitelist)
             is needed because the perl patcher's "already present" guard
             mis-matches on 2022 config.sub (see that method's docstring).
        """
        pairs = [
            (cg, cs) for cg, cs in self._config_script_pairs()
            if os.path.isfile(cg) and os.path.isfile(cs)
        ]
        if not pairs:
            self.output.warning("E007: config.guess/config.sub not found")
            return

        repo = os.environ.get("CI_REPO_ROOT", "")
        script = os.path.join(repo, "scripts", "patch-autotools-ohos.pl") if repo else ""
        for cg, cs in pairs:
            if script and os.path.isfile(script):
                self.run(f'perl "{script}" "{cg}" "{cs}"', cwd=self.source_folder)
            else:
                self.output.info("E007: patch-autotools-ohos.pl not found, Python fallback")
            # Idempotent python pass: fills whatever the perl patcher
            # missed (__OHOS__ LIBC detection on 2022 config.guess) and
            # always applies the kernel-OS whitelist fix.
            self._patch_config_guess_python(cg)
            self._patch_config_sub_python(cs)
            self._patch_config_sub_kernel_whitelist(cs)

    def _patch_config_sub_kernel_whitelist(self, cs_path):
        """Add `linux-ohos` to the kernel-OS validation whitelist.

        2022-era config.sub validates `case $kernel-$os` against a whitelist
        (linux-gnu* | linux-dietlibc* | ... | linux-uclibc*). The official
        perl patcher misses this list on 2022 config.sub (its "already
        present" guard matches the basic_os=linux-ohos line inside the
        ohos-linux triplet instead), so aarch64-unknown-linux-ohos is
        rejected with "Kernel `linux' not known to work with OS `ohos'".
        """
        import re

        with open(cs_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        if "linux-gnu* | linux-dietlibc* | linux-android* | linux-newlib* \\" in content:
            pattern = (
                r"(linux-gnu\*\s*\|\s*linux-dietlibc\*\s*\|\s*linux-android\*"
                r"\s*\|\s*linux-newlib\*\s*\\)"
            )
            replacement = (
                r"\1\n\t\t   | linux-ohos* \\"
            )
            new_content, count = re.subn(pattern, replacement, content, count=1)
            if count > 0 and "linux-ohos*" not in content:
                with open(cs_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                self.output.info("E007: added linux-ohos* to kernel-OS whitelist")
                return
        # Older layout (single-line whitelist, e.g. 2018 config.sub)
        if re.search(r"linux-android\*\s*\|\s*linux-newlib\*", content) and "linux-ohos*" not in content:
            new_content, count = re.subn(
                r"(linux-android\*)",
                r"\1 | linux-ohos*",
                content, count=1,
            )
            if count > 0:
                with open(cs_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                self.output.info("E007: added linux-ohos* to kernel-OS whitelist (single-line)")

    def _patch_config_guess_python(self, cg_path):
        with open(cg_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        changed = False
        if "__OHOS__" not in content:
            old = "#if defined(__ANDROID__)\n    LIBC=android"
            new = (
                "#if defined(__ANDROID__)\n    LIBC=android\n"
                "#elif defined(__OHOS__)\n    LIBC=ohos"
            )
            if old in content:
                content = content.replace(old, new, 1)
                changed = True
        if "HarmonyOS" not in content:
            block = (
                '    *:HarmonyOS:*:*)\n'
                '\tcase "$UNAME_MACHINE" in\n'
                '\t    aarch64|arm64) MACHINE=aarch64 ;;\n'
                '\t    armv7*|armv8*) MACHINE=arm ;;\n'
                '\t    x86_64|amd64)  MACHINE=x86_64 ;;\n'
                '\t    i?86)          MACHINE=i686 ;;\n'
                '\t    *)            MACHINE="$UNAME_MACHINE" ;;\n'
                '\tesac\n'
                '\tGUESS=${MACHINE}-unknown-linux-ohos\n'
                '\t;;\n\n'
                '    *:NetBSD:*:*)'
            )
            if "    *:NetBSD:*:*)" in content:
                content = content.replace("    *:NetBSD:*:*)", block, 1)
                changed = True
        if changed:
            with open(cg_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.output.info("E007: patched config.guess for HarmonyOS")

    def _patch_config_sub_python(self, cs_path):
        import re

        with open(cs_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        changed = False
        if "ohos-linux" not in content:
            pattern = (
                r'(android-linux\)\s*\n\s*basic_machine=\$field1-unknown\s*\n'
                r'\s*basic_os=linux-android\s*\n\s*;;\s*\n)'
            )
            replacement = (
                r'\1\tohos-linux)\n\tbasic_machine=$field1-unknown\n'
                r'\tbasic_os=linux-ohos\n\t;;\n'
            )
            content, count = re.subn(pattern, replacement, content)
            if count > 0:
                changed = True
        if "ohos*" not in content:
            new_content = content.replace("gnu* | android*", "gnu* | android* | ohos*", 1)
            if new_content != content:
                content = new_content
                changed = True
        if "linux-ohos" not in content:
            content, count = re.subn(r'(linux-uclibc[\*/-]?\s*\))', r'\1| linux-ohos*)', content)
            if count > 0:
                changed = True
        if changed:
            with open(cs_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.output.info("E007: patched config.sub for HarmonyOS")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Conan 2 copy() has no delete= argument; remove libtool *.la wrappers
        # (same cleanup as ogg 1.1.1 / aribb24 / a52dec recipes).
        import glob
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Theora")

        dec = self.cpp_info.components["theoradec"]
        dec.libs = ["theoradec"]
        dec.set_property("cmake_target_name", "Theora::theoradec")
        dec.set_property("pkg_config_name", "theoradec")
        # theoradec public headers include <ogg/ogg.h> (ogg_packet type in
        # th_decode_packetin etc.), so the ogg requirement is transitive.
        dec.requires = ["ogg::ogg"]

        enc = self.cpp_info.components["theoraenc"]
        enc.libs = ["theoraenc"]
        enc.set_property("cmake_target_name", "Theora::theoraenc")
        enc.set_property("pkg_config_name", "theoraenc")
        # libtheoraenc links ogg (oggpackB_* writer family in encode.c etc.)
        enc.requires = ["theoradec", "ogg::ogg"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            enc.system_libs = ["m"]

        legacy = self.cpp_info.components["theora"]
        legacy.libs = ["theora"]
        legacy.set_property("cmake_target_name", "Theora::theora")
        legacy.set_property("pkg_config_name", "theora")
        # libtheora (pre-1.0 combined API) links ogg too.
        legacy.requires = ["ogg::ogg"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            legacy.system_libs = ["m"]
