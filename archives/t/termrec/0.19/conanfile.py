#!/usr/bin/env python3
"""Conan recipe — termrec 0.19 (Autotools terminal recorder/player suite).

termrec records and replays terminal sessions in the ttyrec/asciicast
formats: the termrec/termplay/termtime/termcat CLI tools plus the libtty
terminal library (public headers libtty/tty.h, libtty/ttyrec.h).

Build notes:
  * The GitHub tag archive ships no generated configure/Makefile.in —
    bootstrap with upstream autogen.sh (libtoolize --automake, aclocal,
    autoheader, automake --add-missing, autoconf). tool_requires provides
    automake+libtool; autoconf/m4 come from the SDK PATH (declaring
    autoconf would pull OHOS perl 5.42.2 whose XS .so conflicts with the
    SDK perl 5.42.0 interpreter used by autom4te — accel-config precedent).
  * HMDFS: config.status's ``(umask 077 && mktemp -d ...)`` creates
    drwx--S--- dirs the build user cannot write into — a PATH-scoped
    mktemp wrapper living only in the build folder (R6-clean) fixes
    configure (accel-config precedent).
  * config.guess does not know the OHOS uname → explicit
    --build/--host aarch64-unknown-linux-gnu (both set; AGENTS §12.1).
  * The compression stack comes from conan deps bzip2/zlib/liblzma/zstd, so
    the testsuite's .gz/.bz2/.xz/.zst cases execute instead of skipping.
    curl is deliberately not declared: http/ftp URL support degrades
    gracefully (upstream prints a WARN and builds without it).
  * libtty is installed as a real library (static by default, and the tools
    link it statically) so the installed binaries are self-contained on OHOS
    (musl ignores DT_RUNPATH; a shared libtty would need LD_LIBRARY_PATH
    everywhere). `-o termrec/*:shared=True` builds a shared libtty instead.
    The package type is `library` (not `application`): Conan 2 does not expose
    cpp_info to consumers of application packages, so a header library plus
    CLI tools must be declared as a library for consumers to get includes/libs.
  * Upstream tests: 16 AT_SETUP cases in tests/testsuite.at (Autotest,
    N_static = 16); executed for real via ``make check`` in build().
  * ``make install`` is replaced by explicit packaging: upstream install
    also builds man pages via pod2man, which clean CI PATHs do not have
    (POD=no leaves dist_man_MANS unbuilt), and installs more than this
    package needs (daemon/0.8.4 precedent).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get, replace_in_file)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class TermrecConan(ConanFile):
    name = "termrec"
    version = "0.19"
    description = "Record and replay terminal sessions (ttyrec/vt format)"
    license = "LGPL-3.0-only"
    homepage = "https://github.com/kilobyte/termrec"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("bzip2/1.0.8")
        self.requires("liblzma/5.8.1")
        self.requires("zlib/1.3.1.1")
        self.requires("zstd/1.5.7")

    def build_requirements(self):
        # Autotools bootstrap tools; see the module docstring for why
        # autoconf/m4 are intentionally NOT declared (SDK provides both).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"os={self.settings.os} is not supported")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _gnu_triplet(self, arch=None):
        arch = str(arch or self.settings.arch)
        triplets = {
            "aarch64": "aarch64-unknown-linux-gnu",
            "armv8": "aarch64-unknown-linux-gnu",
        }
        triplet = triplets.get(arch)
        if not triplet:
            raise ConanInvalidConfiguration(f"Unsupported arch: {arch}")
        return triplet

    def _create_mktemp_wrapper(self):
        """Build-only mktemp wrapper (never committed).

        config.status wraps its temp-dir creation in ``umask 077``; on HMDFS
        the resulting ``drwx--S---`` directory is not writable by the build
        user (measured: the directory is owned by the HMDFS uid, write access
        comes from the group bits, and 077 strips them), so config.status
        dies with "could not setup config files machinery". The wrapper
        emulates ``mktemp -d`` with a writable mode (umask 022 — measured
        writable) and forwards everything else to the real mktemp. It lives
        only in the build folder and touches nothing outside it.
        """
        wrapper_dir = os.path.join(self.build_folder, "mktemp-wrapper")
        os.makedirs(wrapper_dir, exist_ok=True)
        wrapper = os.path.join(wrapper_dir, "mktemp")
        if not os.path.exists(wrapper):
            with open(wrapper, "w", encoding="utf-8") as f:
                f.write("""#!/bin/sh
mode=""
for a in "$@"; do
  case "$a" in
    -d) mode="-d" ;;
  esac
done
if [ "$mode" != "-d" ]; then
  exec /usr/bin/mktemp "$@"
fi
dir=""
for a in "$@"; do
  case "$a" in
    -d) ;;
    *)  dir="$a" ;;
  esac
done
[ -n "$dir" ] || dir="./tmp.XXXXXX"
base=$(dirname "$dir")
pat=$(basename "$dir")
out=""
i=0
while [ -z "$out" ] && [ $i -lt 100 ]; do
  cand="$base/$(echo "$pat" | sed "s/XXXXXX/$$-$RANDOM/")"
  if (umask 022 && mkdir -p "$cand" 2>/dev/null); then out="$cand"; fi
  i=$((i+1))
done
if [ -n "$out" ]; then
  echo "$out"
  exit 0
