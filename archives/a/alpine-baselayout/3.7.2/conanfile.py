#!/usr/bin/env python3
"""Conan recipe for alpine-baselayout 3.7.2 — Alpine base dir structure and init scripts.

alpine-baselayout 是 Alpine Linux 的基础目录结构与 init 脚本包（noarch 数据/配置包，
上游 APKBUILD 声明 arch="noarch"，GPL-2.0-only）。它由一组静态文本文件组成：
系统配置文件（group/passwd/inittab/profile/protocols/services 等）、
crontab、profile.d 脚本与 modprobe.d 内核模块配置，没有编译步骤
（上游 build() 仅用 awk 从 passwd 生成 shadow）。

本配方从 Alpine aports 仓库（v3.23 分支 3.7.2-r0，commit
15b3b78187b3808104f98f765e9632e0b09281a7）逐文件下载并校验 SHA256，
在 package() 中复现上游安装布局（相对包内路径，不写宿主系统绝对路径），
并安装 GPL-2.0 许可证文本。
"""
import hashlib
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, download, export_conandata_patches
from conan.tools.layout import basic_layout


class AlpineBaselayoutConan(ConanFile):
    name = "alpine-baselayout"
    version = "3.7.2"
    description = "Alpine base dir structure and init scripts"
    license = "GPL-2.0-only"
    homepage = "https://gitlab.alpinelinux.org/alpine/aports/-/tree/master/main/alpine-baselayout"
    url = ""  # CI fills this

    package_type = "application"
    no_copy_source = True

    # L0p: OHOS profile 需要完整四项 settings
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self, src_folder="src")

    def export_sources(self):
        # GPL-2.0.txt (official GPLv2 text from gnu.org) lives in the recipe
        # folder and must reach the source folder for package().
        export_conandata_patches(self)
        copy(self, "GPL-2.0.txt", src=self.recipe_folder,
             dst=self.export_sources_folder)

    def source(self):
        """Download all source files from conandata.yml sources.

        Each entry is a plain text file (shell/config), so use download() —
        get() would try to unzip them and fail with BadZipFile.
        protocols/services carry an explicit `filename` key (downloaded as
        protocols-6.4 / services-6.4 per the upstream APKBUILD source list).
        """
        for fname, info in self.conan_data["sources"]["files"].items():
            target = info.get("filename", fname)
            url = info["url"]
            if url.startswith("file://"):
                # CI predl 预下载把 conandata URL 改写为 file:// 本地缓存路径。
                # conan 的 download() 会 percent-decode 路径（%2D -> '-'），而 predl
                # 保存的文件名保留字面 %2D，导致路径不匹配；这里手动复制并校验 SHA256。
                src_path = url[len("file://"):]
                if not os.path.isfile(src_path):
                    alt = src_path.replace("%2D", "-")
                    if os.path.isfile(alt):
                        src_path = alt
                self.output.info(f"Copying {fname} from predl cache: {src_path}")
                dst = os.path.join(self.source_folder, target)
                shutil.copy2(src_path, dst)
                h = hashlib.sha256()
                with open(dst, "rb") as f:
                    for chunk in iter(lambda: f.read(65536), b""):
                        h.update(chunk)
                if h.hexdigest() != info["sha256"]:
                    raise Exception(f"SHA256 mismatch for {fname}: {h.hexdigest()}")
            else:
                self.output.info(f"Downloading {fname} as {target}...")
                download(self, url, sha256=info["sha256"], filename=target)

        # GPL-2.0.txt was exported to the source root; move it into src/ so
        # package() can find it at self.source_folder.
        gpl_root = os.path.join(self.source_folder, "..", "GPL-2.0.txt")
        if os.path.exists(gpl_root):
            os.rename(gpl_root, os.path.join(self.source_folder, "GPL-2.0.txt"))

    def build(self):
        """Reproduce upstream prepare()+build(): rename netbase files, then
        generate shadow from passwd.

        Upstream APKBUILD prepare():
          mv "$srcdir"/protocols-6.4 "$srcdir"/protocols
          mv "$srcdir"/services-6.4 "$srcdir"/services
        build():
          awk -F: '{ pw = ":!:"; if ($1 == "root") { pw = "::" }
                     print($1 pw ":0:::::") }' passwd > shadow
        """
        src = self.source_folder
        for nb_name in ("protocols-6.4", "services-6.4"):
            nb_path = os.path.join(src, nb_name)
            if os.path.exists(nb_path):
                os.rename(nb_path, os.path.join(src, nb_name.split("-", 1)[0]))

        # No upstream patches for 3.7.2 (conandata patches: {}), but keep the
        # standard hook so future patches apply (G1 completeness).
        apply_conandata_patches(self)

        passwd_path = os.path.join(src, "passwd")
        shadow_path = os.path.join(src, "shadow")
        with open(passwd_path, encoding="utf-8") as f:
            lines = []
            for raw in f:
                name = raw.split(":", 1)[0]
                pw = "::" if name == "root" else ":!:"
                lines.append(f"{name}{pw}:0:::::")
        with open(shadow_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    def package(self):
        """Install real artifacts (relative to package_folder, never host paths).

        Mirrors the upstream APKBUILD package() layout but keeps every
        destination under the Conan package folder. Alpine rootfs paths such
        as /dev, /proc, /sys, /bin, /lib, /var are NOT recreated — those are
        host-system paths that must not be copied into a user-level package.
        """
        src = self.source_folder
        pkg = self.package_folder

        def install(name, rel_dst, mode=0o644):
            dst = os.path.join(pkg, rel_dst)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(os.path.join(src, name), dst)
            os.chmod(dst, mode)

        # etc/crontabs/root (mode 600 upstream)
        install("crontab", "etc/crontabs/root", mode=0o600)

        # etc/profile.d/
        install("color_prompt.sh.disabled", "etc/profile.d/color_prompt.sh.disabled")
        install("20locale.sh", "etc/profile.d/20locale.sh")

        # etc/modprobe.d/
        install("aliases.conf", "etc/modprobe.d/aliases.conf")
        install("blacklist.conf", "etc/modprobe.d/blacklist.conf")
        install("i386.conf", "etc/modprobe.d/i386.conf")

        # etc/ top-level config files
        for f in ("group", "inittab", "passwd", "profile",
                  "protocols", "services"):
            install(f, f"etc/{f}")
        install("shadow", "etc/shadow", mode=0o640)

        # usr/share/man/man7/hier.7
        install("hier.7", "usr/share/man/man7/hier.7")

        # license
        lic = os.path.join(pkg, "licenses")
        os.makedirs(lic, exist_ok=True)
        shutil.copy2(os.path.join(src, "GPL-2.0.txt"), os.path.join(lic, "GPL-2.0.txt"))

    def package_info(self):
        # 纯配置/数据包：无库、无可执行文件
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
