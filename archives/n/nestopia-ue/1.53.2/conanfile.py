#!/usr/bin/env python3
"""Conan recipe — nestopia-ue 1.53.2 (Nestopia UE NES emulator) for HarmonyOS PC.

nestopia-ue is the "Undead Edition" fork of the Nestopia NES/Famicom
emulator.  Upstream ships two frontends: win32 (DirectX) and a Linux
FLTK GUI (source/fltkui) that renders through OpenGL (libepoxy) and
plays audio through SDL2.

HarmonyOS PC adaptation strategy (same approach as far2l: clip the
un-adapted GUI, keep the core):
  - FLTK is not published in the registry and the OHOS image has no
    desktop GL (GLX/X11) stack, so the FLTK GUI frontend
    (fltkui.cpp/fltkui_archive/fltkui_cheats/fltkui_settings/
    videomanager/uiadapter) is replaced by a small headless driver
    (source/headless/nstheadless.cpp) that reuses the frontend-
    agnostic manager layer (JGManager/SettingManager/CheatManager +
    the JG core binding in jg.cpp).
  - The emulator core (source/core + source/nes_ntsc), the JG API
    binding and the manager layer are built unmodified.
  - SDL2 is still linked: the upstream manager layer uses SDL audio
    (audiomanager) — but audiomanager itself is GUI-loop coupled, so
    the headless driver drives Sound::Output directly instead.  SDL2
    remains a dependency of the compiled inputmanager/audiomanager
    translation units that are still part of the build (kept for
    source fidelity; they are not exercised by the headless main).
  - zlib: the core uses it for state save/load compression
    (NstZlib.cpp, NST_NO_ZLIB not defined).
  - libsamplerate: audiomanager resamples audio; kept as a dependency
    because audiomanager.cpp is still compiled.
  - libarchive: used by the FLTK archive chooser (fltkui_archive.cpp)
    which is NOT part of this build — dropped from the recipe.

Autotools notes (mirrors the abiword-plugin / argp-standalone recipe):
  - The release tarball ships no `configure` script, so build() runs
    `autoreconf -fi` first.
  - CI sandbox lacks automake/aclocal/libtoolize — pulled in via
    tool_requires.
  - --build/--host passed explicitly (aarch64-unknown-linux-ohos) so
    configure never runs the config.guess probe.
  - make runs with -j1 (E074: HMDFS jobserver fifo EPERM).
"""
import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


def _prepare_autotools_env():
    """The installed automake/aclocal/libtoolize hardcode absolute paths for
    autoconf/autom4te/sed that do not exist in this environment.  Point the
    env vars at whatever is actually on PATH.

    Additionally: the autoconf package pulls in the original perl/5.42.2
    build whose Cwd.so ships as mode 750 owned by the packaging user —
    dlopen fails with EACCES for every other account, which kills
    autom4te (and therefore autoreconf) before it starts.  The system
    perl under /data/service/hnp/bin (same 5.42.2) has a working Cwd.
    Override PERL to the system interpreter and strip the broken
    package's lib dirs from PERL5LIB so @INC resolution stays intact.
    """
    for tool, var in (("autoconf", "AUTOCONF"),
                      ("autoheader", "AUTOHEADER"),
                      ("autom4te", "AUTOM4TE"),
                      ("sed", "SED")):
        if os.environ.get(var):
            continue
        path = shutil.which(tool)
        if path:
            os.environ[var] = path

    sys_perl = shutil.which("perl")
    if sys_perl and sys_perl.startswith("/data/service/hnp"):
        # System perl (5.42.2, hnp) has a working Cwd module; point the
        # autotools wrappers at it.
        os.environ["PERL"] = sys_perl
        # automake's perl modules (Automake/Config.pm etc.) live in the
        # conan automake package — prepend them on PERL5LIB, dropping the
        # broken perl/5.42.2 package cache entries entirely.
        am_share = None
        for line in os.environ.get("PERL5LIB", "").split(os.pathsep):
            if "automake" in line and "/share/" in line and "/.conan2/p/" in line:
                am_share = line
                break
        if not am_share:
            # derive from the ACLOCAL/automake package if possible
            for cand in (shutil.which("aclocal"), shutil.which("automake")):
                if cand and "/.conan2/p/" in cand:
                    am_share = os.path.join(
                        os.path.dirname(os.path.dirname(os.path.dirname(cand))),
                        "share", "automake-1.18")
                    if os.path.isdir(am_share):
                        break
                    am_share = None
        if am_share and os.path.isdir(am_share):
            os.environ["PERL5LIB"] = am_share
        else:
            os.environ.pop("PERL5LIB", None)


