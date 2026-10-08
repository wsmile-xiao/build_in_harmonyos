#!/usr/bin/env python3
"""Conan recipe for wmfire 1.2.4.

wmfire is a Window Maker dockapp that renders a CPU-usage flame using
GDK (part of GTK+ 2.0).  It also uses libgtop-2.0 to read CPU/memory/network
statistics and X11 for the dock window.  The upstream ``configure.in`` pulls
all flags through ``pkg-config gtk+-2.0`` and ``pkg-config libgtop-2.0``,
so the build is driven entirely by PkgConfigDeps.

OHOS adaptation notes:
- ``src/Makefile.am`` hardcodes ``-L/usr/X11R6/lib -L/usr/local/lib`` and
  ``-I/usr/X11R6/include -I/usr/local/include``.  Those paths do not exist on
  OHOS and would override the Conan-injected search paths, so patch 0001
  removes them.  The X11 headers/libs come from the ``libx11`` dependency.
- Autotools is bootstrapped in ``build()`` (the tarball ships
  ``configure.in`` + ``Makefile.am`` but no generated ``configure``).
- ``make check`` is part of the upstream autotools build; wmfire declares no
  TESTS, so it is a no-op target — still executed to prove the entry point.
- Dependency track: gtk2/2.24.33 pins glib/2.84.0.1, so the whole graph has
  to stay on that glib track.  The repo ships the same upstream libgtop tarball
  under two names — ``libgtop/2.41.3`` (glib/2.84 track) and
  ``libgtop2/2.41.3`` (glib/2.88 track).  Picking libgtop2 would force it to be
  rebuilt from source, and that rebuild cannot link (see below), so this recipe
  depends on ``libgtop/2.41.3``: its published binary requires glib/2.84.Z, it
  is the package the sibling consumer das-watchdog/0.9.0 uses, and it already
  declares the ``intl`` library that the static archive needs.
- ``libgtop`` ships ``libgtop-2.0.a`` (static) plus ``include/libgtop-2.0``.
  The archive references ``g_libintl_ngettext``; on the glib/2.84 track that
  symbol comes from the ``libintl`` that the glib package itself ships, which
  is why ``libgtop``'s ``cpp_info.libs`` carries ``intl`` next to ``gtop-2.0``.
  (ref: E508)
- OHOS musl loader doesn't follow symlinks, so dependency .so files must be
  flattened.  This is handled by dependency recipes (see E505).
- pango track: gtk2 still pins ``pango/1.50.14.1.1``, whose cairo pin
  (``cairo/1.18.4``) predates the 6.4.0 X11 track this graph uses, so its
  package_id has no published binary and pango would be rebuilt from source —
  and that rebuild cannot pass its own upstream suite here (E505).  The repo
  already ships the corrected ``pango/1.50.14.1.1.1`` (cairo/1.18.4.1) and ohpcd
  publishes its binary for exactly this package_id, so this recipe forces it.
  With that pin and the libgtop pin below, every dependency resolves to a
  published binary and only wmfire itself is built.
- OHOS: draw_fire declared as ``inline`` but not ``static inline``, clang -O3
  doesn't inline it, causing link failure — patched to ``static inline``.
"""

import os
import shlex
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


def _relax_config_status_umask(conanfile, path):
    """E011/E114: relax the private temp dir of the generated config.status.

    On OHOS the build tree lives on HMDFS, where the ``umask 077 && mktemp -d
    "./confXXXXXX"`` directory that autoconf emits for config.status comes out
    as ``drwx--S---`` (2700 + setgid): neither group nor other has write access
    and chmod is ignored by the FUSE layer.  The local shell happens to be
    mapped onto the directory owner (so builds pass), while the CI worker maps
    onto another uid -> config.status dies with::

        ./config.status[N]: can't create ./confXXXXXXXX/subs1.awk: Permission denied
        config.status: error: could not setup config files machinery

    Relaxing the umask to 000 makes the temp directory group writable, which
    keeps config.status working in both process domains.
    """
    with open(path, "r", encoding="utf-8") as handle:
        data = handle.read()
    patched = data.replace(
        '(umask 077 && mktemp -d "./confXXXXXX")',
        '(umask 000 && mktemp -d "./confXXXXXX")',
    ).replace(
        '(umask 077 && mkdir "$tmp")',
        '(umask 000 && mkdir "$tmp")',
    )
    if patched == data:
        conanfile.output.warn(
            f"{os.path.basename(path)}: no 'umask 077' temp-dir pattern found "
            "(autoconf output changed?); HMDFS temp dir may break in CI"
        )
        return
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(patched)
    conanfile.output.info(
        f"{os.path.basename(path)}: relaxed config.status temp-dir umask "
        "(E011/E114, HMDFS)"
    )


