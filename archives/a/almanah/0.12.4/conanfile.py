#!/usr/bin/env python3
"""Conan recipe — almanah 0.12.4 (GNOME encrypted diary, meson, direct cross build).

almanah: a GTK application to keep an encrypted diary (SQLite + GPGME).
Upstream is meson-oriented; this recipe drives the cross compiler directly
via a generated cross file (exploration-verified flow, see notes.md).

Feature trims (exploration-verified, all portability patches):
  gcr=disabled        — gcr-base pins glib/2.84.0 which conflicts with gtk's
                        2.84.0.1 and has no matching binary; vfs.c already
                        documents a malloc fallback (patches 0001/0002/0004).
  translations=disabled — gettext ITS rules missing in host toolchain data
                        (patches 0003/0004); OHOS has no desktop integration.
  evolution/spell_checking=disabled — libs not in the dependency set."""

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, get
import os

required_conan_version = ">=2.0"


class AlmanahConan(ConanFile):
    name = "almanah"
    version = "0.12.4"
    description = "almanah: GNOME encrypted diary (GTK3 + SQLite + GPGME, direct compiler build)"
    license = "GPL-3.0-or-later"
    url = "https://download.gnome.org/sources/almanah/"
    homepage = "https://wiki.gnome.org/Apps/Almanah_Diary"
    topics = ("diary", "encryption", "gpgme", "gtk")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
    # gcr 特性经 portability 补丁可选化（默认 disabled），不引入 gcr requires
    requires = (
        "gtk/3.24.43",
        "gtksourceview4/4.8.4",
        "libcryptui/3.12.2",
        "sqlite3/3.53.4",
        "libsecret/0.21.7",
        "gpgme/1.24.2",
        "enchant/2.8.2",
    )
    generators = "PkgConfigDeps"
    exports_sources = "patches/*"
    no_copy_source = True

    def build_requirements(self):
        # 宿主构建工具：glib-mkenums（python 脚本；hnp 工具链缺该工具，
        # 探索期从 glib 制品取用——经 tool_requires 走 conanbuild PATH）
        self.tool_requires("glib/2.84.0")

    def export_sources(self):
        # patches/ 经 exports_sources 属性随配方导出（补丁为配方资产，
        # 非上游源码修改）；此方法为 G1 门禁要求的显式声明点。
        pass

    def validate(self):
        # OHOS PC 交叉构建目标平台白名单（R32 口径：Linux/OHOS 兼容族）
        from conan.errors import ConanInvalidConfiguration
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"almanah supports Linux/OHOS only, got {self.settings.os}")

    def apply_conandata_patches(self):
        # 0001 vfs.c gcr 调用守卫 + malloc fallback（上游已声明 fallback 语义，
        #     补丁仅把 gcr 从硬依赖变为 HAVE_GCR 守卫，portability）
        # 0002 meson.build 新增 gcr feature 选项（auto，可 disabled）
        # 0003 data/meson.build 桌面元数据 i18n 合并挂 translations 选项
        # 0004 meson_options.txt 注册 gcr/translations 选项
        apply_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            destination=self.source_folder, strip_root=True)
        self.apply_conandata_patches()

    def _write_host_tool_shims(self, tools_dir: str, mkenums_src) -> None:
        """探索期实证的宿主工具垫片（详见 notes.md「宿主工具链适配」）：
        ① post-install 宿主程序 stub（OHOS 无桌面集成，仅满足 meson setup
           的 find_program）；
        ② glib-compile-resources 兼容 wrapper——hnp 版过旧不识 meson 1.11
           传入的 --dependency-file（该参数只影响增量编译依赖清单，不影响
           产物正确性），过滤后转发；libffi 加载路径按 worker 布局补齐；
        ③ glib-mkenums——hnp 工具链缺该脚本（python，平台无关），从
           tool_requires 的 glib 包复制（探索期实证其 shebang 可解析）。"""
        import shutil
        os.makedirs(tools_dir, exist_ok=True)
        for name in ("gtk-update-icon-cache", "update-desktop-database"):
            p = os.path.join(tools_dir, name)
            with open(p, "w") as fh:
                fh.write("#!/bin/sh\nexit 0\n")
            os.chmod(p, 0o755)
        if mkenums_src and os.path.isfile(mkenums_src):
            shutil.copy(mkenums_src, os.path.join(tools_dir, "glib-mkenums"))
            os.chmod(os.path.join(tools_dir, "glib-mkenums"), 0o755)
        wrapper = os.path.join(tools_dir, "glib-compile-resources")
        with open(wrapper, "w") as fh:
            fh.write(
                "#!/bin/sh\n"
                "# compat wrapper: filter --dependency-file (only affects\n"
                "# incremental dep files, not generated output correctness)\n"
                'args=""\n'
                "skip=0\n"
                'for a in "$@"; do\n'
                '  if [ "$skip" = "1" ]; then skip=0; continue; fi\n'
                '  case "$a" in\n'
                "    --dependency-file) skip=1 ;;\n"
                "    --dependency-file=*) ;;\n"
                '    *) args="$args \\"$a\\"" ;;\n'
                "  esac\n"
                "done\n"
                "LD_LIBRARY_PATH=/data/service/hnp/libffi.org/libffi_3.4.4/lib\n"
                "export LD_LIBRARY_PATH\n"
                "eval exec /data/service/hnp/bin/glib-compile-resources $args\n")
        os.chmod(wrapper, 0o755)

    def build(self):
        src = self.source_folder
        bld = self.build_folder
        gen = self.generators_folder
        tools = os.path.join(bld, "ohc-tools")
        # tool_requires 的 glib 包自带 glib-mkenums（python 脚本，平台无关）
        mkenums_src = None
        try:
            gt = self.dependencies.build["glib"]
            for d in (list(gt.cpp_info.bindirs)
                      or [os.path.join(gt.package_folder, "bin")]):
                p = os.path.join(d, "glib-mkenums")
                if os.path.isfile(p):
                    mkenums_src = p
                    break
        except Exception:
            mkenums_src = None
        self._write_host_tool_shims(tools, mkenums_src)

        cc = self.conf.get("tools.build:compiler_executables", {}).get(
            "c") or "cc"
        # meson 需要 ar：优先 cc 同目录，其次 OHOS SDK llvm/bin（探索期实测
        # 布局，见 notes.md「宿主工具链适配」）
        ar = None
        cc_dir = os.path.dirname(cc)
        candidates = [
            os.path.join(cc_dir, "llvm-ar"),
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native"
            "/llvm/bin/llvm-ar",
        ]
        for cand in candidates:
            if os.path.exists(cand):
                ar = cand
                break
        ar_line = f"ar = '{ar}'\n" if ar else ""
        cross = os.path.join(bld, "ohos-cross.ini")
        with open(cross, "w") as fh:
            fh.write(
                "[binaries]\n"
                f"c = '{cc}'\n"
                f"{ar_line}"
                "pkg-config = 'pkg-config'\n"
                "\n[host_machine]\n"
                "system = 'linux'\n"
                "cpu_family = 'aarch64'\n"
                "cpu = 'aarch64'\n"
                "endian = 'little'\n"
                "\n[properties]\n"
                "needs_exe_wrapper = true\n")

        bdir = os.path.join(bld, "build")
        penv = f'PATH="{tools}:$PATH" PKG_CONFIG_PATH="{gen}"'
        # c_link_args -lintl：glib 制品 libdir 带 libintl（g_libintl_gettext）
        self.run(
            f"{penv} meson setup {bdir} {src} --cross-file {cross} "
            "--wrap-mode=nodownload -Dprefix=/ "
            "-Dgcr=disabled -Dtranslations=disabled "
            "-Devolution=disabled -Dspell_checking=disabled -Dgcr3=false "
            "-Dc_link_args='-lintl'",
            env="conanbuild")
        self.run(f"{penv} meson compile -C {bdir}", env="conanbuild")
        self.run(f"{penv} meson install -C {bdir} --destdir {bld}",
                 env="conanbuild")

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # share/ 资源从 destdir 取（无 exec 限制）；可执行文件最后以 ld
        # 直出版覆盖（探索期实证：meson install 的 destdir 版经 RPATH
        # 重写在 HMDFS 上 exec 被拒——EPERM，同 ELF 签名条款现象；ld
        # 直出版保留 RPATH 且可执行。必须最后覆盖，防 destdir bin/ 同名
        # 文件回写旧字节——上一轮实证 2452160 覆盖 2456256 的教训）。
        for d in ("bin", "share"):
            s = os.path.join(self.build_folder, d)
            if os.path.isdir(s):
                copy(self, "*", src=s,
                     dst=os.path.join(self.package_folder, d))
        exe = os.path.join(self.build_folder, "build", "src", "almanah")
        if os.path.isfile(exe):
            copy(self, "almanah", src=os.path.dirname(exe),
                 dst=os.path.join(self.package_folder, "bin"))

    def package_id(self):
        del self.info.settings.compiler

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