class NestopiaUeConan(ConanFile):
    name = "nestopia-ue"
    version = "1.53.2"
    description = "Nestopia UE NES/Famicom emulator (headless core for HarmonyOS PC)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/rdanbrook/nestopia"
    url = "https://github.com/rdanbrook/nestopia"
    package_type = "application"
    topics = ("emulator", "nes", "famicom", "games")

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)
        # source/headless is new-file source, exported directly (not via
        # patch — toybox `patch --dry-run` on OHOS applies new-file patches
        # for real, polluting the pristine source tree; the abiword-plugin
        # recipes hit the same issue and solved it the same way).
        copy(self, "*",
             src=os.path.join(self.recipe_folder, "headless_src"),
             dst=os.path.join(self.export_sources_folder, "headless_src"))

    def requirements(self):
        # SDL2: the manager layer (audiomanager/inputmanager) links against
        # it; the packaged OHOS SDL2 (2.32.10) carries native OHAudio /
        # NativeWindow backends.
        self.requires("sdl2/2.32.10", transitive_headers=True)
        # zlib: core state save/load compression
        self.requires("zlib/1.3.1")
        # libsamplerate: audiomanager audio resampling
        self.requires("libsamplerate/0.2.2")

    def build_requirements(self):
        # The release tarball ships no `configure`: build() runs
        # `autoreconf -fi`.  CI/build hosts lack automake/aclocal/libtoolize
        # (only the autoconf suite lives in /data/service/hnp/bin).
        # perl is pulled in transitively by autoconf (original 5.42.2 build
        # ships Cwd.so mode-750 owned by the packaging user — broken for
        # other accounts); the fixed 5.42.2.3 is forced via override so the
        # toolchain resolves against a working interpreter.
        self.tool_requires("automake/1.18")
        self.tool_requires("autoconf/2.72")
        self.tool_requires("autoconf-archive/2024.10.16")
        self.tool_requires("m4/1.4.19")
        self.requires("perl/5.42.2.3", override=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "nestopia-ue only supports Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        # Place the headless driver source into the patched tree.
        # export_sources (headless_src/) are auto-merged by conan into
        # the source folder root, so copy from there.
        exported = os.path.join(self.source_folder, "headless_src")
        recipe = os.path.join(self.recipe_folder, "headless_src")
        src = exported if os.path.isdir(exported) else recipe
        if not os.path.isdir(src):
            raise ConanInvalidConfiguration(
                "headless_src/ missing from recipe folder")
        copy(self, "*", src=src,
             dst=os.path.join(self.source_folder, "source", "headless"))
        # vendor pkg.m4 into the source tree: configure.ac uses
        # PKG_CHECK_MODULES, and the conan automake package's aclocal
        # wrapper replaces the system aclocal dir (--system-acdir), which
        # hides the hnp pkg-config's pkg.m4. aclocal always scans the
        # source-tree m4/ directory (AC_CONFIG_MACRO_DIRS equivalent),
        # so dropping pkg.m4 there makes the macro resolvable everywhere
        # (local build and CI alike).
        m4_dst = os.path.join(self.source_folder, "m4")
        os.makedirs(m4_dst, exist_ok=True)
        pkg_m4 = "/data/service/hnp/pkg-config.org/pkg-config_0.29.2/share/aclocal/pkg.m4"
        if os.path.isfile(pkg_m4):
            copy(self, "pkg.m4", src=os.path.dirname(pkg_m4), dst=m4_dst)
        else:
            raise ConanInvalidConfiguration("pkg.m4 not found at " + pkg_m4)

    def generate(self):
        # PkgConfigDeps: configure.ac uses PKG_CHECK_MODULES for
        # zlib/libarchive/samplerate/sdl2 — generate the .pc files for
        # the conan requirements and put pkg-config on the discovery path.
        PkgConfigDeps(self).generate()
        _prepare_autotools_env()
        # aclocal needs pkg.m4 (PKG_CHECK_MODULES) plus the autoconf-archive
        # macros (AX_*). The system pkg-config ships pkg.m4; the
        # autoconf-archive tool package ships the AX_* set. Wire both into
        # ACLOCAL_PATH so autoreconf can expand every macro. Note: append
        # buildenv_info BEFORE any VirtualBuildEnv generation so the env
        # files include it.
        for m4dir in (
            "/data/service/hnp/pkg-config.org/pkg-config_0.29.2/share/aclocal",
        ):
            if os.path.isdir(m4dir):
                self.buildenv_info.append_path("ACLOCAL_PATH", m4dir)
        # autoconf-archive tool package: locate its share/aclocal via the
        # conan cache (it is a build tool, its m4 files are in the package)
        archive_pkg = None
        try:
            dep = self.dependencies.get("autoconf-archive")
            if dep is not None and dep.package_folder:
                archive_pkg = dep.package_folder
        except Exception:
            pass
        if not archive_pkg:
            # fall back to the conan cache layout
            cache = Path.home() / ".conan2" / "p"
            if cache.is_dir():
                for pkg in sorted(cache.iterdir(), reverse=True):
                    share = pkg / "p" / "share" / "aclocal"
                    if (share / "ax_cxx_compile_stdcxx.m4").is_file():
                        archive_pkg = str(pkg / "p")
                        break
        if archive_pkg:
            for sub in ("share/aclocal", "aclocal"):
                m4dir = os.path.join(archive_pkg, sub)
                if os.path.isdir(m4dir):
                    self.buildenv_info.append_path("ACLOCAL_PATH", m4dir)
                    break
        VirtualBuildEnv(self).generate()

        tc = AutotoolsToolchain(self)
        # OHOS 交叉编译：configure 尝试运行编译出的 conftest 会因
        # libc++_shared.so 无法加载而失败（"cannot run C++ compiled
        # programs"）。用 cache 预设绕过运行测试（libcupsfilters 先例）：
        # --build/--host 同为 aarch64-unknown-linux-ohos 时 config.guess
        # 不会探测，ac_cv_* 预设让编译检查直接通过。
        tc.configure_args.append("ac_cv_prog_cxx_c_o=yes")
        tc.configure_args.append("cross_compiling=yes")
        tc.configure_args.append("ac_cv_func_fork=yes")
        tc.configure_args.append("ac_cv_func_vfork=yes")
        tc.configure_args.append("ac_cv_func_setenv=yes")
        tc.configure_args.append("ac_cv_func_getcwd=yes")
        # AX_CXX_COMPILE_STDCXX 的运行时探测同样被 cache 预设跳过
        tc.configure_args.append("ax_cv_cxx_compile_cxx17=yes")
        tc.configure_args.append("ax_cv_cxx_compile_cxx11=yes")
        # config.guess cannot identify HarmonyOS — pass the triplet
        # explicitly (config.sub understands *-linux-ohos).
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()

    def _write_autoreconf_env(self):
        """Write a supplementary env file for the autoreconf bootstrap.

        self.run(..., env="conanbuild") sources conanbuildenv, whose
        PERL5LIB (contributed by the perl/5.42.2 tool package) points at
        Cwd.so files shipped mode-750 owned by the packaging user — the
        hnp perl interpreter picks that Cwd.pm up and dies with EACCES on
        dlopen.  The written file is sourced *after* conanbuildenv
        (env=["conanbuild", "autoreconf_perl_fix.sh"]) so it wins:
        PERL points at the system interpreter and PERL5LIB is rewritten
        to only the automake perl modules (Automake/Config.pm), which is
        the only thing aclocal needs beyond core perl.
        """
        am_share = self._find_automake_share()
        if not am_share:
            raise ConanInvalidConfiguration(
                "cannot locate the conan automake package's share dir "
                "(Automake/Config.pm) — autoreconf would fail")
        env = Environment()
        env.define("PERL", shutil.which("perl") or "perl")
        env.define("PERL5LIB", am_share)

        path = os.path.join(self.generators_folder, "autoreconf_perl_fix.sh")
        with open(path, "w", encoding="utf-8") as f:
            f.write("# generated by conanfile.py: perl env fix for autoreconf\n")
            for k, v in env.vars(self).items():
                if v is None:
                    f.write(f"unset {k}\n")
                else:
                    f.write(f'export {k}="{v}"\n')
        return "autoreconf_perl_fix.sh"

    def _find_automake_share(self):
        """Locate <automake-pkg>/share/automake-1.18 (contains both the
        Automake perl modules and the aclocal m4 dir).  Resolution order:
        1. the conan dependency graph (works identically on the local
           build host and the CI sandbox — no PATH guessing)
        2. the caller's PERL5LIB (already-sourced conanbuildenv)
        3. a conan cache scan honoring CONAN_HOME (CI uses
           ~/.cache/conan2, the local host ~/.conan2)
        """
        # 1) dependency graph
        try:
            dep = self.dependencies.get("automake")
            if dep is not None and dep.package_folder:
                share = os.path.join(dep.package_folder, "share")
                if os.path.isdir(share):
                    for entry in sorted(os.listdir(share)):
                        if entry.startswith("automake-") and os.path.isdir(
                                os.path.join(share, entry)):
                            return os.path.join(share, entry)
        except Exception:
            pass
        # 2) already-sourced PERL5LIB
        for line in os.environ.get("PERL5LIB", "").split(os.pathsep):
            if "share/automake-" in line and "/conan2/" in line:
                return line
        # 3) conan cache scan (CONAN_HOME aware)
        homes = []
        if os.environ.get("CONAN_HOME"):
            homes.append(Path(os.environ["CONAN_HOME"]))
        homes.append(Path.home() / ".conan2")
        homes.append(Path.home() / ".cache" / "conan2")
        for cache in homes:
            pkgdir = cache / "p"
            if not pkgdir.is_dir():
                continue
            for pkg in sorted(pkgdir.iterdir(), reverse=True):
                share = pkg / "p" / "share"
                if not (pkg / "p" / "bin" / "aclocal").exists():
                    continue
                if not share.is_dir():
                    continue
                for entry in sorted(share.iterdir()):
                    if entry.name.startswith("automake-") and entry.is_dir():
                        return str(entry)
        return None

    def build(self):
        _prepare_autotools_env()
        # Bootstrap configure from configure.ac (tarball ships none).
        # The supplementary env file rewrites PERL5LIB *after*
        # conanbuildenv has been sourced — see _write_autoreconf_env.
        fix = self._write_autoreconf_env()
        self.run("autoreconf -fi", cwd=self.source_folder,
                 env=["conanbuild", fix])
        autotools = Autotools(self)
        autotools.configure()
        # E074: parallel make hits HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Data files needed at runtime by the core (NstDatabase.xml is
        # looked up in NST_DATADIR)
        copy(self, "NstDatabase.xml", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "nestopia"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYRIGHT", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
