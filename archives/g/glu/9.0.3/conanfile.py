#!/usr/bin/env python3
"""Conan recipe for glu 9.0.3 — Mesa OpenGL Utility library (libGLU).

上游为 freedesktop/mesa 的 glu（独立库，随 mesa 一起维护），
发布归档在 archive.mesa3d.org。

OHOS 适配要点
-------------
1. **没有桌面 GL**：OHOS SDK 只提供 EGL + GLES2/GLES3（无 `libGL.so` / `glx.h`）。
   GLU 本身是「桌面 GL 的配套工具库」，但它**不引用 GLX**（实测源码 glX 命中 0），
   只需一份提供 OpenGL API 的实现即可。故选用 **Mesa 的 OSMesa**：
   `mesa/24.3.4.1` 交付 `libOSMesa.so` + `include/GL/gl.h`（离屏软件桌面 GL，
   不需要 X11/Wayland）。glu 的 meson 原生支持这一组合——
   `gl_provider` 选项的 choices 就是 `['glvnd', 'gl', 'osmesa']`。

2. **必须删掉上游的 `gnu_symbol_visibility: 'hidden'`**（补丁 0001）：
   `src/meson.build` 无条件设了该属性，而源码里**没有任何 `visibility default`
   标注**。后果极具欺骗性——编译成功、产物约 1.5 MB 看着正常，但
   **动态符号表里导出 0 个 `glu*` 符号**（符号在 `.symtab` 里是 `LOCAL HIDDEN`），
   任何消费者链接都会失败。实测对照：

   | 配置 | dynsym 导出 `glu*` |
   |------|-------------------|
   | 上游原样（带 hidden）| **0** |
   | 删除该行 | **64**（`gluOrtho2D` = `GLOBAL DEFAULT`）|

3. **`.pc` 名字要对上**：mesa 的 `package_info` 只设了 `libs`/`cmake_*`，
   **未设 `pkg_config_name`**，故 conan 的 `PkgConfigDeps` 生成的是 `mesa.pc`；
   而 glu 在 `gl_provider=osmesa` 时执行 `dependency('osmesa')` —— 名字不匹配。
   故 `generate()` 里把 mesa 包内自带的 `osmesa.pc` 复制出来并**修正其 prefix**
   （包内那份 `prefix=/`、`libdir=/lib`，直接给 meson 用会导致 `-L/lib` 找不到
   `-lOSMesa`，实测链接报 `unable to find library -lOSMesa`）。
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get, replace_in_file, rmdir)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class GluConan(ConanFile):
    name = "glu"
    version = "9.0.3"
    description = "Mesa OpenGL Utility library (GLU): mipmapping, NURBS, tessellation, quadrics"
    license = "SGI-B-2.0"
    homepage = "https://gitlab.freedesktop.org/mesa/glu"
    url = "https://archive.mesa3d.org/glu/"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # OHOS 无桌面 GL，改用 Mesa 的 OSMesa（离屏软件桌面 GL，无 X11 依赖）。
        self.requires("mesa/24.3.4.1")

    def generate(self):
        PkgConfigDeps(self).generate()
        self._provide_osmesa_pc()
        tc = MesonToolchain(self)
        tc.project_options["gl_provider"] = "osmesa"
        tc.generate()
        self._inject_meson_binaries()

    def _inject_meson_binaries(self):
        """把 ar / ranlib / pkg-config 注入 conan_meson_native.ini。

        meson 默认按 PATH 依次找 llvm-ar-15 / llvm-ar / ar / gar，但 OHOS 工具链
        不在 PATH 上（CI profile 只通过 tools.build:compiler_executables 指定了
        c/cpp），实测报：
            Unknown linker(s): [['llvm-ar-15'], ['llvm-ar'], ['ar'], ['gar']]
        故从编译器所在目录推导 ar/ranlib 并显式写入 native file。
        （与 pygobject / gusb / libgudev 配方同一做法。）
        """
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = ce.get("ar")
        rl = ce.get("ranlib")
        if not ar:
            cc = ce.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                for name in ("llvm-ar", "ar"):
                    cand = os.path.join(bindir, name)
                    if os.path.isfile(cand):
                        ar = cand
                        break
                for name in ("llvm-ranlib", "ranlib"):
                    rlc = os.path.join(bindir, name)
                    if os.path.isfile(rlc):
                        rl = rlc
                        break
        pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        for nf_name in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            nf = os.path.join(self.generators_folder, nf_name)
            if not os.path.isfile(nf):
                continue
            with open(nf) as f:
                content = f.read()
            if "[binaries]" not in content:
                continue
            new_lines = []
            for line in content.splitlines(True):
                new_lines.append(line)
                if line.strip() == "[binaries]":
                    if ar and "\nar =" not in content:
                        new_lines.append("ar = '%s'\n" % ar)
                    if rl and "\nranlib =" not in content:
                        new_lines.append("ranlib = '%s'\n" % rl)
                    if pkg_config and "\npkg-config =" not in content:
                        new_lines.append("pkg-config = '%s'\n" % pkg_config)
            new_content = "".join(new_lines)
            if new_content != content:
                with open(nf, "w") as f:
                    f.write(new_content)

    def _provide_osmesa_pc(self):
        """把 mesa 包内的 osmesa.pc 复制到生成目录并修正 prefix。

        PkgConfigDeps 按**包名**生成 `mesa.pc`，而 glu 在 gl_provider=osmesa 时
        执行 `dependency('osmesa')` → 名字对不上，直接失败。mesa 包内自带
        `lib/pkgconfig/osmesa.pc`，但其中 prefix=/ → libdir=/lib，照用会让
        pkg-config 发出 `-L/lib` 而找不到 `-lOSMesa`，故需重写 prefix。
        """
        mesa = self.dependencies["mesa"]
        pkg_folder = mesa.package_folder
        pc_src = os.path.join(pkg_folder, "lib", "pkgconfig", "osmesa.pc")
        dst_dir = os.path.join(self.generators_folder)
        if not os.path.isfile(pc_src):
            self.output.warning(f"osmesa.pc not found in mesa package: {pc_src}")
            return
        dst = os.path.join(dst_dir, "osmesa.pc")
        copy(self, "osmesa.pc", src=os.path.join(pkg_folder, "lib", "pkgconfig"),
             dst=dst_dir, keep_path=False)
        # 修正 prefix（包内写死为 /，指向 conan 包目录）
        replace_in_file(self, dst, "prefix=/", f"prefix={pkg_folder}")
        self.output.info(f"provided osmesa.pc (prefix={pkg_folder})")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        # meson 会把 .pc 与 cmake 文件也装上；保留头文件与库，清掉多余文档目录
        rmdir(self, os.path.join(self.package_folder, "share"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # 必须在所有内容改动**之后**处理 .so：meson.install() 会改写 RUNPATH
        # （构建树里为 <mesa>/lib，安装后为空 —— 实测两文件 sha256 不同），
        # 这会让链接期写入的 .codesign 失效：文件仍带 .codesign 段，但内容与签名
        # 不匹配，dlopen 报 "Permission denied"。实测对照（同一文件）：
        #   包内原样        → dlopen 失败 Permission denied
        #   清掉 .codesign 重签 → dlopen 成功
        # OHOS 要求可 dlopen 的 .so 带有效签名，故此处重新签名。
        self._fix_so_permissions()
        self._sign_so_files()

    def _fix_so_permissions(self):
        """对包内 .so（含符号链接目标）显式 chmod 0755。

        经 meson install 落地的文件权限可能为 750（owner 20001006:file_manager，
        other 无读权限）。CI 进程非 owner 且不在该组时 dlopen 报 Permission denied。
        chmod 不改内容，故不影响后续签名有效性。
        """
        import glob
        for pat in ("**/*.so", "**/*.so.*"):
            for so in glob.glob(os.path.join(self.package_folder, pat), recursive=True):
                if os.path.islink(so):
                    continue
                try:
                    os.chmod(so, 0o755)
                except OSError as e:
                    self.output.warning(f"chmod failed for {so}: {e}")

    def _sign_so_files(self):
        """对包内 .so 重新签名，使签名覆盖 meson.install() 改写后的最终字节。

        仓库既有模式：先 llvm-objcopy --remove-section .codesign 清陈旧段，
        再 binary-sign-tool sign -selfSign 1 自签。
        """
        import glob
        signer = next((p for p in ("/data/service/hnp/bin/binary-sign-tool",
                                   shutil.which("binary-sign-tool") or "")
                       if p and os.path.isfile(p)), None)
        objcopy = next((p for p in ("/data/service/hnp/bin/llvm-objcopy",
                                    shutil.which("llvm-objcopy") or "")
                        if p and os.path.isfile(p)), None)
        if signer is None:
            self.output.warning(
                "binary-sign-tool 未找到，跳过 .so 签名——OHOS 上未签名的 .so "
                "无法 dlopen。若在非 OHOS 环境构建可忽略。")
            return
        sos = set()
        for pat in ("**/*.so", "**/*.so.*"):
            sos.update(glob.glob(os.path.join(self.package_folder, pat), recursive=True))
        n = 0
        for so in sorted(sos):
            if os.path.islink(so):
                continue
            if objcopy:
                self.run(f'"{objcopy}" --remove-section .codesign "{so}" 2>/dev/null || true',
                         ignore_errors=True)
            self.run(f'"{signer}" sign -inFile "{so}" -outFile "{so}" -selfSign 1')
            try:
                os.chmod(so, 0o755)
            except OSError as e:
                self.output.warning(f"chmod failed for {so}: {e}")
            n += 1
        self.output.info(f"signed {n} .so file(s) for OHOS")

    def package_info(self):
        self.cpp_info.libs = ["GLU"]
        self.cpp_info.set_property("cmake_file_name", "glu")
        self.cpp_info.set_property("cmake_target_name", "glu::glu")
        self.cpp_info.set_property("pkg_config_name", "glu")
        # GLU 依赖 OpenGL 实现（此处为 OSMesa），供消费者解析传递依赖
        self.cpp_info.requires = ["mesa::mesa"]
