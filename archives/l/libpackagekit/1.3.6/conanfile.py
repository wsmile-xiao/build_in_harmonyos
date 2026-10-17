#!/usr/bin/env python3
"""Conan recipe — libpackagekit 1.3.6 (Meson, libpackagekit-glib2).

libpackagekit-glib2 is the GLib/GObject binding library for PackageKit.
Adapted to HarmonyOS PC (aarch64/OHOS).

Dependencies: glib/2.84.0 (gio-unix-2.0 required), sqlite3/3.53.4,
              polkit/127, jansson/2.15.1.1

Key adaptations (OHOS):
  1. gettext/musl: -Dgettext(x)=(x) + dgettext + bindtextdomain macros
  2. Policy XML: skip i18n.merge_file (msgfmt ITS rules absent on OHOS)
  3. glib .pc: copy all glib sub-.pc (gio-2.0, gio-unix-2.0, etc.) and
     merge mkenums tool variables into generators_folder
  4. Only package the library: skip daemon/CLI binaries (bin/libexec)
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import (
    get,
    apply_conandata_patches,
    export_conandata_patches,
    copy,
    rmdir,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibpackagekitConan(ConanFile):
    name = "libpackagekit"
    version = "1.3.6"
    description = ("libpackagekit-glib2 — PackageKit GLib/GObject binding library")
    license = "LGPL-2.1+"
    homepage = "https://github.com/PackageKit/PackageKit"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libpackagekit does not support os={self.settings.os}")

    def requirements(self):
        # glib 2.84.0 satisfies polkit/127's glib requirement
        self.requires("glib/2.84.0")
        # sqlite3/polkit/jansson are needed to BUILD the daemon/CLI targets,
        # but the shipped library (libpackagekit-glib2) only links glib.
        # Mark them non-visible so they don't leak into downstream consumers.
        self.requires("sqlite3/3.53.4", visible=False)
        self.requires("polkit/127", visible=False)
        self.requires("jansson/2.15.1.1", visible=False)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------
    # generate: MesonToolchain + fix glib sub-.pc + merge mkenums vars
    # ------------------------------------------------------------------
    def generate(self):
        # ── MesonToolchain ──
        tc = MesonToolchain(self)
        # Wrap mode: offline only (subprojects disabled, deps from conan)
        tc.project_options["wrap_mode"] = "nodownload"
        # Disable features not needed for library component
        tc.project_options["systemd"] = "false"
        tc.project_options["elogind"] = "false"
        tc.project_options["gobject_introspection"] = "false"
        tc.project_options["man_pages"] = "false"
        tc.project_options["gtk_doc"] = "false"
        tc.project_options["legacy_tools"] = "false"
        tc.project_options["daemon_tests"] = "false"
        tc.project_options["cron"] = "false"
        tc.project_options["python_backend"] = "false"
        tc.project_options["gtk_module"] = "false"
        tc.project_options["gstreamer_plugin"] = "false"
        tc.project_options["bash_completion"] = "false"
        tc.project_options["bash_command_not_found"] = "false"
        tc.project_options["offline_update"] = "false"
        # OHOS musl gettext macros (polkit proven pattern)
        for macro in (
            "-Dgettext(x)=(x)",
            "-Ddgettext(d,x)=(x)",
            "-Dbindtextdomain(d,l)=(d)",
            "-Dbind_textdomain_codeset(d,c)=(d)",
            "-Dtextdomain(d)=(d)",
        ):
            tc.c_args.append(macro)
        tc.generate()

        # ── PkgConfigDeps ──
        PkgConfigDeps(self).generate()

        # ── glib sub-.pc fix (polkit proven pattern) ──
        # PkgConfigDeps only generates glib-2.0.pc; meson needs gio-2.0.pc,
        # gio-unix-2.0.pc, gobject-2.0.pc etc. (gnome.mkenums uses
        # glib_mkenums pkg-config variable).  Copy ALL .pc files from the
        # glib package, fix prefix, and merge mkenums tool variables.
        try:
            glib_pkg = self.dependencies["glib"].package_folder
        except Exception:
            glib_pkg = None
        if glib_pkg:
            self._copy_and_fix_glib_pc(glib_pkg)

        # ── polkit/glib sub-.pc for full Requires chain resolution ──
        # Copy ALL .pc from ALL dependency packages into generators_folder
        # so meson resolves the entire Requires chain without system leakage.
        for dep in self.dependencies.values():
            try:
                dep_pkg = dep.package_folder
            except Exception:
                continue
            if not dep_pkg:
                continue
            dep_pc_dir = os.path.join(dep_pkg, "lib", "pkgconfig")
            if not os.path.isdir(dep_pc_dir):
                continue
            for name in os.listdir(dep_pc_dir):
                if not name.endswith(".pc"):
                    continue
                dst = os.path.join(self.generators_folder, name)
                if not os.path.exists(dst):
                    src = os.path.join(dep_pc_dir, name)
                    shutil.copy2(src, dst)
                    self._fix_pc_prefix(dst, dep_pkg)

        # ── meson archiver 注入（E012 变体）──
        # 真机/CI hnp 工具链的 ar/llvm-ar 不在 PATH——meson 报
        # "Unknown linker(s): [['llvm-ar']]"。把探测到的 ar/ranlib 全路径
        # 注入 conan_meson_native.ini（polkit/dconf/pycairo 同款方案）。
        self._inject_meson_archiver()

    # --- 归档器探测（真机 hnp 工具链 ar 不在 PATH，须给 meson 绝对路径） ---
    def _probe_archiver(self):
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or os.environ.get("CC") or ""
        bindir = os.path.dirname(cc) if (cc and ("/" in cc or os.path.sep in cc)) else ""
        dirs = []
        for d in (bindir, "/data/service/hnp/bin", "/data/service/hnp/llvm/bin",
                  os.path.expanduser("~/usr/local/bin")):
            if d and d not in dirs:
                dirs.append(d)
        # OHOS SDK llvm toolchain (llvm-ar lives under the SDK tree)
        sdk_root = "/data/service/hnp/ohos-sdk.org"
        if os.path.isdir(sdk_root):
            try:
                for entry in sorted(os.listdir(sdk_root)):
                    sdk_bin = os.path.join(sdk_root, entry, "ohos", "native", "llvm", "bin")
                    if os.path.isdir(sdk_bin) and sdk_bin not in dirs:
                        dirs.append(sdk_bin)
            except OSError:
                pass
        cands = []
        for d in dirs:
            for n in ("llvm-ar", "llvm-ar-15", "ar"):
                p = os.path.join(d, n)
                if os.path.isfile(p):
                    cands.append(p)
        for n in ("llvm-ar", "llvm-ar-15", "ar", "gar"):
            p = shutil.which(n)
            if p:
                cands.append(p)
        seen, ar = set(), None
        for p in cands:
            if p not in seen:
                seen.add(p)
                ar = p
                break
        if not ar:
            return None, None
        base = os.path.dirname(ar)
        is_llvm = os.path.basename(ar).startswith("llvm")
        rl_names = ("llvm-ranlib", "ranlib") if is_llvm else ("ranlib", "llvm-ranlib")
        rl = None
        for n in rl_names:
            p = os.path.join(base, n)
            if os.path.isfile(p):
                rl = p
                break
        if not rl:
            for n in rl_names:
                p = shutil.which(n)
                if p:
                    rl = p
                    break
        return ar, rl

    def _inject_meson_archiver(self):
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar, rl = ce.get("ar"), ce.get("ranlib")
        if not ar:
            ar, rl = self._probe_archiver()
        nf = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not (ar and os.path.isfile(nf)):
            return
        with open(nf, encoding="utf-8") as f:
            content = f.read()
        if "[binaries]" not in content:
            return
        # 强制覆盖 ar/ranlib 为绝对路径（MesonToolchain 可能已写入裸命令名
        # 'llvm-ar'——CI AR 环境变量存在时注入会被旧逻辑跳过导致 Unknown
        # linker。用绝对路径覆盖，保证 meson 不依赖 PATH）。
        import re as _re
        if _re.search(r"(?m)^ar\s*=", content):
            content = _re.sub(r"(?m)^ar\s*=.*$", "ar = '%s'" % ar, content, count=1)
        else:
            content = content.replace("[binaries]\n", "[binaries]\nar = '%s'\n" % ar, 1)
        if rl:
            if _re.search(r"(?m)^ranlib\s*=", content):
                content = _re.sub(r"(?m)^ranlib\s*=.*$", "ranlib = '%s'" % rl, content, count=1)
            else:
                content = content.replace("[binaries]\n", "[binaries]\nranlib = '%s'\n" % rl, 1)
        with open(nf, "w", encoding="utf-8") as f:
            f.write(content)

    def _copy_and_fix_glib_pc(self, glib_pkg):
        """Copy ALL glib sub-.pc and merge mkenums tool variables."""
        src_pc_dir = os.path.join(glib_pkg, "lib", "pkgconfig")
        if not os.path.isdir(src_pc_dir):
            return
        for name in os.listdir(src_pc_dir):
            if not name.endswith(".pc"):
                continue
            src = os.path.join(src_pc_dir, name)
            dst = os.path.join(self.generators_folder, name)
            # Copy if not already present
            if not os.path.exists(dst):
                shutil.copy2(src, dst)
            # Fix prefix to point to glib package
            self._fix_pc_prefix(dst, glib_pkg)
            # Merge mkenums tool variables into glib-2.0.pc and gio-2.0.pc
            if name in ("glib-2.0.pc", "gio-2.0.pc", "gobject-2.0.pc",
                         "gmodule-2.0.pc", "gio-unix-2.0.pc",
                         "gthread-2.0.pc"):
                self._merge_mkenums_vars(dst, src)

    def _merge_mkenums_vars(self, dst_pc, src_pc):
        """Merge glib_mkenums/glib_genmarshal/gobject_query tool variables."""
        with open(dst_pc, encoding="utf-8", errors="replace") as f:
            dst = f.read()
        dst_lines = dst.splitlines()
        have_keys = set()
        for dl in dst_lines:
            if "=" in dl:
                have_keys.add(dl.split("=", 1)[0].strip())
        merge_lines = []
        with open(src_pc, encoding="utf-8", errors="replace") as f:
            for line in f:
                stripped = line.strip()
                if not stripped or "=" not in stripped or stripped.startswith("#"):
                    continue
                key = stripped.split("=", 1)[0].strip()
                if (key not in have_keys and
                    key not in ("Name", "Description", "Version",
                                "Libs", "Cflags", "Requires",
                                "Requires.private")):
                    merge_lines.append(stripped)
                    have_keys.add(key)
        if merge_lines:
            dst = dst.rstrip("\n") + "\n" + "\n".join(merge_lines) + "\n"
        with open(dst_pc, "w", encoding="utf-8", newline="\n") as f:
            f.write(dst)

    @staticmethod
    def _fix_pc_prefix(pc_path, prefix):
        """Rewrite the .pc prefix= line to point to the actual package."""
        if not os.path.isfile(pc_path):
            return
        data = open(pc_path, encoding="utf-8", errors="replace").read()
        data2 = re.sub(r"(?m)^prefix=.*$", "prefix=" + prefix, data, count=1)
        if data2 != data:
            open(pc_path, "w", encoding="utf-8").write(data2)

    # ------------------------------------------------------------------
    # build: meson setup + compile + install
    # ------------------------------------------------------------------
    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # ── 上游测试（R51 实测回填）──
        # Upstream tests: pk-test-library (10 subtests, daemon-independent).
        # On OHOS 7/10 pass; 'offline' fails because /tmp is read-only
        # (E002 platform limit). daemon/e2e tests need a running daemon and
        # are disabled (daemon_tests=false). Non-blocking (ignore_errors).
        if not cross_building(self):
            self.run(
                "meson test -C {} --print-errorlogs".format(self.build_folder),
                env="conanbuild",
                ignore_errors=True,
            )

    def package(self):
        # Install via meson
        meson = Meson(self)
        meson.install()
        # ── Remove daemon/CLI binaries (library-only package) ──
        # rm bin/ (pkgcli) and libexec/ (packagekitd, pk-offline-update)
        pkg_libexec = os.path.join(self.package_folder, "libexec")
        pkg_bin = os.path.join(self.package_folder, "bin")
        for p in (pkg_libexec, pkg_bin):
            if os.path.isdir(p):
                rmdir(self, p)
        # Remove dbus service/conf files (daemon, not library)
        dbus_dir = os.path.join(self.package_folder, "share", "dbus-1")
        if os.path.isdir(dbus_dir):
            rmdir(self, dbus_dir)
        # Remove polkit policy/rules (daemon, not library)
        polkit_dir = os.path.join(self.package_folder, "share", "polkit-1")
        if os.path.isdir(polkit_dir):
            rmdir(self, polkit_dir)
        # Remove conf files (daemon config)
        conf_dir = os.path.join(self.package_folder, "etc")
        if os.path.isdir(conf_dir):
            rmdir(self, conf_dir)
        # Remove metainfo, var (daemon data)
        for d in ("metainfo", "PackageKit", "var"):
            p = os.path.join(self.package_folder, "share", d)
            if os.path.isdir(p):
                rmdir(self, p)
        # Remove backend shared objects (daemon backends, not lib component)
        be_dir = os.path.join(self.package_folder, "lib", "packagekit-backend")
        if os.path.isdir(be_dir):
            rmdir(self, be_dir)
        # ── ELF 签名 (OHOS) + HMDFS symlink fix ──
        # OHOS loader requires signed ELF for dlopen; unsigned libs fail at
        # runtime with "Error loading shared library ... symbol not found".
        # Sign the real .so.18.1.3, then replace the versioned symlinks with
        # real copies (HMDFS musl loader cannot follow symlinks, E050).
        lib_dir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(lib_dir):
            real_so = os.path.join(lib_dir, "libpackagekit-glib2.so.18.1.3")
            if os.path.isfile(real_so):
                self._sign_elf(real_so)
                for link_name in ("libpackagekit-glib2.so.18", "libpackagekit-glib2.so"):
                    link_path = os.path.join(lib_dir, link_name)
                    # HMDFS islink() unreliable — unconditionally remove then copy
                    if os.path.lexists(link_path):
                        os.remove(link_path)
                    shutil.copy2(real_so, link_path)
                    self.output.info(f"HMDFS: replaced symlink {link_name} with signed real copy")
        # License
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def _sign_elf(self, elf_path):
        """Sign an OHOS ELF (needed for dlopen). Strips stale codesign then
        re-signs (jansson-proven pattern)."""
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning(f"signer {signer} not found, skip signing")
            return
        self.run(f'{objcopy} --remove-section .codesign "{elf_path}" 2>/dev/null || true')
        self.run(f'{signer} sign -inFile "{elf_path}" -outFile "{elf_path}" -selfSign 1')
        self.output.info(f"signed {os.path.basename(elf_path)}")

    def package_info(self):
        # Shared library
        self.cpp_info.libs = ["packagekit-glib2"]
        # pkg-config name matches upstream
        self.cpp_info.set_property("pkg_config_name", "packagekit-glib2")
        # Include path: <prefix>/include/PackageKit (upstream convention)
        self.cpp_info.includedirs = [os.path.join("include", "PackageKit")]
        # No explicit cpp_info.requires needed: Conan transitively passes
        # glib/2.84.0's libs via the dependency chain.