fi
exit 1
""")
            os.chmod(wrapper, 0o755)
        return wrapper_dir

    def generate(self):
        VirtualBuildEnv(self).generate()
        # configure.ac probes compression support with AC_CHECK_HEADERS /
        # AC_CHECK_LIB (not pkg-config), so the dependency include/lib flags
        # must be in CPPFLAGS/LDFLAGS/LIBS — AutotoolsDeps provides exactly
        # that. Without it lzma/zstd are "not found" and termrec silently
        # loses .xz/.zst support (and the testsuite skips those cases).
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            f"--build={self._gnu_triplet()}",
            f"--host={self._gnu_triplet()}",
        ])
        # libtty is installed as a real library (static by default so the CLI
        # tools are self-contained on OHOS: musl ignores DT_RUNPATH, so a
        # shared libtty would need LD_LIBRARY_PATH everywhere).
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        env = tc.environment()
        env.prepend_path("PATH", self._create_mktemp_wrapper())
        # E386 (§12.38①): the profile points SHELL/CONFIG_SHELL at hnp bash,
        # whose getcwd fails inside HMDFS build dirs; autoconf re-execs itself
        # through CONFIG_SHELL, so configure dies with "working directory
        # cannot be determined". Route the autotools shell to /bin/sh.
        env.unset("CONFIG_SHELL")
        env.define("SHELL", "/bin/sh")
        # §12.38③: configure's conftest probes, the built tools and the
        # Autotest suite all execute freshly linked binaries that must resolve
        # dependency shared libraries at runtime (the zstd package ships
        # libzstd.so only). OHOS musl ignores DT_RUNPATH, so absolute dep
        # libdirs go into LD_LIBRARY_PATH.
        dep_libdirs = self._dependency_libdirs()
        if dep_libdirs:
            env.prepend_path("LD_LIBRARY_PATH", dep_libdirs)
        tc.generate(env=env)

    def _dependency_libdirs(self):
        libdirs = []
        for dep in self.dependencies.host.values():
            cpp = dep.cpp_info.aggregated_components()
            for libdir in cpp.libdirs:
                libdirs.append(libdir if os.path.isabs(libdir)
                               else os.path.join(dep.package_folder, libdir))
        return libdirs

    def build(self):
        apply_conandata_patches(self)
        # The tag archive has no generated configure: bootstrap it first.
        # /bin/sh is used explicitly (never a PATH-resolved bash — harmonybrew
        # exists only on the dev device, and hnp bash breaks on HMDFS getcwd,
        # §12.38①); autogen.sh is a POSIX sh script with `set -e`.
        if not os.path.exists(os.path.join(self.source_folder, "configure")):
            self.run("env -u CONFIG_SHELL SHELL=/bin/sh /bin/sh -e ./autogen.sh",
                     cwd=self.source_folder, env="conanbuild")
        if not os.path.exists(os.path.join(self.source_folder, "configure")):
            raise ConanException("autogen.sh did not produce configure")
        # E011/E114 (§12.1): config.status wraps its temp-dir creation in
        # ``umask 077``; on HMDFS the resulting directory is not writable by
        # the build user, so configure dies with "could not setup config files
        # machinery" / "can't create .../subs1.awk: Permission denied".
        # The sanctioned controlled fix relaxes the umask and keeps the real
        # temp-dir creation (build-time only; nothing is committed).
        replace_in_file(self, os.path.join(self.source_folder, "configure"),
                        "umask 077", "umask 022")
        autotools = Autotools(self)
        autotools.configure()
        # Out-of-source quirk: the .pod -> .1/.3 rules write doc/<page>
        # relative to the build folder, but automake does not create that
        # directory (doc/Makefile.am is `include`d into the top Makefile.am
        # rather than listed in SUBDIRS). Without it the man-page rule dies
        # with "/bin/sh: can't create doc/libtty.3: No such file or directory".
        os.makedirs(os.path.join(self.build_folder, "doc"), exist_ok=True)
        autotools.make(args=["-j1"])
        # Upstream Autotest suite — 16 AT_SETUP cases, must really run
        # (R51: "0 executed" is a hard fail regardless of reason).
        autotools.make(target="check")

    def package(self):
        # Tools land in the top build dir (subdir-objects include model);
        # libtool puts the library artefacts under .libs/.
        for tool in ("termrec", "termplay", "termtime", "termcat"):
            copy(self, tool, src=self.build_folder,
                 dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        if self.options.shared:
            copy(self, "libtty.so*", src=os.path.join(self.build_folder, ".libs"),
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        else:
            copy(self, "libtty.a", src=os.path.join(self.build_folder, ".libs"),
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "tty.h", src=os.path.join(self.source_folder, "libtty"),
             dst=os.path.join(self.package_folder, "include", "libtty"),
             keep_path=False)
        copy(self, "ttyrec.h", src=os.path.join(self.source_folder, "libtty"),
             dst=os.path.join(self.package_folder, "include", "libtty"),
             keep_path=False)
        # Man pages are generated by the .pod rules when pod2man is available
        # (they are not built by `make install` here since packaging is manual).
        copy(self, "*.1", src=os.path.join(self.build_folder, "doc"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)
        copy(self, "*.3", src=os.path.join(self.build_folder, "doc"),
             dst=os.path.join(self.package_folder, "share", "man", "man3"),
             keep_path=False)
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = ["include", "include/libtty"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["tty"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "termrec")
        self.cpp_info.set_property("cmake_target_name", "termrec::termrec")
