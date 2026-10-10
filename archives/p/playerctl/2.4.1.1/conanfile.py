from conan import ConanFile
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.env import VirtualBuildEnv, Environment
from conan.tools.files import (
    copy,
    get,
    export_conandata_patches,
    apply_conandata_patches,
)
import glob
import os
import re
import shutil
import subprocess
import sys


_OHOS_BIN = "/data/service/hnp/bin"
_OHOS_OBJCOPY = _OHOS_BIN + "/llvm-objcopy"
_OHOS_SIGNER = _OHOS_BIN + "/binary-sign-tool"


class PlayerctlConan(ConanFile):
    name = "playerctl"
    version = "2.4.1.1"
    description = "Library and command-line utility to control media players implementing MPRIS"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/altdesktop/playerctl"
    url = "https://github.com/altdesktop/playerctl"
    topics = ("mpris", "media", "dbus", "player", "cli")

    # 产出 CLI 工具包（bin/playerctl、bin/playerctld）+ 公共 C 库 libplayerctl.so
    # → R38 需软件级 commands.json（type=tool，binary:true）
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def requirements(self):
        # 对齐 main 2.4.1 适配：glib/2.84.0.1（gobject/gio 组件；gio-unix-2.0 由本配方转发 .pc 补足）
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # OHOS profile 的 [buildenv] 前置的 meson 包装器损坏（ModuleNotFoundError: mesonbuild），
        # 走 ohpcd 预发布版本，由本配方遮罩它。
        self.tool_requires("meson/1.11.0")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        # conandata.yml 的 patches 为空映射（上游源码零补丁），保留 G1 要求的补丁管道入口
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = MesonToolchain(self)
        # 关闭 GIR + 文档（需 gobject-introspection / gtk-doc 与运行中的会话）及可选 shell 补全
        tc.project_options["introspection"] = False
        tc.project_options["gtk-doc"] = False
        tc.project_options["bash-completions"] = False
        tc.project_options["zsh-completions"] = False
        # 依赖一律走 conan，禁止 meson 偷偷下载 wrap 子项目
        tc.project_options["wrap_mode"] = "nodownload"
        # 产出共享库 + CLI（与 main 2.4.1 适配的产出形态一致，便于 .so 别名物化与 ELF 自签）
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.generate()
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()

        # MesonToolchain 把静态归档器 / strip 从 $AR / $STRIP 读取并写入 native file 的
        # [binaries]；该工具链的归档器位于 /data/service/hnp/bin（llvm-ar），meson 裸名
        # 自动探测无法经 PATH 定位，故通过 save_script 钉进 build 作用域。
        env = Environment()
        env.define("AR", "/data/service/hnp/bin/llvm-ar")
        env.define("STRIP", "/data/service/hnp/bin/llvm-strip")
        env.vars(self).save_script("playerctl_ar")

        # glib 配方未导出 gio-unix-2.0 组件，但其头文件与基础 include 路径已由 gio-2.0 提供。
        # 上游 meson.build 直接 dependency('gio-unix-2.0') → 生成一个转发型 gio-unix-2.0.pc。
        # MesonToolchain 把 generators_folder 硬编码为 meson 的 pkg_config_path，故把重定位
        # 后的正确 gio-unix-2.0.pc 直接落进该目录（版本从 gio-2.0.pc 读取，避免硬编码）。
        glib = self.dependencies["glib"]
        version = "2.84.0"
        gio_pc = os.path.join(self.generators_folder, "gio-2.0.pc")
        if os.path.isfile(gio_pc):
            with open(gio_pc, encoding="utf-8") as _f:
                for line in _f:
                    if line.startswith("Version:"):
                        version = line.split(":", 1)[1].strip()
                        break
        gio_unix_pc = os.path.join(self.generators_folder, "gio-unix-2.0.pc")
        with open(gio_unix_pc, "w") as _pc:
            _pc.write(
                "prefix={prefix}\n"
                "includedir=${{prefix}}/include\n"
                "libdir=${{prefix}}/lib\n\n"
                "Name: GIO unix specific APIs\n"
                "Description: unix specific headers for glib I/O library\n"
                "Version: {version}\n"
                "Requires: gobject-2.0, gio-2.0\n"
                "Cflags: -I${{includedir}}/gio-unix-2.0\n".format(
                    prefix=glib.package_folder, version=version)
            )

        # playerctl 的 meson.build 调用 gnome.gdbus_codegen / gnome.mkenums_simple，二者会
        # shell out 到 glib 工具（gdbus-codegen、glib-mkenums）。本 OHOS worker 上的 glib 工具
        # 位于用户卷，新解压文件间歇性 execve EACCES（HMDFS 信任延迟 / 整窗波动），且经 /bin/sh
        # 调用时该失败非确定且无法预热。因此：
        #   (a) patch 构建改为消费预生成的静态源文件而非调用 gnome codegen helper；
        #   (b) 用 python3 解释器直接运行 glib 工具（python3 读取 .py，无需 execve 工具本身，
        #       信任延迟永不触发）预先产出这些文件。这保持了上游构建行为不变。
        self._patch_playerctl_meson()
        self._pregenerate_glib_codegen()

    def _patch_playerctl_meson(self):
        mb = os.path.join(self.source_folder, "playerctl", "meson.build")
        with open(mb, "r") as _f:
            _txt = _f.read()
        _txt = re.sub(
            r"playerctl_generated = gnome\.gdbus_codegen\((?:.*\n)*?\)\n",
            "playerctl_generated = files('playerctl-generated.c', 'playerctl-generated.h')\n",
            _txt, count=1,
        )
        _txt = re.sub(
            r"enums = gnome\.mkenums_simple\((?:.*\n)*?\)\n",
            "enums = files('playerctl-enum-types.c', 'playerctl-enum-types.h')\n",
            _txt, count=1,
        )
        with open(mb, "w") as _f:
            _f.write(_txt)

    def _pregenerate_glib_codegen(self):
        glib = self.dependencies["glib"]
        glib_bin = os.path.join(glib.package_folder, "bin")
        py = sys.executable
        src = self.source_folder
        pctl_dir = os.path.join(src, "playerctl")
        xml = os.path.join(src, "data", "mpris-dbus-interface.xml")
        _dn = open(os.devnull, "w")

        # --- gdbus-codegen（header + body）---
        gdbus = os.path.join(glib_bin, "gdbus-codegen")
        for _out, _kind in (
            (os.path.join(pctl_dir, "playerctl-generated.c"), "--body"),
            (os.path.join(pctl_dir, "playerctl-generated.h"), "--header"),
        ):
            subprocess.run(
                [py, gdbus, "--c-generate-autocleanup", "all",
                 _kind, "--output", _out, xml],
                stdout=_dn, stderr=_dn, check=True,
            )

        # --- glib-mkenums（复刻 gnome.mkenums_simple，无前缀）---
        mkenums = os.path.join(glib_bin, "glib-mkenums")
        headers = ["playerctl.h", "playerctl-player.h",
                   "playerctl-player-manager.h", "playerctl-player-name.h"]
        hdr_paths = [os.path.join(pctl_dir, h) for h in headers]
        fhead_c = '#include "playerctl-enum-types.h"\n'
        for h in headers:
            fhead_c += '#include "%s"\n' % h
        fhead_c += '#define C_ENUM(v) ((gint) v)\n#define C_FLAGS(v) ((guint) v)\n'
        fprod = '/* enumerations from "@basename@" */\n'
        vhead = (
            "GType\n"
            "@enum_name@_get_type (void)\n"
            "{\n"
            "    static gsize gtype_id = 0;\n"
            "    static const G@Type@Value values[] = {\n"
        )
        vprod = '        { C_@TYPE@ (@VALUENAME@), "@VALUENAME@", "@valuenick@" },'
        vtail = (
            "        { 0, NULL, NULL }\n"
            "    };\n"
            "    if (g_once_init_enter (&gtype_id)) {\n"
            "        GType new_type = g_@type@_register_static (g_intern_static_string (\"@EnumName@\"), values);\n"
            "        g_once_init_leave (&gtype_id, new_type);\n"
            "    }\n"
            "    return (GType) gtype_id;\n"
            "}\n"
        )
        h_fhead = "#pragma once\n\n#include <glib-object.h>\n\nG_BEGIN_DECLS\n"
        h_fprod = '/* enumerations from "@basename@" */\n'
        h_vhead = (
            "GType @enum_name@_get_type (void);\n"
            "#define TYPE_@ENUMSHORT@ (@enum_name@_get_type())\n"
        )
        h_ftail = "G_END_DECLS\n"
        with open(os.path.join(pctl_dir, "playerctl-enum-types.c"), "w") as _c:
            subprocess.run([py, mkenums, "--fhead", fhead_c, "--fprod", fprod,
                           "--vhead", vhead, "--vprod", vprod, "--vtail", vtail,
                           *hdr_paths], stdout=_c, stderr=_dn, check=True)
        with open(os.path.join(pctl_dir, "playerctl-enum-types.h"), "w") as _h:
            subprocess.run([py, mkenums, "--fhead", h_fhead, "--fprod", h_fprod,
                           "--vhead", h_vhead, "--ftail", h_ftail,
                           *hdr_paths], stdout=_h, stderr=_dn, check=True)
        _dn.close()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        # playerctl.h / playerctl-player.h 都 `#include <playerctl/playerctl-enum-types.h>`。
        # 上游经 gnome.mkenums_simple 产出该头，改静态文件消费后 meson 不再 install 它，
        # 故手动装到 include/playerctl/ 让下游消费者可编译公共 API。
        copy(self, "playerctl-enum-types.h",
             os.path.join(self.source_folder, "playerctl"),
             os.path.join(self.package_folder, "include", "playerctl"))
        # 保留上游 meson 生成的 lib/pkgconfig/playerctl.pc（test_ohos T6 校验
        # Name=Playerctl / Version=2.4.1），不再删除。
        # 构建沙箱不支持 symlink/link：物化 .so 别名并 ELF 自签（鸿蒙 XPM 要求）
        self._ensure_shared_lib_aliases()
        self._sign_artifacts()

    def _ensure_shared_lib_aliases(self):
        """补齐共享库的链接名与 SONAME 文件。

        构建沙箱内 symlinkat()/linkat() 被内核拒绝（实测 `ln -s` → exit 1、
        os.link → EPERM，而 cp/copy2 正常），meson install 因此打印
        "Symlink creation does not work on this platform. Skipping all
        symlinking." 并跳过全部符号链接，lib/ 只剩 libplayerctl.so.2.4.1。
        消费方 `-lplayerctl`（playerctl.pc 的 Libs）找不到 libplayerctl.so、
        运行时按 SONAME（libplayerctl.so.2）加载也会失败。
        已发布的 glib 包中 libglib-2.0.so / .so.0 / .so.0.8400.0 即为同尺寸实体文件，
        故在别名缺失时用实体文件补齐；meson 能正常建链的环境不产生任何改动。
        """
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        real = [p for p in glob.glob(os.path.join(libdir, "libplayerctl.so.*"))
                if not os.path.islink(p)]
        if not real:
            return
        source = sorted(real)[-1]
        major = os.path.basename(source)[len("libplayerctl.so."):].split(".")[0]
        for alias in ("libplayerctl.so." + major, "libplayerctl.so"):
            target = os.path.join(libdir, alias)
            if os.path.lexists(target):
                continue
            shutil.copy2(source, target)
            self.output.info(
                "Materialized shared library alias %s (symlinks unsupported)"
                % os.path.basename(target))

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_artifacts(self):
        """鸿蒙 PC XPM：被 exec 的可执行文件 / 动态库需代码签名。

        工具（binary-sign-tool / llvm-objcopy）缺失时告警不阻塞，兼容 cross / SDK 环境。
        """
        targets = []
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                path = os.path.join(bindir, name)
                if os.path.isfile(path) and not os.path.islink(path):
                    targets.append(path)
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            for pattern in ("**/*.so", "**/*.so.*"):
                targets.extend(glob.glob(os.path.join(libdir, pattern), recursive=True))
        targets = [t for t in targets if self._is_elf(t)]
        if not targets:
            return
        signer = _OHOS_SIGNER
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip OHOS codesign (cross/SDK env)")
            return
        objcopy = _OHOS_OBJCOPY if os.path.isfile(_OHOS_OBJCOPY) else shutil.which("llvm-objcopy")
        for target in sorted(set(targets)):
            if objcopy:
                self.run('"%s" --remove-section .codesign "%s" 2>/dev/null || true'
                         % (objcopy, target))
            self.run('"%s" sign -inFile "%s" -outFile "%s" -selfSign 1'
                     % (signer, target, target))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "playerctl")
        self.cpp_info.libs = ["playerctl"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        # playerctl.h 直接 include <glib-object.h>/<glib.h>，消费方需要 glib 头
        self.cpp_info.requires = [
            "glib::glib-2.0",
            "glib::gobject-2.0",
            "glib::gio-2.0",
        ]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