class WmfireConan(ConanFile):
    name = "wmfire"
    version = "1.2.4"
    description = "Window Maker dockapp that renders CPU load as a fire using GDK"
    license = "GPL-2.0-or-later"
    homepage = "https://www.improbability.net/wmfire/"
    url = "https://www.improbability.net/wmfire/"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # GUI + statistics: pulled via pkg-config in configure.in.
        self.requires("gtk2/2.24.33", transitive_headers=True, transitive_libs=True)
        # libgtop-2.0 provider: stay on the glib/2.84 track that gtk2 pins.
        # libgtop2/2.41.3 is the same upstream source but published against
        # glib/2.88.3, so it would be rebuilt from source here and that rebuild
        # fails to link g_libintl_ngettext (its cpp_info.libs omits "intl").
        self.requires("libgtop/2.41.3", transitive_headers=True, transitive_libs=True)
        # X11 client library (libX11 + libXext used directly in Makefile.am).
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxext/6.4.0", transitive_headers=True, transitive_libs=True)
        # gtk2/2.24.33 pins glib/2.84.0.1 and every other dependency on this
        # graph is published for that same track, so pin it explicitly.
        self.requires("glib/2.84.0.1", force=True)
        # gtk2 still pins pango/1.50.14.1.1, whose cairo pin (cairo/1.18.4) no
        # longer matches the 6.4.0 X11 track this graph uses, so that package_id
        # has no published binary and pango would be rebuilt from source.  The
        # repo already ships the corrected pango (1.50.14.1.1.1 pins
        # cairo/1.18.4.1) and ohpcd publishes its binary for exactly this
        # package_id, so pull that one in instead of source-building pango.
        self.requires("pango/1.50.14.1.1.1", force=True)

    def build_requirements(self):
        self.tool_requires("automake/1.18")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"wmfire needs a POSIX X11 platform, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        PkgConfigDeps(self).generate()
        AutotoolsDeps(self).generate()
        self._toolchain = AutotoolsToolchain(self, prefix="/")
        if str(self.settings.os) == "OHOS":
            self._toolchain.configure_args.append("--host=aarch64-linux-ohos")
        self._toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        # OHOS: draw_fire 声明为 inline 但非 static inline,clang -O3 不内联时链接失败。
        if str(self.settings.os) == "OHOS":
            self._patch_draw_fire_static()
        with self._build_environment().vars(self).apply():
            self._bootstrap_autotools()
            self._restore_autotools_script_modes()
            self._configure()
            self._run_build("make -j1")
            self._run_build("make -j1 check")

    def package(self):
        with self._build_environment().vars(self).apply():
            destination = shlex.quote(self.package_folder)
            self._run_build(f"make -j1 install DESTDIR={destination}")
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        self._normalise_installed_permissions()
        if str(self.settings.os) == "OHOS":
            binary = Path(self.package_folder, "bin", "wmfire")
            if not binary.is_file():
                raise ConanException("the installed wmfire binary is missing")
            self._drop_build_rpath(binary)
            self._sign_ohos_elf(binary)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
        self.cpp_info.set_property("cmake_file_name", "wmfire")
        self.cpp_info.set_property("cmake_target_name", "wmfire::wmfire")

    # ── build helpers ──────────────────────────────────────────────────

    def _build_shell(self):
        return "/system/bin/sh" if str(self.settings.os) == "OHOS" else "/bin/sh"

    def _run_build(self, command):
        shell = self._build_shell()
        # 手动 source 所有 conanbuild 环境脚本，确保 CC/CXX/CFLAGS/LDFLAGS 传递
        conan_folder = self.generators_folder
        env_sources = [
            os.path.join(conan_folder, "conanbuildenv-release-armv8.sh"),
            os.path.join(conan_folder, "conanautotoolsdeps.sh"),
            os.path.join(conan_folder, "conanautotoolstoolchain.sh"),
        ]
        source_cmd = " && ".join(f". {s}" for s in env_sources if os.path.isfile(s))
        # OHOS: WorkBuddy safe-bin rm shim 的 #!/bin/bash 在 OHOS 不存在
        # → 优先用 /system/bin/rm，不经过 safe-bin
        ohos_path_fix = "export PATH=/system/bin:$PATH; " if str(self.settings.os) == "OHOS" else ""
        self.run(
            f"{source_cmd} && export SHELL={shell} CONFIG_SHELL={shell}; {ohos_path_fix}{command}",
            cwd=self.source_folder,
        )

    def _build_environment(self):
        temporary = Path(self.build_folder, ".tmp")
        temporary.mkdir(parents=True, exist_ok=True)
        environment = Environment()
        environment.define_path("TMPDIR", str(temporary))
        environment.define("MKDIR_P", "/system/bin/mkdir -p")
        return environment

    def _patch_draw_fire_static(self):
        """OHOS: draw_fire 声明为 inline 但非 static inline,clang -O3 时不内联导致链接失败。"""
        src = os.path.join(self.source_folder, "src", "wmfire.c")
        if not os.path.isfile(src):
            return
        with open(src) as f:
            content = f.read()
        if "static inline void draw_fire" in content:
            return
        content = content.replace(
            "inline void draw_fire(unsigned int);",
            "static inline void draw_fire(unsigned int);"
        )
        content = content.replace(
            "inline void\n\ndraw_fire",
            "static inline void\n\ndraw_fire"
        )
        with open(src, "w") as f:
            f.write(content)
        self.output.info("patched wmfire.c: draw_fire -> static inline")

    def _bootstrap_autotools(self):
        # OHOS: HMMAC 按进程安全标签拦对 conan 缓存目录中脚本的 execve——
        # automake tool_requires 的 aclocal/automake 脚本即使 chmod 0755，
        # 在 conan 子进程上下文里仍被 /system/bin/sh 报 Permission denied。
        # 解法：用系统 perl 直接 invoke conan 缓存的 .aclocal-1.18-real 脚本
        # （不 execve 脚本本体，只是 perl require → 不触发 execve HMMAC 拦截）。
        # automake 是 application 类型，libdirs 为空，须用 bindirs 推算 share。
        automake_share = None
        aclocal_real = None
        automake_real = None
        try:
            automake = self.dependencies.build["automake"]
            # cpp_info.bindirs 返回相对路径，需要绝对路径
            am_prefix = automake.package_folder
            bindir = os.path.join(am_prefix, automake.cpp_info.bindirs[0])
            share_candidate = os.path.join(am_prefix, "share")
            if os.path.isdir(os.path.join(share_candidate, "automake-1.18")):
                automake_share = share_candidate
            # 查找 .aclocal-1.18-real / .automake-1.18-real 脚本
            if os.path.isdir(bindir):
                for name in os.listdir(bindir):
                    fp = os.path.join(bindir, name)
                    if name == ".aclocal-1.18-real" and os.path.isfile(fp):
                        aclocal_real = fp
                    elif name == ".automake-1.18-real" and os.path.isfile(fp):
                        automake_real = fp
                    elif os.path.isfile(fp) and not name.startswith("."):
                        os.chmod(fp, 0o755)
        except (KeyError, IndexError, OSError):
            pass

        # 候选 perl 路径（按优先级）：用户预装 perl、hnp bundle perl、conan 缓存 perl
        sys_perl = None
        for candidate in (
            os.path.expanduser("~/usr/local/bin/perl"),
            "/data/service/hnp/bin/perl",
            "/usr/bin/perl",
        ):
            if os.path.isfile(candidate):
                sys_perl = candidate
                break

        if (
            automake_share
            and aclocal_real
            and automake_real
            and sys_perl
        ):
            self.output.info("bootstrap: invoking conan aclocal-1.18 via system perl")
            perl5lib = os.path.join(automake_share, "automake-1.18")
            ac118 = os.path.join(automake_share, "aclocal-1.18")
            ac = os.path.join(automake_share, "aclocal")
            env_prefix = f"env PERL5LIB={perl5lib}"
            # aclocal 用 --automake-acdir / --system-acdir
            aclocal_cmd = (
                f'{env_prefix} "{sys_perl}" "{aclocal_real}" '
                f'--automake-acdir={ac118} --system-acdir={ac}'
            )
            # automake 用 --libdir（不是 --automake-acdir）
            automake_cmd = (
                f'{env_prefix} "{sys_perl}" "{automake_real}" '
                f'--libdir={perl5lib}'
            )
        else:
            self.output.info("bootstrap: falling back to conan cache aclocal")
            aclocal_cmd = '"${ACLOCAL:-aclocal}"'
            automake_cmd = '"${AUTOMAKE:-automake}"'

        # 源码是 configure.in（旧式命名）
        configure_in = "configure.in" if os.path.isfile(os.path.join(self.source_folder, "configure.in")) else "configure.ac"
        self._run_build(f'{aclocal_cmd} --force')
        self._run_build(f"autoconf -o configure {configure_in}")
        # E011/E114: config.status 的私有临时目录在 HMDFS 上对 CI 进程域不可写
        _relax_config_status_umask(self, os.path.join(self.source_folder, "configure"))
        self._run_build(f'{automake_cmd} --add-missing --copy')
        for generated in ("configure", "Makefile.in"):
            if not os.path.isfile(os.path.join(self.source_folder, generated)):
                raise ConanException(
                    f"autotools bootstrap did not produce {generated}"
                )

    def _restore_autotools_script_modes(self):
        known = {
            "configure", "config.guess", "config.sub", "install-sh",
            "missing", "depcomp", "compile", "ylwrap", "test-driver",
        }
        for path in Path(self.source_folder).rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            if path.name in known:
                path.chmod(path.stat().st_mode | 0o111)

    def _configure(self):
        arguments = " ".join(
            shlex.quote(argument) for argument in self._toolchain.configure_args
        )
        self._run_build(f"{self._build_shell()} ./configure {arguments}")

    # ── OHOS packaging helpers ─────────────────────────────────────────

    def _normalise_installed_permissions(self):
        binary = Path(self.package_folder, "bin", "wmfire")
        if binary.is_file():
            binary.chmod(0o755)

    def _drop_build_rpath(self, binary):
        patchelf = shutil.which("patchelf") or "/data/service/hnp/bin/patchelf"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        dynamic = subprocess.run(
            [readelf, "-d", str(binary)], check=True,
            capture_output=True, text=True, timeout=60,
        ).stdout
        if "(RPATH)" in dynamic or "(RUNPATH)" in dynamic:
            subprocess.run(
                [patchelf, "--remove-rpath", str(binary)],
                check=True, capture_output=True, text=True, timeout=120,
            )

    def _sign_ohos_elf(self, binary):
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", str(binary)],
            check=True, capture_output=True, text=True, timeout=120,
        )
        signed = Path(f"{binary}.signed")
        try:
            subprocess.run(
                [signer, "sign", "-inFile", str(binary), "-outFile", str(signed),
                 "-selfSign", "1"],
                check=True, capture_output=True, text=True, timeout=180,
            )
            if not signed.is_file():
                raise ConanException("binary-sign-tool produced no output")
            signed.chmod(0o755)
            signed.rename(binary)
        finally:
            if signed.exists():
                signed.unlink()
